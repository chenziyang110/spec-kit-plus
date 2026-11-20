package main

import (
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"runtime"
	"strings"
	"testing"
)

func TestDoPrepareIssue152BuildInputs(t *testing.T) {
	const script = "packets/BatchPackInstall.ps1"
	for _, test := range []struct {
		name  string
		argv  []string
		check bool
	}{
		{"existing_packaging_script", []string{"powershell.exe", "-NoProfile", "-File", script}, false},
		{"packaging_boolean", []string{"powershell.exe", "-NoProfile", "-File", script, "ReinstallQuotaDevelopmentTest=true"}, false},
		{"packaging_number", []string{"powershell.exe", "-NoProfile", "-File", script, "DevServer=1"}, false},
		{"msbuild_configuration", []string{`C:\BuildTools\MSBuild.exe`, "/p:Configuration=ReleaseJxly"}, false},
		{"msbuild_platform", []string{"msbuild", "/property:Platform=AnyCPU"}, false},
		{"msbuild_number", []string{"msbuild", "-p:ReinstallQuotaDevelopmentTest=1"}, false},
		{"msbuild_secret_binding", []string{"msbuild", "/p:ClientSecret=${BUILD_CLIENT_SECRET}"}, false},
		{"dotnet_configuration", []string{"dotnet", "build", "--configuration=ReleaseJxly"}, false},
		{"cmake_build_type", []string{"cmake", "-DCMAKE_BUILD_TYPE:STRING=ReleaseJxly"}, false},
		{"legacy_package_artifact", []string{"verify-tool", "--file", "packets/ReleaseQH_M32/x86/JZReNewMaster360Ly.exe"}, true},
		{"unicode_package_artifact", []string{"verify-tool", "--file", `packets\版本375\JZWinReNewLxIns_099_375_beta.exe`}, true},
		{"drive_root_artifact", []string{"verify-tool", "--file", `D:\JZWinReNewLxIns_099_375_beta.exe`}, true},
	} {
		t.Run(test.name, func(t *testing.T) {
			root, input := playbookArtifactPathFixture(t, []string{"verify-tool", "--version"})
			mustMkdirLearningTest(t, filepath.Join(root, ".specify"))
			mustWriteLearningTest(t, filepath.Join(root, filepath.FromSlash(script)), "exit 0\n")
			input.Definition.Owner = script
			if test.check {
				input.Definition.Checks[0].Argv = test.argv
			} else {
				input.Definition.Steps[0].Argv = test.argv
			}
			if strings.HasPrefix(test.name, "packaging") || test.name == "existing_packaging_script" {
				input.Definition.Goal = "Run " + script
				input.Definition.Steps[0].Purpose = "Run the existing " + script
				input.Definition.Checks[0].Purpose = "Verify results from BatchPackInstall.ps1"
			}
			before := doFastTree(t, root)
			data, err := doPrepare(root, input)
			if err != nil {
				t.Fatalf("ordinary build input rejected: %v", err)
			}
			prepared := data["start_input"].(doStartInput)
			actual := prepared.Definition.Steps[0].Argv
			if test.check {
				actual = prepared.Definition.Checks[0].Argv
			}
			if !reflect.DeepEqual(actual, test.argv) {
				t.Fatalf("prepare changed the argv: %q", actual)
			}
			doPrepareValidationUnchanged(t, root, before)
		})
	}
}

func TestDoPrepareIssue152BuildInputSafety(t *testing.T) {
	const secret = "xY92mQ73zV84abCD56EfGH"
	for _, test := range []struct {
		name   string
		argv   []string
		policy string
	}{
		{"build_secret_property", []string{"msbuild", "/p:ClientSecret=1"}, ""},
		{"build_compound_password", []string{"msbuild", "/p:PackagingPassword=true"}, ""},
		{"build_license_key", []string{"msbuild", "/p:ProductLicenseKey=1234"}, ""},
		{"cmake_secret_property", []string{"cmake", "-DClientSecret:STRING=false"}, ""},
		{"opaque_configuration", []string{"msbuild", "/p:Configuration=" + secret}, ""},
		{"ordinary_command_not_builder", []string{"verify-tool", "/p:Configuration=ReleaseJxly"}, ""},
		{"shell_snippet_not_build_data", []string{"powershell.exe", "-Command", "ReinstallQuotaDevelopmentTest=true"}, ""},
		{"shell_package_path_not_data", []string{"powershell.exe", "-Command", "packets/ReleaseQH_M32/x86/JZReNewMaster360Ly.exe"}, ""},
		{"secret_shaped_script_argument", []string{"powershell.exe", "-File", "packets/BatchPackInstall.ps1", "Authorization=true"}, ""},
		{"script_compound_password", []string{"powershell.exe", "-File", "packets/BatchPackInstall.ps1", "-FooPassword=1"}, ""},
		{"project_sensitive_configuration", []string{"msbuild", "/p:Configuration=ReleaseJxly"}, `{"project_learning":{"detectors":{"sensitive_terms":["ReleaseJxly"]}}}`},
		{"unicode_credential_artifact", []string{"verify-tool", "--file", "packets/版本375/ghp_AbcDef1234567890InjectedCredential_001.exe"}, ""},
	} {
		t.Run(test.name, func(t *testing.T) {
			root, input := playbookArtifactPathFixture(t, test.argv)
			mustMkdirLearningTest(t, filepath.Join(root, ".specify"))
			mustWriteLearningTest(t, filepath.Join(root, "packets", "BatchPackInstall.ps1"), "exit 0\n")
			if test.policy != "" {
				mustWriteLearningTest(t, filepath.Join(root, ".specify", "config.json"), test.policy)
			}
			_, err := doPrepare(root, input)
			if err == nil || !strings.Contains(err.Error(), "pointer=/checks/0/argv/") {
				t.Fatalf("wanted input rejection at the command argument, got %v", err)
			}
			if strings.Contains(err.Error(), secret) || strings.Contains(err.Error(), test.argv[len(test.argv)-1]) {
				t.Fatalf("diagnostic exposed the rejected input: %v", err)
			}
		})
	}
}

func TestIssue152PowerShellDataRequiresRegularProjectScript(t *testing.T) {
	root := t.TempDir()
	mustMkdirLearningTest(t, filepath.Join(root, ".specify"))
	mustMkdirLearningTest(t, filepath.Join(root, "directory.ps1"))
	outside := t.TempDir()
	mustWriteLearningTest(t, filepath.Join(outside, "build.ps1"), "exit 0\n")
	linked := filepath.Join(root, "redirect")
	if runtime.GOOS == "windows" {
		if output, err := exec.Command("cmd.exe", "/d", "/c", "mklink", "/J", linked, outside).CombinedOutput(); err != nil {
			t.Fatalf("create isolated junction: %v %s", err, output)
		}
	} else if err := os.Symlink(outside, linked); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Remove(linked) })
	for _, script := range []string{"missing.ps1", "directory.ps1", "redirect/build.ps1"} {
		if index := playbookPowerShellFileScriptIndex(root, ".", []string{"pwsh", "-File", script, "ReinstallQuotaDevelopmentTest=true"}); index != -1 {
			t.Fatalf("nonregular or unsafe script qualified for build data: %q", script)
		}
	}
}

func TestLearningCaptureIssue152PreservesScriptName(t *testing.T) {
	root := t.TempDir()
	mustMkdirLearningTest(t, filepath.Join(root, ".specify"))
	const script = "packets/BatchPackInstall.ps1"
	const ref = "debug.packaging-script"
	const token = "ghp_1234567890abcdef"
	const opaque = "xY92mQ73zV84abCD56EfGH.ps1"
	capture := runLearningEnvelopeTest(t, []string{
		"capture", "--project-root", root, "--command", "debug", "--type", "tooling_trap",
		"--summary", "Run " + script, "--evidence", "Verified " + script + "; omit " + token + " and " + opaque,
		"--action", "Run BatchPackInstall.ps1 in the workspace", "--recurrence-key", ref, "--format", "json",
	})
	if capture.Status != "ok" {
		t.Fatalf("capture failed: %#v", capture)
	}
	entry := capture.Data["entry"].(map[string]any)
	if !strings.Contains(stringFromAny(entry["summary"]), script) ||
		!strings.Contains(stringFromAny(entry["evidence"]), script) ||
		!strings.Contains(stringFromAny(entry["recommended_action"]), "BatchPackInstall.ps1") {
		t.Fatalf("capture erased the public script name: %#v", entry)
	}
	detailPath := filepath.Join(root, filepath.FromSlash(stringFromAny(capture.Data["detail_path"])))
	detail, err := os.ReadFile(detailPath)
	if err != nil || !strings.Contains(string(detail), script) || strings.Contains(string(detail), token) || strings.Contains(string(detail), opaque) {
		t.Fatalf("unexpected persisted detail: %v %s", err, detail)
	}
	show := runLearningEnvelopeTest(t, []string{"show", "--project-root", root, "--ref", ref, "--format", "json"})
	guide := show.Data["guidance"].(map[string]any)
	if show.Status != "ok" || !strings.Contains(stringFromAny(guide["action"]), "BatchPackInstall.ps1") {
		t.Fatalf("show erased the captured name: %#v", show)
	}
	assertLearningJSONOmits(t, capture, []string{token, opaque})
	assertLearningJSONOmits(t, show, []string{token, opaque})

	mustWriteLearningTest(t, filepath.Join(root, ".specify", "config.json"), `{"project_learning":{"detectors":{"sensitive_terms":["BatchPackInstall.ps1"]}}}`)
	protected := runLearningEnvelopeTest(t, []string{"show", "--project-root", root, "--ref", ref, "--format", "json"})
	if protected.Status != "ok" {
		t.Fatalf("show with project policy failed: %#v", protected)
	}
	assertLearningJSONOmits(t, protected, []string{"BatchPackInstall.ps1"})
}
