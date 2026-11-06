package main

import (
	"bytes"
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

const playbookSchemaVersion = 1
const playbookMaxJSONBytes = 256 * 1024

// PlaybookDefinition is the ordered, reusable method. Runtime identity,
// revisions, verification observations and usage counters are not agent input.
type PlaybookDefinition struct {
	TaskFamily     string                           `json:"task_family,omitempty"`
	Parameters     map[string]PlaybookParameter     `json:"parameters,omitempty"`
	ExternalInputs map[string]PlaybookExternalInput `json:"external_inputs,omitempty"`
	Operation      string                           `json:"operation"`
	Target         string                           `json:"target"`
	Owner          string                           `json:"owner"`
	Variant        string                           `json:"variant"`
	Title          string                           `json:"title"`
	Goal           string                           `json:"goal"`
	Aliases        []string                         `json:"aliases"`
	Applicability  map[string][]string              `json:"applicability"`
	SourceFiles    []string                         `json:"source_files"`
	Steps          []PlaybookStep                   `json:"steps"`
	Checks         []PlaybookCheck                  `json:"checks"`
	LearningRefs   []string                         `json:"learning_refs"`
}

type PlaybookStep struct {
	NativeAction   *PlaybookNativeAction `json:"native_action,omitempty"`
	ID             string                `json:"id"`
	Purpose        string                `json:"purpose"`
	Cwd            string                `json:"cwd"`
	Argv           []string              `json:"argv"`
	ScriptRef      string                `json:"script_ref,omitempty"`
	SourceWrites   []string              `json:"source_writes,omitempty"`
	DependsOn      []string              `json:"depends_on"`
	Required       bool                  `json:"required"`
	ExpectedResult string                `json:"expected_result"`
	SideEffect     string                `json:"side_effect"`
}

type PlaybookCheck struct {
	NativeAction   *PlaybookNativeAction `json:"native_action,omitempty"`
	ID             string                `json:"id"`
	Purpose        string                `json:"purpose"`
	Cwd            string                `json:"cwd"`
	Argv           []string              `json:"argv"`
	ScriptRef      string                `json:"script_ref,omitempty"`
	DependsOn      []string              `json:"depends_on"`
	Required       bool                  `json:"required"`
	ExpectedResult string                `json:"expected_result"`
	Kind           string                `json:"kind"`
	ResultPath     string                `json:"result_path,omitempty"`
	JSONPointer    string                `json:"json_pointer,omitempty"`
	ExpectedJSON   json.RawMessage       `json:"expected_json,omitempty"`
	MinCases       int                   `json:"min_cases,omitempty"`
}

func playbookRequireJSONFields(raw []byte, names ...string) error {
	var fields map[string]json.RawMessage
	if err := json.Unmarshal(raw, &fields); err != nil || fields == nil {
		return fmt.Errorf("playbook_json_object_required")
	}
	for _, name := range names {
		value, present := fields[name]
		if !present || bytes.Equal(bytes.TrimSpace(value), []byte("null")) {
			return fmt.Errorf("playbook_required_field_missing_or_null: %s", name)
		}
	}
	return nil
}

func (definition *PlaybookDefinition) UnmarshalJSON(raw []byte) error {
	if err := playbookRequireJSONFields(raw, "operation", "target", "owner", "variant", "title", "goal", "aliases", "applicability", "source_files", "steps", "checks", "learning_refs"); err != nil {
		return err
	}
	type plain PlaybookDefinition
	var value plain
	if err := decodePlaybookJSON(raw, &value); err != nil {
		return err
	}
	*definition = PlaybookDefinition(value)
	return nil
}

func (step *PlaybookStep) UnmarshalJSON(raw []byte) error {
	type plain PlaybookStep
	var value plain
	if err := decodePlaybookJSON(raw, &value); err != nil {
		return err
	}
	fields := []string{"id", "purpose", "depends_on", "required", "expected_result", "side_effect"}
	if value.NativeAction == nil {
		fields = append(fields, "cwd", "argv")
	}
	if err := playbookRequireJSONFields(raw, fields...); err != nil {
		return err
	}
	*step = PlaybookStep(value)
	return nil
}

func (check *PlaybookCheck) UnmarshalJSON(raw []byte) error {
	type plain PlaybookCheck
	var value plain
	if err := decodePlaybookJSON(raw, &value); err != nil {
		return err
	}
	fields := []string{"id", "purpose", "depends_on", "required", "expected_result", "kind"}
	if value.NativeAction == nil {
		fields = append(fields, "cwd", "argv")
	}
	if err := playbookRequireJSONFields(raw, fields...); err != nil {
		return err
	}
	*check = PlaybookCheck(value)
	return nil
}

type PlaybookDocument struct {
	SchemaVersion     int                         `json:"schema_version"`
	ID                string                      `json:"id"`
	Revision          int                         `json:"revision"`
	ContentDigest     string                      `json:"content_digest"`
	Status            string                      `json:"status"`
	Definition        PlaybookDefinition          `json:"definition"`
	SourceFingerprint map[string]string           `json:"source_fingerprint"`
	Verification      DoPlaybookValidationReceipt `json:"verification"`
	CreatedAt         string                      `json:"created_at"`
	UpdatedAt         string                      `json:"updated_at"`
}

type PlaybookProposal struct {
	SchemaVersion    int                `json:"schema_version"`
	ID               string             `json:"id"`
	BaseDigest       string             `json:"base_digest"`
	DefinitionDigest string             `json:"definition_digest"`
	Definition       PlaybookDefinition `json:"definition"`
	ChangeSummary    string             `json:"change_summary"`
	CreatedAt        string             `json:"created_at"`
}

type PlaybookUpdateRequest struct {
	ID            string             `json:"id,omitempty"`
	BaseDigest    string             `json:"base_digest,omitempty"`
	Definition    PlaybookDefinition `json:"definition"`
	SessionID     string             `json:"session_id,omitempty"`
	ChangeSummary string             `json:"change_summary"`
	ProposalOnly  bool               `json:"proposal_only,omitempty"`
}

var playbookIDPattern = regexp.MustCompile(`^pb-[a-z0-9][a-z0-9-]{0,47}-[a-f0-9]{16}$`)
var playbookItemIDPattern = regexp.MustCompile(`^[A-Za-z][A-Za-z0-9_-]{0,63}$`)
var playbookContextKeyPattern = regexp.MustCompile(`^(os|arch|shell|toolchain\.[a-z][a-z0-9_-]{0,31})$`)
var playbookDigestPattern = regexp.MustCompile(`^[a-f0-9]{64}$`)

// Decode strictly at every public boundary; duplicated keys must not let a
// reviewer and the runtime interpret the same submitted bytes differently.
func decodePlaybookJSON(raw []byte, target any) error {
	if len(raw) == 0 || len(raw) > playbookMaxJSONBytes {
		return fmt.Errorf("playbook_json_size_invalid")
	}
	if err := playbookRejectDuplicateKeys(raw); err != nil {
		return err
	}
	decoder := json.NewDecoder(bytes.NewReader(raw))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(target); err != nil {
		return playbookDescribeJSONError(raw, target, err)
	}
	var extra any
	if err := decoder.Decode(&extra); err != io.EOF {
		return fmt.Errorf("playbook_json_trailing_value")
	}
	return nil
}

func playbookRejectDuplicateKeys(raw []byte) error {
	decoder := json.NewDecoder(bytes.NewReader(raw))
	decoder.UseNumber()
	var visit func(int) error
	visit = func(depth int) error {
		if depth > 32 {
			return fmt.Errorf("playbook_json_nesting_limit")
		}
		token, err := decoder.Token()
		if err != nil {
			return fmt.Errorf("playbook_json_invalid")
		}
		delimiter, ok := token.(json.Delim)
		if !ok {
			return nil
		}
		switch delimiter {
		case '{':
			seen := map[string]bool{}
			for decoder.More() {
				key, err := decoder.Token()
				if err != nil {
					return fmt.Errorf("playbook_json_invalid")
				}
				name, ok := key.(string)
				if !ok || seen[name] {
					return fmt.Errorf("playbook_json_duplicate_key")
				}
				seen[name] = true
				if err := visit(depth + 1); err != nil {
					return err
				}
			}
		case '[':
			for decoder.More() {
				if err := visit(depth + 1); err != nil {
					return err
				}
			}
		default:
			return fmt.Errorf("playbook_json_invalid")
		}
		_, err = decoder.Token()
		if err != nil {
			return fmt.Errorf("playbook_json_invalid")
		}
		return nil
	}
	if err := visit(0); err != nil {
		return err
	}
	if _, err := decoder.Token(); err != io.EOF {
		return fmt.Errorf("playbook_json_trailing_value")
	}
	return nil
}

func playbookDefinitionDigest(definition PlaybookDefinition) (string, error) {
	raw, err := json.Marshal(playbookNormalizeDefinition(definition))
	if err != nil {
		return "", fmt.Errorf("playbook_definition_encoding_failed")
	}
	return fileContentSHA256(raw), nil
}

func playbookID(definition PlaybookDefinition) string {
	identity := strings.Join([]string{definition.Operation, definition.Target, definition.Owner, definition.Variant}, "\x00")
	slug := regexp.MustCompile(`[^a-z0-9]+`).ReplaceAllString(strings.ToLower(definition.Operation+"-"+definition.Target), "-")
	slug = strings.Trim(slug, "-")
	if len(slug) > 48 {
		slug = strings.TrimRight(slug[:48], "-")
	}
	if slug == "" {
		slug = "operation"
	}
	return "pb-" + slug + "-" + fileContentSHA256([]byte(identity))[:16]
}

func playbookNormalizeDefinition(definition PlaybookDefinition) PlaybookDefinition {
	// Copy ordered collections before normalizing set-valued fields. Unlike
	// Learning merge, this never sorts steps, argv, or verification order.
	result := definition
	result.Parameters = normalizePlaybookParameters(definition.Parameters)
	if len(definition.ExternalInputs) > 0 {
		result.ExternalInputs = map[string]PlaybookExternalInput{}
		for name, binding := range definition.ExternalInputs {
			result.ExternalInputs[name] = binding
		}
	}
	result.Steps = append([]PlaybookStep{}, definition.Steps...)
	result.Checks = append([]PlaybookCheck{}, definition.Checks...)
	result.Applicability = map[string][]string{}
	for key, values := range definition.Applicability {
		result.Applicability[key] = append([]string{}, values...)
	}
	result.Aliases = uniqueSortedTrimmed(result.Aliases)
	result.SourceFiles = uniqueSortedTrimmed(result.SourceFiles)
	result.LearningRefs = uniqueSortedTrimmed(result.LearningRefs)
	if result.Aliases == nil {
		result.Aliases = []string{}
	}
	if result.SourceFiles == nil {
		result.SourceFiles = []string{}
	}
	if result.LearningRefs == nil {
		result.LearningRefs = []string{}
	}
	if result.Applicability == nil {
		result.Applicability = map[string][]string{}
	}
	for key, values := range result.Applicability {
		result.Applicability[key] = uniqueSortedTrimmed(values)
	}
	for i := range result.Steps {
		result.Steps[i].NativeAction = normalizePlaybookNativeAction(result.Steps[i].NativeAction)
		result.Steps[i].Argv = append([]string{}, result.Steps[i].Argv...)
		result.Steps[i].SourceWrites = uniqueSortedTrimmed(result.Steps[i].SourceWrites)
		result.Steps[i].DependsOn = uniqueSortedTrimmed(result.Steps[i].DependsOn)
		if result.Steps[i].DependsOn == nil {
			result.Steps[i].DependsOn = []string{}
		}
	}
	for i := range result.Checks {
		result.Checks[i].NativeAction = normalizePlaybookNativeAction(result.Checks[i].NativeAction)
		result.Checks[i].Argv = append([]string{}, result.Checks[i].Argv...)
		result.Checks[i].DependsOn = uniqueSortedTrimmed(result.Checks[i].DependsOn)
		if result.Checks[i].DependsOn == nil {
			result.Checks[i].DependsOn = []string{}
		}
		if result.Checks[i].Argv == nil {
			result.Checks[i].Argv = []string{}
		}
		if len(result.Checks[i].ExpectedJSON) > 0 {
			var value any
			decoder := json.NewDecoder(bytes.NewReader(result.Checks[i].ExpectedJSON))
			decoder.UseNumber()
			if decoder.Decode(&value) == nil {
				result.Checks[i].ExpectedJSON, _ = json.Marshal(value)
			}
		}
	}
	return result
}

func validateResolvedPlaybookDefinition(projectRoot string, definition PlaybookDefinition) error {
	if err := doExternalDefinition(projectRoot, definition); err != nil {
		return err
	}
	operations := map[string]bool{"build": true, "package": true, "test": true, "check": true, "generate": true, "maintenance": true, "custom": true}
	if !operations[definition.Operation] {
		return fmt.Errorf("playbook_operation_invalid")
	}
	for _, value := range []string{definition.Target, definition.Owner, definition.Variant, definition.Title, definition.Goal} {
		if strings.TrimSpace(value) == "" || strings.TrimSpace(value) != value || len(value) > 2048 || strings.ContainsAny(value, "\x00\r\n") {
			return fmt.Errorf("playbook_identity_or_description_invalid")
		}
	}
	if len(definition.Target) > 128 || len(definition.Owner) > 256 || !regexp.MustCompile(`^[a-z0-9][a-z0-9._-]{0,63}$`).MatchString(definition.Variant) {
		return fmt.Errorf("playbook_identity_invalid")
	}
	if len(definition.Aliases) > 32 || len(definition.LearningRefs) > 32 || len(definition.SourceFiles) < 1 || len(definition.SourceFiles) > 64 || len(definition.Steps) < 1 || len(definition.Steps) > 64 || len(definition.Checks) < 1 || len(definition.Checks) > 64 {
		return fmt.Errorf("playbook_collection_bounds_invalid")
	}
	for _, values := range [][]string{definition.Aliases, definition.LearningRefs} {
		for _, value := range values {
			if strings.TrimSpace(value) == "" || len(value) > 512 || strings.ContainsAny(value, "\x00\r\n") {
				return fmt.Errorf("playbook_reference_or_alias_invalid")
			}
		}
	}
	if len(definition.Applicability) > 24 {
		return fmt.Errorf("playbook_applicability_invalid")
	}
	for key, values := range definition.Applicability {
		if !playbookContextKeyPattern.MatchString(key) || len(values) < 1 || len(values) > 16 {
			return fmt.Errorf("playbook_applicability_invalid")
		}
		for _, value := range values {
			if value == "" || strings.TrimSpace(value) != value || len(value) > 128 || strings.ContainsAny(value, "\x00\r\n") {
				return fmt.Errorf("playbook_applicability_invalid")
			}
		}
	}
	for _, source := range definition.SourceFiles {
		if _, err := playbookSafePath(projectRoot, source, false); err != nil {
			return err
		}
	}
	seen := map[string]bool{}
	requiredSteps, requiredChecks := 0, 0
	for index, step := range definition.Steps {
		cwd := step.Cwd
		if step.NativeAction != nil {
			cwd = "."
		}
		if err := validatePlaybookAction(projectRoot, step.ID, step.Purpose, cwd, step.Argv, step.ScriptRef, step.DependsOn, step.ExpectedResult, seen, step.NativeAction == nil); err != nil {
			if strings.Contains(err.Error(), "pointer=/") {
				return fmt.Errorf("%s", strings.Replace(err.Error(), "pointer=/", fmt.Sprintf("pointer=/steps/%d/", index), 1))
			}
			return fmt.Errorf("%w: pointer=/steps/%d", err, index)
		}
		if err := validatePlaybookNativeAction(projectRoot, step.NativeAction, step.Argv, step.Cwd, step.ScriptRef); err != nil {
			return err
		}
		if step.SideEffect != "read" && step.SideEffect != "local_write" && step.SideEffect != "external_mutation" {
			return fmt.Errorf("playbook_side_effect_invalid")
		}
		if len(step.SourceWrites) > 64 || (len(step.SourceWrites) > 0 && step.SideEffect != "local_write") {
			return fmt.Errorf("playbook_source_writes_require_bounded_local_write_step")
		}
		for _, source := range step.SourceWrites {
			if len(source) > 512 || strings.ContainsAny(source, "*?[]") {
				return fmt.Errorf("playbook_source_write_path_invalid")
			}
			if _, err := playbookSafePath(projectRoot, source, false); err != nil {
				return err
			}
			ownerPath := strings.ToLower(source)
			if ownerPath == ".specify" || strings.HasPrefix(ownerPath, ".specify/") || ownerPath == ".planning" || strings.HasPrefix(ownerPath, ".planning/") {
				return fmt.Errorf("playbook_source_write_cannot_target_workflow_state")
			}
		}
		if step.Required {
			requiredSteps++
		}
		seen[step.ID] = true
	}
	for index, check := range definition.Checks {
		cwd := check.Cwd
		if check.NativeAction != nil {
			cwd = "."
		}
		if err := validatePlaybookAction(projectRoot, check.ID, check.Purpose, cwd, check.Argv, check.ScriptRef, check.DependsOn, check.ExpectedResult, seen, check.Kind == "exit_code"); err != nil {
			if strings.Contains(err.Error(), "pointer=/") {
				return fmt.Errorf("%s", strings.Replace(err.Error(), "pointer=/", fmt.Sprintf("pointer=/checks/%d/", index), 1))
			}
			return fmt.Errorf("%w: pointer=/checks/%d", err, index)
		}
		if err := validatePlaybookNativeAction(projectRoot, check.NativeAction, check.Argv, check.Cwd, check.ScriptRef); err != nil {
			return err
		}
		switch check.Kind {
		case "exit_code":
			if check.NativeAction != nil || check.ResultPath != "" || check.JSONPointer != "" || len(check.ExpectedJSON) > 0 || check.MinCases != 0 {
				return fmt.Errorf("playbook_check_fields_conflict")
			}
		case "observation":
			if check.NativeAction == nil || len(check.DependsOn) == 0 || check.ResultPath != "" || check.MinCases != 0 || (check.JSONPointer != "" && !strings.HasPrefix(check.JSONPointer, "/")) || len(check.ExpectedJSON) == 0 || len(check.ExpectedJSON) > 8192 || !json.Valid(check.ExpectedJSON) {
				return fmt.Errorf("playbook_observation_check_invalid")
			}
			if err := playbookRejectDuplicateKeys(check.ExpectedJSON); err != nil {
				return err
			}
		case "file", "json", "junit":
			if _, err := playbookSafePath(projectRoot, check.ResultPath, false); err != nil {
				return err
			}
			if check.Kind == "json" {
				if (check.JSONPointer != "" && !strings.HasPrefix(check.JSONPointer, "/")) || len(check.ExpectedJSON) == 0 || len(check.ExpectedJSON) > 8192 || !json.Valid(check.ExpectedJSON) || check.MinCases != 0 {
					return fmt.Errorf("playbook_json_check_invalid")
				}
				if err := playbookRejectDuplicateKeys(check.ExpectedJSON); err != nil {
					return err
				}
			} else if check.JSONPointer != "" || len(check.ExpectedJSON) > 0 {
				return fmt.Errorf("playbook_check_fields_conflict")
			}
			if check.Kind == "junit" && (check.MinCases < 1 || check.MinCases > 10000000) {
				return fmt.Errorf("playbook_junit_min_cases_required")
			}
			if check.Kind != "junit" && check.MinCases != 0 {
				return fmt.Errorf("playbook_check_fields_conflict")
			}
		default:
			return fmt.Errorf("playbook_check_kind_invalid")
		}
		if check.Required {
			requiredChecks++
		}
		seen[check.ID] = true
	}
	if requiredSteps == 0 || requiredChecks == 0 {
		return fmt.Errorf("playbook_required_execution_and_check_missing")
	}
	if err := doValidateNativeCoverage(definition); err != nil {
		return err
	}
	raw, err := json.Marshal(definition)
	if err != nil || len(raw) > playbookMaxJSONBytes {
		return fmt.Errorf("playbook_definition_size_invalid")
	}
	return validatePlaybookSensitiveContent(projectRoot, definition)
}

func validatePlaybookAction(root, id, purpose, cwd string, argv []string, script string, dependencies []string, expected string, seen map[string]bool, requireArgv bool) error {
	if !playbookItemIDPattern.MatchString(id) || seen[id] || strings.TrimSpace(purpose) == "" || len(purpose) > 2048 || strings.TrimSpace(expected) == "" || len(expected) > 2048 || len(dependencies) > 64 {
		return fmt.Errorf("playbook_step_or_check_invalid")
	}
	if _, err := playbookSafePath(root, cwd, true); err != nil {
		return fmt.Errorf("%w: pointer=/cwd", err)
	}
	if len(argv) > 128 || (requireArgv && len(argv) == 0) {
		return fmt.Errorf("playbook_argv_invalid")
	}
	for i, arg := range argv {
		if len(arg) > 8192 || strings.ContainsRune(arg, '\x00') || (i == 0 && strings.TrimSpace(arg) == "") {
			return fmt.Errorf("playbook_argv_invalid")
		}
		name, value, hasValue := strings.Cut(arg, "=")
		name = strings.TrimLeft(strings.ToLower(name), "-")
		if regexp.MustCompile(`^(token|password|passwd|secret|api[-_]?key|access[-_]?token|authorization|client[-_]?secret)$`).MatchString(name) {
			if !hasValue && i+1 < len(argv) {
				value = argv[i+1]
			}
			if !regexp.MustCompile(`^\$\{[A-Z_][A-Z0-9_]*\}$`).MatchString(value) {
				return fmt.Errorf("playbook_sensitive_argument_requires_environment_binding: pointer=/argv/%d rule=credential_argument", i)
			}
		}
	}
	if _, err := playbookActionScriptSources(root, cwd, argv); err != nil {
		return err
	}
	if script != "" {
		if _, err := playbookSafePath(root, script, false); err != nil {
			return err
		}
		if len(argv) == 0 {
			return fmt.Errorf("playbook_script_requires_argv")
		}
	}
	for _, dependency := range dependencies {
		if !seen[dependency] {
			return fmt.Errorf("playbook_dependency_must_precede_consumer")
		}
	}
	return nil
}

func playbookSafePath(root, relative string, allowRoot bool) (string, error) {
	if relative == "." && allowRoot {
		return secureProjectPath(root, ".")
	}
	if relative == "" || strings.ContainsAny(relative, "\\:\x00\r\n") || strings.HasPrefix(relative, "/") || path.Clean(relative) != relative || relative == "." {
		return "", fmt.Errorf("playbook_path_must_be_canonical_project_relative")
	}
	for _, part := range strings.Split(relative, "/") {
		if part == ".." || strings.EqualFold(part, ".git") || part == "" {
			return "", fmt.Errorf("playbook_path_outside_source_scope")
		}
	}
	ownerPath := strings.ToLower(relative)
	for _, prefix := range []string{".specify/playbooks", ".specify/do", ".specify/runtime"} {
		if ownerPath == prefix || strings.HasPrefix(ownerPath, prefix+"/") {
			return "", fmt.Errorf("playbook_source_cannot_reference_its_runtime_state")
		}
	}
	base := strings.ToLower(path.Base(relative))
	if base == ".env" || strings.HasPrefix(base, ".env.") || strings.HasSuffix(base, ".pem") || strings.HasSuffix(base, ".key") {
		return "", fmt.Errorf("playbook_secret_source_rejected")
	}
	target, err := secureProjectPath(root, relative)
	if err != nil {
		return "", fmt.Errorf("playbook_path_crosses_link_or_project_boundary")
	}
	return target, nil
}

func playbookSourceFingerprint(root string, definition PlaybookDefinition) (map[string]string, error) {
	sources := append([]string{}, definition.SourceFiles...)
	for _, step := range definition.Steps {
		actualScripts, err := playbookActionScriptSources(root, step.Cwd, step.Argv)
		if err != nil {
			return nil, err
		}
		sources = append(sources, actualScripts...)
		if step.ScriptRef != "" {
			sources = append(sources, step.ScriptRef)
		}
	}
	for _, check := range definition.Checks {
		actualScripts, err := playbookActionScriptSources(root, check.Cwd, check.Argv)
		if err != nil {
			return nil, err
		}
		sources = append(sources, actualScripts...)
		if check.ScriptRef != "" {
			sources = append(sources, check.ScriptRef)
		}
	}
	result := map[string]string{}
	sources = uniqueSortedTrimmed(sources)
	if len(sources) > 192 {
		return nil, fmt.Errorf("playbook_source_fingerprint_invalid")
	}
	for _, source := range sources {
		target, err := playbookSafePath(root, source, false)
		if err != nil {
			return nil, err
		}
		info, err := os.Stat(target)
		if err != nil || !info.Mode().IsRegular() || info.Size() > 32*1024*1024 {
			return nil, fmt.Errorf("playbook_source_missing_nonregular_or_oversized")
		}
		raw, err := os.ReadFile(target)
		if err != nil {
			return nil, fmt.Errorf("playbook_source_unreadable")
		}
		result[source] = fileContentSHA256(raw)
	}
	return result, nil
}

func playbookCompatibility(definition PlaybookDefinition, context map[string]string) []string {
	reasons := []string{}
	for key, allowed := range definition.Applicability {
		actual, ok := context[key]
		if !ok || actual == "" {
			reasons = append(reasons, "context_missing:"+key)
			continue
		}
		matched := false
		for _, value := range allowed {
			if strings.EqualFold(value, actual) {
				matched = true
				break
			}
		}
		if !matched {
			reasons = append(reasons, "context_mismatch:"+key)
		}
	}
	sort.Strings(reasons)
	return reasons
}

func playbookReadContext(raw string) (map[string]string, error) {
	context := map[string]string{"os": runtime.GOOS, "arch": runtime.GOARCH}
	if strings.TrimSpace(raw) != "" {
		var submitted map[string]string
		if err := decodePlaybookJSON([]byte(raw), &submitted); err != nil {
			return nil, err
		}
		if len(submitted) > 24 {
			return nil, fmt.Errorf("playbook_context_invalid")
		}
		for key, value := range submitted {
			if !playbookContextKeyPattern.MatchString(key) || value == "" || len(value) > 128 || strings.ContainsAny(value, "\x00\r\n") {
				return nil, fmt.Errorf("playbook_context_invalid")
			}
			context[key] = value
		}
	}
	return context, nil
}

func playbookCanonicalPath(root, id string) (string, error) {
	if !playbookIDPattern.MatchString(id) {
		return "", fmt.Errorf("playbook_id_invalid")
	}
	target, err := secureProjectPath(root, filepath.ToSlash(filepath.Join(".specify", "playbooks", id, "playbook.json")))
	if err != nil {
		return "", fmt.Errorf("playbook_store_path_unsafe")
	}
	return target, nil
}
