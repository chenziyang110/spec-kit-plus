package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestArtifactTypeRegistryDescribesCanonicalAndDerivedArtifacts(t *testing.T) {
	specType, ok := LookupArtifactType(".specify/features/001-runtime/spec.md")
	if !ok {
		t.Fatalf("spec artifact type was not found")
	}
	if specType.TypeID != "feature-spec" || specType.Owner != "specify-runtime artifact" || specType.Role != "canonical" {
		t.Fatalf("spec artifact type = %#v", specType)
	}
	if specType.Schema == "" || specType.SummaryAdapter == "" || len(specType.Operations) == 0 {
		t.Fatalf("spec artifact type missing metadata = %#v", specType)
	}

	taskIndexType, ok := LookupArtifactType(".specify/features/001-runtime/task-index.json")
	if !ok {
		t.Fatalf("task index artifact type was not found")
	}
	if taskIndexType.TypeID != "feature-task-index" || taskIndexType.Role != "canonical" {
		t.Fatalf("task index artifact type = %#v", taskIndexType)
	}
}

func TestArtifactTypeRegistryCoversCrossWorkflowControlPlaneArtifacts(t *testing.T) {
	tests := map[string]string{
		"specs/001-runtime/specify-draft.md":                                 "feature-specify-draft",
		"specs/001-runtime/alignment.md":                                     "feature-alignment",
		"specs/001-runtime/context.md":                                       "feature-context",
		"specs/001-runtime/references.md":                                    "feature-references",
		"specs/001-runtime/data-model.md":                                    "feature-data-model",
		"specs/001-runtime/quickstart.md":                                    "feature-quickstart",
		"specs/001-runtime/clarification/evidence-index.json":                "clarification-evidence-index",
		"specs/001-runtime/clarification/checkpoints.ndjson":                 "clarification-checkpoints",
		"specs/001-runtime/clarification/handoffs/lane-01.json":              "clarification-handoff",
		"specs/001-runtime/ui-reference-notes.md":                            "feature-ui-reference-notes",
		"specs/001-runtime/research-evidence/EVD-001.json":                   "research-evidence-json",
		"specs/001-runtime/visual-comparison-T001.json":                      "feature-visual-comparison",
		"specs/001-runtime/implementation-review/deferrals/DEF-001.json":     "implementation-deferral",
		"specs/001-runtime/implementation-review/validation-runs.json":       "implementation-validation-ledger",
		"specs/001-runtime/implementation-review/execution-state.json":       "implementation-execution-state",
		"specs/001-runtime/implementation-review/ledger.json":                "implementation-review-ledger",
		"specs/001-runtime/implementation-review/branch-review.md":           "implementation-branch-review",
		"specs/001-runtime/implementation-review/task-briefs/T001.md":        "implementation-task-brief",
		"specs/001-runtime/implementation-review/review-packages/T001.md":    "implementation-review-package",
		"specs/001-runtime/implementation-review/task-reviews/T001.json":     "implementation-task-review",
		"specs/001-runtime/implementation-review/validation-evidence/V1.txt": "implementation-validation-evidence",
		"specs/001-runtime/handoff-to-implement.json":                        "feature-implement-handoff",
		".specify/worker-results/lane-01.json":                               "shared-worker-result",
		".planning/quick/001-fix/worker-results/lane-01.json":                "quick-worker-result",
		".planning/quick/001-fix/PLAN.md":                                    "quick-plan",
		".planning/quick/001-fix/RESEARCH.md":                                "quick-support",
		".planning/quick/001-fix/DISCUSSION.md":                              "quick-support",
		".planning/debug/session.md":                                         "debug-session",
		"specs/001-runtime/checklists/requirements.md":                       "feature-checklist",
		".specify/design/previews/round-01.manifest.json":                    "design-preview-manifest",
		".specify/design/previews/round-01.html":                             "design-html",
		".specify/design/design-brief.md":                                    "design-brief",
		".specify/discussions/index.json":                                    "discussion-index",
		".specify/teams/state/results/request-001.json":                      "teams-runtime-state",
		"specs/001-runtime/brainstorming/stage-manifest.json":                "brainstorming-compatibility-json",
		"specs/001-runtime/brainstorming/journal.ndjson":                     "brainstorming-compatibility-journal",
		"specs/001-runtime/brainstorming/handoff-to-specify.json":            "brainstorming-compatibility-handoff",
		"specs/001-runtime/.human-acceptance-repair.json":                    "acceptance-repair-journal",
		"specs/001-runtime/.human-acceptance-repair-backup.json":             "acceptance-repair-backup",
	}
	for path, wantType := range tests {
		metadata, ok := LookupArtifactType(path)
		if !ok || metadata.TypeID != wantType {
			t.Fatalf("LookupArtifactType(%q) = %#v, %v; want type %q", path, metadata, ok, wantType)
		}
	}

	manifest, ok := LookupArtifactType(".specify/design/previews/round-01.manifest.json")
	if !ok || manifest.Role != "canonical" || !artifactTypeAllows(manifest, "patch") {
		t.Fatalf("design preview manifest must support leased patches: %#v, %v", manifest, ok)
	}

	prdState, ok := LookupArtifactType(".specify/prd-runs/260729-demo/workflow-state.md")
	if !ok || prdState.Role != "canonical" || !artifactTypeAllows(prdState, "patch") {
		t.Fatalf("PRD workflow state must support leased patches after runtime initialization: %#v, %v", prdState, ok)
	}
}

func TestDeterministicScaffoldArtifactsRejectWholeFileSubmit(t *testing.T) {
	tests := map[string]string{
		".specify/memory/constitution.md":                                  "project-constitution",
		".planning/debug/session.md":                                       "debug-session",
		".planning/quick/001-runtime/PLAN.md":                              "quick-plan",
		"specs/001-runtime/deep-research.md":                               "feature-deep-research",
		".specify/design/design-brief.md":                                  "design-brief",
		".specify/design/review.md":                                        "design-review",
		"specs/001-runtime/plan-contract.json":                             "feature-plan-contract",
		"specs/001-runtime/planning/lane-manifest.json":                    "planning-lane-manifest",
		"specs/001-runtime/specify-draft.md":                               "feature-specify-draft",
		"specs/001-runtime/alignment.md":                                   "feature-alignment",
		"specs/001-runtime/context.md":                                     "feature-context",
		"specs/001-runtime/references.md":                                  "feature-references",
		"specs/001-runtime/data-model.md":                                  "feature-data-model",
		"specs/001-runtime/quickstart.md":                                  "feature-quickstart",
		"specs/001-runtime/clarification/evidence-index.json":              "clarification-evidence-index",
		"specs/001-runtime/clarification/checkpoints.ndjson":               "clarification-checkpoints",
		".planning/quick/001-runtime/STATUS.md":                            "quick-status",
		".planning/quick/001-runtime/SUMMARY.md":                           "quick-summary",
		"specs/001-runtime/research.md":                                    "feature-research",
		"specs/001-runtime/spec-contract.json":                             "specs-spec-contract",
		".specify/features/001-runtime/spec-contract.json":                 "feature-spec-contract",
		".specify/features/001-runtime/task-generation/lane-manifest.json": "task-generation-lane-manifest",
		"specs/001-runtime/ui-brief.md":                                    "feature-ui-brief",
		"specs/001-runtime/ui-reference-notes.md":                          "feature-ui-reference-notes",
		"specs/001-runtime/workflow-state.md":                              "feature-workflow-state",
	}
	for path, wantType := range tests {
		metadata, ok := LookupArtifactType(path)
		if !ok || metadata.TypeID != wantType {
			t.Fatalf("LookupArtifactType(%q) = %#v, %v; want %q", path, metadata, ok, wantType)
		}
		if artifactTypeAllows(metadata, "submit") || !artifactTypeAllows(metadata, "patch") {
			t.Fatalf("scaffold artifact %q operations = %#v, want patch without submit", path, metadata.Operations)
		}
	}
}

func TestSpecializedArtifactsExposeOnlyTheirRegisteredMutationCommands(t *testing.T) {
	tests := []struct {
		path      string
		wantType  string
		wantOps   []string
		forbidOps []string
	}{
		{
			path:      "specs/001-runtime/checklists/requirements.md",
			wantType:  "feature-checklist",
			wantOps:   []string{"checklist", "patch", "delete"},
			forbidOps: []string{"submit"},
		},
		{
			path:      ".planning/debug/session.md",
			wantType:  "debug-session",
			wantOps:   []string{"patch", "delete"},
			forbidOps: []string{"submit"},
		},
		{
			path:      ".planning/quick/001-runtime/PLAN.md",
			wantType:  "quick-plan",
			wantOps:   []string{"patch", "delete"},
			forbidOps: []string{"submit"},
		},
	}
	for _, test := range tests {
		metadata, ok := LookupArtifactType(test.path)
		if !ok || metadata.TypeID != test.wantType {
			t.Fatalf("LookupArtifactType(%q) = %#v, %v; want %q", test.path, metadata, ok, test.wantType)
		}
		for _, operation := range test.wantOps {
			if !artifactTypeAllows(metadata, operation) {
				t.Fatalf("%s operations = %#v, want %q", test.path, metadata.Operations, operation)
			}
		}
		for _, operation := range test.forbidOps {
			if artifactTypeAllows(metadata, operation) {
				t.Fatalf("%s operations = %#v, forbid %q", test.path, metadata.Operations, operation)
			}
		}
	}
}

func TestArtifactShowBlocksOversizedExpandedReads(t *testing.T) {
	projectRoot := t.TempDir()
	service := NewArtifactService(projectRoot)
	large := strings.Repeat("x", maxArtifactExpandedViewBytes+1)

	writeArtifactTestFile(t, projectRoot, "specs/001-runtime/spec.md", large)
	summary := service.Show(ArtifactShowRequest{
		Path: "specs/001-runtime/spec.md",
	})
	if summary.Status != "ok" || summary.Data["full_view_requires_targeted_query"] != true || len(summary.ShowArgv) == 0 {
		t.Fatalf("oversized summary did not recommend a targeted read: %#v", summary)
	}
	full := service.Show(ArtifactShowRequest{
		Path: "specs/001-runtime/spec.md",
		View: "full",
	})
	if full.Status != "blocked" || full.Data["content"] != nil || len(full.NextArgv) == 0 {
		t.Fatalf("oversized full view was not bounded: %#v", full)
	}

	raw, err := json.Marshal(map[string]any{"payload": large})
	if err != nil {
		t.Fatal(err)
	}
	writeArtifactTestFile(t, projectRoot, "specs/001-runtime/task-index.json", string(raw))
	queried := service.Show(ArtifactShowRequest{
		Path:        "specs/001-runtime/task-index.json",
		JSONPointer: "/payload",
	})
	if queried.Status != "blocked" || queried.Data["query_result"] != nil || len(queried.NextArgv) == 0 {
		t.Fatalf("oversized query result was not bounded: %#v", queried)
	}
}

func TestArtifactTypeRegistryPreservesDiscussionCanonicalStateRoles(t *testing.T) {
	jsonState, ok := LookupArtifactType(".specify/discussions/runtime/discussion-state.json")
	if !ok || jsonState.TypeID != "discussion-state-json" || jsonState.Role != "canonical" {
		t.Fatalf("discussion JSON state = %#v, %v; want canonical", jsonState, ok)
	}
	markdownState, ok := LookupArtifactType(".specify/discussions/runtime/discussion-state.md")
	if !ok || markdownState.TypeID != "discussion-state-markdown" || markdownState.Role != "derived" {
		t.Fatalf("discussion Markdown state = %#v, %v; want derived", markdownState, ok)
	}
}

func TestArtifactListDiscoversRegisteredInstancesCompactly(t *testing.T) {
	projectRoot := t.TempDir()
	writeArtifactTestFile(t, projectRoot, ".specify/features/001-runtime/spec.md", "# Runtime\n\n## Scope\n\n- One\n")
	writeArtifactTestFile(t, projectRoot, ".specify/features/001-runtime/task-index.json", `{"tasks":[{"id":"T-1"},{"id":"T-2"}]}`)

	service := NewArtifactService(projectRoot)
	result := service.ListArtifacts(ArtifactListRequest{
		PathPrefix: ".specify/features/001-runtime/",
		Limit:      10,
	})
	if result.Status != "ok" {
		t.Fatalf("list status = %q, want ok: %#v", result.Status, result)
	}

	items, ok := result.Data["items"].([]map[string]any)
	if !ok {
		t.Fatalf("list items = %#v, want []map[string]any", result.Data["items"])
	}
	if len(items) != 2 {
		t.Fatalf("list item count = %d, want 2", len(items))
	}
	for _, item := range items {
		if item["content"] != nil {
			t.Fatalf("list leaked content: %#v", item)
		}
		if item["canonical_path"] == "" || item["type_id"] == "" || item["owner"] == "" {
			t.Fatalf("list item missing registry metadata: %#v", item)
		}
	}
}

func TestArtifactShowSupportsJSONPointerSectionAndLimit(t *testing.T) {
	projectRoot := t.TempDir()
	service := NewArtifactService(projectRoot)

	writeArtifactTestFile(
		t,
		projectRoot,
		".specify/features/001-runtime/task-index.json",
		`{"tasks":[{"id":"T-1"},{"id":"T-2"},{"id":"T-3"}],"meta":{"count":3}}`,
	)

	jsonShown := service.Show(ArtifactShowRequest{
		Path:        ".specify/features/001-runtime/task-index.json",
		JSONPointer: "/tasks",
		Limit:       2,
	})
	if jsonShown.Status != "ok" {
		t.Fatalf("json show = %#v", jsonShown)
	}
	if _, leaked := jsonShown.Data["content"]; leaked {
		t.Fatalf("json query leaked full content: %#v", jsonShown.Data)
	}
	query, ok := jsonShown.Data["query_result"].([]any)
	if !ok || len(query) != 2 {
		t.Fatalf("json query result = %#v, want two tasks", jsonShown.Data["query_result"])
	}

	mdPrepared := service.Prepare(ArtifactPrepareRequest{Path: "specs/001-runtime/spec.md"})
	mdSubmitted := service.Submit(ArtifactSubmitRequest{
		LeaseID: mdPrepared.Data["lease_id"].(string),
		Content: []byte("# Runtime\n\n## Requirements\n\n- R1\n- R2\n- R3\n\n## Notes\n\n- N1\n"),
	})
	if mdSubmitted.Status != "ok" {
		t.Fatalf("markdown submit = %#v", mdSubmitted)
	}

	mdShown := service.Show(ArtifactShowRequest{
		Path:    "specs/001-runtime/spec.md",
		Section: "Requirements",
		Limit:   2,
	})
	if mdShown.Status != "ok" {
		t.Fatalf("markdown show = %#v", mdShown)
	}
	section, ok := mdShown.Data["query_result"].(string)
	if !ok {
		t.Fatalf("markdown query result = %#v, want string", mdShown.Data["query_result"])
	}
	if section == "" || section == "# Runtime\n\n## Requirements\n\n- R1\n- R2\n- R3\n\n## Notes\n\n- N1\n" {
		t.Fatalf("markdown section query did not isolate a compact section: %q", section)
	}
}

func TestArtifactGenericMutationRejectsSpecializedStateAndHandoffArtifacts(t *testing.T) {
	service := NewArtifactService(t.TempDir())
	for _, path := range []string{
		".specify/features/001-runtime/task-index.json",
		".specify/features/001-runtime/implementation-handoff.json",
		"specs/001-runtime/task-index.json",
		"specs/001-runtime/tasks.md",
		"specs/001-runtime/implementation-handoff.json",
		"specs/001-runtime/implementation-summary.md",
		"specs/001-runtime/implement-tracker.md",
		"specs/001-runtime/implementation-review/tasks/T001.json",
		"specs/001-runtime/implementation-review/packets/T001.json",
		"specs/001-runtime/worker-results/T001.json",
		"DESIGN.md",
		".specify/prd/status.json",
	} {
		prepared := service.Prepare(ArtifactPrepareRequest{Path: path})
		if prepared.Status != "invalid" {
			t.Fatalf("specialized artifact %q prepare = %#v, want invalid", path, prepared)
		}
		if len(prepared.Blockers) == 0 || prepared.Data["owner"] == nil {
			t.Fatalf("specialized artifact %q lacks owner guidance: %#v", path, prepared)
		}
	}
}

func TestArtifactGenericMutationRejectsUnregisteredWorkflowArtifact(t *testing.T) {
	service := NewArtifactService(t.TempDir())
	prepared := service.Prepare(ArtifactPrepareRequest{
		Path: ".specify/features/001-runtime/invented-state.json",
	})
	if prepared.Status != "invalid" {
		t.Fatalf("unregistered workflow artifact prepare = %#v, want invalid", prepared)
	}
}

func TestArtifactPrepareWritesLeaseLifecycleAndPrunesExpiredLeases(t *testing.T) {
	projectRoot := t.TempDir()
	service := NewArtifactService(projectRoot)

	prepared := service.Prepare(ArtifactPrepareRequest{Path: "specs/001-runtime/spec.md"})
	if prepared.Status != "ok" {
		t.Fatalf("prepare = %#v", prepared)
	}
	leaseID := prepared.Data["lease_id"].(string)

	lease, err := service.readLease(leaseID)
	if err != nil {
		t.Fatalf("read lease: %v", err)
	}
	if lease.CreatedAt == "" || lease.ExpiresAt == "" {
		t.Fatalf("lease lifecycle fields missing: %#v", lease)
	}

	lease.ExpiresAt = time.Now().Add(-time.Hour).UTC().Format(time.RFC3339)
	if err := service.writeLease(lease); err != nil {
		t.Fatalf("rewrite expired lease: %v", err)
	}

	result := service.PruneLeases(ArtifactPruneRequest{
		Now:   time.Now().UTC(),
		Limit: 10,
	})
	if result.Status != "ok" {
		t.Fatalf("prune result = %#v", result)
	}
	if result.Data["pruned"] != 1 {
		t.Fatalf("pruned count = %#v, want 1", result.Data["pruned"])
	}
	if _, err := service.readLease(leaseID); !os.IsNotExist(err) {
		t.Fatalf("expired lease still exists: %v", err)
	}
}

func writeArtifactTestFile(t *testing.T, projectRoot, relativePath, content string) {
	t.Helper()
	target := filepath.Join(projectRoot, filepath.FromSlash(relativePath))
	if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(target, []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
}

func TestArtifactPruneSkipsInvalidLeaseFiles(t *testing.T) {
	projectRoot := t.TempDir()
	service := NewArtifactService(projectRoot)

	leaseDir, err := secureProjectPath(projectRoot, filepath.ToSlash(filepath.Join(".specify", "runtime", "leases")))
	if err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(leaseDir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(leaseDir, "corrupt.json"), []byte(`{"id":`), 0o644); err != nil {
		t.Fatal(err)
	}
	valid := artifactLease{
		ID:            "lease-test-valid",
		CanonicalPath: "specs/001-runtime/spec.md",
		CreatedAt:     time.Now().Add(-2 * time.Hour).UTC().Format(time.RFC3339),
		ExpiresAt:     time.Now().Add(-time.Hour).UTC().Format(time.RFC3339),
	}
	if err := service.writeLease(valid); err != nil {
		t.Fatal(err)
	}

	result := service.PruneLeases(ArtifactPruneRequest{
		Now:   time.Now().UTC(),
		Limit: 10,
	})
	if result.Status != "ok" {
		t.Fatalf("prune result = %#v", result)
	}
	if result.Data["pruned"] != 1 {
		t.Fatalf("pruned count = %#v, want 1", result.Data["pruned"])
	}

	raw, err := os.ReadFile(filepath.Join(leaseDir, "corrupt.json"))
	if err != nil {
		t.Fatalf("corrupt lease file should remain for diagnosis: %v", err)
	}
	var payload map[string]any
	if err := json.Unmarshal(raw, &payload); err == nil {
		t.Fatalf("corrupt lease unexpectedly became valid: %#v", payload)
	}
}
