# Map Scan Packet Ledger Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `sp-map-scan` enforce packet-local task ledgers, path-level coverage accounting, and leader-side gap/quality/contract/systemic acceptance so large repositories can be scanned without silent omission.

**Architecture:** Keep the leader responsible for candidate-universe partitioning and final acceptance, and keep each subagent responsible for proving completion inside a bounded packet ledger. `workbench/scan-packets/<lane-id>.md` remains the read-only instruction packet; `workbench/worker-results/<packet-id>.json` is the machine-checkable result handoff. Templates define the handoff contract; the Go runtime validates boundary alignment, disposition rules, packet accounting, and scan acceptance outcomes.

**Tech Stack:** Go runtime validation, Markdown command templates, pytest template tests, Go unit tests.

---

## Reference Spec

- `docs/superpowers/specs/2026-05-25-map-scan-packet-ledger-design.md`

## File Structure

- `templates/commands/map-scan.md`: add the packet-ledger contract, disposition-alignment rules, and leader acceptance outcomes (`fail_gap`, `fail_quality`, `fail_contract`, `fail_systemic`).
- `templates/command-partials/map-scan/shell.md`: add the short generated-command boundary planning guidance that says the canonical boundary is staged before dispatch.
- `templates/commands/map-build.md`: keep build guidance aligned with the new scan failure taxonomy so build intake routes back on contract/systemic failures instead of assuming local patchability.
- `templates/command-partials/map-build/shell.md`: mirror the build-side boundary acceptance summary if wording must change for the template assertions.
- `tools/project-cognition/internal/scanartifacts/scanartifacts.go`: validate worker-result packet-ledger accounting, scan-packet/result binding, `paths_read` path arrays, pass confidence, evidence-id source-path checks, disposition-to-criticality alignment, fail subset requirements, and new failure modes.
- `tools/project-cognition/internal/scanartifacts/scanartifacts_test.go`: add fixture tests for disposition alignment, packet ledger accounting, `paths_read` rejection, missing pass confidence, scan-packet/result binding, evidence-id mismatches, fail subsets, and systemic/contract rejection paths.
- `tools/project-cognition/internal/validation/scan.go`: keep scan acceptance strict and surface packet-ledger validation through the public gate payload.
- `tools/project-cognition/internal/validation/build.go`: ensure build acceptance still rejects incomplete or misaligned boundary states when scan artifacts are consumed.
- `tests/test_map_scan_build_template_guidance.py`: add assertions for the new scan packet ledger phrases and failure taxonomy.
- `tests/contract/test_hook_cli_surface.py`: only update if the generated scan/build artifact contract assertions fail after template changes.

---

### Task 1: Tighten Scan Template Contracts

**Files:**
- Modify: `templates/commands/map-scan.md`
- Modify: `templates/command-partials/map-scan/shell.md`
- Modify: `templates/commands/map-build.md`
- Modify: `templates/command-partials/map-build/shell.md`
- Test: `tests/test_map_scan_build_template_guidance.py`

- [ ] **Step 1: Add failing template assertions**

Add assertions to `tests/test_map_scan_build_template_guidance.py` that require these phrases in the scan/build templates:

```python
def test_map_scan_template_requires_packet_ledger_contract() -> None:
    content = _read("templates/commands/map-scan.md")
    lowered = content.lower()

    assert "packet-local task ledger" in lowered
    assert "coverage gate" in lowered
    assert "quality gate" in lowered
    assert "fail_gap" in lowered
    assert "fail_quality" in lowered
    assert "fail_contract" in lowered
    assert "fail_systemic" in lowered
    assert "sampled and inventory_only are not free-form" in lowered
    assert "repository-universe.json" in content
    assert "disposition and criticality together justify" in lowered


def test_map_build_template_routes_back_on_contract_and_systemic_failures() -> None:
    content = _read("templates/commands/map-build.md")
    lowered = content.lower()

    assert "repository-universe.json" in content
    assert "scan gap report" in lowered
    assert "contract" in lowered
    assert "systemic" in lowered
    assert "not only a local patch" in lowered or "not local patch" in lowered
```

- [ ] **Step 2: Run the template test and confirm it fails**

Run:

```powershell
pytest tests/test_map_scan_build_template_guidance.py -q
```

Expected: FAIL with missing packet-ledger and failure-taxonomy assertions.

- [ ] **Step 3: Update `map-scan` wording**

Edit `templates/commands/map-scan.md` so it states, in the scan contract section:

```markdown
- Each packet carries a subagent-local task ledger with `todo`, `doing`, `done`, `blocked`, and `overflow`.
- `sampled` and `inventory_only` are not free-form convenience labels; they must align with the recorded disposition and criticality in `repository-universe.json`.
- Critical entrypoints, shared state, configuration, tests, verification surfaces, and generated-surface propagation chains should not pass as `sampled` unless the boundary artifact already records an explicit accepted gap or an equally explicit lower-depth decision.
- Leader acceptance has two gates: coverage and quality.
- The leader may classify packet failure as `fail_gap`, `fail_quality`, `fail_contract`, or `fail_systemic`.
- `fail_quality` must return a machine-checkable repack subset.
- `fail_contract` and `fail_systemic` do not use local patch-only redispatch.
```

- [ ] **Step 4: Update the scan shell partial**

Add a short note to `templates/command-partials/map-scan/shell.md` that the boundary artifact is staged before dispatch and that the leader verifies ledger accounting before accepting any scan packet.

- [ ] **Step 5: Align the build template**

Update `templates/commands/map-build.md` and `templates/command-partials/map-build/shell.md` only as needed so the build-side wording matches the new failure taxonomy. Keep the build contract focused on consuming scan packages and routing back when packet families are contract-invalid or systemic.

- [ ] **Step 6: Run the template test again**

Run:

```powershell
pytest tests/test_map_scan_build_template_guidance.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit template changes**

Run:

```powershell
git add templates/commands/map-scan.md templates/command-partials/map-scan/shell.md templates/commands/map-build.md templates/command-partials/map-build/shell.md tests/test_map_scan_build_template_guidance.py
git commit -m "docs: tighten map scan packet ledger contract"
```

Expected: commit succeeds.

---

### Task 2: Add Runtime Validation For Packet Ledgers

**Files:**
- Modify: `tools/project-cognition/internal/scanartifacts/scanartifacts.go`
- Modify: `tools/project-cognition/internal/scanartifacts/scanartifacts_test.go`
- Modify: `tools/project-cognition/internal/validation/scan.go`
- Modify: `tools/project-cognition/internal/validation/build.go`

- [ ] **Step 1: Add failing scan-artifact tests**

Add Go tests that cover these cases in `tools/project-cognition/internal/scanartifacts/scanartifacts_test.go`:

```go
func TestValidateAcceptsPacketLedgerAlignedSampledOutcome(t *testing.T)
func TestValidateBlocksSampledCriticalEntrypointWithoutAcceptedGap(t *testing.T)
func TestValidateBlocksInventoryOnlyCriticalStateWithoutDispositionSupport(t *testing.T)
func TestValidateReturnsFailSubsetForQualityFailure(t *testing.T)
func TestValidateBlocksContractInvalidPacketLedger(t *testing.T)
func TestValidateBlocksSystemicRepeatedPacketFamilyFailure(t *testing.T)
func TestValidateBlocksBooleanPathsReadInWorkerResult(t *testing.T)
func TestValidateBlocksPassingWorkerResultWithoutConfidence(t *testing.T)
```

Each test should build a minimal fixture and assert:
- `sampled` / `inventory_only` only pass when `repository-universe.json` disposition and criticality support them
- `paths_read` must be a concrete path array in `workbench/worker-results/*.json`, not a boolean flag
- accepted worker results must include confidence
- `fail_quality` includes at least one of `paths`, `claim_ids`, `coverage_row_ids`, or `evidence_ids`
- contract-invalid ledgers are rejected before packet redispatch
- repeated sibling-packet failures elevate to `fail_systemic`

- [ ] **Step 2: Run the new Go tests and confirm they fail**

Run:

```powershell
go test ./tools/project-cognition/internal/scanartifacts ./tools/project-cognition/internal/validation -run TestValidate -count=1
```

Expected: FAIL until the new ledger validation exists.

- [ ] **Step 3: Extend scan artifact validation**

Update `tools/project-cognition/internal/scanartifacts/scanartifacts.go` so scan validation can reason about packet-local ledgers and the new failure classes:

- treat `sampled` and `inventory_only` as disposition-aligned outcomes, not free-form labels
- fail when a packet handoff omits a required repack subset for `fail_quality`
- fail when a packet claims `fail_contract` or `fail_systemic` but still asks for local patch-only redispatch
- keep `fail_gap` limited to missing / blocked / overflowed paths
- continue to reject excluded-path leakage into evidence, coverage, nodes, and build-facing rows

- [ ] **Step 4: Surface validation through the public gates**

Update `tools/project-cognition/internal/validation/scan.go` so `ValidateScan` reports packet-ledger errors through the scan gate payload, and update `tools/project-cognition/internal/validation/build.go` if build acceptance needs to refuse contract-invalid or systemic packet families explicitly.

- [ ] **Step 5: Run the Go tests again**

Run:

```powershell
go test ./tools/project-cognition/internal/scanartifacts ./tools/project-cognition/internal/validation -run TestValidate -count=1
```

Expected: PASS.

- [ ] **Step 6: Commit runtime validation changes**

Run:

```powershell
git add tools/project-cognition/internal/scanartifacts/scanartifacts.go tools/project-cognition/internal/scanartifacts/scanartifacts_test.go tools/project-cognition/internal/validation/scan.go tools/project-cognition/internal/validation/build.go
git commit -m "feat: validate map scan packet ledgers"
```

Expected: commit succeeds.

---

### Task 3: Verify End-To-End Contract Surface

**Files:**
- Modify if needed: `tests/contract/test_hook_cli_surface.py`
- Modify if needed: `tests/test_map_runtime_template_guidance.py`
- Modify if needed: `tests/test_alignment_templates.py`

- [ ] **Step 1: Run the focused regression set**

Run:

```powershell
pytest tests/test_map_scan_build_template_guidance.py tests/test_map_runtime_template_guidance.py tests/test_alignment_templates.py tests/contract/test_hook_cli_surface.py -q
```

Expected: PASS, or identify the smallest assertion set that still expects the old single-gate behavior.

- [ ] **Step 2: Fix any remaining stale assertions**

Only update the failing tests if they still expect:
- summary-only packet acceptance
- sampled/inventory_only without disposition alignment
- local patch-only redispatch for contract/systemic failures
- missing repack subset requirements for quality failures

- [ ] **Step 3: Run the focused regression set again**

Run the same pytest command again.

Expected: PASS.

- [ ] **Step 4: Commit verification updates**

Run:

```powershell
git add tests/contract/test_hook_cli_surface.py tests/test_map_runtime_template_guidance.py tests/test_alignment_templates.py
git commit -m "test: align packet ledger validation coverage"
```

Expected: commit succeeds.
