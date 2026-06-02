package update

import (
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/boundary"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/delta"
	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/store"
)

func testPaths(t *testing.T) rt.Paths {
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

func TestMarkDirtyPreservesOriginMetadata(t *testing.T) {
	paths := testPaths(t)
	status, err := MarkDirty(paths, DirtyInput{
		Reason:           "workflow contract changed",
		OriginCommand:    "implement",
		OriginFeatureDir: ".specify/features/001-demo",
		OriginLaneID:     "lane-1",
		ScopePaths:       []string{"src/auth/login.ts"},
	})
	if err != nil {
		t.Fatal(err)
	}
	if !status.Dirty {
		t.Fatal("expected dirty status")
	}
	if status.DirtyOriginCommand != "implement" {
		t.Fatalf("origin command = %q", status.DirtyOriginCommand)
	}
	if got := status.DirtyScopePaths; len(got) != 1 || got[0] != "src/auth/login.ts" {
		t.Fatalf("scope paths = %#v", got)
	}
}

func TestMarkDirtyDerivesScopeFromPacket(t *testing.T) {
	paths := testPaths(t)
	packet := filepath.Join(paths.Root, "packet.json")
	data, _ := json.Marshal(map[string]any{
		"changed_paths": []string{"src/a.go"},
		"work": []map[string]any{
			{"path": "docs/b.md"},
		},
	})
	if err := os.WriteFile(packet, data, 0o644); err != nil {
		t.Fatal(err)
	}
	status, err := MarkDirty(paths, DirtyInput{Reason: "packet", PacketFile: packet})
	if err != nil {
		t.Fatal(err)
	}
	if len(status.DirtyScopePaths) != 2 {
		t.Fatalf("scope paths = %#v", status.DirtyScopePaths)
	}
}

func TestCompleteRefreshClearsDirtyState(t *testing.T) {
	paths := testPaths(t)
	seedReadyRuntime(t, paths)
	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	status.Dirty = true
	status.Status = "stale"
	status.Freshness = rt.StaleFreshness
	status.Readiness = rt.BlockedReadiness
	status.DirtyReasons = []string{"manual"}
	status.StalePaths = []string{"src/app.go"}
	status.StaleReasons = []string{"manual"}
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}
	status, err = CompleteRefresh(paths, "map-build")
	if err != nil {
		t.Fatal(err)
	}
	if status.Dirty {
		t.Fatal("dirty should be false")
	}
	if status.Freshness != rt.ReadyFreshness {
		t.Fatalf("freshness = %q", status.Freshness)
	}
}

func TestCompleteRefreshBlocksStatusOnlyRuntime(t *testing.T) {
	paths := testPaths(t)
	if _, err := MarkDirty(paths, DirtyInput{Reason: "manual"}); err != nil {
		t.Fatal(err)
	}

	_, err := CompleteRefresh(paths, "map-build")

	if err == nil {
		t.Fatal("expected status-only agreement error")
	}
	if !strings.Contains(err.Error(), "project-cognition.db is missing") {
		t.Fatalf("error = %q, want missing DB", err.Error())
	}
}

func TestCompleteRefreshBlocksPristineMissingBaseline(t *testing.T) {
	paths := testPaths(t)

	_, err := CompleteRefresh(paths, "map-build")

	if err == nil {
		t.Fatal("expected missing baseline agreement error")
	}
	if !strings.Contains(err.Error(), "status.json and project-cognition.db are missing") {
		t.Fatalf("error = %q, want missing baseline", err.Error())
	}
	if _, statErr := os.Stat(paths.StatusPath); !os.IsNotExist(statErr) {
		t.Fatalf("status stat err = %v, want missing status", statErr)
	}
}

func TestRunUpdateWithDeltaSessionReturnsBoundaryResolved(t *testing.T) {
	paths := testPaths(t)
	session, err := delta.Begin(delta.BeginInput{
		Root:              paths.Root,
		RuntimeDir:        paths.RuntimeDir,
		OriginCommand:     "quick",
		InitialDirtyPaths: []string{},
	})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := delta.Append(delta.AppendInput{
		RuntimeDir:   paths.RuntimeDir,
		SessionID:    session.SessionID,
		EventType:    "worker_result",
		ChangedPaths: []string{"src/a.go"},
		Verification: []string{"go test ./... PASS"},
	}); err != nil {
		t.Fatal(err)
	}

	payload, err := RunUpdate(paths, UpdateInput{
		DeltaSessionID: session.SessionID,
		Reason:         "workflow-finalize",
	})
	if err != nil {
		t.Fatal(err)
	}

	if payload.Readiness == rt.ReadyReadiness {
		t.Fatalf("Readiness = %q, did not want ready", payload.Readiness)
	}
	if payload.UpdateOutcome != "boundary_resolved" {
		t.Fatalf("UpdateOutcome = %q, want boundary_resolved", payload.UpdateOutcome)
	}
	if payload.Boundary == nil {
		t.Fatal("Boundary is nil")
	}
	if payload.Boundary.BoundarySource != "delta_journal" {
		t.Fatalf("BoundarySource = %q, want delta_journal", payload.Boundary.BoundarySource)
	}
}

func TestRunUpdateWithDeltaSessionUsesResultStateContract(t *testing.T) {
	paths := testPaths(t)
	seedReadyRuntime(t, paths)
	session, err := delta.Begin(delta.BeginInput{
		Root:              paths.Root,
		RuntimeDir:        paths.RuntimeDir,
		OriginCommand:     "implement",
		InitialDirtyPaths: []string{},
	})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := delta.Append(delta.AppendInput{
		RuntimeDir:       paths.RuntimeDir,
		SessionID:        session.SessionID,
		EventType:        "workflow_closeout",
		ChangedPaths:     []string{"src/app.go"},
		BehaviorSurfaces: []string{"application entrypoint"},
		Verification:     []string{"go test ./... PASS"},
		KnownUnknowns:    []string{},
	}); err != nil {
		t.Fatal(err)
	}

	payload, err := RunUpdate(paths, UpdateInput{
		DeltaSessionID: session.SessionID,
		Reason:         "workflow-finalize",
	})
	if err != nil {
		t.Fatal(err)
	}
	if payload.ResultState != ResultReady {
		t.Fatalf("ResultState = %q, payload=%#v", payload.ResultState, payload)
	}
	if payload.StatusUpdate.LastUpdateOutcome != ResultReady {
		t.Fatalf("StatusUpdate = %#v", payload.StatusUpdate)
	}
}

func TestRunUpdateKeepsIgnoredPathsOutOfMinimalLiveReads(t *testing.T) {
	paths := testPaths(t)
	seedReadyRuntime(t, paths)
	if err := os.WriteFile(filepath.Join(paths.Root, ".cognitionignore"), []byte("vendor/\n"), 0o644); err != nil {
		t.Fatalf("write .cognitionignore: %v", err)
	}

	payload, err := RunUpdate(paths, UpdateInput{
		ChangedPaths: []string{"src/a.go", "vendor/a.go"},
		Reason:       "manual",
	})
	if err != nil {
		t.Fatal(err)
	}

	if containsString(payload.MinimalLiveReads, "vendor/a.go") {
		t.Fatalf("MinimalLiveReads = %v, did not want vendor/a.go", payload.MinimalLiveReads)
	}
	if !containsString(payload.IgnoredPaths, "vendor/a.go") {
		t.Fatalf("IgnoredPaths = %v, want vendor/a.go", payload.IgnoredPaths)
	}
	accounting, ok := payload.PathAdoption["path_accounting"].(map[string]boundary.PathAccounting)
	if !ok {
		t.Fatalf("path_accounting = %#v, want map[string]boundary.PathAccounting", payload.PathAdoption["path_accounting"])
	}
	if _, ok := accounting["vendor/a.go"]; !ok {
		t.Fatalf("path_accounting = %#v, want vendor/a.go", accounting)
	}

	st, err := store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	defer st.Close()
	var changedPathsJSON string
	if err := st.DB().QueryRowContext(context.Background(), `SELECT changed_paths_json FROM updates WHERE id = ?`, payload.UpdateID).Scan(&changedPathsJSON); err != nil {
		t.Fatal(err)
	}
	var recordedChangedPaths []string
	if err := json.Unmarshal([]byte(changedPathsJSON), &recordedChangedPaths); err != nil {
		t.Fatalf("parse recorded changed paths: %v", err)
	}
	if !containsString(recordedChangedPaths, "src/a.go") {
		t.Fatalf("recorded changed paths = %v, want src/a.go", recordedChangedPaths)
	}
	if containsString(recordedChangedPaths, "vendor/a.go") {
		t.Fatalf("recorded changed paths = %v, did not want vendor/a.go", recordedChangedPaths)
	}
}

func TestRunUpdateNoOpWhenAllChangedPathsAreIgnored(t *testing.T) {
	paths := testPaths(t)
	seedReadyRuntime(t, paths)
	if err := os.WriteFile(filepath.Join(paths.Root, ".cognitionignore"), []byte("vendor/\n"), 0o644); err != nil {
		t.Fatal(err)
	}

	payload, err := RunUpdate(paths, UpdateInput{
		ChangedPaths: []string{"vendor/a.go"},
		Reason:       "workflow-finalize",
	})
	if err != nil {
		t.Fatal(err)
	}
	if payload.ResultState != ResultNoOp {
		t.Fatalf("ResultState = %q, want %q", payload.ResultState, ResultNoOp)
	}
	if containsString(payload.MinimalLiveReads, "vendor/a.go") {
		t.Fatalf("MinimalLiveReads = %#v, did not want ignored path", payload.MinimalLiveReads)
	}
}

func TestRunUpdatePathOnlyUnknownCoverageReturnsPartialRefresh(t *testing.T) {
	paths := testPaths(t)
	seedReadyRuntime(t, paths)

	payload, err := RunUpdate(paths, UpdateInput{
		ChangedPaths: []string{"src/new-feature.go"},
		Reason:       "workflow-finalize",
	})
	if err != nil {
		t.Fatal(err)
	}
	if payload.ResultState != ResultPartialRefresh {
		t.Fatalf("ResultState = %q, want partial_refresh", payload.ResultState)
	}
	if payload.Readiness != "review" {
		t.Fatalf("Readiness = %q, want review", payload.Readiness)
	}
	if !containsString(payload.MinimalLiveReads, "src/new-feature.go") {
		t.Fatalf("MinimalLiveReads = %#v, want changed path", payload.MinimalLiveReads)
	}
	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	if status.LastUpdateOutcome != ResultPartialRefresh {
		t.Fatalf("LastUpdateOutcome = %q", status.LastUpdateOutcome)
	}
}

func TestRunUpdateAdoptsVerifiedUnindexedPath(t *testing.T) {
	paths := testPaths(t)
	seedReadyRuntime(t, paths)

	payload, err := RunUpdate(paths, UpdateInput{
		ChangedPaths:     []string{"src/new-feature.go"},
		Reason:           "workflow-finalize",
		Workflow:         "sp-quick",
		BehaviorSurfaces: []string{"new feature entrypoint"},
		Verification: []VerificationEvidence{
			{Command: "go test ./...", Result: "passed"},
		},
	})
	if err != nil {
		t.Fatal(err)
	}
	if payload.ResultState != ResultReady {
		t.Fatalf("ResultState = %q, payload=%#v", payload.ResultState, payload)
	}
	if !containsString(payload.AdoptedPaths, "src/new-feature.go") {
		t.Fatalf("AdoptedPaths = %#v, want new feature path", payload.AdoptedPaths)
	}
	if len(payload.AffectedNodes) == 0 {
		t.Fatalf("AffectedNodes = %#v, want adopted workflow update node", payload.AffectedNodes)
	}
	st, err := store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	defer st.Close()
	nodes, err := st.NodesForPaths(context.Background(), []string{"src/new-feature.go"})
	if err != nil {
		t.Fatal(err)
	}
	if len(nodes) == 0 {
		t.Fatal("expected adopted path to be queryable")
	}
}

func TestRunUpdatePayloadFileAcceptsVerificationEvidenceAlias(t *testing.T) {
	paths := testPaths(t)
	seedReadyRuntime(t, paths)
	payloadPath := filepath.Join(paths.RuntimeDir, "updates", "workflow-finalize.json")
	if err := os.MkdirAll(filepath.Dir(payloadPath), 0o755); err != nil {
		t.Fatal(err)
	}
	data := []byte(`{
  "workflow": "sp-fast",
  "reason": "workflow-finalize",
  "changed_paths": ["src/new-feature.go"],
  "behavior_surfaces": ["new feature entrypoint"],
  "verification_evidence": [
    {"command": "go test ./...", "result": "passed", "artifact": "artifacts/quality-runs/unit/report.md"}
  ],
  "known_unknowns": []
}`)
	if err := os.WriteFile(payloadPath, data, 0o644); err != nil {
		t.Fatal(err)
	}

	payload, err := RunUpdate(paths, UpdateInput{
		PayloadFile: payloadPath,
		Reason:      "workflow-finalize",
	})
	if err != nil {
		t.Fatal(err)
	}
	if payload.ResultState != ResultReady {
		t.Fatalf("ResultState = %q, payload=%#v", payload.ResultState, payload)
	}
	if !containsString(payload.AdoptedPaths, "src/new-feature.go") {
		t.Fatalf("AdoptedPaths = %#v, want payload alias path adoption", payload.AdoptedPaths)
	}
}

func TestRunUpdatePayloadFileAcceptsStringVerificationEvidenceAlias(t *testing.T) {
	paths := testPaths(t)
	seedReadyRuntime(t, paths)
	payloadPath := filepath.Join(paths.RuntimeDir, "updates", "workflow-finalize.json")
	if err := os.MkdirAll(filepath.Dir(payloadPath), 0o755); err != nil {
		t.Fatal(err)
	}
	data := []byte(`{
  "workflow": "sp-quick",
  "reason": "workflow-finalize",
  "changed_paths": ["src/string-evidence.go"],
  "behavior_surfaces": ["string evidence entrypoint"],
  "verification_evidence": ["go test ./... PASS"],
  "known_unknowns": []
}`)
	if err := os.WriteFile(payloadPath, data, 0o644); err != nil {
		t.Fatal(err)
	}

	payload, err := RunUpdate(paths, UpdateInput{
		PayloadFile: payloadPath,
		Reason:      "workflow-finalize",
	})
	if err != nil {
		t.Fatal(err)
	}
	if payload.ResultState != ResultReady {
		t.Fatalf("ResultState = %q, payload=%#v", payload.ResultState, payload)
	}
	if !containsString(payload.AdoptedPaths, "src/string-evidence.go") {
		t.Fatalf("AdoptedPaths = %#v, want string evidence path adoption", payload.AdoptedPaths)
	}
}

func TestRunUpdateFailedVerificationDoesNotReturnReady(t *testing.T) {
	paths := testPaths(t)
	seedReadyRuntime(t, paths)

	payload, err := RunUpdate(paths, UpdateInput{
		ChangedPaths:     []string{"src/app.go"},
		Reason:           "workflow-finalize",
		Workflow:         "sp-implement",
		BehaviorSurfaces: []string{"application entrypoint"},
		Verification: []VerificationEvidence{
			{Command: "go test ./...", Result: "failed"},
		},
	})
	if err != nil {
		t.Fatal(err)
	}
	if payload.ResultState == ResultReady {
		t.Fatalf("ResultState = %q, payload=%#v, want not ready for failed verification", payload.ResultState, payload)
	}
	if payload.Readiness == rt.ReadyReadiness {
		t.Fatalf("Readiness = %q, want not query_ready for failed verification", payload.Readiness)
	}
}

func TestRunUpdatePayloadForIndexedPathReturnsReady(t *testing.T) {
	paths := testPaths(t)
	seedReadyRuntime(t, paths)

	payload, err := RunUpdate(paths, UpdateInput{
		ChangedPaths:     []string{"src/app.go"},
		Reason:           "workflow-finalize",
		Workflow:         "sp-implement",
		BehaviorSurfaces: []string{"application entrypoint"},
		Verification: []VerificationEvidence{
			{Command: "go test ./...", Result: "passed", Artifact: "artifacts/quality-runs/example/report.md"},
		},
	})
	if err != nil {
		t.Fatal(err)
	}
	if payload.ResultState != ResultReady {
		t.Fatalf("ResultState = %q, payload=%#v", payload.ResultState, payload)
	}
	if payload.Readiness != rt.ReadyReadiness {
		t.Fatalf("Readiness = %q, want query_ready", payload.Readiness)
	}
	if len(payload.AffectedNodes) == 0 {
		t.Fatalf("AffectedNodes = %#v, want indexed node", payload.AffectedNodes)
	}
	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	if status.Freshness != rt.ReadyFreshness || status.LastUpdateOutcome != ResultReady {
		t.Fatalf("status = %#v", status)
	}
}

func TestRunUpdateRecordsAffectedClosure(t *testing.T) {
	paths := testPaths(t)
	seedReadyRuntime(t, paths)

	payload, err := RunUpdate(paths, UpdateInput{
		ChangedPaths: []string{"src/app.go"},
		Reason:       "workflow-finalize",
		Verification: []VerificationEvidence{
			{Command: "go test ./...", Result: "passed"},
		},
	})
	if err != nil {
		t.Fatal(err)
	}

	st, err := store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	defer st.Close()
	var nodesJSON, claimsJSON, slicesJSON string
	if err := st.DB().QueryRowContext(context.Background(), `SELECT affected_nodes_json, affected_claims_json, affected_slices_json FROM updates WHERE id = ?`, payload.UpdateID).Scan(&nodesJSON, &claimsJSON, &slicesJSON); err != nil {
		t.Fatal(err)
	}
	if !jsonArrayContains(t, nodesJSON, "N-app") {
		t.Fatalf("affected_nodes_json = %s, want N-app", nodesJSON)
	}
	if !jsonArrayContains(t, claimsJSON, "claim:app") {
		t.Fatalf("affected_claims_json = %s, want claim:app", claimsJSON)
	}
	if !jsonArrayContains(t, slicesJSON, "slice:runtime") {
		t.Fatalf("affected_slices_json = %s, want slice:runtime", slicesJSON)
	}
}

func TestCompleteRefreshBlocksSplitBrainBaselineBeforeStatusWrite(t *testing.T) {
	paths := testPaths(t)
	seedSplitBrainRuntime(t, paths)

	_, err := CompleteRefresh(paths, "manual")

	if err == nil {
		t.Fatal("expected split-brain agreement error")
	}
	if !strings.Contains(err.Error(), "rewrite_status_from_db_metadata") {
		t.Fatalf("error = %q, want rewrite_status_from_db_metadata", err.Error())
	}
	assertStatusActiveGeneration(t, paths, "GEN-old")
}

func TestMarkDirtyBlocksSplitBrainBaselineBeforeStatusWrite(t *testing.T) {
	paths := testPaths(t)
	seedSplitBrainRuntime(t, paths)

	_, err := MarkDirty(paths, DirtyInput{Reason: "manual", ScopePaths: []string{"src/app.go"}})

	if err == nil {
		t.Fatal("expected split-brain agreement error")
	}
	if !strings.Contains(err.Error(), "rewrite_status_from_db_metadata") {
		t.Fatalf("error = %q, want rewrite_status_from_db_metadata", err.Error())
	}
	assertStatusActiveGeneration(t, paths, "GEN-old")
}

func TestRunUpdateBlocksSplitBrainBaselineBeforeMutation(t *testing.T) {
	paths := testPaths(t)
	seedSplitBrainRuntime(t, paths)

	_, err := RunUpdate(paths, UpdateInput{
		ChangedPaths: []string{"src/app.go"},
		Reason:       "manual",
	})

	if err == nil {
		t.Fatal("expected split-brain agreement error")
	}
	if !strings.Contains(err.Error(), "rewrite_status_from_db_metadata") {
		t.Fatalf("error = %q, want rewrite_status_from_db_metadata", err.Error())
	}

	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	if status.LastUpdateID != "" {
		t.Fatalf("LastUpdateID = %q, want no mutation", status.LastUpdateID)
	}
	if status.ActiveGenerationID != "GEN-old" {
		t.Fatalf("ActiveGenerationID = %q, want GEN-old", status.ActiveGenerationID)
	}
}

func TestRunUpdateWithDeltaSessionBlocksSplitBrainBaselineBeforeMutation(t *testing.T) {
	paths := testPaths(t)
	seedSplitBrainRuntime(t, paths)
	session, err := delta.Begin(delta.BeginInput{
		Root:          paths.Root,
		RuntimeDir:    paths.RuntimeDir,
		OriginCommand: "quick",
	})
	if err != nil {
		t.Fatal(err)
	}

	_, err = RunUpdate(paths, UpdateInput{
		DeltaSessionID: session.SessionID,
		Reason:         "workflow-finalize",
	})

	if err == nil {
		t.Fatal("expected split-brain agreement error")
	}
	if !strings.Contains(err.Error(), "rewrite_status_from_db_metadata") {
		t.Fatalf("error = %q, want rewrite_status_from_db_metadata", err.Error())
	}
}

func TestRunUpdateWithDeltaSessionRecordsStatusMetadata(t *testing.T) {
	paths := testPaths(t)
	session, err := delta.Begin(delta.BeginInput{
		Root:          paths.Root,
		RuntimeDir:    paths.RuntimeDir,
		OriginCommand: "quick",
	})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := delta.Append(delta.AppendInput{
		RuntimeDir:   paths.RuntimeDir,
		SessionID:    session.SessionID,
		EventType:    "worker_result",
		ChangedPaths: []string{"src/a.go"},
	}); err != nil {
		t.Fatal(err)
	}

	if _, err := RunUpdate(paths, UpdateInput{
		DeltaSessionID: session.SessionID,
		Reason:         "workflow-finalize",
	}); err != nil {
		t.Fatal(err)
	}

	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	if status.LastDeltaSessionID != session.SessionID {
		t.Fatalf("LastDeltaSessionID = %q, want %q", status.LastDeltaSessionID, session.SessionID)
	}
	if status.LastUpdateOutcome != ResultPartialRefresh {
		t.Fatalf("LastUpdateOutcome = %q, want partial_refresh", status.LastUpdateOutcome)
	}
	if status.LastUpdateBoundary != "delta_journal" {
		t.Fatalf("LastUpdateBoundary = %q, want delta_journal", status.LastUpdateBoundary)
	}
}

func TestRunUpdateWithDeltaSessionSkipsAutoCommitInBoundaryOnlyLayer(t *testing.T) {
	paths := testPaths(t)
	session, err := delta.Begin(delta.BeginInput{
		Root:          paths.Root,
		RuntimeDir:    paths.RuntimeDir,
		OriginCommand: "quick",
	})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := delta.Append(delta.AppendInput{
		RuntimeDir:   paths.RuntimeDir,
		SessionID:    session.SessionID,
		EventType:    "worker_result",
		ChangedPaths: []string{"src/a.go"},
	}); err != nil {
		t.Fatal(err)
	}

	payload, err := RunUpdate(paths, UpdateInput{
		DeltaSessionID: session.SessionID,
		Reason:         "workflow-finalize",
	})
	if err != nil {
		t.Fatal(err)
	}

	if got := payload.PathAdoption["auto_commit_decision"]; got != "commit_skipped" {
		t.Fatalf("path adoption auto_commit_decision = %#v, want commit_skipped", got)
	}
	if payload.Boundary == nil {
		t.Fatal("Boundary is nil")
	}
	if payload.Boundary.AutoCommitDecision != "commit_skipped" {
		t.Fatalf("Boundary AutoCommitDecision = %q, want commit_skipped", payload.Boundary.AutoCommitDecision)
	}
	if !containsText(payload.KnownUnknowns, "auto-commit not attempted") {
		t.Fatalf("KnownUnknowns = %#v, want auto-commit not attempted warning", payload.KnownUnknowns)
	}
	if !containsText(payload.Boundary.Warnings, "auto-commit not attempted") {
		t.Fatalf("Boundary Warnings = %#v, want auto-commit not attempted warning", payload.Boundary.Warnings)
	}
}

func TestRunUpdateWithDeltaSessionRejectsMalformedCommitRange(t *testing.T) {
	paths := testPaths(t)
	session, err := delta.Begin(delta.BeginInput{
		Root:          paths.Root,
		RuntimeDir:    paths.RuntimeDir,
		OriginCommand: "quick",
	})
	if err != nil {
		t.Fatal(err)
	}

	if _, err := RunUpdate(paths, UpdateInput{
		DeltaSessionID: session.SessionID,
		CommitRange:    "bad-range",
		Reason:         "workflow-finalize",
	}); err == nil {
		t.Fatal("expected malformed commit range error")
	}
}

func TestGitDiffPathsFromCommitRangeReturnsErrorWhenGitDiffFails(t *testing.T) {
	_, err := gitDiffPathsFromCommitRange(t.TempDir(), "base..head")
	if err == nil {
		t.Fatal("expected git diff error")
	}
}

func TestGitDiffPathsFromCommitRangeRejectsOptionLikeBaseEndpoint(t *testing.T) {
	root := t.TempDir()
	_, err := gitDiffPathsFromCommitRange(root, "--output=probe..HEAD")
	if err == nil {
		t.Fatal("expected option-like commit range endpoint error")
	}
	if !strings.Contains(err.Error(), "invalid commit range endpoint") {
		t.Fatalf("error = %q, want invalid commit range endpoint", err.Error())
	}
	if _, statErr := os.Stat(filepath.Join(root, "probe")); !os.IsNotExist(statErr) {
		t.Fatalf("probe file stat err = %v, want not exist", statErr)
	}
}

func TestGitDiffPathsFromCommitRangeRejectsOptionLikeHeadEndpoint(t *testing.T) {
	_, err := gitDiffPathsFromCommitRange(t.TempDir(), "HEAD..--output=probe")
	if err == nil {
		t.Fatal("expected option-like commit range endpoint error")
	}
	if !strings.Contains(err.Error(), "invalid commit range endpoint") {
		t.Fatalf("error = %q, want invalid commit range endpoint", err.Error())
	}
}

func containsText(values []string, want string) bool {
	for _, value := range values {
		if strings.Contains(value, want) {
			return true
		}
	}
	return false
}

func seedSplitBrainRuntime(t *testing.T, paths rt.Paths) {
	t.Helper()
	seedRuntimeGeneration(t, paths, "GEN-db")
	status := rt.DefaultStatus(paths)
	status.Status = "ok"
	status.Freshness = rt.ReadyFreshness
	status.Readiness = rt.ReadyReadiness
	status.RecommendedNextAction = "use_project_cognition"
	status.GraphReady = true
	status.ActiveGenerationID = "GEN-old"
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}
}

func seedReadyRuntime(t *testing.T, paths rt.Paths) {
	t.Helper()
	seedRuntimeGeneration(t, paths, "GEN-db")
	status := rt.DefaultStatus(paths)
	status.Status = "ok"
	status.Freshness = rt.ReadyFreshness
	status.Readiness = rt.ReadyReadiness
	status.RecommendedNextAction = "use_project_cognition"
	status.GraphReady = true
	status.ActiveGenerationID = "GEN-db"
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}
}

func seedRuntimeGeneration(t *testing.T, paths rt.Paths, generationID string) {
	t.Helper()
	st, err := store.Open(paths)
	if err != nil {
		t.Fatal(err)
	}
	_, err = st.ImportGeneration(context.Background(), store.ImportInput{
		GenerationID: generationID,
		Kind:         "full",
		SourceCommit: "abc123",
		Evidence:     []store.EvidenceImport{{ID: "E-app", SourceKind: "file", SourcePath: "src/app.go", CommitSHA: "abc123", Extractor: "test", ContentHash: "hash-app"}},
		Nodes:        []store.NodeImport{{ID: "N-app", Type: "capability", Title: "App", Confidence: "verified", EvidenceIDs: []string{"E-app"}}},
		Claims: []store.ClaimImport{{
			ID:          "claim:app",
			SubjectRef:  "N-app",
			Predicate:   "owns",
			ObjectText:  "src/app.go",
			Confidence:  "verified",
			EvidenceIDs: []string{"E-app"},
		}},
		PathIndex:    []store.PathIndexImport{{ID: "P-app", Path: "src/app.go", NodeID: "N-app", Relation: "owns", Confidence: "verified", EvidenceID: "E-app"}},
		SliceMembers: []store.SliceMemberImport{{ID: "slice-member:app", SliceID: "slice:runtime", ObjectType: "node", ObjectID: "N-app", Rank: 1, Reason: "runtime entrypoint"}},
	})
	if err != nil {
		_ = st.Close()
		t.Fatal(err)
	}
	if _, _, err := st.PublishRuntimeMetadata(context.Background(), generationID, rt.BaselineKindBrownfieldFull); err != nil {
		_ = st.Close()
		t.Fatal(err)
	}
	if closeErr := st.Close(); closeErr != nil {
		t.Fatal(closeErr)
	}
}

func jsonArrayContains(t *testing.T, raw string, want string) bool {
	t.Helper()
	var values []string
	if err := json.Unmarshal([]byte(raw), &values); err != nil {
		t.Fatal(err)
	}
	return containsString(values, want)
}

func assertStatusActiveGeneration(t *testing.T, paths rt.Paths, want string) {
	t.Helper()
	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	if status.ActiveGenerationID != want {
		t.Fatalf("ActiveGenerationID = %q, want %q", status.ActiveGenerationID, want)
	}
}
