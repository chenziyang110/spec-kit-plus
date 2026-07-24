package main

import (
	"os"
	"path/filepath"
	"testing"
)

func TestRuntimeIntegrationReadinessAndCloseout(t *testing.T) {
	root := t.TempDir()
	featureRoot := filepath.Join(root, ".specify", "features", "001-demo")
	if err := os.MkdirAll(featureRoot, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(
		filepath.Join(featureRoot, "implement-tracker.md"),
		[]byte("---\nstatus: resolved\n---\n"),
		0o644,
	); err != nil {
		t.Fatal(err)
	}
	record := runtimeLaneRecord{
		LaneID:             "lane-001",
		FeatureID:          "001-demo",
		FeatureDir:         ".specify/features/001-demo",
		BranchName:         "001-demo",
		WorktreePath:       ".specify/worktrees/lane-001",
		LifecycleState:     "implementing",
		RecoveryState:      "resumable",
		LastCommand:        "implement",
		VerificationStatus: "passed",
	}
	writeRuntimeLaneTestRecord(t, root, record)

	ready, checks := assessRuntimeIntegration(root, record)
	if !ready {
		t.Fatalf("integration ready = false, checks=%#v", checks)
	}
	record.LifecycleState = "completed"
	record.RecoveryState = "completed"
	record.LastCommand = "integrate"
	if err := persistRuntimeLane(root, record); err != nil {
		t.Fatal(err)
	}
	records, err := readRuntimeLanes(root)
	if err != nil {
		t.Fatal(err)
	}
	if len(records) != 1 || records[0].LastCommand != "integrate" || records[0].RecoveryState != "completed" {
		t.Fatalf("persisted lanes = %#v, want completed integration", records)
	}
}

func TestRuntimeIntegrationBlocksMissingVerification(t *testing.T) {
	root := t.TempDir()
	record := runtimeLaneRecord{
		FeatureDir:         ".specify/features/001-demo",
		BranchName:         "001-demo",
		RecoveryState:      "completed",
		LastCommand:        "implement",
		VerificationStatus: "failed",
	}
	ready, _ := assessRuntimeIntegration(root, record)
	if ready {
		t.Fatal("integration unexpectedly ready with failed verification")
	}
}
