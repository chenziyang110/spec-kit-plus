package main

import (
	"bytes"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestArtifactSubmitAcceptsLargeProjectFileContent(t *testing.T) {
	projectRoot := t.TempDir()
	path := ".specify/design/changes/UD-0042/references.md"
	content := "# References\n\n" + strings.Repeat("runtime-owned handoff evidence\n", 3000)
	inputPath := filepath.Join(projectRoot, ".specify", "runtime", "inputs", "references.md")
	if err := os.MkdirAll(filepath.Dir(inputPath), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(inputPath, []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
	service := NewArtifactService(projectRoot)
	lease := service.Prepare(ArtifactPrepareRequest{Path: path})
	leaseID, _ := lease.Data["lease_id"].(string)
	if lease.Status != "ok" || leaseID == "" {
		t.Fatalf("prepare submit lease: %#v", lease)
	}

	var stdout, stderr bytes.Buffer
	exit := Run([]string{
		"artifact", "submit",
		"--project-root", projectRoot,
		"--lease", leaseID,
		"--content", "@.specify/runtime/inputs/references.md",
		"--format", "json",
	}, &stdout, &stderr, "test")
	if exit != 0 {
		t.Fatalf("file-backed submit exit=%d stdout=%s stderr=%s", exit, stdout.String(), stderr.String())
	}
	stored, err := os.ReadFile(filepath.Join(projectRoot, filepath.FromSlash(path)))
	if err != nil {
		t.Fatal(err)
	}
	if string(stored) != content {
		t.Fatal("artifact submit stored the @path token instead of the referenced content")
	}
}

func TestEvidenceRegisterAcceptsLargeProjectFileContent(t *testing.T) {
	projectRoot := t.TempDir()
	content := "# Evidence\n\n" + strings.Repeat("bounded runtime diagnostics\n", 3000)
	inputPath := filepath.Join(projectRoot, ".specify", "runtime", "inputs", "evidence.md")
	if err := os.MkdirAll(filepath.Dir(inputPath), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(inputPath, []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}

	exit, payload := runEvidenceCommand(t, projectRoot, []string{
		"register",
		"--project-root", projectRoot,
		"--content", "@.specify/runtime/inputs/evidence.md",
		"--scope", "review",
		"--source", "runtime-diagnostics",
		"--provenance", "agent",
		"--mime", "text/markdown",
	})
	if exit != 0 {
		t.Fatalf("file-backed evidence register exit=%d payload=%#v", exit, payload)
	}
	data := requireEvidenceObject(t, payload, "data")
	objectPath := filepath.Join(projectRoot, filepath.FromSlash(evidenceTestString(data["object_ref"])))
	if got := string(mustReadFile(t, objectPath)); got != content {
		t.Fatal("evidence register stored the @path token instead of the referenced content")
	}
}

func TestImplementResultMergeReadsFileBackedResultJSON(t *testing.T) {
	projectRoot := t.TempDir()
	inputPath := filepath.Join(projectRoot, ".specify", "runtime", "inputs", "worker-result.json")
	if err := os.MkdirAll(filepath.Dir(inputPath), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(inputPath, []byte(`{"task_id":"T001","status":"success"}`), 0o644); err != nil {
		t.Fatal(err)
	}

	payload, err := readImplementTaskResult(
		[]string{"--result-json", "@.specify/runtime/inputs/worker-result.json"},
		projectRoot,
	)
	if err != nil {
		t.Fatal(err)
	}
	if payload["task_id"] != "T001" || payload["status"] != "success" {
		t.Fatalf("file-backed implement result = %#v", payload)
	}
}

func TestResolveTextInputBytesEscapesLiteralAtPrefix(t *testing.T) {
	root := t.TempDir()
	raw, err := resolveTextInputBytes("@@operator mention", root, "artifact submit", "--content")
	if err != nil {
		t.Fatal(err)
	}
	if string(raw) != "@operator mention" {
		t.Fatalf("escaped literal content = %q", raw)
	}
}

func TestResolveTextInputBytesKeepsWhitespacePrefixedAtLiteral(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, "notes.md"), []byte("unexpected file content"), 0o644); err != nil {
		t.Fatal(err)
	}
	raw, err := resolveTextInputBytes("  @notes.md", root, "artifact submit", "--content")
	if err != nil {
		t.Fatal(err)
	}
	if string(raw) != "  @notes.md" {
		t.Fatalf("whitespace-prefixed literal = %q", raw)
	}
}

func TestResolveTextInputBytesRejectsOversizedEscapedLiteral(t *testing.T) {
	root := t.TempDir()
	_, err := resolveTextInputBytes("@@"+strings.Repeat("x", maxAgentJSONInputBytes+1), root, "artifact submit", "--content")
	if err == nil || !strings.Contains(err.Error(), "exceeds") {
		t.Fatalf("oversized escaped literal error = %v", err)
	}
}
