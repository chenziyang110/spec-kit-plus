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
	projectRoot := optionValue(args, "--project-root", ".")
	service := NewWorkflowService(projectRoot)
	switch args[0] {
	case "start":
		env := service.Start(WorkflowStartRequest{
			FeatureID: optionValue(args, "--feature", ""),
			Stage:     optionValue(args, "--stage", "specify"),
		})
		return writeEnvelope(stdout, env)
	case "transition":
		revision, _ := strconv.Atoi(optionValue(args, "--expected-revision", "0"))
		env := service.Transition(WorkflowTransitionRequest{
			FeatureID:        optionValue(args, "--feature", ""),
			To:               optionValue(args, "--to", ""),
			ExpectedRevision: revision,
		})
		return writeEnvelope(stdout, env)
	case "status":
		return writeEnvelope(stdout, service.Status(optionValue(args, "--feature", "")))
	default:
		return writeEnvelope(stdout, NewEnvelope("usage-error", fmt.Sprintf("unknown workflow subcommand %q", args[0])))
	}
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

func hasFlag(args []string, name string) bool {
	for _, arg := range args {
		if arg == name {
			return true
		}
	}
	return false
}

func writeEnvelope(stdout io.Writer, env Envelope) int {
	encoder := json.NewEncoder(stdout)
	encoder.SetEscapeHTML(false)
	if err := encoder.Encode(env); err != nil {
		return 1
	}
	return ExitCodeForStatus(env.Status)
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
		"validate.spec",
		"workflow.start",
		"workflow.status",
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
	case "artifact.show":
		return "Read compact or full artifact views."
	case "validate.spec":
		return "Validate core specification artifacts."
	case "workflow.start":
		return "Create the typed workflow state."
	case "workflow.status":
		return "Read the current typed workflow state."
	case "workflow.transition":
		return "Advance workflow state with optimistic revision checks."
	default:
		return "Runtime capability."
	}
}
