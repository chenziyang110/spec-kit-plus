package closeout

import (
	"context"
	"encoding/json"
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
	wantArgv := []string{"project-cognition", "update", "--payload-file", ".specify/project-cognition/updates/custom.json", "--reason", "workflow-finalize", "--format", "json"}
	if !reflect.DeepEqual(payload.UpdateArgv, wantArgv) {
		t.Fatalf("UpdateArgv = %#v", payload.UpdateArgv)
	}
	if strings.Contains(payload.UpdateCommand, ".specify/project-cognition/updates/custom.json") {
		t.Fatalf("UpdateCommand = %q, want display-only placeholder without concrete path", payload.UpdateCommand)
	}
	if payload.PayloadDraft == nil || !reflect.DeepEqual(payload.PayloadDraft.UpdateArgv, wantArgv) {
		t.Fatalf("draft UpdateArgv = %#v", payload.PayloadDraft)
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
	if payload.DeltaAppendDraft == nil {
		t.Fatal("DeltaAppendDraft is nil")
	}
	if !reflect.DeepEqual(payload.DeltaAppendDraft.ChangedPaths, []string{"src/app.go"}) {
		t.Fatalf("DeltaAppendDraft.ChangedPaths = %#v", payload.DeltaAppendDraft.ChangedPaths)
	}
	if len(payload.DeltaAppendDraft.ArgvPlaceholders) == 0 || !containsCloseoutString(payload.DeltaAppendDraft.ArgvPlaceholders, "<agent-owned passing verification evidence>") {
		t.Fatalf("DeltaAppendDraft.ArgvPlaceholders = %#v", payload.DeltaAppendDraft.ArgvPlaceholders)
	}
	if !reflect.DeepEqual(payload.UpdateArgv, []string{"project-cognition", "update", "--delta-session", "D-session", "--reason", "workflow-finalize", "--format", "json"}) {
		t.Fatalf("UpdateArgv = %#v", payload.UpdateArgv)
	}
	if payload.RecommendedNextCommand != "fill_delta_append_draft_then_update" {
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
	assertBlockedArraysEncodeAsEmpty(t, payload)
}

func TestRunBlocksInRepoOutOfContractWorkflowNames(t *testing.T) {
	_, paths := initCloseoutFixture(t)

	for _, workflow := range []string{"sp-implement-teams", "sp-team"} {
		t.Run(workflow, func(t *testing.T) {
			payload, err := Run(paths, Input{
				Workflow:           workflow,
				IncludeWorkingTree: true,
				IncludeUntracked:   true,
			})
			if err != nil {
				t.Fatalf("Run returned error: %v", err)
			}
			if payload.Status != "blocked" {
				t.Fatalf("Status = %q, want blocked", payload.Status)
			}
			if payload.UpdateCommand != "" || len(payload.UpdateArgv) != 0 {
				t.Fatalf("update command fields = %q/%#v, want empty", payload.UpdateCommand, payload.UpdateArgv)
			}
			if len(payload.Errors) == 0 || !strings.Contains(payload.Errors[0], "unknown workflow") {
				t.Fatalf("Errors = %#v", payload.Errors)
			}
			assertBlockedArraysEncodeAsEmpty(t, payload)
		})
	}
}

func TestRunUsesStructuredArgvForShellMetacharacters(t *testing.T) {
	root, paths := initCloseoutFixture(t)
	writeCloseoutFile(t, root, "src/app.go", "package app\n\nfunc App() string { return \"meta\" }\n")

	payloadPath := `.specify/project-cognition/updates/closeout"; rm -rf nope; ".json`
	sessionID := `D-session"; rm -rf nope; "`

	payload, err := Run(paths, Input{
		Workflow:           "implement",
		Reason:             `workflow-finalize"; rm -rf nope; "`,
		IncludeWorkingTree: true,
		IncludeUntracked:   true,
		PayloadPath:        payloadPath,
	})
	if err != nil {
		t.Fatalf("Run payload mode returned error: %v", err)
	}
	if strings.Contains(payload.UpdateCommand, payloadPath) {
		t.Fatalf("UpdateCommand includes user-supplied payload path: %q", payload.UpdateCommand)
	}
	if !containsCloseoutString(payload.UpdateArgv, payloadPath) {
		t.Fatalf("UpdateArgv = %#v, want payload path as one argv element", payload.UpdateArgv)
	}

	deltaPayload, err := Run(paths, Input{
		Workflow:           "quick",
		DeltaSessionID:     sessionID,
		IncludeWorkingTree: true,
		IncludeUntracked:   true,
	})
	if err != nil {
		t.Fatalf("Run delta mode returned error: %v", err)
	}
	if strings.Contains(deltaPayload.UpdateCommand, sessionID) || strings.Contains(deltaPayload.DeltaAppendCommand, sessionID) {
		t.Fatalf("display command leaked session id: update=%q delta=%q", deltaPayload.UpdateCommand, deltaPayload.DeltaAppendCommand)
	}
	if !containsCloseoutString(deltaPayload.UpdateArgv, sessionID) {
		t.Fatalf("UpdateArgv = %#v, want session id as one argv element", deltaPayload.UpdateArgv)
	}
	if deltaPayload.DeltaAppendDraft == nil || !containsCloseoutString(deltaPayload.DeltaAppendDraft.ArgvPrefix, sessionID) {
		t.Fatalf("DeltaAppendDraft = %#v, want session id in structured argv prefix", deltaPayload.DeltaAppendDraft)
	}
}

func TestRunThreadsReasonAndIntentDefaults(t *testing.T) {
	root, paths := initCloseoutFixture(t)
	writeCloseoutFile(t, root, "src/app.go", "package app\n\nfunc App() string { return \"reason\" }\n")

	payload, err := Run(paths, Input{
		Workflow:           "implement",
		Reason:             "custom-closeout",
		Intent:             "custom-intent",
		IncludeWorkingTree: true,
		IncludeUntracked:   true,
	})
	if err != nil {
		t.Fatalf("Run returned error: %v", err)
	}
	if payload.PayloadDraft == nil {
		t.Fatal("PayloadDraft is nil")
	}
	if payload.PayloadDraft.Reason != "custom-closeout" {
		t.Fatalf("PayloadDraft.Reason = %q", payload.PayloadDraft.Reason)
	}
	if !reflect.DeepEqual(payload.UpdateArgv, []string{"project-cognition", "update", "--payload-file", ".specify/project-cognition/updates/sp-implement-closeout.json", "--reason", "custom-closeout", "--format", "json"}) {
		t.Fatalf("UpdateArgv = %#v", payload.UpdateArgv)
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

func assertBlockedArraysEncodeAsEmpty(t *testing.T, payload Payload) {
	t.Helper()
	data, err := json.Marshal(payload)
	if err != nil {
		t.Fatalf("Marshal payload: %v", err)
	}
	encoded := string(data)
	for _, want := range []string{
		`"update_argv":[]`,
		`"required_agent_fields":[]`,
		`"known_paths":[]`,
		`"unknown_paths":[]`,
		`"unknown_path_dispositions":[]`,
		`"changes":[]`,
		`"warnings":[]`,
	} {
		if !strings.Contains(encoded, want) {
			t.Fatalf("blocked payload JSON = %s, want %s", encoded, want)
		}
	}
}
