package query

import (
	"context"
	"database/sql"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/store"
)

func TestParsePlanNormalizesLegacyAliases(t *testing.T) {
	plan, err := ParsePlan(`{"path_hints":["./src/a.go"],"reason":"because"}`, "")
	if err != nil {
		t.Fatal(err)
	}
	if len(plan.Paths) != 1 || plan.Paths[0] != "src/a.go" {
		t.Fatalf("paths = %#v", plan.Paths)
	}
	if plan.SelectionReason != "because" {
		t.Fatalf("selection reason = %q", plan.SelectionReason)
	}
}

func TestParsePlanAcceptsConceptDecisionsAndGeneration(t *testing.T) {
	plan, err := ParsePlan(`{
		"raw_query": "GUI feels laggy",
		"lexicon_generation_id": "GEN-ui",
		"selected_concepts": ["concept:GEN-ui:N-gui"],
		"rejected_concepts": ["concept:GEN-ui:N-login"],
		"concept_decisions": [
			{
				"concept_id": "concept:GEN-ui:N-gui",
				"decision": "selected",
				"selection_reason": "GUI owns the whole surface described by the user.",
				"confidence": "high",
				"paths": ["src/gui/window.tsx"]
			},
			{
				"concept_id": "concept:GEN-ui:N-login",
				"decision": "rejected",
				"selection_reason": "Login is a GUI flow but the request is not authentication-specific.",
				"confidence": "medium",
				"risk": "over-narrowing"
			}
		]
	}`, "")
	if err != nil {
		t.Fatal(err)
	}
	if plan.LexiconGenerationID != "GEN-ui" {
		t.Fatalf("LexiconGenerationID = %q, want GEN-ui", plan.LexiconGenerationID)
	}
	if len(plan.ConceptDecisions) != 2 {
		t.Fatalf("ConceptDecisions = %#v, want two decisions", plan.ConceptDecisions)
	}
	if got := plan.ConceptDecisions[0].Paths; len(got) != 1 || got[0] != "src/gui/window.tsx" {
		t.Fatalf("decision paths = %#v, want src/gui/window.tsx", got)
	}
}

func TestNormalizePlanBackfillsLegacyConceptDecisions(t *testing.T) {
	plan := NormalizePlan(Plan{
		SelectedConcepts: []string{"concept:GEN-ui:N-gui", "concept:GEN-ui:N-gui"},
		RejectedConcepts: []string{"concept:GEN-ui:N-login"},
		SelectionReason:  "GUI is relevant; login is too narrow.",
	})

	if got := plan.SelectedConcepts; len(got) != 1 || got[0] != "concept:GEN-ui:N-gui" {
		t.Fatalf("SelectedConcepts = %#v", got)
	}
	if len(plan.ConceptDecisions) != 2 {
		t.Fatalf("ConceptDecisions = %#v, want selected and rejected compatibility decisions", plan.ConceptDecisions)
	}
	if plan.ConceptDecisions[0].Decision != "selected" {
		t.Fatalf("first decision = %#v, want selected", plan.ConceptDecisions[0])
	}
	if plan.ConceptDecisions[1].Decision != "rejected" {
		t.Fatalf("second decision = %#v, want rejected", plan.ConceptDecisions[1])
	}
}

func TestNormalizePlanBackfillsMissingLegacyDecisionsForMixedInput(t *testing.T) {
	plan := NormalizePlan(Plan{
		ConceptDecisions: []ConceptDecision{
			{
				ConceptID:       "concept:GEN-ui:N-gui",
				Decision:        "selected",
				SelectionReason: "GUI owns the explicit user interaction surface.",
			},
		},
		SelectedConcepts: []string{"concept:GEN-ui:N-gui", "concept:GEN-ui:N-rendering"},
		RejectedConcepts: []string{"concept:GEN-ui:N-login"},
		SelectionReason:  "GUI and rendering match the request; login is out of scope.",
	})

	want := []ConceptDecision{
		{
			ConceptID:       "concept:GEN-ui:N-gui",
			Decision:        "selected",
			SelectionReason: "GUI owns the explicit user interaction surface.",
		},
		{
			ConceptID:       "concept:GEN-ui:N-rendering",
			Decision:        "selected",
			SelectionReason: "GUI and rendering match the request; login is out of scope.",
		},
		{
			ConceptID:       "concept:GEN-ui:N-login",
			Decision:        "rejected",
			SelectionReason: "GUI and rendering match the request; login is out of scope.",
		},
	}

	if len(plan.ConceptDecisions) != len(want) {
		t.Fatalf("ConceptDecisions = %#v, want %#v", plan.ConceptDecisions, want)
	}
	seen := map[string]bool{}
	for i, decision := range plan.ConceptDecisions {
		if decision.ConceptID != want[i].ConceptID || decision.Decision != want[i].Decision || decision.SelectionReason != want[i].SelectionReason {
			t.Fatalf("ConceptDecisions[%d] = %#v, want %#v", i, decision, want[i])
		}
		key := decision.ConceptID + "\x00" + decision.Decision
		if seen[key] {
			t.Fatalf("duplicate concept decision for %q/%q", decision.ConceptID, decision.Decision)
		}
		seen[key] = true
	}
}

func TestParsePlanSupportsAtFile(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "plan.json")
	if err := os.WriteFile(path, []byte(`{"paths":["docs/x.md"]}`), 0o644); err != nil {
		t.Fatal(err)
	}
	plan, err := ParsePlan("@"+path, "")
	if err != nil {
		t.Fatal(err)
	}
	if len(plan.Paths) != 1 || plan.Paths[0] != "docs/x.md" {
		t.Fatalf("paths = %#v", plan.Paths)
	}
}

func TestRunBlocksSplitBrainBaseline(t *testing.T) {
	paths := queryTestPaths(t)
	seedSplitBrainRuntime(t, paths)

	_, err := Run(paths, QueryInput{Query: "app", Plan: Plan{Paths: []string{"src/app.go"}}})

	if err == nil {
		t.Fatal("expected split-brain agreement error")
	}
	if !strings.Contains(err.Error(), "rewrite_status_from_db_metadata") {
		t.Fatalf("error = %q, want rewrite_status_from_db_metadata", err.Error())
	}
}

func TestLexiconBlocksSplitBrainBaseline(t *testing.T) {
	paths := queryTestPaths(t)
	seedSplitBrainRuntime(t, paths)

	_, err := Lexicon(paths, "plan", "app", 10)

	if err == nil {
		t.Fatal("expected split-brain agreement error")
	}
	if !strings.Contains(err.Error(), "rewrite_status_from_db_metadata") {
		t.Fatalf("error = %q, want rewrite_status_from_db_metadata", err.Error())
	}
}

func TestLexiconReturnsGraphCandidatesWithoutInventedTermConcepts(t *testing.T) {
	paths := queryTestPaths(t)
	seedReadyGraph(t, paths, store.ImportInput{
		GenerationID: "GEN-ui",
		Kind:         "full",
		SourceCommit: "abc123",
		Evidence: []store.EvidenceImport{{
			ID:          "E-gui",
			SourceKind:  "source",
			SourcePath:  "src/gui/window.tsx",
			CommitSHA:   "abc123",
			Extractor:   "test",
			ContentHash: "hash-gui",
		}, {
			ID:          "E-login",
			SourceKind:  "source",
			SourcePath:  "src/auth/login.tsx",
			CommitSHA:   "abc123",
			Extractor:   "test",
			ContentHash: "hash-login",
		}},
		Nodes: []store.NodeImport{{
			ID:          "N-gui",
			Type:        "capability",
			Title:       "GUI Shell",
			Confidence:  "verified",
			EvidenceIDs: []string{"E-gui"},
			Attrs: map[string]any{
				"aliases":            []any{"GUI", "desktop UI", "smoothness"},
				"domain":             "desktop",
				"owner":              "frontend",
				"verification_hints": []any{"npm test -- gui"},
			},
		}, {
			ID:          "N-login",
			Type:        "capability",
			Title:       "Login Flow",
			Confidence:  "verified",
			EvidenceIDs: []string{"E-login"},
			Attrs:       map[string]any{"aliases": []any{"login", "auth"}},
		}},
		PathIndex: []store.PathIndexImport{{
			ID:         "P-gui",
			Path:       "src/gui/window.tsx",
			NodeID:     "N-gui",
			Relation:   "owns",
			Confidence: "verified",
			EvidenceID: "E-gui",
		}, {
			ID:         "P-login",
			Path:       "src/auth/login.tsx",
			NodeID:     "N-login",
			Relation:   "owns",
			Confidence: "verified",
			EvidenceID: "E-login",
		}},
	})

	payload, err := Lexicon(paths, "debug", "The GUI feels laggy and not smooth", 10)
	if err != nil {
		t.Fatal(err)
	}
	if payload.ActiveGenerationID != "GEN-ui" || payload.LexiconGenerationID != "GEN-ui" {
		t.Fatalf("generation fields = %#v", payload)
	}
	if payload.CandidateUniverseVersion != CandidateUniverseVersion {
		t.Fatalf("CandidateUniverseVersion = %d", payload.CandidateUniverseVersion)
	}
	if len(payload.ConceptCandidates) == 0 {
		t.Fatal("ConceptCandidates is empty")
	}
	first := payload.ConceptCandidates[0]
	if first["concept_id"] != "concept:GEN-ui:N-gui" {
		t.Fatalf("first candidate = %#v, want GUI concept", first)
	}
	for _, candidate := range payload.ConceptCandidates {
		conceptID, ok := candidate["concept_id"].(string)
		if !ok {
			t.Fatalf("candidate concept_id is not string: %#v", candidate)
		}
		if strings.HasPrefix(conceptID, "term:") {
			t.Fatalf("lexicon invented term candidate: %#v", candidate)
		}
	}
	if payload.UnmappedIntent {
		t.Fatalf("UnmappedIntent = true with GUI graph candidate: %#v", payload)
	}
}

func TestLexiconRanksRelevantCandidateBeyondInitialWindow(t *testing.T) {
	paths := queryTestPaths(t)
	evidence := make([]store.EvidenceImport, 0, 60)
	nodes := make([]store.NodeImport, 0, 60)
	pathIndex := make([]store.PathIndexImport, 0, 60)
	for i := 1; i <= 60; i++ {
		nodeID := fmt.Sprintf("N-filler-%02d", i)
		title := fmt.Sprintf("Filler Concept %02d", i)
		sourcePath := fmt.Sprintf("src/filler/%02d.go", i)
		aliases := []any{"unrelated"}
		if i == 60 {
			nodeID = "N-render-latency"
			title = "Render Latency"
			sourcePath = "src/render/latency.go"
			aliases = []any{"render latency"}
		}
		suffix := strings.TrimPrefix(nodeID, "N-")
		evidenceID := "E-" + suffix
		pathID := "P-" + suffix
		evidence = append(evidence, store.EvidenceImport{
			ID:          evidenceID,
			SourceKind:  "source",
			SourcePath:  sourcePath,
			CommitSHA:   "abc123",
			Extractor:   "test",
			ContentHash: "hash-" + suffix,
		})
		nodes = append(nodes, store.NodeImport{
			ID:          nodeID,
			Type:        "capability",
			Title:       title,
			Confidence:  "verified",
			EvidenceIDs: []string{evidenceID},
			Attrs:       map[string]any{"aliases": aliases},
		})
		pathIndex = append(pathIndex, store.PathIndexImport{
			ID:         pathID,
			Path:       sourcePath,
			NodeID:     nodeID,
			Relation:   "owns",
			Confidence: "verified",
			EvidenceID: evidenceID,
		})
	}
	seedReadyGraph(t, paths, store.ImportInput{
		GenerationID: "GEN-latency",
		Kind:         "full",
		SourceCommit: "abc123",
		Evidence:     evidence,
		Nodes:        nodes,
		PathIndex:    pathIndex,
	})

	payload, err := Lexicon(paths, "debug", "render latency", 5)
	if err != nil {
		t.Fatal(err)
	}
	if len(payload.ConceptCandidates) == 0 {
		t.Fatal("ConceptCandidates is empty")
	}
	first := payload.ConceptCandidates[0]
	if first["concept_id"] != "concept:GEN-latency:N-render-latency" {
		t.Fatalf("first candidate = %#v, want late render latency concept", first)
	}
	if payload.UnmappedIntent {
		t.Fatalf("UnmappedIntent = true with late render latency candidate: %#v", payload)
	}
}

func TestLexiconReportsEmptyQueryTerms(t *testing.T) {
	paths := queryTestPaths(t)

	payload, err := Lexicon(paths, "implement", "!!!", 10)
	if err != nil {
		t.Fatal(err)
	}
	if !payload.UnmappedIntent {
		t.Fatalf("UnmappedIntent = false, payload = %#v", payload)
	}
	if !hasString(payload.MissingCoverage, "empty_query_terms") {
		t.Fatalf("MissingCoverage = %#v, want empty_query_terms", payload.MissingCoverage)
	}
	if len(payload.ConceptCandidates) != 0 {
		t.Fatalf("ConceptCandidates = %#v, want empty", payload.ConceptCandidates)
	}
	counts, ok := payload.CandidateUniverse["counts"].(map[string]any)
	if !ok {
		t.Fatalf("CandidateUniverse counts = %#v, want map", payload.CandidateUniverse["counts"])
	}
	if counts["nodes"] != 0 || counts["candidates"] != 0 {
		t.Fatalf("CandidateUniverse counts = %#v, want zero nodes and candidates", counts)
	}
}

func TestLexiconReportsUnmappedIntentWhenNoGraphCandidateMatches(t *testing.T) {
	paths := queryTestPaths(t)
	seedReadyGraph(t, paths, store.ImportInput{
		GenerationID: "GEN-ui",
		Kind:         "full",
		SourceCommit: "abc123",
		Evidence: []store.EvidenceImport{{
			ID:          "E-gui",
			SourceKind:  "source",
			SourcePath:  "src/gui/window.tsx",
			CommitSHA:   "abc123",
			Extractor:   "test",
			ContentHash: "hash-gui",
		}},
		Nodes: []store.NodeImport{{
			ID:          "N-gui",
			Type:        "capability",
			Title:       "GUI Shell",
			Confidence:  "verified",
			EvidenceIDs: []string{"E-gui"},
		}},
		PathIndex: []store.PathIndexImport{{
			ID:         "P-gui",
			Path:       "src/gui/window.tsx",
			NodeID:     "N-gui",
			Relation:   "owns",
			Confidence: "verified",
			EvidenceID: "E-gui",
		}},
	})

	payload, err := Lexicon(paths, "implement", "payment settlement ledger rounding", 10)
	if err != nil {
		t.Fatal(err)
	}
	if !payload.UnmappedIntent {
		t.Fatalf("UnmappedIntent = false, payload = %#v", payload)
	}
	if !hasString(payload.MissingCoverage, "no_graph_candidate_matched_query") {
		t.Fatalf("MissingCoverage = %#v, want no_graph_candidate_matched_query", payload.MissingCoverage)
	}
	for _, candidate := range payload.ConceptCandidates {
		conceptID, ok := candidate["concept_id"].(string)
		if !ok {
			t.Fatalf("candidate concept_id is not string: %#v", candidate)
		}
		if strings.HasPrefix(conceptID, "term:") {
			t.Fatalf("lexicon invented term candidate: %#v", candidate)
		}
	}
}

func TestRunBlocksStatusOnlyBaselineWithoutCreatingDatabase(t *testing.T) {
	paths := queryTestPaths(t)
	status := rt.DefaultStatus(paths)
	status.Status = "ok"
	status.Freshness = rt.ReadyFreshness
	status.Readiness = rt.ReadyReadiness
	status.GraphReady = true
	status.ActiveGenerationID = "GEN-status"
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}

	_, err := Run(paths, QueryInput{Query: "app", Plan: Plan{Paths: []string{"src/app.go"}}})

	if err == nil {
		t.Fatal("expected status-only agreement error")
	}
	if !strings.Contains(err.Error(), "project-cognition.db is missing") {
		t.Fatalf("error = %q, want missing DB", err.Error())
	}
	if _, statErr := os.Stat(paths.DatabasePath); !os.IsNotExist(statErr) {
		t.Fatalf("database stat err = %v, want missing DB", statErr)
	}
}

func TestRunBlocksIncompatibleDatabaseWithoutArchiving(t *testing.T) {
	paths := queryTestPaths(t)
	if err := os.MkdirAll(paths.RuntimeDir, 0o755); err != nil {
		t.Fatal(err)
	}
	db, err := sql.Open("sqlite", paths.DatabasePath)
	if err != nil {
		t.Fatal(err)
	}
	for _, statement := range []string{
		`CREATE TABLE metadata(key TEXT PRIMARY KEY, value_json TEXT NOT NULL, updated_at TEXT NOT NULL)`,
		`CREATE TABLE generations(id TEXT PRIMARY KEY, state TEXT NOT NULL)`,
		`INSERT INTO metadata(key, value_json, updated_at) VALUES('active_generation_id', '"GEN-db"', 'now')`,
		`INSERT INTO generations(id, state) VALUES('GEN-db', 'active')`,
	} {
		if _, err := db.Exec(statement); err != nil {
			_ = db.Close()
			t.Fatal(err)
		}
	}
	if err := db.Close(); err != nil {
		t.Fatal(err)
	}
	status := rt.DefaultStatus(paths)
	status.Status = "ok"
	status.Freshness = rt.ReadyFreshness
	status.Readiness = rt.ReadyReadiness
	status.GraphReady = true
	status.ActiveGenerationID = "GEN-db"
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}

	_, err = Run(paths, QueryInput{Query: "app", Plan: Plan{Paths: []string{"src/app.go"}}})

	if err == nil {
		t.Fatal("expected incompatible DB agreement error")
	}
	if !strings.Contains(err.Error(), "schema is incompatible") {
		t.Fatalf("error = %q, want incompatible schema", err.Error())
	}
	if _, statErr := os.Stat(paths.DatabasePath + ".legacy"); !os.IsNotExist(statErr) {
		t.Fatalf("legacy archive stat err = %v, want no archive", statErr)
	}
}

func TestRunMissingBaselineReturnsNeedsRebuildWithoutCreatingDatabase(t *testing.T) {
	paths := queryTestPaths(t)

	payload, err := Run(paths, QueryInput{Query: "app", Plan: Plan{Paths: []string{"src/app.go"}}})

	if err != nil {
		t.Fatalf("Run() error = %v", err)
	}
	if payload.Readiness != rt.NeedsRebuildReadiness {
		t.Fatalf("Readiness = %q, want needs_rebuild", payload.Readiness)
	}
	if payload.RecommendedNextAction != "run_map_scan_build" {
		t.Fatalf("RecommendedNextAction = %q, want run_map_scan_build", payload.RecommendedNextAction)
	}
	if _, statErr := os.Stat(paths.DatabasePath); !os.IsNotExist(statErr) {
		t.Fatalf("database stat err = %v, want missing DB", statErr)
	}
}

func queryTestPaths(t *testing.T) rt.Paths {
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

func seedReadyGraph(t *testing.T, paths rt.Paths, input store.ImportInput) {
	t.Helper()
	st, err := store.Open(paths)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := st.ImportGeneration(context.Background(), input); err != nil {
		_ = st.Close()
		t.Fatal(err)
	}
	generationID, err := st.ActiveGenerationID(context.Background())
	if err != nil {
		_ = st.Close()
		t.Fatal(err)
	}
	if _, _, err := st.PublishRuntimeMetadata(context.Background(), generationID); err != nil {
		_ = st.Close()
		t.Fatal(err)
	}
	if err := st.Close(); err != nil {
		t.Fatal(err)
	}
	status := rt.DefaultStatus(paths)
	status.Status = "ok"
	status.Freshness = rt.ReadyFreshness
	status.Readiness = rt.ReadyReadiness
	status.RecommendedNextAction = "use_project_cognition"
	status.GraphReady = true
	status.ActiveGenerationID = generationID
	status.QueryContractVersion = 1
	status.UpdateContractVersion = 1
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}
}

func hasString(values []string, want string) bool {
	for _, value := range values {
		if value == want {
			return true
		}
	}
	return false
}
