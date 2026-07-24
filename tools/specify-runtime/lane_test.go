package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestRuntimeLaneResolutionSelectsUniqueResumableCandidate(t *testing.T) {
	root := t.TempDir()
	writeRuntimeLaneTestRecord(t, root, runtimeLaneRecord{
		LaneID:               "lane-001",
		FeatureID:            "001-demo",
		FeatureDir:           ".specify/features/001-demo",
		BranchName:           "001-demo",
		WorktreePath:         ".specify/worktrees/lane-001",
		RecoveryState:        "resumable",
		LastCommand:          "plan",
		LastStableCheckpoint: "plan-ready",
	})
	records, err := readRuntimeLanes(root)
	if err != nil {
		t.Fatal(err)
	}
	candidates := []runtimeLaneRecord{}
	for _, lane := range records {
		if inferRuntimeLaneCommand(root, lane) == "plan" {
			candidates = append(candidates, lane)
		}
	}
	mode, selected, reason := resolveRuntimeLaneCandidates(candidates, false)
	if mode != "resume" || selected != "lane-001" || reason != "unique-safe-candidate" {
		t.Fatalf("lane resolution = %q %q %q, want unique resume", mode, selected, reason)
	}
}

func TestRuntimeLaneResolutionRequiresChoiceForUncertainCandidate(t *testing.T) {
	mode, selected, reason := resolveRuntimeLaneCandidates([]runtimeLaneRecord{
		{LaneID: "lane-001", RecoveryState: "resumable"},
		{LaneID: "lane-002", RecoveryState: "uncertain"},
	}, false)
	if mode != "choose" || selected != "" || reason != "ambiguous-or-uncertain" {
		t.Fatalf("lane resolution = %q %q %q, want choose", mode, selected, reason)
	}
}

func TestCopyRuntimeBindingRejectsSymlinkedWorktreeBin(t *testing.T) {
	root := t.TempDir()
	target := filepath.Join(root, "worktree")
	outside := t.TempDir()
	sourceName := filepath.Base(filepath.FromSlash(strings.TrimPrefix(
		strings.TrimPrefix(projectRuntimeRelativeEntrypoint(), "./"),
		`.\`,
	)))
	source := filepath.Join(root, ".specify", "bin", sourceName)
	if err := os.MkdirAll(filepath.Dir(source), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(source, []byte("runtime"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Join(target, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(outside, filepath.Join(target, ".specify", "bin")); err != nil {
		t.Skipf("symlinks unavailable: %v", err)
	}

	if err := copyRuntimeBindingToWorktree(root, target); err == nil {
		t.Fatal("copyRuntimeBindingToWorktree accepted a symlinked .specify/bin")
	}
	if _, err := os.Stat(filepath.Join(outside, sourceName)); !os.IsNotExist(err) {
		t.Fatalf("outside runtime was written through symlink: %v", err)
	}
}

func TestCopyRuntimeBindingRejectsDigestMismatchBeforeWriting(t *testing.T) {
	root := t.TempDir()
	target := filepath.Join(root, "worktree")
	sourceName := filepath.Base(filepath.FromSlash(strings.TrimPrefix(
		strings.TrimPrefix(projectRuntimeRelativeEntrypoint(), "./"),
		`.\`,
	)))
	source := filepath.Join(root, ".specify", "bin", sourceName)
	if err := os.MkdirAll(filepath.Dir(source), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(source, []byte("runtime"), 0o755); err != nil {
		t.Fatal(err)
	}
	config := map[string]any{
		"runtime_launcher": map[string]any{
			"command": projectRuntimeRelativeEntrypoint(),
			"argv":    []string{projectRuntimeRelativeEntrypoint()},
		},
		"runtime_launcher_binding": map[string]any{
			"runtime_entrypoint":    projectRuntimeRelativeEntrypoint(),
			"runtime_binary_sha256": strings.Repeat("0", 64),
		},
	}
	configRaw, err := json.Marshal(config)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, ".specify", "config.json"), configRaw, 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(target, 0o755); err != nil {
		t.Fatal(err)
	}

	if err := copyRuntimeBindingToWorktree(root, target); err == nil {
		t.Fatal("copyRuntimeBindingToWorktree accepted a mismatched runtime digest")
	}
	if _, err := os.Stat(filepath.Join(target, ".specify", "bin", sourceName)); !os.IsNotExist(err) {
		t.Fatalf("target runtime was written before digest validation: %v", err)
	}
}

func TestCopyRuntimeBindingProvisionedWorktreePreservesOtherConfig(t *testing.T) {
	root := t.TempDir()
	target := filepath.Join(root, "worktree")
	sourceName := filepath.Base(filepath.FromSlash(strings.TrimPrefix(
		strings.TrimPrefix(projectRuntimeRelativeEntrypoint(), "./"),
		`.\`,
	)))
	runtimeRaw := []byte("runtime")
	source := filepath.Join(root, ".specify", "bin", sourceName)
	if err := os.MkdirAll(filepath.Dir(source), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(source, runtimeRaw, 0o755); err != nil {
		t.Fatal(err)
	}
	config := map[string]any{
		"runtime_launcher": map[string]any{
			"command": projectRuntimeRelativeEntrypoint(),
			"argv":    []string{projectRuntimeRelativeEntrypoint()},
		},
		"runtime_launcher_binding": map[string]any{
			"runtime_entrypoint":    projectRuntimeRelativeEntrypoint(),
			"runtime_binary_sha256": sha256String(string(runtimeRaw)),
		},
	}
	configRaw, err := json.Marshal(config)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, ".specify", "config.json"), configRaw, 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Join(target, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(
		filepath.Join(target, ".specify", "config.json"),
		[]byte(`{"user_setting":true}`),
		0o644,
	); err != nil {
		t.Fatal(err)
	}

	if err := copyRuntimeBindingToWorktree(root, target); err != nil {
		t.Fatal(err)
	}
	copiedRuntime, err := os.ReadFile(filepath.Join(target, ".specify", "bin", sourceName))
	if err != nil {
		t.Fatal(err)
	}
	if string(copiedRuntime) != string(runtimeRaw) {
		t.Fatalf("copied runtime = %q, want %q", copiedRuntime, runtimeRaw)
	}
	targetConfigRaw, err := os.ReadFile(filepath.Join(target, ".specify", "config.json"))
	if err != nil {
		t.Fatal(err)
	}
	var targetConfig map[string]any
	if err := json.Unmarshal(targetConfigRaw, &targetConfig); err != nil {
		t.Fatal(err)
	}
	if targetConfig["user_setting"] != true {
		t.Fatalf("user_setting = %#v, want true", targetConfig["user_setting"])
	}
	if _, ok := targetConfig["runtime_launcher_binding"].(map[string]any); !ok {
		t.Fatalf("runtime_launcher_binding = %#v, want object", targetConfig["runtime_launcher_binding"])
	}
}

func writeRuntimeLaneTestRecord(t *testing.T, root string, record runtimeLaneRecord) {
	t.Helper()
	target := filepath.Join(root, ".specify", "lanes", record.LaneID, "lane.json")
	if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil {
		t.Fatal(err)
	}
	raw, err := json.Marshal(record)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(target, raw, 0o644); err != nil {
		t.Fatal(err)
	}
}
