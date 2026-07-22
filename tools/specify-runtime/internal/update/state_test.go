package update

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/boundary"
	changemodel "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/changes/model"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/claim"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/delta"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/query"
	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtimegate"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/store"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/validation"
)

func TestRunUpdateInvalidatesOnlyAffectedGraphClaimsAndReportsIDs(t *testing.T) {
	paths := testPaths(t)
	seedReadyRuntime(t, paths)
	st, err := store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := st.DB().ExecContext(context.Background(), `INSERT INTO claims(id, generation_id, node_id, graph_claim_type, summary, state, prior_state, freshness, state_reason, attrs_json, created_at, updated_at) VALUES('claim:app-owner', 'GEN-db', 'N-app', 'runtime_owner', 'App owns runtime behavior', ?, '', ?, 'supporting_evidence', '{}', '2026-07-13T00:00:00Z', '2026-07-13T00:00:00Z')`, claim.StateSupported, claim.FreshnessFresh); err != nil {
		_ = st.Close()
		t.Fatal(err)
	}
	if _, err := st.DB().ExecContext(context.Background(), `INSERT INTO claim_evidence(claim_id, evidence_id, role) VALUES('claim:app-owner', 'E-app', 'supporting')`); err != nil {
		_ = st.Close()
		t.Fatal(err)
	}
	if _, err := st.DB().ExecContext(context.Background(), `INSERT INTO evidence(id, generation_id, source_kind, source_path, commit_sha, span, extractor, content_hash, captured_at, attrs_json) VALUES('E-other', 'GEN-db', 'source', 'src/other.go', 'abc123', '', 'test', 'hash-other', '2026-07-13T00:00:00Z', '{}')`); err != nil {
		_ = st.Close()
		t.Fatal(err)
	}
	if _, err := st.DB().ExecContext(context.Background(), `INSERT INTO nodes(id, generation_id, type, title, confidence, attrs_json, created_at, updated_at) VALUES('N-other', 'GEN-db', 'capability', 'Other', 'high', '{}', '2026-07-13T00:00:00Z', '2026-07-13T00:00:00Z')`); err != nil {
		_ = st.Close()
		t.Fatal(err)
	}
	if _, err := st.DB().ExecContext(context.Background(), `INSERT INTO path_index(id, generation_id, path, node_id, relation, confidence, evidence_id, updated_at) VALUES('P-other', 'GEN-db', 'src/other.go', 'N-other', 'owns', 'high', 'E-other', '2026-07-13T00:00:00Z')`); err != nil {
		_ = st.Close()
		t.Fatal(err)
	}
	if _, err := st.DB().ExecContext(context.Background(), `INSERT INTO claims(id, generation_id, node_id, graph_claim_type, summary, state, prior_state, freshness, state_reason, attrs_json, created_at, updated_at) VALUES('claim:other-owner', 'GEN-db', 'N-other', 'runtime_owner', 'Other owns unrelated behavior', ?, '', ?, 'supporting_evidence', '{}', '2026-07-13T00:00:00Z', '2026-07-13T00:00:00Z')`, claim.StateSupported, claim.FreshnessFresh); err != nil {
		_ = st.Close()
		t.Fatal(err)
	}
	if _, err := st.DB().ExecContext(context.Background(), `INSERT INTO claim_evidence(claim_id, evidence_id, role) VALUES('claim:other-owner', 'E-other', 'supporting')`); err != nil {
		_ = st.Close()
		t.Fatal(err)
	}
	if err := st.Close(); err != nil {
		t.Fatal(err)
	}

	payload, err := RunUpdate(paths, UpdateInput{ChangedPaths: []string{"src/app.go"}, Reason: "manual"})
	if err != nil {
		t.Fatal(err)
	}
	if len(payload.AffectedGraphClaims) != 1 || payload.AffectedGraphClaims[0] != "claim:app-owner" {
		t.Fatalf("AffectedGraphClaims = %#v, want claim:app-owner", payload.AffectedGraphClaims)
	}
	st, err = store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	defer st.Close()
	var state, priorState, freshness string
	if err := st.DB().QueryRowContext(context.Background(), `SELECT state, prior_state, freshness FROM claims WHERE id = 'claim:app-owner'`).Scan(&state, &priorState, &freshness); err != nil {
		t.Fatal(err)
	}
	if state != string(claim.StateStale) || priorState != string(claim.StateSupported) || freshness != string(claim.FreshnessStale) {
		t.Fatalf("claim lifecycle = %q/%q/%q, want stale/supported/stale", state, priorState, freshness)
	}
	if err := st.DB().QueryRowContext(context.Background(), `SELECT state, freshness FROM claims WHERE id = 'claim:other-owner'`).Scan(&state, &freshness); err != nil {
		t.Fatal(err)
	}
	if state != string(claim.StateSupported) || freshness != string(claim.FreshnessFresh) {
		t.Fatalf("unrelated claim lifecycle = %q/%q, want supported/fresh", state, freshness)
	}
}

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

func TestCompleteRefreshRejectsNonReadyLatestUpdateOutcomes(t *testing.T) {
	for _, outcome := range []string{ResultPartialRefresh, ResultBlocked, ResultRecorded} {
		t.Run(outcome, func(t *testing.T) {
			paths := testPaths(t)
			seedReadyRuntime(t, paths)
			seedLatestUpdateOutcome(t, paths, "upd-non-ready", outcome)

			_, err := CompleteRefresh(paths, "map-update")

			if err == nil {
				t.Fatalf("CompleteRefresh accepted latest update outcome %q", outcome)
			}
			if !strings.Contains(err.Error(), outcome) {
				t.Fatalf("error = %q, want latest update outcome %q", err.Error(), outcome)
			}
			status, readErr := rt.ReadStatus(paths)
			if readErr != nil {
				t.Fatal(readErr)
			}
			if status.LastUpdateOutcome != outcome {
				t.Fatalf("LastUpdateOutcome = %q, want unchanged %q", status.LastUpdateOutcome, outcome)
			}
		})
	}
}

func TestCompleteRefreshRequiresValidationReceiptForLatestReadyUpdate(t *testing.T) {
	paths := testPaths(t)
	seedReadyRuntime(t, paths)
	payload, err := RunUpdate(paths, UpdateInput{
		ChangedPaths: []string{"src/app.go"},
		Reason:       "workflow-finalize",
		Verification: []VerificationEvidence{{Command: "go test ./...", Result: "passed"}},
	})
	if err != nil {
		t.Fatal(err)
	}
	if payload.ResultState != ResultReady {
		t.Fatalf("ResultState = %q, want ready", payload.ResultState)
	}

	_, err = CompleteRefresh(paths, "map-update")

	if err == nil {
		t.Fatal("CompleteRefresh accepted a ready update without a validate-build receipt")
	}
	if !strings.Contains(err.Error(), "validate-build") {
		t.Fatalf("error = %q, want validate-build receipt guidance", err.Error())
	}
}

func TestCommittedFinalizableUpdateRecoversThroughValidateAndCompleteRefreshAfterStatusLoss(t *testing.T) {
	paths := testPaths(t)
	writeUpdateMatchingScanPackage(t, paths)
	seedReadyRuntime(t, paths)
	if err := os.WriteFile(filepath.Join(paths.Root, ".cognitionignore"), []byte("vendor/\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	baselineStatus, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	payload, err := RunUpdate(paths, UpdateInput{
		ChangedPaths: []string{"vendor/generated.go"},
		Reason:       "workflow-finalize",
		Workflow:     "sp-review",
		Verification: []VerificationEvidence{{Command: "go test ./...", Result: "passed"}},
	})
	if err != nil {
		t.Fatal(err)
	}
	if payload.ResultState != ResultNoOp {
		t.Fatalf("ResultState = %q, want no_op", payload.ResultState)
	}

	// Model a process/filesystem failure after the SQLite transaction committed
	// but before the new status snapshot became durable.
	if err := rt.WriteStatus(paths, baselineStatus); err != nil {
		t.Fatal(err)
	}
	if agreement := runtimegate.Check(paths); agreement.CauseCode != runtimegate.CauseStatusLatestUpdateMismatch {
		t.Fatalf("agreement = %#v, want latest-update mismatch", agreement)
	}
	repaired, err := runtimegate.RepairStatusFromDB(paths)
	if err != nil {
		t.Fatal(err)
	}
	if !repaired.Dirty || repaired.LastUpdateID != payload.UpdateID || repaired.LastUpdateOutcome != ResultNoOp {
		t.Fatalf("repaired status = %#v, want conservative recovered finalizable update", repaired)
	}
	if agreement := runtimegate.Check(paths); agreement.CauseCode != runtimegate.CauseUpdateFinalizationPending {
		t.Fatalf("agreement = %#v, want pending receipt-bound finalization", agreement)
	}

	gate := validation.ValidateBuild(paths)
	if gate.Status != "ok" || gate.Readiness != rt.ReadyReadiness {
		t.Fatalf("ValidateBuild = %#v, want successful build acceptance", gate)
	}
	if err := RecordValidateBuildReceipt(paths, gate.Status, gate.Gate, gate.Readiness); err != nil {
		t.Fatal(err)
	}
	finalized, err := CompleteRefresh(paths, "validated-recovered-update")
	if err != nil {
		t.Fatalf("CompleteRefresh after repair returned error: %v", err)
	}
	if !cleanRefreshStatus(finalized) || finalized.LastFinalizedUpdateID != payload.UpdateID {
		t.Fatalf("finalized status = %#v, want clean finalized recovered update", finalized)
	}
	if agreement := runtimegate.Check(paths); agreement.Status != "ok" {
		t.Fatalf("final agreement = %#v, want ok", agreement)
	}
}

func TestConcurrentRunUpdateHonorsCrossProcessLockAndCommitsOnePendingUpdate(t *testing.T) {
	paths := testPaths(t)
	seedReadyRuntime(t, paths)
	releaseExternalLock, err := rt.AcquireUpdateLock(paths)
	if err != nil {
		t.Fatal(err)
	}
	lockPresent := true
	t.Cleanup(func() {
		if lockPresent {
			releaseExternalLock()
		}
	})

	type updateResult struct {
		payload UpdatePayload
		err     error
	}
	results := make(chan updateResult, 2)
	start := make(chan struct{})
	for _, reason := range []string{"concurrent-update-a", "concurrent-update-b"} {
		reason := reason
		go func() {
			<-start
			payload, err := RunUpdate(paths, UpdateInput{
				ChangedPaths: []string{"src/app.go"},
				Reason:       reason,
				Verification: []VerificationEvidence{{Command: "go test ./...", Result: "passed"}},
			})
			results <- updateResult{payload: payload, err: err}
		}()
	}
	close(start)

	select {
	case early := <-results:
		releaseExternalLock()
		lockPresent = false
		<-results
		t.Fatalf("RunUpdate bypassed external update lock: payload=%#v err=%v", early.payload, early.err)
	case <-time.After(750 * time.Millisecond):
	}
	releaseExternalLock()
	lockPresent = false

	first := <-results
	second := <-results
	successes := 0
	blocked := 0
	for _, result := range []updateResult{first, second} {
		if result.err == nil {
			successes++
			if result.payload.ResultState != ResultReady {
				t.Fatalf("successful payload = %#v, want ready", result.payload)
			}
			continue
		}
		if strings.Contains(result.err.Error(), runtimegate.FinalizeUpdateAction) {
			blocked++
			continue
		}
		t.Fatalf("concurrent RunUpdate returned unexpected error: %v", result.err)
	}
	if successes != 1 || blocked != 1 {
		t.Fatalf("concurrent results successes/blocked = %d/%d, want 1/1", successes, blocked)
	}

	st, err := store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	defer st.Close()
	var updateCount int
	if err := st.DB().QueryRowContext(context.Background(), `SELECT COUNT(*) FROM updates WHERE generation_id = 'GEN-db'`).Scan(&updateCount); err != nil {
		t.Fatal(err)
	}
	if updateCount != 1 {
		t.Fatalf("update count = %d, want exactly one committed update", updateCount)
	}
	agreement := runtimegate.Check(paths)
	if agreement.CauseCode != runtimegate.CauseUpdateFinalizationPending || agreement.StatusLatestUpdateID != agreement.DBLatestUpdateID {
		t.Fatalf("agreement = %#v, want one matching pending update", agreement)
	}
}

func TestReceiptAndFinalizationHonorCrossProcessUpdateLock(t *testing.T) {
	paths := testPaths(t)
	seedReadyRuntime(t, paths)
	seedValidatedReadyUpdate(t, paths)

	assertWaitsForExternalUpdateLock(t, paths, func() error {
		return RecordValidateBuildReceipt(paths, "ok", "build_acceptance", rt.ReadyReadiness)
	})
	assertWaitsForExternalUpdateLock(t, paths, func() error {
		_, err := CompleteRefresh(paths, "validated-update")
		return err
	})

	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	if !cleanRefreshStatus(status) || status.LastFinalizedUpdateID != "upd-validated" {
		t.Fatalf("final status = %#v, want clean finalized update", status)
	}
}

func assertWaitsForExternalUpdateLock(t *testing.T, paths rt.Paths, operation func() error) {
	t.Helper()
	releaseExternalLock, err := rt.AcquireUpdateLock(paths)
	if err != nil {
		t.Fatal(err)
	}
	locked := true
	t.Cleanup(func() {
		if locked {
			releaseExternalLock()
		}
	})

	done := make(chan error, 1)
	go func() { done <- operation() }()
	select {
	case err := <-done:
		releaseExternalLock()
		locked = false
		t.Fatalf("operation bypassed external update lock: %v", err)
	case <-time.After(250 * time.Millisecond):
	}
	releaseExternalLock()
	locked = false
	select {
	case err := <-done:
		if err != nil {
			t.Fatalf("operation failed after update lock release: %v", err)
		}
	case <-time.After(5 * time.Second):
		t.Fatal("operation did not resume after update lock release")
	}
}

func TestCompleteRefreshRecordsGitBaselineCommit(t *testing.T) {
	paths := testPaths(t)
	seedReadyRuntime(t, paths)
	seedValidatedReadyUpdate(t, paths)
	initGitRepositoryForUpdateTest(t, paths.Root)

	before, err := rt.GitHead(paths.Root)
	if err != nil {
		t.Fatalf("GitHead before complete refresh: %v", err)
	}

	status, err := CompleteRefresh(paths, "map-update")
	if err != nil {
		t.Fatalf("CompleteRefresh returned error: %v", err)
	}

	if status.LastRefreshGitCommit != before {
		t.Fatalf("LastRefreshGitCommit = %q, want %q", status.LastRefreshGitCommit, before)
	}
	if status.LastRefreshGitBranch == "" {
		t.Fatal("LastRefreshGitBranch is empty")
	}
	if status.LastFinalizedUpdateID != status.LastUpdateID {
		t.Fatalf("LastFinalizedUpdateID = %q, want latest update %q", status.LastFinalizedUpdateID, status.LastUpdateID)
	}
}

func TestRecordRefreshRecordsGitBaselineCommitWhenGitExists(t *testing.T) {
	paths := testPaths(t)
	seedReadyRuntime(t, paths)
	seedValidatedReadyUpdate(t, paths)
	initGitRepositoryForUpdateTest(t, paths.Root)

	want, err := rt.GitHead(paths.Root)
	if err != nil {
		t.Fatalf("GitHead before record refresh: %v", err)
	}

	status, err := RecordRefresh(paths, "map-update")
	if err != nil {
		t.Fatalf("RecordRefresh returned error: %v", err)
	}

	if status.LastRefreshGitCommit != want {
		t.Fatalf("LastRefreshGitCommit = %q, want %q", status.LastRefreshGitCommit, want)
	}
	if status.LastRefreshGitBranch == "" {
		t.Fatal("LastRefreshGitBranch is empty")
	}
}

func TestRecordRefreshDoesNotFailOutsideGitRepository(t *testing.T) {
	paths := testPaths(t)
	seedReadyRuntime(t, paths)
	seedValidatedReadyUpdate(t, paths)

	status, err := RecordRefresh(paths, "manual")
	if err != nil {
		t.Fatalf("RecordRefresh returned error outside git repository: %v", err)
	}
	if status.LastRefreshGitCommit != "" {
		t.Fatalf("LastRefreshGitCommit = %q, want empty outside git", status.LastRefreshGitCommit)
	}
}

func TestRecordRefreshRejectsUnvalidatedStatusOnlyBaseline(t *testing.T) {
	paths := testPaths(t)
	seedReadyRuntime(t, paths)

	_, err := RecordRefresh(paths, "manual")
	if err == nil {
		t.Fatal("RecordRefresh accepted a baseline without a validated update receipt")
	}
	if !strings.Contains(err.Error(), "latest update") {
		t.Fatalf("error = %q, want latest update diagnostic", err.Error())
	}
}

func TestClearDirtyRejectsUnvalidatedDirtyState(t *testing.T) {
	paths := testPaths(t)
	seedReadyRuntime(t, paths)
	if _, err := MarkDirty(paths, DirtyInput{Reason: "unfinished", ScopePaths: []string{"src/app.go"}}); err != nil {
		t.Fatal(err)
	}

	_, err := ClearDirty(paths)
	if err == nil {
		t.Fatal("ClearDirty accepted unvalidated dirty state")
	}
	status, readErr := rt.ReadStatus(paths)
	if readErr != nil {
		t.Fatal(readErr)
	}
	if !status.Dirty || status.Status != "stale" {
		t.Fatalf("status = %#v, want dirty state preserved", status)
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
	seedReadyRuntime(t, paths)
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

func TestRunUpdateWithDeltaSessionDoesNotInferPassedResultFromFreeFormText(t *testing.T) {
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
	if payload.ResultState != ResultPartialRefresh {
		t.Fatalf("ResultState = %q, payload=%#v, want partial_refresh", payload.ResultState, payload)
	}
	if payload.StatusUpdate.LastUpdateOutcome != ResultPartialRefresh {
		t.Fatalf("StatusUpdate = %#v", payload.StatusUpdate)
	}
}

func TestRunUpdateWithDeltaSessionAcceptsStructuredVerificationJSON(t *testing.T) {
	paths := testPaths(t)
	seedReadyRuntime(t, paths)
	session, err := delta.Begin(delta.BeginInput{
		Root:          paths.Root,
		RuntimeDir:    paths.RuntimeDir,
		OriginCommand: "implement",
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
		Verification:     []string{`{"command":"go test ./...","result":"passed","artifact":"artifacts/unit.json"}`},
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
	if payload.ResultState != ResultReady || payload.Readiness != rt.ReadyReadiness {
		t.Fatalf("payload = %#v, want ready from structured delta verification", payload)
	}
}

func TestRunUpdateWithDeltaSessionMergesEvidenceForSameTypedPathAcrossEvents(t *testing.T) {
	paths := testPaths(t)
	seedReadyRuntime(t, paths)
	session, err := delta.Begin(delta.BeginInput{
		Root:          paths.Root,
		RuntimeDir:    paths.RuntimeDir,
		OriginCommand: "implement",
	})
	if err != nil {
		t.Fatal(err)
	}
	disposition := changemodel.DispositionAdoptable
	for index, evidenceRef := range []string{"test:event-a", "test:event-b"} {
		verification := []string{}
		if index == 1 {
			verification = []string{`{"command":"go test ./...","result":"passed"}`}
		}
		if _, err := delta.Append(delta.AppendInput{
			RuntimeDir: paths.RuntimeDir,
			SessionID:  session.SessionID,
			EventType:  "workflow_closeout",
			PathChanges: []changemodel.PathChange{{
				Path:         "src/app.go",
				Operation:    changemodel.OperationModify,
				NodeID:       "N-app",
				Disposition:  &disposition,
				EvidenceRefs: []string{evidenceRef},
			}},
			Verification: verification,
		}); err != nil {
			t.Fatal(err)
		}
	}

	payload, err := RunUpdate(paths, UpdateInput{
		DeltaSessionID: session.SessionID,
		Reason:         "workflow-finalize",
	})
	if err != nil {
		t.Fatal(err)
	}
	if payload.ResultState != ResultReady || len(payload.PathChanges) != 1 {
		t.Fatalf("payload = %#v, want one ready merged path change", payload)
	}
	refs := payload.PathChanges[0].EvidenceRefs
	if len(refs) != 2 || !containsString(refs, "test:event-a") || !containsString(refs, "test:event-b") {
		t.Fatalf("EvidenceRefs = %#v, want both delta event references", refs)
	}
}

func TestRunUpdateDeltaCannotMutateCognitionIgnoredTypedPath(t *testing.T) {
	paths := testPaths(t)
	seedReadyRuntime(t, paths)
	if err := os.WriteFile(filepath.Join(paths.Root, ".cognitionignore"), []byte("vendor/\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	session, err := delta.Begin(delta.BeginInput{
		Root:          paths.Root,
		RuntimeDir:    paths.RuntimeDir,
		OriginCommand: "implement",
	})
	if err != nil {
		t.Fatal(err)
	}
	disposition := changemodel.DispositionAdoptable
	if _, err := delta.Append(delta.AppendInput{
		RuntimeDir: paths.RuntimeDir,
		SessionID:  session.SessionID,
		EventType:  "workflow_closeout",
		PathChanges: []changemodel.PathChange{{
			Path:        "vendor/new.go",
			Operation:   changemodel.OperationAdd,
			Disposition: &disposition,
		}},
		Verification: []string{`{"command":"go test ./...","result":"passed"}`},
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
	if len(payload.AdoptedPaths) != 0 || !containsString(payload.IgnoredPaths, "vendor/new.go") {
		t.Fatalf("payload = %#v, want ignored path without graph adoption", payload)
	}
	st, err := store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	defer st.Close()
	mapped, err := st.NodeIDsForExactPaths(context.Background(), []string{"vendor/new.go"})
	if err != nil {
		t.Fatal(err)
	}
	if mapped["vendor/new.go"] != "" {
		t.Fatalf("ignored path mapped to %q", mapped["vendor/new.go"])
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
	if containsString(recordedChangedPaths, "src/a.go") {
		t.Fatalf("recorded changed paths = %v, did not want review-only src/a.go treated as a graph mutation", recordedChangedPaths)
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

func TestRunUpdateConvertsRenameIntoIgnoredTargetToDeleteOldPathCoverage(t *testing.T) {
	paths := testPaths(t)
	seedReadyRuntime(t, paths)
	if err := os.WriteFile(filepath.Join(paths.Root, ".cognitionignore"), []byte("vendor/\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	disposition := changemodel.DispositionAdoptable
	payload, err := RunUpdate(paths, UpdateInput{
		ChangedPaths: []string{"vendor/renamed-app.go"},
		PathChanges: []changemodel.PathChange{{
			Path:         "vendor/renamed-app.go",
			OldPath:      "src/app.go",
			Operation:    changemodel.OperationRename,
			NodeID:       "N-app",
			Disposition:  &disposition,
			EvidenceRefs: []string{"test:rename-into-ignore"},
		}},
		Reason:       "workflow-finalize",
		Verification: []VerificationEvidence{{Command: "go test ./...", Result: "passed"}},
	})
	if err != nil {
		t.Fatal(err)
	}
	if payload.ResultState != ResultReady {
		t.Fatalf("ResultState = %q, payload=%#v, want ready delete", payload.ResultState, payload)
	}
	if !containsString(payload.IgnoredPaths, "vendor/renamed-app.go") {
		t.Fatalf("IgnoredPaths = %#v, want ignored rename target", payload.IgnoredPaths)
	}
	if len(payload.PathChanges) != 1 || payload.PathChanges[0].Path != "src/app.go" || payload.PathChanges[0].OldPath != "" || payload.PathChanges[0].Operation != changemodel.OperationDelete {
		t.Fatalf("PathChanges = %#v, want old path converted to delete", payload.PathChanges)
	}

	st, err := store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	defer st.Close()
	mapped, err := st.NodeIDsForExactPaths(context.Background(), []string{"src/app.go", "vendor/renamed-app.go"})
	if err != nil {
		t.Fatal(err)
	}
	if mapped["src/app.go"] != "" || mapped["vendor/renamed-app.go"] != "" {
		t.Fatalf("path mappings = %#v, want old coverage removed and ignored target absent", mapped)
	}
}

func TestRunUpdateDoesNotLetNoOpMaskExistingDirtyState(t *testing.T) {
	paths := testPaths(t)
	seedReadyRuntime(t, paths)
	if _, err := MarkDirty(paths, DirtyInput{
		Reason:     "existing stale work",
		ScopePaths: []string{"src/app.go"},
	}); err != nil {
		t.Fatal(err)
	}
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
	if payload.ResultState != ResultPartialRefresh {
		t.Fatalf("ResultState = %q, want partial_refresh while prior dirty state remains", payload.ResultState)
	}
	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	if !status.Dirty || status.Freshness == rt.ReadyFreshness || status.Readiness == rt.ReadyReadiness {
		t.Fatalf("status = %#v, want existing dirty/stale state preserved", status)
	}
	if !containsString(status.StalePaths, "src/app.go") {
		t.Fatalf("StalePaths = %#v, want src/app.go", status.StalePaths)
	}
}

func TestRunUpdateRejectsInvalidVerificationEvidenceBeforeMutation(t *testing.T) {
	tests := []struct {
		name         string
		verification VerificationEvidence
	}{
		{name: "missing command", verification: VerificationEvidence{Result: "passed"}},
		{name: "missing result", verification: VerificationEvidence{Command: "go test ./..."}},
		{name: "pass alias", verification: VerificationEvidence{Command: "go test ./...", Result: "pass"}},
		{name: "success alias", verification: VerificationEvidence{Command: "go test ./...", Result: "success"}},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			paths := testPaths(t)
			seedReadyRuntime(t, paths)

			_, err := RunUpdate(paths, UpdateInput{
				ChangedPaths: []string{"src/app.go"},
				Reason:       "workflow-finalize",
				Verification: []VerificationEvidence{tt.verification},
			})

			if err == nil {
				t.Fatalf("RunUpdate accepted invalid verification %#v", tt.verification)
			}
			if !strings.Contains(err.Error(), "verification") {
				t.Fatalf("error = %q, want verification diagnostic", err.Error())
			}
			status, readErr := rt.ReadStatus(paths)
			if readErr != nil {
				t.Fatal(readErr)
			}
			if status.LastUpdateID != "" {
				t.Fatalf("LastUpdateID = %q, want no mutation", status.LastUpdateID)
			}
		})
	}
}

func TestVerificationEvidenceFromTextDoesNotInferSubstringPass(t *testing.T) {
	for _, value := range []string{
		"go test ./... bypass",
		"go test ./... not passed",
		"go test ./... PASS",
	} {
		evidence := verificationEvidenceFromText(value)
		if evidence.Result != ResultRecorded {
			t.Fatalf("verificationEvidenceFromText(%q).Result = %q, want recorded", value, evidence.Result)
		}
	}
}

func TestNormalizePathChangesMergesCrossEventEvidenceAndRejectsNodeConflict(t *testing.T) {
	disposition := changemodel.DispositionAdoptable
	merged, err := normalizePathChanges([]changemodel.PathChange{
		{
			Path:         "src/app.go",
			Operation:    changemodel.OperationModify,
			NodeID:       "N-app",
			Disposition:  &disposition,
			EvidenceRefs: []string{"test:event-b"},
		},
		{
			Path:         "./src/app.go",
			Operation:    changemodel.OperationModify,
			NodeID:       "N-app",
			Disposition:  &disposition,
			EvidenceRefs: []string{"test:event-a", "test:event-b"},
		},
	})
	if err != nil {
		t.Fatal(err)
	}
	if len(merged) != 1 || merged[0].NodeID != "N-app" || len(merged[0].EvidenceRefs) != 2 ||
		merged[0].EvidenceRefs[0] != "test:event-a" || merged[0].EvidenceRefs[1] != "test:event-b" {
		t.Fatalf("merged path changes = %#v, want one row with cumulative evidence", merged)
	}

	_, err = normalizePathChanges([]changemodel.PathChange{
		{Path: "src/app.go", Operation: changemodel.OperationModify, NodeID: "N-app", Disposition: &disposition},
		{Path: "src/app.go", Operation: changemodel.OperationModify, NodeID: "N-other", Disposition: &disposition},
	})
	if err == nil || !strings.Contains(err.Error(), "conflicting path changes") {
		t.Fatalf("normalizePathChanges node conflict error = %v, want fail-closed conflict", err)
	}
}

func TestRunUpdateBlocksMissingBaselineWithoutWritingStatus(t *testing.T) {
	paths := testPaths(t)

	_, err := RunUpdate(paths, UpdateInput{
		ChangedPaths: []string{"src/app.go"},
		Reason:       "workflow-finalize",
	})

	if err == nil {
		t.Fatal("RunUpdate accepted a missing baseline")
	}
	if !strings.Contains(err.Error(), "run_map_scan_build") {
		t.Fatalf("error = %q, want rebuild guidance", err.Error())
	}
	if _, statErr := os.Stat(paths.StatusPath); !os.IsNotExist(statErr) {
		t.Fatalf("status stat err = %v, want status.json to remain missing", statErr)
	}
}

func TestRunUpdateBlocksNeedsRebuildBaselineWithoutMutation(t *testing.T) {
	paths := testPaths(t)
	seedReadyRuntime(t, paths)
	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	status.Status = "missing"
	status.Freshness = rt.MissingFreshness
	status.Readiness = rt.NeedsRebuildReadiness
	status.RecommendedNextAction = "run_map_scan_build"
	status.GraphReady = false
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}

	_, err = RunUpdate(paths, UpdateInput{
		ChangedPaths: []string{"src/app.go"},
		Reason:       "workflow-finalize",
	})

	if err == nil {
		t.Fatal("RunUpdate accepted a needs_rebuild baseline")
	}
	status, readErr := rt.ReadStatus(paths)
	if readErr != nil {
		t.Fatal(readErr)
	}
	if status.LastUpdateID != "" || status.Status != "missing" || status.Readiness != rt.NeedsRebuildReadiness {
		t.Fatalf("status = %#v, want needs_rebuild baseline unchanged", status)
	}
	st, openErr := store.OpenExisting(paths)
	if openErr != nil {
		t.Fatal(openErr)
	}
	defer st.Close()
	var count int
	if err := st.DB().QueryRowContext(context.Background(), `SELECT COUNT(*) FROM updates`).Scan(&count); err != nil {
		t.Fatal(err)
	}
	if count != 0 {
		t.Fatalf("update count = %d, want zero", count)
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
	if !containsString(payload.PartialRefreshReasons, "changed_paths_missing_active_path_index") {
		t.Fatalf("PartialRefreshReasons = %#v, want missing path_index diagnostic", payload.PartialRefreshReasons)
	}
	if !containsString(payload.PartialRefreshReasons, "missing_passing_verification_result") {
		t.Fatalf("PartialRefreshReasons = %#v, want missing verification diagnostic", payload.PartialRefreshReasons)
	}
	reasons, ok := payload.PathAdoption["partial_refresh_reasons"].([]string)
	if !ok {
		t.Fatalf("path adoption partial_refresh_reasons = %#v, want []string", payload.PathAdoption["partial_refresh_reasons"])
	}
	if !containsString(reasons, "missing_passing_verification_result") {
		t.Fatalf("path adoption partial_refresh_reasons = %#v, want missing verification", reasons)
	}
	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	if status.LastUpdateOutcome != ResultPartialRefresh {
		t.Fatalf("LastUpdateOutcome = %q", status.LastUpdateOutcome)
	}
}

func TestRunUpdatePayloadFileAppliesTypedRename(t *testing.T) {
	paths := testPaths(t)
	seedReadyRuntime(t, paths)
	payloadPath := filepath.Join(paths.RuntimeDir, "updates", "typed-rename.json")
	if err := os.MkdirAll(filepath.Dir(payloadPath), 0o755); err != nil {
		t.Fatal(err)
	}
	data := []byte(`{
  "workflow": "sp-implement",
  "reason": "workflow-finalize",
  "changed_paths": ["src/renamed-app.go"],
  "path_changes": [{
    "path": "src/renamed-app.go",
    "old_path": "src/app.go",
    "operation": "rename",
    "node_id": "N-app",
    "disposition": "adoptable",
    "evidence_refs": ["test:rename"]
  }],
  "behavior_surfaces": ["application entrypoint"],
  "verification": [{"command": "go test ./...", "result": "passed"}],
  "known_unknowns": []
}`)
	if err := os.WriteFile(payloadPath, data, 0o644); err != nil {
		t.Fatal(err)
	}

	payload, err := RunUpdate(paths, UpdateInput{PayloadFile: payloadPath})
	if err != nil {
		t.Fatal(err)
	}
	if payload.ResultState != ResultReady {
		t.Fatalf("ResultState = %q, payload=%#v", payload.ResultState, payload)
	}
	if len(payload.PathChanges) != 1 || payload.PathChanges[0].Operation != changemodel.OperationRename {
		t.Fatalf("PathChanges = %#v, want typed rename", payload.PathChanges)
	}
	st, err := store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	defer st.Close()
	mapped, err := st.NodeIDsForExactPaths(context.Background(), []string{"src/app.go", "src/renamed-app.go"})
	if err != nil {
		t.Fatal(err)
	}
	if mapped["src/app.go"] != "" || mapped["src/renamed-app.go"] != "N-app" {
		t.Fatalf("mapped paths = %#v, want old path removed and new path mapped", mapped)
	}
}

func TestRunUpdateRejectsUnixAbsoluteTypedPathBeforeMutation(t *testing.T) {
	paths := testPaths(t)
	seedReadyRuntime(t, paths)
	disposition := changemodel.DispositionAdoptable

	_, err := RunUpdate(paths, UpdateInput{
		PathChanges: []changemodel.PathChange{{
			Path:        "/tmp/outside-repository.go",
			Operation:   changemodel.OperationAdd,
			Disposition: &disposition,
		}},
		Reason:       "workflow-finalize",
		Workflow:     "sp-implement",
		Verification: []VerificationEvidence{{Command: "go test ./...", Result: "passed"}},
	})
	if err == nil || !strings.Contains(err.Error(), "concrete repository-relative path") {
		t.Fatalf("RunUpdate error = %v, want absolute typed path rejection", err)
	}
}

func TestRunUpdatePayloadFileAppliesUnknownPathAgentDisposition(t *testing.T) {
	paths := testPaths(t)
	seedReadyRuntime(t, paths)
	payloadPath := filepath.Join(paths.RuntimeDir, "updates", "agent-disposition.json")
	if err := os.MkdirAll(filepath.Dir(payloadPath), 0o755); err != nil {
		t.Fatal(err)
	}
	data := []byte(`{
  "workflow": "sp-implement",
  "reason": "workflow-finalize",
  "changed_paths": ["src/new-feature.go"],
  "path_changes": [{
    "path": "src/new-feature.go",
    "operation": "add"
  }],
  "unknown_path_dispositions": [{
    "path": "src/new-feature.go",
    "agent_disposition": "adoptable"
  }],
  "verification": [{"command": "go test ./...", "result": "passed"}]
}`)
	if err := os.WriteFile(payloadPath, data, 0o644); err != nil {
		t.Fatal(err)
	}

	payload, err := RunUpdate(paths, UpdateInput{PayloadFile: payloadPath})
	if err != nil {
		t.Fatal(err)
	}
	if payload.ResultState != ResultReady || len(payload.AdoptedPaths) != 1 || payload.AdoptedPaths[0] != "src/new-feature.go" {
		t.Fatalf("payload = %#v, want agent disposition applied as adoptable", payload)
	}
}

func TestRunUpdateTypedRenameClearsDirtyOldPathScope(t *testing.T) {
	paths := testPaths(t)
	seedReadyRuntime(t, paths)
	if _, err := MarkDirty(paths, DirtyInput{
		Reason:     "workflow-finalize",
		ScopePaths: []string{"src/app.go"},
	}); err != nil {
		t.Fatal(err)
	}
	disposition := changemodel.DispositionAdoptable

	payload, err := RunUpdate(paths, UpdateInput{
		ChangedPaths: []string{"src/renamed-app.go"},
		PathChanges: []changemodel.PathChange{{
			Path:        "src/renamed-app.go",
			OldPath:     "src/app.go",
			Operation:   changemodel.OperationRename,
			NodeID:      "N-app",
			Disposition: &disposition,
		}},
		Reason:       "workflow-finalize",
		Workflow:     "sp-implement",
		Verification: []VerificationEvidence{{Command: "go test ./...", Result: "passed"}},
	})
	if err != nil {
		t.Fatal(err)
	}
	if payload.ResultState != ResultReady {
		t.Fatalf("payload = %#v, want ready rename covering old dirty scope", payload)
	}
	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	if status.Dirty || len(status.StalePaths) != 0 || len(status.DirtyScopePaths) != 0 {
		t.Fatalf("status = %#v, want old rename scope cleared", status)
	}
}

func TestRunUpdateBoundsClosureFromExplicitExistingNodeOnAdd(t *testing.T) {
	paths := testPaths(t)
	seedReadyRuntime(t, paths)
	st, err := store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	for index := 1; index <= 2; index++ {
		nodeID := fmt.Sprintf("N-related-%d", index)
		if _, err := st.DB().ExecContext(context.Background(), `INSERT INTO nodes(id, generation_id, type, title, confidence, attrs_json, created_at, updated_at) VALUES(?, 'GEN-db', 'capability', ?, 'verified', '{}', '2026-07-21T00:00:00Z', '2026-07-21T00:00:00Z')`, nodeID, nodeID); err != nil {
			_ = st.Close()
			t.Fatal(err)
		}
	}
	if _, err := st.DB().ExecContext(context.Background(), `INSERT INTO edges(id, generation_id, type, source_id, target_id, confidence, attrs_json, created_at, updated_at) VALUES
('EDGE-related-1', 'GEN-db', 'consumes', 'N-app', 'N-related-1', 'verified', '{}', '2026-07-21T00:00:00Z', '2026-07-21T00:00:00Z'),
('EDGE-related-2', 'GEN-db', 'consumes', 'N-related-1', 'N-related-2', 'verified', '{}', '2026-07-21T00:00:00Z', '2026-07-21T00:00:00Z')`); err != nil {
		_ = st.Close()
		t.Fatal(err)
	}
	if err := st.Close(); err != nil {
		t.Fatal(err)
	}
	previousBudget := closureNodeBudget
	closureNodeBudget = 2
	t.Cleanup(func() { closureNodeBudget = previousBudget })
	disposition := changemodel.DispositionAdoptable

	payload, err := RunUpdate(paths, UpdateInput{
		ChangedPaths: []string{"src/new-entry.go"},
		PathChanges: []changemodel.PathChange{{
			Path:        "src/new-entry.go",
			Operation:   changemodel.OperationAdd,
			NodeID:      "N-app",
			Disposition: &disposition,
		}},
		Workflow:     "sp-implement",
		Reason:       "workflow-finalize",
		Verification: []VerificationEvidence{{Command: "go test ./...", Result: "passed"}},
	})
	if err != nil {
		t.Fatal(err)
	}
	if payload.ResultState != ResultPartialRefresh || !payload.ClosureTruncated || payload.ClosureTruncationReason != "node_budget_exhausted" {
		t.Fatalf("payload = %#v, want bounded explicit-node closure to force partial_refresh", payload)
	}
}

func TestRunUpdateRejectsTypedPathChangeWithoutDispositionBeforeMutation(t *testing.T) {
	paths := testPaths(t)
	seedReadyRuntime(t, paths)

	_, err := RunUpdate(paths, UpdateInput{
		ChangedPaths: []string{"src/new-feature.go"},
		PathChanges: []changemodel.PathChange{{
			Path:      "src/new-feature.go",
			Operation: changemodel.OperationAdd,
		}},
		Verification: []VerificationEvidence{{Command: "go test ./...", Result: "passed"}},
	})
	if err == nil {
		t.Fatal("RunUpdate accepted a typed path change without disposition")
	}
	if !strings.Contains(err.Error(), "disposition") {
		t.Fatalf("error = %q, want disposition diagnostic", err.Error())
	}
	status, readErr := rt.ReadStatus(paths)
	if readErr != nil {
		t.Fatal(readErr)
	}
	if status.LastUpdateID != "" {
		t.Fatalf("LastUpdateID = %q, want no mutation", status.LastUpdateID)
	}
}

func TestRunUpdateReviewOnlyPathDoesNotMutateGraphOrReportReady(t *testing.T) {
	paths := testPaths(t)
	seedReadyRuntime(t, paths)
	disposition := changemodel.DispositionReviewOnly

	payload, err := RunUpdate(paths, UpdateInput{
		ChangedPaths: []string{"src/review-me.go"},
		PathChanges: []changemodel.PathChange{{
			Path:        "src/review-me.go",
			Operation:   changemodel.OperationAdd,
			Disposition: &disposition,
		}},
		Verification: []VerificationEvidence{{Command: "go test ./...", Result: "passed"}},
	})
	if err != nil {
		t.Fatal(err)
	}
	if payload.ResultState != ResultPartialRefresh || !containsString(payload.ReviewPaths, "src/review-me.go") {
		t.Fatalf("payload = %#v, want review-only partial refresh", payload)
	}
	st, err := store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	defer st.Close()
	mapped, err := st.NodeIDsForExactPaths(context.Background(), []string{"src/review-me.go"})
	if err != nil {
		t.Fatal(err)
	}
	if mapped["src/review-me.go"] != "" {
		t.Fatalf("mapped paths = %#v, review_only path must not mutate graph", mapped)
	}
	var changedPathsJSON string
	if err := st.DB().QueryRowContext(context.Background(), `SELECT changed_paths_json FROM updates WHERE id = ?`, payload.UpdateID).Scan(&changedPathsJSON); err != nil {
		t.Fatal(err)
	}
	if values := jsonArrayValues(t, changedPathsJSON); len(values) != 0 {
		t.Fatalf("changed_paths_json = %#v, review_only path must remain audit-only", values)
	}
}

func TestRunUpdateReviewOnlyMappedPathDoesNotStaleGraphClaims(t *testing.T) {
	paths := testPaths(t)
	seedReadyRuntime(t, paths)
	st, err := store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := st.DB().ExecContext(context.Background(), `INSERT INTO claims(id, generation_id, node_id, graph_claim_type, summary, state, prior_state, freshness, state_reason, attrs_json, created_at, updated_at) VALUES('claim:review-only', 'GEN-db', 'N-app', 'runtime_owner', 'Review-only claim', ?, '', ?, 'supporting_evidence', '{}', '2026-07-13T00:00:00Z', '2026-07-13T00:00:00Z')`, claim.StateSupported, claim.FreshnessFresh); err != nil {
		_ = st.Close()
		t.Fatal(err)
	}
	if err := st.Close(); err != nil {
		t.Fatal(err)
	}
	disposition := changemodel.DispositionReviewOnly

	payload, err := RunUpdate(paths, UpdateInput{
		ChangedPaths: []string{"src/app.go"},
		PathChanges: []changemodel.PathChange{{
			Path:        "src/app.go",
			Operation:   changemodel.OperationModify,
			NodeID:      "N-app",
			Disposition: &disposition,
		}},
		Verification: []VerificationEvidence{{Command: "go test ./...", Result: "passed"}},
	})
	if err != nil {
		t.Fatal(err)
	}
	if len(payload.AffectedGraphClaims) != 0 {
		t.Fatalf("AffectedGraphClaims = %#v, review-only path must remain audit-only", payload.AffectedGraphClaims)
	}
	st, err = store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	defer st.Close()
	var state, freshness string
	if err := st.DB().QueryRowContext(context.Background(), `SELECT state, freshness FROM claims WHERE id = 'claim:review-only'`).Scan(&state, &freshness); err != nil {
		t.Fatal(err)
	}
	if state != string(claim.StateSupported) || freshness != string(claim.FreshnessFresh) {
		t.Fatalf("review-only claim lifecycle = %q/%q, want supported/fresh", state, freshness)
	}
}

func TestRunUpdateIgnoredDispositionIsAuditedAsNoOp(t *testing.T) {
	paths := testPaths(t)
	seedReadyRuntime(t, paths)
	disposition := changemodel.DispositionIgnored

	payload, err := RunUpdate(paths, UpdateInput{
		ChangedPaths: []string{"generated/ignored.go"},
		PathChanges: []changemodel.PathChange{{
			Path:        "generated/ignored.go",
			Operation:   changemodel.OperationAdd,
			Disposition: &disposition,
		}},
	})
	if err != nil {
		t.Fatal(err)
	}
	if payload.ResultState != ResultNoOp || len(payload.PathChanges) != 1 || !containsString(payload.IgnoredPaths, "generated/ignored.go") {
		t.Fatalf("payload = %#v, want audited ignored no_op", payload)
	}
	st, err := store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	defer st.Close()
	var changedPathsJSON, attrsJSON string
	if err := st.DB().QueryRowContext(context.Background(), `SELECT changed_paths_json, attrs_json FROM updates WHERE id = ?`, payload.UpdateID).Scan(&changedPathsJSON, &attrsJSON); err != nil {
		t.Fatal(err)
	}
	if values := jsonArrayValues(t, changedPathsJSON); len(values) != 0 {
		t.Fatalf("changed_paths_json = %#v, ignored path must not mutate graph", values)
	}
	if !strings.Contains(attrsJSON, `"disposition":"ignored"`) {
		t.Fatalf("attrs_json = %s, want ignored path_changes audit", attrsJSON)
	}
}

func TestRunUpdateAdoptsVerifiedUnindexedPath(t *testing.T) {
	paths := testPaths(t)
	seedReadyRuntime(t, paths)

	payload, err := RunUpdate(paths, UpdateInput{
		ChangedPaths:     []string{"src/new-feature.go"},
		PathChanges:      []changemodel.PathChange{adoptableAddPathChange("src/new-feature.go")},
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

	var relation, confidence string
	if err := st.DB().QueryRowContext(context.Background(), `SELECT relation, confidence FROM path_index WHERE path = ?`, "src/new-feature.go").Scan(&relation, &confidence); err != nil {
		t.Fatal(err)
	}
	if relation != "provisional_path" {
		t.Fatalf("relation = %q, want provisional_path", relation)
	}
	if confidence != "partial" {
		t.Fatalf("confidence = %q, want partial", confidence)
	}
}

func TestRunUpdateAdoptsVerifiedUnindexedPathInMixedWorkflowCloseout(t *testing.T) {
	paths := testPaths(t)
	seedReadyRuntime(t, paths)

	payload, err := RunUpdate(paths, UpdateInput{
		ChangedPaths:     []string{"src/app.go", "src/new-feature.go"},
		PathChanges:      []changemodel.PathChange{adoptableAddPathChange("src/new-feature.go")},
		Reason:           "workflow-finalize",
		Workflow:         "sp-implement",
		BehaviorSurfaces: []string{"application entrypoint", "new feature entrypoint"},
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
		t.Fatalf("AdoptedPaths = %#v, want new-feature adoption", payload.AdoptedPaths)
	}
	if len(payload.ReviewPaths) != 0 {
		t.Fatalf("ReviewPaths = %#v, want none", payload.ReviewPaths)
	}

	st, err := store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	defer st.Close()
	nodes, err := st.NodesForPaths(context.Background(), []string{"src/app.go", "src/new-feature.go"})
	if err != nil {
		t.Fatal(err)
	}
	if len(nodes) < 2 {
		t.Fatalf("NodesForPaths returned %#v, want indexed and adopted nodes", nodes)
	}
}

func TestRunUpdateTreatsExcludedUnrelatedDirtyWorkspaceNoteAsNonBlocking(t *testing.T) {
	paths := testPaths(t)
	seedReadyRuntime(t, paths)

	payload, err := RunUpdate(paths, UpdateInput{
		ChangedPaths:     []string{"src/app.go"},
		Reason:           "workflow-finalize",
		Workflow:         "sp-implement",
		BehaviorSurfaces: []string{"application entrypoint"},
		Verification: []VerificationEvidence{
			{Command: "go test ./...", Result: "passed"},
		},
		KnownUnknowns: []string{
			"unrelated dirty workspace paths excluded by explicit workflow-owned paths; include-working-tree=false include-untracked=false",
		},
	})
	if err != nil {
		t.Fatal(err)
	}
	if payload.ResultState != ResultReady {
		t.Fatalf("ResultState = %q, payload=%#v", payload.ResultState, payload)
	}
	if !containsText(payload.KnownUnknowns, "unrelated dirty workspace paths excluded") {
		t.Fatalf("KnownUnknowns = %#v, want retained non-blocking scope note", payload.KnownUnknowns)
	}
}

func TestRunUpdateAdoptionPassesBuildIdentityValidation(t *testing.T) {
	paths := testPaths(t)
	writeUpdateMatchingScanPackage(t, paths)
	seedReadyRuntime(t, paths)

	payload, err := RunUpdate(paths, UpdateInput{
		ChangedPaths:     []string{"src/new-feature.go"},
		PathChanges:      []changemodel.PathChange{adoptableAddPathChange("src/new-feature.go")},
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

	build := validation.ValidateBuild(paths)
	if build.Status != "ok" {
		t.Fatalf("ValidateBuild status = %q, errors=%#v", build.Status, build.Errors)
	}
}

func TestRunUpdatePayloadFileNormalizesPathChangesBeforeDispositionResolution(t *testing.T) {
	paths := testPaths(t)
	seedReadyRuntime(t, paths)
	payloadPath := filepath.Join(paths.RuntimeDir, "updates", "normalized-disposition.json")
	if err := os.MkdirAll(filepath.Dir(payloadPath), 0o755); err != nil {
		t.Fatal(err)
	}
	data := []byte(`{
  "workflow": "sp-review",
  "reason": "workflow-finalize",
  "changed_paths": ["./src/app.go"],
  "path_changes": [{
    "path": "./src/app.go",
    "operation": "modify",
    "node_id": "N-app",
    "evidence_refs": ["test:normalized-disposition"]
  }],
  "unknown_path_dispositions": [{
    "path": "src/app.go",
    "agent_disposition": "adoptable"
  }],
  "verification": [{"command": "go test ./...", "result": "passed"}]
}`)
	if err := os.WriteFile(payloadPath, data, 0o644); err != nil {
		t.Fatal(err)
	}

	payload, err := RunUpdate(paths, UpdateInput{PayloadFile: payloadPath})
	if err != nil {
		t.Fatal(err)
	}
	if payload.ResultState != ResultReady || len(payload.PathChanges) != 1 {
		t.Fatalf("payload = %#v, want one ready normalized path change", payload)
	}
	change := payload.PathChanges[0]
	if change.Path != "src/app.go" || change.OldPath != "" || change.Disposition == nil || *change.Disposition != changemodel.DispositionAdoptable {
		t.Fatalf("PathChanges = %#v, want normalized matched disposition", payload.PathChanges)
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
  "path_changes": [{"path": "src/new-feature.go", "operation": "add", "disposition": "adoptable"}],
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

func TestRunUpdatePayloadFileRejectsPassedVerificationAliases(t *testing.T) {
	paths := testPaths(t)
	seedReadyRuntime(t, paths)
	payloadPath := filepath.Join(paths.RuntimeDir, "updates", "workflow-finalize.json")
	if err := os.MkdirAll(filepath.Dir(payloadPath), 0o755); err != nil {
		t.Fatal(err)
	}
	data := []byte(`{
  "workflow": "sp-implement",
  "reason": "workflow-finalize",
  "changed_paths": ["src/pass-alias.go"],
  "behavior_surfaces": ["pass alias entrypoint"],
  "verification": [
    {"command": "go test ./...", "result": "pass"}
  ],
  "known_unknowns": []
}`)
	if err := os.WriteFile(payloadPath, data, 0o644); err != nil {
		t.Fatal(err)
	}

	_, err := RunUpdate(paths, UpdateInput{
		PayloadFile: payloadPath,
		Reason:      "workflow-finalize",
	})
	if err == nil {
		t.Fatal("RunUpdate accepted non-canonical verification result alias")
	}
	if !strings.Contains(err.Error(), "verification") {
		t.Fatalf("error = %q, want verification diagnostic", err.Error())
	}
}

func TestRunUpdateAdoptedPathIsCompassDiscoverable(t *testing.T) {
	paths := testPaths(t)
	seedReadyRuntime(t, paths)

	payload, err := RunUpdate(paths, UpdateInput{
		ChangedPaths:     []string{"src/semantic-router.go"},
		PathChanges:      []changemodel.PathChange{adoptableAddPathChange("src/semantic-router.go")},
		Reason:           "workflow-finalize",
		Workflow:         "sp-implement",
		BehaviorSurfaces: []string{"semantic routing"},
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

	pendingCompass, err := query.Compass(paths, query.CompassInput{
		Intent: "implement",
		Query:  "semantic router",
	})
	if err != nil {
		t.Fatal(err)
	}
	if pendingCompass.Readiness != rt.BlockedReadiness || len(pendingCompass.MinimalLiveReads) != 0 {
		t.Fatalf("pending compass = %#v, want finalizer gate to withhold routes", pendingCompass)
	}
	if err := RecordValidateBuildReceipt(paths, "ok", "build_acceptance", rt.ReadyReadiness); err != nil {
		t.Fatal(err)
	}
	if _, err := CompleteRefresh(paths, "validated-update"); err != nil {
		t.Fatal(err)
	}
	compass, err := query.Compass(paths, query.CompassInput{
		Intent: "implement",
		Query:  "semantic router",
	})
	if err != nil {
		t.Fatal(err)
	}
	if !containsString(compass.MinimalLiveReads, "src/semantic-router.go") {
		t.Fatalf("MinimalLiveReads = %#v, want adopted semantic router path", compass.MinimalLiveReads)
	}
}

func TestRunUpdatePayloadFileTreatsStringVerificationEvidenceAsRecorded(t *testing.T) {
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
	if payload.ResultState != ResultPartialRefresh {
		t.Fatalf("ResultState = %q, payload=%#v, want partial_refresh", payload.ResultState, payload)
	}
	if containsString(payload.AdoptedPaths, "src/string-evidence.go") {
		t.Fatalf("AdoptedPaths = %#v, did not want recorded-only path adoption", payload.AdoptedPaths)
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

func TestRunUpdateRefreshesEachIndexedPathAgainstItsOwnNode(t *testing.T) {
	paths := testPaths(t)
	seedReadyRuntimeWithImports(t, paths,
		[]store.EvidenceImport{
			{ID: "E-app", SourceKind: "file", SourcePath: "src/app.go", CommitSHA: "abc123", Extractor: "test", ContentHash: "hash-app"},
			{ID: "E-worker", SourceKind: "file", SourcePath: "src/worker.go", CommitSHA: "abc123", Extractor: "test", ContentHash: "hash-worker"},
		},
		[]store.NodeImport{
			{ID: "N-app", Type: "capability", Title: "App", Confidence: "verified", EvidenceIDs: []string{"E-app"}},
			{ID: "N-worker", Type: "capability", Title: "Worker", Confidence: "verified", EvidenceIDs: []string{"E-worker"}},
		},
		[]store.PathIndexImport{
			{ID: "P-app", Path: "src/app.go", NodeID: "N-app", Relation: "owns", Confidence: "verified", EvidenceID: "E-app"},
			{ID: "P-worker", Path: "src/worker.go", NodeID: "N-worker", Relation: "owns", Confidence: "verified", EvidenceID: "E-worker"},
		},
	)

	payload, err := RunUpdate(paths, UpdateInput{
		ChangedPaths: []string{"src/app.go", "src/worker.go"},
		Reason:       "workflow-finalize",
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

	st, err := store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	defer st.Close()
	for path, wantNode := range map[string]string{
		"src/app.go":    "N-app",
		"src/worker.go": "N-worker",
	} {
		var gotNode string
		if err := st.DB().QueryRowContext(context.Background(), `SELECT node_id FROM path_index WHERE path = ?`, path).Scan(&gotNode); err != nil {
			t.Fatal(err)
		}
		if gotNode != wantNode {
			t.Fatalf("path %s node_id = %q, want %q", path, gotNode, wantNode)
		}
	}
}

func TestRunUpdateRejectsUnsafeChangedPathsBeforeMutation(t *testing.T) {
	paths := testPaths(t)
	seedReadyRuntime(t, paths)

	_, err := RunUpdate(paths, UpdateInput{
		ChangedPaths: []string{"../outside.go"},
		Reason:       "workflow-finalize",
		Verification: []VerificationEvidence{
			{Command: "go test ./...", Result: "passed"},
		},
	})
	if err == nil {
		t.Fatal("expected unsafe changed path error")
	}
	if !strings.Contains(err.Error(), "invalid changed path") {
		t.Fatalf("error = %q, want invalid changed path", err.Error())
	}

	status, statusErr := rt.ReadStatus(paths)
	if statusErr != nil {
		t.Fatal(statusErr)
	}
	if status.LastUpdateID != "" {
		t.Fatalf("LastUpdateID = %q, want no mutation", status.LastUpdateID)
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
	if got := jsonArrayValues(t, claimsJSON); len(got) != 0 {
		t.Fatalf("affected_claims_json = %#v, want empty schema-v2 claim closure", got)
	}
	if got := jsonArrayValues(t, slicesJSON); len(got) != 0 {
		t.Fatalf("affected_slices_json = %#v, want empty schema-v2 slice closure", got)
	}
}

func TestCompleteRefreshBlocksSplitBrainBaselineBeforeStatusWrite(t *testing.T) {
	paths := testPaths(t)
	seedSplitBrainRuntime(t, paths)

	_, err := CompleteRefresh(paths, "manual")

	if err == nil {
		t.Fatal("expected split-brain agreement error")
	}
	if !strings.Contains(err.Error(), "project_cognition.repair_status") {
		t.Fatalf("error = %q, want project_cognition.repair_status", err.Error())
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
	if !strings.Contains(err.Error(), "project_cognition.repair_status") {
		t.Fatalf("error = %q, want project_cognition.repair_status", err.Error())
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
	if !strings.Contains(err.Error(), "project_cognition.repair_status") {
		t.Fatalf("error = %q, want project_cognition.repair_status", err.Error())
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
	if !strings.Contains(err.Error(), "project_cognition.repair_status") {
		t.Fatalf("error = %q, want project_cognition.repair_status", err.Error())
	}
}

func TestRunUpdateWithDeltaSessionRecordsStatusMetadata(t *testing.T) {
	paths := testPaths(t)
	seedReadyRuntime(t, paths)
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
	seedReadyRuntime(t, paths)
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
	seedReadyRuntimeWithImports(t, paths,
		[]store.EvidenceImport{{ID: "E-app", SourceKind: "file", SourcePath: "src/app.go", CommitSHA: "abc123", Extractor: "test", ContentHash: "hash-app"}},
		[]store.NodeImport{{ID: "N-app", Type: "capability", Title: "App", Confidence: "verified", EvidenceIDs: []string{"E-app"}}},
		[]store.PathIndexImport{{ID: "P-app", Path: "src/app.go", NodeID: "N-app", Relation: "owns", Confidence: "verified", EvidenceID: "E-app"}},
	)
}

func seedReadyRuntimeWithImports(t *testing.T, paths rt.Paths, evidence []store.EvidenceImport, nodes []store.NodeImport, pathIndex []store.PathIndexImport) {
	t.Helper()
	seedRuntimeGenerationWithImports(t, paths, "GEN-db", evidence, nodes, pathIndex)
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

func seedLatestUpdateOutcome(t *testing.T, paths rt.Paths, updateID string, outcome string) {
	t.Helper()
	st, err := store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	if err := st.RecordStructuredUpdate(context.Background(), store.UpdateRecord{
		ID:          updateID,
		Trigger:     "test",
		ResultState: outcome,
	}); err != nil {
		_ = st.Close()
		t.Fatal(err)
	}
	if err := st.Close(); err != nil {
		t.Fatal(err)
	}
	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	status.LastUpdateID = updateID
	status.LastUpdateOutcome = outcome
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}
}

func seedValidatedReadyUpdate(t *testing.T, paths rt.Paths) {
	t.Helper()
	const updateID = "upd-validated"
	seedLatestUpdateOutcome(t, paths, updateID, ResultReady)
	receipt := map[string]any{
		"version":              1,
		"gate":                 "build_acceptance",
		"status":               "ok",
		"readiness":            rt.ReadyReadiness,
		"active_generation_id": "GEN-db",
		"update_id":            updateID,
		"update_outcome":       ResultReady,
		"validated_at":         "2026-07-21T00:00:00Z",
	}
	data, err := json.Marshal(receipt)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(paths.RuntimeDir, "validate-build-receipt.json"), append(data, '\n'), 0o644); err != nil {
		t.Fatal(err)
	}
}

func seedRuntimeGeneration(t *testing.T, paths rt.Paths, generationID string) {
	t.Helper()
	seedRuntimeGenerationWithImports(t, paths, generationID,
		[]store.EvidenceImport{{ID: "E-app", SourceKind: "file", SourcePath: "src/app.go", CommitSHA: "abc123", Extractor: "test", ContentHash: "hash-app"}},
		[]store.NodeImport{{ID: "N-app", Type: "capability", Title: "App", Confidence: "verified", EvidenceIDs: []string{"E-app"}}},
		[]store.PathIndexImport{{ID: "P-app", Path: "src/app.go", NodeID: "N-app", Relation: "owns", Confidence: "verified", EvidenceID: "E-app"}},
	)
}

func seedRuntimeGenerationWithImports(t *testing.T, paths rt.Paths, generationID string, evidence []store.EvidenceImport, nodes []store.NodeImport, pathIndex []store.PathIndexImport) {
	t.Helper()
	aliases := make([]store.AliasImport, 0, len(nodes))
	for _, node := range nodes {
		if node.Title == "" {
			continue
		}
		aliases = append(aliases, store.AliasImport{
			ID:              "ALIAS-" + node.ID + "-title",
			Alias:           node.Title,
			NormalizedAlias: strings.ToLower(node.Title),
			TargetType:      "node",
			TargetID:        node.ID,
			Source:          "node_title",
			Confidence:      node.Confidence,
		})
	}
	st, err := store.Open(paths)
	if err != nil {
		t.Fatal(err)
	}
	_, err = st.ImportGeneration(context.Background(), store.ImportInput{
		GenerationID: generationID,
		Kind:         "full",
		SourceCommit: "abc123",
		Evidence:     evidence,
		Nodes:        nodes,
		PathIndex:    pathIndex,
		Aliases:      aliases,
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

func writeUpdateMatchingScanPackage(t *testing.T, paths rt.Paths) {
	t.Helper()
	files := map[string]string{
		filepath.Join(paths.RuntimeDir, "evidence", "E-app.json"):                 `{"id":"E-app","source_kind":"file","source_path":"src/app.go","commit_sha":"abc123","span":"L1-L5","extractor":"test","content_hash":"hash-app","attrs":{"language":"go"}}`,
		filepath.Join(paths.RuntimeDir, "provisional", "nodes.json"):              `{"nodes":[{"id":"N-app","type":"capability","title":"App","confidence":"verified","paths":["src/app.go"],"evidence_ids":["E-app"],"attrs":{"owner":"app"}}]}`,
		filepath.Join(paths.RuntimeDir, "provisional", "edges.json"):              `{"edges":[]}`,
		filepath.Join(paths.RuntimeDir, "provisional", "observations.json"):       `{"observations":[]}`,
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
			"coverage":[{"path":"src/app.go","outcome":"read","evidence_ids":["E-app"]}],
			"confidence":"high",
			"acceptance":"pass"
		}`,
		filepath.Join(paths.RuntimeDir, "workbench", "map-state.md"):             `# Map State`,
		filepath.Join(paths.RuntimeDir, "workbench", "capability-ledger.json"):   `{"rows":[]}`,
		filepath.Join(paths.RuntimeDir, "workbench", "control-ledger.json"):      `{"rows":[]}`,
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
	}
	for path, content := range files {
		if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(path, []byte(content+"\n"), 0o644); err != nil {
			t.Fatal(err)
		}
	}
}

func adoptableAddPathChange(path string) changemodel.PathChange {
	disposition := changemodel.DispositionAdoptable
	return changemodel.PathChange{
		Path:        path,
		Operation:   changemodel.OperationAdd,
		Disposition: &disposition,
	}
}

func jsonArrayContains(t *testing.T, raw string, want string) bool {
	t.Helper()
	return containsString(jsonArrayValues(t, raw), want)
}

func jsonArrayValues(t *testing.T, raw string) []string {
	t.Helper()
	var values []string
	if err := json.Unmarshal([]byte(raw), &values); err != nil {
		t.Fatal(err)
	}
	return values
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

func initGitRepositoryForUpdateTest(t *testing.T, root string) {
	t.Helper()
	runUpdateGit(t, root, "init")
	runUpdateGit(t, root, "config", "user.email", "test@example.com")
	runUpdateGit(t, root, "config", "user.name", "Test User")
	runUpdateGit(t, root, "add", ".")
	runUpdateGit(t, root, "commit", "-m", "baseline")
}

func runUpdateGit(t *testing.T, root string, args ...string) string {
	t.Helper()
	cmd := exec.Command("git", args...)
	cmd.Dir = root
	output, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("git %v failed: %v\n%s", args, err, output)
	}
	return string(output)
}
