package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// Full-package regression at the worker-proof boundary. Unlike the standalone
// lexical tests this uses the real result reader, normalizer and proof gate.
func TestQuickScopeWorkerProofGate(t *testing.T) {
	tests := []struct {
		name         string
		files, scope []string
		wantError    string
	}{
		{"no-write changed files", []string{"src/main.go"}, nil, "outside packet write_scope"},
		{"traversal", []string{"src/../outside.go"}, []string{"src"}, "path must stay within the project"},
		{"blank result", []string{" "}, []string{"src"}, "path must be a project-relative path"},
		{"no-write evidence", []string{}, nil, ""},
		{"bounded write", []string{"src/main.go"}, []string{"src"}, ""},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			workspace := t.TempDir()
			resultDir := filepath.Join(workspace, "worker-results")
			if err := os.Mkdir(resultDir, 0o700); err != nil {
				t.Fatal(err)
			}
			raw, err := json.Marshal(map[string]any{
				"task_id": "Q1", "work_item_id": "Q1", "status": "success",
				"summary": "scope regression fixture", "changed_files": test.files,
				"validation_results": []map[string]string{{"command": "fixture verification", "status": "passed"}},
				"blockers":           []string{},
			})
			if err != nil {
				t.Fatal(err)
			}
			if err := os.WriteFile(filepath.Join(resultDir, "Q1.json"), raw, 0o600); err != nil {
				t.Fatal(err)
			}
			item := quickConfirmationItem{ID: "Q1", WriteScope: test.scope}
			row := quickWorkItemStatus{WorkItemID: "Q1", Status: "in_progress", RequiresWorker: true}
			doc := &quickConfirmationDoc{
				Decision:  quickConfirmationDecision{Items: []quickConfirmationItem{item}},
				Execution: quickConfirmationExecution{WorkItemStatus: []quickWorkItemStatus{row}},
			}
			proof, err := requireQuickWorkerAcceptProof(workspace, "fixture", "Q1", item, doc, row)
			if test.wantError != "" {
				if err == nil || proof != nil || !strings.Contains(err.Error(), test.wantError) {
					t.Fatalf("expected rejected worker proof containing %q; proof=%+v err=%v", test.wantError, proof, err)
				}
			} else if err != nil || proof == nil || proof.Mode != "worker" {
				t.Fatalf("valid worker result rejected: proof=%+v err=%v", proof, err)
			}
			if doc.Execution.WorkItemStatus[0].Status != "in_progress" {
				t.Fatal("proof validation mutated lifecycle")
			}
		})
	}
}
