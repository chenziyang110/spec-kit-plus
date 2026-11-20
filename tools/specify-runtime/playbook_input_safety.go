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
var playbookPublicPathToken = regexp.MustCompile(`^[\p{L}\p{M}\p{N}._/-]+$`)
var playbookPowerShellPreference = regexp.MustCompile(`(?i)^\$(?:ErrorAction|Progress|Warning|Information|Verbose|Debug|Confirm|WhatIf)Preference=?$`)
var playbookPublicArtifactPath = regexp.MustCompile(`(?i)^(?:[a-z]:)?/{0,2}(?:[\p{L}\p{M}\p{N}._-]+/)*([a-z](?:[a-z0-9._-]*[._-][0-9]+(?:[._-][a-z0-9]+)*|[a-z_-]*[0-9]{2,8}[a-z]{0,5})\.(?:exe|dll|msi|msix|msixbundle|zip|7z|cab|iso|wim|esd|tar|gz|bz2|xz))$`)
var playbookBuildFlagName = regexp.MustCompile(`(?i)^[a-z][a-z_-]{0,63}$`)
var playbookBuildFlagValue = regexp.MustCompile(`(?i)^(?:true|false|[0-9]{1,6})$`)
var playbookBuildSelectorValue = regexp.MustCompile(`(?i)^[a-z][a-z0-9_.-]{0,63}$`)
var playbookBuildCredentialField = regexp.MustCompile(`(?i)(?:password|passwd|secret|token|authorization|credentials?|(?:api|access|license|private|signing)[-_]?key)$`)

func playbookAddPublicPathTokens(tokens map[string]bool, value string) {
	for _, part := range strings.Split(value, "/") {
		tokens[part] = true
	}
}

func playbookExistingScript(root, source string) bool {
	if !playbookScriptPath(source) || !playbookPublicPathToken.MatchString(source) {
		return false
	}
	target, err := playbookSafePath(root, source, false)
	if err != nil {
		return false
	}
	info, err := os.Lstat(target)
	return err == nil && info.Mode().IsRegular()
}

// Inspect field values rather than JSON punctuation. Only the entropy fallback
// gets syntax-aware exceptions; credentials and project policy always run first.
func validatePlaybookSensitiveContent(root string, definition PlaybookDefinition) error {
	if err := doProtectedPrivatePayload(definition, definition); err != nil {
		return err
	}
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
	argvScriptTokens := map[string]map[string]bool{}
	argvPublicTokens := map[string]string{}
	prosePublicTokens := map[string]bool{}
	prosePointers := map[string]bool{"/title": true, "/goal": true}
	bindProseScript := func(source string) {
		if playbookExistingScript(root, source) {
			prosePublicTokens[path.Base(source)] = true
		}
	}
	for _, source := range definition.SourceFiles {
		bindProseScript(source)
	}
	bindProseScript(definition.Owner)
	argvCredentialPointers := map[string]bool{}
	bindPublicTokens := func(pointer, cwd, script string, argv []string) {
		prosePointers[pointer+"/purpose"] = true
		prosePointers[pointer+"/expected_result"] = true
		bindProseScript(script)
		sources, err := playbookActionScriptSources(root, cwd, argv)
		if err != nil || len(argv) == 0 {
			return
		}
		scriptTokens := map[string]bool{}
		for _, source := range sources {
			if playbookPublicPathToken.MatchString(source) {
				playbookAddPublicPathTokens(scriptTokens, source)
				bindProseScript(source)
			}
		}
		argvScriptTokens[pointer+"/argv"] = scriptTokens
		executable := playbookExecutableName(argv[0])
		fileScript := playbookPowerShellFileScriptIndex(root, cwd, argv)
		for i, arg := range argv {
			if i > 0 && !playbookDirectDataArgument(executable, fileScript, i) {
				continue
			}
			argumentPointer := pointer + "/argv/" + strconv.Itoa(i)
			if i > 0 && fileScript >= 0 {
				option, value, assigned := strings.Cut(arg, "=")
				name := strings.TrimLeft(option, "-")
				if assigned && playbookBuildFlagName.MatchString(name) && playbookBuildCredentialField.MatchString(name) && !playbookEnvironmentBinding.MatchString(value) {
					argvCredentialPointers[argumentPointer] = true
				}
			}
			// Only the versioned basename is public; directories and
			// arbitrary shell text are still scanned normally.
			if basename := playbookPublicArtifactBasename(arg); basename != "" {
				argvPublicTokens[argumentPointer] = basename
			} else if i > 0 && playbookPublicBuildSetting(executable, fileScript >= 0, arg) {
				// MSBuild /p:Key=Value (and typed CMake -D) may be
				// split on a colon by the entropy detector.
				argvPublicTokens[argumentPointer] = arg[strings.LastIndex(arg, ":")+1:]
			}
		}
	}
	// The definition validator checks these paths and their existing parents
	// before sensitivity validation. A reusable template is checked via its
	// resolved example first; only literal path components qualify here. Use
	// exact positions so arbitrary JSON with the same keys is still inspected.
	typedPathPointers := map[string]bool{}
	for index, step := range definition.Steps {
		pointer := "/steps/" + strconv.Itoa(index)
		bindPublicTokens(pointer, step.Cwd, step.ScriptRef, step.Argv)
		for i := range step.SourceWrites {
			typedPathPointers[pointer+"/source_writes/"+strconv.Itoa(i)] = true
		}
	}
	for index, check := range definition.Checks {
		pointer := "/checks/" + strconv.Itoa(index)
		bindPublicTokens(pointer, check.Cwd, check.ScriptRef, check.Argv)
		switch check.Kind {
		case "file", "json", "junit":
			typedPathPointers[pointer+"/result_path"] = true
		}
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
			if argvCredentialPointers[pointer] {
				return fmt.Errorf("playbook_sensitive_argument_requires_environment_binding: pointer=%s rule=credential_argument", pointer)
			}
			if playbookSecretField.MatchString(key) && !playbookEnvironmentBinding.MatchString(item) {
				return fmt.Errorf("playbook_sensitive_content_rejected_use_environment_bindings: pointer=%s rule=credential_field", pointer)
			}
			projection := regexp.MustCompile(`\$\{[A-Z_][A-Z0-9_]*\}`).ReplaceAllString(item, "[REDACTED_SECRET]")
			publicTokens := map[string]bool{}
			if typedPathPointers[pointer] && playbookPublicPathToken.MatchString(item) {
				playbookAddPublicPathTokens(publicTokens, item)
			}
			// A canonical owner may name an existing project script rather than
			// a person or service. Exempt only its verified path components from
			// entropy; deterministic credentials and project policy still apply.
			if pointer == "/owner" && playbookExistingScript(root, item) {
				playbookAddPublicPathTokens(publicTokens, item)
			}
			if key == "source_files" || key == "script_ref" || key == "cwd" || (key == "argv" && playbookScriptPath(item)) {
				candidate := strings.TrimPrefix(strings.ReplaceAll(item, "\\", "/"), "./")
				if playbookPublicPathToken.MatchString(candidate) {
					if _, pathErr := playbookSafePath(root, candidate, key == "cwd"); pathErr == nil {
						playbookAddPublicPathTokens(publicTokens, candidate)
					}
				}
			}
			redacted := redactLearningTextWithPolicyAndEntropyFilter(projection, policy, func(token string) bool {
				return publicTokens[token] || argvScriptTokens[path.Dir(pointer)][token] || argvPublicTokens[pointer] == token ||
					(prosePointers[pointer] && prosePublicTokens[token]) ||
					(key == "argv" && playbookPowerShellPreference.MatchString(token))
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
	if match := playbookPublicArtifactPath.FindStringSubmatch(normalized); match != nil {
		return match[1]
	}
	return ""
}

func playbookExecutableName(value string) string {
	return strings.TrimSuffix(strings.ToLower(path.Base(strings.ReplaceAll(value, "\\", "/"))), ".exe")
}

func playbookDirectDataArgument(executable string, fileScript, index int) bool {
	switch executable {
	case "powershell", "pwsh":
		return fileScript >= 0 && index > fileScript
	case "cmd", "sh", "bash", "zsh", "dash", "ksh", "fish", "node", "ruby", "perl", "wsl":
		return false
	default:
		return !strings.HasPrefix(executable, "python")
	}
}

// Parse only the property syntaxes these build tools know; arbitrary commands
// and inline shell programs do not get a general key=value exemption.
func playbookBuilderProperty(executable, option string) string {
	switch executable {
	case "msbuild", "dotnet":
		if key, ok := strings.CutPrefix(option, "/"); ok {
			option = "-" + key
		}
		lower := strings.ToLower(option)
		for _, prefix := range []string{"-p:", "-property:"} {
			if strings.HasPrefix(lower, prefix) {
				return lower[len(prefix):]
			}
		}
	case "cmake":
		if property, ok := strings.CutPrefix(option, "-D"); ok {
			name, _, _ := strings.Cut(property, ":") // -DNAME[:TYPE]=value
			return strings.ToLower(name)
		}
	}
	return ""
}

func playbookPublicBuildSetting(executable string, fixedPowerShellScript bool, arg string) bool {
	option, value, ok := strings.Cut(arg, "=")
	if !ok {
		return false
	}
	name := playbookBuilderProperty(executable, option)
	if name != "" {
		if playbookBuildCredentialField.MatchString(name) {
			return false
		}
		if playbookBuildFlagName.MatchString(name) && playbookBuildFlagValue.MatchString(value) {
			return true
		}
	}
	if fixedPowerShellScript {
		name := strings.TrimLeft(option, "-")
		return !playbookBuildCredentialField.MatchString(name) && playbookBuildFlagName.MatchString(name) && playbookBuildFlagValue.MatchString(value)
	}
	if executable == "dotnet" && name == "" {
		switch strings.ToLower(option) {
		case "--configuration", "--framework", "--runtime", "--arch", "--os":
			name = "configuration" // These options take a single selector.
		}
	}
	switch name {
	case "configuration", "platform", "platformtarget", "targetframework", "runtimeidentifier":
		if executable == "cmake" {
			return false
		}
	case "cmake_build_type":
		if executable != "cmake" {
			return false
		}
	default:
		return false
	}
	// A documented selector's value is still scanned separately, so a
	// genuinely opaque value can't borrow the option name's exemption.
	return playbookBuildSelectorValue.MatchString(value) && redactLearningText(value).text == value
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
	executable := playbookExecutableName(argv[0])
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
