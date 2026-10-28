package main

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	runtimeconfig "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/config"
)

func TestPlaybookPublicContentAndScriptBinding(t *testing.T) {
	root, input := playbookFixture(t)
	script := "packets/BatchPackInstall.ps1"
	if err := os.MkdirAll(filepath.Join(root, "packets"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, script), []byte("Write-Output hello"), 0o644); err != nil {
		t.Fatal(err)
	}
	for _, test := range []struct {
		name   string
		argv   []string
		source bool
	}{
		{"public-argv-path", []string{"powershell.exe", "-File", script}, false},
		{"public-source-path", []string{"powershell.exe", "-Command", "Write-Output hello"}, true},
		{"ordinary-preference", []string{"powershell.exe", "-Command", "$ErrorActionPreference='Stop'"}, false},
	} {
		t.Run(test.name, func(t *testing.T) {
			definition := playbookNormalizeDefinition(input.Definition)
			definition.Steps[0].Argv = test.argv
			if test.source {
				definition.SourceFiles = []string{script}
			}
			if err := validatePlaybookDefinition(root, definition); err != nil {
				t.Fatal(err)
			}
		})
	}
	for _, argv := range [][]string{
		{"tool", "--token", "literal-value"},
		{"powershell.exe", "-Command", "$ErrorActionPreference='ghp_AbcDef1234567890InjectedCredential'"},
		{"tool", "xY92!mQ73+zV84=abCD56"},
	} {
		definition := playbookNormalizeDefinition(input.Definition)
		definition.Steps[0].Argv = argv
		err := validatePlaybookDefinition(root, definition)
		if err == nil || !strings.Contains(err.Error(), "/steps/0/argv/") {
			t.Fatalf("missing safe field diagnosis: %v", err)
		}
		if strings.Contains(err.Error(), argv[len(argv)-1]) {
			t.Fatal("diagnostic exposed the rejected value")
		}
	}

	definition := playbookNormalizeDefinition(input.Definition)
	definition.Steps[0].Argv = []string{"powershell.exe", "-File", "BatchPackInstall.ps1"}
	definition.Steps[0].Cwd = "packets"
	before, err := playbookSourceFingerprint(root, definition)
	if err != nil || before[script] != fileContentSHA256([]byte("Write-Output hello")) {
		t.Fatalf("actual cwd-relative script was not bound: %v %v", before, err)
	}
	input.Definition = definition
	session, err := doStart(root, input)
	if err != nil {
		t.Fatal(err)
	}
	session = doRecordFixture(t, root, session, "start-script", doRecordEvent{AttemptID: "script-1", TargetID: "run", Kind: "step", Event: "started"})
	if err := os.WriteFile(filepath.Join(root, script), []byte("Write-Output changed"), 0o644); err != nil {
		t.Fatal(err)
	}
	after, err := playbookSourceFingerprint(root, definition)
	if err != nil || before[script] == after[script] {
		t.Fatalf("changed actual script did not change fingerprint: %v", err)
	}
	zero := 0
	_, _, err = doApplyRecordEvent(root, session, doRecordEvent{AttemptID: "script-1", TargetID: "run", Kind: "step", Event: "completed", Status: "passed", EvidenceOrigin: "agent_tool_observation", ToolCallID: "unit-script-observation", Argv: definition.Steps[0].Argv, Cwd: "packets", StartedAt: doNow(), FinishedAt: doNow(), ExitCode: &zero}, map[string]bool{"script-1": true})
	if err == nil || !strings.Contains(err.Error(), "source changed during") {
		t.Fatalf("changed script accepted as a passing observation: %v", err)
	}
	definition.Steps[0].ScriptRef = script
	for _, argv := range [][]string{
		{"powershell.exe", "-Command", "& ([ScriptBlock]::Create($env:DO_BUILD))"},
		{"bash", "-c", `"$DO_BUILD"`},
		{"cmd", "/c", `"%DO_BUILD%"`},
		{"node", "-e", "eval(process.env.DO_CODE)"},
	} {
		definition.Steps[0].Argv = argv
		if err := validatePlaybookDefinition(root, definition); err == nil || !strings.Contains(err.Error(), "dynamic_script") {
			t.Fatalf("environment payload bypass accepted for %v: %v", argv[:2], err)
		}
	}
}

func TestPlaybookPublicTokensNeverSkipCredentialOrPolicyRules(t *testing.T) {
	policy := learningPolicyFromConfig(runtimeconfig.ProjectLearningConfig{Detectors: runtimeconfig.LearningDetectorsConfig{SensitiveTerms: []string{"BatchPackInstall.ps1"}, SecretPrefixes: []string{"company_private_"}}})
	for _, value := range []string{"BatchPackInstall.ps1", "company_private_VALUE", "ghp_AbcDef1234567890InjectedCredential", "Authorization: Bearer actualvalue", "password=actualvalue"} {
		redacted := redactLearningTextWithPolicyAndEntropyFilter(value, policy, func(string) bool { return true })
		if redacted.text == value {
			t.Fatal("an entropy exception bypassed a deterministic safety rule")
		}
	}
	for _, value := range []string{"BatchPackInstall.ps1", "$ErrorActionPreference="} {
		if redactLearningText(value).text == value {
			t.Fatal("the default Learning sanitizer changed behavior")
		}
	}
}

func TestPlaybookRecognizedScriptSources(t *testing.T) {
	root, input := playbookFixture(t)
	for _, name := range []string{"build.ps1", "build.py", "build.sh", "build.js", "verify.ps1"} {
		if err := os.WriteFile(filepath.Join(root, name), []byte(name), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	for _, argv := range [][]string{
		{"build.ps1"}, {"pwsh", "-File", ".\\build.ps1"},
		{"python", "-u", "build.py"}, {"bash", "build.sh"},
		{"node", "build.js"}, {"pwsh", "-Command", "& './build.ps1' -Mode release"},
	} {
		definition := playbookNormalizeDefinition(input.Definition)
		definition.Steps[0].Argv = argv
		definition.Checks[0].ScriptRef = "verify.ps1"
		fingerprint, err := playbookSourceFingerprint(root, definition)
		if err != nil || len(fingerprint) != 3 || fingerprint["verify.ps1"] == "" {
			t.Fatalf("script sources not bound for %v: %v %v", argv, fingerprint, err)
		}
	}
}
