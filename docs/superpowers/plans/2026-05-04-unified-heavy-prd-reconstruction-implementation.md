# Unified Heavy PRD Reconstruction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade `sp-prd-scan -> sp-prd-build` into a unified heavy reconstruction workflow with mandatory subagent orchestration, expanded reconstruction artifacts, stricter validation, and a larger export archive that supports near-original product recreation from code-only evidence.

**Architecture:** Implement the heavy PRD standard in vertical slices. Start by locking the contract into command templates and tests, then expand the PRD run-state helpers so new scan and build artifacts exist in the workspace contract. Once the artifact surface is real, extend export templates and packaging, then harden `artifact_validation.py` so shallow or incomplete scan packages are blocked. Finish by propagating the new PRD semantics into generated integration guidance, routing skills, handbook/docs, and the full test matrix. Keep the two-step `prd-scan -> prd-build` model intact throughout.

**Tech Stack:** Python 3.13, Typer CLI, pytest, Markdown command templates, Bash/PowerShell helper scripts, workflow validation hooks, generated integration surfaces, Spec Kit template packaging.

---

## Context

Read before editing:

- [2026-05-04-unified-heavy-prd-reconstruction-design.md](/F:/github/spec-kit-plus/docs/superpowers/specs/2026-05-04-unified-heavy-prd-reconstruction-design.md)
- [prd-scan.md](/F:/github/spec-kit-plus/templates/commands/prd-scan.md)
- [prd-build.md](/F:/github/spec-kit-plus/templates/commands/prd-build.md)
- [prd.md](/F:/github/spec-kit-plus/templates/commands/prd.md)
- [project-to-prd/SKILL.md](/F:/github/spec-kit-plus/templates/passive-skills/project-to-prd/SKILL.md)
- [spec-kit-workflow-routing/SKILL.md](/F:/github/spec-kit-plus/templates/passive-skills/spec-kit-workflow-routing/SKILL.md)
- [prd-state.sh](/F:/github/spec-kit-plus/scripts/bash/prd-state.sh)
- [prd-state.ps1](/F:/github/spec-kit-plus/scripts/powershell/prd-state.ps1)
- [artifact_validation.py](/F:/github/spec-kit-plus/src/specify_cli/hooks/artifact_validation.py)
- [__init__.py](/F:/github/spec-kit-plus/src/specify_cli/__init__.py)
- [master-pack-template.md](/F:/github/spec-kit-plus/templates/prd/master-pack-template.md)
- [export-prd-template.md](/F:/github/spec-kit-plus/templates/prd/export-prd-template.md)
- [test_prd_scan_build_template_guidance.py](/F:/github/spec-kit-plus/tests/test_prd_scan_build_template_guidance.py)
- [test_prd_export_templates.py](/F:/github/spec-kit-plus/tests/test_prd_export_templates.py)
- [test_prd_cli_helpers.py](/F:/github/spec-kit-plus/tests/test_prd_cli_helpers.py)
- [test_prd_hook_contract.py](/F:/github/spec-kit-plus/tests/test_prd_hook_contract.py)
- [test_hook_cli_surface.py](/F:/github/spec-kit-plus/tests/contract/test_hook_cli_surface.py)

Keep these constraints in mind while implementing:

- The workflow must remain exactly two steps: `sp-prd-scan -> sp-prd-build`.
- The new standard is intentionally breaking: old PRD workspaces are not guaranteed to satisfy the new completion contract.
- `sp-prd-build` must never become a second repository scan.
- The heavy standard is uniform across product types; do not add UI-only/service-only gating branches to the workflow core.
- Multi-subagent orchestration is part of the workflow contract, but the first implementation pass can encode it in prompt/template/runtime surfaces without introducing a large new Python dispatch engine for PRD.
- Existing untracked or unrelated files in the worktree must not be reverted.

## File Structure

Create:

- [export-config-contracts-template.md](/F:/github/spec-kit-plus/templates/prd/export-config-contracts-template.md) - final export template for configuration contracts, defaults, precedence, and behavior switches.
- [export-protocol-contracts-template.md](/F:/github/spec-kit-plus/templates/prd/export-protocol-contracts-template.md) - final export template for protocol mappings, compatibility, and boundary contracts.
- [export-state-machines-template.md](/F:/github/spec-kit-plus/templates/prd/export-state-machines-template.md) - final export template for state sets, triggers, guards, failures, and recovery.
- [export-error-semantics-template.md](/F:/github/spec-kit-plus/templates/prd/export-error-semantics-template.md) - final export template for error triggers, exposure semantics, and recovery paths.
- [export-verification-surface-template.md](/F:/github/spec-kit-plus/templates/prd/export-verification-surface-template.md) - final export template for tests, minimum verification commands, and parity checkpoints.
- [export-reconstruction-risks-template.md](/F:/github/spec-kit-plus/templates/prd/export-reconstruction-risks-template.md) - final export template for residual unknowns, fidelity risks, and blocked critical gaps.

Modify:

- [prd-scan.md](/F:/github/spec-kit-plus/templates/commands/prd-scan.md) - encode the heavy scan contract, mandatory subagents, critical item families, `L1-L4` evidence levels, new machine-readable artifacts, and stricter gates.
- [prd-build.md](/F:/github/spec-kit-plus/templates/commands/prd-build.md) - encode heavy build semantics, packet evidence intake, new exports, and reconstruction refusal gates.
- [prd.md](/F:/github/spec-kit-plus/templates/commands/prd.md) - keep it compatibility-only while routing toward the heavier two-step standard.
- [project-to-prd/SKILL.md](/F:/github/spec-kit-plus/templates/passive-skills/project-to-prd/SKILL.md) - describe the heavy standard and its output set.
- [spec-kit-workflow-routing/SKILL.md](/F:/github/spec-kit-plus/templates/passive-skills/spec-kit-workflow-routing/SKILL.md) - keep PRD routing aligned with the new heavy semantics.
- [prd-state.sh](/F:/github/spec-kit-plus/scripts/bash/prd-state.sh) - initialize and report the expanded scan/build artifact surface.
- [prd-state.ps1](/F:/github/spec-kit-plus/scripts/powershell/prd-state.ps1) - PowerShell parity for the expanded PRD artifact surface.
- [state_validation.py](/F:/github/spec-kit-plus/src/specify_cli/hooks/state_validation.py) - keep `analysis-only` validation aligned with any workflow-state wording changes.
- [artifact_validation.py](/F:/github/spec-kit-plus/src/specify_cli/hooks/artifact_validation.py) - enforce the new required files, JSON shapes, `L4` critical readiness, worker-result requirements, and expanded build exports.
- [__init__.py](/F:/github/spec-kit-plus/src/specify_cli/__init__.py) - update command help/guidance text and any surfaced artifact descriptions for the heavy standard.
- [master-pack-template.md](/F:/github/spec-kit-plus/templates/prd/master-pack-template.md) - expand the single truth source to include config, protocol, state, error, verification, and export landing dossiers.
- [export-prd-template.md](/F:/github/spec-kit-plus/templates/prd/export-prd-template.md) - reference the heavy archive and preserve new confidence/reconstruction semantics.
- [export-service-spec-template.md](/F:/github/spec-kit-plus/templates/prd/export-service-spec-template.md) - ensure service-oriented exports still align with the heavy archive vocabulary.
- [export-ui-spec-template.md](/F:/github/spec-kit-plus/templates/prd/export-ui-spec-template.md) - ensure UI-oriented exports still align with the heavy archive vocabulary.
- [export-flows-ia-template.md](/F:/github/spec-kit-plus/templates/prd/export-flows-ia-template.md) - preserve key-flow routing and navigation semantics under the heavy standard.
- [export-data-rules-template.md](/F:/github/spec-kit-plus/templates/prd/export-data-rules-template.md) - align data/rules export language with reconstruction-ready field preservation.
- [export-internal-brief-template.md](/F:/github/spec-kit-plus/templates/prd/export-internal-brief-template.md) - expand mapping and verification notes for the heavy archive.
- [README.md](/F:/github/spec-kit-plus/README.md) - update user/operator guidance for the heavy PRD standard.
- [PROJECT-HANDBOOK.md](/F:/github/spec-kit-plus/PROJECT-HANDBOOK.md) - update repo-local source-of-truth guidance for PRD reconstruction.
- Integration rendering surfaces that reference `prd-scan` or `prd-build`, especially [base.py](/F:/github/spec-kit-plus/src/specify_cli/integrations/base.py) and [codex/__init__.py](/F:/github/spec-kit-plus/src/specify_cli/integrations/codex/__init__.py), when generated content must mention mandatory PRD subagent orchestration.
- PRD-related tests, packaging tests, and integration wording tests that assert the old artifact set or old text.

## Naming Rules

Use these new scan artifacts consistently:

- `entrypoint-ledger.json`
- `config-contracts.json`
- `protocol-contracts.json`
- `state-machines.json`
- `error-semantics.json`
- `verification-surfaces.json`

Use these new build exports consistently:

- `exports/config-contracts.md`
- `exports/protocol-contracts.md`
- `exports/state-machines.md`
- `exports/error-semantics.md`
- `exports/verification-surface.md`
- `exports/reconstruction-risks.md`

Use these evidence levels consistently:

- `L1 Exists`
- `L2 Surface`
- `L3 Behavioral`
- `L4 Reconstruction-Ready`

Do not introduce alternate spellings like `reconstruction ready`, `L4 Ready`, or `behavioral-ready`. Keep the wording stable for tests and validation.

---

### Task 1: Lock the heavy scan/build contract into template tests first

**Files:**
- Modify: [test_prd_scan_build_template_guidance.py](/F:/github/spec-kit-plus/tests/test_prd_scan_build_template_guidance.py)
- Modify: [test_prd_template_guidance.py](/F:/github/spec-kit-plus/tests/test_prd_template_guidance.py)

- [ ] **Step 1: Extend the scan/build guidance tests with new contract expectations**

Add assertions like these to `tests/test_prd_scan_build_template_guidance.py`:

```python
def test_prd_scan_template_defines_heavy_reconstruction_contract() -> None:
    content = _content("templates/commands/prd-scan.md")

    assert "execution_model: subagent-mandatory" in content
    assert "PrdScanPacket" in content
    assert "L1 Exists" in content
    assert "L2 Surface" in content
    assert "L3 Behavioral" in content
    assert "L4 Reconstruction-Ready" in content
    assert "Main Capability Chains" in content
    assert "External Entrypoints and Command Surfaces" in content
    assert "State Machines and Flow Control" in content
    assert "Data and Persistence Contracts" in content
    assert "Configuration and Behavior Switches" in content
    assert "Protocol and Boundary Contracts" in content
    assert "Error Semantics and Recovery Behavior" in content
    assert "Verification and Regression Entrypoints" in content
    assert "entrypoint-ledger.json" in content
    assert "config-contracts.json" in content
    assert "protocol-contracts.json" in content
    assert "state-machines.json" in content
    assert "error-semantics.json" in content
    assert "verification-surfaces.json" in content


def test_prd_build_template_defines_heavy_reconstruction_exports_and_refusal() -> None:
    content = _content("templates/commands/prd-build.md")

    assert "packet evidence intake" in content.lower()
    assert "mandatory subagents" in content.lower() or "execution_model: subagent-mandatory" in content
    assert "exports/config-contracts.md" in content
    assert "exports/protocol-contracts.md" in content
    assert "exports/state-machines.md" in content
    assert "exports/error-semantics.md" in content
    assert "exports/verification-surface.md" in content
    assert "exports/reconstruction-risks.md" in content
    assert "Critical Unknown Refusal Gate" in content
    assert "Traceability Gate" in content
    assert "Reconstruction Readiness Gate" in content
```

- [ ] **Step 2: Tighten the compatibility-entrypoint expectations**

Add assertions like these to `tests/test_prd_template_guidance.py`:

```python
def test_prd_template_routes_to_heavy_scan_then_build() -> None:
    content = _content()

    assert "compatibility" in content.lower()
    assert "sp-prd-scan" in content
    assert "sp-prd-build" in content
    assert "reconstruction" in content.lower()
    assert "L4 Reconstruction-Ready" in content
```

- [ ] **Step 3: Run the template tests to verify RED**

Run:

```powershell
pytest tests/test_prd_scan_build_template_guidance.py tests/test_prd_template_guidance.py -q
```

Expected: FAIL because the current templates do not yet describe the heavy standard.

- [ ] **Step 4: Commit the RED tests**

Run:

```bash
git add tests/test_prd_scan_build_template_guidance.py tests/test_prd_template_guidance.py
git commit -m "test: lock heavy prd template contract"
```

### Task 2: Implement the heavy command-template contract

**Files:**
- Modify: [prd-scan.md](/F:/github/spec-kit-plus/templates/commands/prd-scan.md)
- Modify: [prd-build.md](/F:/github/spec-kit-plus/templates/commands/prd-build.md)
- Modify: [prd.md](/F:/github/spec-kit-plus/templates/commands/prd.md)

- [ ] **Step 1: Expand `prd-scan.md` to define the heavy scan contract**

Update `templates/commands/prd-scan.md` so it explicitly includes:

```markdown
## Mandatory Subagent Execution

Use `execution_model: subagent-mandatory`.
Use `dispatch_shape: one-subagent | parallel-subagents`.
Use `execution_surface: native-subagents`.

## Unified Critical Item Families

1. Main Capability Chains
2. External Entrypoints and Command Surfaces
3. State Machines and Flow Control
4. Data and Persistence Contracts
5. Configuration and Behavior Switches
6. Protocol and Boundary Contracts
7. Error Semantics and Recovery Behavior
8. Verification and Regression Entrypoints

## Evidence Depth Model

- `L1 Exists`
- `L2 Surface`
- `L3 Behavioral`
- `L4 Reconstruction-Ready`
```

Also extend the output contract list to include:

```markdown
- `.specify/prd-runs/<run-id>/entrypoint-ledger.json`
- `.specify/prd-runs/<run-id>/config-contracts.json`
- `.specify/prd-runs/<run-id>/protocol-contracts.json`
- `.specify/prd-runs/<run-id>/state-machines.json`
- `.specify/prd-runs/<run-id>/error-semantics.json`
- `.specify/prd-runs/<run-id>/verification-surfaces.json`
```

- [ ] **Step 2: Expand `prd-build.md` to define heavy compilation and refusal**

Update `templates/commands/prd-build.md` so the output contract includes:

```markdown
- `.specify/prd-runs/<run-id>/exports/config-contracts.md`
- `.specify/prd-runs/<run-id>/exports/protocol-contracts.md`
- `.specify/prd-runs/<run-id>/exports/state-machines.md`
- `.specify/prd-runs/<run-id>/exports/error-semantics.md`
- `.specify/prd-runs/<run-id>/exports/verification-surface.md`
- `.specify/prd-runs/<run-id>/exports/reconstruction-risks.md`
```

Add build quality gate headings:

```markdown
- Critical Unknown Refusal Gate
- Traceability Gate
- Reconstruction Readiness Gate
```

Add wording that `sp-prd-build` compiles a packet evidence intake before export synthesis and must not reread the repository.

- [ ] **Step 3: Keep `prd.md` compatibility-only while routing to the heavy lane**

Add or adjust text in `templates/commands/prd.md` so it says:

```markdown
`sp-prd` is a deprecated compatibility entrypoint.
Use `sp-prd-scan -> sp-prd-build` for the unified heavy reconstruction workflow.
Critical reconstruction claims must meet `L4 Reconstruction-Ready`.
```

- [ ] **Step 4: Run the template tests to verify GREEN**

Run:

```powershell
pytest tests/test_prd_scan_build_template_guidance.py tests/test_prd_template_guidance.py -q
```

Expected: PASS

- [ ] **Step 5: Commit the command-template contract changes**

Run:

```bash
git add templates/commands/prd-scan.md templates/commands/prd-build.md templates/commands/prd.md tests/test_prd_scan_build_template_guidance.py tests/test_prd_template_guidance.py
git commit -m "feat: define heavy prd scan build workflow contract"
```

### Task 3: Update routing skills and public command guidance

**Files:**
- Modify: [project-to-prd/SKILL.md](/F:/github/spec-kit-plus/templates/passive-skills/project-to-prd/SKILL.md)
- Modify: [spec-kit-workflow-routing/SKILL.md](/F:/github/spec-kit-plus/templates/passive-skills/spec-kit-workflow-routing/SKILL.md)
- Modify: [__init__.py](/F:/github/spec-kit-plus/src/specify_cli/__init__.py)
- Modify: PRD-related routing and help tests

- [ ] **Step 1: Add RED assertions for heavy PRD routing language**

Extend `tests/test_passive_skill_guidance.py` and PRD CLI help tests with expectations like:

```python
assert "heavy reconstruction" in content.lower()
assert "L4 Reconstruction-Ready" in content
assert "subagent-mandatory" in content
assert "config-contracts.json" in content
```

- [ ] **Step 2: Update passive skill and CLI help text**

Add language to the skill files and `src/specify_cli/__init__.py` describing:

- the heavy reconstruction standard
- the larger output surface
- the fact that `prd-build` is build-only, not a second scan
- the new refusal semantics for missing critical evidence

- [ ] **Step 3: Run the routing/help tests**

Run:

```powershell
pytest tests/test_passive_skill_guidance.py tests/contract/test_hook_cli_surface.py -q
```

Expected: PASS after the wording is updated. If unrelated failures appear in `test_hook_cli_surface.py`, rerun the single failing test node until the new wording assertions pass.

- [ ] **Step 4: Commit the routing/help changes**

Run:

```bash
git add templates/passive-skills/project-to-prd/SKILL.md templates/passive-skills/spec-kit-workflow-routing/SKILL.md src/specify_cli/__init__.py tests/test_passive_skill_guidance.py tests/contract/test_hook_cli_surface.py
git commit -m "feat: align routing guidance with heavy prd standard"
```

### Task 4: Add RED helper tests for the expanded PRD artifact surface

**Files:**
- Modify: [test_prd_cli_helpers.py](/F:/github/spec-kit-plus/tests/test_prd_cli_helpers.py)

- [ ] **Step 1: Expand helper expectations for new scan files**

Update `tests/test_prd_cli_helpers.py` so scan init/status expects these new surfaces:

```python
assert payload["surfaces"]["entrypoint_ledger_json"] is True
assert payload["surfaces"]["config_contracts_json"] is True
assert payload["surfaces"]["protocol_contracts_json"] is True
assert payload["surfaces"]["state_machines_json"] is True
assert payload["surfaces"]["error_semantics_json"] is True
assert payload["surfaces"]["verification_surfaces_json"] is True
```

Add them to the expected payload dictionaries as well.

- [ ] **Step 2: Expand build expectations for new export files**

Update the build-status expectations in the same file so they also require:

```python
assert payload["surfaces"]["config_contracts"] is True
assert payload["surfaces"]["protocol_contracts"] is True
assert payload["surfaces"]["state_machines"] is True
assert payload["surfaces"]["error_semantics"] is True
assert payload["surfaces"]["verification_surface"] is True
assert payload["surfaces"]["reconstruction_risks"] is True
```

- [ ] **Step 3: Run helper tests to verify RED**

Run:

```powershell
pytest tests/test_prd_cli_helpers.py -q
```

Expected: FAIL because the helper scripts do not yet initialize or report the new artifacts.

- [ ] **Step 4: Commit the RED helper expectations**

Run:

```bash
git add tests/test_prd_cli_helpers.py
git commit -m "test: require heavy prd helper artifact surfaces"
```

### Task 5: Implement the expanded PRD helper/state surface

**Files:**
- Modify: [prd-state.sh](/F:/github/spec-kit-plus/scripts/bash/prd-state.sh)
- Modify: [prd-state.ps1](/F:/github/spec-kit-plus/scripts/powershell/prd-state.ps1)
- Modify: [state_validation.py](/F:/github/spec-kit-plus/src/specify_cli/hooks/state_validation.py)

- [ ] **Step 1: Extend the helper surface maps**

Update both helper scripts so `EXPECTED_SURFACES` includes keys like:

```python
"entrypoint_ledger_json": "entrypoint-ledger.json",
"config_contracts_json": "config-contracts.json",
"protocol_contracts_json": "protocol-contracts.json",
"state_machines_json": "state-machines.json",
"error_semantics_json": "error-semantics.json",
"verification_surfaces_json": "verification-surfaces.json",
"config_contracts": "exports/config-contracts.md",
"protocol_contracts": "exports/protocol-contracts.md",
"state_machines": "exports/state-machines.md",
"error_semantics": "exports/error-semantics.md",
"verification_surface": "exports/verification-surface.md",
"reconstruction_risks": "exports/reconstruction-risks.md",
```

- [ ] **Step 2: Initialize the new scan JSON files**

In `init_scan_artifacts`, add:

```python
write_file_if_missing(
    run_dir / "entrypoint-ledger.json",
    json.dumps({"entrypoints": []}, indent=2) + "\n",
)
write_file_if_missing(
    run_dir / "config-contracts.json",
    json.dumps({"configs": []}, indent=2) + "\n",
)
write_file_if_missing(
    run_dir / "protocol-contracts.json",
    json.dumps({"protocols": []}, indent=2) + "\n",
)
write_file_if_missing(
    run_dir / "state-machines.json",
    json.dumps({"machines": []}, indent=2) + "\n",
)
write_file_if_missing(
    run_dir / "error-semantics.json",
    json.dumps({"errors": []}, indent=2) + "\n",
)
write_file_if_missing(
    run_dir / "verification-surfaces.json",
    json.dumps({"surfaces": []}, indent=2) + "\n",
)
```

Mirror the same behavior in PowerShell.

- [ ] **Step 3: Expand build completion keys**

Extend `BUILD_SURFACE_KEYS` in both helper scripts so completion requires the six new exports in addition to the existing ones.

- [ ] **Step 4: Keep workflow-state authoring aligned**

Update the generated `workflow-state.md` content so:

- `Allowed Artifact Writes` includes the new JSON artifacts for scan
- `Authoritative Files` mentions the new contracts where appropriate
- `Next Command` stays `/sp.prd-build`

`state_validation.py` should remain `analysis-only`, but adjust string-sensitive expectations if needed so validation still accepts the updated workflow state.

- [ ] **Step 5: Run helper and state validation tests**

Run:

```powershell
pytest tests/test_prd_cli_helpers.py tests/test_prd_hook_contract.py -q
```

Expected: PASS

- [ ] **Step 6: Commit the helper/state changes**

Run:

```bash
git add scripts/bash/prd-state.sh scripts/powershell/prd-state.ps1 src/specify_cli/hooks/state_validation.py tests/test_prd_cli_helpers.py tests/test_prd_hook_contract.py
git commit -m "feat: expand prd helper surfaces for heavy reconstruction"
```

### Task 6: Add RED export-template tests for the new archive outputs

**Files:**
- Modify: [test_prd_export_templates.py](/F:/github/spec-kit-plus/tests/test_prd_export_templates.py)

- [ ] **Step 1: Extend the expected template registry**

Update `EXPECTED_PRD_TEMPLATES` to include:

```python
"export-config-contracts-template.md": [
    "# Configuration Contracts",
    "Config Surface",
    "Default Value",
    "Precedence",
],
"export-protocol-contracts-template.md": [
    "# Protocol Contracts",
    "Boundary",
    "Field Mapping",
    "Compatibility",
],
"export-state-machines-template.md": [
    "# State Machines",
    "State Set",
    "Transition Trigger",
    "Recovery",
],
"export-error-semantics-template.md": [
    "# Error Semantics",
    "Trigger",
    "Exposure",
    "Recovery Behavior",
],
"export-verification-surface-template.md": [
    "# Verification Surface",
    "Minimum Verification Command",
    "Locked Behavior",
    "Parity Checkpoint",
],
"export-reconstruction-risks-template.md": [
    "# Reconstruction Risks",
    "Critical Gap",
    "Unknown",
    "Fidelity Risk",
],
```

- [ ] **Step 2: Add master-pack expectations for the new dossiers**

Add assertions like:

```python
assert "Config Dossiers" in content
assert "Protocol Dossiers" in content
assert "State Machine Dossiers" in content
assert "Error Semantic Dossiers" in content
assert "Verification Dossiers" in content
assert "Export Landing Map" in content
```

- [ ] **Step 3: Run the export template tests to verify RED**

Run:

```powershell
pytest tests/test_prd_export_templates.py -q
```

Expected: FAIL because the new template files do not exist yet and the master pack has not been expanded.

- [ ] **Step 4: Commit the RED export-template expectations**

Run:

```bash
git add tests/test_prd_export_templates.py
git commit -m "test: require heavy prd export archive templates"
```

### Task 7: Implement the heavy PRD export templates

**Files:**
- Modify: [master-pack-template.md](/F:/github/spec-kit-plus/templates/prd/master-pack-template.md)
- Modify: [export-prd-template.md](/F:/github/spec-kit-plus/templates/prd/export-prd-template.md)
- Modify: [export-service-spec-template.md](/F:/github/spec-kit-plus/templates/prd/export-service-spec-template.md)
- Modify: [export-ui-spec-template.md](/F:/github/spec-kit-plus/templates/prd/export-ui-spec-template.md)
- Modify: [export-flows-ia-template.md](/F:/github/spec-kit-plus/templates/prd/export-flows-ia-template.md)
- Modify: [export-data-rules-template.md](/F:/github/spec-kit-plus/templates/prd/export-data-rules-template.md)
- Modify: [export-internal-brief-template.md](/F:/github/spec-kit-plus/templates/prd/export-internal-brief-template.md)
- Create: [export-config-contracts-template.md](/F:/github/spec-kit-plus/templates/prd/export-config-contracts-template.md)
- Create: [export-protocol-contracts-template.md](/F:/github/spec-kit-plus/templates/prd/export-protocol-contracts-template.md)
- Create: [export-state-machines-template.md](/F:/github/spec-kit-plus/templates/prd/export-state-machines-template.md)
- Create: [export-error-semantics-template.md](/F:/github/spec-kit-plus/templates/prd/export-error-semantics-template.md)
- Create: [export-verification-surface-template.md](/F:/github/spec-kit-plus/templates/prd/export-verification-surface-template.md)
- Create: [export-reconstruction-risks-template.md](/F:/github/spec-kit-plus/templates/prd/export-reconstruction-risks-template.md)

- [ ] **Step 1: Expand the master pack truth source**

Add sections like these to `templates/prd/master-pack-template.md`:

```markdown
## Config Dossiers

| Config Surface | Path or Key | Default Value | Precedence | Runtime Effect | Evidence/Inference/Unknown |
|----------------|-------------|---------------|------------|----------------|----------------------------|
| [CONFIG] | [PATH_OR_KEY] | [DEFAULT] | [PRECEDENCE] | [EFFECT] | [Evidence] |

## Protocol Dossiers

| Boundary | Producer | Consumer | Field Mapping | Compatibility Notes | Evidence/Inference/Unknown |
|----------|----------|----------|---------------|---------------------|----------------------------|
| [BOUNDARY] | [PRODUCER] | [CONSUMER] | [MAPPING] | [NOTES] | [Evidence] |
```

- [ ] **Step 2: Create the six new export templates**

Create each new template file with `[PROJECT]`, `[RUN_ID]`, and `Evidence/Inference/Unknown` markers, plus the required headings from the tests. For example, `templates/prd/export-config-contracts-template.md` should start like:

```markdown
# Configuration Contracts: [PROJECT]

**Run ID**: [RUN_ID]
**Derived From**: `master/master-pack.md`
**Status**: Draft

This export preserves configuration keys, defaults, precedence, and runtime behavior from the reconstruction package.

## Config Surface Inventory

| Config Surface | Path or Key | Default Value | Precedence | Runtime Effect | Evidence/Inference/Unknown |
|----------------|-------------|---------------|------------|----------------|----------------------------|
| [CONFIG] | [PATH_OR_KEY] | [DEFAULT] | [PRECEDENCE] | [EFFECT] | [Evidence] |
```

- [ ] **Step 3: Adjust existing export templates for archive semantics**

Update the existing export templates so they reference the heavy archive, not just a light PRD set. Add wording such as:

```markdown
This export is one part of the reconstruction archive and must preserve critical fields and confidence semantics from `master/master-pack.md`.
```

- [ ] **Step 4: Run export template and packaging tests**

Run:

```powershell
pytest tests/test_prd_export_templates.py tests/test_packaging_assets.py -q
```

Expected: PASS

- [ ] **Step 5: Commit the export-template changes**

Run:

```bash
git add templates/prd tests/test_prd_export_templates.py tests/test_packaging_assets.py
git commit -m "feat: expand prd export archive templates"
```

### Task 8: Add RED validation tests for the new heavy artifacts and gates

**Files:**
- Modify: [test_prd_hook_contract.py](/F:/github/spec-kit-plus/tests/test_prd_hook_contract.py)
- Modify: [test_hook_cli_surface.py](/F:/github/spec-kit-plus/tests/contract/test_hook_cli_surface.py)

- [ ] **Step 1: Add scan validation expectations for the new JSON artifacts**

Add a blocking test like:

```python
def test_prd_artifact_validation_blocks_missing_heavy_scan_contract_artifacts(tmp_path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "prd-runs" / "260504-heavy-missing"
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_complete_prd_artifacts(run_dir)

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "prd-scan", "feature_dir": str(run_dir)},
    )

    assert result.status == "blocked"
    assert any("entrypoint-ledger.json" in message for message in result.errors)
    assert any("config-contracts.json" in message for message in result.errors)
    assert any("protocol-contracts.json" in message for message in result.errors)
```

- [ ] **Step 2: Add build validation expectations for new exports and worker-result structure**

Add tests asserting:

```python
assert any("exports/config-contracts.md" in message for message in payload["errors"])
assert any("exports/protocol-contracts.md" in message for message in payload["errors"])
assert any("exports/state-machines.md" in message for message in payload["errors"])
assert any("exports/error-semantics.md" in message for message in payload["errors"])
assert any("exports/verification-surface.md" in message for message in payload["errors"])
assert any("exports/reconstruction-risks.md" in message for message in payload["errors"])
```

and a separate case where:

```python
(run_dir / "worker-results" / "lane-a.json").write_text("{\"status\": \"ok\"}\n", encoding="utf-8")
```

is rejected because `paths_read` and `unknowns` are missing.

- [ ] **Step 3: Run the validation tests to verify RED**

Run:

```powershell
pytest tests/test_prd_hook_contract.py tests/contract/test_hook_cli_surface.py -q
```

Expected: FAIL because the validator does not yet enforce the new artifacts or worker-result structure.

- [ ] **Step 4: Commit the RED validation expectations**

Run:

```bash
git add tests/test_prd_hook_contract.py tests/contract/test_hook_cli_surface.py
git commit -m "test: require heavy prd validation gates"
```

### Task 9: Implement the heavy PRD artifact validation rules

**Files:**
- Modify: [artifact_validation.py](/F:/github/spec-kit-plus/src/specify_cli/hooks/artifact_validation.py)

- [ ] **Step 1: Extend required file and directory tables**

Update the PRD-related constants so scan requires:

```python
"entrypoint-ledger.json",
"config-contracts.json",
"protocol-contracts.json",
"state-machines.json",
"error-semantics.json",
"verification-surfaces.json",
```

and build requires:

```python
"exports/config-contracts.md",
"exports/protocol-contracts.md",
"exports/state-machines.md",
"exports/error-semantics.md",
"exports/verification-surface.md",
"exports/reconstruction-risks.md",
```

- [ ] **Step 2: Validate the new JSON shapes**

Add checks similar to the existing ledger validations. For example:

```python
entrypoint_payload, entrypoint_errors = _read_json_artifact(feature_dir / "entrypoint-ledger.json", "entrypoint-ledger.json")
if entrypoint_payload is not None and not isinstance(entrypoint_payload, dict):
    errors.append("entrypoint-ledger.json must contain a top-level JSON object")
elif isinstance(entrypoint_payload, dict) and not isinstance(entrypoint_payload.get("entrypoints"), list):
    errors.append("entrypoint-ledger.json must define a top-level entrypoints array")
```

Repeat for:

- `config-contracts.json` -> `configs`
- `protocol-contracts.json` -> `protocols`
- `state-machines.json` -> `machines`
- `error-semantics.json` -> `errors`
- `verification-surfaces.json` -> `surfaces`

- [ ] **Step 3: Enforce worker-result structure for PRD build readiness**

Add helper logic that inspects JSON files under `worker-results` and blocks when a result file lacks:

```python
required_keys = {"paths_read", "unknowns", "confidence", "recommended_ledger_updates"}
```

At minimum, emit one error per missing key and include the result filename in the message.

- [ ] **Step 4: Tighten critical readiness wording**

Keep the existing critical-capability check, but extend the message and status logic so PRD build blocks if critical items are not explicitly `L4 Reconstruction-Ready` or equivalent approved status. If you need compatibility, accept legacy `reconstruction-ready` for old fixtures, but require the new template language in newly generated artifacts.

- [ ] **Step 5: Run the validation tests**

Run:

```powershell
pytest tests/test_prd_hook_contract.py tests/contract/test_hook_cli_surface.py -q
```

Expected: PASS

- [ ] **Step 6: Commit the validator changes**

Run:

```bash
git add src/specify_cli/hooks/artifact_validation.py tests/test_prd_hook_contract.py tests/contract/test_hook_cli_surface.py
git commit -m "feat: enforce heavy prd validation rules"
```

### Task 10: Propagate heavy PRD wording into docs and generated integration guidance

**Files:**
- Modify: [README.md](/F:/github/spec-kit-plus/README.md)
- Modify: [PROJECT-HANDBOOK.md](/F:/github/spec-kit-plus/PROJECT-HANDBOOK.md)
- Modify: [base.py](/F:/github/spec-kit-plus/src/specify_cli/integrations/base.py)
- Modify: [codex/__init__.py](/F:/github/spec-kit-plus/src/specify_cli/integrations/codex/__init__.py)
- Modify: PRD-related integration wording tests

- [ ] **Step 1: Add RED assertions for heavy PRD wording in integration tests**

Extend PRD-related integration wording tests so generated content expects phrases like:

```python
assert "subagent-mandatory" in content
assert "L4 Reconstruction-Ready" in content
assert "config-contracts.json" in content
assert "protocol-contracts.json" in content
assert "state-machines.json" in content
assert "error-semantics.json" in content
assert "verification-surfaces.json" in content
```

- [ ] **Step 2: Update README and handbook**

Add documentation that the PRD lane now produces a reconstruction archive rather than a slim PRD set. Include the new export names and the fact that critical evidence gaps block completion.

- [ ] **Step 3: Update generated integration guidance**

Where integrations emit PRD-specific instructions, add wording that:

- `prd-scan` is mandatory-subagent for substantive runs
- packetized worker results are required
- `prd-build` must not reread the repository
- the final archive includes config/protocol/state/error/verification/risk exports

- [ ] **Step 4: Run the docs/integration wording tests**

Run:

```powershell
pytest tests/integrations -q
```

Expected: PASS after the wording updates. If the full integration suite is too slow, run the failing PRD-related nodes first and then the broader suite before finalizing.

- [ ] **Step 5: Commit the docs and integration wording changes**

Run:

```bash
git add README.md PROJECT-HANDBOOK.md src/specify_cli/integrations templates/passive-skills tests/integrations
git commit -m "docs: propagate heavy prd reconstruction guidance"
```

### Task 11: Run the final focused verification pass

**Files:**
- Modify: none unless verification uncovers bugs
- Test: PRD-related tests and any directly touched integration suites

- [ ] **Step 1: Run the focused PRD verification suite**

Run:

```powershell
pytest ^
  tests/test_prd_scan_build_template_guidance.py ^
  tests/test_prd_template_guidance.py ^
  tests/test_prd_export_templates.py ^
  tests/test_prd_cli_helpers.py ^
  tests/test_prd_hook_contract.py ^
  tests/contract/test_hook_cli_surface.py -q
```

Expected: PASS

- [ ] **Step 2: Run packaging and integration verification**

Run:

```powershell
pytest tests/test_packaging_assets.py tests/integrations -q
```

Expected: PASS

- [ ] **Step 3: Inspect the final diff**

Run:

```bash
git status --short
git diff --stat
```

Expected: only planned PRD-heavy workflow, template, helper, validation, docs, and test files are modified.

- [ ] **Step 4: Commit any final verification fixes**

If verification required fixes, commit them with a focused message such as:

```bash
git add <fixed-files>
git commit -m "fix: resolve heavy prd verification regressions"
```

## Self-Review

Spec coverage check:

- Heavy two-step model: covered by Tasks 1-3.
- Mandatory subagent orchestration: covered by Tasks 1-3 and Task 10.
- Expanded scan artifacts: covered by Tasks 4-5 and Task 9.
- Expanded build exports: covered by Tasks 6-7 and Task 9.
- `L1-L4` evidence language and `critical -> L4`: covered by Tasks 1-2 and Task 9.
- Strict validation and refusal: covered by Tasks 8-9.
- Docs/integration propagation: covered by Task 10.
- Packaging/test lock-in: covered by Tasks 6, 10, and 11.

Placeholder scan:

- No `TODO` / `TBD` markers are present.
- Every task names exact files, commands, and expected outcomes.

Type consistency:

- New scan JSON shapes consistently use:
  - `entrypoints`
  - `configs`
  - `protocols`
  - `machines`
  - `errors`
  - `surfaces`
- New export filenames consistently use:
  - `config-contracts.md`
  - `protocol-contracts.md`
  - `state-machines.md`
  - `error-semantics.md`
  - `verification-surface.md`
  - `reconstruction-risks.md`

