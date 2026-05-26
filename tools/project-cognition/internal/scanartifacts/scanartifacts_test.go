package scanartifacts

import (
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"testing"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
)

func TestValidateArtifactsDoesNotRequireStatusJSON(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "ok" {
		t.Fatalf("Status = %q, want ok; errors=%#v", result.Status, result.Errors)
	}
	if !containsString(result.CheckedPaths, ".specify/project-cognition/workbench/repository-universe.json") {
		t.Fatalf("CheckedPaths = %#v, want repository-universe.json", result.CheckedPaths)
	}
	for _, checked := range result.CheckedPaths {
		if strings.Contains(checked, ".specify/project-map") {
			t.Fatalf("CheckedPaths = %#v, must not include .specify/project-map", result.CheckedPaths)
		}
	}
}

func TestValidateArtifactsReportsUTF8BOM(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "coverage.json"), append([]byte{0xEF, 0xBB, 0xBF}, []byte(`{"rows":[{"path":"src/app.go"}]}`)...))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "coverage.json contains UTF-8 BOM") {
		t.Fatalf("Errors = %#v, want UTF-8 BOM error", result.Errors)
	}
}

func TestValidateArtifactsRequiresStatusJSONObjectWhenRequested(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "status.json"), []byte("[]\n"))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: true})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "status.json must contain a top-level JSON object") {
		t.Fatalf("Errors = %#v, want status object error", result.Errors)
	}
}

func TestLoadRequiresSchedulerArtifacts(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	removeFile(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"))
	removeFile(t, filepath.Join(paths.RuntimeDir, "workbench", "handoff-ledger.json"))

	_, result := Load(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	for _, want := range []string{
		"missing .specify/project-cognition/workbench/scan-queue.json",
		"missing .specify/project-cognition/workbench/handoff-ledger.json",
	} {
		if !containsError(result.Errors, want) {
			t.Fatalf("Errors = %#v, want %q", result.Errors, want)
		}
	}
}

func TestLoadRejectsWorkerResultWithoutQueueReturn(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-packets", "p1.md"), []byte("# P1\n"))
	writeWorkerResult(t, paths, "p1.json", `{
		"packet_id":"p1",
		"family_id":"app",
		"assigned_paths":["src/app.go"],
		"paths_read":["src/app.go"],
		"ledger":{"todo":[],"doing":[],"done":["src/app.go"],"blocked":[],"overflow":[]},
		"coverage":[{"path":"src/app.go","outcome":"read","evidence_ids":["E-001"]}],
		"confidence":"high",
		"acceptance":"pass"
	}`)

	_, result := Load(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	for _, want := range []string{
		"worker result p1 has no matching scan-queue row",
		"worker result p1 has no matching return event in handoff-ledger.json",
	} {
		if !containsError(result.Errors, want) {
			t.Fatalf("Errors = %#v, want %q", result.Errors, want)
		}
	}
}

func TestLoadRejectsQueueWorkerAssignedPathMismatch(t *testing.T) {
	for _, tc := range []struct {
		name              string
		queueAssignedJSON string
		wantExtra         string
	}{
		{
			name:              "empty accepted queue assignment",
			queueAssignedJSON: `[]`,
			wantExtra:         "scan-queue packet lane-1 accepted state requires assigned_paths",
		},
		{
			name:              "different queue assignment",
			queueAssignedJSON: `["src/other.go"]`,
		},
	} {
		t.Run(tc.name, func(t *testing.T) {
			paths := scanArtifactTestPaths(t)
			writeMinimalScanPackage(t, paths)
			writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"), []byte(`{
				"rows":[{
					"packet_id":"lane-1",
					"state":"accepted",
					"assigned_paths":`+tc.queueAssignedJSON+`,
					"result_handoff_path":".specify/project-cognition/workbench/worker-results/lane-1.json"
				}]
			}`+"\n"))

			_, result := Load(paths, ValidateOptions{RequireStatusJSON: false})

			if result.Status != "blocked" {
				t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
			}
			if !containsError(result.Errors, "scan-queue packet lane-1 assigned_paths must match worker result assigned_paths") {
				t.Fatalf("Errors = %#v, want queue/worker assigned_paths mismatch error", result.Errors)
			}
			if tc.wantExtra != "" && !containsError(result.Errors, tc.wantExtra) {
				t.Fatalf("Errors = %#v, want %q", result.Errors, tc.wantExtra)
			}
		})
	}
}

func TestLoadRejectsHandoffReturnWrongWorkerResultPath(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "handoff-ledger.json"), []byte(`{"events":[
		{"event_id":"dispatch-1","packet_id":"lane-1","event_type":"dispatched","created_at":"2026-05-26T00:00:00Z"},
		{"event_id":"return-1","packet_id":"lane-1","event_type":"returned","worker_result_path":".specify/project-cognition/workbench/worker-results/wrong.json","created_at":"2026-05-26T00:01:00Z"}
	]}`+"\n"))

	_, result := Load(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "handoff-ledger return for packet lane-1 worker_result_path") {
		t.Fatalf("Errors = %#v, want handoff worker_result_path error", result.Errors)
	}
}

func TestLoadRejectsHandoffReturnMissingWorkerResultPath(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "handoff-ledger.json"), []byte(`{"events":[
		{"event_id":"dispatch-1","packet_id":"lane-1","event_type":"dispatched","created_at":"2026-05-26T00:00:00Z"},
		{"event_id":"return-1","packet_id":"lane-1","event_type":"returned","created_at":"2026-05-26T00:01:00Z"}
	]}`+"\n"))

	_, result := Load(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "handoff-ledger return for packet lane-1 worker_result_path") {
		t.Fatalf("Errors = %#v, want handoff worker_result_path error", result.Errors)
	}
}

func TestLoadRejectsHandoffReturnWrongResultHandoffPathAlias(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "handoff-ledger.json"), []byte(`{"events":[
		{"event_id":"dispatch-1","packet_id":"lane-1","event_type":"dispatched","created_at":"2026-05-26T00:00:00Z"},
		{"event_id":"return-1","packet_id":"lane-1","event_type":"returned","result_handoff_path":".specify/project-cognition/workbench/worker-results/wrong.json","created_at":"2026-05-26T00:01:00Z"}
	]}`+"\n"))

	_, result := Load(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "handoff-ledger return for packet lane-1 worker_result_path") {
		t.Fatalf("Errors = %#v, want handoff worker result path error", result.Errors)
	}
}

func TestLoadRejectsHandoffReturnWithConflictingResultPathAliases(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "handoff-ledger.json"), []byte(`{"events":[
		{"event_id":"dispatch-1","packet_id":"lane-1","event_type":"dispatched","created_at":"2026-05-26T00:00:00Z"},
		{"event_id":"return-1","packet_id":"lane-1","event_type":"returned","worker_result_path":".specify/project-cognition/workbench/worker-results/lane-1.json","result_handoff_path":".specify/project-cognition/workbench/worker-results/wrong.json","created_at":"2026-05-26T00:01:00Z"}
	]}`+"\n"))

	_, result := Load(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "handoff-ledger return for packet lane-1 result_handoff_path") {
		t.Fatalf("Errors = %#v, want handoff result_handoff_path error", result.Errors)
	}
}

func TestLoadRejectsHandoffReturnWithoutWorkerResultArtifact(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	removeFile(t, filepath.Join(paths.RuntimeDir, "workbench", "worker-results", "lane-1.json"))
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "handoff-ledger.json"), []byte(`{"events":[
		{"event_id":"dispatch-1","packet_id":"lane-1","event_type":"dispatched","created_at":"2026-05-26T00:00:00Z"},
		{"event_id":"return-1","packet_id":"lane-1","event_type":"returned","worker_result_path":".specify/project-cognition/workbench/worker-results/lane-1.json","created_at":"2026-05-26T00:01:00Z"}
	]}`+"\n"))

	_, result := Load(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "handoff-ledger return for packet lane-1 worker_result_path artifact is missing") {
		t.Fatalf("Errors = %#v, want missing handoff artifact error", result.Errors)
	}
}

func TestLoadRejectsDuplicateValidHandoffReturns(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "handoff-ledger.json"), []byte(`{"events":[
		{"event_id":"dispatch-1","packet_id":"lane-1","event_type":"dispatched","created_at":"2026-05-26T00:00:00Z"},
		{"event_id":"return-1","packet_id":"lane-1","event_type":"returned","worker_result_path":".specify/project-cognition/workbench/worker-results/lane-1.json","created_at":"2026-05-26T00:01:00Z"},
		{"event_id":"return-2","packet_id":"lane-1","event_type":"returned","result_handoff_path":".specify/project-cognition/workbench/worker-results/lane-1.json","created_at":"2026-05-26T00:02:00Z"}
	]}`+"\n"))

	_, result := Load(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "handoff-ledger packet lane-1 has duplicate return events") {
		t.Fatalf("Errors = %#v, want duplicate return event error", result.Errors)
	}
}

func TestLoadRejectsDuplicateHandoffReturnWithMissingPath(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "handoff-ledger.json"), []byte(`{"events":[
		{"event_id":"dispatch-1","packet_id":"lane-1","event_type":"dispatched","created_at":"2026-05-26T00:00:00Z"},
		{"event_id":"return-1","packet_id":"lane-1","event_type":"returned","worker_result_path":".specify/project-cognition/workbench/worker-results/lane-1.json","created_at":"2026-05-26T00:01:00Z"},
		{"event_id":"return-2","packet_id":"lane-1","event_type":"returned","created_at":"2026-05-26T00:02:00Z"}
	]}`+"\n"))

	_, result := Load(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "handoff-ledger return for packet lane-1 worker_result_path") {
		t.Fatalf("Errors = %#v, want handoff worker_result_path error", result.Errors)
	}
}

func TestLoadRejectsAcceptedQueueWithoutCoverageWhenWorkerResultMissing(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	removeFile(t, filepath.Join(paths.RuntimeDir, "workbench", "worker-results", "lane-1.json"))
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json"), []byte(`{
		"rows":[{"path":"docs/guide.md","status":"covered"}],
		"open_gaps":[]
	}`+"\n"))
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"), []byte(`{
		"rows":[{
			"packet_id":"lane-1",
			"state":"accepted",
			"assigned_paths":["src/app.go"],
			"result_handoff_path":".specify/project-cognition/workbench/worker-results/lane-1.json"
		}]
	}`+"\n"))

	_, result := Load(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "scan-queue packet lane-1 accepted state requires accepted coverage for assigned path src/app.go") {
		t.Fatalf("Errors = %#v, want accepted queue coverage error", result.Errors)
	}
}

func TestLoadRejectsAcceptedQueueWithoutCoverage(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json"), []byte(`{
		"rows":[{"path":"docs/guide.md"}],
		"open_gaps":[]
	}`+"\n"))
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"), []byte(`{
		"rows":[{"packet_id":"lane-1","state":"accepted","assigned_paths":["src/app.go"]}]
	}`+"\n"))
	writeWorkerResult(t, paths, "lane-1.json", `{
		"packet_id":"lane-1",
		"family_id":"app",
		"assigned_paths":["src/app.go"],
		"paths_read":[],
		"ledger":{"todo":[],"doing":[],"done":[],"blocked":["src/app.go"],"overflow":[]},
		"coverage":[{"path":"src/app.go","outcome":"blocked"}],
		"acceptance":"fail_gap"
	}`)

	_, result := Load(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "scan-queue packet lane-1 accepted state requires accepted coverage for assigned path src/app.go") {
		t.Fatalf("Errors = %#v, want accepted queue coverage error", result.Errors)
	}
}

func TestLoadRejectsAcceptedQueueWithBlockedOrPartialLedgerRows(t *testing.T) {
	for _, row := range []string{
		`{"path":"src/app.go","status":"blocked"}`,
		`{"path":"src/app.go","coverage_state":"partial"}`,
		`{"path":"src/app.go","outcome":"overflow"}`,
	} {
		t.Run(row, func(t *testing.T) {
			paths := scanArtifactTestPaths(t)
			writeMinimalScanPackage(t, paths)
			writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json"), []byte(`{
				"rows":[`+row+`],
				"open_gaps":[]
			}`+"\n"))

			_, result := Load(paths, ValidateOptions{RequireStatusJSON: false})

			if result.Status != "blocked" {
				t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
			}
			if !containsError(result.Errors, "scan-queue packet lane-1 accepted state requires accepted coverage for assigned path src/app.go") {
				t.Fatalf("Errors = %#v, want accepted queue coverage error", result.Errors)
			}
		})
	}
}

func TestLoadRejectsAcceptedQueueWithBareLedgerRow(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json"), []byte(`{
		"rows":[{"path":"src/app.go"}],
		"open_gaps":[]
	}`+"\n"))

	_, result := Load(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "scan-queue packet lane-1 accepted state requires accepted coverage for assigned path src/app.go") {
		t.Fatalf("Errors = %#v, want accepted queue coverage error", result.Errors)
	}
}

func TestLoadRejectsAcceptedQueueClosedOnlyByAcceptedGap(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json"), []byte(`{
		"rows":[],
		"open_gaps":[{"path":"src/app.go","status":"low_risk_open_gap","owner":"scan","reason":"deferred","evidence_expectation":"non-critical path","revisit_condition":"next scan"}]
	}`+"\n"))

	_, result := Load(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "scan-queue packet lane-1 accepted state requires accepted coverage for assigned path src/app.go") {
		t.Fatalf("Errors = %#v, want accepted queue coverage error", result.Errors)
	}
}

func TestLoadRejectsMalformedOverflowOpenGapMetadata(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"), []byte(`{
		"rows":[{"packet_id":"lane-1","state":"overflow","assigned_paths":["src/app.go"]}]
	}`+"\n"))
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json"), []byte(`{
		"rows":[{"path":"src/app.go"}],
		"open_gaps":[{"packet_id":"lane-1","status":"blocked"}]
	}`+"\n"))

	_, result := Load(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "coverage-ledger open_gaps[0] is missing required metadata") {
		t.Fatalf("Errors = %#v, want malformed open gap error", result.Errors)
	}
}

func TestLoadRejectsOverflowQueueWithUnrelatedValidOpenGap(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"), []byte(`{
		"rows":[{"packet_id":"lane-1","state":"overflow","assigned_paths":["src/app.go"]}]
	}`+"\n"))
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json"), []byte(`{
		"rows":[{"path":"src/app.go","status":"covered"}],
		"open_gaps":[{"owner":"scan","reason":"other packet split","evidence_expectation":"child packet closes src/other.go","revisit_condition":"child packet returns","paths":["src/other.go"],"coverage_state":"low_risk_open_gap"}]
	}`+"\n"))

	_, result := Load(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "scan-queue packet lane-1 state overflow requires an open coverage gap or child packet") {
		t.Fatalf("Errors = %#v, want unclosed queue-state error", result.Errors)
	}
}

func TestLoadRejectsOverflowQueueWithSamePathOpenGapWithoutLineage(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"), []byte(`{
		"rows":[{"packet_id":"lane-1","state":"overflow","assigned_paths":["src/app.go"]}]
	}`+"\n"))
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json"), []byte(`{
		"rows":[{"path":"src/app.go","status":"covered"}],
		"open_gaps":[{"owner":"scan","reason":"packet split","evidence_expectation":"child packet closes src/app.go","revisit_condition":"child packet returns","paths":["src/app.go"],"coverage_state":"low_risk_open_gap"}]
	}`+"\n"))

	_, result := Load(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "scan-queue packet lane-1 state overflow requires an open coverage gap or child packet") {
		t.Fatalf("Errors = %#v, want unclosed queue-state error", result.Errors)
	}
}

func TestLoadRejectsOverflowQueueWithSiblingParentOpenGap(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-packets", "lane-2.md"), []byte("# Lane 2\n"))
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"), []byte(`{
		"rows":[
			{"packet_id":"lane-1","state":"accepted","assigned_paths":["src/app.go"],"parent_packet_id":"parent-1","result_handoff_path":".specify/project-cognition/workbench/worker-results/lane-1.json"},
			{"packet_id":"lane-2","state":"overflow","assigned_paths":["src/other.go"],"parent_packet_id":"parent-1"}
		]
	}`+"\n"))
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json"), []byte(`{
		"rows":[{"path":"src/app.go","status":"covered"}],
		"open_gaps":[{"parent_packet_id":"parent-1","owner":"scan","reason":"sibling packet split","evidence_expectation":"child packet closes src/other.go","revisit_condition":"child packet returns","paths":["src/other.go"],"coverage_state":"low_risk_open_gap"}]
	}`+"\n"))

	_, result := Load(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "scan-queue packet lane-2 state overflow requires an open coverage gap or child packet") {
		t.Fatalf("Errors = %#v, want lane-2 unclosed queue-state error", result.Errors)
	}
}

func TestLoadAcceptsOverflowQueueWithChildPacketButNoOpenGap(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-packets", "lane-2.md"), []byte("# Lane 2\n"))
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"), []byte(`{
		"rows":[
			{"packet_id":"lane-1","state":"overflow","assigned_paths":["src/app.go"]},
			{"packet_id":"lane-2","state":"accepted","assigned_paths":["src/app.go"],"parent_packet_id":"lane-1"}
		]
	}`+"\n"))
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json"), []byte(`{
		"rows":[{"path":"src/app.go","status":"covered"}],
		"open_gaps":[]
	}`+"\n"))

	_, result := Load(paths, ValidateOptions{RequireStatusJSON: false})

	if containsError(result.Errors, "scan-queue packet lane-1 state overflow requires an open coverage gap or child packet") {
		t.Fatalf("Errors = %#v, want no lane-1 unclosed queue-state error", result.Errors)
	}
}

func TestLoadRejectsUnclosedOverflowQueueState(t *testing.T) {
	for _, state := range []string{"overflow", "blocked", "repack_required"} {
		t.Run(state, func(t *testing.T) {
			paths := scanArtifactTestPaths(t)
			writeMinimalScanPackage(t, paths)
			writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"), []byte(`{
				"rows":[{"packet_id":"lane-1","state":"`+state+`","assigned_paths":["src/app.go"]}]
			}`+"\n"))

			_, result := Load(paths, ValidateOptions{RequireStatusJSON: false})

			if result.Status != "blocked" {
				t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
			}
			if !containsError(result.Errors, "scan-queue packet lane-1 state "+state+" requires an open coverage gap or child packet") {
				t.Fatalf("Errors = %#v, want unclosed queue-state error", result.Errors)
			}
		})
	}
}

func TestLoadAcceptsOverflowQueueWithOpenGap(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"), []byte(`{
		"rows":[{"packet_id":"lane-1","state":"overflow","assigned_paths":["src/app.go"]}]
	}`+"\n"))
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json"), []byte(`{
		"rows":[{"path":"src/app.go"}],
		"open_gaps":[{"packet_id":"lane-1","owner":"scan","reason":"packet split","evidence_expectation":"child packet closes src/app.go","revisit_condition":"child packet returns","paths":["src/app.go"],"coverage_state":"low_risk_open_gap"}]
	}`+"\n"))

	_, result := Load(paths, ValidateOptions{RequireStatusJSON: false})

	if containsError(result.Errors, "scan-queue packet lane-1 state overflow requires an open coverage gap or child packet") {
		t.Fatalf("Errors = %#v, want no unclosed queue-state error", result.Errors)
	}
}

func TestLoadAcceptsOverflowQueueWithParentPacketOpenGap(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"), []byte(`{
		"rows":[{"packet_id":"lane-1","state":"overflow","assigned_paths":["src/app.go"]}]
	}`+"\n"))
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json"), []byte(`{
		"rows":[{"path":"src/app.go"}],
		"open_gaps":[{"parent_packet_id":"lane-1","owner":"scan","reason":"packet split","evidence_expectation":"child packet closes src/app.go","revisit_condition":"child packet returns","paths":["src/app.go"],"coverage_state":"low_risk_open_gap"}]
	}`+"\n"))

	_, result := Load(paths, ValidateOptions{RequireStatusJSON: false})

	if containsError(result.Errors, "scan-queue packet lane-1 state overflow requires an open coverage gap or child packet") {
		t.Fatalf("Errors = %#v, want no unclosed queue-state error", result.Errors)
	}
}

func TestLoadAcceptsOverflowQueueWithChildPacketOpenGap(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-packets", "lane-2.md"), []byte("# Lane 2\n"))
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"), []byte(`{
		"rows":[
			{"packet_id":"lane-1","state":"overflow","assigned_paths":["src/app.go"]},
			{"packet_id":"lane-2","state":"accepted","assigned_paths":["src/app.go"],"parent_packet_id":"lane-1"}
		]
	}`+"\n"))
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json"), []byte(`{
		"rows":[{"path":"src/app.go","status":"covered"}],
		"open_gaps":[{"packet_id":"lane-2","owner":"scan","reason":"child packet split","evidence_expectation":"child packet closes src/app.go","revisit_condition":"child packet returns","paths":["src/app.go"],"coverage_state":"low_risk_open_gap"}]
	}`+"\n"))

	_, result := Load(paths, ValidateOptions{RequireStatusJSON: false})

	if containsError(result.Errors, "scan-queue packet lane-1 state overflow requires an open coverage gap or child packet") {
		t.Fatalf("Errors = %#v, want no lane-1 unclosed queue-state error", result.Errors)
	}
}

func TestLoadExtractsIdentitySets(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)

	pkg, result := Load(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "ok" {
		t.Fatalf("Status = %q, want ok; errors=%#v", result.Status, result.Errors)
	}
	assertIdentity(t, pkg.Identities.Evidence, "E-001|src/app.go|hash-app")
	assertIdentity(t, pkg.Identities.Nodes, "N-app")
	assertIdentity(t, pkg.Identities.Edges, "EDGE-app-self|N-app|N-app|owns")
	assertIdentity(t, pkg.Identities.Observations, "OBS-app")
	assertIdentity(t, pkg.Identities.CoveragePaths, "src/app.go")
}

func TestLoadAcceptsSingularEvidenceAndEdgeEndpointAliases(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "evidence", "E-001.json"), []byte(`{
		"evidence_id":"mod-001",
		"source_kind":"file",
		"source_path":"src/app.go",
		"commit_sha":"abc123",
		"span":"L1-L5",
		"extractor":"test",
		"content_hash":"hash-app",
		"attrs":{"language":"go"}
	}`))
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "provisional", "nodes.json"), []byte(`{"nodes":[{
		"id":"N-app",
		"type":"capability",
		"title":"App",
		"confidence":"verified",
		"paths":["src/app.go"],
		"evidence_id":"mod-001",
		"attrs":{"owner":"app"}
	}]}`))
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "provisional", "edges.json"), []byte(`{"edges":[{
		"id":"EDGE-app-self",
		"type":"owns",
		"source":"N-app",
		"target":"N-app",
		"confidence":"verified",
		"evidence_id":"mod-001",
		"attrs":{"relation":"self"}
	}]}`))
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "provisional", "observations.json"), []byte(`{"observations":[{
		"id":"OBS-app",
		"observation_type":"implementation",
		"summary":"App exists",
		"evidence_id":"mod-001",
		"attrs":{"source":"test"}
	}]}`))
	writeWorkerResult(t, paths, "lane-1.json", `{
		"packet_id":"lane-1",
		"family_id":"app",
		"assigned_paths":["src/app.go"],
		"paths_read":["src/app.go"],
		"ledger":{"todo":[],"doing":[],"done":["src/app.go"],"blocked":[],"overflow":[]},
		"coverage":[{"path":"src/app.go","outcome":"read","evidence_id":"mod-001"}],
		"confidence":"high",
		"acceptance":"pass"
	}`)

	pkg, result := Load(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "ok" {
		t.Fatalf("Status = %q, want ok; errors=%#v", result.Status, result.Errors)
	}
	if got := pkg.Evidence[0].ID; got != "mod-001" {
		t.Fatalf("Evidence ID = %q, want mod-001", got)
	}
	if got := strings.Join(pkg.Nodes[0].EvidenceIDs, ","); got != "mod-001" {
		t.Fatalf("Node EvidenceIDs = %q, want mod-001", got)
	}
	if got := pkg.Edges[0].SourceID + "->" + pkg.Edges[0].TargetID; got != "N-app->N-app" {
		t.Fatalf("Edge endpoints = %q, want N-app->N-app", got)
	}
	if got := strings.Join(pkg.Edges[0].EvidenceIDs, ","); got != "mod-001" {
		t.Fatalf("Edge EvidenceIDs = %q, want mod-001", got)
	}
	if got := strings.Join(pkg.Observations[0].EvidenceIDs, ","); got != "mod-001" {
		t.Fatalf("Observation EvidenceIDs = %q, want mod-001", got)
	}
	assertIdentity(t, pkg.Identities.Evidence, "mod-001|src/app.go|hash-app")
	assertIdentity(t, pkg.Identities.Edges, "EDGE-app-self|N-app|N-app|owns")
}

func TestLoadNormalizesDownstreamNaturalScanArtifactFields(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	const pagePath = "desktop/src/pages/ActiveSession.tsx"
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "evidence", "E-001.json"), []byte(`{
		"id":"E-001",
		"source_kind":"file",
		"source_path":"`+pagePath+`",
		"commit_sha":"abc123",
		"span":"L1-L5",
		"extractor":"test",
		"content_hash":"hash-page",
		"attrs_json":{"language":"typescript"}
	}`))
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "provisional", "nodes.json"), []byte(`{"nodes":[{
		"node_id":"NO_ID",
		"kind":"page",
		"label":"Active Session Page",
		"confidence":"medium",
		"evidence_id":"E-001",
		"attrs_json":{"path":"`+pagePath+`","detail":"session UI"}
	}]}`))
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "provisional", "edges.json"), []byte(`{"edges":[{
		"id":"NO_ID",
		"kind":"owns",
		"source_node_id":"`+pagePath+`",
		"target_node_id":"`+pagePath+`",
		"confidence":"medium",
		"evidence_id":"E-001",
		"attrs_json":{"detail":"self ownership"}
	}]}`))
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "provisional", "observations.json"), []byte(`{"observations":["Active session page owns session UI state"]}`))
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "coverage.json"), []byte(`{"coverage":[{"path":"`+pagePath+`"}]}`))
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json"), []byte(`{"rows":[{"path":"`+pagePath+`","status":"covered"}],"open_gaps":[]}`))
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"), []byte(`{
		"packets":[{
			"packet_id":"lane-1",
			"state":"accepted",
			"assigned_paths":["`+pagePath+`"],
			"result_handoff_path":".specify/project-cognition/workbench/worker-results/lane-1.json"
		}]
	}`))
	writeWorkerResult(t, paths, "lane-1.json", `{
		"packet_id":"lane-1",
		"family_id":"desktop",
		"assigned_paths":["`+pagePath+`"],
		"paths_read":["`+pagePath+`"],
		"ledger":{"todo":[],"doing":[],"done":["`+pagePath+`"],"blocked":[],"overflow":[]},
		"coverage":[{"path":"`+pagePath+`","outcome":"read","evidence_id":"E-001"}],
		"confidence":"high",
		"acceptance":"pass"
	}`)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), []byte(`{"rows":[{"path":"`+pagePath+`"}]}`))

	pkg, result := Load(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "ok" {
		t.Fatalf("Status = %q, want ok; errors=%#v", result.Status, result.Errors)
	}
	if len(pkg.Nodes) != 1 {
		t.Fatalf("Nodes = %#v, want one normalized node", pkg.Nodes)
	}
	node := pkg.Nodes[0]
	if node.ID == "" || node.ID == "NO_ID" {
		t.Fatalf("Node ID = %q, want generated stable ID", node.ID)
	}
	if node.Type != "page" || node.Title != "Active Session Page" {
		t.Fatalf("Node = %#v, want kind/label normalized to type/title", node)
	}
	if got := strings.Join(node.Paths, ","); got != pagePath {
		t.Fatalf("Node Paths = %q, want %s", got, pagePath)
	}
	if got := node.Attrs["detail"]; got != "session UI" {
		t.Fatalf("Node Attrs = %#v, want attrs_json detail", node.Attrs)
	}
	if len(pkg.Edges) != 1 || pkg.Edges[0].ID == "" || pkg.Edges[0].ID == "NO_ID" {
		t.Fatalf("Edges = %#v, want generated edge ID", pkg.Edges)
	}
	if got := pkg.Edges[0].SourceID + "->" + pkg.Edges[0].TargetID; got != node.ID+"->"+node.ID {
		t.Fatalf("Edge endpoints = %q, want path endpoints resolved to node ID %s", got, node.ID)
	}
	if len(pkg.Observations) != 1 || pkg.Observations[0].Summary != "Active session page owns session UI state" {
		t.Fatalf("Observations = %#v, want string observation normalized", pkg.Observations)
	}
	if got := strings.Join(pkg.CoveragePaths, ","); got != pagePath {
		t.Fatalf("CoveragePaths = %q, want coverage alias path", got)
	}
}

func TestLoadMergesCoverageRowsAndCompatibilityCoverageArrays(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "coverage.json"), []byte(`{
		"rows":[{"path":"src/app.go"}],
		"coverage":[{"path":"desktop/src/pages/ActiveSession.tsx"}]
	}`))

	pkg, result := Load(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "ok" {
		t.Fatalf("Status = %q, want ok; errors=%#v", result.Status, result.Errors)
	}
	if got := strings.Join(pkg.CoveragePaths, ","); got != "src/app.go,desktop/src/pages/ActiveSession.tsx" {
		t.Fatalf("CoveragePaths = %q, want merged rows and coverage arrays", got)
	}
}

func TestLoadDoesNotMergeCanonicalGraphRowsWithGenericRowsFallback(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "provisional", "nodes.json"), []byte(`{
		"nodes":[{
			"id":"N-canonical",
			"type":"capability",
			"title":"Canonical",
			"confidence":"verified",
			"paths":["src/app.go"]
		}],
		"rows":[{
			"id":"N-generic",
			"type":"capability",
			"title":"Generic",
			"confidence":"verified",
			"paths":["src/generic.go"]
		}]
	}`))

	pkg, result := Load(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "ok" {
		t.Fatalf("Status = %q, want ok; errors=%#v", result.Status, result.Errors)
	}
	if len(pkg.Nodes) != 1 || pkg.Nodes[0].ID != "N-canonical" {
		t.Fatalf("Nodes = %#v, want only canonical nodes array", pkg.Nodes)
	}
}

func TestLoadResolvesPathEdgeEndpointsToOwningNodes(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "provisional", "edges.json"), []byte(`{"edges":[{
		"id":"EDGE-app-path",
		"type":"owns",
		"source":"src/app.go",
		"target":"src/app.go",
		"confidence":"verified",
		"evidence_ids":["E-001"],
		"attrs":{"relation":"self"}
	}]}`))

	pkg, result := Load(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "ok" {
		t.Fatalf("Status = %q, want ok; errors=%#v", result.Status, result.Errors)
	}
	if got := pkg.Edges[0].SourceID + "->" + pkg.Edges[0].TargetID; got != "N-app->N-app" {
		t.Fatalf("Edge endpoints = %q, want N-app->N-app", got)
	}
	assertIdentity(t, pkg.Identities.Edges, "EDGE-app-path|N-app|N-app|owns")
}

func TestLoadKeepsExplicitNodeIDWhenItAlsoMatchesNodePath(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "provisional", "nodes.json"), []byte(`{"nodes":[
		{
			"id":"src/app.go",
			"type":"file",
			"title":"Path Named Node",
			"confidence":"verified",
			"paths":["src/other.go"],
			"evidence_ids":["E-001"],
			"attrs":{"owner":"app"}
		},
		{
			"id":"N-owner",
			"type":"capability",
			"title":"Owner",
			"confidence":"verified",
			"paths":["src/app.go"],
			"evidence_ids":["E-001"],
			"attrs":{"owner":"app"}
		}
	]}`))
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "provisional", "edges.json"), []byte(`{"edges":[{
		"id":"EDGE-explicit-node",
		"type":"owns",
		"source":"src/app.go",
		"target":"src/app.go",
		"confidence":"verified",
		"evidence_ids":["E-001"],
		"attrs":{"relation":"self"}
	}]}`))

	pkg, result := Load(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "ok" {
		t.Fatalf("Status = %q, want ok; errors=%#v", result.Status, result.Errors)
	}
	if got := pkg.Edges[0].SourceID + "->" + pkg.Edges[0].TargetID; got != "src/app.go->src/app.go" {
		t.Fatalf("Edge endpoints = %q, want src/app.go->src/app.go", got)
	}
	assertIdentity(t, pkg.Identities.Edges, "EDGE-explicit-node|src/app.go|src/app.go|owns")
}

func TestValidateArtifactsBlocksOpenGapForAnyOwner(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json"), []byte(`{
		"rows":[{"path":"src/app.go"}],
		"open_gaps":[{"owner":"other","status":"blocked"}]
	}`))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "coverage gap must be resolved") {
		t.Fatalf("Errors = %#v, want blocked coverage gap error", result.Errors)
	}
}

func TestValidateBlocksIncludedCandidateWithoutCoverageOrGap(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), []byte(`{
		"schema_version":1,
		"candidate_universe":[{"path":"src/app.go","disposition":"deep_read","decision_source":"git"},{"path":"src/missing.go","disposition":"deep_read","decision_source":"git"}],
		"included_paths":["src/app.go","src/missing.go"],
		"excluded_paths":[],
		"ambiguous_paths":[],
		"dispositions":{"src/app.go":"deep_read","src/missing.go":"deep_read"},
		"criticality":{"src/app.go":"important","src/missing.go":"important"},
		"classification_reasons":{"src/app.go":"source","src/missing.go":"source"},
		"decision_source":{"src/app.go":"git","src/missing.go":"git"}
	}`))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "repository-universe included path src/missing.go has no coverage row or accepted nonblocking gap") {
		t.Fatalf("Errors = %#v, want missing included path coverage error", result.Errors)
	}
}

func TestValidateBlocksExcludedPathInCoverage(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "coverage.json"), []byte(`{"rows":[{"path":"src/app.go"},{"path":"vendor/lib.go"}]}`))
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), []byte(`{
		"schema_version":1,
		"candidate_universe":[{"path":"src/app.go","disposition":"deep_read","decision_source":"git"},{"path":"vendor/lib.go","disposition":"excluded","decision_source":".cognitionignore"}],
		"included_paths":["src/app.go"],
		"excluded_paths":[{"path":"vendor/lib.go","reason":"vendor","decision_source":".cognitionignore"}],
		"ambiguous_paths":[],
		"dispositions":{"src/app.go":"deep_read","vendor/lib.go":"excluded"},
		"criticality":{"src/app.go":"important","vendor/lib.go":"low_risk"},
		"classification_reasons":{"src/app.go":"source","vendor/lib.go":"vendor"},
		"decision_source":{"src/app.go":"git","vendor/lib.go":".cognitionignore"}
	}`))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "excluded path vendor/lib.go must not appear in coverage.json") {
		t.Fatalf("Errors = %#v, want excluded coverage error", result.Errors)
	}
}

func TestValidateBlocksExcludedPathInEvidence(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "evidence", "E-002.json"), []byte(`{
		"id":"E-002",
		"source_kind":"file",
		"source_path":"vendor/lib.go",
		"commit_sha":"abc123",
		"span":"L1-L5",
		"extractor":"test",
		"content_hash":"hash-vendor",
		"attrs":{"language":"go"}
	}`))
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), []byte(`{
		"schema_version":1,
		"candidate_universe":[{"path":"src/app.go","disposition":"deep_read","decision_source":"git"},{"path":"vendor/lib.go","disposition":"excluded","decision_source":".cognitionignore"}],
		"included_paths":["src/app.go"],
		"excluded_paths":["vendor/lib.go"],
		"ambiguous_paths":[],
		"dispositions":{"src/app.go":"deep_read","vendor/lib.go":"excluded"},
		"criticality":{"src/app.go":"important","vendor/lib.go":"low_risk"},
		"classification_reasons":{"src/app.go":"source","vendor/lib.go":"vendor"},
		"decision_source":{"src/app.go":"git","vendor/lib.go":".cognitionignore"}
	}`))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "excluded path vendor/lib.go must not appear in evidence source paths") {
		t.Fatalf("Errors = %#v, want excluded evidence path error", result.Errors)
	}
}

func TestValidateBlocksExcludedPathInNodePaths(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "provisional", "nodes.json"), []byte(`{"nodes":[{
		"id":"N-app",
		"type":"capability",
		"title":"App",
		"confidence":"verified",
		"paths":["src/app.go","vendor/lib.go"],
		"evidence_ids":["E-001"],
		"attrs":{"owner":"app"}
	}]}`))
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), []byte(`{
		"schema_version":1,
		"candidate_universe":[{"path":"src/app.go","disposition":"deep_read","decision_source":"git"},{"path":"vendor/lib.go","disposition":"excluded","decision_source":".cognitionignore"}],
		"included_paths":["src/app.go"],
		"excluded_paths":["vendor/lib.go"],
		"ambiguous_paths":[],
		"dispositions":{"src/app.go":"deep_read","vendor/lib.go":"excluded"},
		"criticality":{"src/app.go":"important","vendor/lib.go":"low_risk"},
		"classification_reasons":{"src/app.go":"source","vendor/lib.go":"vendor"},
		"decision_source":{"src/app.go":"git","vendor/lib.go":".cognitionignore"}
	}`))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "excluded path vendor/lib.go must not appear in node paths") {
		t.Fatalf("Errors = %#v, want excluded node path error", result.Errors)
	}
}

func TestValidateBlocksExcludedPathInEdgeEndpoints(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "provisional", "edges.json"), []byte(`{"edges":[{
		"id":"EDGE-vendor",
		"type":"owns",
		"source":"vendor/lib.go",
		"target":"N-app",
		"confidence":"verified",
		"evidence_ids":["E-001"],
		"attrs":{"relation":"vendor"}
	}]}`))
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), []byte(`{
		"schema_version":1,
		"candidate_universe":[{"path":"src/app.go","disposition":"deep_read","decision_source":"git"},{"path":"vendor/lib.go","disposition":"excluded","decision_source":".cognitionignore"}],
		"included_paths":["src/app.go"],
		"excluded_paths":["vendor/lib.go"],
		"ambiguous_paths":[],
		"dispositions":{"src/app.go":"deep_read","vendor/lib.go":"excluded"},
		"criticality":{"src/app.go":"important","vendor/lib.go":"low_risk"},
		"classification_reasons":{"src/app.go":"source","vendor/lib.go":"vendor"},
		"decision_source":{"src/app.go":"git","vendor/lib.go":".cognitionignore"}
	}`))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "excluded path vendor/lib.go must not appear in edge endpoints") {
		t.Fatalf("Errors = %#v, want excluded edge endpoint error", result.Errors)
	}
}

func TestValidateAcceptsBoundaryExcludedPathOutsideCoverage(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), []byte(`{
		"schema_version":1,
		"candidate_universe":[{"path":"src/app.go","disposition":"deep_read","decision_source":"git"},{"path":"vendor/lib.go","disposition":"excluded","decision_source":".cognitionignore"}],
		"included_paths":["src/app.go"],
		"excluded_paths":[{"path":"vendor/lib.go","reason":"vendor","decision_source":".cognitionignore"}],
		"ambiguous_paths":[],
		"dispositions":{"src/app.go":"deep_read","vendor/lib.go":"excluded"},
		"criticality":{"src/app.go":"important","vendor/lib.go":"low_risk"},
		"classification_reasons":{"src/app.go":"source","vendor/lib.go":"vendor"},
		"decision_source":{"src/app.go":"git","vendor/lib.go":".cognitionignore"}
	}`))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "ok" {
		t.Fatalf("Status = %q, want ok; errors=%#v", result.Status, result.Errors)
	}
}

func TestValidateBlocksCoveragePathOutsideBoundary(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "coverage.json"), []byte(`{"rows":[{"path":"src/app.go"},{"path":"src/extra.go"}]}`))
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), []byte(`{
		"schema_version":1,
		"candidate_universe":[{"path":"src/app.go","disposition":"deep_read","decision_source":"git"}],
		"included_paths":["src/app.go"],
		"excluded_paths":[],
		"ambiguous_paths":[],
		"dispositions":{"src/app.go":"deep_read"},
		"criticality":{"src/app.go":"important"},
		"classification_reasons":{"src/app.go":"source"},
		"decision_source":{"src/app.go":"git"}
	}`))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "coverage path src/extra.go must be listed in repository-universe candidate_universe and included_paths with coverage-eligible disposition") {
		t.Fatalf("Errors = %#v, want coverage outside boundary error", result.Errors)
	}
}

func TestValidateAcceptsLegacyRowsUniverseWithoutStrictCoverageMatch(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "coverage.json"), []byte(`{"rows":[{"path":"src/renamed.go"}]}`))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "ok" {
		t.Fatalf("Status = %q, want ok; errors=%#v", result.Status, result.Errors)
	}
}

func TestValidateAcceptsIncludedPathCoveredByAcceptedGapPath(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json"), []byte(`{
		"rows":[{"path":"src/app.go","status":"covered"}],
		"open_gaps":[{"path":"src/missing.go","status":"low_risk_open_gap","owner":"scan","reason":"deferred","evidence_expectation":"non-critical path","revisit_condition":"next scan"}]
	}`))
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), []byte(`{
		"schema_version":1,
		"candidate_universe":[{"path":"src/app.go","disposition":"deep_read","decision_source":"git"},{"path":"src/missing.go","disposition":"sampled","decision_source":"git"}],
		"included_paths":["src/app.go","src/missing.go"],
		"excluded_paths":[],
		"ambiguous_paths":[],
		"dispositions":{"src/app.go":"deep_read","src/missing.go":"sampled"},
		"criticality":{"src/app.go":"important","src/missing.go":"low_risk"},
		"classification_reasons":{"src/app.go":"source","src/missing.go":"source"},
		"decision_source":{"src/app.go":"git","src/missing.go":"git"}
	}`))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "ok" {
		t.Fatalf("Status = %q, want ok; errors=%#v", result.Status, result.Errors)
	}
}

func TestValidateAcceptsIncludedPathCoveredByAcceptedGapPathsArray(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json"), []byte(`{
		"rows":[{"path":"src/app.go","status":"covered"}],
		"open_gaps":[{"paths":["src/missing.go"],"status":"low_risk_open_gap","owner":"scan","reason":"deferred","evidence_expectation":"non-critical path","revisit_condition":"next scan"}]
	}`))
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), []byte(`{
		"schema_version":1,
		"candidate_universe":[{"path":"src/app.go","disposition":"deep_read","decision_source":"git"},{"path":"src/missing.go","disposition":"sampled","decision_source":"git"}],
		"included_paths":["src/app.go","src/missing.go"],
		"excluded_paths":[],
		"ambiguous_paths":[],
		"dispositions":{"src/app.go":"deep_read","src/missing.go":"sampled"},
		"criticality":{"src/app.go":"important","src/missing.go":"low_risk"},
		"classification_reasons":{"src/app.go":"source","src/missing.go":"source"},
		"decision_source":{"src/app.go":"git","src/missing.go":"git"}
	}`))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "ok" {
		t.Fatalf("Status = %q, want ok; errors=%#v", result.Status, result.Errors)
	}
}

func TestValidateAcceptsPacketLedgerAlignedSampledOutcome(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeVersionedUniverse(t, paths, `[
		{"path":"src/app.go","disposition":"sampled","criticality":"low_risk","decision_source":"scan"}
	]`, `{"src/app.go":"sampled"}`, `{"src/app.go":"low_risk"}`)
	writeWorkerResult(t, paths, "lane-1.json", `{
		"packet_id":"lane-1",
		"family_id":"app",
		"assigned_paths":["src/app.go"],
		"paths_read":["src/app.go"],
		"ledger":{"todo":[],"doing":[],"done":["src/app.go"],"blocked":[],"overflow":[]},
		"coverage":[{"path":"src/app.go","outcome":"sampled","evidence_ids":["E-001"]}],
		"confidence":"medium",
		"acceptance":"pass"
	}`)

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "ok" {
		t.Fatalf("Status = %q, want ok; errors=%#v", result.Status, result.Errors)
	}
}

func TestValidateBlocksSampledCriticalEntrypointWithoutAcceptedGap(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeVersionedUniverse(t, paths, `[
		{"path":"src/app.go","disposition":"sampled","criticality":"critical","decision_source":"scan"}
	]`, `{"src/app.go":"sampled"}`, `{"src/app.go":"critical"}`)
	writeWorkerResult(t, paths, "lane-1.json", `{
		"packet_id":"lane-1",
		"family_id":"app",
		"assigned_paths":["src/app.go"],
		"paths_read":["src/app.go"],
		"ledger":{"todo":[],"doing":[],"done":["src/app.go"],"blocked":[],"overflow":[]},
		"coverage":[{"path":"src/app.go","outcome":"sampled","evidence_ids":["E-001"]}],
		"confidence":"medium",
		"acceptance":"pass"
	}`)

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "packet lane-1 path src/app.go outcome sampled is not allowed for criticality critical without accepted gap") {
		t.Fatalf("Errors = %#v, want critical sampled disposition error", result.Errors)
	}
}

func TestValidateBlocksInventoryOnlyCriticalStateWithoutDispositionSupport(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeVersionedUniverse(t, paths, `[
		{"path":"src/app.go","disposition":"deep_read","criticality":"critical","decision_source":"scan"}
	]`, `{"src/app.go":"deep_read"}`, `{"src/app.go":"critical"}`)
	writeWorkerResult(t, paths, "lane-1.json", `{
		"packet_id":"lane-1",
		"family_id":"app",
		"assigned_paths":["src/app.go"],
		"paths_read":["src/app.go"],
		"ledger":{"todo":[],"doing":[],"done":["src/app.go"],"blocked":[],"overflow":[]},
		"coverage":[{"path":"src/app.go","outcome":"inventory_only","evidence_ids":["E-001"]}],
		"confidence":"medium",
		"acceptance":"pass"
	}`)

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "packet lane-1 path src/app.go outcome inventory_only conflicts with repository-universe disposition deep_read") {
		t.Fatalf("Errors = %#v, want inventory disposition error", result.Errors)
	}
}

func TestValidateBlocksVersionedBoundaryWithoutCriticalityMap(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), []byte(`{
		"schema_version":1,
		"candidate_universe":[{"path":"src/app.go","disposition":"deep_read","decision_source":"scan"}],
		"included_paths":["src/app.go"],
		"excluded_paths":[],
		"ambiguous_paths":[],
		"dispositions":{"src/app.go":"deep_read"},
		"classification_reasons":{"src/app.go":"source"},
		"decision_source":{"src/app.go":"scan"}
	}`))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "repository-universe criticality must be an object") {
		t.Fatalf("Errors = %#v, want missing criticality schema error", result.Errors)
	}
}

func TestValidateBlocksVersionedBoundaryWithoutCandidateCriticality(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeVersionedUniverse(t, paths, `[
		{"path":"src/app.go","disposition":"deep_read","criticality":"important","decision_source":"scan"}
	]`, `{"src/app.go":"deep_read"}`, `{}`)

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "repository-universe candidate path src/app.go has no criticality") {
		t.Fatalf("Errors = %#v, want missing candidate criticality error", result.Errors)
	}
}

func TestValidateBlocksInvalidCandidateCriticality(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeVersionedUniverse(t, paths, `[
		{"path":"src/app.go","disposition":"deep_read","criticality":"urgent","decision_source":"scan"}
	]`, `{"src/app.go":"deep_read"}`, `{"src/app.go":"urgent"}`)

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "repository-universe candidate path src/app.go has invalid criticality urgent") {
		t.Fatalf("Errors = %#v, want invalid candidate criticality error", result.Errors)
	}
}

func TestValidateReturnsFailSubsetForQualityFailure(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeVersionedUniverse(t, paths, `[
		{"path":"src/app.go","disposition":"deep_read","criticality":"important","decision_source":"scan"}
	]`, `{"src/app.go":"deep_read"}`, `{"src/app.go":"important"}`)
	writeWorkerResult(t, paths, "lane-1.json", `{
		"packet_id":"lane-1",
		"family_id":"app",
		"assigned_paths":["src/app.go"],
		"paths_read":["src/app.go"],
		"ledger":{"todo":[],"doing":[],"done":["src/app.go"],"blocked":[],"overflow":[]},
		"coverage":[{"path":"src/app.go","outcome":"read","evidence_ids":["E-001"]}],
		"acceptance":"fail_quality",
		"repack_subset":{"paths":["src/app.go"]}
	}`)

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked for quality redispatch; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "packet lane-1 failed quality gate for repack subset") {
		t.Fatalf("Errors = %#v, want quality repack subset error", result.Errors)
	}
}

func TestValidateBlocksContractInvalidPacketLedger(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeVersionedUniverse(t, paths, `[
		{"path":"src/app.go","disposition":"deep_read","criticality":"important","decision_source":"scan"}
	]`, `{"src/app.go":"deep_read"}`, `{"src/app.go":"important"}`)
	writeWorkerResult(t, paths, "lane-1.json", `{
		"packet_id":"lane-1",
		"family_id":"app",
		"assigned_paths":["src/app.go"],
		"paths_read":["src/app.go"],
		"coverage":[{"path":"src/app.go","outcome":"read","evidence_ids":["E-001"]}],
		"acceptance":"fail_contract",
		"redispatch":"local_patch"
	}`)

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "packet lane-1 must define packet-local ledger") {
		t.Fatalf("Errors = %#v, want missing ledger error", result.Errors)
	}
	if !containsError(result.Errors, "packet lane-1 acceptance fail_contract must not request local patch redispatch") {
		t.Fatalf("Errors = %#v, want contract local patch error", result.Errors)
	}
}

func TestValidateBlocksSystemicRepeatedPacketFamilyFailure(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "coverage.json"), []byte(`{"rows":[{"path":"src/app.go"},{"path":"src/worker.go"}]}`))
	writeVersionedUniverse(t, paths, `[
		{"path":"src/app.go","disposition":"deep_read","criticality":"important","decision_source":"scan"},
		{"path":"src/worker.go","disposition":"deep_read","criticality":"important","decision_source":"scan"}
	]`, `{"src/app.go":"deep_read","src/worker.go":"deep_read"}`, `{"src/app.go":"important","src/worker.go":"important"}`)
	writeWorkerResult(t, paths, "lane-1.json", `{
		"packet_id":"lane-1",
		"family_id":"app",
		"assigned_paths":["src/app.go"],
		"paths_read":["src/app.go"],
		"ledger":{"todo":[],"doing":[],"done":["src/app.go"],"blocked":[],"overflow":[]},
		"coverage":[{"path":"src/app.go","outcome":"read","evidence_ids":["E-001"]}],
		"acceptance":"fail_quality",
		"repack_subset":{"paths":["src/app.go"]}
	}`)
	writeWorkerResult(t, paths, "lane-2.json", `{
		"packet_id":"lane-2",
		"family_id":"app",
		"assigned_paths":["src/worker.go"],
		"paths_read":["src/worker.go"],
		"ledger":{"todo":[],"doing":[],"done":["src/worker.go"],"blocked":[],"overflow":[]},
		"coverage":[{"path":"src/worker.go","outcome":"read","evidence_ids":["E-002"]}],
		"acceptance":"fail_quality",
		"repack_subset":{"paths":["src/worker.go"]}
	}`)

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "packet family app has repeated fail_quality outcomes; escalate to fail_systemic") {
		t.Fatalf("Errors = %#v, want systemic family escalation error", result.Errors)
	}
}

func TestValidateBlocksBooleanPathsReadInWorkerResult(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeWorkerResult(t, paths, "lane-1.json", `{
		"packet_id":"lane-1",
		"family_id":"app",
		"assigned_paths":["src/app.go"],
		"paths_read":true,
		"ledger":{"todo":[],"doing":[],"done":["src/app.go"],"blocked":[],"overflow":[]},
		"coverage":[{"path":"src/app.go","outcome":"read","evidence_ids":["E-001"]}],
		"confidence":"high",
		"acceptance":"pass"
	}`)

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "packet lane-1 paths_read must be an array of concrete paths") {
		t.Fatalf("Errors = %#v, want boolean paths_read rejection", result.Errors)
	}
}

func TestValidateBlocksPassingWorkerResultWithoutConfidence(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeWorkerResult(t, paths, "lane-1.json", `{
		"packet_id":"lane-1",
		"family_id":"app",
		"assigned_paths":["src/app.go"],
		"paths_read":["src/app.go"],
		"ledger":{"todo":[],"doing":[],"done":["src/app.go"],"blocked":[],"overflow":[]},
		"coverage":[{"path":"src/app.go","outcome":"read","evidence_ids":["E-001"]}],
		"acceptance":"pass"
	}`)

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "packet lane-1 pass acceptance must include confidence") {
		t.Fatalf("Errors = %#v, want missing confidence rejection", result.Errors)
	}
}

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

func TestValidateBlocksWorkerResultsRegularFile(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	workerResultsDir := filepath.Join(paths.RuntimeDir, "workbench", "worker-results")
	if err := os.RemoveAll(workerResultsDir); err != nil {
		t.Fatal(err)
	}
	writeFileBytes(t, workerResultsDir, []byte("not a directory\n"))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "required artifact must be a directory: .specify/project-cognition/workbench/worker-results") {
		t.Fatalf("Errors = %#v, want worker-results directory error", result.Errors)
	}
}

func TestValidateBlocksScanPacketsRegularFile(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	scanPacketsDir := filepath.Join(paths.RuntimeDir, "workbench", "scan-packets")
	if err := os.RemoveAll(scanPacketsDir); err != nil {
		t.Fatal(err)
	}
	writeFileBytes(t, scanPacketsDir, []byte("not a directory\n"))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "required artifact must be a directory: .specify/project-cognition/workbench/scan-packets") {
		t.Fatalf("Errors = %#v, want scan-packets directory error", result.Errors)
	}
}

func TestValidateBlocksAcceptedFailGapPacket(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeWorkerResult(t, paths, "lane-1.json", `{
		"packet_id":"lane-1",
		"family_id":"app",
		"assigned_paths":["src/app.go"],
		"paths_read":[],
		"ledger":{"todo":[],"doing":[],"done":[],"blocked":["src/app.go"],"overflow":[]},
		"coverage":[{"path":"src/app.go","outcome":"blocked"}],
		"acceptance":"fail_gap"
	}`)

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "packet lane-1 failed coverage gate") {
		t.Fatalf("Errors = %#v, want fail_gap blocking error", result.Errors)
	}
}

func TestValidateBlocksAcceptedFailContractPacket(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeWorkerResult(t, paths, "lane-1.json", `{
		"packet_id":"lane-1",
		"family_id":"app",
		"assigned_paths":["src/app.go"],
		"paths_read":[],
		"ledger":{"todo":[],"doing":[],"done":["src/app.go"],"blocked":[],"overflow":[]},
		"coverage":[{"path":"src/app.go","outcome":"read","evidence_ids":["E-001"]}],
		"acceptance":"fail_contract"
	}`)

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "packet lane-1 acceptance fail_contract requires scan packet schema repair or packet-family repack") {
		t.Fatalf("Errors = %#v, want fail_contract blocking error", result.Errors)
	}
}

func TestValidateBlocksAcceptedFailSystemicPacket(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeWorkerResult(t, paths, "lane-1.json", `{
		"packet_id":"lane-1",
		"family_id":"app",
		"assigned_paths":["src/app.go"],
		"paths_read":[],
		"ledger":{"todo":[],"doing":[],"done":["src/app.go"],"blocked":[],"overflow":[]},
		"coverage":[{"path":"src/app.go","outcome":"read","evidence_ids":["E-001"]}],
		"acceptance":"fail_systemic"
	}`)

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "packet lane-1 acceptance fail_systemic requires scan packet schema repair or packet-family repack") {
		t.Fatalf("Errors = %#v, want fail_systemic blocking error", result.Errors)
	}
}

func TestValidateBlocksWorkerResultWithMissingEvidenceID(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeWorkerResult(t, paths, "lane-1.json", `{
		"packet_id":"lane-1",
		"family_id":"app",
		"assigned_paths":["src/app.go"],
		"paths_read":["src/app.go"],
		"ledger":{"todo":[],"doing":[],"done":["src/app.go"],"blocked":[],"overflow":[]},
		"coverage":[{"path":"src/app.go","outcome":"read","evidence_ids":["E-missing"]}],
		"confidence":"high",
		"acceptance":"pass"
	}`)

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "packet lane-1 path src/app.go references missing evidence_id E-missing") {
		t.Fatalf("Errors = %#v, want missing evidence id error", result.Errors)
	}
}

func TestValidateBlocksWorkerResultEvidenceForDifferentPath(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "evidence", "E-002.json"), []byte(`{
		"id":"E-002",
		"source_kind":"file",
		"source_path":"docs/app.md",
		"commit_sha":"abc123",
		"span":"L1-L5",
		"extractor":"test",
		"content_hash":"hash-docs"
	}`))
	writeWorkerResult(t, paths, "lane-1.json", `{
		"packet_id":"lane-1",
		"family_id":"app",
		"assigned_paths":["src/app.go"],
		"paths_read":["src/app.go"],
		"ledger":{"todo":[],"doing":[],"done":["src/app.go"],"blocked":[],"overflow":[]},
		"coverage":[{"path":"src/app.go","outcome":"read","evidence_ids":["E-002"]}],
		"confidence":"high",
		"acceptance":"pass"
	}`)

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "packet lane-1 path src/app.go read outcome must reference evidence with matching source_path") {
		t.Fatalf("Errors = %#v, want evidence source_path mismatch error", result.Errors)
	}
}

func TestValidateBlocksEmptyScanPacketsDirectory(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	scanPacketsDir := filepath.Join(paths.RuntimeDir, "workbench", "scan-packets")
	if err := os.RemoveAll(scanPacketsDir); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(scanPacketsDir, 0o755); err != nil {
		t.Fatal(err)
	}

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "workbench/scan-packets must contain at least one scan packet Markdown file") {
		t.Fatalf("Errors = %#v, want empty scan-packets error", result.Errors)
	}
}

func TestValidateBlocksOrphanWorkerResult(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeWorkerResult(t, paths, "orphan.json", `{
		"packet_id":"orphan",
		"family_id":"app",
		"assigned_paths":["src/app.go"],
		"paths_read":["src/app.go"],
		"ledger":{"todo":[],"doing":[],"done":["src/app.go"],"blocked":[],"overflow":[]},
		"coverage":[{"path":"src/app.go","outcome":"read","evidence_ids":["E-001"]}],
		"confidence":"high",
		"acceptance":"pass"
	}`)

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "worker result orphan.json has no matching scan packet") {
		t.Fatalf("Errors = %#v, want orphan worker result error", result.Errors)
	}
}

func TestValidateBlocksScanPacketWithoutWorkerResult(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-packets", "lane-2.md"), []byte("# Lane 2\n"))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "scan packet lane-2 has no matching worker result") {
		t.Fatalf("Errors = %#v, want missing worker result error", result.Errors)
	}
}

func TestValidateBlocksWorkerResultPacketIDMismatch(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeWorkerResult(t, paths, "lane-1.json", `{
		"packet_id":"different-lane",
		"family_id":"app",
		"assigned_paths":["src/app.go"],
		"paths_read":["src/app.go"],
		"ledger":{"todo":[],"doing":[],"done":["src/app.go"],"blocked":[],"overflow":[]},
		"coverage":[{"path":"src/app.go","outcome":"read","evidence_ids":["E-001"]}],
		"confidence":"high",
		"acceptance":"pass"
	}`)

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "worker result lane-1.json packet_id different-lane must match file stem lane-1") {
		t.Fatalf("Errors = %#v, want packet id mismatch error", result.Errors)
	}
}

func TestValidateBlocksDuplicateWorkerResultPacketID(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-packets", "lane-2.md"), []byte("# Lane 2\n"))
	writeWorkerResult(t, paths, "lane-2.json", `{
		"packet_id":"lane-1",
		"family_id":"app",
		"assigned_paths":["src/app.go"],
		"paths_read":["src/app.go"],
		"ledger":{"todo":[],"doing":[],"done":["src/app.go"],"blocked":[],"overflow":[]},
		"coverage":[{"path":"src/app.go","outcome":"read","evidence_ids":["E-001"]}],
		"confidence":"high",
		"acceptance":"pass"
	}`)

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "worker result packet_id lane-1 appears more than once") {
		t.Fatalf("Errors = %#v, want duplicate packet id error", result.Errors)
	}
}

func TestValidateBlocksNonStringPathsReadItem(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeWorkerResult(t, paths, "lane-1.json", `{
		"packet_id":"lane-1",
		"family_id":"app",
		"assigned_paths":["src/app.go"],
		"paths_read":["src/app.go",7],
		"ledger":{"todo":[],"doing":[],"done":["src/app.go"],"blocked":[],"overflow":[]},
		"coverage":[{"path":"src/app.go","outcome":"read","evidence_ids":["E-001"]}],
		"confidence":"high",
		"acceptance":"pass"
	}`)

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "packet lane-1 paths_read[1] must be a concrete path string") {
		t.Fatalf("Errors = %#v, want mixed paths_read item error", result.Errors)
	}
}

func TestValidateBlocksDeepReadCandidateOmittedFromIncludedPaths(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), []byte(`{
		"schema_version":1,
		"candidate_universe":[{"path":"src/app.go","disposition":"deep_read","decision_source":"git"},{"path":"src/missing.go","disposition":"deep_read","decision_source":"git"}],
		"included_paths":["src/app.go"],
		"excluded_paths":[],
		"ambiguous_paths":[],
		"dispositions":{"src/app.go":"deep_read","src/missing.go":"deep_read"},
		"criticality":{"src/app.go":"important","src/missing.go":"important"},
		"classification_reasons":{"src/app.go":"source","src/missing.go":"source"},
		"decision_source":{"src/app.go":"git","src/missing.go":"git"}
	}`))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "repository-universe candidate path src/missing.go with disposition deep_read must be listed in included_paths") {
		t.Fatalf("Errors = %#v, want missing included membership error", result.Errors)
	}
	if !containsError(result.Errors, "repository-universe included path src/missing.go has no coverage row or accepted nonblocking gap") {
		t.Fatalf("Errors = %#v, want missing candidate coverage error", result.Errors)
	}
}

func TestValidateBlocksExcludedCandidateOmittedFromExcludedPathsInCoverage(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "coverage.json"), []byte(`{"rows":[{"path":"src/app.go"},{"path":"vendor/lib.go"}]}`))
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), []byte(`{
		"schema_version":1,
		"candidate_universe":[{"path":"src/app.go","disposition":"deep_read","decision_source":"git"},{"path":"vendor/lib.go","disposition":"excluded","decision_source":".cognitionignore"}],
		"included_paths":["src/app.go"],
		"excluded_paths":[],
		"ambiguous_paths":[],
		"dispositions":{"src/app.go":"deep_read","vendor/lib.go":"excluded"},
		"criticality":{"src/app.go":"important","vendor/lib.go":"low_risk"},
		"classification_reasons":{"src/app.go":"source","vendor/lib.go":"vendor"},
		"decision_source":{"src/app.go":"git","vendor/lib.go":".cognitionignore"}
	}`))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "repository-universe candidate path vendor/lib.go with excluded disposition must be listed in excluded_paths") {
		t.Fatalf("Errors = %#v, want missing excluded membership error", result.Errors)
	}
	if !containsError(result.Errors, "excluded path vendor/lib.go must not appear in coverage.json") {
		t.Fatalf("Errors = %#v, want excluded candidate coverage error", result.Errors)
	}
}

func TestValidateBlocksPathInIncludedAndExcludedPaths(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), []byte(`{
		"schema_version":1,
		"candidate_universe":[{"path":"src/app.go","disposition":"deep_read","decision_source":"git"}],
		"included_paths":["src/app.go"],
		"excluded_paths":["src/app.go"],
		"ambiguous_paths":[],
		"dispositions":{"src/app.go":"deep_read"},
		"criticality":{"src/app.go":"important"},
		"classification_reasons":{"src/app.go":"source"},
		"decision_source":{"src/app.go":"git"}
	}`))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "repository-universe path src/app.go must not appear in both included_paths and excluded_paths") {
		t.Fatalf("Errors = %#v, want conflicting boundary list error", result.Errors)
	}
}

func TestValidateBlocksBlockedCandidateMissingFromBoundaryLists(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), []byte(`{
		"schema_version":1,
		"candidate_universe":[{"path":"src/app.go","disposition":"deep_read","decision_source":"git"},{"path":"src/blocked.go","disposition":"blocked","decision_source":"scan"}],
		"included_paths":["src/app.go"],
		"excluded_paths":[],
		"ambiguous_paths":[],
		"dispositions":{"src/app.go":"deep_read","src/blocked.go":"blocked"},
		"criticality":{"src/app.go":"important","src/blocked.go":"low_risk"},
		"classification_reasons":{"src/app.go":"source","src/blocked.go":"ambiguous"},
		"decision_source":{"src/app.go":"git","src/blocked.go":"scan"}
	}`))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "repository-universe candidate path src/blocked.go must appear in exactly one boundary list") {
		t.Fatalf("Errors = %#v, want missing candidate list membership error", result.Errors)
	}
}

func TestValidateBlocksBlockedCandidateInIncludedPaths(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), []byte(`{
		"schema_version":1,
		"candidate_universe":[{"path":"src/app.go","disposition":"deep_read","decision_source":"git"},{"path":"src/blocked.go","disposition":"blocked","decision_source":"scan"}],
		"included_paths":["src/app.go","src/blocked.go"],
		"excluded_paths":[],
		"ambiguous_paths":[],
		"dispositions":{"src/app.go":"deep_read","src/blocked.go":"blocked"},
		"criticality":{"src/app.go":"important","src/blocked.go":"low_risk"},
		"classification_reasons":{"src/app.go":"source","src/blocked.go":"ambiguous"},
		"decision_source":{"src/app.go":"git","src/blocked.go":"scan"}
	}`))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "repository-universe candidate path src/blocked.go with blocked disposition must be listed in ambiguous_paths") {
		t.Fatalf("Errors = %#v, want blocked candidate ambiguous membership error", result.Errors)
	}
}

func TestValidateBlocksIncludedAndAmbiguousOverlap(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), []byte(`{
		"schema_version":1,
		"candidate_universe":[{"path":"src/app.go","disposition":"deep_read","decision_source":"git"}],
		"included_paths":["src/app.go"],
		"excluded_paths":[],
		"ambiguous_paths":["src/app.go"],
		"dispositions":{"src/app.go":"deep_read"},
		"criticality":{"src/app.go":"important"},
		"classification_reasons":{"src/app.go":"source"},
		"decision_source":{"src/app.go":"git"}
	}`))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "repository-universe path src/app.go must not appear in both included_paths and ambiguous_paths") {
		t.Fatalf("Errors = %#v, want included ambiguous overlap error", result.Errors)
	}
}

func TestValidateBlocksStrayIncludedPathMissingFromCandidateUniverse(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "coverage.json"), []byte(`{"rows":[{"path":"src/app.go"},{"path":"src/extra.go"}]}`))
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), []byte(`{
		"schema_version":1,
		"candidate_universe":[{"path":"src/app.go","disposition":"deep_read","decision_source":"git"}],
		"included_paths":["src/app.go","src/extra.go"],
		"excluded_paths":[],
		"ambiguous_paths":[],
		"dispositions":{"src/app.go":"deep_read","src/extra.go":"deep_read"},
		"criticality":{"src/app.go":"important","src/extra.go":"important"},
		"classification_reasons":{"src/app.go":"source","src/extra.go":"source"},
		"decision_source":{"src/app.go":"git","src/extra.go":"git"}
	}`))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "repository-universe included path src/extra.go is missing from candidate_universe") {
		t.Fatalf("Errors = %#v, want stray included path error", result.Errors)
	}
}

func TestValidateBlocksStrayExcludedPathMissingFromCandidateUniverse(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), []byte(`{
		"schema_version":1,
		"candidate_universe":[{"path":"src/app.go","disposition":"deep_read","decision_source":"git"}],
		"included_paths":["src/app.go"],
		"excluded_paths":["vendor/extra.go"],
		"ambiguous_paths":[],
		"dispositions":{"src/app.go":"deep_read","vendor/extra.go":"excluded"},
		"criticality":{"src/app.go":"important","vendor/extra.go":"low_risk"},
		"classification_reasons":{"src/app.go":"source","vendor/extra.go":"vendor"},
		"decision_source":{"src/app.go":"git","vendor/extra.go":".cognitionignore"}
	}`))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "repository-universe excluded path vendor/extra.go is missing from candidate_universe") {
		t.Fatalf("Errors = %#v, want stray excluded path error", result.Errors)
	}
}

func TestValidateBlocksStrayAmbiguousPathMissingFromCandidateUniverse(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), []byte(`{
		"schema_version":1,
		"candidate_universe":[{"path":"src/app.go","disposition":"deep_read","decision_source":"git"}],
		"included_paths":["src/app.go"],
		"excluded_paths":[],
		"ambiguous_paths":["src/unknown.go"],
		"dispositions":{"src/app.go":"deep_read","src/unknown.go":"blocked"},
		"criticality":{"src/app.go":"important","src/unknown.go":"low_risk"},
		"classification_reasons":{"src/app.go":"source","src/unknown.go":"ambiguous"},
		"decision_source":{"src/app.go":"git","src/unknown.go":"scan"}
	}`))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "repository-universe ambiguous path src/unknown.go is missing from candidate_universe") {
		t.Fatalf("Errors = %#v, want stray ambiguous path error", result.Errors)
	}
}

func TestValidateBlocksMetadataIncompleteGapForBoundaryCoverage(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json"), []byte(`{
		"rows":[{"path":"src/app.go","status":"covered"}],
		"open_gaps":[{"path":"src/missing.go","status":"low_risk_open_gap","reason":"deferred","evidence_expectation":"non-critical path","revisit_condition":"next scan"}]
	}`))
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), []byte(`{
		"schema_version":1,
		"candidate_universe":[{"path":"src/app.go","disposition":"deep_read","decision_source":"git"},{"path":"src/missing.go","disposition":"sampled","decision_source":"git"}],
		"included_paths":["src/app.go","src/missing.go"],
		"excluded_paths":[],
		"ambiguous_paths":[],
		"dispositions":{"src/app.go":"deep_read","src/missing.go":"sampled"},
		"criticality":{"src/app.go":"important","src/missing.go":"low_risk"},
		"classification_reasons":{"src/app.go":"source","src/missing.go":"source"},
		"decision_source":{"src/app.go":"git","src/missing.go":"git"}
	}`))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "repository-universe included path src/missing.go has no coverage row or accepted nonblocking gap") {
		t.Fatalf("Errors = %#v, want incomplete gap ignored for coverage", result.Errors)
	}
}

func TestValidateAcceptsLowRiskGapPathsArrayWithRequiredMetadata(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json"), []byte(`{
		"rows":[{"path":"src/app.go","status":"covered"}],
		"open_gaps":[{"paths":["src/missing.go"],"coverage_state":"low_risk_open_gap","owner":"scan","reason":"deferred","evidence_expectation":"non-critical path","revisit_condition":"next scan"}]
	}`))
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), []byte(`{
		"schema_version":1,
		"candidate_universe":[{"path":"src/app.go","disposition":"deep_read","decision_source":"git"},{"path":"src/missing.go","disposition":"sampled","decision_source":"git"}],
		"included_paths":["src/app.go","src/missing.go"],
		"excluded_paths":[],
		"ambiguous_paths":[],
		"dispositions":{"src/app.go":"deep_read","src/missing.go":"sampled"},
		"criticality":{"src/app.go":"important","src/missing.go":"low_risk"},
		"classification_reasons":{"src/app.go":"source","src/missing.go":"source"},
		"decision_source":{"src/app.go":"git","src/missing.go":"git"}
	}`))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "ok" {
		t.Fatalf("Status = %q, want ok; errors=%#v", result.Status, result.Errors)
	}
}

func TestValidateBlocksImportantAcceptedGapForBoundaryCoverage(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json"), []byte(`{
		"rows":[{"path":"src/app.go","status":"covered"}],
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

func TestValidateBlocksMalformedVersionedBoundaryFieldShape(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), []byte(`{
		"schema_version":1,
		"candidate_universe":[{"path":"src/app.go","disposition":"deep_read","decision_source":"git"}],
		"included_paths":{"path":"src/app.go"},
		"excluded_paths":[],
		"ambiguous_paths":[],
		"dispositions":{"src/app.go":"deep_read"},
		"criticality":{"src/app.go":"important"},
		"classification_reasons":{"src/app.go":"source"},
		"decision_source":{"src/app.go":"git"}
	}`))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "repository-universe included_paths must be an array") {
		t.Fatalf("Errors = %#v, want malformed included_paths error", result.Errors)
	}
}

func TestValidateBlocksVersionedBoundaryMissingSchemaVersion(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), []byte(`{
		"candidate_universe":[{"path":"src/app.go","disposition":"deep_read","decision_source":"git"}],
		"included_paths":["src/app.go"],
		"excluded_paths":[],
		"ambiguous_paths":[],
		"dispositions":{"src/app.go":"deep_read"},
		"criticality":{"src/app.go":"important"},
		"classification_reasons":{"src/app.go":"source"},
		"decision_source":{"src/app.go":"git"}
	}`))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "repository-universe schema_version is required") {
		t.Fatalf("Errors = %#v, want missing schema_version error", result.Errors)
	}
}

func TestValidateBlocksVersionedBoundaryNonNumericSchemaVersion(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), []byte(`{
		"schema_version":"1",
		"candidate_universe":[{"path":"src/app.go","disposition":"deep_read","decision_source":"git"}],
		"included_paths":["src/app.go"],
		"excluded_paths":[],
		"ambiguous_paths":[],
		"dispositions":{"src/app.go":"deep_read"},
		"classification_reasons":{"src/app.go":"source"},
		"decision_source":{"src/app.go":"git"}
	}`))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "repository-universe schema_version must be a number") {
		t.Fatalf("Errors = %#v, want non-numeric schema_version error", result.Errors)
	}
}

func TestValidateBlocksMismatchedCandidateAndDispositionMap(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), []byte(`{
		"schema_version":1,
		"candidate_universe":[{"path":"src/app.go","disposition":"deep_read","decision_source":"git"}],
		"included_paths":["src/app.go"],
		"excluded_paths":[],
		"ambiguous_paths":[],
		"dispositions":{"src/app.go":"sampled"},
		"criticality":{"src/app.go":"important"},
		"classification_reasons":{"src/app.go":"source"},
		"decision_source":{"src/app.go":"git"}
	}`))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "repository-universe candidate path src/app.go disposition deep_read conflicts with dispositions map sampled") {
		t.Fatalf("Errors = %#v, want disposition mismatch error", result.Errors)
	}
}

func TestValidateBlocksIncludedPathWithoutDisposition(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), []byte(`{
		"schema_version":1,
		"candidate_universe":[{"path":"src/app.go","decision_source":"git"}],
		"included_paths":["src/app.go"],
		"excluded_paths":[],
		"ambiguous_paths":[],
		"dispositions":{},
		"criticality":{"src/app.go":"important"},
		"classification_reasons":{"src/app.go":"source"},
		"decision_source":{"src/app.go":"git"}
	}`))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "repository-universe candidate path src/app.go has no disposition") {
		t.Fatalf("Errors = %#v, want missing candidate disposition error", result.Errors)
	}
}

func TestValidateBlocksExcludedPathWithDeepReadDisposition(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), []byte(`{
		"schema_version":1,
		"candidate_universe":[{"path":"src/app.go","disposition":"deep_read","decision_source":"git"},{"path":"vendor/lib.go","disposition":"deep_read","decision_source":".cognitionignore"}],
		"included_paths":["src/app.go"],
		"excluded_paths":[{"path":"vendor/lib.go","reason":"vendor","decision_source":".cognitionignore"}],
		"ambiguous_paths":[],
		"dispositions":{"src/app.go":"deep_read","vendor/lib.go":"deep_read"},
		"criticality":{"src/app.go":"important","vendor/lib.go":"low_risk"},
		"classification_reasons":{"src/app.go":"source","vendor/lib.go":"vendor"},
		"decision_source":{"src/app.go":"git","vendor/lib.go":".cognitionignore"}
	}`))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "repository-universe excluded path vendor/lib.go must have excluded disposition") {
		t.Fatalf("Errors = %#v, want excluded disposition mismatch error", result.Errors)
	}
}

func TestLoadFallbackContentHashUsesNormalizedEvidenceObject(t *testing.T) {
	first := fallbackEvidenceIdentityForSourcePath(t, `./src\app.go`)
	second := fallbackEvidenceIdentityForSourcePath(t, `src/app.go`)

	if first != second {
		t.Fatalf("fallback evidence identities differ:\nfirst:  %s\nsecond: %s", first, second)
	}
}

func scanArtifactTestPaths(t *testing.T) rt.Paths {
	t.Helper()
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	return paths
}

func fallbackEvidenceIdentityForSourcePath(t *testing.T, sourcePath string) string {
	t.Helper()
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "evidence", "E-001.json"), []byte(`{
		"id":"E-001",
		"source_kind":" file ",
		"source_path":`+strconv.Quote(sourcePath)+`,
		"commit_sha":" abc123 ",
		"span":" L1-L5 ",
		"extractor":" test ",
		"attrs":{"language":"go"}
	}`))

	pkg, result := Load(paths, ValidateOptions{RequireStatusJSON: false})
	if result.Status != "ok" {
		t.Fatalf("Status = %q, want ok; errors=%#v", result.Status, result.Errors)
	}
	for identity := range pkg.Identities.Evidence {
		return identity
	}
	t.Fatal("missing evidence identity")
	return ""
}

func writeMinimalScanPackage(t *testing.T, paths rt.Paths) {
	t.Helper()
	files := map[string]string{
		filepath.Join(paths.RuntimeDir, "evidence", "E-001.json"): `{
			"id":"E-001",
			"source_kind":"file",
			"source_path":"src/app.go",
			"commit_sha":"abc123",
			"span":"L1-L5",
			"extractor":"test",
			"content_hash":"hash-app",
			"attrs":{"language":"go"}
		}`,
		filepath.Join(paths.RuntimeDir, "provisional", "nodes.json"): `{"nodes":[{
			"id":"N-app",
			"type":"capability",
			"title":"App",
			"confidence":"verified",
			"paths":["src/app.go"],
			"evidence_ids":["E-001"],
			"attrs":{"owner":"app"}
		}]}`,
		filepath.Join(paths.RuntimeDir, "provisional", "edges.json"): `{"edges":[{
			"id":"EDGE-app-self",
			"type":"owns",
			"source_id":"N-app",
			"target_id":"N-app",
			"confidence":"verified",
			"evidence_ids":["E-001"],
			"attrs":{"relation":"self"}
		}]}`,
		filepath.Join(paths.RuntimeDir, "provisional", "observations.json"): `{"observations":[{
			"id":"OBS-app",
			"observation_type":"implementation",
			"summary":"App exists",
			"evidence_ids":["E-001"],
			"attrs":{"source":"test"}
		}]}`,
		filepath.Join(paths.RuntimeDir, "coverage.json"):                          `{"rows":[{"path":"src/app.go"}]}`,
		filepath.Join(paths.RuntimeDir, "workbench", "map-scan.md"):               `# Map Scan`,
		filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.md"):        `# Coverage Ledger`,
		filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json"):      `{"rows":[{"path":"src/app.go","status":"covered"}],"open_gaps":[]}`,
		filepath.Join(paths.RuntimeDir, "workbench", "scan-packets", "lane-1.md"): `# Lane 1`,
		filepath.Join(paths.RuntimeDir, "workbench", "worker-results", "lane-1.json"): `{
			"packet_id":"lane-1",
			"family_id":"app",
			"assigned_paths":["src/app.go"],
			"paths_read":["src/app.go"],
			"ledger":{"todo":[],"doing":[],"done":["src/app.go"],"blocked":[],"overflow":[]},
			"coverage":[{"path":"src/app.go","outcome":"read","evidence_ids":["E-001"]}],
			"confidence":"high",
			"acceptance":"pass"
		}`,
		filepath.Join(paths.RuntimeDir, "workbench", "map-state.md"):             `# Map State`,
		filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"): `{"rows":[{"path":"src/app.go"}]}`,
		filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"): `{"packets":[{
			"packet_id":"lane-1",
			"state":"accepted",
			"assigned_paths":["src/app.go"],
			"result_handoff_path":".specify/project-cognition/workbench/worker-results/lane-1.json"
		}]}`,
		filepath.Join(paths.RuntimeDir, "workbench", "handoff-ledger.json"): `{"events":[
			{"event_id":"dispatch-1","packet_id":"lane-1","event_type":"dispatched","created_at":"2026-05-26T00:00:00Z"},
			{"event_id":"return-1","packet_id":"lane-1","event_type":"returned","worker_result_path":".specify/project-cognition/workbench/worker-results/lane-1.json","created_at":"2026-05-26T00:01:00Z"}
		]}`,
		filepath.Join(paths.RuntimeDir, "workbench", "capability-ledger.json"): `{"rows":[]}`,
		filepath.Join(paths.RuntimeDir, "workbench", "control-ledger.json"):    `{"rows":[]}`,
	}
	for path, content := range files {
		writeFileBytes(t, path, []byte(content+"\n"))
	}
}

func writeVersionedUniverse(t *testing.T, paths rt.Paths, candidateUniverse string, dispositions string, criticality string) {
	t.Helper()
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), []byte(`{
		"schema_version":1,
		"candidate_universe":`+candidateUniverse+`,
		"included_paths":`+universeIncludedPaths(candidateUniverse)+`,
		"excluded_paths":[],
		"ambiguous_paths":[],
		"dispositions":`+dispositions+`,
		"criticality":`+criticality+`,
		"classification_reasons":{"src/app.go":"source","src/worker.go":"source"},
		"decision_source":{"src/app.go":"scan","src/worker.go":"scan"}
	}`))
}

func universeIncludedPaths(candidateUniverse string) string {
	paths := []string{}
	if strings.Contains(candidateUniverse, `"src/app.go"`) {
		paths = append(paths, `"src/app.go"`)
	}
	if strings.Contains(candidateUniverse, `"src/worker.go"`) {
		paths = append(paths, `"src/worker.go"`)
	}
	return "[" + strings.Join(paths, ",") + "]"
}

func writeWorkerResult(t *testing.T, paths rt.Paths, name string, content string) {
	t.Helper()
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "worker-results", name), []byte(content+"\n"))
}

func removeFile(t *testing.T, path string) {
	t.Helper()
	if err := os.Remove(path); err != nil && !os.IsNotExist(err) {
		t.Fatal(err)
	}
}

func writeFileBytes(t *testing.T, path string, content []byte) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, content, 0o644); err != nil {
		t.Fatal(err)
	}
}

func assertIdentity(t *testing.T, identities map[string]bool, key string) {
	t.Helper()
	if !identities[key] {
		t.Fatalf("identities = %#v, want %q", identities, key)
	}
}

func containsString(values []string, want string) bool {
	for _, value := range values {
		if value == want {
			return true
		}
	}
	return false
}

func containsError(errors []string, want string) bool {
	for _, err := range errors {
		if strings.Contains(err, want) {
			return true
		}
	}
	return false
}
