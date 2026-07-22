package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/buildinfo"
	cognitioncli "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/cli"
)

var version = "dev"

const protocolVersion = "specify-runtime.v1"

func main() {
	os.Exit(Run(os.Args[1:], os.Stdout, os.Stderr, version))
}

func Run(args []string, stdout, stderr io.Writer, cliVersion string) int {
	if len(args) == 0 {
		return writeEnvelope(stdout, NewEnvelope("usage-error", "missing command"))
	}
	if args[0] == "--help" || args[0] == "-h" || args[0] == "help" {
		return writeHelp(stdout)
	}

	switch args[0] {
	case "version":
		return runVersion(args[1:], stdout, cliVersion)
	case "api":
		return runAPI(args[1:], stdout, stderr, cliVersion)
	case "artifact":
		return runArtifact(args[1:], stdout)
	case "workflow":
		return runWorkflow(args[1:], stdout)
	case "validate":
		return runValidate(args[1:], stdout)
	case "cognition":
		return runCognition(args[1:], stdout, stderr, cliVersion)
	default:
		env := NewEnvelope("usage-error", fmt.Sprintf("unknown command %q", args[0]))
		return writeEnvelope(stdout, env)
	}
}

func writeHelp(stdout io.Writer) int {
	_, _ = fmt.Fprintln(stdout, "specify-runtime commands:")
	for _, name := range []string{"api", "artifact", "cognition", "validate", "version", "workflow"} {
		_, _ = fmt.Fprintf(stdout, "  %s\n", name)
	}
	return 0
}

func runVersion(args []string, stdout io.Writer, cliVersion string) int {
	env := NewEnvelope("ok", "runtime version")
	env.Data["cli_version"] = cliVersion
	env.Data["protocol_version"] = protocolVersion
	info := buildinfo.Current(cliVersion)
	env.Data["source_revision"] = info.SourceRevision
	env.Data["dirty"] = info.Dirty
	env.Data["cognition_schema_version"] = info.SchemaVersion
	if wantsJSON(args) {
		return writeEnvelope(stdout, env)
	}
	_, _ = fmt.Fprintf(stdout, "specify-runtime %s\n", cliVersion)
	return 0
}

func runAPI(args []string, stdout, stderr io.Writer, cliVersion string) int {
	if len(args) == 0 {
		return writeEnvelope(stdout, NewEnvelope("usage-error", "missing api subcommand"))
	}
	switch args[0] {
	case "handshake":
		env := NewEnvelope("ok", "api handshake")
		env.Data["cli_version"] = cliVersion
		env.Data["protocol_version"] = protocolVersion
		env.Data["capability_ids"] = defaultCapabilities()
		return writeEnvelope(stdout, env)
	case "list":
		env := NewEnvelope("ok", "capability list")
		for _, card := range defaultCapabilityCards() {
			env.Items = append(env.Items, card)
		}
		return writeEnvelope(stdout, env)
	default:
		_ = stderr
		return writeEnvelope(stdout, NewEnvelope("usage-error", fmt.Sprintf("unknown api subcommand %q", args[0])))
	}
}

func runArtifact(args []string, stdout io.Writer) int {
	if len(args) == 0 {
		return writeEnvelope(stdout, NewEnvelope("usage-error", "missing artifact subcommand"))
	}
	projectRoot := optionValue(args, "--project-root", ".")
	service := NewArtifactService(projectRoot)
	switch args[0] {
	case "catalog":
		return writeEnvelope(stdout, ArtifactScaffoldCatalog())
	case "prepare":
		env := service.Prepare(ArtifactPrepareRequest{
			FeatureID: optionValue(args, "--feature", ""),
			Kind:      optionValue(args, "--kind", ""),
			Path:      optionValue(args, "--path", ""),
		})
		return writeEnvelope(stdout, env)
	case "scaffold":
		variables := map[string]any{}
		varsJSON := optionValue(args, "--vars", "{}")
		if err := json.Unmarshal([]byte(varsJSON), &variables); err != nil {
			env := NewEnvelope("usage-error", "artifact scaffold variables are invalid")
			env.Blockers = append(env.Blockers, "--vars must be a JSON object: "+err.Error())
			return writeEnvelope(stdout, env)
		}
		if variables == nil {
			env := NewEnvelope("usage-error", "artifact scaffold variables are invalid")
			env.Blockers = append(env.Blockers, "--vars must be a JSON object")
			return writeEnvelope(stdout, env)
		}
		env := service.Scaffold(ArtifactScaffoldRequest{
			Kind:      optionValue(args, "--kind", ""),
			Path:      optionValue(args, "--path", ""),
			Variables: variables,
		})
		return writeEnvelope(stdout, env)
	case "submit":
		contentFile := optionValue(args, "--content-file", "")
		var content any = optionValue(args, "--content", "")
		if contentFile != "" {
			raw, err := os.ReadFile(contentFile)
			if err != nil {
				env := NewEnvelope("blocked", "artifact content file is unavailable")
				env.Blockers = append(env.Blockers, err.Error())
				return writeEnvelope(stdout, env)
			}
			content = raw
		}
		env := service.Submit(ArtifactSubmitRequest{
			LeaseID: optionValue(args, "--lease", ""),
			Content: content,
		})
		return writeEnvelope(stdout, env)
	case "show":
		env := service.Show(ArtifactShowRequest{
			FeatureID: optionValue(args, "--feature", ""),
			Kind:      optionValue(args, "--kind", ""),
			Path:      optionValue(args, "--path", ""),
			View:      optionValue(args, "--view", "summary"),
		})
		return writeEnvelope(stdout, env)
	default:
		return writeEnvelope(stdout, NewEnvelope("usage-error", fmt.Sprintf("unknown artifact subcommand %q", args[0])))
	}
}

func runWorkflow(args []string, stdout io.Writer) int {
	if len(args) == 0 {
		return writeEnvelope(stdout, NewEnvelope("usage-error", "missing workflow subcommand"))
	}
	if args[0] == "--help" || args[0] == "-h" || args[0] == "help" {
		_, _ = fmt.Fprintln(stdout, "specify-runtime workflow commands:")
		for _, command := range []string{"show", "enter", "next", "complete-stage", "transition", "reopen", "block", "resolve", "closeout"} {
			_, _ = fmt.Fprintf(stdout, "  %s\n", command)
		}
		return 0
	}
	projectRoot := optionValue(args, "--project-root", ".")
	service := NewWorkflowService(projectRoot)
	switch args[0] {
	case "show":
		return writeEnvelope(stdout, service.Show(WorkflowShowRequest{FeatureDir: optionValue(args, "--feature-dir", "")}))
	case "enter":
		revision, env, ok := workflowRevisionOption(args, "--expected-revision", false, 0)
		if !ok {
			return writeEnvelope(stdout, env)
		}
		env = service.Enter(WorkflowEnterRequest{
			FeatureDir:       optionValue(args, "--feature-dir", ""),
			Command:          optionValue(args, "--command", "specify"),
			ExpectedRevision: revision,
			Summary:          optionValue(args, "--summary", ""),
		})
		return writeEnvelope(stdout, env)
	case "next":
		return writeEnvelope(stdout, service.Next(WorkflowShowRequest{FeatureDir: optionValue(args, "--feature-dir", "")}))
	case "complete-stage":
		revision, env, ok := workflowRevisionOption(args, "--expected-revision", true, 0)
		if !ok {
			return writeEnvelope(stdout, env)
		}
		env = service.CompleteStage(WorkflowCompleteStageRequest{
			FeatureDir:       optionValue(args, "--feature-dir", ""),
			ExpectedRevision: revision,
			Summary:          optionValue(args, "--summary", ""),
		})
		return writeEnvelope(stdout, env)
	case "transition":
		revision, env, ok := workflowRevisionOption(args, "--expected-revision", true, 0)
		if !ok {
			return writeEnvelope(stdout, env)
		}
		env = service.Transition(WorkflowTransitionRequest{
			FeatureDir:       optionValue(args, "--feature-dir", ""),
			To:               optionValue(args, "--to", ""),
			ExpectedRevision: revision,
			Summary:          optionValue(args, "--summary", ""),
		})
		return writeEnvelope(stdout, env)
	case "reopen":
		revision, env, ok := workflowRevisionOption(args, "--expected-revision", true, 0)
		if !ok {
			return writeEnvelope(stdout, env)
		}
		env = service.Reopen(WorkflowReopenRequest{
			FeatureDir:           optionValue(args, "--feature-dir", ""),
			To:                   optionValue(args, "--to", ""),
			ExpectedRevision:     revision,
			Reason:               optionValue(args, "--reason", ""),
			Evidence:             optionValues(args, "--evidence"),
			InvalidatedArtifacts: optionValues(args, "--invalidated-artifacts"),
			RepairRoute:          optionValue(args, "--repair-route", ""),
			FindingID:            optionValue(args, "--finding-id", ""),
		})
		return writeEnvelope(stdout, env)
	case "block":
		request, env, ok := readWorkflowBlockInput(projectRoot, optionValue(args, "--input", ""))
		if !ok {
			return writeEnvelope(stdout, env)
		}
		if override := optionValue(args, "--feature-dir", ""); strings.TrimSpace(override) != "" {
			request.FeatureDir = override
		}
		return writeEnvelope(stdout, service.Block(request))
	case "resolve":
		revision, env, ok := workflowRevisionOption(args, "--expected-revision", true, 0)
		if !ok {
			return writeEnvelope(stdout, env)
		}
		env = service.Resolve(WorkflowResolveRequest{
			FeatureDir:         optionValue(args, "--feature-dir", ""),
			ExpectedRevision:   revision,
			ResolutionEvidence: optionValues(args, "--resolution-evidence"),
			Summary:            optionValue(args, "--summary", ""),
		})
		return writeEnvelope(stdout, env)
	case "closeout":
		revision, env, ok := workflowRevisionOption(args, "--expected-revision", true, 0)
		if !ok {
			return writeEnvelope(stdout, env)
		}
		env = service.Closeout(WorkflowCloseoutRequest{
			FeatureDir:       optionValue(args, "--feature-dir", ""),
			ExpectedRevision: revision,
			Summary:          optionValue(args, "--summary", ""),
		})
		return writeEnvelope(stdout, env)
	default:
		return writeEnvelope(stdout, NewEnvelope("usage-error", fmt.Sprintf("unknown workflow subcommand %q", args[0])))
	}
}

func workflowRevisionOption(args []string, name string, required bool, fallback int) (int, Envelope, bool) {
	raw := optionValue(args, name, "")
	if strings.TrimSpace(raw) == "" {
		if !required {
			return fallback, Envelope{}, true
		}
		env := NewEnvelope("usage-error", fmt.Sprintf("missing required %s", name))
		env.Data["error_code"] = "invalid-argument"
		return 0, env, false
	}
	revision, err := strconv.Atoi(raw)
	if err != nil || revision < 0 {
		env := NewEnvelope("usage-error", fmt.Sprintf("%s must be a non-negative integer", name))
		env.Data["error_code"] = "invalid-argument"
		return 0, env, false
	}
	return revision, Envelope{}, true
}

func readWorkflowBlockInput(projectRoot, input string) (WorkflowBlockRequest, Envelope, bool) {
	var request WorkflowBlockRequest
	input = strings.TrimSpace(input)
	if input == "" {
		env := NewEnvelope("usage-error", "workflow block requires --input")
		env.Data["error_code"] = "invalid-block-input"
		return request, env, false
	}
	root, err := filepath.Abs(projectRoot)
	if err == nil {
		root, err = filepath.EvalSymlinks(root)
	}
	if err != nil {
		env := workflowInvalid("workflow block project root is invalid", "invalid-block-input", err)
		return request, env, false
	}
	inputPath := input
	if !filepath.IsAbs(inputPath) && filepath.VolumeName(inputPath) == "" {
		inputPath = filepath.Join(root, filepath.FromSlash(inputPath))
	}
	inputPath, err = filepath.Abs(inputPath)
	if err != nil {
		env := workflowInvalid("workflow block input path is invalid", "invalid-block-input", err)
		return request, env, false
	}
	relative, err := filepath.Rel(root, inputPath)
	if err != nil || relative == ".." || strings.HasPrefix(relative, ".."+string(filepath.Separator)) {
		env := workflowInvalid("workflow block input must stay inside the project", "invalid-block-input", fmt.Errorf("--input must be a project-root-contained JSON file"))
		return request, env, false
	}
	secureInput, err := secureProjectPath(root, filepath.ToSlash(relative))
	if err != nil || !sameFilesystemPath(secureInput, inputPath) {
		if err == nil {
			err = fmt.Errorf("input path is not canonical")
		}
		env := workflowInvalid("workflow block input path is unsafe", "invalid-block-input", err)
		return request, env, false
	}
	if !strings.EqualFold(filepath.Ext(secureInput), ".json") {
		env := workflowInvalid("workflow block input type is invalid", "invalid-block-input", fmt.Errorf("--input must name a JSON file"))
		return request, env, false
	}
	info, err := os.Stat(secureInput)
	if err != nil || !info.Mode().IsRegular() {
		if err == nil {
			err = fmt.Errorf("--input must be a regular file")
		}
		env := workflowInvalid("workflow block input is unavailable", "invalid-block-input", err)
		return request, env, false
	}
	raw, err := os.ReadFile(secureInput)
	if err != nil {
		env := workflowInvalid("workflow block input is unavailable", "invalid-block-input", err)
		return request, env, false
	}
	var fields map[string]json.RawMessage
	if err := json.Unmarshal(raw, &fields); err != nil {
		env := workflowInvalid("workflow block input is invalid", "invalid-block-input", err)
		return request, env, false
	}
	for _, required := range []string{
		"feature_dir", "expected_revision", "category", "owner", "cause", "evidence",
		"attempted_recovery", "affected_scope", "exact_next_action", "unblock_criteria",
	} {
		if _, ok := fields[required]; !ok {
			env := workflowInvalid("workflow block input is invalid", "invalid-block-input", fmt.Errorf("missing required field %q", required))
			return request, env, false
		}
	}
	decoder := json.NewDecoder(bytes.NewReader(raw))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&request); err != nil {
		env := workflowInvalid("workflow block input is invalid", "invalid-block-input", err)
		return request, env, false
	}
	if err := ensureJSONEOF(decoder); err != nil {
		env := workflowInvalid("workflow block input is invalid", "invalid-block-input", err)
		return request, env, false
	}
	return request, Envelope{}, true
}

func runValidate(args []string, stdout io.Writer) int {
	if len(args) == 0 {
		return writeEnvelope(stdout, NewEnvelope("usage-error", "missing validate subcommand"))
	}
	switch args[0] {
	case "spec":
		featureDir := optionValue(args, "--dir", "")
		if featureDir == "" {
			feature := optionValue(args, "--feature", "")
			if feature != "" {
				featureDir = filepath.Join(optionValue(args, "--project-root", "."), ".specify", "features", feature)
			}
		}
		return writeEnvelope(stdout, ValidateSpec(SpecValidationRequest{
			FeatureDir: featureDir,
			Tier:       optionValue(args, "--tier", "standard"),
			ShowPasses: hasFlag(args, "--show-passes"),
		}))
	default:
		return writeEnvelope(stdout, NewEnvelope("usage-error", fmt.Sprintf("unknown validate subcommand %q", args[0])))
	}
}

func runCognition(args []string, stdout, stderr io.Writer, cliVersion string) int {
	if containsHelpFlag(args) {
		return cognitioncli.Run(args, stdout, stderr, cliVersion)
	}

	var rawStdout bytes.Buffer
	var rawStderr bytes.Buffer
	code := cognitioncli.Run(args, &rawStdout, &rawStderr, cliVersion)
	trimmed := bytes.TrimSpace(rawStdout.Bytes())
	if len(trimmed) == 0 || !json.Valid(trimmed) {
		if rawStdout.Len() > 0 {
			_, _ = stdout.Write(rawStdout.Bytes())
		}
		if rawStderr.Len() > 0 {
			_, _ = stderr.Write(rawStderr.Bytes())
		}
		return code
	}

	var payload map[string]any
	if err := json.Unmarshal(trimmed, &payload); err != nil {
		_, _ = stdout.Write(rawStdout.Bytes())
		return code
	}
	status := cognitionEnvelopeStatus(payload, code)
	summary := "project cognition command completed"
	if status != "ok" {
		summary = "project cognition command did not complete"
	}
	env := NewEnvelope(status, summary)
	env.Data = payload
	if detail := strings.TrimSpace(rawStderr.String()); detail != "" {
		env.Blockers = append(env.Blockers, detail)
	}
	return writeEnvelope(stdout, env)
}

func containsHelpFlag(args []string) bool {
	if len(args) == 0 {
		return true
	}
	for _, arg := range args {
		if arg == "--help" || arg == "-h" {
			return true
		}
	}
	return false
}

func cognitionEnvelopeStatus(payload map[string]any, code int) string {
	if raw, ok := payload["status"].(string); ok {
		switch raw {
		case "ok", "warn", "repaired", "blocked", "repairable-block", "invalid", "usage-error", "error":
			return raw
		case "failed":
			return "blocked"
		}
	}
	switch code {
	case 0:
		return "ok"
	case 2:
		return "usage-error"
	case 10:
		return "blocked"
	default:
		return "error"
	}
}

func wantsJSON(args []string) bool {
	for i := 0; i < len(args)-1; i++ {
		if args[i] == "--format" && args[i+1] == "json" {
			return true
		}
	}
	return false
}

func optionValue(args []string, name, fallback string) string {
	for i := 0; i < len(args)-1; i++ {
		if args[i] == name {
			return args[i+1]
		}
	}
	return fallback
}

func optionValues(args []string, name string) []string {
	values := []string{}
	for index := 0; index < len(args)-1; index++ {
		if args[index] == name {
			values = append(values, args[index+1])
			index++
		}
	}
	return values
}

func hasFlag(args []string, name string) bool {
	for _, arg := range args {
		if arg == name {
			return true
		}
	}
	return false
}

func writeEnvelope(stdout io.Writer, env Envelope) int {
	bindEnvelopeRuntimeArgv(&env)
	encoder := json.NewEncoder(stdout)
	encoder.SetEscapeHTML(false)
	if err := encoder.Encode(env); err != nil {
		return 1
	}
	return ExitCodeForStatus(env.Status)
}

func bindEnvelopeRuntimeArgv(env *Envelope) {
	executable, err := os.Executable()
	if err != nil || strings.TrimSpace(executable) == "" {
		return
	}
	if absolute, absErr := filepath.Abs(executable); absErr == nil {
		executable = absolute
	}
	bind := func(argv []string) []string {
		if len(argv) > 0 && argv[0] == "specify-runtime" {
			result := append([]string{}, argv...)
			result[0] = executable
			return result
		}
		return argv
	}
	env.NextArgv = bind(env.NextArgv)
	env.ShowArgv = bind(env.ShowArgv)
	env.Data = bindRuntimeArgvValue(env.Data, executable).(map[string]any)
	env.Items = bindRuntimeArgvValue(env.Items, executable).([]any)
	env.Blockers = bindRuntimeArgvValue(env.Blockers, executable).([]any)
}

func bindRuntimeArgvValue(value any, executable string) any {
	switch typed := value.(type) {
	case map[string]any:
		result := make(map[string]any, len(typed))
		for key, item := range typed {
			result[key] = bindRuntimeArgvValue(item, executable)
		}
		return result
	case []any:
		result := make([]any, len(typed))
		for index, item := range typed {
			result[index] = bindRuntimeArgvValue(item, executable)
		}
		if len(result) > 0 && result[0] == "specify-runtime" {
			result[0] = executable
		}
		return result
	case []string:
		result := append([]string{}, typed...)
		if len(result) > 0 && result[0] == "specify-runtime" {
			result[0] = executable
		}
		return result
	default:
		return value
	}
}

func defaultCapabilities() []string {
	capabilities := []string{
		"api.handshake",
		"api.list",
		"artifact.catalog",
		"artifact.prepare",
		"artifact.scaffold",
		"artifact.show",
		"artifact.submit",
		"cognition.run",
		"validate.spec",
		"workflow.block",
		"workflow.closeout",
		"workflow.complete-stage",
		"workflow.enter",
		"workflow.next",
		"workflow.reopen",
		"workflow.resolve",
		"workflow.show",
		"workflow.transition",
	}
	sort.Strings(capabilities)
	return capabilities
}

func defaultCapabilityCards() []map[string]string {
	ids := defaultCapabilities()
	cards := make([]map[string]string, 0, len(ids))
	for _, id := range ids {
		cards = append(cards, map[string]string{
			"id":      id,
			"summary": capabilitySummary(id),
		})
	}
	return cards
}

func capabilitySummary(id string) string {
	switch id {
	case "api.handshake":
		return "Publish runtime protocol, version, and capability ids."
	case "api.list":
		return "List compact capability cards for agent discovery."
	case "artifact.prepare":
		return "Create a one-use lease for a canonical workflow artifact."
	case "artifact.catalog":
		return "List deterministic artifact scaffold kinds and fill targets."
	case "artifact.scaffold":
		return "Create a registered, create-only workflow artifact scaffold."
	case "artifact.submit":
		return "Write leased artifact content atomically."
	case "cognition.run":
		return "Run the namespaced project cognition command surface."
	case "artifact.show":
		return "Read compact or full artifact views."
	case "validate.spec":
		return "Validate core specification artifacts."
	case "workflow.show":
		return "Read the current typed workflow state."
	case "workflow.enter":
		return "Create the typed workflow state at discussion or specify."
	case "workflow.next":
		return "Resolve the exact revision-bound next workflow action."
	case "workflow.complete-stage":
		return "Validate artifacts and complete the active workflow stage."
	case "workflow.transition":
		return "Validate artifacts and advance one completed workflow stage."
	case "workflow.reopen":
		return "Reopen an invalidated earlier stage or route a guarded acceptance repair."
	case "workflow.block":
		return "Persist one structured workflow blocker."
	case "workflow.resolve":
		return "Resolve a persisted workflow blocker with evidence."
	case "workflow.closeout":
		return "Atomically bind passed human acceptance to terminal workflow state."
	default:
		return "Runtime capability."
	}
}
