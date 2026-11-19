package main

import (
	"encoding/json"
	"errors"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"testing"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runcontrol"
)

const doTypedScript = "packets/Build-WebInstaller.ps1"
const doTypedResult = "out/r376/NorthStarDesktopInstaller_001_200.exe"

func TestDoPrepareTypedPublicPaths(t *testing.T) {
	root, input := doCommandFixture(t)
	for _, filename := range []string{doTypedScript, doTypedResult} {
		if redactLearningText(filename).text == filename {
			t.Fatal("fixture no longer exercises the generic entropy detector")
		}
	}
	before := doFastTree(t, root)
	prepared, err := doPrepare(root, input)
	if err != nil {
		t.Fatalf("source_files rejected: %v", err)
	}
	canonical := prepared["start_input"].(doStartInput)
	if len(canonical.Definition.SourceFiles) != 1 || canonical.Definition.SourceFiles[0] != doTypedScript {
		t.Fatal("prepare did not bind the declared script as a source file")
	}
	input.Command.SourceWrites = []string{doTypedScript}
	input.WriteScope = []string{doTypedScript}
	prepared, err = doPrepare(root, input)
	if err != nil {
		t.Errorf("same script rejected in source_writes: %v", err)
	} else if prepared["start_input"].(doStartInput).Definition.Steps[0].SourceWrites[0] != doTypedScript {
		t.Fatal("prepare did not preserve the exact source write")
	}
	input.Command.SourceWrites = nil
	input.WriteScope = nil
	input.Command.Checks[0].ResultPath = doTypedResult
	prepared, err = doPrepare(root, input)
	if err != nil {
		t.Errorf("future result_path rejected: %v", err)
	} else if prepared["start_input"].(doStartInput).Definition.Checks[0].ResultPath != doTypedResult {
		t.Fatal("prepare did not preserve the exact result path")
	}
	doPrepareValidationUnchanged(t, root, before)
}

func TestDoPrepareTypedPathGuards(t *testing.T) {
	root, base := doCommandFixture(t)
	for _, tc := range []struct {
		name   string
		change func(*doStartInput)
		want   string
	}{
		{"source-scope", func(in *doStartInput) {
			in.Command.SourceWrites = []string{doTypedScript}
		}, "source_writes must remain inside the explicit write_scope: pointer=/steps/0/source_writes/0"},
		{"result-scope", func(in *doStartInput) {
			in.Command.Checks[0].ResultPath = "not-output/NorthStarDesktopInstaller_001_200.exe"
		}, "must be in an explicit output/write scope: pointer=/checks/0/result_path"},
		{"result-escape", func(in *doStartInput) {
			in.Command.Checks[0].ResultPath = "out/../../NorthStarDesktopInstaller_001_200.exe"
		}, "canonical_project_relative"},
		{"owner-boundary", func(in *doStartInput) {
			in.Command.SourceWrites = []string{".specify/project-cognition/Build-WebInstaller.ps1"}
			in.WriteScope = []string{".specify/project-cognition/Build-WebInstaller.ps1"}
		}, "source_write_cannot_target_workflow_state"},
		{"credential-shape", func(in *doStartInput) {
			in.Command.Checks[0].ResultPath = "out/ghp_SyntheticFixtureCredential1234567890.exe"
		}, "pointer=/checks/0/result_path rule=credential"},
		{"untyped-json", func(in *doStartInput) {
			in.Command.Checks[0] = doCommandCheck{
				Kind: "json", ResultPath: "out/report.json",
				ExpectedJSON: json.RawMessage(`{"result_path":"out/r376/NorthStarDesktopInstaller_001_200.exe"}`),
			}
		}, "pointer=/checks/0/expected_json/result_path rule=credential"},
	} {
		t.Run(tc.name, func(t *testing.T) {
			input, command := base, *base.Command
			command.Checks = append([]doCommandCheck(nil), command.Checks...)
			input.Command = &command
			tc.change(&input)
			if _, err := doPrepare(root, input); err == nil || !strings.Contains(err.Error(), tc.want) || strings.Contains(err.Error(), input.Command.Checks[0].ResultPath) {
				t.Fatalf("expected %q, got %v", tc.want, err)
			}
		})
	}
	if err := os.MkdirAll(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, ".specify/config.json"), []byte(`{"project_learning":{"detectors":{"sensitive_terms":["NorthStarDesktopInstaller"]}}}`), 0o644); err != nil {
		t.Fatal(err)
	}
	base.Command.Checks[0].ResultPath = doTypedResult
	if _, err := doPrepare(root, base); err == nil || !strings.Contains(err.Error(), "pointer=/checks/0/result_path rule=organization_sensitive") || strings.Contains(err.Error(), doTypedResult) {
		t.Fatalf("project-sensitive result path was not safely refused: %v", err)
	}
}

func TestDoPrepareTypedFutureResultRejectsLinkedParent(t *testing.T) {
	root, input := doCommandFixture(t)
	outside := t.TempDir()
	linked := filepath.Join(root, "out", "redirect")
	if err := os.MkdirAll(filepath.Dir(linked), 0o755); err != nil {
		t.Fatal(err)
	}
	if runtime.GOOS == "windows" {
		if output, err := exec.Command("cmd.exe", "/c", "mklink", "/J", linked, outside).CombinedOutput(); err != nil {
			t.Fatalf("create isolated junction: %v %s", err, output)
		}
	} else if err := os.Symlink(outside, linked); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Remove(linked) })
	input.Command.Checks[0].ResultPath = "out/redirect/future/NorthStarDesktopInstaller_001_200.exe"
	if _, err := doPrepare(root, input); err == nil || !strings.Contains(err.Error(), "playbook_path_crosses_link_or_project_boundary") {
		t.Fatalf("prepare accepted a missing artifact below a linked parent: %v", err)
	}
}

func TestDoPrepareTypedPathsPreserveProtectedPayloadAndOwnership(t *testing.T) {
	root, file, input := doProtectedFixture(t)
	input.Command.Checks[0].ResultPath = "out/" + doProtectedTestContent + ".exe"
	if _, err := doPrepare(root, input); err == nil || !strings.Contains(err.Error(), "protected_input_private_payload_forbidden") {
		t.Fatalf("literal protected contents were not refused: %v", err)
	} else {
		doProtectedNoLeak(t, file, err.Error())
	}
	input.Command.Checks[0].ResultPath = doTypedResult
	input.OutputScope = []string{doTypedResult}
	input.Command.SourceWrites = []string{doTypedScript}
	input.WriteScope = []string{doTypedScript}
	prepared, err := doPrepare(root, input)
	if err != nil {
		t.Fatal(err)
	}
	start := prepared["start_input"].(doStartInput)
	if _, err := doStart(root, start); err != nil {
		t.Fatal(err)
	}
	start.SessionID = "second"
	start.AgentID = "different-owner"
	if _, err := doStart(root, start); !errors.Is(err, runcontrol.ErrWorkIntentConflict) {
		t.Fatalf("exact typed paths were not protected by the existing Work claim: %v", err)
	}
	if _, err := os.Stat(filepath.Join(root, filepath.FromSlash(doSessionRef(start.SessionID)))); !os.IsNotExist(err) {
		t.Fatalf("Work conflict published another session: %v", err)
	}
}
