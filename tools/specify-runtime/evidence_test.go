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

func TestEvidenceImportStoresImmutableObjectAndCompactReceipt(t *testing.T) {
	projectRoot := t.TempDir()
	externalRoot := t.TempDir()
	sourcePath := filepath.Join(externalRoot, "capture.log")
	if err := os.WriteFile(sourcePath, []byte("hello evidence\n"), 0o644); err != nil {
		t.Fatal(err)
	}

	code, payload := runEvidenceCommand(t, projectRoot, []string{
		"import",
		"--project-root", projectRoot,
		"--file", sourcePath,
		"--scope", "review",
		"--task-id", "T100",
		"--scenario-id", "SR-001",
		"--source", "manual-capture",
		"--provenance", "playwright",
	})
	if code != 0 {
		t.Fatalf("import code = %d payload=%#v", code, payload)
	}
	if payload["status"] != "ok" {
		t.Fatalf("import payload = %#v, want ok", payload)
	}
	data := requireEvidenceObject(t, payload, "data")
	if data["sha256"] == "" || data["evidence_id"] == "" {
		t.Fatalf("import receipt = %#v, want digest and id", data)
	}
	if data["path"] != nil {
		t.Fatalf("import receipt leaked full path: %#v", data)
	}
	recordPath := filepath.Join(projectRoot, filepath.FromSlash(evidenceTestString(data["record_ref"])))
	objectPath := filepath.Join(projectRoot, filepath.FromSlash(evidenceTestString(data["object_ref"])))
	record := readEvidenceJSONFile(t, recordPath)
	if record["sha256"] != data["sha256"] || record["scope"] != "review" {
		t.Fatalf("record = %#v, want imported metadata", record)
	}
	if evidenceTestString(record["source"]) != "manual-capture" || evidenceTestString(record["provenance"]) != "playwright" {
		t.Fatalf("record source metadata = %#v", record)
	}
	if evidenceTestString(record["external_source_path"]) != sourcePath {
		t.Fatalf("record external source path = %#v, want %q", record["external_source_path"], sourcePath)
	}
	if got := string(mustReadFile(t, objectPath)); got != "hello evidence\n" {
		t.Fatalf("object content = %q, want imported bytes", got)
	}
}

func TestEvidenceRegisterCreatesMetadataForExistingObjectOnlyInsideEvidenceRoot(t *testing.T) {
	projectRoot := t.TempDir()
	objectPath := filepath.Join(projectRoot, ".specify", "evidence", "objects", "sha256", strings.Repeat("a", 2), strings.Repeat("a", 64))
	if err := os.MkdirAll(filepath.Dir(objectPath), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(objectPath, []byte("registered object\n"), 0o444); err != nil {
		t.Fatal(err)
	}

	code, payload := runEvidenceCommand(t, projectRoot, []string{
		"register",
		"--project-root", projectRoot,
		"--object", ".specify/evidence/objects/sha256/aa/" + strings.Repeat("a", 64),
		"--scope", "debug",
		"--task-id", "T200",
		"--source", "result-handoff",
		"--provenance", "agent",
		"--mime", "text/plain",
	})
	if code != 0 {
		t.Fatalf("register code = %d payload=%#v", code, payload)
	}
	data := requireEvidenceObject(t, payload, "data")
	record := readEvidenceJSONFile(t, filepath.Join(projectRoot, filepath.FromSlash(evidenceTestString(data["record_ref"]))))
	if record["scope"] != "debug" || record["mime"] != "text/plain" {
		t.Fatalf("record = %#v, want registered metadata", record)
	}
	if evidenceTestString(record["object_ref"]) != ".specify/evidence/objects/sha256/aa/"+strings.Repeat("a", 64) {
		t.Fatalf("object ref = %#v", record["object_ref"])
	}
}

func TestEvidenceRegisterStoresInlineContentWithoutTemporaryFile(t *testing.T) {
	projectRoot := t.TempDir()
	content := `{"schema_version":"spec-kit-visual-comparison-v1","status":"pass"}`

	code, payload := runEvidenceCommand(t, projectRoot, []string{
		"register",
		"--project-root", projectRoot,
		"--content", content,
		"--scope", "review",
		"--scenario-id", "SR-visual",
		"--source", "visual-comparison",
		"--provenance", "agent",
		"--mime", "application/json",
	})
	if code != 0 {
		t.Fatalf("inline register code = %d payload=%#v", code, payload)
	}
	if payload["summary"] != "inline evidence registered" {
		t.Fatalf("inline register payload = %#v", payload)
	}
	data := requireEvidenceObject(t, payload, "data")
	record := readEvidenceJSONFile(t, filepath.Join(projectRoot, filepath.FromSlash(evidenceTestString(data["record_ref"]))))
	if record["external_source_path"] != nil {
		t.Fatalf("inline record leaked an external source path: %#v", record)
	}
	objectPath := filepath.Join(projectRoot, filepath.FromSlash(evidenceTestString(data["object_ref"])))
	if got := string(mustReadFile(t, objectPath)); got != content {
		t.Fatalf("inline object content = %q, want %q", got, content)
	}
}

func TestEvidenceRegisterRejectsObjectAndInlineContentTogether(t *testing.T) {
	projectRoot := t.TempDir()
	code, payload := runEvidenceCommand(t, projectRoot, []string{
		"register",
		"--project-root", projectRoot,
		"--object", ".specify/evidence/objects/sha256/aa/" + strings.Repeat("a", 64),
		"--content", `{}`,
		"--scope", "review",
	})
	if code != 2 {
		t.Fatalf("ambiguous register code = %d payload=%#v", code, payload)
	}
	if payload["status"] != "usage-error" {
		t.Fatalf("ambiguous register payload = %#v, want usage-error", payload)
	}
}

func TestEvidenceRegisterRejectsObjectOutsideEvidenceRoot(t *testing.T) {
	projectRoot := t.TempDir()
	outside := filepath.Join(projectRoot, "outside.bin")
	if err := os.WriteFile(outside, []byte("bad"), 0o644); err != nil {
		t.Fatal(err)
	}

	code, payload := runEvidenceCommand(t, projectRoot, []string{
		"register",
		"--project-root", projectRoot,
		"--object", "outside.bin",
		"--scope", "review",
	})
	if code != 2 {
		t.Fatalf("register outside code = %d payload=%#v", code, payload)
	}
	if payload["status"] != "usage-error" {
		t.Fatalf("register outside payload = %#v, want usage-error", payload)
	}
}

func TestEvidenceShowReturnsCompactSummaryAndOptionalFullRecord(t *testing.T) {
	projectRoot := t.TempDir()
	recordRef := importEvidenceFixture(t, projectRoot, "scenario-output.txt", "scenario output\n")

	code, payload := runEvidenceCommand(t, projectRoot, []string{
		"show",
		"--project-root", projectRoot,
		"--record", recordRef,
	})
	if code != 0 {
		t.Fatalf("show summary code = %d payload=%#v", code, payload)
	}
	data := requireEvidenceObject(t, payload, "data")
	if data["metadata"] != nil || data["source_path"] != nil {
		t.Fatalf("summary payload leaked full metadata = %#v", data)
	}

	code, payload = runEvidenceCommand(t, projectRoot, []string{
		"show",
		"--project-root", projectRoot,
		"--record", recordRef,
		"--view", "full",
	})
	if code != 0 {
		t.Fatalf("show full code = %d payload=%#v", code, payload)
	}
	full := requireEvidenceObject(t, payload, "data")
	metadata := requireEvidenceObject(t, full, "metadata")
	if metadata["sha256"] == "" || metadata["scope"] == "" {
		t.Fatalf("full metadata = %#v, want record", metadata)
	}
}

func TestEvidenceVerifyDetectsObjectTamper(t *testing.T) {
	projectRoot := t.TempDir()
	recordRef := importEvidenceFixture(t, projectRoot, "verify.txt", "original\n")
	record := readEvidenceJSONFile(t, filepath.Join(projectRoot, filepath.FromSlash(recordRef)))
	objectRef := evidenceTestString(record["object_ref"])
	objectPath := filepath.Join(projectRoot, filepath.FromSlash(objectRef))
	if err := os.Chmod(objectPath, 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(objectPath, []byte("tampered\n"), 0o644); err != nil {
		t.Fatal(err)
	}

	code, payload := runEvidenceCommand(t, projectRoot, []string{
		"verify",
		"--project-root", projectRoot,
		"--record", recordRef,
	})
	if code != 2 && code != 10 {
		t.Fatalf("verify tamper code = %d payload=%#v", code, payload)
	}
	if payload["status"] != "invalid" {
		t.Fatalf("verify tamper payload = %#v, want invalid", payload)
	}
}

func TestEvidenceAllocateReservesRecordPathInsideEvidenceRoot(t *testing.T) {
	projectRoot := t.TempDir()
	code, payload := runEvidenceCommand(t, projectRoot, []string{
		"allocate",
		"--project-root", projectRoot,
		"--scope", "review",
		"--task-id", "T300",
		"--source", "leader",
	})
	if code != 0 {
		t.Fatalf("allocate code = %d payload=%#v", code, payload)
	}
	data := requireEvidenceObject(t, payload, "data")
	recordRef := evidenceTestString(data["record_ref"])
	if !strings.HasPrefix(filepath.ToSlash(recordRef), ".specify/evidence/records/") {
		t.Fatalf("record_ref = %q, want evidence root", recordRef)
	}
	record := readEvidenceJSONFile(t, filepath.Join(projectRoot, filepath.FromSlash(recordRef)))
	if record["status"] != "allocated" || record["scope"] != "review" {
		t.Fatalf("allocated record = %#v", record)
	}
}

func runEvidenceCommand(t *testing.T, projectRoot string, args []string) (int, map[string]any) {
	t.Helper()
	var stdout bytes.Buffer
	code := runEvidence(args, &stdout)
	return code, decodeEvidenceJSONObject(t, stdout.Bytes())
}

func importEvidenceFixture(t *testing.T, projectRoot, name, content string) string {
	t.Helper()
	externalRoot := t.TempDir()
	sourcePath := filepath.Join(externalRoot, name)
	if err := os.WriteFile(sourcePath, []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
	code, payload := runEvidenceCommand(t, projectRoot, []string{
		"import",
		"--project-root", projectRoot,
		"--file", sourcePath,
		"--scope", "review",
		"--task-id", "T-fixture",
		"--source", "fixture",
	})
	if code != 0 {
		t.Fatalf("fixture import code = %d payload=%#v", code, payload)
	}
	return evidenceTestString(requireEvidenceObject(t, payload, "data")["record_ref"])
}

func mustReadFile(t *testing.T, path string) []byte {
	t.Helper()
	raw, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	return raw
}

func decodeEvidenceJSONObject(t *testing.T, raw []byte) map[string]any {
	t.Helper()
	var payload map[string]any
	if err := json.Unmarshal(raw, &payload); err != nil {
		t.Fatalf("decode JSON object: %v; output=%q", err, string(raw))
	}
	return payload
}

func requireEvidenceObject(t *testing.T, payload map[string]any, key string) map[string]any {
	t.Helper()
	value, ok := payload[key].(map[string]any)
	if !ok {
		t.Fatalf("%s = %#v, want object", key, payload[key])
	}
	return value
}

func readEvidenceJSONFile(t *testing.T, path string) map[string]any {
	t.Helper()
	raw, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	return decodeEvidenceJSONObject(t, raw)
}

func evidenceTestString(value any) string {
	return strings.TrimSpace(fmt.Sprint(value))
}

func TestEvidenceCompactReceiptJSONShape(t *testing.T) {
	projectRoot := t.TempDir()
	recordRef := importEvidenceFixture(t, projectRoot, "shape.txt", "shape\n")
	code, payload := runEvidenceCommand(t, projectRoot, []string{
		"show",
		"--project-root", projectRoot,
		"--record", recordRef,
	})
	if code != 0 {
		t.Fatalf("show code = %d payload=%#v", code, payload)
	}
	raw, err := json.Marshal(payload)
	if err != nil {
		t.Fatal(err)
	}
	if bytes.Contains(raw, []byte("external_source_path")) {
		t.Fatalf("summary JSON leaked external source path: %s", raw)
	}
}
