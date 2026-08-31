package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
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

func TestArtifactShowManyCLIConsumesPublishedSchemaFieldNames(t *testing.T) {
	projectRoot := t.TempDir()
	path := ".specify/features/001-batch/spec-contract.json"
	writeArtifactTestFile(t, projectRoot, path, `{"nested":{"value":"kept"},"rows":["first","second"]}`)
	input := `{"queries":[{"path":".specify/features/001-batch/spec-contract.json","json_pointer":"/nested/value"},{"feature":"001-batch","kind":"spec-contract","json_pointer":"/rows","limit":1}]}`
	var stdout, stderr bytes.Buffer
	code := Run([]string{"artifact", "show-many", "--project-root", projectRoot, "--input-json", input, "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("published show-many request failed: %d %s %s", code, stdout.String(), stderr.String())
	}
	items := requireObjectSlice(t, decodeJSONObject(t, stdout.Bytes()), "items")
	if len(items) != 2 || items[0]["status"] != "ok" || items[1]["status"] != "ok" {
		t.Fatalf("published selectors were not accepted: %#v", items)
	}
	if requireObject(t, items[0], "data")["query_result"] != "kept" {
		t.Fatalf("json_pointer was not applied: %#v", items[0])
	}
	if got := anyStringSlice(requireObject(t, items[1], "data")["query_result"]); len(got) != 1 || got[0] != "first" {
		t.Fatalf("feature/kind or limit was not applied: %#v", items[1])
	}
}

func TestArtifactPatchBatchStdinKeepsLargeUnicodePayloadAtomic(t *testing.T) {
	projectRoot := t.TempDir()
	path := ".planning/debug/large-stdin.md"
	writeArtifactTestFile(t, projectRoot, path, "---\nstatus: intake\n---\n\n# Debug\n\n## Evidence\n\nold\n")
	prepared := NewArtifactService(projectRoot).Prepare(ArtifactPrepareRequest{Path: path})
	if prepared.Status != "ok" {
		t.Fatalf("prepare = %#v", prepared)
	}
	lease := prepared.Data["lease_id"].(string)
	largeContent := strings.Repeat("x", 40*1024) + "\n中文审核 ✓\n"
	input, err := json.Marshal(map[string]any{"operations": []any{
		map[string]any{"section": "Evidence", "content": largeContent},
		map[string]any{"frontmatter": map[string]any{"status": "investigating"}},
	}})
	if err != nil {
		t.Fatal(err)
	}
	code, payload := runArtifactBatchCLIWithStdin(t, input,
		"artifact", "patch-batch", "--project-root", projectRoot, "--lease", lease, "--input-json", "-", "--format", "json",
	)
	if code != 0 {
		t.Fatalf("large stdin patch = %d: %#v", code, payload)
	}
	if requireObject(t, payload, "data")["operation_count"] != float64(2) {
		t.Fatalf("stdin batch was not one transaction: %#v", payload)
	}
	updated, err := os.ReadFile(filepath.Join(projectRoot, filepath.FromSlash(path)))
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Contains(updated, []byte(strings.TrimSpace(largeContent))) || !bytes.Contains(updated, []byte("investigating")) {
		t.Fatal("large payload or UTF-8 content was truncated or changed")
	}
	code, replay := runArtifactBatchCLIWithStdin(t, input,
		"artifact", "patch-batch", "--project-root", projectRoot, "--lease", lease, "--input-json", "-", "--format", "json",
	)
	if code == 0 {
		t.Fatalf("stdin reused a consumed lease: %#v", replay)
	}
	afterReplay, err := os.ReadFile(filepath.Join(projectRoot, filepath.FromSlash(path)))
	if err != nil || !bytes.Equal(updated, afterReplay) {
		t.Fatalf("rejected lease replay changed the artifact: %v", err)
	}
}

func runArtifactBatchCLIWithStdin(t *testing.T, input []byte, args ...string) (int, map[string]any) {
	t.Helper()
	reader, writer, err := os.Pipe()
	if err != nil {
		t.Fatal(err)
	}
	priorStdin := os.Stdin
	os.Stdin = reader
	defer func() { os.Stdin = priorStdin; _ = reader.Close(); _ = writer.Close() }()
	written := make(chan error, 1)
	go func() {
		_, err := writer.Write(input)
		if closeErr := writer.Close(); err == nil {
			err = closeErr
		}
		written <- err
	}()
	var stdout, stderr bytes.Buffer
	code := Run(args, &stdout, &stderr, "test")
	_ = reader.Close()
	if err := <-written; err != nil {
		t.Fatal(fmt.Errorf("write CLI stdin: %w", err))
	}
	return code, decodeJSONObject(t, stdout.Bytes())
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
