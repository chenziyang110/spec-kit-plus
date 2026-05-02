# sp-prd v2 Depth-Aware Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade `sp-prd` to a depth-aware current-state PRD workflow that triages critical capabilities, requires targeted evidence harvest, strengthens master-pack/export structure, and blocks shallow PRD suites through compatible artifact validation.

**Architecture:** Keep `templates/commands/prd.md` and `templates/prd/*.md` as the product-truth source for the workflow and export shape, then harden `src/specify_cli/hooks/artifact_validation.py` so completion can fail closed when the PRD suite is only surface-complete. Preserve the existing artifact set and generated-skill projection paths; do not introduce a new runtime subsystem or new hard-required artifact files in `v2.1`.

**Tech Stack:** Markdown workflow templates, Python hook validators, pytest contract tests, generated Codex/skills surfaces

---

## File Structure

```text
MODIFY:
  templates/commands/prd.md                         — Add capability triage, targeted evidence harvest, depth-aware coverage semantics, and quality gates
  templates/prd/master-pack-template.md             — Add tiered capability inventory and critical capability dossiers
  templates/prd/export-prd-template.md              — Reflect depth-qualified capability output and confidence handling
  templates/prd/export-internal-brief-template.md   — Map critical capabilities back to code/module hotspots
  templates/passive-skills/project-to-prd/SKILL.md  — Route PRD work as depth-aware current-state extraction
  src/specify_cli/hooks/artifact_validation.py      — Add compatible structural validation for depth-aware PRD suites
  tests/test_prd_template_guidance.py               — Assert new workflow contract and quality-gate language
  tests/test_prd_export_templates.py                — Assert master-pack/export template depth structure
  tests/test_prd_hook_contract.py                   — Assert PRD hook blocks shallow master-pack/coverage artifacts
  tests/contract/test_hook_cli_surface.py           — Assert CLI validate-artifacts path enforces new PRD structure
  tests/test_passive_skill_guidance.py              — Assert passive skill guidance mentions depth-aware extraction
  tests/test_extension_skills.py                    — Assert generated `sp-prd` skills include new workflow semantics
  tests/integrations/test_integration_codex.py      — Assert Codex-generated `sp-prd` skill projects the new contract

VERIFY ONLY:
  tests/test_prd_cli_helpers.py                     — Sanity check helper-created PRD workspaces still match the unchanged artifact skeleton
```

## Scope and Release Order

Ship this in five slices:

1. Harden the `sp-prd` command template contract
2. Upgrade the master-pack and export templates
3. Update passive/generated skill guidance propagation
4. Add compatible artifact-validation gates
5. Run focused regressions and freeze `v2.1`

Do not add new standalone `capability-triage.md` or `depth-policy.md` files in this slice. Encode the contract inside the existing required artifacts first.

---

### Task 1: Harden the `sp-prd` Command Template Contract

**Files:**
- Modify: `templates/commands/prd.md`
- Test: `tests/test_prd_template_guidance.py`

**Intent:** Make the workflow itself require capability triage, targeted evidence harvest, depth-aware coverage semantics, and completion gates before any hook logic is added.

- [ ] **Step 1: Add failing template-guidance tests for the new workflow phases and quality gates**

Append these tests to `tests/test_prd_template_guidance.py`:

```python
def test_prd_template_requires_capability_triage_and_targeted_evidence_harvest() -> None:
    content = _content().lower()

    assert "capability triage" in content
    assert "targeted evidence harvest" in content
    assert "critical" in content
    assert "high" in content
    assert "standard" in content
    assert "auxiliary" in content


def test_prd_template_requires_depth_aware_coverage_and_quality_gates() -> None:
    content = _content()
    lowered = content.lower()

    assert "depth-qualified" in lowered
    assert "surface-covered" in lowered
    assert "depth-gap" in lowered
    assert "## Quality Gates" in content or "quality gates" in lowered
    assert "Capability Triage Gate" in content
    assert "Critical Depth Gate" in content
    assert "Traceability Gate" in content
    assert "Export Integrity Gate" in content
```

- [ ] **Step 2: Run the template-guidance tests to verify the new assertions fail**

Run:

```bash
pytest tests/test_prd_template_guidance.py -q
```

Expected: FAIL with missing references to `capability triage`, `targeted evidence harvest`, and the new quality gates.

- [ ] **Step 3: Update `templates/commands/prd.md` to add the new phases and contract language**

In `templates/commands/prd.md`, replace the current process core with a depth-aware sequence. The edited sections must add:

- a new `4. **Capability triage**`
- a renamed `5. **Targeted evidence harvest**`
- a depth-aware `6. **Build coverage matrix**`
- a master-pack section that calls for `critical` and `high` capability dossiers
- a new `8. **Run quality gates**`

Insert and adapt content in this shape:

```markdown
4. **Capability triage**
   - Identify the repository-backed core value proposition before broad synthesis.
   - Reconstruct capability IDs and assign each one a depth tier: `critical`, `high`, `standard`, or `auxiliary`.
   - Record why each `critical` or `high` capability matters, which sources own it, and which implementation details must be reconstructed before completion can be claimed.
   - Treat cross-cutting behaviors as first-class capabilities even when they span multiple modules or do not align to one UI screen or one service entrypoint.

5. **Targeted evidence harvest**
   - Populate `.specify/prd-runs/<run-id>/evidence/` with notes or files for relevant surfaces.
   - Continue broad surface collection for repository surfaces, UI surfaces, service surfaces, entities and models, workflows, rules, integrations, configuration, permissions, error states, and test/verification clues.
   - For `critical` and `high` capabilities, deepen collection to implementation files, key functions, parsers/serializers, compatibility logic, edge-case handlers, and failure paths.
   - Label every consequential claim as `Evidence`, `Inference`, or `Unknown`.

6. **Build depth-aware coverage matrix**
   - Maintain `.specify/prd-runs/<run-id>/coverage-matrix.md`.
   - Track each capability, its tier, evidence status, depth status, source paths, confidence, and export destinations.
   - Use depth-aware states such as `surface-covered`, `partially-reconstructed`, `depth-gap`, `blocked-by-unknowns`, and `depth-qualified`.
   - For `critical` and `high` capabilities, include a breakdown covering implementation mechanisms, format/protocol coverage when applicable, edge cases, and traceability.

7. **Synthesize the unified master pack**
   - Write `.specify/prd-runs/<run-id>/master/master-pack.md`.
   - Treat `master/master-pack.md` as the single truth source for all exports.
   - Include product frame, capability inventory, critical capability dossiers, UI/service surface inventory, data and rule model, integrations, constraints, Evidence/Inference/Unknown registry, and coverage/export map.
   - Do not maintain separate export-only facts that are absent from the master pack.

8. **Run quality gates**
   - Run the Capability Triage Gate: block completion if core capabilities and tiers were never made explicit.
   - Run the Critical Depth Gate: block completion if a `critical` capability lacks implementation-grade reconstruction.
   - Run the Traceability Gate: block completion if key mechanism claims cannot be traced back to repository evidence.
   - Run the Export Integrity Gate: block completion if exports introduce consequential facts not grounded in `master-pack.md`, or if critical capabilities lack required export landings.
   - Record pass/fail status in `workflow-state.md`.
```

Also update the `## Output Contract` / `## Guardrails` wording so it explicitly preserves the existing artifact set while calling out depth-aware completion semantics:

```markdown
Each artifact must preserve the Evidence/Inference/Unknown distinction. Unknowns must remain visible rather than being silently filled. Coverage is not complete merely because a capability is mentioned; `critical` capabilities must be depth-qualified before the PRD suite can be marked complete.
```

- [ ] **Step 4: Re-run the template-guidance tests and verify they pass**

Run:

```bash
pytest tests/test_prd_template_guidance.py -q
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add templates/commands/prd.md tests/test_prd_template_guidance.py
git commit -m "feat: harden sp-prd workflow contract for depth-aware extraction"
```

---

### Task 2: Upgrade the Master-Pack Template for Tiered Capability Reconstruction

**Files:**
- Modify: `templates/prd/master-pack-template.md`
- Test: `tests/test_prd_export_templates.py`

**Intent:** Turn `master-pack-template.md` into a truth source that can actually hold critical capability depth instead of only flat inventories.

- [ ] **Step 1: Add failing export-template tests for capability tiers and dossiers**

Update `tests/test_prd_export_templates.py`:

```python
def test_prd_master_pack_template_requires_tiered_capability_fields() -> None:
    content = (PRD_TEMPLATE_DIR / "master-pack-template.md").read_text(encoding="utf-8")

    assert "Core Value Proposition" in content
    assert "| Capability ID | Tier |" in content
    assert "## Critical Capability Dossiers" in content
    assert "Implementation Mechanisms" in content
    assert "Format or Protocol Matrix" in content
    assert "Edge Cases and Failure Paths" in content
    assert "Source Traceability" in content
```

Also edit the existing `EXPECTED_PRD_TEMPLATES["master-pack-template.md"]` list in the same file so it contains these exact fragments in addition to its existing entries:

```python
"Critical Capability Dossiers",
"Coverage and Export Map",
```

- [ ] **Step 2: Run the export-template tests to verify failure**

Run:

```bash
pytest tests/test_prd_export_templates.py -q
```

Expected: FAIL because `master-pack-template.md` does not yet contain the new sections.

- [ ] **Step 3: Refactor `templates/prd/master-pack-template.md` to hold tiered capability truth**

Replace the flat overview/capability structure with this upgraded shape:

```markdown
## Product Frame

- **Evidence/Inference/Unknown**: [Mark the confidence of the product summary.]
- **What exists now**: [Current-state product or service summary.]
- **Who it serves**: [Roles, users, operators, or systems.]
- **Core value proposition**: [Repository-backed statement of the product-defining value.]
- **Project mode**: [ui | service | mixed]

## Capability Inventory

| Capability ID | Capability | Tier | User or System Value | Surfaces | Rules or Data | Depth Status | Evidence/Inference/Unknown | Export Destinations |
|---------------|------------|------|----------------------|----------|---------------|--------------|----------------------------|---------------------|
| [CAP-001] | [CAPABILITY] | [critical] | [VALUE] | [SCREENS_OR_ENTRYPOINTS] | [RULES_OR_ENTITIES] | [surface-covered | depth-qualified] | [Evidence] | [prd.md, ui-spec.md] |

## Critical Capability Dossiers

### [CAP-001] [CAPABILITY]

#### Overview

- Purpose: [WHY_THIS_CAPABILITY_EXISTS]
- Tier: [critical | high]
- Evidence/Inference/Unknown: [CONFIDENCE]

#### Implementation Mechanisms

- [Mechanism name] -> [What it does and where it lives]

#### Format or Protocol Matrix

| Surface | Format / Protocol | Parser / Serializer | Constraints | Sources |
|---------|-------------------|---------------------|-------------|---------|
| [CONFIG_OR_API] | [FORMAT] | [PARSER] | [RULE] | [PATHS] |

#### Edge Cases and Failure Paths

- [Failure or compatibility case] -> [Handling behavior] -> [Sources]

#### Source Traceability

- [Claim] -> [file path or function path]

#### Unknowns and Inference Notes

- Unknown: [UNRESOLVED_GAP]
- Inference: [BOUNDED_INFERENCE]

## Coverage and Export Map

| Master Item | Tier | Depth Status | prd.md | ui-spec.md | service-spec.md | flows-and-ia.md | data-rules-appendix.md | internal-implementation-brief.md |
|-------------|------|--------------|--------|------------|-----------------|-----------------|------------------------|----------------------------------|
| [CAP-001] | [critical] | [depth-qualified] | [yes] | [yes/no] | [yes/no] | [yes/no] | [yes/no] | [yes] |
```

- [ ] **Step 4: Re-run the export-template tests and verify they pass**

Run:

```bash
pytest tests/test_prd_export_templates.py -q
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add templates/prd/master-pack-template.md tests/test_prd_export_templates.py
git commit -m "feat: add tiered capability dossiers to prd master-pack template"
```

---

### Task 3: Upgrade the Reader-Facing PRD and Internal Brief Exports

**Files:**
- Modify: `templates/prd/export-prd-template.md`
- Modify: `templates/prd/export-internal-brief-template.md`
- Test: `tests/test_prd_export_templates.py`

**Intent:** Make the primary exports reflect depth-qualified capabilities without turning them into second truth sources.

- [ ] **Step 1: Add failing tests for depth-aware export sections**

Append to `tests/test_prd_export_templates.py`:

```python
def test_prd_export_template_calls_out_depth_qualified_capabilities() -> None:
    content = (PRD_TEMPLATE_DIR / "export-prd-template.md").read_text(encoding="utf-8")

    assert "Critical Capability Notes" in content
    assert "depth-qualified" in content
    assert "surface-covered" in content


def test_internal_brief_template_maps_critical_capabilities_to_code() -> None:
    content = (PRD_TEMPLATE_DIR / "export-internal-brief-template.md").read_text(encoding="utf-8")

    assert "Critical Capability-to-Code Mapping" in content
    assert "Primary Files or Functions" in content
    assert "Verification Clues" in content
```

- [ ] **Step 2: Run the export-template tests to verify failure**

Run:

```bash
pytest tests/test_prd_export_templates.py -q
```

Expected: FAIL because the export templates do not yet expose those sections.

- [ ] **Step 3: Update `templates/prd/export-prd-template.md` to summarize critical capability depth safely**

Insert these sections after `## Capability Overview` and before `## Key Flows`:

```markdown
## Critical Capability Notes

| Capability | Tier | Depth Status | Why It Matters | Evidence/Inference/Unknown |
|------------|------|--------------|----------------|----------------------------|
| [CAPABILITY] | [critical] | [depth-qualified | depth-gap] | [WHY_THIS_CAPABILITY_IS_CORE] | [Evidence] |

## Confidence and Unknown Handling

- `depth-qualified` means the master pack reconstructs the capability with mechanism-level detail and traceable evidence.
- `surface-covered` means the capability appears in repository surfaces but still lacks enough reconstruction depth to be treated as complete.
```

Keep the document derived from `master-pack.md`; do not add any export-only facts.

- [ ] **Step 4: Update `templates/prd/export-internal-brief-template.md` to point planners back to the right hotspots**

Replace the current capability mapping block with:

```markdown
## Critical Capability-to-Code Mapping

| Capability | Tier | Repository Module or Area | Primary Files or Functions | Evidence/Inference/Unknown |
|------------|------|---------------------------|----------------------------|----------------------------|
| [CAPABILITY] | [critical] | [MODULE] | [PATHS_OR_FUNCTIONS] | [Evidence] |

## Verification Clues

- [Existing test, fixture, command, route, or behavior that verifies a critical capability claim.]
```

Preserve the later `Planning Handoff Notes` section exactly as a downstream note rather than an implementation plan.

- [ ] **Step 5: Re-run the export-template tests and verify they pass**

Run:

```bash
pytest tests/test_prd_export_templates.py -q
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add templates/prd/export-prd-template.md templates/prd/export-internal-brief-template.md tests/test_prd_export_templates.py
git commit -m "feat: make prd exports reflect depth-qualified capabilities"
```

---

### Task 4: Update Passive Guidance and Generated Skill Propagation

**Files:**
- Modify: `templates/passive-skills/project-to-prd/SKILL.md`
- Modify: `tests/test_passive_skill_guidance.py`
- Modify: `tests/test_extension_skills.py`
- Modify: `tests/integrations/test_integration_codex.py`

**Intent:** Ensure the new `sp-prd` semantics survive the skill-generation path instead of living only in the source template.

- [ ] **Step 1: Add failing tests for passive guidance and generated skill propagation**

Add the following assertions:

In `tests/test_passive_skill_guidance.py`:

```python
def test_project_to_prd_mentions_depth_aware_reconstruction() -> None:
    content = _read("templates/passive-skills/project-to-prd/SKILL.md").lower()

    assert "capability triage" in content
    assert "targeted evidence harvest" in content
    assert "critical capabilities" in content
    assert "depth-aware" in content
```

In `tests/test_extension_skills.py`, inside the existing `prd_body` assertions:

```python
assert "capability triage" in prd_lower
assert "targeted evidence harvest" in prd_lower
assert "depth-qualified" in prd_lower
assert "critical depth gate" in prd_lower
```

In `tests/integrations/test_integration_codex.py`, inside the existing `prd_content` assertions:

```python
assert "capability triage" in prd_content
assert "targeted evidence harvest" in prd_content
assert "depth-qualified" in prd_content
assert "critical depth gate" in prd_content
```

- [ ] **Step 2: Run the propagation tests to verify failure**

Run:

```bash
pytest tests/test_passive_skill_guidance.py tests/test_extension_skills.py tests/integrations/test_integration_codex.py -q -k "project_to_prd or sp_prd"
```

Expected: FAIL because the passive skill and generated skill text do not yet mention the new workflow terms.

- [ ] **Step 3: Update `templates/passive-skills/project-to-prd/SKILL.md`**

Add the new workflow semantics under `## Required Behavior` and `## Output Expectations`:

```markdown
- Treat `sp-prd` as a depth-aware current-state extraction workflow, not a flat repo summary pass.
- Require capability triage before claiming the PRD suite is complete.
- Use targeted evidence harvest for `critical` and `high` capabilities.
- Keep `critical` capabilities visible until they are depth-qualified rather than merely surface-covered.
```

Do not change the routing decision itself; this skill is still only about recognizing and routing existing-project PRD work.

- [ ] **Step 4: Re-run the propagation tests and verify they pass**

Run:

```bash
pytest tests/test_passive_skill_guidance.py tests/test_extension_skills.py tests/integrations/test_integration_codex.py -q -k "project_to_prd or sp_prd"
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add templates/passive-skills/project-to-prd/SKILL.md tests/test_passive_skill_guidance.py tests/test_extension_skills.py tests/integrations/test_integration_codex.py
git commit -m "feat: propagate depth-aware sp-prd guidance to passive and generated skills"
```

---

### Task 5: Add Compatible Artifact Validation for Depth-Aware PRD Suites

**Files:**
- Modify: `src/specify_cli/hooks/artifact_validation.py`
- Modify: `tests/test_prd_hook_contract.py`
- Modify: `tests/contract/test_hook_cli_surface.py`

**Intent:** Block PRD suites that still satisfy the old file-exists contract but fail the new structural depth contract.

- [ ] **Step 1: Add failing hook tests for missing depth-aware sections**

Update `tests/test_prd_hook_contract.py` to replace the old "complete artifacts" fixture with a depth-aware one:

```python
def _write_complete_prd_artifacts(run_dir: Path) -> None:
    _write_prd_workflow_state(run_dir)
    (run_dir / "coverage-matrix.md").write_text(
        "\n".join(
            [
                "# Coverage Matrix",
                "",
                "| Capability | Tier | Evidence Status | Depth Status | Export Destinations | Overall Status |",
                "|------------|------|-----------------|--------------|---------------------|----------------|",
                "| Config Management | critical | Evidence | depth-qualified | prd.md | depth-qualified |",
            ]
        ),
        encoding="utf-8",
    )
    master_dir = run_dir / "master"
    master_dir.mkdir()
    (master_dir / "master-pack.md").write_text(
        "\n".join(
            [
                "# Master Pack",
                "",
                "## Capability Inventory",
                "",
                "## Critical Capability Dossiers",
                "",
                "### CAP-001 Config Management",
                "",
                "#### Implementation Mechanisms",
                "",
                "#### Source Traceability",
                "",
                "## Coverage and Export Map",
            ]
        ),
        encoding="utf-8",
    )
    exports_dir = run_dir / "exports"
    exports_dir.mkdir()
    (exports_dir / "prd.md").write_text(
        "\n".join(
            [
                "# PRD",
                "",
                "**Derived From**: `master/master-pack.md`",
                "",
                "## Capability Overview",
                "",
                "## Critical Capability Notes",
                "",
                "## Unknowns and Evidence Confidence",
            ]
        ),
        encoding="utf-8",
    )
    (master_dir / "exports").mkdir()


def test_prd_artifact_validation_blocks_missing_depth_aware_sections(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "prd-runs" / "260503-depth-gap-prd"
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_prd_workflow_state(run_dir)
    (run_dir / "coverage-matrix.md").write_text("# Coverage Matrix\n", encoding="utf-8")
    master_dir = run_dir / "master"
    master_dir.mkdir()
    (master_dir / "master-pack.md").write_text("# Master Pack\n", encoding="utf-8")
    (master_dir / "exports").mkdir()
    exports_dir = run_dir / "exports"
    exports_dir.mkdir()
    (exports_dir / "prd.md").write_text("# PRD\n", encoding="utf-8")

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "prd", "feature_dir": str(run_dir)},
    )

    assert result.status == "blocked"
    assert any("coverage-matrix.md is missing depth-aware columns" in message for message in result.errors)
    assert any("master/master-pack.md is missing required section" in message for message in result.errors)
    assert any("exports/prd.md is missing required section" in message for message in result.errors)
```

Add a matching CLI surface test in `tests/contract/test_hook_cli_surface.py`:

```python
def test_hook_validate_artifacts_blocks_shallow_prd_suite(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "prd-runs" / "260503-demo-prd"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "workflow-state.md").write_text("# Workflow State\n", encoding="utf-8")
    (run_dir / "coverage-matrix.md").write_text("# Coverage Matrix\n", encoding="utf-8")
    master_dir = run_dir / "master"
    master_dir.mkdir()
    (master_dir / "master-pack.md").write_text("# Master Pack\n", encoding="utf-8")
    (master_dir / "exports").mkdir()
    exports_dir = run_dir / "exports"
    exports_dir.mkdir()
    (exports_dir / "prd.md").write_text("# PRD\n", encoding="utf-8")

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "prd", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert any("depth-aware" in message.lower() or "required section" in message.lower() for message in payload["errors"])
```

- [ ] **Step 2: Run the hook tests to verify failure**

Run:

```bash
pytest tests/test_prd_hook_contract.py tests/contract/test_hook_cli_surface.py -q -k "prd"
```

Expected: FAIL because `artifact_validation.py` only checks file existence and directory shape today.

- [ ] **Step 3: Implement structural PRD validation in `artifact_validation.py`**

Add PRD-specific structural checks without introducing new required files:

```python
PRD_MASTER_PACK_REQUIRED_SECTIONS = (
    "## Capability Inventory",
    "## Critical Capability Dossiers",
    "## Coverage and Export Map",
)

PRD_EXPORT_REQUIRED_SECTIONS = (
    "## Capability Overview",
    "## Critical Capability Notes",
    "## Unknowns and Evidence Confidence",
)

PRD_COVERAGE_REQUIRED_TOKENS = (
    "Tier",
    "Depth Status",
    "Overall Status",
)


def _validate_markdown_contains(path: Path, required_items: tuple[str, ...], label: str) -> list[str]:
    content = path.read_text(encoding="utf-8", errors="replace")
    return [f"{label} is missing required section: {item}" for item in required_items if item not in content]


def _validate_prd_artifacts(feature_dir: Path) -> list[str]:
    errors: list[str] = []
    master_exports_dir = feature_dir / "master" / "exports"
    if master_exports_dir.exists() and not master_exports_dir.is_dir():
        errors.append("master/exports must be a directory")

    coverage_path = feature_dir / "coverage-matrix.md"
    coverage_content = coverage_path.read_text(encoding="utf-8", errors="replace")
    missing_coverage = [token for token in PRD_COVERAGE_REQUIRED_TOKENS if token not in coverage_content]
    if missing_coverage:
        joined = ", ".join(missing_coverage)
        errors.append(f"coverage-matrix.md is missing depth-aware columns or fields: {joined}")

    errors.extend(
        _validate_markdown_contains(
            feature_dir / "master" / "master-pack.md",
            PRD_MASTER_PACK_REQUIRED_SECTIONS,
            "master/master-pack.md",
        )
    )
    errors.extend(
        _validate_markdown_contains(
            feature_dir / "exports" / "prd.md",
            PRD_EXPORT_REQUIRED_SECTIONS,
            "exports/prd.md",
        )
    )
    return errors
```

This is intentionally structural. Do not try to build a full semantic diff between `master-pack.md` and `exports/prd.md` in `v2.1`.

- [ ] **Step 4: Re-run the hook tests and verify they pass**

Run:

```bash
pytest tests/test_prd_hook_contract.py tests/contract/test_hook_cli_surface.py -q -k "prd"
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/specify_cli/hooks/artifact_validation.py tests/test_prd_hook_contract.py tests/contract/test_hook_cli_surface.py
git commit -m "feat: block shallow sp-prd artifacts with depth-aware validation"
```

---

### Task 6: Run the Focused Regression Suite and Freeze `v2.1`

**Files:**
- Verify only: `tests/test_prd_template_guidance.py`
- Verify only: `tests/test_prd_export_templates.py`
- Verify only: `tests/test_passive_skill_guidance.py`
- Verify only: `tests/test_prd_hook_contract.py`
- Verify only: `tests/contract/test_hook_cli_surface.py`
- Verify only: `tests/test_extension_skills.py`
- Verify only: `tests/integrations/test_integration_codex.py`
- Verify only: `tests/test_prd_cli_helpers.py`

**Intent:** Prove the template, hook, and generated-skill surfaces all agree on the new `sp-prd v2` contract.

- [ ] **Step 1: Run the focused regression suite**

Run:

```bash
pytest \
  tests/test_prd_template_guidance.py \
  tests/test_prd_export_templates.py \
  tests/test_passive_skill_guidance.py \
  tests/test_prd_hook_contract.py \
  tests/contract/test_hook_cli_surface.py \
  tests/test_extension_skills.py \
  tests/integrations/test_integration_codex.py \
  tests/test_prd_cli_helpers.py \
  -q
```

Expected: PASS

- [ ] **Step 2: Spot-check generated Codex `sp-prd` skill content after `init`**

Run:

```bash
pytest tests/integrations/test_integration_codex.py -q -k "sp_prd or generated_shared_workflow_skills"
```

Expected: PASS with generated `sp-prd` skill containing `capability triage`, `targeted evidence harvest`, `depth-qualified`, and `critical depth gate`.

- [ ] **Step 3: Review the diff for unintended scope creep**

Run:

```bash
git diff -- templates/commands/prd.md templates/prd/master-pack-template.md templates/prd/export-prd-template.md templates/prd/export-internal-brief-template.md templates/passive-skills/project-to-prd/SKILL.md src/specify_cli/hooks/artifact_validation.py tests/test_prd_template_guidance.py tests/test_prd_export_templates.py tests/test_passive_skill_guidance.py tests/test_prd_hook_contract.py tests/contract/test_hook_cli_surface.py tests/test_extension_skills.py tests/integrations/test_integration_codex.py
```

Expected: only the files listed in this plan changed; no runtime, packaging, or unrelated workflow surfaces appear in the diff.

- [ ] **Step 4: Commit the final verification-only sweep if any follow-up adjustments were needed**

```bash
git add templates/commands/prd.md templates/prd/master-pack-template.md templates/prd/export-prd-template.md templates/prd/export-internal-brief-template.md templates/passive-skills/project-to-prd/SKILL.md src/specify_cli/hooks/artifact_validation.py tests/test_prd_template_guidance.py tests/test_prd_export_templates.py tests/test_passive_skill_guidance.py tests/test_prd_hook_contract.py tests/contract/test_hook_cli_surface.py tests/test_extension_skills.py tests/integrations/test_integration_codex.py
git commit -m "test: verify sp-prd v2 depth-aware extraction contract"
```

If Step 1 and Step 3 pass with no extra edits, skip this commit and keep the earlier feature commits.

---

## Spec-to-Plan Coverage Check

This plan covers every approved `v2.1` requirement from `docs/superpowers/specs/2026-05-03-sp-prd-v2-depth-aware-extraction-design.md`:

- capability triage: Task 1
- targeted evidence harvest: Task 1
- depth-aware coverage matrix semantics: Task 1 and Task 5
- critical capability dossiers: Task 2
- export alignment for depth-qualified capabilities: Task 3
- passive/generated skill propagation: Task 4
- compatible structural quality gates: Task 5
- no new hard-required artifact files in `v2.1`: Tasks 1, 2, and 5 preserve the existing artifact set

No `v2.2` automation work is included.

## Placeholder Scan

Checked for forbidden placeholders:

- no `TBD`
- no `TODO`
- no "implement later"
- no unnamed "add validation" steps
- every code-changing task includes concrete snippets and exact commands

## Type and Naming Consistency

This plan uses one consistent vocabulary across files and tests:

- `capability triage`
- `targeted evidence harvest`
- `critical`, `high`, `standard`, `auxiliary`
- `surface-covered`, `partially-reconstructed`, `depth-gap`, `blocked-by-unknowns`, `depth-qualified`
- `Critical Capability Dossiers`
- `Coverage and Export Map`

Do not rename those phrases during implementation unless every template and test in this plan is updated together.
