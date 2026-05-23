package update

import (
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"

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
	if _, err := MarkDirty(paths, DirtyInput{Reason: "manual"}); err != nil {
		t.Fatal(err)
	}
	status, err := CompleteRefresh(paths, "map-build")
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
	if status.LastUpdateOutcome != "boundary_resolved" {
		t.Fatalf("LastUpdateOutcome = %q, want boundary_resolved", status.LastUpdateOutcome)
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
	st, err := store.Open(paths)
	if err != nil {
		t.Fatal(err)
	}
	_, err = st.ImportGeneration(context.Background(), store.ImportInput{
		GenerationID: "GEN-db",
		Kind:         "full",
		SourceCommit: "abc123",
		Evidence:     []store.EvidenceImport{{ID: "E-app", SourceKind: "file", SourcePath: "src/app.go", CommitSHA: "abc123", Extractor: "test", ContentHash: "hash-app"}},
		Nodes:        []store.NodeImport{{ID: "N-app", Type: "capability", Title: "App", Confidence: "verified", EvidenceIDs: []string{"E-app"}}},
		PathIndex:    []store.PathIndexImport{{ID: "P-app", Path: "src/app.go", NodeID: "N-app", Relation: "owns", Confidence: "verified", EvidenceID: "E-app"}},
	})
	if closeErr := st.Close(); closeErr != nil {
		t.Fatal(closeErr)
	}
	if err != nil {
		t.Fatal(err)
	}
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
