package main

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
)

func doCommandFixture(t *testing.T) (string, doStartInput) {
	t.Helper()
	root, input := doFixture(t)
	if err := os.MkdirAll(filepath.Join(root, "packets"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "packets/Build-WebInstaller.ps1"), []byte("param([string]$Revision)\nWrite-Output $Revision\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	input.Definition = PlaybookDefinition{}
	input.Goal = "Build the requested local test package"
	input.Command = &doCommandInput{Operation: "package", Argv: []string{"pwsh", "-NoProfile", "-File", "packets/Build-WebInstaller.ps1", "-Revision", "r376"}, Checks: []doCommandCheck{{Kind: "file", ResultPath: "out/installer.exe"}}}
	return root, input
}

func TestDoCommandPrepareGeneratesMinimalBoundSession(t *testing.T) {
	root, input := doCommandFixture(t)
	before := doFastTree(t, root)
	prepared, err := doPrepare(root, input)
	if err != nil {
		t.Fatal(err)
	}
	doPrepareValidationUnchanged(t, root, before)
	canonical := prepared["start_input"].(doStartInput)
	if canonical.Command != nil || canonical.Definition.Owner != "packets/Build-WebInstaller.ps1" || len(canonical.Definition.Parameters) != 0 || len(canonical.Definition.Checks) != 1 || canonical.Definition.Checks[0].Kind != "file" {
		t.Fatalf("shortcut did not supply correct method metadata: %+v", canonical)
	}
	if !reflect.DeepEqual(canonical.Definition.Steps[0].Argv, input.Command.Argv) {
		t.Fatal("shortcut rewrote the actual command")
	}
	fingerprint := prepared["source_fingerprint"]
	if fingerprint == nil {
		t.Fatal("script source was not bound")
	}
	session, err := doStart(root, canonical)
	if err != nil {
		t.Fatal(err)
	}
	next, err := doNext(root, session)
	if err != nil || len(next["ready"].([]map[string]any)) != 1 {
		t.Fatalf("minimal session did not reach native execution: %v %+v", err, next)
	}
	if _, err := os.Stat(filepath.Join(root, ".specify/playbooks")); !os.IsNotExist(err) {
		t.Fatal("method was saved before verified execution")
	}
}

func TestDoCommandPrepareRejectsUnverifiedOrAmbiguousInputs(t *testing.T) {
	for _, mode := range []string{"no-check", "mixed-definition", "direct-start"} {
		t.Run(mode, func(t *testing.T) {
			root, input := doCommandFixture(t)
			before := doFastTree(t, root)
			switch mode {
			case "no-check":
				input.Command.Checks = nil
			case "mixed-definition":
				input.Definition.Operation = "package"
			case "direct-start":
				if _, err := doStart(root, input); err == nil {
					t.Fatal("start accepted a noncanonical shortcut")
				}
				doPrepareValidationUnchanged(t, root, before)
				return
			}
			if _, err := doPrepare(root, input); err == nil {
				t.Fatal("invalid shortcut was accepted")
			}
			doPrepareValidationUnchanged(t, root, before)
		})
	}
}

func TestDoPrepareCollectsIndependentFieldErrorsWithoutSession(t *testing.T) {
	root, input := doFixture(t)
	input.Definition = playbookNormalizeDefinition(input.Definition)
	input.Definition.Parameters = map[string]PlaybookParameter{"revision": {Kind: "string", Required: false, Example: "r376"}}
	input.Definition.Steps[0].Cwd = "D:/work/project"
	raw, _ := json.Marshal(input)
	var output bytes.Buffer
	before := doFastTree(t, root)
	if runDo([]string{"prepare", "--input-json", string(raw), "--project-root", root, "--format", "json"}, &output) == 0 {
		t.Fatal("invalid definition passed")
	}
	var env Envelope
	if err := json.Unmarshal(output.Bytes(), &env); err != nil {
		t.Fatal(err)
	}
	issues := env.Data["validation_errors"].([]any)
	for _, expected := range []string{"/definition/parameters/revision/pattern", "/definition/parameters/revision/default", "/definition/steps/0/cwd"} {
		found := false
		for _, issue := range issues {
			if issue.(map[string]any)["instance_path"] == expected {
				found = true
			}
		}
		if !found {
			t.Fatalf("independent error missing %s: %s", expected, output.String())
		}
	}
	if len(env.ShowArgv) != 0 || strings.Contains(output.String(), "inspect the exact session") {
		t.Fatal("prepare fabricated session recovery")
	}
	doPrepareValidationUnchanged(t, root, before)
}
