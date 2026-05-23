package runtimegate

import (
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/store"
)

func TestCheckAgreementAcceptsMatchingStatusAndDB(t *testing.T) {
	paths := testPaths(t)
	st, err := store.Open(paths)
	if err != nil {
		t.Fatal(err)
	}
	defer st.Close()
	if _, err := st.ImportGeneration(context.Background(), store.ImportInput{GenerationID: "GEN-1", Kind: "full"}); err != nil {
		t.Fatal(err)
	}
	status := rt.DefaultStatus(paths)
	status.Status = "ok"
	status.Freshness = rt.ReadyFreshness
	status.Readiness = rt.ReadyReadiness
	status.GraphReady = true
	status.ActiveGenerationID = "GEN-1"
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}

	agreement := Check(paths)

	if agreement.Status != "ok" {
		t.Fatalf("Status = %q, want ok; errors=%v", agreement.Status, agreement.Errors)
	}
}

func TestCheckAgreementBlocksSplitBrainActiveGeneration(t *testing.T) {
	paths := testPaths(t)
	st, err := store.Open(paths)
	if err != nil {
		t.Fatal(err)
	}
	defer st.Close()
	if _, err := st.ImportGeneration(context.Background(), store.ImportInput{GenerationID: "GEN-db", Kind: "full"}); err != nil {
		t.Fatal(err)
	}
	status := rt.DefaultStatus(paths)
	status.Status = "ok"
	status.Freshness = rt.ReadyFreshness
	status.Readiness = rt.ReadyReadiness
	status.GraphReady = true
	status.ActiveGenerationID = "GEN-old"
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}

	agreement := Check(paths)

	if agreement.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked", agreement.Status)
	}
	if agreement.RecoveryAction != "rewrite_status_from_db_metadata" {
		t.Fatalf("RecoveryAction = %q, want rewrite_status_from_db_metadata", agreement.RecoveryAction)
	}
	if !strings.Contains(strings.Join(agreement.Errors, "\n"), "mismatch") {
		t.Fatalf("Errors = %v, want mismatch message", agreement.Errors)
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
