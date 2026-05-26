# Map Scan Stateful Subagent Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement stateful `sp-map-scan` packet scheduling contracts, worker result intake validation, and sparse `path_index` gates so broad project cognition scans cannot publish query-ready baselines with mostly unindexed paths.

**Architecture:** Keep the Go `project-cognition` runtime as the source of truth. Add scan queue and handoff ledger validation to `scanartifacts`, expose accepted nonblocking gap and path-index requirement helpers for build validation, and make `build-from-scan` publish ready status only after sparse gates pass. Update generated workflow templates and the Python fake runtime so prompts, hooks, and integration tests enforce the same contract.

**Tech Stack:** Go 1.x runtime under `tools/project-cognition`, SQLite via `modernc.org/sqlite`, Python pytest hook/integration tests, Markdown workflow templates.

---

## File Structure

- Modify `tools/project-cognition/internal/scanartifacts/scanartifacts.go`
  - Own required scan artifact list, worker result parsing, queue/handoff ledger validation, accepted nonblocking gap calculation, node path-source diagnostics, and exported path-index requirement helpers.
- Modify `tools/project-cognition/internal/scanartifacts/scanartifacts_test.go`
  - Add RED tests for required scheduler artifacts, queue/handoff stale-state invariants, acceptance schema, low-risk accepted gaps, and compatibility-derived node path diagnostics.
- Modify `tools/project-cognition/internal/validation/build.go`
  - Add sparse path-index validation details, hard failures, and warnings.
- Modify `tools/project-cognition/internal/validation/build_test.go`
  - Add RED tests for ratio hard failure, warning threshold, critical/important missing path index, accepted gap denominator behavior, and aggregate-only ownership failures.
- Create `tools/project-cognition/internal/buildgate/sparse.go`
  - Own reusable sparse path-index gate logic shared by `build-from-scan` and `validate-build`.
- Create `tools/project-cognition/internal/buildgate/sparse_test.go`
  - Exercise sparse gate behavior without full runtime status requirements.
- Modify `tools/project-cognition/internal/build/build.go`
  - Call sparse gates after DB import and before writing ready `status.json`.
- Modify `tools/project-cognition/internal/build/build_test.go`
  - Add RED tests that sparse gate failure leaves `status.json` missing or blocked and never writes query-ready state.
- Modify `templates/commands/map-scan.md`
  - Add durable `scan-queue.json` and `handoff-ledger.json` outputs, leader loop, strict worker prompt contract, and `acceptance=fail_gap` overflow wording.
- Modify `templates/commands/map-build.md`
  - Require scheduler artifacts and sparse gates before build publication.
- Modify `templates/command-partials/map-scan/shell.md`
  - Mention stateful queue and handoff artifacts in shell guidance.
- Modify `templates/command-partials/map-build/shell.md`
  - Mention sparse gates and ready-publication ordering.
- Modify `templates/project-handbook-template.md`
  - Teach generated projects that map-scan/build readiness includes queue, handoff, and sparse path-index validation.
- Modify `tests/test_map_scan_build_template_guidance.py`
  - Assert generated command templates contain the new stateful scheduler and worker contract phrases.
- Modify `tests/project_cognition_fake.py`
  - Mirror required scan queue/handoff artifacts, worker acceptance parsing, and sparse build gate behavior used by hook tests.
- Modify or add tests in `tests/hooks/test_artifact_hooks.py` only if fake-runtime validation is not covered by existing hook surfaces after `tests/project_cognition_fake.py` changes.

## Task 1: Require Scheduler Artifacts And Validate Queue/Handoff Invariants

**Files:**
- Modify: `tools/project-cognition/internal/scanartifacts/scanartifacts_test.go`
- Modify: `tools/project-cognition/internal/scanartifacts/scanartifacts.go`

- [ ] **Step 1: Write failing tests for required artifacts**

Add these tests near the existing required artifact tests in `tools/project-cognition/internal/scanartifacts/scanartifacts_test.go`:

```go
func TestValidateRequiresScanQueueAndHandoffLedger(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	_ = os.Remove(filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"))
	_ = os.Remove(filepath.Join(paths.RuntimeDir, "workbench", "handoff-ledger.json"))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "missing .specify/project-cognition/workbench/scan-queue.json") {
		t.Fatalf("Errors = %#v, want missing scan-queue.json", result.Errors)
	}
	if !containsError(result.Errors, "missing .specify/project-cognition/workbench/handoff-ledger.json") {
		t.Fatalf("Errors = %#v, want missing handoff-ledger.json", result.Errors)
	}
}

func TestValidateBlocksWorkerResultWithoutQueueReturnEvent(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "handoff-ledger.json"), []byte(`{"events":[{"event_id":"dispatch-1","packet_id":"lane-1","event_type":"dispatched","created_at":"2026-05-26T00:00:00Z"}]}`))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "worker result lane-1.json has no matching handoff return event") {
		t.Fatalf("Errors = %#v, want missing return event", result.Errors)
	}
}

func TestValidateBlocksAcceptedQueueRowWithOverflowCoverage(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeWorkerResult(t, paths, "lane-1.json", `{
		"packet_id":"lane-1",
		"family_id":"app",
		"assigned_paths":["src/app.go"],
		"paths_read":[],
		"ledger":{"todo":[],"doing":[],"done":[],"blocked":[],"overflow":["src/app.go"]},
		"coverage":[{"path":"src/app.go","outcome":"overflow"}],
		"confidence":"low",
		"acceptance":"fail_gap"
	}`)

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "queue packet lane-1 is accepted but path src/app.go is overflow") {
		t.Fatalf("Errors = %#v, want accepted queue overflow error", result.Errors)
	}
}

func TestValidateAcceptsOverflowQueueWithOpenGap(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"), []byte(`{
		"packets":[{"packet_id":"lane-1","state":"overflow","assigned_paths":["src/app.go"],"result_handoff_path":".specify/project-cognition/workbench/worker-results/lane-1.json","next_action":"split"}]
	}`))
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "handoff-ledger.json"), []byte(`{
		"events":[
			{"event_id":"dispatch-1","packet_id":"lane-1","event_type":"dispatched","created_at":"2026-05-26T00:00:00Z"},
			{"event_id":"return-1","packet_id":"lane-1","event_type":"returned","worker_result_path":".specify/project-cognition/workbench/worker-results/lane-1.json","created_at":"2026-05-26T00:01:00Z"}
		]
	}`))
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json"), []byte(`{
		"rows":[{"path":"src/app.go","coverage_state":"overflow","packet_id":"lane-1"}],
		"open_gaps":[{"paths":["src/app.go"],"packet_id":"lane-1","status":"overflow","owner":"scan","reason":"packet exceeded context","evidence_expectation":"split packet","revisit_condition":"child packet closes path","next_action":"split"}]
	}`))
	writeWorkerResult(t, paths, "lane-1.json", `{
		"packet_id":"lane-1",
		"family_id":"app",
		"assigned_paths":["src/app.go"],
		"paths_read":[],
		"ledger":{"todo":[],"doing":[],"done":[],"blocked":[],"overflow":["src/app.go"]},
		"coverage":[{"path":"src/app.go","outcome":"overflow"}],
		"confidence":"low",
		"acceptance":"fail_gap"
	}`)

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if !containsError(result.Errors, "packet lane-1 failed coverage gate") {
		t.Fatalf("Errors = %#v, want fail_gap coverage gate error", result.Errors)
	}
	if containsError(result.Errors, "queue packet lane-1 state overflow has no coverage-ledger gap or child packet") {
		t.Fatalf("Errors = %#v, did not expect queue stale-state error", result.Errors)
	}
}

func TestValidateBlocksOverflowQueueWithoutGapOrChildPacket(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"), []byte(`{
		"packets":[{"packet_id":"lane-1","state":"overflow","assigned_paths":["src/app.go"],"result_handoff_path":".specify/project-cognition/workbench/worker-results/lane-1.json","next_action":"split"}]
	}`))
	writeWorkerResult(t, paths, "lane-1.json", `{
		"packet_id":"lane-1",
		"family_id":"app",
		"assigned_paths":["src/app.go"],
		"paths_read":[],
		"ledger":{"todo":[],"doing":[],"done":[],"blocked":[],"overflow":["src/app.go"]},
		"coverage":[{"path":"src/app.go","outcome":"overflow"}],
		"confidence":"low",
		"acceptance":"fail_gap"
	}`)

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "queue packet lane-1 state overflow has no coverage-ledger gap or child packet") {
		t.Fatalf("Errors = %#v, want queue stale-state error", result.Errors)
	}
}
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```powershell
go test ./tools/project-cognition/internal/scanartifacts -run "TestValidateRequiresScanQueueAndHandoffLedger|TestValidateBlocksWorkerResultWithoutQueueReturnEvent|TestValidateBlocksAcceptedQueueRowWithOverflowCoverage|TestValidateAcceptsOverflowQueueWithOpenGap|TestValidateBlocksOverflowQueueWithoutGapOrChildPacket" -count=1
```

Expected: FAIL because `scan-queue.json` and `handoff-ledger.json` are not required and no queue/handoff invariants exist.

- [ ] **Step 3: Add required artifacts and helper types**

In `tools/project-cognition/internal/scanartifacts/scanartifacts.go`, add `scan-queue.json` and `handoff-ledger.json` to `requiredArtifactPaths` immediately after `repository-universe.json`:

```go
".specify/project-cognition/workbench/scan-queue.json",
".specify/project-cognition/workbench/handoff-ledger.json",
```

Add these helper types near `PacketValidationSummary`:

```go
type ScanQueueRow struct {
	PacketID          string
	ParentPacketID    string
	State             string
	AssignedPaths     []string
	ResultHandoffPath string
	NextAction        string
}

type HandoffEvent struct {
	PacketID         string
	EventType        string
	WorkerResultPath string
}

type QueueState struct {
	Rows          map[string]ScanQueueRow
	ReturnEvents  map[string]bool
	ChildPackets  map[string]bool
	GapPackets    map[string]bool
}
```

- [ ] **Step 4: Add queue and handoff loaders**

Add these functions below `loadOptionalWorkbenchJSON`:

```go
func loadQueueState(paths rt.Paths, result *Result) QueueState {
	state := QueueState{
		Rows:         map[string]ScanQueueRow{},
		ReturnEvents: map[string]bool{},
		ChildPackets: map[string]bool{},
		GapPackets:   coverageGapPacketIDs(paths),
	}
	raw, err := readJSONFile(filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"), "scan-queue.json")
	if err != nil {
		result.Errors = append(result.Errors, err.Error())
		return state
	}
	rows, err := arrayRowsForKeys(raw, "packets", "rows", "queue")
	if err != nil {
		result.Errors = append(result.Errors, "scan-queue.json: "+err.Error())
		return state
	}
	for i, row := range rows {
		packetID := normalizedString(row["packet_id"])
		if packetID == "" {
			result.Errors = append(result.Errors, fmt.Sprintf("scan-queue.json packets[%d] is missing packet_id", i))
			continue
		}
		if state.Rows[packetID].PacketID != "" {
			result.Errors = append(result.Errors, fmt.Sprintf("scan-queue.json packet_id %s appears more than once", packetID))
			continue
		}
		parentID := normalizedString(row["parent_packet_id"])
		if parentID != "" {
			state.ChildPackets[parentID] = true
		}
		state.Rows[packetID] = ScanQueueRow{
			PacketID:          packetID,
			ParentPacketID:    parentID,
			State:             normalizedString(row["state"]),
			AssignedPaths:     normalizedStringSlice(row["assigned_paths"]),
			ResultHandoffPath: normalizedString(row["result_handoff_path"]),
			NextAction:        normalizedString(row["next_action"]),
		}
	}
	rawEvents, err := readJSONFile(filepath.Join(paths.RuntimeDir, "workbench", "handoff-ledger.json"), "handoff-ledger.json")
	if err != nil {
		result.Errors = append(result.Errors, err.Error())
		return state
	}
	events, err := arrayRowsForKeys(rawEvents, "events", "rows", "handoffs")
	if err != nil {
		result.Errors = append(result.Errors, "handoff-ledger.json: "+err.Error())
		return state
	}
	for i, row := range events {
		packetID := normalizedString(row["packet_id"])
		if packetID == "" {
			result.Errors = append(result.Errors, fmt.Sprintf("handoff-ledger.json events[%d] is missing packet_id", i))
			continue
		}
		eventType := normalizedString(row["event_type"])
		if eventType == "returned" || eventType == "return" {
			state.ReturnEvents[packetID] = true
		}
	}
	return state
}

func coverageGapPacketIDs(paths rt.Paths) map[string]bool {
	packetIDs := map[string]bool{}
	raw, err := readJSONFile(filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json"), "coverage-ledger.json")
	if err != nil {
		return packetIDs
	}
	obj, ok := raw.(map[string]any)
	if !ok {
		return packetIDs
	}
	gaps, ok := obj["open_gaps"].([]any)
	if !ok {
		return packetIDs
	}
	for _, gap := range gaps {
		gapObj, ok := gap.(map[string]any)
		if !ok {
			continue
		}
		if packetID := normalizedString(gapObj["packet_id"]); packetID != "" {
			packetIDs[packetID] = true
		}
		if packetID := normalizedString(gapObj["parent_packet_id"]); packetID != "" {
			packetIDs[packetID] = true
		}
		if packetID := normalizedString(gapObj["source_packet_id"]); packetID != "" {
			packetIDs[packetID] = true
		}
	}
	return packetIDs
}
```

- [ ] **Step 5: Wire queue validation into `Load` and worker result validation**

In `Load`, after `boundary := loadBoundary(paths, &result)`, add:

```go
queueState := loadQueueState(paths, &result)
validateScanPacketQueueFiles(paths, queueState, &result)
```

Change the call to `validateWorkerResults` to pass `queueState`:

```go
packetSummary := validateWorkerResults(paths, boundary, pkg, queueState, &result)
```

Change the function signature:

```go
func validateWorkerResults(paths rt.Paths, boundary Boundary, pkg Package, queueState QueueState, result *Result) PacketValidationSummary
```

Inside `validateWorkerResults`, after the existing scan-packet match check, add:

```go
if queueState.Rows[packetID].PacketID == "" {
	result.Errors = append(result.Errors, fmt.Sprintf("worker result %s has no matching scan-queue row", entry.Name()))
}
if !queueState.ReturnEvents[packetID] {
	result.Errors = append(result.Errors, fmt.Sprintf("worker result %s has no matching handoff return event", entry.Name()))
}
```

Change the `validateScanPacket` call to include the queue row:

```go
validateScanPacket(packetID, packet, boundary, pkg, queueState.Rows[packetID], result)
```

- [ ] **Step 6: Add queue stale-state checks**

Add this function below `validateScanPacketFiles`:

```go
func validateScanPacketQueueFiles(paths rt.Paths, queueState QueueState, result *Result) {
	packetIDs := validateScanPacketFiles(paths, result)
	for packetID := range packetIDs {
		if queueState.Rows[packetID].PacketID == "" {
			result.Errors = append(result.Errors, fmt.Sprintf("scan packet %s has no matching scan-queue row", packetID))
		}
	}
	for packetID := range queueState.Rows {
		if len(packetIDs) > 0 && !packetIDs[packetID] {
			result.Errors = append(result.Errors, fmt.Sprintf("scan-queue packet %s has no matching scan packet", packetID))
		}
	}
}
```

Change `validateScanPacket` signature:

```go
func validateScanPacket(packetID string, packet map[string]any, boundary Boundary, pkg Package, queueRow ScanQueueRow, result *Result)
```

At the end of `validateScanPacket`, call:

```go
validateQueueRowClosure(packetID, queueRow, coverageByPath, pkg, queueState, result)
```

Add:

```go
func validateQueueRowClosure(packetID string, queueRow ScanQueueRow, coverageByPath map[string]map[string]any, pkg Package, queueState QueueState, result *Result) {
	if queueRow.PacketID == "" {
		return
	}
	switch queueRow.State {
	case "accepted":
		for _, path := range queueRow.AssignedPaths {
			row := coverageByPath[path]
			outcome := normalizedString(row["outcome"])
			if row == nil && !pkg.AcceptedGaps[path] {
				result.Errors = append(result.Errors, fmt.Sprintf("queue packet %s is accepted but path %s has no coverage closure", packetID, path))
				continue
			}
			if outcome == "blocked" || outcome == "overflow" {
				result.Errors = append(result.Errors, fmt.Sprintf("queue packet %s is accepted but path %s is %s", packetID, path, outcome))
			}
		}
	case "overflow", "blocked", "repack_required":
		if queueRow.NextAction == "" {
			result.Errors = append(result.Errors, fmt.Sprintf("queue packet %s state %s must define next_action", packetID, queueRow.State))
		}
		if !queueState.ChildPackets[packetID] && !queueState.GapPackets[packetID] {
			result.Errors = append(result.Errors, fmt.Sprintf("queue packet %s state %s has no coverage-ledger gap or child packet", packetID, queueRow.State))
		}
	}
}
```

- [ ] **Step 7: Update minimal scan package helpers**

Update both `writeMinimalScanPackage` helpers in `scanartifacts_test.go` and `build_test.go` to write:

```go
writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"), []byte(`{
	"packets":[{"packet_id":"lane-1","state":"accepted","assigned_paths":["src/app.go"],"result_handoff_path":".specify/project-cognition/workbench/worker-results/lane-1.json","next_action":"none"}]
}`))
writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "handoff-ledger.json"), []byte(`{
	"events":[
		{"event_id":"dispatch-1","packet_id":"lane-1","event_type":"dispatched","created_at":"2026-05-26T00:00:00Z"},
		{"event_id":"return-1","packet_id":"lane-1","event_type":"returned","worker_result_path":".specify/project-cognition/workbench/worker-results/lane-1.json","created_at":"2026-05-26T00:01:00Z"}
	]
}`))
```

- [ ] **Step 8: Run targeted tests**

Run:

```powershell
go test ./tools/project-cognition/internal/scanartifacts -run "TestValidateRequiresScanQueueAndHandoffLedger|TestValidateBlocksWorkerResultWithoutQueueReturnEvent|TestValidateBlocksAcceptedQueueRowWithOverflowCoverage|TestValidateAcceptsOverflowQueueWithOpenGap|TestValidateBlocksOverflowQueueWithoutGapOrChildPacket" -count=1
```

Expected: PASS.

- [ ] **Step 9: Commit**

```powershell
git add tools/project-cognition/internal/scanartifacts/scanartifacts.go tools/project-cognition/internal/scanartifacts/scanartifacts_test.go tools/project-cognition/internal/build/build_test.go
git commit -m "feat(cognition): validate map scan scheduler state"
```

## Task 2: Enforce Worker Acceptance Contract

**Files:**
- Modify: `tools/project-cognition/internal/scanartifacts/scanartifacts_test.go`
- Modify: `tools/project-cognition/internal/scanartifacts/scanartifacts.go`

- [ ] **Step 1: Write failing tests for acceptance**

Add:

```go
func TestValidateBlocksWorkerResultMissingAcceptance(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeWorkerResult(t, paths, "lane-1.json", `{
		"packet_id":"lane-1",
		"family_id":"app",
		"assigned_paths":["src/app.go"],
		"paths_read":["src/app.go"],
		"ledger":{"todo":[],"doing":[],"done":["src/app.go"],"blocked":[],"overflow":[]},
		"coverage":[{"path":"src/app.go","outcome":"read","evidence_ids":["E-001"]}],
		"confidence":"high"
	}`)

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "packet lane-1 must define acceptance") {
		t.Fatalf("Errors = %#v, want missing acceptance error", result.Errors)
	}
}

func TestValidateWarnsForLegacyOutcomeAlias(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeWorkerResult(t, paths, "lane-1.json", `{
		"packet_id":"lane-1",
		"family_id":"app",
		"assigned_paths":["src/app.go"],
		"paths_read":["src/app.go"],
		"ledger":{"todo":[],"doing":[],"done":["src/app.go"],"blocked":[],"overflow":[]},
		"coverage":[{"path":"src/app.go","outcome":"read","evidence_ids":["E-001"]}],
		"confidence":"high",
		"outcome":"pass"
	}`)

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "ok" {
		t.Fatalf("Status = %q, want ok; errors=%#v", result.Status, result.Errors)
	}
	if !containsString(result.Warnings, "packet lane-1 uses legacy top-level outcome alias; new worker results must write acceptance") {
		t.Fatalf("Warnings = %#v, want legacy outcome warning", result.Warnings)
	}
}

func TestValidateBlocksPacketLevelOverflowAcceptance(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeWorkerResult(t, paths, "lane-1.json", `{
		"packet_id":"lane-1",
		"family_id":"app",
		"assigned_paths":["src/app.go"],
		"paths_read":[],
		"ledger":{"todo":[],"doing":[],"done":[],"blocked":[],"overflow":["src/app.go"]},
		"coverage":[{"path":"src/app.go","outcome":"overflow"}],
		"confidence":"low",
		"acceptance":"overflow"
	}`)

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "packet lane-1 has invalid acceptance overflow") {
		t.Fatalf("Errors = %#v, want invalid acceptance error", result.Errors)
	}
}
```

- [ ] **Step 2: Run tests to verify RED**

```powershell
go test ./tools/project-cognition/internal/scanartifacts -run "TestValidateBlocksWorkerResultMissingAcceptance|TestValidateWarnsForLegacyOutcomeAlias|TestValidateBlocksPacketLevelOverflowAcceptance" -count=1
```

Expected: FAIL because missing acceptance defaults to `pass` and legacy alias does not warn.

- [ ] **Step 3: Add an acceptance extraction helper**

In `scanartifacts.go`, add:

```go
func packetAcceptance(packetID string, packet map[string]any, result *Result) (string, bool) {
	acceptance := normalizedString(packet["acceptance"])
	if acceptance != "" {
		return acceptance, true
	}
	legacy := normalizedString(packet["outcome"])
	if legacy != "" {
		result.Warnings = append(result.Warnings, fmt.Sprintf("packet %s uses legacy top-level outcome alias; new worker results must write acceptance", packetID))
		return legacy, true
	}
	result.Errors = append(result.Errors, fmt.Sprintf("packet %s must define acceptance", packetID))
	return "", false
}
```

- [ ] **Step 4: Replace default-pass behavior**

In `validateWorkerResults`, replace:

```go
outcome := normalizedString(packet["acceptance"])
if outcome == "" {
	outcome = normalizedString(packet["outcome"])
}
if outcome == "" {
	outcome = "pass"
}
summary.Outcomes[outcome]++
```

with:

```go
outcome, ok := packetAcceptance(packetID, packet, result)
if ok {
	summary.Outcomes[outcome]++
}
```

In `validatePacketAcceptance`, replace the current acceptance extraction block with:

```go
acceptance, ok := packetAcceptance(packetID, packet, result)
if !ok {
	return
}
```

- [ ] **Step 5: Run targeted tests**

```powershell
go test ./tools/project-cognition/internal/scanartifacts -run "TestValidateBlocksWorkerResultMissingAcceptance|TestValidateWarnsForLegacyOutcomeAlias|TestValidateBlocksPacketLevelOverflowAcceptance" -count=1
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add tools/project-cognition/internal/scanartifacts/scanartifacts.go tools/project-cognition/internal/scanartifacts/scanartifacts_test.go
git commit -m "fix(cognition): require packet acceptance"
```

## Task 3: Tighten Accepted Nonblocking Gap Semantics

**Files:**
- Modify: `tools/project-cognition/internal/scanartifacts/scanartifacts_test.go`
- Modify: `tools/project-cognition/internal/scanartifacts/scanartifacts.go`

- [ ] **Step 1: Write failing tests for important accepted gaps**

Add:

```go
func TestValidateBlocksImportantAcceptedGapForBoundaryCoverage(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json"), []byte(`{
		"rows":[{"path":"src/app.go"}],
		"open_gaps":[{"paths":["src/missing.go"],"coverage_state":"low_risk_open_gap","owner":"scan","reason":"deferred","evidence_expectation":"non-critical path","revisit_condition":"next scan"}]
	}`))
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), []byte(`{
		"schema_version":1,
		"candidate_universe":[{"path":"src/app.go","disposition":"deep_read","decision_source":"git"},{"path":"src/missing.go","disposition":"sampled","decision_source":"git"}],
		"included_paths":["src/app.go","src/missing.go"],
		"excluded_paths":[],
		"ambiguous_paths":[],
		"dispositions":{"src/app.go":"deep_read","src/missing.go":"sampled"},
		"criticality":{"src/app.go":"important","src/missing.go":"important"},
		"classification_reasons":{"src/app.go":"source","src/missing.go":"source"},
		"decision_source":{"src/app.go":"git","src/missing.go":"git"}
	}`))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "repository-universe included path src/missing.go has no coverage row or accepted nonblocking gap") {
		t.Fatalf("Errors = %#v, want important gap denominator error", result.Errors)
	}
}
```

- [ ] **Step 2: Run test to verify RED**

```powershell
go test ./tools/project-cognition/internal/scanartifacts -run "TestValidateBlocksImportantAcceptedGapForBoundaryCoverage|TestValidateAcceptsLowRiskGapPathsArrayWithRequiredMetadata" -count=1
```

Expected: FAIL because `acceptedGapPaths` currently does not check path criticality.

- [ ] **Step 3: Load boundary before accepted gaps**

In `Load`, replace:

```go
pkg.AcceptedGaps = acceptedGapPaths(paths)
boundary := loadBoundary(paths, &result)
```

with:

```go
boundary := loadBoundary(paths, &result)
pkg.AcceptedGaps = acceptedNonblockingGapPaths(paths, boundary)
```

- [ ] **Step 4: Rename and tighten accepted gap helper**

Rename `acceptedGapPaths` to `acceptedNonblockingGapPaths` and add criticality filtering:

```go
func acceptedNonblockingGapPaths(paths rt.Paths, boundary Boundary) map[string]bool {
	accepted := map[string]bool{}
	raw, err := readJSONFile(filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json"), "coverage-ledger.json")
	if err != nil {
		return accepted
	}
	obj, ok := raw.(map[string]any)
	if !ok {
		return accepted
	}
	gaps, ok := obj["open_gaps"].([]any)
	if !ok {
		return accepted
	}
	for _, gap := range gaps {
		gapObj, ok := gap.(map[string]any)
		if !ok {
			continue
		}
		status := normalizedString(gapObj["status"])
		reason := normalizedString(gapObj["reason"])
		coverageState := normalizedString(gapObj["coverage_state"])
		if blockedGapStatusOrReason(status) || blockedGapStatusOrReason(reason) || blockedGapStatusOrReason(coverageState) {
			continue
		}
		if status != "low_risk_open_gap" && coverageState != "low_risk_open_gap" {
			continue
		}
		if normalizedString(gapObj["owner"]) == "" ||
			reason == "" ||
			normalizedString(gapObj["evidence_expectation"]) == "" ||
			normalizedString(gapObj["revisit_condition"]) == "" {
			continue
		}
		for _, path := range gapPaths(gapObj) {
			if boundary.Criticality[path] == "low_risk" {
				accepted[path] = true
			}
		}
	}
	return accepted
}

func gapPaths(gapObj map[string]any) []string {
	values := []string{}
	if path := normalizedString(gapObj["path"]); path != "" {
		values = append(values, path)
	}
	values = append(values, normalizedStringSlice(gapObj["paths"])...)
	return uniqueStrings(values)
}
```

- [ ] **Step 5: Update boundary coverage error wording**

In `validateBoundaryCoverage`, change both occurrences of:

```go
"has no coverage row or accepted gap"
```

to:

```go
"has no coverage row or accepted nonblocking gap"
```

Update existing test assertions that intentionally check this message.

- [ ] **Step 6: Run targeted tests**

```powershell
go test ./tools/project-cognition/internal/scanartifacts -run "AcceptedGap|NonblockingGap|BoundaryCoverage" -count=1
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add tools/project-cognition/internal/scanartifacts/scanartifacts.go tools/project-cognition/internal/scanartifacts/scanartifacts_test.go
git commit -m "fix(cognition): restrict accepted scan gaps"
```

## Task 4: Track Canonical Versus Compatibility-Derived Node Paths

**Files:**
- Modify: `tools/project-cognition/internal/scanartifacts/scanartifacts_test.go`
- Modify: `tools/project-cognition/internal/scanartifacts/scanartifacts.go`
- Modify: `tools/project-cognition/internal/build/build_test.go`

- [ ] **Step 1: Write failing diagnostics test**

Add:

```go
func TestLoadReportsCanonicalAndCompatibilityNodePathCounts(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "provisional", "nodes.json"), []byte(`{
		"nodes":[
			{"id":"N-canonical","type":"file","title":"Canonical","paths":["src/app.go"],"evidence_ids":["E-001"]},
			{"id":"N-compat","type":"file","title":"Compat","attrs_json":{"path":"src/compat.go"},"evidence_ids":["E-001"]}
		]
	}`))
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "coverage.json"), []byte(`{"rows":[{"path":"src/app.go"},{"path":"src/compat.go"}]}`))
	writeVersionedUniverse(t, paths,
		`[{"path":"src/app.go","disposition":"deep_read","decision_source":"git"},{"path":"src/compat.go","disposition":"deep_read","decision_source":"git"}]`,
		`{"src/app.go":"deep_read","src/compat.go":"deep_read"}`,
		`{"src/app.go":"important","src/compat.go":"important"}`,
	)

	_, result := Load(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Details["canonical_node_path_count"] != 1 {
		t.Fatalf("canonical_node_path_count = %#v, want 1", result.Details["canonical_node_path_count"])
	}
	if result.Details["compatibility_derived_node_path_count"] != 1 {
		t.Fatalf("compatibility_derived_node_path_count = %#v, want 1", result.Details["compatibility_derived_node_path_count"])
	}
}
```

- [ ] **Step 2: Run test to verify RED**

```powershell
go test ./tools/project-cognition/internal/scanartifacts -run TestLoadReportsCanonicalAndCompatibilityNodePathCounts -count=1
```

Expected: FAIL because the detail keys do not exist.

- [ ] **Step 3: Extend `NodeRow`**

Add fields:

```go
CanonicalPathCount     int
CompatibilityPathCount int
```

Change `loadNodes` to call:

```go
paths, canonicalCount, compatibilityCount := nodePathInfo(row, attrs)
item := NodeRow{
	ID:                     normalizedIdentityString(firstValue(row, "id", "node_id")),
	Type:                   firstNormalizedString(row, "type", "kind"),
	Title:                  firstNormalizedString(row, "title", "label", "name"),
	Confidence:             normalizedString(row["confidence"]),
	Paths:                  paths,
	CanonicalPathCount:     canonicalCount,
	CompatibilityPathCount: compatibilityCount,
	EvidenceIDs:            evidenceRefs(row),
	Attrs:                  attrs,
}
```

- [ ] **Step 4: Replace `nodePaths` with counted helper**

Replace `nodePaths` with:

```go
func nodePathInfo(row map[string]any, attrs map[string]any) ([]string, int, int) {
	canonical := normalizedStringSlice(row["paths"])
	compatibility := []string{}
	for _, key := range []string{"path", "source_path", "file_path"} {
		if path := normalizedString(row[key]); path != "" {
			compatibility = append(compatibility, path)
		}
		if path := normalizedString(attrs[key]); path != "" {
			compatibility = append(compatibility, path)
		}
	}
	paths := uniqueStrings(append(append([]string{}, canonical...), compatibility...))
	return paths, len(uniqueStrings(canonical)), len(uniqueStrings(compatibility))
}
```

- [ ] **Step 5: Add package details**

Add:

```go
func nodePathCounts(nodes []NodeRow) (int, int) {
	canonical := 0
	compatibility := 0
	for _, node := range nodes {
		canonical += node.CanonicalPathCount
		compatibility += node.CompatibilityPathCount
	}
	return canonical, compatibility
}
```

In `Load`, before returning:

```go
canonicalNodePathCount, compatibilityNodePathCount := nodePathCounts(pkg.Nodes)
result.Details["canonical_node_path_count"] = canonicalNodePathCount
result.Details["compatibility_derived_node_path_count"] = compatibilityNodePathCount
```

- [ ] **Step 6: Rename natural-fields build test**

In `tools/project-cognition/internal/build/build_test.go`, rename `TestRunBuildsPathIndexFromDownstreamNaturalNodeFields` to:

```go
func TestRunBuildsPathIndexFromCompatibilityNodeFields(t *testing.T) {
```

Keep the assertions. This preserves compatibility while making the behavior explicit.

- [ ] **Step 7: Run targeted tests**

```powershell
go test ./tools/project-cognition/internal/scanartifacts -run TestLoadReportsCanonicalAndCompatibilityNodePathCounts -count=1
go test ./tools/project-cognition/internal/build -run TestRunBuildsPathIndexFromCompatibilityNodeFields -count=1
```

Expected: PASS.

- [ ] **Step 8: Commit**

```powershell
git add tools/project-cognition/internal/scanartifacts/scanartifacts.go tools/project-cognition/internal/scanartifacts/scanartifacts_test.go tools/project-cognition/internal/build/build_test.go
git commit -m "feat(cognition): report node path source counts"
```

## Task 5: Add Sparse Path-Index Build Gates

**Files:**
- Modify: `tools/project-cognition/internal/validation/build_test.go`
- Modify: `tools/project-cognition/internal/validation/build.go`
- Modify: `tools/project-cognition/internal/scanartifacts/scanartifacts.go`
- Create: `tools/project-cognition/internal/buildgate/sparse.go`

- [ ] **Step 1: Write failing validation tests**

Add these tests to `tools/project-cognition/internal/validation/build_test.go`:

```go
func TestValidateBuildBlocksCriticalAndImportantMissingPathIndex(t *testing.T) {
	paths := validationTestPaths(t)
	writeBuildAcceptanceInputs(t, paths)
	seedMatchingQueryReadyDatabase(t, paths, nil, nil)
	writeScanPackageWithUniverse(t, paths,
		[]string{"src/app.go", "src/critical.go", "src/important.go"},
		map[string]string{"src/app.go": "important", "src/critical.go": "critical", "src/important.go": "important"},
		[]string{"src/app.go"},
	)

	payload := ValidateBuild(paths)

	if payload.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", payload.Status, payload.Errors)
	}
	if !hasValidationError(payload.Errors, "critical_missing_path_index: src/critical.go") {
		t.Fatalf("Errors = %#v, want critical missing path index", payload.Errors)
	}
	if !hasValidationError(payload.Errors, "important_missing_path_index: src/important.go") {
		t.Fatalf("Errors = %#v, want important missing path index", payload.Errors)
	}
}

func TestValidateBuildWarnsBelowNinetyPercentAndFailsBelowSeventyPercent(t *testing.T) {
	paths := validationTestPaths(t)
	writeBuildAcceptanceInputs(t, paths)
	seedQueryReadyDatabaseWithPaths(t, paths, []string{"src/a.go", "src/b.go", "src/c.go", "src/d.go", "src/e.go", "src/f.go", "src/g.go"})
	writeScanPackageWithUniverse(t, paths,
		[]string{"src/a.go", "src/b.go", "src/c.go", "src/d.go", "src/e.go", "src/f.go", "src/g.go", "src/h.go", "src/i.go", "src/j.go"},
		map[string]string{"src/a.go": "low_risk", "src/b.go": "low_risk", "src/c.go": "low_risk", "src/d.go": "low_risk", "src/e.go": "low_risk", "src/f.go": "low_risk", "src/g.go": "low_risk", "src/h.go": "low_risk", "src/i.go": "low_risk", "src/j.go": "low_risk"},
		[]string{"src/a.go", "src/b.go", "src/c.go", "src/d.go", "src/e.go", "src/f.go", "src/g.go"},
	)

	payload := ValidateBuild(paths)

	if payload.Status != "ok" {
		t.Fatalf("Status = %q, want ok; errors=%#v", payload.Status, payload.Errors)
	}
	if !hasValidationWarning(payload.Warnings, "path_index_to_included_ratio 0.70 is below warning threshold 0.90") {
		t.Fatalf("Warnings = %#v, want sparse warning", payload.Warnings)
	}
}

func TestValidateBuildFailsBelowSeventyPercentRatio(t *testing.T) {
	paths := validationTestPaths(t)
	writeBuildAcceptanceInputs(t, paths)
	seedQueryReadyDatabaseWithPaths(t, paths, []string{"src/a.go", "src/b.go", "src/c.go", "src/d.go", "src/e.go", "src/f.go"})
	writeScanPackageWithUniverse(t, paths,
		[]string{"src/a.go", "src/b.go", "src/c.go", "src/d.go", "src/e.go", "src/f.go", "src/g.go", "src/h.go", "src/i.go", "src/j.go"},
		map[string]string{"src/a.go": "low_risk", "src/b.go": "low_risk", "src/c.go": "low_risk", "src/d.go": "low_risk", "src/e.go": "low_risk", "src/f.go": "low_risk", "src/g.go": "low_risk", "src/h.go": "low_risk", "src/i.go": "low_risk", "src/j.go": "low_risk"},
		[]string{"src/a.go", "src/b.go", "src/c.go", "src/d.go", "src/e.go", "src/f.go"},
	)

	payload := ValidateBuild(paths)

	if payload.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", payload.Status, payload.Errors)
	}
	if !hasValidationError(payload.Errors, "path_index_to_included_ratio 0.60 is below hard threshold 0.70") {
		t.Fatalf("Errors = %#v, want sparse hard failure", payload.Errors)
	}
}
```

- [ ] **Step 2: Add test helpers**

Add these helpers near existing seed helpers in `build_test.go`:

```go
func seedQueryReadyDatabaseWithPaths(t *testing.T, paths rt.Paths, indexedPaths []string) {
	t.Helper()
	st, err := store.Open(paths)
	if err != nil {
		t.Fatal(err)
	}
	defer st.Close()
	evidence := []store.EvidenceImport{}
	nodes := []store.NodeImport{}
	pathIndex := []store.PathIndexImport{}
	for i, path := range indexedPaths {
		evidenceID := fmt.Sprintf("E-%03d", i+1)
		nodeID := fmt.Sprintf("N-%03d", i+1)
		evidence = append(evidence, store.EvidenceImport{ID: evidenceID, SourceKind: "file", SourcePath: path, CommitSHA: "abc123", Span: "L1", Extractor: "test", ContentHash: "hash"})
		nodes = append(nodes, store.NodeImport{ID: nodeID, Type: "file", Title: path, Confidence: "verified", EvidenceIDs: []string{evidenceID}})
		pathIndex = append(pathIndex, store.PathIndexImport{ID: fmt.Sprintf("P-%03d", i+1), Path: path, NodeID: nodeID, Relation: "owns", Confidence: "verified", EvidenceID: evidenceID})
	}
	_, err = st.ImportGeneration(context.Background(), store.ImportInput{
		GenerationID:  "GEN-0001",
		Kind:          "full",
		SourceCommit:  "abc123",
		Evidence:      evidence,
		Nodes:         nodes,
		PathIndex:     pathIndex,
		Rejections:    []store.RowDecision{},
		MergeRecords:  []store.MergeRecord{},
		Observations:  []store.ObservationImport{},
		Edges:         []store.EdgeImport{},
	})
	if err != nil {
		t.Fatal(err)
	}
}

func writeScanPackageWithUniverse(t *testing.T, paths rt.Paths, included []string, criticality map[string]string, indexed []string) {
	t.Helper()
	workbench := filepath.Join(paths.RuntimeDir, "workbench")
	if err := os.MkdirAll(filepath.Join(paths.RuntimeDir, "evidence"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Join(paths.RuntimeDir, "provisional"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Join(workbench, "scan-packets"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Join(workbench, "worker-results"), 0o755); err != nil {
		t.Fatal(err)
	}
	candidateUniverse := []map[string]any{}
	dispositions := map[string]string{}
	reasons := map[string]string{}
	source := map[string]string{}
	for _, path := range included {
		candidateUniverse = append(candidateUniverse, map[string]any{"path": path, "disposition": "deep_read", "decision_source": "git"})
		dispositions[path] = "deep_read"
		reasons[path] = "test"
		source[path] = "git"
	}
	coverageRows := []map[string]any{}
	workerCoverageRows := []map[string]any{}
	nodeRows := []map[string]any{}
	for i, path := range indexed {
		evidenceID := fmt.Sprintf("E-%03d", i+1)
		writeJSONFileForBuildTest(t, filepath.Join(paths.RuntimeDir, "evidence", evidenceID+".json"), map[string]any{"id": evidenceID, "source_kind": "file", "source_path": path, "commit_sha": "abc123", "span": "L1", "extractor": "test", "content_hash": "hash"})
		coverageRows = append(coverageRows, map[string]any{"path": path})
		workerCoverageRows = append(workerCoverageRows, map[string]any{"path": path, "outcome": "read", "evidence_ids": []string{evidenceID}})
		nodeRows = append(nodeRows, map[string]any{"id": fmt.Sprintf("N-%03d", i+1), "type": "file", "title": path, "paths": []string{path}, "evidence_ids": []string{evidenceID}, "confidence": "verified"})
	}
	writeJSONFileForBuildTest(t, filepath.Join(paths.RuntimeDir, "provisional", "nodes.json"), map[string]any{"nodes": nodeRows})
	writeJSONFileForBuildTest(t, filepath.Join(paths.RuntimeDir, "provisional", "edges.json"), map[string]any{"edges": []map[string]any{}})
	writeJSONFileForBuildTest(t, filepath.Join(paths.RuntimeDir, "provisional", "observations.json"), map[string]any{"observations": []map[string]any{}})
	writeJSONFileForBuildTest(t, filepath.Join(paths.RuntimeDir, "coverage.json"), map[string]any{"rows": coverageRows})
	writeJSONFileForBuildTest(t, filepath.Join(workbench, "repository-universe.json"), map[string]any{"schema_version": 1, "candidate_universe": candidateUniverse, "included_paths": included, "excluded_paths": []string{}, "ambiguous_paths": []string{}, "dispositions": dispositions, "criticality": criticality, "classification_reasons": reasons, "decision_source": source})
	writeJSONFileForBuildTest(t, filepath.Join(workbench, "coverage-ledger.json"), map[string]any{"rows": coverageRows, "open_gaps": []map[string]any{}})
	writeJSONFileForBuildTest(t, filepath.Join(workbench, "scan-queue.json"), map[string]any{"packets": []map[string]any{{"packet_id": "lane-1", "state": "accepted", "assigned_paths": indexed, "result_handoff_path": ".specify/project-cognition/workbench/worker-results/lane-1.json", "next_action": "none"}}})
	writeJSONFileForBuildTest(t, filepath.Join(workbench, "handoff-ledger.json"), map[string]any{"events": []map[string]any{{"event_id": "return-1", "packet_id": "lane-1", "event_type": "returned", "worker_result_path": ".specify/project-cognition/workbench/worker-results/lane-1.json", "created_at": "2026-05-26T00:00:00Z"}}})
	writeJSONFileForBuildTest(t, filepath.Join(workbench, "worker-results", "lane-1.json"), map[string]any{"packet_id": "lane-1", "assigned_paths": indexed, "paths_read": indexed, "ledger": map[string]any{"todo": []string{}, "doing": []string{}, "done": indexed, "blocked": []string{}, "overflow": []string{}}, "coverage": workerCoverageRows, "confidence": "high", "acceptance": "pass"})
	if err := os.WriteFile(filepath.Join(workbench, "scan-packets", "lane-1.md"), []byte("# Lane 1\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(workbench, "map-scan.md"), []byte("# Map Scan\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(workbench, "coverage-ledger.md"), []byte("# Coverage Ledger\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(workbench, "map-state.md"), []byte("# Map State\n"), 0o644); err != nil {
		t.Fatal(err)
	}
}
```

Add imports `encoding/json` and `fmt` if missing, and this helper:

```go
func writeJSONFileForBuildTest(t *testing.T, path string, payload any) {
	t.Helper()
	data, err := json.Marshal(payload)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, append(data, '\n'), 0o644); err != nil {
		t.Fatal(err)
	}
}
```

Add:

```go
func hasValidationWarning(warnings []string, want string) bool {
	for _, warning := range warnings {
		if strings.Contains(warning, want) {
			return true
		}
	}
	return false
}
```

- [ ] **Step 3: Run tests to verify RED**

```powershell
go test ./tools/project-cognition/internal/validation -run "TestValidateBuildBlocksCriticalAndImportantMissingPathIndex|TestValidateBuildWarnsBelowNinetyPercentAndFailsBelowSeventyPercent|TestValidateBuildFailsBelowSeventyPercentRatio" -count=1
```

Expected: FAIL because sparse gates are not implemented.

- [ ] **Step 4: Export path-index requirements from scanartifacts**

Add to `scanartifacts.go`:

```go
type PathIndexRequirements struct {
	IncludedPaths                  []string
	ExcludedPaths                  []string
	AcceptedNonblockingGapPaths    []string
	IndexRequiredPaths             []string
	CriticalIndexRequiredPaths      []string
	ImportantIndexRequiredPaths     []string
	CanonicalNodePathCount          int
	CompatibilityDerivedPathCount   int
}

func LoadPathIndexRequirements(paths rt.Paths) (PathIndexRequirements, []string) {
	result := newResult(nil)
	boundary := loadBoundary(paths, &result)
	accepted := acceptedNonblockingGapPaths(paths, boundary)
	canonical, compatibility := nodePathCountsFromFiles(paths)
	req := PathIndexRequirements{
		IncludedPaths:                sortedKeys(boundary.IncludedPaths),
		ExcludedPaths:                sortedKeys(boundary.ExcludedPaths),
		AcceptedNonblockingGapPaths:  sortedKeys(accepted),
		CanonicalNodePathCount:        canonical,
		CompatibilityDerivedPathCount: compatibility,
	}
	for path := range boundary.IncludedPaths {
		if boundary.ExcludedPaths[path] || accepted[path] {
			continue
		}
		req.IndexRequiredPaths = append(req.IndexRequiredPaths, path)
		switch boundary.Criticality[path] {
		case "critical":
			req.CriticalIndexRequiredPaths = append(req.CriticalIndexRequiredPaths, path)
		case "important":
			req.ImportantIndexRequiredPaths = append(req.ImportantIndexRequiredPaths, path)
		}
	}
	sort.Strings(req.IndexRequiredPaths)
	sort.Strings(req.CriticalIndexRequiredPaths)
	sort.Strings(req.ImportantIndexRequiredPaths)
	return req, result.Errors
}

func sortedKeys(values map[string]bool) []string {
	out := make([]string, 0, len(values))
	for key := range values {
		out = append(out, key)
	}
	sort.Strings(out)
	return out
}

func nodePathCountsFromFiles(paths rt.Paths) (int, int) {
	pkg := Package{Identities: newIdentitySet()}
	result := newResult(nil)
	loadNodes(paths, &pkg, &result)
	return nodePathCounts(pkg.Nodes)
}
```

- [ ] **Step 5: Create reusable sparse gate package**

Create `tools/project-cognition/internal/buildgate/sparse.go`:

```go
package buildgate

import (
	"database/sql"
	"fmt"
	"strings"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/scanartifacts"
)

const (
	pathIndexHardThreshold = 0.70
	pathIndexWarnThreshold = 0.90
)

type SparseResult struct {
	Details  map[string]any
	Errors   []string
	Warnings []string
}

func ValidateSparsePathIndex(paths rt.Paths, db *sql.DB, generationID string) SparseResult {
	details := map[string]any{}
	errors := []string{}
	warnings := []string{}
	req, reqErrors := scanartifacts.LoadPathIndexRequirements(paths)
	if len(reqErrors) > 0 {
		return SparseResult{Details: details, Errors: reqErrors, Warnings: warnings}
	}
	indexed, err := activePathIndexSet(db, generationID)
	if err != nil {
		return SparseResult{Details: details, Errors: []string{err.Error()}, Warnings: warnings}
	}
	details["included_paths_count"] = len(req.IncludedPaths)
	details["index_required_paths_count"] = len(req.IndexRequiredPaths)
	details["canonical_node_path_count"] = req.CanonicalNodePathCount
	details["compatibility_derived_node_path_count"] = req.CompatibilityDerivedPathCount
	details["accepted_nonblocking_gap_paths"] = req.AcceptedNonblockingGapPaths
	if len(req.IndexRequiredPaths) == 0 {
		details["path_index_to_included_ratio"] = 1.0
		return SparseResult{Details: details, Errors: errors, Warnings: warnings}
	}
	indexedRequired := 0
	for _, path := range req.IndexRequiredPaths {
		if indexed[path] {
			indexedRequired++
		}
	}
	ratio := float64(indexedRequired) / float64(len(req.IndexRequiredPaths))
	details["path_index_to_included_ratio"] = ratio
	for _, path := range req.CriticalIndexRequiredPaths {
		if !indexed[path] {
			errors = append(errors, "critical_missing_path_index: "+path)
		}
	}
	for _, path := range req.ImportantIndexRequiredPaths {
		if !indexed[path] {
			errors = append(errors, "important_missing_path_index: "+path)
		}
	}
	if ratio < pathIndexHardThreshold {
		errors = append(errors, fmt.Sprintf("path_index_to_included_ratio %.2f is below hard threshold %.2f", ratio, pathIndexHardThreshold))
	} else if ratio < pathIndexWarnThreshold {
		warnings = append(warnings, fmt.Sprintf("path_index_to_included_ratio %.2f is below warning threshold %.2f", ratio, pathIndexWarnThreshold))
	}
	return SparseResult{Details: details, Errors: errors, Warnings: warnings}
}

func activePathIndexSet(db *sql.DB, generationID string) (map[string]bool, error) {
	rows, err := db.Query("SELECT path FROM path_index WHERE generation_id = ?", generationID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	indexed := map[string]bool{}
	for rows.Next() {
		var path string
		if err := rows.Scan(&path); err != nil {
			return nil, err
		}
		indexed[canonicalPath(path)] = true
	}
	return indexed, rows.Err()
}

func canonicalPath(value string) string {
	normalized := strings.TrimSpace(strings.ReplaceAll(value, "\\", "/"))
	for strings.HasPrefix(normalized, "./") {
		normalized = strings.TrimPrefix(normalized, "./")
	}
	return normalized
}
```

- [ ] **Step 6: Call sparse gate from `validateGraphStore`**

In `validation/build.go`, import:

```go
"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/buildgate"
```

After `pathCount` is computed and zero count is checked, add:

```go
sparse := buildgate.ValidateSparsePathIndex(paths, db, activeGenerationID)
for key, value := range sparse.Details {
	details[key] = value
}
errors = append(errors, sparse.Errors...)
details["sparse_path_index_warnings"] = sparse.Warnings
```

In `ValidateBuild`, after `graphDetails, graphErrors := validateGraphStore(...)`, append any detail warnings:

```go
if values, ok := graphDetails["sparse_path_index_warnings"].([]string); ok {
	payload.Warnings = append(payload.Warnings, values...)
	delete(graphDetails, "sparse_path_index_warnings")
}
```

- [ ] **Step 7: Run targeted tests**

```powershell
go test ./tools/project-cognition/internal/validation -run "TestValidateBuildBlocksCriticalAndImportantMissingPathIndex|TestValidateBuildWarnsBelowNinetyPercentAndFailsBelowSeventyPercent|TestValidateBuildFailsBelowSeventyPercentRatio" -count=1
```

Expected: PASS.

- [ ] **Step 8: Commit**

```powershell
git add tools/project-cognition/internal/scanartifacts/scanartifacts.go tools/project-cognition/internal/buildgate/sparse.go tools/project-cognition/internal/validation/build.go tools/project-cognition/internal/validation/build_test.go
git commit -m "feat(cognition): gate sparse path indexes"
```

## Task 6: Prevent Ready Publication When Sparse Gates Fail

**Files:**
- Modify: `tools/project-cognition/internal/build/build_test.go`
- Modify: `tools/project-cognition/internal/build/build.go`
- Modify: `tools/project-cognition/internal/buildgate/sparse.go`

- [ ] **Step 1: Write failing build publication test**

Add to `build_test.go`:

```go
func TestRunDoesNotPublishReadyStatusWhenSparsePathIndexGateFails(t *testing.T) {
	paths := writeMinimalScanPackage(t)
	writeJSON(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), map[string]any{
		"schema_version": 1,
		"candidate_universe": []map[string]any{
			{"path": "src/app.go", "disposition": "deep_read", "decision_source": "git"},
			{"path": "src/missing.go", "disposition": "deep_read", "decision_source": "git"},
		},
		"included_paths": []string{"src/app.go", "src/missing.go"},
		"excluded_paths": []string{},
		"ambiguous_paths": []string{},
		"dispositions": map[string]string{"src/app.go": "deep_read", "src/missing.go": "deep_read"},
		"criticality": map[string]string{"src/app.go": "important", "src/missing.go": "important"},
		"classification_reasons": map[string]string{"src/app.go": "source", "src/missing.go": "source"},
		"decision_source": map[string]string{"src/app.go": "git", "src/missing.go": "git"},
	})

	payload, err := Run(paths)
	if err != nil {
		t.Fatalf("Run() error = %v", err)
	}
	if payload.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", payload.Status, payload.Errors)
	}
	if !containsBuildError(payload.Errors, "important_missing_path_index: src/missing.go") {
		t.Fatalf("Errors = %#v, want sparse path-index gate error", payload.Errors)
	}
	status, statusErr := rt.ReadStatus(paths)
	if statusErr == nil && status.GraphReady {
		t.Fatalf("status.GraphReady = true, want not ready after sparse gate failure: %#v", status)
	}
}
```

Add helper:

```go
func containsBuildError(errors []string, want string) bool {
	for _, err := range errors {
		if strings.Contains(err, want) {
			return true
		}
	}
	return false
}
```

- [ ] **Step 2: Run test to verify RED**

```powershell
go test ./tools/project-cognition/internal/build -run TestRunDoesNotPublishReadyStatusWhenSparsePathIndexGateFails -count=1
```

Expected: FAIL because `Run` writes ready status before sparse build validation.

- [ ] **Step 3: Call sparse gate before writing status**

Import buildgate in `build.go`:

```go
"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/buildgate"
```

After identity reconciliation passes and before creating `status := rt.DefaultStatus(paths)`, add:

```go
sparse := buildgate.ValidateSparsePathIndex(paths, st.DB(), generationID)
if len(sparse.Errors) > 0 {
	payload.Status = "blocked"
	payload.Readiness = rt.BlockedReadiness
	payload.Errors = append(payload.Errors, sparse.Errors...)
	payload.Warnings = append(payload.Warnings, sparse.Warnings...)
	return payload, nil
}
payload.Warnings = append(payload.Warnings, sparse.Warnings...)
```

- [ ] **Step 4: Run targeted test**

```powershell
go test ./tools/project-cognition/internal/build -run TestRunDoesNotPublishReadyStatusWhenSparsePathIndexGateFails -count=1
```

Expected: PASS.

- [ ] **Step 5: Run build and validation packages**

```powershell
go test ./tools/project-cognition/internal/build ./tools/project-cognition/internal/validation -count=1
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add tools/project-cognition/internal/build/build.go tools/project-cognition/internal/build/build_test.go
git commit -m "fix(cognition): gate ready status publication"
```

## Task 7: Update Workflow Templates And Template Tests

**Files:**
- Modify: `templates/commands/map-scan.md`
- Modify: `templates/commands/map-build.md`
- Modify: `templates/command-partials/map-scan/shell.md`
- Modify: `templates/command-partials/map-build/shell.md`
- Modify: `templates/project-handbook-template.md`
- Modify: `tests/test_map_scan_build_template_guidance.py`

- [ ] **Step 1: Write failing template assertions**

Add to `test_map_scan_template_defines_complete_scan_package_contract`:

```python
    assert ".specify/project-cognition/workbench/scan-queue.json" in content
    assert ".specify/project-cognition/workbench/handoff-ledger.json" in content
    assert "leader receives worker result" in lowered
    assert "leader reads durable scan state" in lowered
    assert "leader updates queue, coverage, and handoff ledgers" in lowered
    assert "acceptance=fail_gap" in lowered
    assert 'coverage[].outcome="overflow"' in lowered
    assert "top-level `outcome`" in lowered
    assert "legacy alias" in lowered
    assert "accepted_nonblocking_gap_paths" in content
```

Add to `test_map_build_template_refuses_incomplete_scan_packages`:

```python
    assert ".specify/project-cognition/workbench/scan-queue.json" in content
    assert ".specify/project-cognition/workbench/handoff-ledger.json" in content
    assert "path_index_to_included_ratio" in content
    assert "accepted_nonblocking_gap_paths" in content
    assert "must not set `freshness=ready`" in lowered
    assert "must not set `graphready=true`" in lowered
```

- [ ] **Step 2: Run tests to verify RED**

```powershell
pytest tests/test_map_scan_build_template_guidance.py -q
```

Expected: FAIL with missing phrases.

- [ ] **Step 3: Update map-scan output contract**

In `templates/commands/map-scan.md`, add these bullets under `## Output Contract`:

```markdown
- `.specify/project-cognition/workbench/scan-queue.json`
- `.specify/project-cognition/workbench/handoff-ledger.json`
```

Under `## Project Cognition Workbench State Protocol`, add:

```markdown
- `scan-queue.json` is the leader-owned scheduler queue. Every `scan-packets/<packet-id>.md` file must have exactly one queue row.
- `handoff-ledger.json` records every dispatch and return event. Every `worker-results/<packet-id>.json` file must have a matching queue row and return event.
- The leader loop is: leader receives worker result, leader reads durable scan state, leader validates handoff quality, leader updates queue, coverage, and handoff ledgers, leader plans next packets, and leader dispatches the next bounded wave.
- Worker packet acceptance is separate from path coverage outcome. If a packet exceeds budget, the worker returns `acceptance=fail_gap`, marks affected paths as `coverage[].outcome="overflow"`, and includes split recommendations.
- New worker results must write top-level `acceptance`. Top-level `outcome` is a legacy alias only and must not appear in generated worker prompt examples.
- `accepted_nonblocking_gap_paths` contains only low-risk paths with owner, reason, evidence expectation, revisit condition, and `low_risk_open_gap` status.
```

Replace the existing sentence:

```markdown
- If assigned paths do not fit in context, the subagent must return `overflow` or `blocked`; the leader must split and redispatch or record an open gap.
```

with:

```markdown
- If assigned paths do not fit in context, the subagent must return `acceptance=fail_gap`, mark path-level `coverage[].outcome="overflow"` or `coverage[].outcome="blocked"`, and include split or recovery recommendations; the leader records queue state `overflow` or `blocked`.
```

- [ ] **Step 4: Update map-build sparse contract**

In `templates/commands/map-build.md`, add scan queue and handoff ledger to `## Required Inputs`:

```markdown
- `.specify/project-cognition/workbench/scan-queue.json`
- `.specify/project-cognition/workbench/handoff-ledger.json`
```

Under `## Boundary Acceptance`, add:

```markdown
- `path_index_to_included_ratio` must be computed from included paths minus true exclusions and `accepted_nonblocking_gap_paths`.
- Critical and important included paths must remain in the sparse path-index denominator unless they are true repository-universe exclusions.
- `build-from-scan` must not set `Freshness=ready`, `Readiness=query_ready`, or `GraphReady=true` until sparse path-index gates pass.
```

- [ ] **Step 5: Update command partials and handbook template**

In `templates/command-partials/map-scan/shell.md`, add:

```markdown
- [AGENT] Treat `scan-queue.json` and `handoff-ledger.json` as required scan workbench artifacts before `validate-scan`.
```

In `templates/command-partials/map-build/shell.md`, add:

```markdown
- [AGENT] Treat sparse path-index gates as build preflight; do not publish query-ready status when `validate-build` would fail `path_index_to_included_ratio`, critical path, or important path checks.
```

In `templates/project-handbook-template.md`, update the map-scan/build guidance paragraph to include:

```markdown
Stateful first-baseline scans also require `.specify/project-cognition/workbench/scan-queue.json` and `handoff-ledger.json`; build readiness requires sparse `path_index` gates to pass before `status.json` can be query-ready.
```

- [ ] **Step 6: Run template tests**

```powershell
pytest tests/test_map_scan_build_template_guidance.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add templates/commands/map-scan.md templates/commands/map-build.md templates/command-partials/map-scan/shell.md templates/command-partials/map-build/shell.md templates/project-handbook-template.md tests/test_map_scan_build_template_guidance.py
git commit -m "docs(cognition): teach stateful map scan workflow"
```

## Task 8: Align Python Fake Runtime And Hook Surfaces

**Files:**
- Modify: `tests/project_cognition_fake.py`
- Modify: `tests/hooks/test_artifact_hooks.py` if no existing hook test exercises the fake-runtime path

- [ ] **Step 1: Add fake runtime tests through artifact hook if needed**

If `tests/hooks/test_artifact_hooks.py` has no map-scan artifact hook test, add:

```python
def test_map_scan_artifact_hook_blocks_missing_scheduler_artifacts(tmp_path: Path, monkeypatch) -> None:
    install_fake_project_cognition(monkeypatch, tmp_path)
    project = tmp_path / "project"
    cognition = project / ".specify" / "project-cognition"
    (cognition / "evidence").mkdir(parents=True)
    (cognition / "provisional").mkdir()
    (cognition / "workbench" / "scan-packets").mkdir(parents=True)
    (cognition / "workbench" / "worker-results").mkdir()
    (cognition / "status.json").write_text("{}", encoding="utf-8")
    (cognition / "provisional" / "nodes.json").write_text('{"nodes":[]}', encoding="utf-8")
    (cognition / "provisional" / "edges.json").write_text('{"edges":[]}', encoding="utf-8")
    (cognition / "provisional" / "observations.json").write_text('{"observations":[]}', encoding="utf-8")
    (cognition / "coverage.json").write_text('{"rows":[]}', encoding="utf-8")
    (cognition / "workbench" / "coverage-ledger.json").write_text('{"rows":[],"open_gaps":[]}', encoding="utf-8")

    result = validate_artifacts_hook(
        project,
        {"command_name": "map-scan", "feature_dir": str(cognition)},
    )

    assert result.status == "blocked"
    assert any("scan-queue.json" in error for error in result.errors)
    assert any("handoff-ledger.json" in error for error in result.errors)
```

Import `install_fake_project_cognition` and `validate_artifacts_hook` if the file does not already import them.

- [ ] **Step 2: Run hook test to verify RED**

```powershell
pytest tests/hooks/test_artifact_hooks.py -q
```

Expected: FAIL if fake runtime still treats queue and handoff artifacts as optional.

- [ ] **Step 3: Update fake `_validate_scan` required artifacts**

In `tests/project_cognition_fake.py`, add to `required`:

```python
".specify/project-cognition/workbench/scan-queue.json",
".specify/project-cognition/workbench/handoff-ledger.json",
".specify/project-cognition/workbench/worker-results",
```

Add JSON parse checks for:

```python
".specify/project-cognition/workbench/scan-queue.json",
".specify/project-cognition/workbench/handoff-ledger.json",
```

- [ ] **Step 4: Add fake worker acceptance checks**

Inside `_validate_scan`, after coverage ledger parsing, add:

```python
                worker_results_dir = Path.cwd() / ".specify/project-cognition/workbench/worker-results"
                if worker_results_dir.is_dir():
                    for result_path in sorted(worker_results_dir.glob("*.json")):
                        try:
                            result_payload = json.loads(result_path.read_text(encoding="utf-8"))
                        except json.JSONDecodeError as exc:
                            errors.append(f"{result_path.name}: {exc}")
                            continue
                        if not isinstance(result_payload, dict):
                            errors.append(f"{result_path.name} must contain a top-level JSON object")
                            continue
                        acceptance = str(result_payload.get("acceptance") or result_payload.get("outcome") or "").strip()
                        if not acceptance:
                            errors.append(f"packet {result_path.stem} must define acceptance")
                        elif acceptance in {"overflow", "blocked", "repack_required"}:
                            errors.append(f"packet {result_path.stem} has invalid acceptance {acceptance}")
```

- [ ] **Step 5: Add fake sparse build check**

Inside `_validate_build`, after `path_count` is computed, add:

```python
                                universe_path = Path.cwd() / ".specify/project-cognition/workbench/repository-universe.json"
                                if universe_path.exists():
                                    try:
                                        universe = json.loads(universe_path.read_text(encoding="utf-8"))
                                    except json.JSONDecodeError as exc:
                                        errors.append(f".specify/project-cognition/workbench/repository-universe.json: {exc}")
                                    else:
                                        included = universe.get("included_paths", []) if isinstance(universe, dict) else []
                                        if isinstance(included, list) and len(included) > 0:
                                            ratio = float(path_count) / float(len(included))
                                            if ratio < 0.70:
                                                errors.append(f"path_index_to_included_ratio {ratio:.2f} is below hard threshold 0.70")
```

- [ ] **Step 6: Run fake/hook tests**

```powershell
pytest tests/hooks/test_artifact_hooks.py tests/contract/test_hook_cli_surface.py tests/hooks/test_preflight_hooks.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add tests/project_cognition_fake.py tests/hooks/test_artifact_hooks.py
git commit -m "test(cognition): align fake runtime scan gates"
```

## Task 9: Final Verification

**Files:**
- No source edits expected unless verification finds a regression.

- [ ] **Step 1: Run Go runtime tests**

```powershell
go test ./tools/project-cognition/... -count=1
```

Expected: PASS.

- [ ] **Step 2: Run focused Python tests**

```powershell
pytest tests/test_map_scan_build_template_guidance.py tests/test_map_runtime_template_guidance.py tests/test_project_cognition_launcher_rendering.py tests/hooks/test_artifact_hooks.py tests/contract/test_hook_cli_surface.py -q
```

Expected: PASS.

- [ ] **Step 3: Run integration base template tests**

```powershell
pytest tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_base_toml.py -q
```

Expected: PASS.

- [ ] **Step 4: Inspect status**

```powershell
git status --short
```

Expected: clean after commits.

- [ ] **Step 5: Review commit history**

```powershell
git log --oneline -8
```

Expected: commits for scheduler validation, acceptance contract, accepted gap semantics, node path diagnostics, sparse build gates, ready publication, template guidance, and fake runtime alignment.

## Spec Coverage Self-Review

- Durable artifacts: Task 1 makes `scan-queue.json` and `handoff-ledger.json` required and validates queue/result/handoff relationships.
- Packet acceptance vs path outcome: Task 2 removes implicit packet `pass`, preserves legacy `outcome` only as a warning alias, and rejects packet-level `overflow`.
- Accepted gap denominator: Task 3 constrains accepted nonblocking gaps to low-risk paths with required metadata.
- Compatibility-derived paths: Task 4 reports canonical and compatibility-derived node path counts.
- Sparse path-index gates: Task 5 adds ratio, critical, and important checks.
- Ready publication order: Task 6 blocks query-ready status before sparse gates pass.
- Prompt/template contract: Task 7 updates generated workflow surfaces.
- Fake runtime and hook alignment: Task 8 mirrors the Go runtime behavior for Python tests.
- Verification: Task 9 covers Go runtime, template tests, hook tests, and integration base surfaces.
