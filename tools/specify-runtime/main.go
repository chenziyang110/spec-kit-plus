package main

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	goruntime "runtime"
	"sort"
	"strconv"
	"strings"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/buildinfo"
	cognitioncli "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/cli"
	runtimepaths "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
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
	case "result":
		return runResult(args[1:], stdout)
	case "run":
		return runRun(args[1:], stdout)
	case "workflow":
		return runWorkflow(args[1:], stdout)
	case "validate":
		return runValidate(args[1:], stdout)
	case "cognition":
		return runCognition(args[1:], stdout, stderr, cliVersion)
	case "discussion":
		return runDiscussion(args[1:], stdout)
	case "design":
		return runDesign(args[1:], stdout)
	case "evidence":
		return runEvidence(args[1:], stdout)
	case "doctor":
		return runDoctor(args[1:], stdout)
	case "hook":
		return runHook(args[1:], stdout)
	case "integrate":
		return runIntegrate(args[1:], stdout)
	case "tasks":
		return runTasks(args[1:], stdout)
	case "implement":
		return runImplement(args[1:], stdout)
	case "review":
		return runReview(args[1:], stdout)
	case "accept":
		return runAccept(args[1:], stdout)
	case "sp-teams":
		return runTeams(args[1:], stdout)
	case "learning":
		return runLearning(args[1:], stdout)
	case "lane":
		return runLane(args[1:], stdout)
	case "prd-build":
		return runPRDBuild(args[1:], stdout)
	case "prd-scan":
		return runPRDScan(args[1:], stdout)
	case "quick":
		return runQuick(args[1:], stdout)
	default:
		env := NewEnvelope("usage-error", fmt.Sprintf("unknown command %q", args[0]))
		return writeEnvelope(stdout, env)
	}
}

func writeHelp(stdout io.Writer) int {
	_, _ = fmt.Fprintln(stdout, "specify-runtime commands:")
	for _, name := range []string{
		"api",
		"artifact",
		"cognition",
		"discussion",
		"design",
		"doctor",
		"evidence",
		"hook",
		"integrate",
		"tasks",
		"implement",
		"review",
		"accept",
		"sp-teams",
		"learning",
		"lane",
		"prd-build",
		"prd-scan",
		"quick",
		"result",
		"run",
		"validate",
		"version",
		"workflow",
	} {
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
	case "schema":
		return runAPISchema(args[1:], stdout)
	case "show":
		return runAPIShow(args[1:], stdout)
	default:
		_ = stderr
		return writeEnvelope(stdout, NewEnvelope("usage-error", fmt.Sprintf("unknown api subcommand %q", args[0])))
	}
}

func runArtifact(args []string, stdout io.Writer) int {
	if len(args) == 0 {
		return writeEnvelope(stdout, NewEnvelope("usage-error", "missing artifact subcommand"))
	}
	if args[0] == "--help" || args[0] == "-h" || args[0] == "help" {
		return writeArtifactHelp(stdout, "")
	}
	if len(args) > 1 && (args[1] == "--help" || args[1] == "-h") {
		return writeArtifactHelp(stdout, args[0])
	}
	projectRoot := optionValue(args, "--project-root", ".")
	service := NewArtifactService(projectRoot)
	switch args[0] {
	case "catalog":
		if env, ok := validateArtifactOptions(args, "--format", "--project-root"); !ok {
			return writeEnvelope(stdout, env)
		}
		return writeEnvelope(stdout, ArtifactScaffoldCatalog())
	case "checklist":
		if env, ok := validateArtifactOptions(args, "--format", "--input-json", "--path", "--project-root"); !ok {
			return writeEnvelope(stdout, env)
		}
		pathValue := strings.TrimSpace(optionValue(args, "--path", ""))
		if pathValue == "" || !hasFlag(args, "--input-json") {
			return writeEnvelope(stdout, artifactUsageEnvelope("checklist", "artifact checklist requires --path and --input-json"))
		}
		return writeEnvelope(stdout, service.UpsertChecklist(ArtifactChecklistRequest{
			Path:      pathValue,
			InputJSON: []byte(optionValue(args, "--input-json", "")),
		}))
	case "registry":
		if env, ok := validateArtifactOptions(args, "--format", "--project-root"); !ok {
			return writeEnvelope(stdout, env)
		}
		return writeEnvelope(stdout, ArtifactTypeCatalog())
	case "list":
		if env, ok := validateArtifactOptions(args, "--format", "--limit", "--owner", "--path-prefix", "--project-root", "--type"); !ok {
			return writeEnvelope(stdout, env)
		}
		limit, err := parseArtifactPositiveInt(optionValue(args, "--limit", "50"), "--limit")
		if err != nil {
			return writeEnvelope(stdout, artifactUsageEnvelope("list", err.Error()))
		}
		env := service.ListArtifacts(ArtifactListRequest{
			PathPrefix: optionValue(args, "--path-prefix", ""),
			TypeID:     optionValue(args, "--type", ""),
			Owner:      optionValue(args, "--owner", ""),
			Limit:      limit,
		})
		return writeEnvelope(stdout, env)
	case "prepare":
		if env, ok := validateArtifactOptions(args, "--feature", "--format", "--kind", "--path", "--project-root"); !ok {
			return writeEnvelope(stdout, env)
		}
		env := service.Prepare(ArtifactPrepareRequest{
			FeatureID: optionValue(args, "--feature", ""),
			Kind:      optionValue(args, "--kind", ""),
			Path:      optionValue(args, "--path", ""),
		})
		return writeEnvelope(stdout, env)
	case "scaffold":
		if env, ok := validateArtifactOptions(args, "--format", "--kind", "--out", "--path", "--project-root", "--vars"); !ok {
			return writeEnvelope(stdout, env)
		}
		kind := strings.TrimSpace(optionValue(args, "--kind", ""))
		if kind == "" {
			return writeEnvelope(stdout, artifactUsageEnvelope("scaffold", "artifact scaffold requires --kind"))
		}
		pathValue := strings.TrimSpace(optionValue(args, "--path", ""))
		outValue := strings.TrimSpace(optionValue(args, "--out", ""))
		if pathValue != "" && outValue != "" {
			env := artifactUsageEnvelope("scaffold", "artifact scaffold accepts either --path or deprecated --out, not both")
			env.Blockers = append(env.Blockers, "use --path for the canonical invocation")
			return writeEnvelope(stdout, env)
		}
		if pathValue == "" {
			pathValue = outValue
		}
		if pathValue == "" {
			env := artifactUsageEnvelope("scaffold", "artifact scaffold requires --path")
			env.Blockers = append(env.Blockers, "use --path <project-relative-path>; --out remains a deprecated compatibility alias")
			return writeEnvelope(stdout, env)
		}
		variables := map[string]any{}
		varsJSON := optionValue(args, "--vars", "{}")
		if err := json.Unmarshal([]byte(varsJSON), &variables); err != nil {
			env := artifactUsageEnvelope("scaffold", "artifact scaffold variables are invalid")
			env.Blockers = append(env.Blockers, "--vars must be a JSON object: "+err.Error())
			return writeEnvelope(stdout, env)
		}
		if variables == nil {
			env := artifactUsageEnvelope("scaffold", "artifact scaffold variables are invalid")
			env.Blockers = append(env.Blockers, "--vars must be a JSON object")
			return writeEnvelope(stdout, env)
		}
		env := service.Scaffold(ArtifactScaffoldRequest{
			Kind:      kind,
			Path:      pathValue,
			Variables: variables,
		})
		if env.Status != "ok" {
			bindArtifactUsage(&env, "scaffold")
		}
		if outValue != "" {
			env.Data["compatibility"] = map[string]any{
				"deprecated_option": "--out",
				"replacement":       "--path",
			}
		}
		return writeEnvelope(stdout, env)
	case "submit":
		if env, ok := validateArtifactOptions(args, "--content", "--format", "--lease", "--project-root", "--recovery-file"); !ok {
			return writeEnvelope(stdout, env)
		}
		hasInlineContent := hasFlag(args, "--content")
		hasRecoveryFile := hasFlag(args, "--recovery-file")
		if hasInlineContent == hasRecoveryFile {
			return writeEnvelope(stdout, artifactUsageEnvelope("submit", "provide exactly one of --content or --recovery-file"))
		}
		leaseID := optionValue(args, "--lease", "")
		if hasRecoveryFile {
			return writeEnvelope(stdout, service.SubmitRecoveryBackup(leaseID, optionValue(args, "--recovery-file", "")))
		}
		env := service.Submit(ArtifactSubmitRequest{
			LeaseID: leaseID,
			Content: optionValue(args, "--content", ""),
		})
		return writeEnvelope(stdout, env)
	case "delete":
		if env, ok := validateArtifactOptions(args, "--format", "--lease", "--project-root"); !ok {
			return writeEnvelope(stdout, env)
		}
		leaseID := strings.TrimSpace(optionValue(args, "--lease", ""))
		if leaseID == "" {
			return writeEnvelope(stdout, artifactUsageEnvelope("delete", "artifact delete requires --lease"))
		}
		return writeEnvelope(stdout, service.Delete(ArtifactDeleteRequest{LeaseID: leaseID}))
	case "restore":
		if env, ok := validateArtifactOptions(args, "--archive", "--format", "--project-root"); !ok {
			return writeEnvelope(stdout, env)
		}
		archiveID := strings.TrimSpace(optionValue(args, "--archive", ""))
		if archiveID == "" {
			return writeEnvelope(stdout, artifactUsageEnvelope("restore", "artifact restore requires --archive"))
		}
		return writeEnvelope(stdout, service.Restore(ArtifactRestoreRequest{ArchiveID: archiveID}))
	case "patch":
		if env, ok := validateArtifactOptions(args, "--append-json", "--content", "--format", "--frontmatter-json", "--heading", "--json-pointer", "--lease", "--new-heading", "--preamble", "--project-root", "--section", "--value-json"); !ok {
			return writeEnvelope(stdout, env)
		}
		jsonMode := hasFlag(args, "--json-pointer") || hasFlag(args, "--value-json")
		sectionMode := hasFlag(args, "--section") || hasFlag(args, "--content")
		frontmatterMode := hasFlag(args, "--frontmatter-json")
		headingMode := hasFlag(args, "--heading") || hasFlag(args, "--new-heading")
		preambleMode := hasFlag(args, "--preamble")
		appendMode := hasFlag(args, "--append-json")
		modeCount := 0
		for _, enabled := range []bool{jsonMode, sectionMode, frontmatterMode, headingMode, preambleMode, appendMode} {
			if enabled {
				modeCount++
			}
		}
		if modeCount != 1 || (jsonMode && (!hasFlag(args, "--json-pointer") || !hasFlag(args, "--value-json"))) || (sectionMode && (!hasFlag(args, "--section") || !hasFlag(args, "--content"))) || (headingMode && (!hasFlag(args, "--heading") || !hasFlag(args, "--new-heading"))) {
			return writeEnvelope(stdout, artifactUsageEnvelope("patch", "choose exactly one complete patch mode: --json-pointer with --value-json, --section with --content, --frontmatter-json, --heading with --new-heading, --preamble, or --append-json"))
		}
		request := ArtifactPatchRequest{
			LeaseID:     optionValue(args, "--lease", ""),
			JSONPointer: optionValue(args, "--json-pointer", ""),
			Section:     optionValue(args, "--section", ""),
			Content:     optionValue(args, "--content", ""),
			Heading:     optionValue(args, "--heading", ""),
			NewHeading:  optionValue(args, "--new-heading", ""),
		}
		if preambleMode {
			preamble := optionValue(args, "--preamble", "")
			request.Preamble = &preamble
		}
		if jsonMode {
			if err := json.Unmarshal([]byte(optionValue(args, "--value-json", "")), &request.Value); err != nil {
				return writeEnvelope(stdout, artifactUsageEnvelope("patch", "--value-json must be valid JSON: "+err.Error()))
			}
		}
		if frontmatterMode {
			if err := json.Unmarshal([]byte(optionValue(args, "--frontmatter-json", "")), &request.Frontmatter); err != nil || request.Frontmatter == nil {
				if err == nil {
					err = fmt.Errorf("value must be a JSON object")
				}
				return writeEnvelope(stdout, artifactUsageEnvelope("patch", "--frontmatter-json is invalid: "+err.Error()))
			}
		}
		if appendMode {
			request.Append = true
			if err := json.Unmarshal([]byte(optionValue(args, "--append-json", "")), &request.AppendJSON); err != nil {
				return writeEnvelope(stdout, artifactUsageEnvelope("patch", "--append-json must be valid JSON: "+err.Error()))
			}
		}
		return writeEnvelope(stdout, service.Patch(request))
	case "show":
		if env, ok := validateArtifactOptions(args, "--feature", "--format", "--json-pointer", "--kind", "--limit", "--path", "--project-root", "--section", "--view"); !ok {
			return writeEnvelope(stdout, env)
		}
		limit := 0
		if rawLimit := strings.TrimSpace(optionValue(args, "--limit", "")); rawLimit != "" {
			var err error
			limit, err = parseArtifactPositiveInt(rawLimit, "--limit")
			if err != nil {
				return writeEnvelope(stdout, artifactUsageEnvelope("show", err.Error()))
			}
		}
		env := service.Show(ArtifactShowRequest{
			FeatureID:   optionValue(args, "--feature", ""),
			Kind:        optionValue(args, "--kind", ""),
			Path:        optionValue(args, "--path", ""),
			View:        optionValue(args, "--view", "summary"),
			JSONPointer: optionValue(args, "--json-pointer", ""),
			Section:     optionValue(args, "--section", ""),
			Limit:       limit,
		})
		return writeEnvelope(stdout, env)
	case "prune":
		if env, ok := validateArtifactOptions(args, "--format", "--limit", "--project-root"); !ok {
			return writeEnvelope(stdout, env)
		}
		limit, err := parseArtifactPositiveInt(optionValue(args, "--limit", "100"), "--limit")
		if err != nil {
			return writeEnvelope(stdout, artifactUsageEnvelope("prune", err.Error()))
		}
		return writeEnvelope(stdout, service.PruneLeases(ArtifactPruneRequest{Limit: limit}))
	default:
		return writeEnvelope(stdout, NewEnvelope("usage-error", fmt.Sprintf("unknown artifact subcommand %q", args[0])))
	}
}

func writeArtifactHelp(stdout io.Writer, subcommand string) int {
	switch subcommand {
	case "":
		_, _ = fmt.Fprintln(stdout, "specify-runtime artifact commands:")
		for _, command := range []string{"catalog", "checklist", "delete", "list", "patch", "prepare", "prune", "registry", "restore", "scaffold", "show", "submit"} {
			_, _ = fmt.Fprintf(stdout, "  %s\n", command)
		}
	case "scaffold":
		_, _ = fmt.Fprintln(stdout, "Usage: specify-runtime artifact scaffold --kind <kind> --path <project-relative-path> [--vars <json>] [--format json]")
		_, _ = fmt.Fprintln(stdout, "  --path is canonical; --out is a deprecated compatibility alias.")
		_, _ = fmt.Fprintln(stdout, "  Run specify-runtime artifact catalog --format json for registered kinds and paths.")
	case "checklist":
		_, _ = fmt.Fprintln(stdout, "Usage: specify-runtime artifact checklist --path <feature-dir>/checklists/<name>.md --input-json <object> [--format json]")
		_, _ = fmt.Fprintln(stdout, "  Creates or appends categories atomically and assigns the next CHK identifiers.")
	case "patch":
		_, _ = fmt.Fprintln(stdout, "Usage: specify-runtime artifact patch --lease <id> (--json-pointer <pointer> --value-json <json> | --section <heading> --content <text> | --frontmatter-json <object> | --heading <current> --new-heading <replacement> | --preamble <text> | --append-json <json>)")
	case "submit":
		_, _ = fmt.Fprintln(stdout, "Usage: specify-runtime artifact submit --lease <id> --content <inline-payload> [--format json]")
		_, _ = fmt.Fprintln(stdout, "  --recovery-file is reserved for a runtime-created human acceptance repair backup bound by its sibling journal.")
	case "delete":
		_, _ = fmt.Fprintln(stdout, "Usage: specify-runtime artifact delete --lease <id> [--format json]")
		_, _ = fmt.Fprintln(stdout, "  Moves a generic artifact into the runtime-owned recoverable archive.")
	case "restore":
		_, _ = fmt.Fprintln(stdout, "Usage: specify-runtime artifact restore --archive <archive-id> [--format json]")
	default:
		_, _ = fmt.Fprintf(stdout, "Usage: specify-runtime artifact %s [options]\n", subcommand)
		_, _ = fmt.Fprintln(stdout, "  Run specify-runtime api show artifact."+subcommand+" --format json for capability details.")
	}
	return 0
}

func parseArtifactPositiveInt(value, option string) (int, error) {
	parsed, err := strconv.Atoi(strings.TrimSpace(value))
	if err != nil || parsed <= 0 {
		return 0, fmt.Errorf("%s must be a positive integer", option)
	}
	return parsed, nil
}

func validateArtifactOptions(args []string, allowed ...string) (Envelope, bool) {
	allowedSet := make(map[string]bool, len(allowed))
	for _, name := range allowed {
		allowedSet[name] = true
	}
	seen := map[string]bool{}
	for index := 1; index < len(args); index++ {
		name := args[index]
		if !strings.HasPrefix(name, "--") || !allowedSet[name] {
			env := artifactUsageEnvelope(args[0], fmt.Sprintf("artifact %s options are invalid", args[0]))
			message := fmt.Sprintf("unknown option %q", name)
			if args[0] == "scaffold" {
				message += "; use --path (canonical) or --out (deprecated compatibility alias)"
			}
			env.Blockers = append(env.Blockers, message)
			return env, false
		}
		if seen[name] {
			env := artifactUsageEnvelope(args[0], fmt.Sprintf("artifact %s option %s was repeated", args[0], name))
			return env, false
		}
		seen[name] = true
		if index+1 >= len(args) {
			env := artifactUsageEnvelope(args[0], fmt.Sprintf("artifact %s option %s requires a value", args[0], name))
			return env, false
		}
		index++
	}
	return Envelope{}, true
}

func artifactUsageEnvelope(subcommand, summary string) Envelope {
	env := usageEnvelope(summary)
	bindArtifactUsage(&env, subcommand)
	return env
}

func bindArtifactUsage(env *Envelope, subcommand string) {
	if len(env.ShowArgv) == 0 {
		env.ShowArgv = []string{"specify-runtime", "api", "show", "artifact." + subcommand, "--format", "json"}
	}
	if subcommand == "scaffold" && len(env.NextArgv) == 0 {
		env.NextArgv = []string{"specify-runtime", "artifact", "catalog", "--format", "json"}
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
		raw, err := readAgentJSONInput(args, projectRoot, "workflow block")
		if err != nil {
			env := workflowInvalid("workflow block input is invalid", "invalid-block-input", err)
			return writeEnvelope(stdout, env)
		}
		request, env, ok := decodeWorkflowBlockInput(raw)
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

func decodeWorkflowBlockInput(raw []byte) (WorkflowBlockRequest, Envelope, bool) {
	var request WorkflowBlockRequest
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
	cleanArgs, persistDir, persistErr := cognitionPersistenceOption(args)
	if persistErr != nil {
		return writeEnvelope(stdout, usageEnvelope(persistErr.Error()))
	}
	args = cleanArgs
	var auditInput any
	if persistDir != "" {
		inputJSON := optionValue(args, "--input-json", "")
		if !hasFlag(args, "--input-json") || strings.TrimSpace(inputJSON) == "" {
			return writeEnvelope(stdout, usageEnvelope("cognition semantic-audit --persist-dir requires --input-json"))
		}
		if err := json.Unmarshal([]byte(inputJSON), &auditInput); err != nil {
			return writeEnvelope(stdout, usageEnvelope("cognition semantic-audit --input-json must be valid JSON when --persist-dir is used"))
		}
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
	if persistDir != "" && code == 0 && status == "ok" {
		persistence, err := persistSemanticAuditPair(persistDir, auditInput, payload)
		if err != nil {
			return writeEnvelope(stdout, errorEnvelope("semantic audit artifacts could not be persisted", err))
		}
		env.Data["persistence"] = persistence
	}
	if detail := strings.TrimSpace(rawStderr.String()); detail != "" {
		env.Blockers = append(env.Blockers, detail)
	}
	return writeEnvelope(stdout, env)
}

func cognitionPersistenceOption(args []string) ([]string, string, error) {
	if len(args) == 0 || args[0] != "semantic-audit" {
		return args, "", nil
	}
	clean := make([]string, 0, len(args))
	persistDir := ""
	for index := 0; index < len(args); index++ {
		if args[index] != "--persist-dir" {
			clean = append(clean, args[index])
			continue
		}
		if persistDir != "" {
			return nil, "", errors.New("cognition semantic-audit accepts --persist-dir only once")
		}
		if index+1 >= len(args) || strings.HasPrefix(args[index+1], "--") {
			return nil, "", errors.New("cognition semantic-audit --persist-dir requires a value")
		}
		persistDir = strings.TrimSpace(args[index+1])
		index++
	}
	if persistDir != "" {
		if filepath.IsAbs(persistDir) || filepath.VolumeName(persistDir) != "" || validateSafeRelativeSlashPath(filepath.ToSlash(persistDir)) != nil {
			return nil, "", errors.New("cognition semantic-audit --persist-dir must be a safe project-relative path")
		}
	}
	return clean, filepath.ToSlash(persistDir), nil
}

func persistSemanticAuditPair(persistDir string, input, output any) (map[string]any, error) {
	root, err := filepath.Abs(".")
	if err != nil {
		return nil, err
	}
	inputRef := filepath.ToSlash(filepath.Join(persistDir, "semantic-audit-input.json"))
	outputRef := filepath.ToSlash(filepath.Join(persistDir, "semantic-audit-output.json"))
	for ref, typeID := range map[string]string{inputRef: "semantic-audit-input", outputRef: "semantic-audit-output"} {
		metadata, ok := LookupArtifactType(ref)
		if !ok || metadata.TypeID != typeID {
			return nil, fmt.Errorf("semantic audit persistence path is not a registered %s artifact: %s", typeID, ref)
		}
	}
	inputRaw, err := marshalReviewAcceptJSON(input)
	if err != nil {
		return nil, err
	}
	outputRaw, err := marshalReviewAcceptJSON(output)
	if err != nil {
		return nil, err
	}
	inputPath, err := secureProjectPath(root, inputRef)
	if err != nil {
		return nil, err
	}
	outputPath, err := secureProjectPath(root, outputRef)
	if err != nil {
		return nil, err
	}
	receipt, err := applyFileTransaction(root, "semantic-audit-persist", []fileTransactionUpdate{
		{Path: inputPath, Content: inputRaw, Perm: 0o644},
		{Path: outputPath, Content: outputRaw, Perm: 0o644},
	})
	if err != nil {
		return nil, err
	}
	return map[string]any{
		"input_ref": inputRef, "input_sha256": fileContentSHA256(inputRaw),
		"output_ref": outputRef, "output_sha256": fileContentSHA256(outputRaw),
		"transaction_receipt_ref": receipt.ReceiptRef,
	}, nil
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
	if cwd, cwdErr := os.Getwd(); cwdErr == nil {
		executable = projectLocalRuntimeInvocation(cwd, executable)
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

func projectLocalRuntimeInvocation(cwd, fallback string) string {
	root, err := runtimepaths.FindProjectRoot(cwd)
	if err != nil {
		return fallback
	}
	executableName := "specify-runtime"
	if goruntime.GOOS == "windows" {
		executableName += ".exe"
	}
	entrypoint := filepath.Join(root, ".specify", "bin", executableName)
	info, err := os.Lstat(entrypoint)
	if err != nil || !info.Mode().IsRegular() || info.Mode()&os.ModeSymlink != 0 {
		return fallback
	}
	relative, err := filepath.Rel(cwd, entrypoint)
	if err != nil || filepath.IsAbs(relative) {
		return fallback
	}
	currentPrefix := "." + string(filepath.Separator)
	parentPrefix := ".." + string(filepath.Separator)
	if relative != "." &&
		relative != ".." &&
		!strings.HasPrefix(relative, currentPrefix) &&
		!strings.HasPrefix(relative, parentPrefix) {
		relative = "." + string(filepath.Separator) + relative
	}
	return relative
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
		"api.schema",
		"api.show",
		"artifact.catalog",
		"artifact.checklist",
		"artifact.delete",
		"artifact.list",
		"artifact.patch",
		"artifact.prepare",
		"artifact.prune",
		"artifact.registry",
		"artifact.restore",
		"artifact.scaffold",
		"artifact.show",
		"artifact.submit",
		"cognition.build-from-scan",
		"cognition.archive-incompatible-store",
		"cognition.changes",
		"cognition.claim-reconcile.apply",
		"cognition.claim-reconcile.prepare",
		"cognition.clear-dirty",
		"cognition.closeout-plan",
		"cognition.compass",
		"cognition.complete-refresh",
		"cognition.delta.append",
		"cognition.delta.begin",
		"cognition.delta.status",
		"cognition.discover",
		"cognition.expand",
		"cognition.generate-ignore",
		"cognition.init-empty",
		"cognition.lexicon",
		"cognition.mark-dirty",
		"cognition.query",
		"cognition.read",
		"cognition.record-refresh",
		"cognition.run",
		"cognition.scan-accept",
		"cognition.scan-checkpoint",
		"cognition.scan-lease",
		"cognition.scan-packet",
		"cognition.scan-prepare",
		"cognition.scan-requeue",
		"cognition.scan-set",
		"cognition.scan-status",
		"cognition.scan-yield",
		"cognition.semantic-audit",
		"cognition.semantic-audit-resume",
		"cognition.semantic-intake",
		"cognition.status",
		"cognition.update",
		"cognition.validate-build",
		"cognition.validate-scan",
		"design.approve",
		"design.export",
		"design.import",
		"design.lint",
		"design.preview",
		"design.preview-manifest",
		"design.preview-lint",
		"design.profiles",
		"design.ui-target",
		"design.ui-target-lint",
		"discussion.archive",
		"discussion.bind-consumer",
		"discussion.checkpoint",
		"discussion.close",
		"discussion.confirm-handoff",
		"discussion.init",
		"discussion.list",
		"discussion.mark-consumed",
		"discussion.mark-ready",
		"discussion.resume",
		"discussion.status",
		"discussion.validate-handoff",
		"discussion.write-handoff",
		"doctor.check",
		"evidence.allocate",
		"evidence.import",
		"evidence.register",
		"evidence.show",
		"evidence.visual-compare",
		"evidence.verify",
		"hook.extension-plan",
		"hook.validate-artifacts",
		"hook.validate-commit",
		"hook.validate-state",
		"integrate.close",
		"integrate.discover",
		"implement.closeout",
		"implement.deferral-confirm",
		"implement.deferral-propose",
		"implement.packet-compile",
		"implement.result-merge",
		"implement.resume-audit",
		"implement.task-accept",
		"implement.task-next",
		"implement.task-start",
		"implement.validation-finish",
		"implement.validation-start",
		"implement.validation-status",
		"review.closeout",
		"review.exception-confirm",
		"review.exception-propose",
		"review.prepare",
		"review.resume-audit",
		"review.target-bind",
		"review.validate",
		"run.cancel",
		"run.create",
		"run.events",
		"run.show",
		"accept.closeout",
		"accept.prepare",
		"accept.route-repair",
		"accept.validate",
		"sp-teams.auto-dispatch",
		"sp-teams.complete-batch",
		"sp-teams.doctor",
		"sp-teams.live-probe",
		"sp-teams.result-template",
		"sp-teams.status",
		"sp-teams.submit-result",
		"sp-teams.sync-back",
		"learning.capture",
		"learning.capture-auto",
		"learning.list",
		"learning.promote",
		"learning.show",
		"learning.start",
		"lane.resolve",
		"prd-build.status",
		"prd-build.scaffold",
		"prd-scan.finalize",
		"prd-scan.init",
		"prd-scan.record-list",
		"prd-scan.record-remove",
		"prd-scan.record-show",
		"prd-scan.record-upsert",
		"prd-scan.status",
		"quick.archive",
		"quick.close",
		"quick.list",
		"quick.resume",
		"quick.status",
		"result.path",
		"result.submit",
		"tasks.build",
		"tasks.finalize",
		"tasks.handoff",
		"tasks.remove",
		"tasks.set-root",
		"tasks.upsert",
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
	case "artifact.checklist":
		return "Create or append a feature checklist from compact structured input and assign stable item identifiers."
	case "artifact.delete":
		return "Move a leased generic artifact into a runtime-owned recoverable archive."
	case "artifact.restore":
		return "Restore a recoverably archived generic artifact after integrity checks."
	case "artifact.catalog":
		return "List deterministic artifact scaffold kinds and fill targets."
	case "artifact.scaffold":
		return "Create a registered, create-only workflow artifact scaffold."
	case "artifact.submit":
		return "Write inline leased artifact content atomically; file-backed input is limited to a journal-bound runtime recovery backup."
	case "artifact.patch":
		return "Patch one leased JSON pointer, Markdown section, frontmatter object, heading, or preamble atomically."
	case "artifact.list":
		return "List registered artifact instances without returning full content."
	case "discussion.bind-consumer":
		return "Bind a ready discussion digest into a runtime-owned feature compatibility pointer."
	case "review.target-bind":
		return "Atomically bind a compact reviewed runtime target, its exact identity evidence, snapshot, and digests."
	case "cognition.semantic-audit":
		return "Build a semantic routing audit and optionally persist its canonical input/output pair atomically."
	case "evidence.visual-compare":
		return "Materialize a task-bound visual comparison report from compact observed differences and captures."
	case "prd-scan.record-upsert":
		return "Create or replace one PRD scan contract record without rewriting its JSON document."
	case "prd-scan.record-remove":
		return "Remove one revision-bound PRD scan contract record atomically."
	case "prd-scan.record-show":
		return "Read one selected PRD scan contract record and its current file digest."
	case "prd-scan.record-list":
		return "List compact PRD scan contract record summaries without returning the full document."
	case "prd-build.scaffold":
		return "Create all missing PRD build documents from installed stable templates in one transaction."
	case "hook.extension-plan":
		return "Resolve enabled unconditional extension hooks without exposing project YAML to the agent."
	case "artifact.registry":
		return "List artifact types, owners, roles, schemas, and allowed operations."
	case "artifact.prune":
		return "Prune expired artifact leases."
	case "evidence.allocate":
		return "Allocate a runtime-owned evidence record and destination."
	case "evidence.import":
		return "Import a local evidence file into content-addressed storage."
	case "evidence.register":
		return "Register an inline evidence object without a temporary file."
	case "evidence.show":
		return "Read compact or full evidence metadata."
	case "evidence.verify":
		return "Verify evidence bytes and metadata against their digest."
	case "cognition.run":
		return "Run the namespaced project cognition command surface."
	case "cognition.archive-incompatible-store":
		return "Archive an incompatible cognition database using an optimistic SHA-256 guard and reset runtime status."
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
	case "run.create":
		return "Record a new isolated workflow Run request in the repository control plane."
	case "run.show":
		return "Read the current revision, status, and fence for one Run."
	case "run.events":
		return "List the ordered lifecycle events for one Run."
	case "run.cancel":
		return "Cancel one revision-bound Run and advance its fence before cleanup."
	default:
		return "Runtime capability."
	}
}
