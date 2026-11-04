package main

import (
	"path/filepath"
	"strings"
	"testing"
)

func playbookArtifactPathFixture(t *testing.T, argv []string) (string, doStartInput) {
	t.Helper()
	root, input := doFixture(t)
	input.Definition.Operation = "package"
	input.Definition.Checks = []PlaybookCheck{{ID: "verify", Purpose: "verify the package artifact", Cwd: ".", Argv: argv, DependsOn: []string{"run"}, Required: true, ExpectedResult: "exit zero", Kind: "exit_code"}}
	input.Definition = playbookNormalizeDefinition(input.Definition)
	return root, input
}

func TestDoPreparePublicArtifactPathsAreNotCredentials(t *testing.T) {
	for _, test := range []struct {
		name string
		path string
	}{
		{"reported_windows_path", `D:\work\JZWinPassClear\output\r370\JZWinPassClearIns_001_200.exe`},
		{"relative_path", `output/r370/JZWinPassClearIns_001_200.exe`},
		{"forward_slash_drive", `D:/work/JZWinPassClear/output/r370/JZWinPassClearIns_001_200.exe`},
		{"different_product_version", `D:\artifacts\NorthStarDesktopInstaller_024_815_20261105.exe`},
	} {
		t.Run(test.name, func(t *testing.T) {
			// The public-path exception must stay scoped to argv handling;
			// changing the global Learning detector would hide this regression.
			if redactLearningText(test.path).text == test.path {
				t.Fatal("fixture no longer exercises the generic entropy detector")
			}
			root, input := playbookArtifactPathFixture(t, []string{"verify-tool", "--file", test.path})
			before := doFastTree(t, root)
			data, err := doPrepare(root, input)
			if err != nil {
				t.Fatalf("ordinary package artifact path rejected: %v", err)
			}
			prepared := data["start_input"].(doStartInput)
			if prepared.Definition.Checks[0].Argv[2] != test.path {
				t.Fatal("preparation changed the frozen artifact argument")
			}
			doPrepareValidationUnchanged(t, root, before)
		})
	}
}

func TestDoPrepareArtifactPathExceptionPreservesSafetyRules(t *testing.T) {
	const artifact = `D:\work\JZWinPassClear\output\r370\JZWinPassClearIns_001_200.exe`
	for _, test := range []struct {
		name   string
		argv   []string
		policy string
	}{
		{"github_credential_filename", []string{"verify-tool", "--file", `D:\artifacts\ghp_AbcDef1234567890InjectedCredential_001.exe`}, ""},
		{"api_credential_filename", []string{"verify-tool", "--file", `D:\artifacts\sk-AbcDef1234567890InjectedCredential_001.exe`}, ""},
		{"credential_assignment", []string{"verify-tool", "--file", `D:\artifacts\password=actualvalue.exe`}, ""},
		{"credential_flag", []string{"verify-tool", "--token", artifact}, ""},
		{"organization_sensitive_path", []string{"verify-tool", "--file", artifact}, `{"project_learning":{"detectors":{"sensitive_terms":["JZWinPassClear"]}}}`},
		{"organization_secret_prefix", []string{"verify-tool", "--file", artifact}, `{"project_learning":{"detectors":{"secret_prefixes":["JZWinPassClearIns_"]}}}`},
		{"bare_high_entropy_value", []string{"verify-tool", "--file", "xY92!mQ73+zV84=abCD56"}, ""},
		{"opaque_value_with_extension", []string{"verify-tool", "--file", `D:\artifacts\xY92mQ73zV84abCD56EfGH.exe`}, ""},
		{"sensitive_directory", []string{"verify-tool", "--file", `D:\xY92mQ73zV84abCD56EfGH\Installer_001.exe`}, ""},
		{"parent_traversal", []string{"verify-tool", "--file", `output/../JZWinPassClearIns_001_200.exe`}, ""},
		{"shell_snippet", []string{"pwsh", "-Command", `Get-Item 'D:\work\JZWinPassClear\output\r370\JZWinPassClearIns_001_200.exe'`}, ""},
	} {
		t.Run(test.name, func(t *testing.T) {
			root, input := playbookArtifactPathFixture(t, test.argv)
			if test.policy != "" {
				mustWriteLearningTest(t, filepath.Join(root, ".specify", "config.json"), test.policy)
			}
			before := doFastTree(t, root)
			_, err := doPrepare(root, input)
			if err == nil {
				t.Fatal("artifact-path exception bypassed a safety rule")
			}
			if strings.Contains(err.Error(), test.argv[len(test.argv)-1]) {
				t.Fatal("diagnostic exposed the rejected argument")
			}
			doPrepareValidationUnchanged(t, root, before)
		})
	}
}
