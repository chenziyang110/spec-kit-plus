package config

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"unicode"
	"unicode/utf8"
)

const autoCommitEnv = "SPECIFY_PROJECT_COGNITION_AUTO_COMMIT"

const (
	DefaultLearningDeferredReviewDays = 7
	MaxLearningDetectorItems          = 64
	MaxLearningDetectorCharacters     = 128
)

type Config struct {
	ProjectCognition ProjectCognitionConfig `json:"project_cognition"`
}

type ProjectCognitionConfig struct {
	AutoCommit bool `json:"auto_commit"`
}

type ProjectLearningConfig struct {
	Detectors          LearningDetectorsConfig `json:"detectors,omitempty"`
	DeferredReviewDays int                     `json:"deferred_review_days,omitempty"`
}

type LearningDetectorsConfig struct {
	SecretPrefixes     []string `json:"secret_prefixes,omitempty"`
	SensitiveKeyNames  []string `json:"sensitive_key_names,omitempty"`
	BusinessIDPrefixes []string `json:"business_id_prefixes,omitempty"`
	SensitiveTerms     []string `json:"sensitive_terms,omitempty"`
}

type rawProjectLearningConfig struct {
	Detectors          json.RawMessage `json:"detectors"`
	DeferredReviewDays *int            `json:"deferred_review_days"`
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

// LoadProjectLearning reads and strictly validates only the project_learning
// subtree. Other top-level configuration remains owned by its respective
// runtime package and is deliberately ignored here.
func LoadProjectLearning(root string) (ProjectLearningConfig, error) {
	policy := defaultProjectLearningConfig()
	data, err := os.ReadFile(filepath.Join(root, ".specify", "config.json"))
	if err != nil {
		if os.IsNotExist(err) {
			return policy, nil
		}
		return ProjectLearningConfig{}, fmt.Errorf("project_learning config cannot be read")
	}
	var topLevel map[string]json.RawMessage
	if err := json.Unmarshal(data, &topLevel); err != nil {
		return ProjectLearningConfig{}, fmt.Errorf("project_learning config file is malformed")
	}
	raw, exists := topLevel["project_learning"]
	if !exists {
		return policy, nil
	}
	if bytes.Equal(bytes.TrimSpace(raw), []byte("null")) {
		return ProjectLearningConfig{}, fmt.Errorf("project_learning config must be an object")
	}
	decoder := json.NewDecoder(bytes.NewReader(raw))
	decoder.DisallowUnknownFields()
	var rawPolicy rawProjectLearningConfig
	if err := decoder.Decode(&rawPolicy); err != nil {
		return ProjectLearningConfig{}, fmt.Errorf("project_learning config has an invalid shape")
	}
	if decoder.Decode(&struct{}{}) != io.EOF {
		return ProjectLearningConfig{}, fmt.Errorf("project_learning config has trailing content")
	}
	configured := defaultProjectLearningConfig()
	var policyFields map[string]json.RawMessage
	if err := json.Unmarshal(raw, &policyFields); err != nil {
		return ProjectLearningConfig{}, fmt.Errorf("project_learning config has an invalid shape")
	}
	if value, ok := policyFields["deferred_review_days"]; ok && bytes.Equal(bytes.TrimSpace(value), []byte("null")) {
		return ProjectLearningConfig{}, fmt.Errorf("project_learning.deferred_review_days must be an integer")
	}
	if rawPolicy.DeferredReviewDays != nil {
		configured.DeferredReviewDays = *rawPolicy.DeferredReviewDays
	}
	if rawPolicy.Detectors != nil {
		if bytes.Equal(bytes.TrimSpace(rawPolicy.Detectors), []byte("null")) {
			return ProjectLearningConfig{}, fmt.Errorf("project_learning.detectors must be an object")
		}
		detectorDecoder := json.NewDecoder(bytes.NewReader(rawPolicy.Detectors))
		detectorDecoder.DisallowUnknownFields()
		if err := detectorDecoder.Decode(&configured.Detectors); err != nil {
			return ProjectLearningConfig{}, fmt.Errorf("project_learning.detectors has an invalid shape")
		}
		var detectorFields map[string]json.RawMessage
		if err := json.Unmarshal(rawPolicy.Detectors, &detectorFields); err != nil {
			return ProjectLearningConfig{}, fmt.Errorf("project_learning.detectors has an invalid shape")
		}
		for _, name := range []string{"secret_prefixes", "sensitive_key_names", "business_id_prefixes", "sensitive_terms"} {
			if value, ok := detectorFields[name]; ok && bytes.Equal(bytes.TrimSpace(value), []byte("null")) {
				return ProjectLearningConfig{}, fmt.Errorf("project_learning.detectors.%s must be an array", name)
			}
		}
	}
	if err := validateProjectLearningConfig(&configured); err != nil {
		return ProjectLearningConfig{}, err
	}
	return configured, nil
}

func defaultProjectLearningConfig() ProjectLearningConfig {
	return ProjectLearningConfig{DeferredReviewDays: DefaultLearningDeferredReviewDays}
}

func validateProjectLearningConfig(policy *ProjectLearningConfig) error {
	if policy.DeferredReviewDays < 1 || policy.DeferredReviewDays > 365 {
		return fmt.Errorf("project_learning.deferred_review_days must be between 1 and 365")
	}
	groups := []struct {
		name   string
		values *[]string
	}{
		{"secret_prefixes", &policy.Detectors.SecretPrefixes},
		{"sensitive_key_names", &policy.Detectors.SensitiveKeyNames},
		{"business_id_prefixes", &policy.Detectors.BusinessIDPrefixes},
		{"sensitive_terms", &policy.Detectors.SensitiveTerms},
	}
	for _, group := range groups {
		values := *group.values
		if len(values) > MaxLearningDetectorItems {
			return fmt.Errorf("project_learning.detectors.%s exceeds the item limit", group.name)
		}
		cleaned := make([]string, 0, len(values))
		seen := map[string]bool{}
		for index, value := range values {
			trimmed := strings.TrimSpace(value)
			length := utf8.RuneCountInString(trimmed)
			if length < 1 || length > MaxLearningDetectorCharacters {
				return fmt.Errorf("project_learning.detectors.%s item %d has invalid length", group.name, index)
			}
			for _, character := range trimmed {
				if unicode.IsControl(character) {
					return fmt.Errorf("project_learning.detectors.%s item %d contains a control character", group.name, index)
				}
			}
			key := strings.ToLower(trimmed)
			if seen[key] {
				continue
			}
			seen[key] = true
			cleaned = append(cleaned, trimmed)
		}
		*group.values = cleaned
	}
	return nil
}

func disablesAutoCommit(value string) bool {
	switch strings.ToLower(strings.TrimSpace(value)) {
	case "0", "false", "no":
		return true
	default:
		return false
	}
}
