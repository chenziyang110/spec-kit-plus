package closeout

import (
	"context"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"strings"
	"testing"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/store"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/update"
)

func TestRunPlansPayloadModeForKnownMappedChange(t *testing.T) {
	root, paths := initCloseoutFixture(t)
	writeCloseoutFile(t, root, "src/app.go", "package app\n\nfunc App() string { return \"v2\" }\n")

	payload, err := Run(paths, Input{
		Workflow:           "implement",
		IncludeWorkingTree: true,
		IncludeUntracked:   true,
		PayloadPath:        ".specify/project-cognition/updates/custom.json",
	})
	if err != nil {
		t.Fatalf("Run returned error: %v", err)
	}

	if payload.Status != "ok" {
		t.Fatalf("Status = %q, errors=%#v", payload.Status, payload.Errors)
	}
	if payload.Workflow != "sp-implement" || payload.WorkflowCanonical != "sp-implement" {
		t.Fatalf("workflow fields = %q/%q", payload.Workflow, payload.WorkflowCanonical)
	}
	if payload.UpdateMode != "payload_file" {
		t.Fatalf("UpdateMode = %q, want payload_file", payload.UpdateMode)
	}
	if payload.PayloadDraft == nil {
		t.Fatal("PayloadDraft is nil")
	}
	if payload.PayloadDraft.Workflow != "sp-implement" {
		t.Fatalf("draft workflow = %q", payload.PayloadDraft.Workflow)
	}
	if !reflect.DeepEqual(payload.PayloadDraft.ChangedPaths, []string{"src/app.go"}) {
		t.Fatalf("ChangedPaths = %#v", payload.PayloadDraft.ChangedPaths)
	}
	if !reflect.DeepEqual(payload.KnownPaths, []string{"src/app.go"}) {
		t.Fatalf("KnownPaths = %#v", payload.KnownPaths)
	}
	if len(payload.UnknownPathDispositions) != 0 {
		t.Fatalf("UnknownPathDispositions = %#v, want none", payload.UnknownPathDispositions)
	}
	if !strings.Contains(payload.UpdateCommand, `project-cognition update --payload-file ".specify/project-cognition/updates/custom.json" --reason workflow-finalize --format json`) {
		t.Fatalf("UpdateCommand = %q", payload.UpdateCommand)
	}
	if !containsCloseoutString(payload.RequiredAgentFields, "verification") || !containsCloseoutString(payload.RequiredAgentFields, "behavior_surfaces") {
		t.Fatalf("RequiredAgentFields = %#v", payload.RequiredAgentFields)
	}
}

func TestRunQueuesUnknownPathDispositionWithoutBlockingKnownUnknown(t *testing.T) {
	root, paths := initCloseoutFixture(t)
	writeCloseoutFile(t, root, "src/new-feature.go", "package app\n\nfunc NewFeature() string { return \"new\" }\n")

	payload, err := Run(paths, Input{
		Workflow:           "quick",
		IncludeWorkingTree: true,
		IncludeUntracked:   true,
	})
	if err != nil {
		t.Fatalf("Run returned error: %v", err)
	}

	if payload.Workflow != "sp-quick" {
		t.Fatalf("Workflow = %q", payload.Workflow)
	}
	if !reflect.DeepEqual(payload.UnknownPaths, []string{"src/new-feature.go"}) {
		t.Fatalf("UnknownPaths = %#v", payload.UnknownPaths)
	}
	if len(payload.UnknownPathDispositions) != 1 {
		t.Fatalf("UnknownPathDispositions = %#v", payload.UnknownPathDispositions)
	}
	disposition := payload.UnknownPathDispositions[0]
	if disposition.Path != "src/new-feature.go" {
		t.Fatalf("Disposition path = %q", disposition.Path)
	}
	if disposition.ChangeLevel != "new_path" {
		t.Fatalf("ChangeLevel = %q, want new_path", disposition.ChangeLevel)
	}
	wantAllowed := []string{"adoptable", "review_only", "ignored", "blocking_known_unknown"}
	if !reflect.DeepEqual(disposition.AllowedDispositions, wantAllowed) {
		t.Fatalf("AllowedDispositions = %#v", disposition.AllowedDispositions)
	}
	if disposition.AgentDisposition != nil {
		t.Fatalf("AgentDisposition = %#v, want nil", disposition.AgentDisposition)
	}
	if !disposition.RequiredAgentDecision {
		t.Fatal("RequiredAgentDecision = false, want true")
	}
	if len(disposition.PlannerReason) == 0 {
		t.Fatal("PlannerReason is empty")
	}
	if payload.PayloadDraft == nil {
		t.Fatal("PayloadDraft is nil")
	}
	if len(payload.PayloadDraft.KnownUnknowns) != 0 {
		t.Fatalf("draft KnownUnknowns = %#v, want none", payload.PayloadDraft.KnownUnknowns)
	}
	if !containsCloseoutString(payload.RequiredAgentFields, "unknown_path_dispositions") {
		t.Fatalf("RequiredAgentFields = %#v, want unknown_path_dispositions", payload.RequiredAgentFields)
	}
}

func TestRunPreservesDeltaSessionMode(t *testing.T) {
	root, paths := initCloseoutFixture(t)
	writeCloseoutFile(t, root, "src/app.go", "package app\n\nfunc App() string { return \"delta\" }\n")

	payload, err := Run(paths, Input{
		Workflow:           "/sp.quick",
		DeltaSessionID:     "D-session",
		IncludeWorkingTree: true,
		IncludeUntracked:   true,
	})
	if err != nil {
		t.Fatalf("Run returned error: %v", err)
	}

	if payload.Workflow != "sp-quick" {
		t.Fatalf("Workflow = %q", payload.Workflow)
	}
	if payload.UpdateMode != "delta_session" {
		t.Fatalf("UpdateMode = %q", payload.UpdateMode)
	}
	if payload.DeltaSessionID == nil || *payload.DeltaSessionID != "D-session" {
		t.Fatalf("DeltaSessionID = %#v", payload.DeltaSessionID)
	}
	if payload.PayloadDraft != nil {
		t.Fatalf("PayloadDraft = %#v, want nil in delta mode", payload.PayloadDraft)
	}
	if !strings.Contains(payload.DeltaAppendCommand, `project-cognition delta append --session "D-session" --event-type workflow_closeout`) {
		t.Fatalf("DeltaAppendCommand = %q", payload.DeltaAppendCommand)
	}
	if !strings.Contains(payload.UpdateCommand, `project-cognition update --delta-session "D-session" --reason workflow-finalize --format json`) {
		t.Fatalf("UpdateCommand = %q", payload.UpdateCommand)
	}
	if payload.RecommendedNextCommand != "append_delta_then_update" {
		t.Fatalf("RecommendedNextCommand = %q", payload.RecommendedNextCommand)
	}
}

func TestRunBlocksUnknownWorkflowName(t *testing.T) {
	_, paths := initCloseoutFixture(t)

	payload, err := Run(paths, Input{
		Workflow:           "custom-flow",
		IncludeWorkingTree: true,
		IncludeUntracked:   true,
	})
	if err != nil {
		t.Fatalf("Run returned error: %v", err)
	}

	if payload.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked", payload.Status)
	}
	if len(payload.Errors) == 0 || !strings.Contains(payload.Errors[0], "unknown workflow") {
		t.Fatalf("Errors = %#v", payload.Errors)
	}
	if payload.UpdateCommand != "" {
		t.Fatalf("UpdateCommand = %q, want empty", payload.UpdateCommand)
	}
}

func initCloseoutFixture(t *testing.T) (string, rt.Paths) {
	t.Helper()
	root := t.TempDir()
	if err := os.MkdirAll(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatalf("create .specify: %v", err)
	}
	writeCloseoutFile(t, root, ".cognitionignore", ".specify/\n")
	writeCloseoutFile(t, root, "src/app.go", "package app\n\nfunc App() string { return \"v1\" }\n")
	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatalf("ResolvePaths: %v", err)
	}
	seedCloseoutRuntimePathIndex(t, paths)
	status := rt.DefaultStatus(paths)
	status.Status = "ok"
	status.Freshness = rt.ReadyFreshness
	status.Readiness = rt.ReadyReadiness
	status.GraphReady = true
	status.ActiveGenerationID = "GEN-closeout"
	status.BaselineKind = rt.BaselineKindBrownfieldFull
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatalf("WriteStatus: %v", err)
	}
	runCloseoutGit(t, root, "init")
	runCloseoutGit(t, root, "config", "user.email", "test@example.com")
	runCloseoutGit(t, root, "config", "user.name", "Test User")
	runCloseoutGit(t, root, "add", ".")
	runCloseoutGit(t, root, "commit", "-m", "baseline")
	if _, err := update.CompleteRefresh(paths, "map-build"); err != nil {
		t.Fatalf("CompleteRefresh: %v", err)
	}
	return root, paths
}

func seedCloseoutRuntimePathIndex(t *testing.T, paths rt.Paths) {
	t.Helper()
	st, err := store.Open(paths)
	if err != nil {
		t.Fatalf("store.Open: %v", err)
	}
	defer st.Close()
	if _, err := st.ImportGeneration(context.Background(), store.ImportInput{
		GenerationID: "GEN-closeout",
		Kind:         "full",
		SourceCommit: "abc123",
		Evidence: []store.EvidenceImport{{
			ID:          "E-app",
			SourceKind:  "file",
			SourcePath:  "src/app.go",
			CommitSHA:   "abc123",
			Extractor:   "test",
			ContentHash: "hash-app",
		}},
		Nodes: []store.NodeImport{{
			ID:          "N-app",
			Type:        "capability",
			Title:       "App",
			Confidence:  "verified",
			EvidenceIDs: []string{"E-app"},
		}},
		PathIndex: []store.PathIndexImport{{
			ID:         "P-app",
			Path:       "src/app.go",
			NodeID:     "N-app",
			Relation:   "owns",
			Confidence: "verified",
			EvidenceID: "E-app",
		}},
		Aliases: []store.AliasImport{{
			ID:              "ALIAS-app",
			Alias:           "App",
			NormalizedAlias: "app",
			TargetType:      "node",
			TargetID:        "N-app",
			Source:          "node_title",
			Confidence:      "verified",
		}},
	}); err != nil {
		t.Fatalf("ImportGeneration: %v", err)
	}
	if _, _, err := st.PublishRuntimeMetadata(context.Background(), "GEN-closeout", rt.BaselineKindBrownfieldFull); err != nil {
		t.Fatalf("PublishRuntimeMetadata: %v", err)
	}
}

func writeCloseoutFile(t *testing.T, root string, rel string, content string) {
	t.Helper()
	path := filepath.Join(root, rel)
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatalf("mkdir %s: %v", filepath.Dir(path), err)
	}
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatalf("write %s: %v", rel, err)
	}
}

func runCloseoutGit(t *testing.T, dir string, args ...string) string {
	t.Helper()
	cmd := exec.Command("git", args...)
	cmd.Dir = dir
	data, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("git %v failed: %v\n%s", args, err, data)
	}
	return string(data)
}

func containsCloseoutString(values []string, want string) bool {
	for _, value := range values {
		if value == want {
			return true
		}
	}
	return false
}
