package main

import (
	"crypto/sha256"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestArtifactShowManyReturnsIndependentQueryStatuses(t *testing.T) {
	projectRoot := t.TempDir()
	writeArtifactTestFile(t, projectRoot, "specs/001-runtime/spec.md", "# Runtime\n\n## Current\n\nready\n")
	writeArtifactTestFile(t, projectRoot, "specs/001-runtime/spec-contract.json", `{"nested":{"value":"kept"}}`)

	result := NewArtifactService(projectRoot).ShowMany(ArtifactShowManyRequest{Queries: []ArtifactShowRequest{
		{Path: "specs/001-runtime/spec.md", Section: "Current"},
		{Path: "specs/002-runtime/spec.md", View: "summary"},
		{Path: "specs/001-runtime/spec-contract.json", JSONPointer: "/nested/value"},
	}})

	if result.Status != "warn" {
		t.Fatalf("show-many status = %q, want warn: %#v", result.Status, result)
	}
	if len(result.Items) != 3 {
		t.Fatalf("show-many items = %d, want 3: %#v", len(result.Items), result.Items)
	}
	if item := requireArtifactBatchItem(t, result, 0); item["status"] != "ok" {
		t.Fatalf("first item = %#v, want ok", item)
	}
	if item := requireArtifactBatchItem(t, result, 1); item["status"] != "blocked" {
		t.Fatalf("second item = %#v, want blocked", item)
	}
	third := requireArtifactBatchItem(t, result, 2)
	if third["status"] != "ok" {
		t.Fatalf("third item = %#v, want ok", third)
	}
	thirdData, ok := third["data"].(map[string]any)
	if !ok || thirdData["query_result"] != "kept" {
		t.Fatalf("third query data = %#v, want kept", third["data"])
	}
	if result.Data["query_count"] != 3 || result.Data["ok_queries"] != 2 || result.Data["failed_queries"] != 1 {
		t.Fatalf("show-many counts = %#v", result.Data)
	}
}

func TestArtifactShowManyEnforcesQueryCountLimitBeforeReading(t *testing.T) {
	queries := make([]ArtifactShowRequest, maxArtifactShowManyQueries+1)
	for index := range queries {
		queries[index] = ArtifactShowRequest{Path: "specs/001-runtime/spec.md"}
	}

	result := NewArtifactService(t.TempDir()).ShowMany(ArtifactShowManyRequest{Queries: queries})

	if result.Status != "invalid" || len(result.Items) != 0 {
		t.Fatalf("oversized show-many = %#v, want invalid with no reads", result)
	}
	if len(result.Blockers) == 0 || !strings.Contains(fmt.Sprint(result.Blockers), fmt.Sprint(maxArtifactShowManyQueries)) {
		t.Fatalf("oversized show-many blockers = %#v", result.Blockers)
	}
}

func TestArtifactShowManyBoundsAggregateOutputAndReportsOmittedItems(t *testing.T) {
	projectRoot := t.TempDir()
	largeBody := "# Runtime\n\n" + strings.Repeat("x", 80*1024)
	writeArtifactTestFile(t, projectRoot, "specs/001-runtime/spec.md", largeBody)
	writeArtifactTestFile(t, projectRoot, "specs/002-runtime/spec.md", largeBody)

	result := NewArtifactService(projectRoot).ShowMany(ArtifactShowManyRequest{Queries: []ArtifactShowRequest{
		{Path: "specs/001-runtime/spec.md", View: "full"},
		{Path: "specs/002-runtime/spec.md", View: "full"},
	}})

	encoded, err := json.Marshal(result)
	if err != nil {
		t.Fatal(err)
	}
	if len(encoded) > maxArtifactShowManyOutputBytes {
		t.Fatalf("show-many encoded bytes = %d, limit = %d", len(encoded), maxArtifactShowManyOutputBytes)
	}
	if result.Status != "warn" || len(result.Items) != 2 || result.Data["omitted_queries"] != 1 {
		t.Fatalf("bounded show-many = %#v", result)
	}
	if requireArtifactBatchItem(t, result, 0)["status"] != "ok" || requireArtifactBatchItem(t, result, 1)["status"] != "blocked" {
		t.Fatalf("bounded show-many item statuses = %#v", result.Items)
	}
}

func TestArtifactPatchBatchAppliesMarkdownOperationsWithOneValidationAndAtomicWrite(t *testing.T) {
	projectRoot := t.TempDir()
	path := "specs/001-runtime/workflow-state.md"
	writeArtifactTestFile(t, projectRoot, path, "---\nstatus: draft\nconfirmed: false\n---\n\n# State\n\n## Current\n\nold\n\n## Evidence\n\nnone\n")
	service := NewArtifactService(projectRoot)
	leaseID := prepareArtifactBatchLease(t, service, path)

	priorValidate := validateArtifactBatchContent
	priorWrite := writeArtifactBatchFile
	validationCalls := 0
	writeCalls := 0
	validateArtifactBatchContent = func(canonicalPath string, content []byte) error {
		validationCalls++
		return validateArtifactContent(canonicalPath, content)
	}
	writeArtifactBatchFile = func(target string, content []byte, perm os.FileMode) error {
		writeCalls++
		return atomicWriteFile(target, content, perm)
	}
	t.Cleanup(func() {
		validateArtifactBatchContent = priorValidate
		writeArtifactBatchFile = priorWrite
	})

	result := service.PatchBatch(ArtifactPatchBatchRequest{
		LeaseID: leaseID,
		Operations: []ArtifactPatchBatchOperation{
			{Section: "Current", Content: "new"},
			{Section: "Evidence", Content: "captured"},
			{Frontmatter: map[string]any{"status": "ready", "confirmed": true}},
		},
	})

	if result.Status != "ok" {
		t.Fatalf("patch-batch = %#v", result)
	}
	if validationCalls != 1 || writeCalls != 1 {
		t.Fatalf("validation calls = %d, atomic writes = %d; want 1 each", validationCalls, writeCalls)
	}
	stored, err := os.ReadFile(filepath.Join(projectRoot, filepath.FromSlash(path)))
	if err != nil {
		t.Fatal(err)
	}
	for _, expected := range []string{"status: \"ready\"", "confirmed: true", "## Current\n\nnew", "## Evidence\n\ncaptured"} {
		if !strings.Contains(string(stored), expected) {
			t.Fatalf("stored markdown missing %q:\n%s", expected, stored)
		}
	}
	wantDigest := fmt.Sprintf("%x", sha256.Sum256(stored))
	if result.Data["after_sha256"] != wantDigest || result.Data["operation_count"] != 3 {
		t.Fatalf("patch-batch result data = %#v", result.Data)
	}
	changedTargets, ok := result.Data["changed_targets"].([]map[string]any)
	if !ok || len(changedTargets) != 3 {
		t.Fatalf("changed_targets = %#v, want three compact targets", result.Data["changed_targets"])
	}
}

func TestArtifactPatchBatchAppliesMultipleJSONPointers(t *testing.T) {
	projectRoot := t.TempDir()
	path := "specs/001-runtime/spec-contract.json"
	writeArtifactTestFile(t, projectRoot, path, `{"state":{"status":"draft","count":1},"keep":true}`)
	service := NewArtifactService(projectRoot)

	result := service.PatchBatch(ArtifactPatchBatchRequest{
		LeaseID: prepareArtifactBatchLease(t, service, path),
		Operations: []ArtifactPatchBatchOperation{
			{JSONPointer: "/state/status", Value: "ready"},
			{JSONPointer: "/state/count", Value: 2},
		},
	})

	if result.Status != "ok" {
		t.Fatalf("json patch-batch = %#v", result)
	}
	stored, err := os.ReadFile(filepath.Join(projectRoot, filepath.FromSlash(path)))
	if err != nil {
		t.Fatal(err)
	}
	var payload map[string]any
	if err := json.Unmarshal(stored, &payload); err != nil {
		t.Fatal(err)
	}
	state := payload["state"].(map[string]any)
	if state["status"] != "ready" || state["count"] != float64(2) || payload["keep"] != true {
		t.Fatalf("stored JSON = %#v", payload)
	}
}

func TestArtifactPatchBatchOperationFailureLeavesArtifactUnchanged(t *testing.T) {
	projectRoot := t.TempDir()
	path := "specs/001-runtime/workflow-state.md"
	original := "# State\n\n## Current\n\nold\n\n## Keep\n\nunchanged\n"
	writeArtifactTestFile(t, projectRoot, path, original)
	service := NewArtifactService(projectRoot)
	leaseID := prepareArtifactBatchLease(t, service, path)

	priorWrite := writeArtifactBatchFile
	writes := 0
	writeArtifactBatchFile = func(target string, content []byte, perm os.FileMode) error {
		writes++
		return atomicWriteFile(target, content, perm)
	}
	t.Cleanup(func() { writeArtifactBatchFile = priorWrite })

	result := service.PatchBatch(ArtifactPatchBatchRequest{
		LeaseID: leaseID,
		Operations: []ArtifactPatchBatchOperation{
			{Section: "Current", Content: "new"},
			{Section: "Missing", Content: "must fail"},
		},
	})

	if result.Status != "invalid" || writes != 0 {
		t.Fatalf("failed patch-batch = %#v, writes = %d", result, writes)
	}
	stored, err := os.ReadFile(filepath.Join(projectRoot, filepath.FromSlash(path)))
	if err != nil {
		t.Fatal(err)
	}
	if string(stored) != original {
		t.Fatalf("failed patch-batch changed artifact:\n%s", stored)
	}
}

func TestArtifactPatchBatchFinalValidationFailureLeavesArtifactUnchanged(t *testing.T) {
	projectRoot := t.TempDir()
	path := "specs/001-runtime/spec-contract.json"
	original := `{"status":"draft"}`
	writeArtifactTestFile(t, projectRoot, path, original)
	service := NewArtifactService(projectRoot)

	priorValidate := validateArtifactBatchContent
	priorWrite := writeArtifactBatchFile
	writes := 0
	validateArtifactBatchContent = func(string, []byte) error { return errors.New("injected final validation failure") }
	writeArtifactBatchFile = func(target string, content []byte, perm os.FileMode) error {
		writes++
		return atomicWriteFile(target, content, perm)
	}
	t.Cleanup(func() {
		validateArtifactBatchContent = priorValidate
		writeArtifactBatchFile = priorWrite
	})

	result := service.PatchBatch(ArtifactPatchBatchRequest{
		LeaseID:    prepareArtifactBatchLease(t, service, path),
		Operations: []ArtifactPatchBatchOperation{{JSONPointer: "/status", Value: "ready"}},
	})

	if result.Status != "invalid" || writes != 0 || !strings.Contains(fmt.Sprint(result.Blockers), "injected final validation failure") {
		t.Fatalf("validation failure result = %#v, writes = %d", result, writes)
	}
	stored, err := os.ReadFile(filepath.Join(projectRoot, filepath.FromSlash(path)))
	if err != nil {
		t.Fatal(err)
	}
	if string(stored) != original {
		t.Fatalf("validation failure changed artifact: %s", stored)
	}
}

func TestArtifactPatchBatchRejectsDuplicateAndConflictingTargetsWithoutWriting(t *testing.T) {
	tests := []struct {
		name       string
		path       string
		content    string
		operations []ArtifactPatchBatchOperation
	}{
		{
			name:    "duplicate markdown section",
			path:    "specs/001-runtime/workflow-state.md",
			content: "# State\n\n## Current\n\nold\n",
			operations: []ArtifactPatchBatchOperation{
				{Section: "Current", Content: "one"},
				{Section: "## current", Content: "two"},
			},
		},
		{
			name:    "duplicate frontmatter key",
			path:    "specs/001-runtime/workflow-state.md",
			content: "---\nstatus: draft\n---\n\n# State\n",
			operations: []ArtifactPatchBatchOperation{
				{Frontmatter: map[string]any{"status": "ready"}},
				{Frontmatter: map[string]any{"status": "done"}},
			},
		},
		{
			name:    "ancestor JSON pointer",
			path:    "specs/001-runtime/spec-contract.json",
			content: `{"state":{"status":"draft"}}`,
			operations: []ArtifactPatchBatchOperation{
				{JSONPointer: "/state", Value: map[string]any{"status": "ready"}},
				{JSONPointer: "/state/status", Value: "done"},
			},
		},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			projectRoot := t.TempDir()
			writeArtifactTestFile(t, projectRoot, test.path, test.content)
			service := NewArtifactService(projectRoot)
			result := service.PatchBatch(ArtifactPatchBatchRequest{
				LeaseID:    prepareArtifactBatchLease(t, service, test.path),
				Operations: test.operations,
			})
			if result.Status != "invalid" || !strings.Contains(strings.ToLower(fmt.Sprint(result.Blockers)), "conflict") {
				t.Fatalf("conflicting patch-batch = %#v", result)
			}
			stored, err := os.ReadFile(filepath.Join(projectRoot, filepath.FromSlash(test.path)))
			if err != nil {
				t.Fatal(err)
			}
			if string(stored) != test.content {
				t.Fatalf("conflicting patch-batch changed artifact: %s", stored)
			}
		})
	}
}

func TestArtifactPatchBatchBlocksStaleAndUsedLeases(t *testing.T) {
	t.Run("stale", func(t *testing.T) {
		projectRoot := t.TempDir()
		path := "specs/001-runtime/spec-contract.json"
		writeArtifactTestFile(t, projectRoot, path, `{"status":"draft"}`)
		service := NewArtifactService(projectRoot)
		leaseID := prepareArtifactBatchLease(t, service, path)
		mutated := []byte(`{"status":"external"}`)
		if err := os.WriteFile(filepath.Join(projectRoot, filepath.FromSlash(path)), mutated, 0o644); err != nil {
			t.Fatal(err)
		}

		result := service.PatchBatch(ArtifactPatchBatchRequest{
			LeaseID:    leaseID,
			Operations: []ArtifactPatchBatchOperation{{JSONPointer: "/status", Value: "ready"}},
		})
		if result.Status != "blocked" || !strings.Contains(fmt.Sprint(result.Blockers), "changed after lease preparation") {
			t.Fatalf("stale patch-batch = %#v", result)
		}
		stored, _ := os.ReadFile(filepath.Join(projectRoot, filepath.FromSlash(path)))
		if string(stored) != string(mutated) {
			t.Fatalf("stale patch-batch overwrote external change: %s", stored)
		}
	})

	t.Run("used", func(t *testing.T) {
		projectRoot := t.TempDir()
		path := "specs/001-runtime/spec-contract.json"
		writeArtifactTestFile(t, projectRoot, path, `{"status":"draft"}`)
		service := NewArtifactService(projectRoot)
		leaseID := prepareArtifactBatchLease(t, service, path)
		request := ArtifactPatchBatchRequest{
			LeaseID:    leaseID,
			Operations: []ArtifactPatchBatchOperation{{JSONPointer: "/status", Value: "ready"}},
		}
		if first := service.PatchBatch(request); first.Status != "ok" {
			t.Fatalf("first patch-batch = %#v", first)
		}
		second := service.PatchBatch(request)
		if second.Status != "blocked" || !strings.Contains(fmt.Sprint(second.Blockers), "already been claimed") {
			t.Fatalf("reused patch-batch lease = %#v", second)
		}
	})
}

func prepareArtifactBatchLease(t *testing.T, service *ArtifactService, path string) string {
	t.Helper()
	prepared := service.Prepare(ArtifactPrepareRequest{Path: path})
	if prepared.Status != "ok" {
		t.Fatalf("prepare %s = %#v", path, prepared)
	}
	leaseID, ok := prepared.Data["lease_id"].(string)
	if !ok || leaseID == "" {
		t.Fatalf("prepare lease id = %#v", prepared.Data["lease_id"])
	}
	return leaseID
}

func requireArtifactBatchItem(t *testing.T, result Envelope, index int) map[string]any {
	t.Helper()
	if index < 0 || index >= len(result.Items) {
		t.Fatalf("batch item index %d out of range: %#v", index, result.Items)
	}
	item, ok := result.Items[index].(map[string]any)
	if !ok {
		t.Fatalf("batch item %d = %#v, want object", index, result.Items[index])
	}
	return item
}
