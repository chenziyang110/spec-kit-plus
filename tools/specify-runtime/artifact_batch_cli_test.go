package main

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

func TestArtifactShowManyCLIReadsMultipleTargetedQueries(t *testing.T) {
	projectRoot := t.TempDir()
	writeArtifactTestFile(t, projectRoot, "specs/001-batch/spec.md", "# Spec\n\n## Requirements\n\n- FR-001\n")
	writeArtifactTestFile(t, projectRoot, "specs/001-batch/plan.md", "# Plan\n\n## Summary\n\nReady.\n")
	input := map[string]any{"queries": []any{
		map[string]any{"path": "specs/001-batch/spec.md", "section": "Requirements", "limit": 10},
		map[string]any{"path": "specs/001-batch/plan.md", "view": "summary"},
	}}
	raw, err := json.Marshal(input)
	if err != nil {
		t.Fatal(err)
	}
	var stdout, stderr bytes.Buffer
	code := Run([]string{"artifact", "show-many", "--project-root", projectRoot, "--input-json", string(raw), "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("show-many exit=%d stdout=%s stderr=%s", code, stdout.String(), stderr.String())
	}
	payload := decodeJSONObject(t, stdout.Bytes())
	if payload["status"] != "ok" || len(payload["items"].([]any)) != 2 {
		t.Fatalf("show-many payload = %#v", payload)
	}
}

func TestArtifactPatchBatchCLIAppliesOneLeasedTransaction(t *testing.T) {
	projectRoot := t.TempDir()
	relativePath := ".planning/debug/cli-batch.md"
	writeArtifactTestFile(t, projectRoot, relativePath, "---\nstatus: intake\n---\n\n# Debug\n\n## Current Focus\n\nold\n\n## Evidence\n\nnone\n")
	service := NewArtifactService(projectRoot)
	prepared := service.Prepare(ArtifactPrepareRequest{Path: relativePath})
	leaseID := prepared.Data["lease_id"].(string)
	input := map[string]any{"operations": []any{
		map[string]any{"section": "Current Focus", "content": "next"},
		map[string]any{"section": "Evidence", "content": "- E-001"},
		map[string]any{"frontmatter": map[string]any{"status": "investigating"}},
	}}
	raw, err := json.Marshal(input)
	if err != nil {
		t.Fatal(err)
	}
	var stdout, stderr bytes.Buffer
	code := Run([]string{"artifact", "patch-batch", "--project-root", projectRoot, "--lease", leaseID, "--input-json", string(raw), "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("patch-batch exit=%d stdout=%s stderr=%s", code, stdout.String(), stderr.String())
	}
	payload := decodeJSONObject(t, stdout.Bytes())
	data := requireObject(t, payload, "data")
	if data["operation_count"] != float64(3) || len(data["after_sha256"].(string)) != 64 {
		t.Fatalf("patch-batch data = %#v", data)
	}
	updated, err := os.ReadFile(filepath.Join(projectRoot, filepath.FromSlash(relativePath)))
	if err != nil {
		t.Fatal(err)
	}
	for _, expected := range []string{"status: \"investigating\"", "next", "- E-001"} {
		if !bytes.Contains(updated, []byte(expected)) {
			t.Fatalf("patched artifact missing %q: %s", expected, updated)
		}
	}
}

func TestArtifactBatchCLIRejectsUnknownInputFields(t *testing.T) {
	projectRoot := t.TempDir()
	for _, args := range [][]string{
		{"artifact", "show-many", "--project-root", projectRoot, "--input-json", `{"queries":[],"legacy":true}`, "--format", "json"},
		{"artifact", "patch-batch", "--project-root", projectRoot, "--lease", "lease", "--input-json", `{"operations":[],"legacy":true}`, "--format", "json"},
	} {
		var stdout, stderr bytes.Buffer
		code := Run(args, &stdout, &stderr, "test")
		if code != 2 {
			t.Fatalf("%v exit=%d stdout=%s stderr=%s", args, code, stdout.String(), stderr.String())
		}
		payload := decodeJSONObject(t, stdout.Bytes())
		if payload["status"] != "usage-error" {
			t.Fatalf("%v payload=%#v, want usage-error", args, payload)
		}
	}
}
