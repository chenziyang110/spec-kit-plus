package config

import (
	"os"
	"path/filepath"
	"testing"
)

func writeConfig(t *testing.T, root string, content string) {
	t.Helper()
	specifyDir := filepath.Join(root, ".specify")
	if err := os.MkdirAll(specifyDir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(specifyDir, "config.json"), []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
}

func TestLoadDefaultsAutoCommitEnabled(t *testing.T) {
	t.Setenv("SPECIFY_PROJECT_COGNITION_AUTO_COMMIT", "")

	cfg, err := Load(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	if !cfg.ProjectCognition.AutoCommit {
		t.Fatal("auto commit should default to enabled")
	}
}

func TestLoadConfigDisablesAutoCommit(t *testing.T) {
	t.Setenv("SPECIFY_PROJECT_COGNITION_AUTO_COMMIT", "")
	root := t.TempDir()
	writeConfig(t, root, `{"project_cognition":{"auto_commit":false}}`)

	cfg, err := Load(root)
	if err != nil {
		t.Fatal(err)
	}
	if cfg.ProjectCognition.AutoCommit {
		t.Fatal("config should disable auto commit")
	}
}

func TestEnvironmentDisablesAutoCommit(t *testing.T) {
	t.Setenv("SPECIFY_PROJECT_COGNITION_AUTO_COMMIT", "no")
	root := t.TempDir()
	writeConfig(t, root, `{"project_cognition":{"auto_commit":true}}`)

	cfg, err := Load(root)
	if err != nil {
		t.Fatal(err)
	}
	if cfg.ProjectCognition.AutoCommit {
		t.Fatal("environment should disable auto commit")
	}
}

func TestLoadRejectsMalformedConfig(t *testing.T) {
	t.Setenv("SPECIFY_PROJECT_COGNITION_AUTO_COMMIT", "")
	root := t.TempDir()
	writeConfig(t, root, `{"project_cognition":`)

	if _, err := Load(root); err == nil {
		t.Fatal("expected malformed config error")
	}
}

func TestLoadProjectLearningValidatesLiteralDetectorPolicy(t *testing.T) {
	root := t.TempDir()
	writeConfig(t, root, `{
		"project_learning": {
			"detectors": {
				"secret_prefixes": ["acme_live_"],
				"sensitive_key_names": ["customer.secret"],
				"business_id_prefixes": ["CUST-"],
				"sensitive_terms": ["Project (Zephyr)"]
			},
			"deferred_review_days": 14
		}
	}`)

	policy, err := LoadProjectLearning(root)
	if err != nil {
		t.Fatal(err)
	}
	if policy.DeferredReviewDays != 14 || len(policy.Detectors.SecretPrefixes) != 1 {
		t.Fatalf("unexpected project learning policy: %#v", policy)
	}
	if policy.Detectors.SensitiveTerms[0] != "Project (Zephyr)" {
		t.Fatalf("detector literals must be preserved, got %#v", policy.Detectors.SensitiveTerms)
	}
}

func TestLoadProjectLearningDefaultsAndStrictValidation(t *testing.T) {
	policy, err := LoadProjectLearning(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	if policy.DeferredReviewDays != DefaultLearningDeferredReviewDays {
		t.Fatalf("unexpected default review days: %d", policy.DeferredReviewDays)
	}

	cases := map[string]string{
		"unknown field": `{"project_learning":{"detectors":{"secret_prefixes":[],"regexes":[".*"]}}}`,
		"wrong type":    `{"project_learning":{"detectors":{"secret_prefixes":"secret"}}}`,
		"empty item":    `{"project_learning":{"detectors":{"sensitive_terms":["   "]}}}`,
		"days low":      `{"project_learning":{"deferred_review_days":0}}`,
		"days high":     `{"project_learning":{"deferred_review_days":366}}`,
	}
	for name, raw := range cases {
		t.Run(name, func(t *testing.T) {
			root := t.TempDir()
			writeConfig(t, root, raw)
			if _, err := LoadProjectLearning(root); err == nil {
				t.Fatal("expected strict project learning policy validation error")
			}
		})
	}
}
