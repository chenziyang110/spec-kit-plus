package config

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
)

const autoCommitEnv = "SPECIFY_PROJECT_COGNITION_AUTO_COMMIT"

type Config struct {
	ProjectCognition ProjectCognitionConfig `json:"project_cognition"`
}

type ProjectCognitionConfig struct {
	AutoCommit bool `json:"auto_commit"`
}

type rawConfig struct {
	ProjectCognition *rawProjectCognitionConfig `json:"project_cognition"`
}

type rawProjectCognitionConfig struct {
	AutoCommit *bool `json:"auto_commit"`
}

func Load(root string) (Config, error) {
	cfg := Config{
		ProjectCognition: ProjectCognitionConfig{
			AutoCommit: true,
		},
	}

	data, err := os.ReadFile(filepath.Join(root, ".specify", "config.json"))
	if err != nil {
		if !os.IsNotExist(err) {
			return Config{}, err
		}
	} else {
		var raw rawConfig
		if err := json.Unmarshal(data, &raw); err != nil {
			return Config{}, err
		}
		if raw.ProjectCognition != nil && raw.ProjectCognition.AutoCommit != nil {
			cfg.ProjectCognition.AutoCommit = *raw.ProjectCognition.AutoCommit
		}
	}

	if disablesAutoCommit(os.Getenv(autoCommitEnv)) {
		cfg.ProjectCognition.AutoCommit = false
	}

	return cfg, nil
}

func disablesAutoCommit(value string) bool {
	switch strings.ToLower(strings.TrimSpace(value)) {
	case "0", "false", "no":
		return true
	default:
		return false
	}
}
