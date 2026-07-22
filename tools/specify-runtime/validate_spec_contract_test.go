package main

import (
	"os"
	"path/filepath"
	"testing"
)

func TestValidateSpecReturnsUnifiedSuccessEnvelope(t *testing.T) {
	featureDir := t.TempDir()
	writeTestFile(t, featureDir, "spec.md", "# Feature Specification\n\n## Requirements\n\n- FR-001: The runtime validates a specification.\n")
	writeTestFile(t, featureDir, "spec-contract.json", `{"schema_version":1,"status":"ready"}`+"\n")

	result := ValidateSpec(SpecValidationRequest{
		FeatureDir: featureDir,
		Tier:       "light",
	})

	payload := decodeJSONValue(t, result)
	requireUnifiedEnvelope(t, payload)
	if payload["status"] != "ok" {
		t.Fatalf("validate spec status = %#v, want ok; payload=%#v", payload["status"], payload)
	}
	data := requireObject(t, payload, "data")
	if data["tier"] != "light" {
		t.Fatalf("validate spec data.tier = %#v, want light", data["tier"])
	}
	if blockers := payload["blockers"].([]any); len(blockers) != 0 {
		t.Fatalf("validate spec blockers = %#v, want empty", blockers)
	}
}

func TestValidateSpecReturnsRepairableBlockForMissingCoreArtifacts(t *testing.T) {
	featureDir := t.TempDir()

	result := ValidateSpec(SpecValidationRequest{
		FeatureDir: featureDir,
		Tier:       "light",
	})

	payload := decodeJSONValue(t, result)
	requireUnifiedEnvelope(t, payload)
	if payload["status"] != "blocked" {
		t.Fatalf("validate missing spec status = %#v, want blocked; payload=%#v", payload["status"], payload)
	}
	blockers := payload["blockers"].([]any)
	if len(blockers) == 0 {
		t.Fatalf("validate missing spec blockers = %#v, want actionable blocker", blockers)
	}
	if code := ExitCodeForStatus(payload["status"].(string)); code != 10 {
		t.Fatalf("validate missing spec exit code = %d, want 10", code)
	}
}

func writeTestFile(t *testing.T, root, relative, content string) {
	t.Helper()
	path := filepath.Join(root, relative)
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatalf("create parent for %s: %v", relative, err)
	}
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatalf("write %s: %v", relative, err)
	}
}
