package store

import (
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
)

func TestImportGenerationPublishesActiveIdentitySnapshot(t *testing.T) {
	ctx := context.Background()
	st := openImportTestStore(t)
	defer st.Close()

	generationID, err := st.ImportGeneration(ctx, ImportInput{
		GenerationID: "GEN-import",
		Kind:         "full",
		SourceCommit: "abc123",
		Evidence: []EvidenceImport{{
			ID:          "E-001",
			SourcePath:  "src/app.go",
			SourceKind:  "source",
			CommitSHA:   "abc123",
			Extractor:   "test",
			ContentHash: "hash-app",
		}},
		Nodes: []NodeImport{{
			ID:          "N-app",
			Type:        "capability",
			Title:       "App",
			Confidence:  "verified",
			EvidenceIDs: []string{"E-001"},
		}},
		Edges: []EdgeImport{{
			ID:          "EDGE-app-self",
			Type:        "owns",
			SourceID:    "N-app",
			TargetID:    "N-app",
			Confidence:  "verified",
			EvidenceIDs: []string{"E-001"},
		}},
		Observations: []ObservationImport{{
			ID:              "OBS-app",
			ObservationType: "summary",
			Summary:         "App observed",
			EvidenceIDs:     []string{"E-001"},
		}},
		PathIndex: []PathIndexImport{{
			ID:         "P-src-app-go",
			Path:       "src/app.go",
			NodeID:     "N-app",
			Relation:   "owns",
			Confidence: "verified",
			EvidenceID: "E-001",
		}},
		Rejections: []RowDecision{{
			Category: "coverage",
			Identity: "docs/missing.md",
			Reason:   "no_node_relation",
		}},
		MergeRecords: []MergeRecord{{
			Category:       "node",
			SourceIdentity: "N-app-duplicate",
			TargetIdentity: "N-app",
			Reason:         "duplicate_label",
		}},
	})
	if err != nil {
		t.Fatal(err)
	}
	if generationID != "GEN-import" {
		t.Fatalf("generationID = %q, want GEN-import", generationID)
	}
	activeID, err := st.ActiveGenerationID(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if activeID != "GEN-import" {
		t.Fatalf("activeID = %q, want GEN-import", activeID)
	}

	snapshot, err := st.ActiveIdentitySnapshot(ctx)
	if err != nil {
		t.Fatal(err)
	}
	assertSnapshotIdentity(t, snapshot.Evidence, "E-001|src/app.go|hash-app")
	assertSnapshotIdentity(t, snapshot.Nodes, "N-app")
	assertSnapshotIdentity(t, snapshot.Edges, "EDGE-app-self|N-app|N-app|owns")
	assertSnapshotIdentity(t, snapshot.Observations, "OBS-app")
	assertSnapshotIdentity(t, snapshot.CoveragePaths, "src/app.go")
	if len(snapshot.Rejections) != 1 || snapshot.Rejections[0].Reason != "no_node_relation" {
		t.Fatalf("Rejections = %#v, want one no_node_relation rejection", snapshot.Rejections)
	}
	if len(snapshot.MergeRecords) != 1 || snapshot.MergeRecords[0].TargetIdentity != "N-app" {
		t.Fatalf("MergeRecords = %#v, want one N-app target merge record", snapshot.MergeRecords)
	}
}

func TestImportGenerationRollsBackOnInvalidEdge(t *testing.T) {
	ctx := context.Background()
	st := openImportTestStore(t)
	defer st.Close()

	_, err := st.ImportGeneration(ctx, ImportInput{
		GenerationID: "GEN-bad",
		Edges: []EdgeImport{{
			ID:       "EDGE-bad",
			Type:     "owns",
			SourceID: "N-missing-source",
			TargetID: "N-missing-target",
		}},
	})
	if err == nil {
		t.Fatal("ImportGeneration error = nil, want invalid edge error")
	}
	activeID, err := st.ActiveGenerationID(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if activeID != "" {
		t.Fatalf("activeID = %q, want empty after rollback", activeID)
	}
}

func TestImportGenerationRollsBackOnInvalidNodeEvidence(t *testing.T) {
	ctx := context.Background()
	st := openImportTestStore(t)
	defer st.Close()

	_, err := st.ImportGeneration(ctx, ImportInput{
		GenerationID: "GEN-bad-node-evidence",
		Nodes: []NodeImport{{
			ID:          "N-app",
			Type:        "capability",
			Title:       "App",
			Confidence:  "verified",
			EvidenceIDs: []string{"E-missing"},
		}},
	})
	if err == nil {
		t.Fatal("ImportGeneration error = nil, want invalid node evidence error")
	}
	activeID, err := st.ActiveGenerationID(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if activeID != "" {
		t.Fatalf("activeID = %q, want empty after rollback", activeID)
	}
}

func TestImportGenerationRollsBackInvalidPathIndexAndPreservesActiveGeneration(t *testing.T) {
	ctx := context.Background()
	st := openImportTestStore(t)
	defer st.Close()

	if _, err := st.ImportGeneration(ctx, validImportInput("GEN-active")); err != nil {
		t.Fatal(err)
	}

	tests := []struct {
		name      string
		pathIndex PathIndexImport
	}{
		{
			name: "missing node",
			pathIndex: PathIndexImport{
				ID:         "P-missing-node",
				Path:       "src/app.go",
				NodeID:     "N-missing",
				Relation:   "owns",
				Confidence: "verified",
				EvidenceID: "E-002",
			},
		},
		{
			name: "missing evidence",
			pathIndex: PathIndexImport{
				ID:         "P-missing-evidence",
				Path:       "src/app.go",
				NodeID:     "N-app-2",
				Relation:   "owns",
				Confidence: "verified",
				EvidenceID: "E-missing",
			},
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			_, err := st.ImportGeneration(ctx, ImportInput{
				GenerationID: "GEN-bad-path-" + tt.name,
				Evidence: []EvidenceImport{{
					ID:          "E-002",
					SourcePath:  "src/app.go",
					SourceKind:  "source",
					CommitSHA:   "abc123",
					Extractor:   "test",
					ContentHash: "hash-app",
				}},
				Nodes: []NodeImport{{
					ID:         "N-app-2",
					Type:       "capability",
					Title:      "App",
					Confidence: "verified",
				}},
				PathIndex: []PathIndexImport{tt.pathIndex},
			})
			if err == nil {
				t.Fatal("ImportGeneration error = nil, want invalid path_index reference error")
			}
			activeID, err := st.ActiveGenerationID(ctx)
			if err != nil {
				t.Fatal(err)
			}
			if activeID != "GEN-active" {
				t.Fatalf("activeID = %q, want GEN-active after rollback", activeID)
			}
		})
	}
}

func TestImportGenerationRollsBackOnEmptyPathIndexEvidence(t *testing.T) {
	ctx := context.Background()
	st := openImportTestStore(t)
	defer st.Close()

	input := validImportInput("GEN-empty-path-evidence")
	input.PathIndex[0].EvidenceID = ""
	_, err := st.ImportGeneration(ctx, input)
	if err == nil {
		t.Fatal("ImportGeneration error = nil, want empty path_index evidence error")
	}
	activeID, err := st.ActiveGenerationID(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if activeID != "" {
		t.Fatalf("activeID = %q, want empty after rollback", activeID)
	}
}

func TestImportGenerationAllowsStableRowIDsAcrossGenerations(t *testing.T) {
	ctx := context.Background()
	st := openImportTestStore(t)
	defer st.Close()

	if _, err := st.ImportGeneration(ctx, validImportInput("GEN-active")); err != nil {
		t.Fatal(err)
	}
	if _, err := st.ImportGeneration(ctx, validImportInput("GEN-next")); err != nil {
		t.Fatal(err)
	}

	activeID, err := st.ActiveGenerationID(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if activeID != "GEN-next" {
		t.Fatalf("activeID = %q, want GEN-next", activeID)
	}
	snapshot, err := st.ActiveIdentitySnapshot(ctx)
	if err != nil {
		t.Fatal(err)
	}
	assertSnapshotIdentity(t, snapshot.Evidence, "E-001|src/app.go|hash-app")
	assertSnapshotIdentity(t, snapshot.Nodes, "N-app")
	assertSnapshotIdentity(t, snapshot.CoveragePaths, "src/app.go")

	var activeOldCount int
	if err := st.DB().QueryRowContext(ctx, `SELECT COUNT(*) FROM generations WHERE id = ? AND state = 'active'`, "GEN-active").Scan(&activeOldCount); err != nil {
		t.Fatal(err)
	}
	if activeOldCount != 0 {
		t.Fatalf("GEN-active active count = %d, want 0", activeOldCount)
	}
}

func TestImportGenerationStableIDFailurePreservesPriorActiveGeneration(t *testing.T) {
	ctx := context.Background()
	st := openImportTestStore(t)
	defer st.Close()

	if _, err := st.ImportGeneration(ctx, validImportInput("GEN-active")); err != nil {
		t.Fatal(err)
	}
	input := validImportInput("GEN-next")
	input.PathIndex[0].EvidenceID = "E-missing"
	_, err := st.ImportGeneration(ctx, input)
	if err == nil {
		t.Fatal("ImportGeneration error = nil, want invalid path_index evidence error")
	}

	activeID, err := st.ActiveGenerationID(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if activeID != "GEN-active" {
		t.Fatalf("activeID = %q, want GEN-active after rollback", activeID)
	}
	snapshot, err := st.ActiveIdentitySnapshot(ctx)
	if err != nil {
		t.Fatal(err)
	}
	assertSnapshotIdentity(t, snapshot.Evidence, "E-001|src/app.go|hash-app")
	assertSnapshotIdentity(t, snapshot.Nodes, "N-app")
	assertSnapshotIdentity(t, snapshot.CoveragePaths, "src/app.go")
}

func TestImportGenerationRollsBackOnInvalidEdgeOrObservationEvidence(t *testing.T) {
	ctx := context.Background()
	st := openImportTestStore(t)
	defer st.Close()

	tests := []struct {
		name  string
		input ImportInput
	}{
		{
			name: "edge evidence",
			input: ImportInput{
				GenerationID: "GEN-bad-edge-evidence",
				Nodes: []NodeImport{
					{ID: "N-source", Type: "capability", Title: "Source", Confidence: "verified"},
					{ID: "N-target", Type: "capability", Title: "Target", Confidence: "verified"},
				},
				Edges: []EdgeImport{{
					ID:          "EDGE-bad",
					Type:        "owns",
					SourceID:    "N-source",
					TargetID:    "N-target",
					Confidence:  "verified",
					EvidenceIDs: []string{"E-missing"},
				}},
			},
		},
		{
			name: "observation evidence",
			input: ImportInput{
				GenerationID: "GEN-bad-observation-evidence",
				Observations: []ObservationImport{{
					ID:              "OBS-bad",
					ObservationType: "summary",
					Summary:         "Bad evidence",
					EvidenceIDs:     []string{"E-missing"},
				}},
			},
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			_, err := st.ImportGeneration(ctx, tt.input)
			if err == nil {
				t.Fatal("ImportGeneration error = nil, want invalid evidence error")
			}
			activeID, err := st.ActiveGenerationID(ctx)
			if err != nil {
				t.Fatal(err)
			}
			if activeID != "" {
				t.Fatalf("activeID = %q, want empty after rollback", activeID)
			}
		})
	}
}

func TestImportGenerationStoresRejectionsInGenerationAttrs(t *testing.T) {
	ctx := context.Background()
	st := openImportTestStore(t)
	defer st.Close()

	_, err := st.ImportGeneration(ctx, ImportInput{
		GenerationID: "GEN-rejections",
		Rejections: []RowDecision{{
			Category: "coverage",
			Identity: "docs/missing.md",
			Reason:   "no_node_relation",
		}},
	})
	if err != nil {
		t.Fatal(err)
	}

	var attrsJSON string
	if err := st.DB().QueryRowContext(ctx, `SELECT attrs_json FROM generations WHERE id = ?`, "GEN-rejections").Scan(&attrsJSON); err != nil {
		t.Fatal(err)
	}
	var attrs struct {
		Rejections []RowDecision `json:"rejections"`
	}
	if err := json.Unmarshal([]byte(attrsJSON), &attrs); err != nil {
		t.Fatal(err)
	}
	if len(attrs.Rejections) != 1 || attrs.Rejections[0].Reason != "no_node_relation" {
		t.Fatalf("attrs rejections = %#v, want top-level no_node_relation rejection", attrs.Rejections)
	}
}

func openImportTestStore(t *testing.T) *Store {
	t.Helper()
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	st, err := Open(paths)
	if err != nil {
		t.Fatal(err)
	}
	return st
}

func validImportInput(generationID string) ImportInput {
	return ImportInput{
		GenerationID: generationID,
		Kind:         "full",
		SourceCommit: "abc123",
		Evidence: []EvidenceImport{{
			ID:          "E-001",
			SourcePath:  "src/app.go",
			SourceKind:  "source",
			CommitSHA:   "abc123",
			Extractor:   "test",
			ContentHash: "hash-app",
		}},
		Nodes: []NodeImport{{
			ID:          "N-app",
			Type:        "capability",
			Title:       "App",
			Confidence:  "verified",
			EvidenceIDs: []string{"E-001"},
		}},
		PathIndex: []PathIndexImport{{
			ID:         "P-src-app-go",
			Path:       "src/app.go",
			NodeID:     "N-app",
			Relation:   "owns",
			Confidence: "verified",
			EvidenceID: "E-001",
		}},
	}
}

func assertSnapshotIdentity(t *testing.T, identities map[string]bool, identity string) {
	t.Helper()
	if !identities[identity] {
		t.Fatalf("identity %q missing from %#v", identity, identities)
	}
}
