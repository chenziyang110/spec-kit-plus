package update

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"

	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/delta"
	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
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
