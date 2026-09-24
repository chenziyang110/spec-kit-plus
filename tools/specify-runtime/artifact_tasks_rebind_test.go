package main

import (
	"os"
	"path/filepath"
	"testing"
	"time"
)

func TestArtifactTaskRebindHistoryCanBeListedAndInspectedWithoutWriteLease(t *testing.T) {
	for _, feature := range []string{".specify/features/001-runtime", "specs/001-runtime"} {
		t.Run(feature, func(t *testing.T) {
			root := t.TempDir()
			service := NewArtifactService(root)
			content := `{"version":1,"kind":"tasks.rebind","reason":"refresh pending coverage","workflow_revision":3,"previous_task_index_sha256":"before","task_index_sha256":"after","test_design_handoff_sha256":"handoff","preserved_task_ids":["T001"],"refreshed_ui_task_ids":[],"previous_files":{}}`
			path := feature + "/task-rebind-history/" + taskControlSHA256([]byte(content)) + ".json"
			writeArtifactTestFile(t, root, path, content)

			listed := service.ListArtifacts(ArtifactListRequest{PathPrefix: feature + "/", TypeID: "task-rebind-history"})
			items, ok := listed.Data["items"].([]map[string]any)
			if listed.Status != "ok" || !ok || len(items) != 1 {
				t.Fatalf("rebind history list = %#v", listed)
			}
			item := items[0]
			if item["canonical_path"] != path || item["owner"] != "specify-runtime tasks rebind" || item["schema"] != "json/task-rebind-history" || item["role"] != "canonical" {
				t.Fatalf("rebind history metadata = %#v", item)
			}
			if item["content"] != nil {
				t.Fatalf("rebind history list expanded immutable audit content: %#v", item)
			}

			shown := service.Show(ArtifactShowRequest{Path: path, JSONPointer: "/reason"})
			if shown.Status != "ok" || shown.Data["query_result"] != "refresh pending coverage" {
				t.Fatalf("targeted rebind history read = %#v", shown)
			}
			prepared := service.Prepare(ArtifactPrepareRequest{Path: path})
			if prepared.Status != "invalid" || prepared.Data["owner"] != "specify-runtime tasks rebind" || prepared.Data["lease_id"] != nil {
				t.Fatalf("rebind history must not receive a generic write lease: %#v", prepared)
			}
		})
	}
}

func TestArtifactTaskRebindHistoryRejectsExistingLeaseMutation(t *testing.T) {
	for _, operation := range []string{"submit", "patch", "delete"} {
		t.Run(operation, func(t *testing.T) {
			root := t.TempDir()
			service := NewArtifactService(root)
			content := `{"version":1,"kind":"tasks.rebind","reason":"retain immutable recovery evidence"}`
			digest := taskControlSHA256([]byte(content))
			path := "specs/001-runtime/task-rebind-history/" + digest + ".json"
			writeArtifactTestFile(t, root, path, content)

			// Simulate a pre-existing lease to verify mutation entrypoints enforce
			// ownership independently of Prepare's read-only admission check.
			lease := artifactLease{
				ID: "lease-rebind-" + operation, CanonicalPath: path,
				TargetExists: true, TargetSHA256: digest,
				CreatedAt: nowUTC().Format(time.RFC3339),
				ExpiresAt: nowUTC().Add(time.Hour).Format(time.RFC3339),
			}
			if err := service.writeLease(lease); err != nil {
				t.Fatal(err)
			}
			var result Envelope
			switch operation {
			case "submit":
				result = service.Submit(ArtifactSubmitRequest{LeaseID: lease.ID, Content: []byte(`{"kind":"rewritten"}`)})
			case "patch":
				result = service.Patch(ArtifactPatchRequest{LeaseID: lease.ID, JSONPointer: "/reason", Value: "rewritten"})
			case "delete":
				result = service.Delete(ArtifactDeleteRequest{LeaseID: lease.ID})
			}
			if result.Status != "invalid" || result.Data["owner"] != "specify-runtime tasks rebind" {
				t.Fatalf("rebind history %s must reject generic mutation: %#v", operation, result)
			}
			actual, err := os.ReadFile(filepath.Join(root, filepath.FromSlash(path)))
			if err != nil || string(actual) != content {
				t.Fatalf("rebind history %s altered immutable evidence: content=%q, err=%v", operation, actual, err)
			}
		})
	}
}
