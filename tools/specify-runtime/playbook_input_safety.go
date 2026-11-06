package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path"
	"regexp"
	"sort"
	"strconv"
	"strings"
)

var playbookSecretField = regexp.MustCompile(`(?i)^(token|password|passwd|secret|api[-_]?key|access[-_]?token|authorization|client[-_]?secret)$`)
var playbookEnvironmentBinding = regexp.MustCompile(`^\$\{[A-Z_][A-Z0-9_]*\}$`)
var playbookPublicPathToken = regexp.MustCompile(`^[A-Za-z0-9._/-]+$`)
var playbookPowerShellPreference = regexp.MustCompile(`(?i)^\$(?:ErrorAction|Progress|Warning|Information|Verbose|Debug|Confirm|WhatIf)Preference=?$`)
var playbookPublicArtifactPath = regexp.MustCompile(`(?i)^(?:[a-z]:)?(?:[\\/]{1,2})?(?:[a-z0-9._-]+[\\/])*([a-z][a-z0-9._-]*[._-][0-9]+(?:[._-][a-z0-9]+)*\.(?:exe|dll|msi|msix|msixbundle|zip|7z|cab|iso|wim|esd|tar|gz|bz2|xz))$`)

// Inspect field values rather than JSON punctuation. Only the entropy fallback
// gets syntax-aware exceptions; credentials and project policy always run first.
func validatePlaybookSensitiveContent(root string, definition PlaybookDefinition) error {
	policy, _, err := (learningService{projectRoot: root}).loadLearningPolicy(true)
	if err != nil {
		return err
	}
	raw, err := json.Marshal(definition)
	if err != nil {
		return err
	}
	var decoded any
	if err := json.Unmarshal(raw, &decoded); err != nil {
		return err
	}
	argvPublicTokens := map[string]map[string]bool{}
	bindPublicTokens := func(pointer, cwd string, argv []string) {
		sources, err := playbookActionScriptSources(root, cwd, argv)
		if err != nil {
			return
		}
		tokens := map[string]bool{}
		for _, source := range sources {
			if playbookPublicPathToken.MatchString(source) {
				for _, part := range strings.Split(source, "/") {
					tokens[part] = true
				}
			}
		}
		argvPublicTokens[pointer] = tokens
	}
	for index, step := range definition.Steps {
		bindPublicTokens("/steps/"+strconv.Itoa(index)+"/argv", step.Cwd, step.Argv)
	}
	for index, check := range definition.Checks {
		bindPublicTokens("/checks/"+strconv.Itoa(index)+"/argv", check.Cwd, check.Argv)
	}
	var inspect func(any, string, string) error
	inspect = func(value any, pointer, key string) error {
		switch item := value.(type) {
		case map[string]any:
			keys := make([]string, 0, len(item))
			for name := range item {
				keys = append(keys, name)
			}
			sort.Strings(keys)
			for _, name := range keys {
				if redacted := redactLearningTextWithPolicy(name, policy); redacted.text != name {
					return fmt.Errorf("playbook_sensitive_content_rejected_use_environment_bindings: pointer=%s rule=sensitive_field_name", pointer)
				}
				escaped := strings.ReplaceAll(strings.ReplaceAll(name, "~", "~0"), "/", "~1")
				if playbookSecretField.MatchString(name) {
					text, ok := item[name].(string)
					if !ok || !playbookEnvironmentBinding.MatchString(text) {
						return fmt.Errorf("playbook_sensitive_content_rejected_use_environment_bindings: pointer=%s/%s rule=credential_field", pointer, escaped)
					}
				}
				if err := inspect(item[name], pointer+"/"+escaped, name); err != nil {
					return err
				}
			}
		case []any:
			for index, child := range item {
				if err := inspect(child, pointer+"/"+strconv.Itoa(index), key); err != nil {
					return err
				}
			}
		case string:
			if playbookSecretField.MatchString(key) && !playbookEnvironmentBinding.MatchString(item) {
				return fmt.Errorf("playbook_sensitive_content_rejected_use_environment_bindings: pointer=%s rule=credential_field", pointer)
			}
			projection := regexp.MustCompile(`\$\{[A-Z_][A-Z0-9_]*\}`).ReplaceAllString(item, "[REDACTED_SECRET]")
			publicTokens := map[string]bool{}
			for token := range argvPublicTokens[path.Dir(pointer)] {
				publicTokens[token] = true
			}
			// Versioned package filenames are public command data, even before
			// the output exists. Only their basename bypasses the entropy
			// fallback; directories, shell text and deterministic secret/policy
			// detectors retain their existing checks.
			if key == "argv" {
				if basename := playbookPublicArtifactBasename(item); basename != "" {
					publicTokens[basename] = true
				}
			}
			// A canonical owner may name an existing project script rather than
			// a person or service. Exempt only its verified path components from
			// entropy; deterministic credentials and project policy still apply.
			if pointer == "/owner" && playbookScriptPath(item) && playbookPublicPathToken.MatchString(item) {
				if target, pathErr := playbookSafePath(root, item, false); pathErr == nil {
					if info, statErr := os.Lstat(target); statErr == nil && info.Mode().IsRegular() {
						for _, part := range strings.Split(item, "/") {
							publicTokens[part] = true
						}
					}
				}
			}
			if key == "source_files" || key == "script_ref" || key == "cwd" || (key == "argv" && playbookScriptPath(item)) {
				candidate := strings.TrimPrefix(strings.ReplaceAll(item, "\\", "/"), "./")
				if playbookPublicPathToken.MatchString(candidate) {
					if _, pathErr := playbookSafePath(root, candidate, key == "cwd"); pathErr == nil {
						for _, part := range strings.Split(candidate, "/") {
							publicTokens[part] = true
						}
					}
				}
			}
			redacted := redactLearningTextWithPolicyAndEntropyFilter(projection, policy, func(token string) bool {
				return publicTokens[token] || (key == "argv" && playbookPowerShellPreference.MatchString(token))
			})
			if redacted.text != projection {
				return fmt.Errorf("playbook_sensitive_content_rejected_use_environment_bindings: pointer=%s rule=%s", pointer, strings.Join(redacted.labels, ","))
			}
		}
		return nil
	}
	return inspect(decoded, "", "")
}

func playbookPublicArtifactBasename(value string) string {
	normalized := strings.ReplaceAll(value, "\\", "/")
	if !strings.Contains(normalized, "/") {
		return ""
	}
	if len(normalized) >= 2 && normalized[1] == ':' && (len(normalized) < 3 || normalized[2] != '/') {
		return "" // Windows drive-relative paths are not explicit local paths.
	}
	for _, part := range strings.Split(normalized, "/") {
		if part == "." || part == ".." {
			return ""
		}
	}
	if match := playbookPublicArtifactPath.FindStringSubmatch(value); match != nil {
		return match[1]
	}
	return ""
}

func playbookScriptPath(value string) bool {
	switch strings.ToLower(path.Ext(strings.ReplaceAll(value, "\\", "/"))) {
	case ".ps1", ".psm1", ".py", ".sh", ".bash", ".cmd", ".bat", ".js", ".mjs", ".cjs", ".ts", ".rb", ".pl":
		return true
	}
	return false
}

// Resolve only recognizable script entrypoints. This is not a shell parser:
// arbitrary command data and indirect project dependencies stay explicitly declared.
func playbookActionScriptSources(root, cwd string, argv []string) ([]string, error) {
	if len(argv) == 0 {
		return nil, nil
	}
	scripts := []string{}
	add := func(value string) error {
		value = strings.ReplaceAll(strings.Trim(value, "\"'"), "\\", "/")
		if !playbookScriptPath(value) {
			return nil
		}
		if strings.ContainsAny(value, "$%{}") {
			return fmt.Errorf("playbook_dynamic_script_requires_static_project_file")
		}
		if strings.HasPrefix(value, "/") || strings.Contains(value, ":") {
			return fmt.Errorf("playbook_script_path_must_be_project_relative")
		}
		relative := path.Clean(path.Join(cwd, value))
		if _, err := playbookSafePath(root, relative, false); err != nil {
			return err
		}
		scripts = append(scripts, relative)
		return nil
	}
	if err := add(argv[0]); err != nil {
		return nil, err
	}
	executable := strings.TrimSuffix(strings.ToLower(path.Base(strings.ReplaceAll(argv[0], "\\", "/"))), ".exe")
	powershell := executable == "pwsh" || executable == "powershell"
	interpreter := powershell || executable == "bash" || executable == "sh" || executable == "zsh" || executable == "cmd" || executable == "node" || executable == "ruby" || executable == "perl" || regexp.MustCompile(`^python(?:[0-9.]+)?$`).MatchString(executable)
	if !interpreter {
		return uniqueSortedTrimmed(scripts), nil
	}
	for index := 1; index < len(argv); index++ {
		arg := argv[index]
		lower := strings.ToLower(arg)
		inline := (powershell && (lower == "-command" || lower == "-c")) || (!powershell && (lower == "-c" || lower == "-e" || lower == "/c"))
		if inline {
			if index+1 < len(argv) {
				command := argv[index+1]
				directVariableCommand := regexp.MustCompile(`(?i)^\s*["']?(?:\$[A-Za-z_][A-Za-z0-9_]*|\$\{[A-Za-z_][A-Za-z0-9_]*\}|%[A-Za-z_][A-Za-z0-9_]*%)["']?(?:\s|$)`).MatchString(command)
				if directVariableCommand || regexp.MustCompile(`(?i)(?:scriptblock\s*\]::\s*create|invoke-expression|\biex\b|\beval\b|\bexec\s*\()[^\r\n]*(?:\$env:|\$\{|\$[A-Za-z_]|%[A-Za-z_]|environ|process\s*\.\s*env|os\s*\.\s*getenv)`).MatchString(command) || regexp.MustCompile(`(?i)(?:^|[;&|])\s*(?:&\s*)?\$env:|&\s*\(?\s*\$env:`).MatchString(command) {
					return nil, fmt.Errorf("playbook_dynamic_script_requires_static_project_file")
				}
				// A simple quoted or bare script invocation is statically bindable.
				matches := regexp.MustCompile(`(?:^|[;|&])\s*(?:[&.]\s+)?(?:"([^"\r\n]+)"|'([^'\r\n]+)'|([^\s;|&]+))`).FindAllStringSubmatch(command, -1)
				for _, match := range matches {
					for _, value := range match[1:] {
						if value != "" {
							if err := add(value); err != nil {
								return nil, err
							}
							break
						}
					}
				}
			}
			break
		}
		if powershell && (lower == "-file" || lower == "-f") {
			if index+1 < len(argv) {
				if strings.ContainsAny(argv[index+1], "$%{}") {
					return nil, fmt.Errorf("playbook_dynamic_script_requires_static_project_file")
				}
				if err := add(argv[index+1]); err != nil {
					return nil, err
				}
			}
			break
		}
		if strings.HasPrefix(arg, "-") || strings.HasPrefix(arg, "/") {
			continue
		}
		if err := add(arg); err != nil {
			return nil, err
		}
		if playbookScriptPath(arg) || !powershell {
			break
		}
	}
	return uniqueSortedTrimmed(scripts), nil
}
