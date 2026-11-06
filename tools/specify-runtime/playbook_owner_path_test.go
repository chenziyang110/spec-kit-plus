package main

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func playbookOwnerScriptFixture(t *testing.T, owner string) (string, doStartInput) {
	t.Helper()
	root, input := doFixture(t)
	input.Definition.Owner = owner
	filename := filepath.Join(root, filepath.FromSlash(owner))
	if err := os.MkdirAll(filepath.Dir(filename), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filename, []byte("Write-Output 'fixture'\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	return root, input
}

func TestDoPrepareRecognizesLiveScriptOwnerPath(t *testing.T) {
	const owner = "packets/Build-WebInstaller.ps1"
	root, input := playbookOwnerScriptFixture(t, owner)
	if redactLearningText(owner).text == owner {
		t.Fatal("fixture no longer exercises the unchanged generic entropy detector")
	}
	before := doFastTree(t, root)
	if _, err := doPrepare(root, input); err != nil {
		t.Fatalf("public live script owner rejected: %v", err)
	}
	doPrepareValidationUnchanged(t, root, before)
	if err := os.Remove(filepath.Join(root, filepath.FromSlash(owner))); err != nil {
		t.Fatal(err)
	}
	if _, err := doPrepare(root, input); err == nil {
		t.Fatal("missing owner script retained a live-path entropy exception")
	}
}

func TestDoPrepareScriptOwnerPreservesCredentialAndPolicyRules(t *testing.T) {
	for _, test := range []struct {
		name   string
		owner  string
		policy string
	}{
		{"credential", "packets/ghp_AbcDef1234567890InjectedCredential.ps1", ""},
		{"sensitive_term", "packets/Build-WebInstaller.ps1", `{"project_learning":{"detectors":{"sensitive_terms":["Build-WebInstaller"]}}}`},
		{"secret_prefix", "packets/Build-WebInstaller.ps1", `{"project_learning":{"detectors":{"secret_prefixes":["Build-Web"]}}}`},
	} {
		t.Run(test.name, func(t *testing.T) {
			root, input := playbookOwnerScriptFixture(t, test.owner)
			if test.policy != "" {
				mustWriteLearningTest(t, filepath.Join(root, ".specify", "config.json"), test.policy)
			}
			_, err := doPrepare(root, input)
			if err == nil || !strings.Contains(err.Error(), "pointer=/owner") {
				t.Fatalf("owner path bypassed credential/policy validation: %v", err)
			}
			if strings.Contains(err.Error(), test.owner) {
				t.Fatal("owner rejection exposed the input value")
			}
		})
	}
}

func TestPlaybookActionErrorsKeepExactFieldPointers(t *testing.T) {
	for _, test := range []struct {
		name   string
		mutate func(*PlaybookDefinition)
		want   string
	}{
		{"step_cwd", func(def *PlaybookDefinition) { def.Steps[0].Cwd = "../outside" }, "pointer=/steps/0/cwd"},
		{"check_cwd", func(def *PlaybookDefinition) { def.Checks[0].Cwd = "../outside" }, "pointer=/checks/0/cwd"},
		{"credential_argv", func(def *PlaybookDefinition) { def.Steps[0].Argv = []string{"tool", "--token", "literal-value"} }, "pointer=/steps/0/argv/1"},
	} {
		t.Run(test.name, func(t *testing.T) {
			root, input := doFixture(t)
			test.mutate(&input.Definition)
			_, err := doPrepare(root, input)
			if err == nil || !strings.Contains(err.Error(), test.want) {
				t.Fatalf("missing exact action-field pointer %s: %v", test.want, err)
			}
			if strings.Count(err.Error(), "pointer=") != 1 {
				t.Fatalf("action error contains competing pointers: %v", err)
			}
		})
	}
}
