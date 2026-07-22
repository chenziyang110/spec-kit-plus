package reference

import (
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"

	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/store"
)

func TestDiscoverReportsSplitBrainReferenceAsBlocked(t *testing.T) {
	paths := referenceTestPaths(t)
	seedSplitBrainRuntime(t, paths)

	payload, err := Discover(paths.Root)
	if err != nil {
		t.Fatal(err)
	}
	if len(payload.Projects) != 1 {
		t.Fatalf("Projects = %#v, want one project", payload.Projects)
	}
	project := payload.Projects[0]
	if project.GraphReady {
		t.Fatalf("GraphReady = true, want false for split-brain reference")
	}
	if project.ReferenceReadiness != rt.BlockedReadiness {
		t.Fatalf("ReferenceReadiness = %q, want %q", project.ReferenceReadiness, rt.BlockedReadiness)
	}
	if !containsText(project.Blockers, "run_map_scan_build") {
		t.Fatalf("Blockers = %#v, want graph-store rebuild", project.Blockers)
	}
}

func TestReadRejectsSplitBrainReference(t *testing.T) {
	paths := referenceTestPaths(t)
	seedSplitBrainRuntime(t, paths)
	writeReferenceSlice(t, paths, "overview", `{"summary":"demo"}`)

	_, err := Read(paths.Root, "overview", nil)

	if err == nil {
		t.Fatal("expected split-brain reference error")
	}
	if !strings.Contains(err.Error(), "run_map_scan_build") {
		t.Fatalf("error = %q, want graph-store rebuild", err.Error())
	}
}

func referenceTestPaths(t *testing.T) rt.Paths {
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

func writeReferenceSlice(t *testing.T, paths rt.Paths, name, content string) {
	t.Helper()
	path := filepath.Join(paths.RuntimeDir, "slices", name+".json")
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(content+"\n"), 0o644); err != nil {
		t.Fatal(err)
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
