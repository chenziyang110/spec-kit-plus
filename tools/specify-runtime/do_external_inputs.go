package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path"
	"path/filepath"
	"regexp"
	"runtime"
	"sort"
	"strings"
)

// Only symbolic bindings belong in a method. Their actual paths and file bytes
// remain process-local and are never returned by the runtime.
type PlaybookExternalInput struct {
	Environment string `json:"environment"`
}

func (input *PlaybookExternalInput) UnmarshalJSON(raw []byte) error {
	if err := playbookRequireJSONFields(raw, "environment"); err != nil {
		return err
	}
	type plain PlaybookExternalInput
	var decoded plain
	if err := decodePlaybookJSON(raw, &decoded); err != nil {
		return err
	}
	*input = PlaybookExternalInput(decoded)
	return nil
}

type DoExternalInputSnapshot struct {
	Environment   string `json:"environment"`
	ContentSHA256 string `json:"content_sha256"`
}

// All fields are safe symbolic identifiers or runtime-owned diagnostics. Never
// attach an os.PathError, environment value, resolved path or file contents.
type doExternalInputError struct {
	Code        string
	Name        string
	Environment string
	Pointer     string
}

func (err *doExternalInputError) Error() string {
	message := err.Code + ": pointer=" + err.Pointer
	if err.Environment != "" {
		message += " environment=" + err.Environment
	}
	return message
}

var doExternalEnvironment = regexp.MustCompile(`^[A-Z_][A-Z0-9_]{0,127}$`)
var doExternalName = regexp.MustCompile(`^[a-z][a-z0-9_]{0,63}$`)
var doExternalToken = regexp.MustCompile(`^\{\{external:([a-z][a-z0-9_]{0,63})\}\}$`)

func doExternalDefinition(root string, definition PlaybookDefinition) error {
	issue := func(code, name, pointer string) error {
		return &doExternalInputError{Code: code, Name: name, Pointer: pointer}
	}
	if len(definition.ExternalInputs) > 32 {
		return issue("external_input_count_invalid", "", "/external_inputs")
	}
	for name, input := range definition.ExternalInputs {
		if !doExternalName.MatchString(name) {
			return issue("external_input_name_invalid", "", "/external_inputs")
		}
		if !doExternalEnvironment.MatchString(input.Environment) {
			return issue("external_input_environment_invalid", name, playbookJSONPointer("/external_inputs", name)+"/environment")
		}
	}
	if len(definition.ExternalInputs) > 0 {
		for index, step := range definition.Steps {
			if step.NativeAction != nil {
				return issue("external_input_requires_process_execution", "", fmt.Sprintf("/steps/%d/native_action", index))
			}
		}
		for index, check := range definition.Checks {
			if check.NativeAction != nil {
				return issue("external_input_requires_process_execution", "", fmt.Sprintf("/checks/%d/native_action", index))
			}
			if check.Kind != "exit_code" && check.Kind != "file" {
				return issue("external_input_checks_must_not_capture_contents", "", fmt.Sprintf("/checks/%d/kind", index))
			}
		}
	}
	used := map[string]bool{}
	scrubbed := definition
	scrubbed.Steps = append([]PlaybookStep{}, definition.Steps...)
	scrubbed.Checks = append([]PlaybookCheck{}, definition.Checks...)
	inspect := func(cwd string, argv []string, pointer string) ([]string, error) {
		result := append([]string{}, argv...)
		scriptIndex := -1
		for index, argument := range argv {
			if !strings.Contains(argument, "{{external:") {
				continue
			}
			location := fmt.Sprintf("%s/%d", pointer, index)
			match := doExternalToken.FindStringSubmatch(argument)
			if len(match) != 2 {
				return nil, issue("external_input_requires_complete_argv_token", "", location)
			}
			name := match[1]
			if _, exists := definition.ExternalInputs[name]; !exists {
				return nil, issue("external_input_not_declared", name, location)
			}
			if scriptIndex < 0 {
				scriptIndex = doExternalScriptDataIndex(root, cwd, argv)
			}
			if scriptIndex < 0 || index <= scriptIndex {
				return nil, issue("external_input_requires_fixed_script_data_position", name, location)
			}
			used[name] = true
			result[index] = "protected-external-input"
		}
		return result, nil
	}
	for index, step := range definition.Steps {
		argv, err := inspect(step.Cwd, step.Argv, fmt.Sprintf("/steps/%d/argv", index))
		if err != nil {
			return err
		}
		scrubbed.Steps[index].Argv = argv
	}
	for index, check := range definition.Checks {
		argv, err := inspect(check.Cwd, check.Argv, fmt.Sprintf("/checks/%d/argv", index))
		if err != nil {
			return err
		}
		scrubbed.Checks[index].Argv = argv
	}
	raw, err := json.Marshal(scrubbed)
	if err != nil || bytes.Contains(raw, []byte("{{external:")) {
		return issue("external_input_outside_script_argv", "", "")
	}
	for name := range definition.ExternalInputs {
		if !used[name] {
			return issue("external_input_not_used", name, playbookJSONPointer("/external_inputs", name))
		}
	}
	return nil
}

// Shell command strings and interpreter expressions never qualify. Supported
// interpreters must name a fixed existing project script before the data slot.
func doExternalScriptDataIndex(root, cwd string, argv []string) int {
	if len(argv) == 0 || strings.Contains(cwd, "{{") {
		return -1
	}
	command := strings.TrimSuffix(strings.ToLower(path.Base(strings.ReplaceAll(argv[0], "\\", "/"))), ".exe")
	if command == "pwsh" || command == "powershell" {
		return playbookPowerShellFileScriptIndex(root, cwd, argv)
	}
	bind := func(index int, extensions map[string]bool) int {
		script := strings.ReplaceAll(argv[index], "\\", "/")
		if !extensions[strings.ToLower(path.Ext(script))] || strings.HasPrefix(script, "/") || strings.ContainsAny(script, ":$%{}\"'`;|&()*?[]\x00\r\n") {
			return -1
		}
		relative := path.Clean(path.Join(cwd, script))
		if _, err := playbookSafePath(root, relative, false); err != nil {
			return -1
		}
		if _, err := secureProjectReadFile(root, relative); err != nil {
			return -1
		}
		return index
	}
	python := regexp.MustCompile(`^python(?:[0-9.]+)?$`).MatchString(command)
	if python {
		for index := 1; index < len(argv); index++ {
			if strings.HasPrefix(argv[index], "-") {
				switch argv[index] {
				case "-u", "-B", "-E", "-I", "-O", "-OO", "-s", "-S", "-q":
					continue
				default:
					return -1
				}
			}
			return bind(index, map[string]bool{".py": true})
		}
		return -1
	}
	if command == "node" || command == "ruby" || command == "perl" || command == "bash" || command == "sh" || command == "zsh" {
		if len(argv) < 2 {
			return -1
		}
		extensions := map[string]map[string]bool{
			"node": {".js": true, ".mjs": true, ".cjs": true}, "ruby": {".rb": true}, "perl": {".pl": true},
			"bash": {".sh": true, ".bash": true}, "sh": {".sh": true}, "zsh": {".sh": true},
		}
		return bind(1, extensions[command])
	}
	return bind(0, map[string]bool{".py": true, ".ps1": true, ".sh": true, ".bash": true, ".js": true, ".mjs": true, ".cjs": true, ".rb": true, ".pl": true})
}

func doExternalSnapshot(root string, definition PlaybookDefinition) (map[string]DoExternalInputSnapshot, string, error) {
	if err := doExternalDefinition(root, definition); err != nil {
		return nil, "", err
	}
	if len(definition.ExternalInputs) == 0 {
		return nil, "", nil
	}
	project, err := filepath.Abs(root)
	if err == nil {
		project, err = filepath.EvalSymlinks(project)
	}
	if err != nil {
		return nil, "", &doExternalInputError{Code: "external_input_project_boundary_unavailable", Pointer: "/external_inputs"}
	}
	names := make([]string, 0, len(definition.ExternalInputs))
	for name := range definition.ExternalInputs {
		names = append(names, name)
	}
	sort.Strings(names)
	metadata := make(map[string]DoExternalInputSnapshot, len(names))
	aggregate := sha256.New()
	for _, name := range names {
		input := definition.ExternalInputs[name]
		failure := func(code string) (map[string]DoExternalInputSnapshot, string, error) {
			return nil, "", &doExternalInputError{Code: code, Name: name, Environment: input.Environment, Pointer: playbookJSONPointer("/external_inputs", name) + "/environment"}
		}
		value, exists := os.LookupEnv(input.Environment)
		if !exists || value == "" {
			return failure("external_input_environment_unavailable")
		}
		if !filepath.IsAbs(value) || strings.TrimSpace(value) != value || strings.ContainsAny(value, "\x00\r\n") || len(value) > 32768 {
			return failure("external_input_requires_absolute_file_binding")
		}
		before, statErr := os.Lstat(value)
		if statErr != nil {
			return failure("external_input_file_unavailable")
		}
		if !before.Mode().IsRegular() {
			return failure("external_input_requires_regular_file")
		}
		resolved, resolveErr := filepath.EvalSymlinks(value)
		if resolveErr != nil {
			return failure("external_input_file_unavailable")
		}
		resolved = filepath.Clean(resolved)
		relative, relativeErr := filepath.Rel(project, resolved)
		if relativeErr == nil && !filepath.IsAbs(relative) && relative != ".." && !strings.HasPrefix(relative, ".."+string(filepath.Separator)) {
			return failure("external_input_must_stay_outside_project")
		}
		file, openErr := os.Open(resolved)
		if openErr != nil {
			return failure("external_input_file_unreadable")
		}
		opened, openedErr := file.Stat()
		if openedErr != nil || !opened.Mode().IsRegular() || !os.SameFile(before, opened) {
			_ = file.Close()
			return failure("external_input_changed_during_read")
		}
		content := sha256.New()
		readBytes, readErr := io.Copy(content, io.LimitReader(file, before.Size()+1))
		after, afterErr := file.Stat()
		closeErr := file.Close()
		current, currentErr := os.Lstat(value)
		confirmed, confirmedErr := filepath.EvalSymlinks(value)
		if readErr != nil || afterErr != nil || closeErr != nil || currentErr != nil || confirmedErr != nil {
			return failure("external_input_file_unreadable")
		}
		if readBytes != before.Size() || !after.Mode().IsRegular() || !current.Mode().IsRegular() || !os.SameFile(before, after) || !os.SameFile(after, current) || before.Size() != after.Size() || after.Size() != current.Size() || !before.ModTime().Equal(after.ModTime()) || !after.ModTime().Equal(current.ModTime()) || filepath.Clean(confirmed) != resolved {
			return failure("external_input_changed_during_read")
		}
		contentDigest := hex.EncodeToString(content.Sum(nil))
		metadata[name] = DoExternalInputSnapshot{Environment: input.Environment, ContentSHA256: contentDigest}
		if runtime.GOOS == "windows" {
			resolved = strings.ToLower(resolved)
		}
		pathDigest := sha256.Sum256([]byte(resolved))
		// The path hash exists only inside this opaque aggregate. Publishing it
		// separately would make private filenames easier to guess independently.
		_ = json.NewEncoder(aggregate).Encode([]string{name, input.Environment, contentDigest, hex.EncodeToString(pathDigest[:])})
	}
	return metadata, hex.EncodeToString(aggregate.Sum(nil)), nil
}
