package main

import (
	"bytes"
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
	nextArgv := payload["next_argv"].([]any)
	wantPrefix := []string{"specify-runtime", "validate", "spec", "--feature-dir"}
	if len(nextArgv) < len(wantPrefix) {
		t.Fatalf("validate missing spec next_argv = %#v, want executable rerun command", nextArgv)
	}
	for index, want := range wantPrefix {
		if nextArgv[index] != want {
			t.Fatalf("validate missing spec next_argv[%d] = %#v, want %q; argv=%#v", index, nextArgv[index], want, nextArgv)
		}
	}
}

func TestRunValidateSpecAcceptsFeatureDirAlias(t *testing.T) {
	featureDir := t.TempDir()
	writeTestFile(t, featureDir, "spec.md", "# Feature Specification\n\n## Requirements\n\n- FR-001: The runtime validates a specification.\n")
	writeTestFile(t, featureDir, "spec-contract.json", `{"schema_version":1,"status":"ready"}`+"\n")

	var out bytes.Buffer
	if code := runValidate([]string{"spec", "--feature-dir", featureDir, "--tier", "light", "--format", "json"}, &out); code != 0 {
		t.Fatalf("validate --feature-dir exit = %d stdout=%s", code, out.String())
	}
	payload := decodeJSONObject(t, out.Bytes())
	if payload["status"] != "ok" {
		t.Fatalf("validate --feature-dir status = %#v, want ok", payload["status"])
	}
	data := requireObject(t, payload, "data")
	if data["feature_dir"] != featureDir {
		t.Fatalf("validate --feature-dir data.feature_dir = %#v, want %q", data["feature_dir"], featureDir)
	}

	out.Reset()
	if code := runValidate([]string{"spec", "--dir", featureDir, "--tier", "light", "--format", "json"}, &out); code != 0 {
		t.Fatalf("validate --dir exit = %d stdout=%s", code, out.String())
	}
	legacy := decodeJSONObject(t, out.Bytes())
	if legacy["status"] != "ok" {
		t.Fatalf("validate --dir status = %#v, want ok", legacy["status"])
	}

	out.Reset()
	if code := runValidate([]string{"spec", "--feature-dir", featureDir, "--dir", featureDir + "-other", "--tier", "light"}, &out); code == 0 {
		t.Fatalf("conflicting flags should fail; stdout=%s", out.String())
	}
	conflict := decodeJSONObject(t, out.Bytes())
	if conflict["status"] != "usage-error" {
		t.Fatalf("conflicting flags status = %#v, want usage-error", conflict["status"])
	}
}

func TestValidateSpecStandardTierIncludesStructuredContractDiagnostics(t *testing.T) {
	featureDir := t.TempDir()
	writeTestFile(t, featureDir, "spec.md", "# Feature Specification\n\n## Requirements\n\n- FR-001: The runtime validates a specification.\n")
	writeTestFile(t, featureDir, "spec-contract.json", `{"schema_version":1,"status":"ready"}`+"\n")

	result := ValidateSpec(SpecValidationRequest{
		FeatureDir: featureDir,
		Tier:       "standard",
	})

	payload := decodeJSONValue(t, result)
	requireUnifiedEnvelope(t, payload)
	if payload["status"] != "blocked" {
		t.Fatalf("validate incomplete standard contract status = %#v, want blocked; payload=%#v", payload["status"], payload)
	}
	data := requireObject(t, payload, "data")
	failures, ok := data["failures"].([]any)
	if !ok || len(failures) == 0 {
		t.Fatalf("validate incomplete standard contract data.failures = %#v, want structured diagnostics", data["failures"])
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
