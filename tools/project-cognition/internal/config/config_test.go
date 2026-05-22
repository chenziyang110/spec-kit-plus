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
