package main

import (
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func doExternalFixture(t *testing.T) (string, string, PlaybookDefinition) {
	t.Helper()
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, "operation.py"), []byte("# a fixed project script\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "operation.ps1"), []byte("param([string]$Config)\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	file := filepath.Join(t.TempDir(), "private-fixture.xml")
	if err := os.WriteFile(file, []byte("<private>fake-confidential-config</private>"), 0o600); err != nil {
		t.Fatal(err)
	}
	t.Setenv("SPEC_KIT_TEST_EXTERNAL_CONFIG", file)
	definition := PlaybookDefinition{
		ExternalInputs: map[string]PlaybookExternalInput{"config": {Environment: "SPEC_KIT_TEST_EXTERNAL_CONFIG"}},
		Steps:          []PlaybookStep{{ID: "run", Cwd: ".", Argv: []string{"python", "operation.py", "--config", "{{external:config}}"}}},
		Checks:         []PlaybookCheck{{ID: "verify", Kind: "exit_code", Cwd: ".", Argv: []string{"python", "operation.py", "--check"}}},
	}
	return root, file, definition
}

func TestDoExternalSnapshotReturnsOnlySymbolicMetadata(t *testing.T) {
	root, privatePath, definition := doExternalFixture(t)
	before, err := os.ReadFile(privatePath)
	if err != nil {
		t.Fatal(err)
	}
	metadata, fingerprint, err := doExternalSnapshot(root, definition)
	if err != nil {
		t.Fatal(err)
	}
	if len(fingerprint) != 64 || metadata["config"].Environment != "SPEC_KIT_TEST_EXTERNAL_CONFIG" || metadata["config"].ContentSHA256 != fileContentSHA256(before) {
		t.Fatalf("wrong symbolic snapshot: %v", metadata)
	}
	encoded, _ := json.Marshal(map[string]any{"metadata": metadata, "fingerprint": fingerprint, "definition": definition})
	for _, forbidden := range []string{privatePath, filepath.Base(privatePath), "fake-confidential-config", string(before)} {
		if strings.Contains(string(encoded), forbidden) {
			t.Fatal("snapshot exposed a protected value")
		}
	}
	after, err := os.ReadFile(privatePath)
	if err != nil || string(before) != string(after) {
		t.Fatal("snapshot modified the external file")
	}
	entries, err := os.ReadDir(root)
	if err != nil || len(entries) != 2 {
		t.Fatal("read-only snapshot created project files")
	}
}

func TestDoExternalSnapshotBindsContentAndOpaquePathIdentity(t *testing.T) {
	root, original, definition := doExternalFixture(t)
	first, firstFingerprint, err := doExternalSnapshot(root, definition)
	if err != nil {
		t.Fatal(err)
	}
	copyPath := filepath.Join(t.TempDir(), "other-fixture.xml")
	content, _ := os.ReadFile(original)
	if err := os.WriteFile(copyPath, content, 0o600); err != nil {
		t.Fatal(err)
	}
	t.Setenv("SPEC_KIT_TEST_EXTERNAL_CONFIG", copyPath)
	second, secondFingerprint, err := doExternalSnapshot(root, definition)
	if err != nil || first["config"].ContentSHA256 != second["config"].ContentSHA256 || firstFingerprint == secondFingerprint {
		t.Fatal("same-content path retargeting did not invalidate the binding")
	}
	if err := os.WriteFile(copyPath, []byte("changed-fake-config"), 0o600); err != nil {
		t.Fatal(err)
	}
	third, thirdFingerprint, err := doExternalSnapshot(root, definition)
	if err != nil || second["config"].ContentSHA256 == third["config"].ContentSHA256 || secondFingerprint == thirdFingerprint {
		t.Fatal("external content drift did not invalidate the binding")
	}
}

func TestDoExternalSnapshotRejectsUnsafeBindingsWithSafeTypedDiagnostics(t *testing.T) {
	root, _, definition := doExternalFixture(t)
	inside := filepath.Join(root, "operation.py")
	for _, binding := range []string{"", "relative-secret.xml", t.TempDir(), filepath.Join(t.TempDir(), "missing-secret.xml"), inside} {
		t.Run("binding", func(t *testing.T) {
			t.Setenv("SPEC_KIT_TEST_EXTERNAL_CONFIG", binding)
			metadata, fingerprint, err := doExternalSnapshot(root, definition)
			var typed *doExternalInputError
			if !errors.As(err, &typed) || metadata != nil || fingerprint != "" || typed.Name != "config" || typed.Environment != "SPEC_KIT_TEST_EXTERNAL_CONFIG" || typed.Pointer != "/external_inputs/config/environment" {
				t.Fatalf("missing safe symbolic repair diagnosis: %v", err)
			}
			if binding != "" && strings.Contains(err.Error(), binding) {
				t.Fatal("diagnostic exposed an actual environment value")
			}
			var pathError *os.PathError
			if errors.As(err, &pathError) {
				t.Fatal("OS path errors escaped the protected boundary")
			}
		})
	}
}

func TestDoExternalDefinitionAcceptsOnlyCompleteFixedScriptDataTokens(t *testing.T) {
	root, _, definition := doExternalFixture(t)
	for _, argv := range [][]string{
		{"python", "operation.py", "--config", "{{external:config}}"},
		{"python", "-u", "operation.py", "{{external:config}}"},
		{"pwsh", "-NoProfile", "-File", "operation.ps1", "-Config", "{{external:config}}"},
	} {
		definition.Steps[0].Argv = argv
		if err := doExternalDefinition(root, definition); err != nil {
			t.Fatal(err)
		}
	}
	for _, argv := range [][]string{
		{"{{external:config}}"},
		{"python", "{{external:config}}"},
		{"python", "-c", "{{external:config}}"},
		{"pwsh", "-Command", "{{external:config}}"},
		{"python", "operation.py", "--config={{external:config}}"},
		{"python", "operation.py", "{{external:unknown}}"},
		{"python", "operation.py", "{{external:config}}/suffix"},
		{"tool", "{{external:config}}"},
	} {
		definition.Steps[0].Argv = argv
		if err := doExternalDefinition(root, definition); err == nil {
			t.Fatal("external binding acquired a command or expression position")
		}
	}
	definition.Steps[0].Argv = []string{"python", "operation.py", "{{external:config}}"}
	definition.Goal = "{{external:config}}"
	if err := doExternalDefinition(root, definition); err == nil {
		t.Fatal("protected binding was allowed in persisted descriptive fields")
	}
	definition.Goal = ""
	definition.Steps[0].Argv = []string{"python", "operation.py"}
	if err := doExternalDefinition(root, definition); err == nil {
		t.Fatal("unused declaration authorized an unrelated external read")
	}
}

func TestDoExternalDefinitionRejectsContentCaptureAndMalformedDeclarations(t *testing.T) {
	root, _, definition := doExternalFixture(t)
	for _, kind := range []string{"json", "junit", "observation"} {
		definition.Checks[0].Kind = kind
		if err := doExternalDefinition(root, definition); err == nil || !strings.Contains(err.Error(), "external_input_checks_must_not_capture_contents") {
			t.Fatalf("content-capturing check accepted: %v", err)
		}
	}
	definition.Checks[0].Kind = "file"
	definition.Steps[0].NativeAction = &PlaybookNativeAction{Kind: "file"}
	if err := doExternalDefinition(root, definition); err == nil {
		t.Fatal("native action could capture protected contents")
	}
	for _, raw := range []string{`{"environment":null}`, `{"environment":4}`, `{"environment":"SPEC_KIT_TEST_EXTERNAL_CONFIG","actual_path":"private"}`} {
		var input PlaybookExternalInput
		if err := json.Unmarshal([]byte(raw), &input); err == nil {
			t.Fatal("malformed external declaration accepted")
		}
	}
	definition.Steps[0].NativeAction = nil
	longName := "config" + strings.Repeat("x", 58)
	definition.ExternalInputs = map[string]PlaybookExternalInput{longName: {Environment: "SPEC_KIT_TEST_EXTERNAL_CONFIG"}}
	definition.Steps[0].Argv = []string{"python", "operation.py", "{{external:" + longName + "}}"}
	if err := doExternalDefinition(root, definition); err != nil {
		t.Fatalf("published 64-character external name was rejected: %v", err)
	}
	definition.ExternalInputs = map[string]PlaybookExternalInput{"config": {Environment: "SPEC_KIT_TEST_EXTERNAL_CONFIG"}}
	definition.Steps[0].Argv = []string{"python", "operation.py", "{{external:config}}"}
	definition.ExternalInputs["config"] = PlaybookExternalInput{Environment: "not an environment variable"}
	if err := doExternalDefinition(root, definition); err == nil {
		t.Fatal("unsafe environment declaration accepted")
	}
}
