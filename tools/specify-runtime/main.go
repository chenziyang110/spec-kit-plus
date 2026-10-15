package main

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path"
	"path/filepath"
	goruntime "runtime"
	"sort"
	"strconv"
	"strings"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/buildinfo"
	cognitioncli "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/cli"
	runtimepaths "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/scopedregistration"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/store"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/update"
)

var version = "dev"

var scopedRegistrationAfterApplyHook func(scopedregistration.Payload) error

const protocolVersion = "specify-runtime.v1"

func main() {
	args := os.Args[1:]
	timeout, err := runtimeCommandTimeout(args)
	if err != nil {
		env := NewEnvelope("usage-error", "runtime timeout configuration is invalid")
		env.Blockers = append(env.Blockers, err.Error())
		os.Exit(writeEnvelope(os.Stdout, env))
	}
	os.Exit(runWithWatchdog(args, os.Stdout, os.Stderr, buildinfo.Current(version).Version, timeout, RunContext))
}

func Run(args []string, stdout, stderr io.Writer, cliVersion string) int {
	return RunContext(context.Background(), args, stdout, stderr, cliVersion)
}

func RunContext(ctx context.Context, args []string, stdout, stderr io.Writer, cliVersion string) int {
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
	case "assets":
		return runAssets(args[1:], stdout)
	case "result":
		return runResult(args[1:], stdout)
	case "execution":
		return runExecution(args[1:], stdout)
	case "work":
		return runWork(args[1:], stdout)
	case "board":
		return runBoard(args[1:], stdout)
	case "workflow":
		return runWorkflow(args[1:], stdout)
	case "validate":
		return runValidate(args[1:], stdout)
	case "cognition":
		return runCognition(args[1:], stdout, stderr, cliVersion)
	case "discussion":
		return runDiscussion(args[1:], stdout)
	case "do":
		return runDo(args[1:], stdout)
	case "playbook":
		return runPlaybook(args[1:], stdout)
	case "design":
		return runDesign(args[1:], stdout)
	case "test-design":
		return runTestDesign(args[1:], stdout)
	case "deep-research":
		return runDeepResearch(args[1:], stdout)
	case "e2e":
		return runE2E(args[1:], stdout)
	case "evidence":
		return runEvidence(args[1:], stdout)
	case "doctor":
		return runDoctor(args[1:], stdout)
	case "hook":
		return runHook(args[1:], stdout)
	case "tasks":
		if len(args) > 1 && args[1] == "rebind" && (hasFlag(args[2:], "--help") || hasFlag(args[2:], "-h")) {
			return runAPIShow([]string{"tasks.rebind", "--format", "json"}, stdout)
		}
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
	case "prd-build":
		return runPRDBuild(args[1:], stdout)
	case "prd-scan":
		return runPRDScan(args[1:], stdout)
	case "quick":
		return runQuickWithContext(ctx, args[1:], stdout)
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
		"assets",
		"board",
		"cognition",
		"discussion",
		"do",
		"design",
		"deep-research",
		"e2e",
		"test-design",
		"doctor",
		"evidence",
		"execution",
		"hook",
		"tasks",
		"implement",
		"review",
		"accept",
		"sp-teams",
		"learning",
		"playbook",
		"prd-build",
		"prd-scan",
		"quick",
		"result",
		"validate",
		"version",
		"workflow",
		"work",
	} {
		_, _ = fmt.Fprintf(stdout, "  %s\n", name)
	}
	_, _ = fmt.Fprintln(stdout, "timeout budgets:")
	_, _ = fmt.Fprintf(stdout, "  queries: %s\n", defaultRuntimeQueryTimeout)
	_, _ = fmt.Fprintf(stdout, "  commands: %s\n", defaultRuntimeCommandTimeout)
	_, _ = fmt.Fprintf(
		stdout,
		"  override: %s accepts positive seconds up to %s and cannot disable the watchdog\n",
		runtimeTimeoutEnv,
		maxRuntimeCommandTimeout,
	)
	return 0
}

func runVersion(args []string, stdout io.Writer, cliVersion string) int {
	env := NewEnvelope("ok", "runtime version")
	info := buildinfo.Current(cliVersion)
	env.Data["cli_version"] = info.Version
	env.Data["protocol_version"] = protocolVersion
	env.Data["source_revision"] = info.SourceRevision
	env.Data["dirty"] = info.Dirty
	env.Data["cognition_schema_version"] = info.SchemaVersion
	if wantsJSON(args) {
		return writeEnvelope(stdout, env)
	}
	_, _ = fmt.Fprintf(stdout, "specify-runtime %s\n", info.Version)
	return 0
}

func runAPI(args []string, stdout, stderr io.Writer, cliVersion string) int {
	if len(args) == 0 {
		return writeEnvelope(stdout, NewEnvelope("usage-error", "missing api subcommand"))
	}
	switch args[0] {
	case "handshake":
		env := NewEnvelope("ok", "api handshake")
		info := buildinfo.Current(cliVersion)
		env.Data["cli_version"] = info.Version
		env.Data["protocol_version"] = protocolVersion
		env.Data["source_revision"] = info.SourceRevision
		env.Data["dirty"] = info.Dirty
		env.Data["capability_ids"] = defaultCapabilities()
		env.Data["capability_set_sha256"] = capabilitySetSHA256()
		return writeEnvelope(stdout, env)
	case "list":
		env := NewEnvelope("ok", "capability list")
		env.Data["capability_set_sha256"] = capabilitySetSHA256()
		for _, card := range defaultCapabilityCards() {
			env.Items = append(env.Items, card)
		}
		return writeEnvelope(stdout, env)
	case "ensure":
		return runAPIEnsure(args[1:], stdout, cliVersion)
	case "pack":
		return runAPIPack(args[1:], stdout, cliVersion)
	case "schema":
		return runAPISchema(args[1:], stdout)
	case "show":
		return runAPIShowWithQuickShadow(args[1:], stdout)
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
		inputRaw, err := resolveAgentJSONInputBytes(optionValue(args, "--input-json", ""), projectRoot, "artifact checklist")
		if err != nil {
			return writeEnvelope(stdout, artifactUsageEnvelope("checklist", err.Error()))
		}
		return writeEnvelope(stdout, service.UpsertChecklist(ArtifactChecklistRequest{
			Path:      pathValue,
			InputJSON: inputRaw,
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
	case "show-many":
		if env, ok := validateArtifactOptions(args, "--format", "--input-json", "--project-root"); !ok {
			return writeEnvelope(stdout, env)
		}
		request, env, ok := decodeArtifactShowManyCLI(args, projectRoot)
		if !ok {
			return writeEnvelope(stdout, env)
		}
		return writeEnvelope(stdout, service.ShowMany(request))
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
		contentBytes, err := resolveTextInputBytes(optionValue(args, "--content", ""), projectRoot, "artifact submit", "--content")
		if err != nil {
			return writeEnvelope(stdout, artifactUsageEnvelope("submit", err.Error()))
		}
		env := service.Submit(ArtifactSubmitRequest{
			LeaseID: leaseID,
			Content: string(contentBytes),
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
		if env, ok := validateArtifactOptions(args, "--append-json", "--content", "--format", "--frontmatter-json", "--frontmatter-pointer", "--heading", "--json-pointer", "--lease", "--new-heading", "--preamble", "--project-root", "--section", "--value-json", "--value-json-pointer"); !ok {
			return writeEnvelope(stdout, env)
		}
		jsonMode := hasFlag(args, "--json-pointer")
		frontmatterPointerMode := hasFlag(args, "--frontmatter-pointer")
		valueJSONMode := hasFlag(args, "--value-json")
		sectionMode := hasFlag(args, "--section") || hasFlag(args, "--content")
		frontmatterMode := hasFlag(args, "--frontmatter-json")
		headingMode := hasFlag(args, "--heading") || hasFlag(args, "--new-heading")
		preambleMode := hasFlag(args, "--preamble")
		appendMode := hasFlag(args, "--append-json")
		modeCount := 0
		for _, enabled := range []bool{jsonMode, frontmatterPointerMode, sectionMode, frontmatterMode, headingMode, preambleMode, appendMode} {
			if enabled {
				modeCount++
			}
		}
		pointerMode := jsonMode || frontmatterPointerMode
		if modeCount != 1 || (pointerMode && !valueJSONMode) || (!pointerMode && valueJSONMode) || (hasFlag(args, "--value-json-pointer") && !pointerMode) || (sectionMode && (!hasFlag(args, "--section") || !hasFlag(args, "--content"))) || (headingMode && (!hasFlag(args, "--heading") || !hasFlag(args, "--new-heading"))) {
			return writeEnvelope(stdout, artifactUsageEnvelope("patch", "choose exactly one complete patch mode: --json-pointer with --value-json, --frontmatter-pointer with --value-json, --section with --content, --frontmatter-json, --heading with --new-heading, --preamble, or --append-json"))
		}
		request := ArtifactPatchRequest{
			LeaseID:            optionValue(args, "--lease", ""),
			JSONPointer:        optionValue(args, "--json-pointer", ""),
			FrontmatterPointer: optionValue(args, "--frontmatter-pointer", ""),
			Section:            optionValue(args, "--section", ""),
			Content:            optionValue(args, "--content", ""),
			Heading:            optionValue(args, "--heading", ""),
			NewHeading:         optionValue(args, "--new-heading", ""),
		}
		if preambleMode {
			preambleBytes, err := resolveTextInputBytes(optionValue(args, "--preamble", ""), projectRoot, "artifact patch", "--preamble")
			if err != nil {
				return writeEnvelope(stdout, artifactUsageEnvelope("patch", err.Error()))
			}
			preamble := string(preambleBytes)
			request.Preamble = &preamble
		}
		if sectionMode {
			contentBytes, err := resolveTextInputBytes(optionValue(args, "--content", ""), projectRoot, "artifact patch", "--content")
			if err != nil {
				return writeEnvelope(stdout, artifactUsageEnvelope("patch", err.Error()))
			}
			request.Content = string(contentBytes)
		}
		if pointerMode {
			raw, err := resolveJSONInputBytesFrom(optionValue(args, "--value-json", ""), projectRoot, "artifact patch", "--value-json", os.Stdin)
			if err != nil {
				return writeEnvelope(stdout, artifactUsageEnvelope("patch", err.Error()))
			}
			if err := json.Unmarshal(raw, &request.Value); err != nil {
				return writeEnvelope(stdout, artifactUsageEnvelope("patch", "--value-json must be valid JSON: "+err.Error()))
			}
			if sourcePointer := strings.TrimSpace(optionValue(args, "--value-json-pointer", "")); sourcePointer != "" {
				selected, err := resolveJSONPointer(request.Value, sourcePointer)
				if err != nil {
					return writeEnvelope(stdout, artifactUsageEnvelope("patch", "--value-json-pointer is invalid: "+err.Error()))
				}
				request.Value = selected
			}
		}
		if frontmatterMode {
			raw, err := resolveJSONInputBytesFrom(optionValue(args, "--frontmatter-json", ""), projectRoot, "artifact patch", "--frontmatter-json", os.Stdin)
			if err != nil {
				return writeEnvelope(stdout, artifactUsageEnvelope("patch", err.Error()))
			}
			if err := json.Unmarshal(raw, &request.Frontmatter); err != nil || request.Frontmatter == nil {
				if err == nil {
					err = fmt.Errorf("value must be a JSON object")
				}
				return writeEnvelope(stdout, artifactUsageEnvelope("patch", "--frontmatter-json is invalid: "+err.Error()))
			}
		}
		if appendMode {
			request.Append = true
			raw, err := resolveJSONInputBytesFrom(optionValue(args, "--append-json", ""), projectRoot, "artifact patch", "--append-json", os.Stdin)
			if err != nil {
				return writeEnvelope(stdout, artifactUsageEnvelope("patch", err.Error()))
			}
			if err := json.Unmarshal(raw, &request.AppendJSON); err != nil {
				return writeEnvelope(stdout, artifactUsageEnvelope("patch", "--append-json must be valid JSON: "+err.Error()))
			}
		}
		return writeEnvelope(stdout, service.Patch(request))
	case "patch-batch":
		if env, ok := validateArtifactOptions(args, "--format", "--input-json", "--lease", "--project-root"); !ok {
			return writeEnvelope(stdout, env)
		}
		request, env, ok := decodeArtifactPatchBatchCLI(args, projectRoot)
		if !ok {
			return writeEnvelope(stdout, env)
		}
		return writeEnvelope(stdout, service.PatchBatch(request))
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
		for _, command := range []string{"catalog", "checklist", "delete", "list", "patch", "patch-batch", "prepare", "prune", "registry", "restore", "scaffold", "show", "show-many", "submit"} {
			_, _ = fmt.Fprintf(stdout, "  %s\n", command)
		}
	case "scaffold":
		_, _ = fmt.Fprintln(stdout, "Usage: specify-runtime artifact scaffold --kind <kind> --path <project-relative-path> [--vars <json>] [--format json]")
		_, _ = fmt.Fprintln(stdout, "  --path is canonical; --out is a deprecated compatibility alias.")
		_, _ = fmt.Fprintln(stdout, "  Run specify-runtime artifact catalog --format json for registered kinds and paths.")
	case "checklist":
		_, _ = fmt.Fprintln(stdout, "Usage: specify-runtime artifact checklist --path <feature-dir>/checklists/<name>.md --input-json <object|@path|-> [--format json]")
		_, _ = fmt.Fprintln(stdout, "  Creates or appends categories atomically and assigns the next CHK identifiers.")
		_, _ = fmt.Fprintln(stdout, "  --input-json accepts inline JSON, @path, or - (stdin). Schema: title, purpose, feature, categories[{heading,items[]}].")
	case "prepare":
		_, _ = fmt.Fprintln(stdout, "Usage: specify-runtime artifact prepare --path <project-relative-path> [--format json]")
		_, _ = fmt.Fprintln(stdout, "  Returns a one-shot lease_id for submit/patch/delete. There is no --operation flag.")
		_, _ = fmt.Fprintln(stdout, "  Optional: --feature <id> --kind <kind> --project-root <path>.")
	case "patch":
		_, _ = fmt.Fprintln(stdout, "Usage: specify-runtime artifact patch --lease <id> (--json-pointer <pointer> --value-json <json|@path|-> [--value-json-pointer <source-pointer>] | --frontmatter-pointer <pointer> --value-json <json|@path|-> [--value-json-pointer <source-pointer>] | --section <heading> --content <text|@path|-> | --frontmatter-json <object|@path|-> | --heading <current> --new-heading <replacement> | --preamble <text|@path|-> | --append-json <json|@path|->)")
		_, _ = fmt.Fprintln(stdout, "  Markdown --section must match an exact existing heading from artifact show (scaffold headings), not a free-form title.")
		_, _ = fmt.Fprintln(stdout, "  --frontmatter-pointer replaces one existing nested YAML mapping field with the selected JSON value; --value-json-pointer can select a subtree such as /reproduction from a runtime-owned sidecar.")
	case "patch-batch":
		_, _ = fmt.Fprintln(stdout, "Usage: specify-runtime artifact patch-batch --lease <id> --input-json <object|@path|-> [--format json]")
		_, _ = fmt.Fprintln(stdout, "  Applies 1..32 JSON-pointer, Markdown-section, or frontmatter operations to one leased artifact and writes only when every operation validates.")
	case "show-many":
		_, _ = fmt.Fprintln(stdout, "Usage: specify-runtime artifact show-many --input-json <object|@path|-> [--format json]")
		_, _ = fmt.Fprintln(stdout, "  Executes 1..16 bounded artifact queries and returns independent per-query status in one envelope.")
	case "submit":
		_, _ = fmt.Fprintln(stdout, "Usage: specify-runtime artifact submit --lease <id> --content <inline-payload|@path|-> [--format json]")
		_, _ = fmt.Fprintln(stdout, "  Large or Windows-sensitive content may use a project-contained @path or - for stdin; prefix literal text that begins with @ as @@.")
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
		for _, command := range []string{"show", "ensure", "enter", "next", "complete-stage", "transition", "reopen", "block", "reconcile-blocker", "resolve", "closeout"} {
			_, _ = fmt.Fprintf(stdout, "  %s\n", command)
		}
		return 0
	}
	projectRoot := optionValue(args, "--project-root", ".")
	service := NewWorkflowService(projectRoot)
	switch args[0] {
	case "show":
		return writeEnvelope(stdout, service.Show(WorkflowShowRequest{FeatureDir: optionValue(args, "--feature-dir", "")}))
	case "ensure":
		return writeEnvelope(stdout, service.Ensure(WorkflowEnterRequest{
			FeatureDir: optionValue(args, "--feature-dir", ""),
			Command:    optionValue(args, "--command", "specify"),
			Summary:    optionValue(args, "--summary", ""),
		}))
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
	case "reconcile-blocker":
		raw, err := readAgentJSONInput(args, projectRoot, "workflow reconcile-blocker")
		if err != nil {
			env := workflowInvalid("workflow blocker reconciliation input is invalid", "invalid-reconcile-blocker-input", err)
			return writeEnvelope(stdout, env)
		}
		request, env, ok := decodeWorkflowReconcileBlockerInput(raw)
		if !ok {
			return writeEnvelope(stdout, env)
		}
		if override := optionValue(args, "--feature-dir", ""); strings.TrimSpace(override) != "" {
			request.FeatureDir = override
		}
		return writeEnvelope(stdout, service.ReconcileBlocker(request))
	case "resolve":
		revision, env, ok := workflowRevisionOption(args, "--expected-revision", true, 0)
		if !ok {
			return writeEnvelope(stdout, env)
		}
		env = service.Resolve(WorkflowResolveRequest{
			FeatureDir:                 optionValue(args, "--feature-dir", ""),
			ExpectedRevision:           revision,
			ResolutionEvidence:         optionValues(args, "--resolution-evidence"),
			Summary:                    optionValue(args, "--summary", ""),
			ReopenTo:                   optionValue(args, "--reopen-to", ""),
			ReopenReason:               optionValue(args, "--reopen-reason", ""),
			ReopenEvidence:             optionValues(args, "--reopen-evidence"),
			ReopenInvalidatedArtifacts: optionValues(args, "--invalidated-artifacts"),
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

func decodeWorkflowReconcileBlockerInput(raw []byte) (WorkflowReconcileBlockerRequest, Envelope, bool) {
	var request WorkflowReconcileBlockerRequest
	var fields map[string]json.RawMessage
	if err := json.Unmarshal(raw, &fields); err != nil {
		env := workflowInvalid("workflow blocker reconciliation input is invalid", "invalid-reconcile-blocker-input", err)
		return request, env, false
	}
	for _, required := range []string{
		"feature_dir", "expected_revision", "resolved_subcauses", "remaining_cause",
		"remaining_evidence", "remaining_scope", "exact_next_action", "unblock_criteria",
	} {
		if _, ok := fields[required]; !ok {
			env := workflowInvalid("workflow blocker reconciliation input is invalid", "invalid-reconcile-blocker-input", fmt.Errorf("missing required field %q", required))
			return request, env, false
		}
	}
	decoder := json.NewDecoder(bytes.NewReader(raw))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&request); err != nil {
		env := workflowInvalid("workflow blocker reconciliation input is invalid", "invalid-reconcile-blocker-input", err)
		return request, env, false
	}
	if err := ensureJSONEOF(decoder); err != nil {
		env := workflowInvalid("workflow blocker reconciliation input is invalid", "invalid-reconcile-blocker-input", err)
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
		featureDir, err := resolveValidateSpecFeatureDir(args)
		if err != nil {
			return writeEnvelope(stdout, NewEnvelope("usage-error", err.Error()))
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

// resolveValidateSpecFeatureDir accepts --feature-dir (preferred, matches the
// rest of the runtime CLI), legacy --dir, or --feature <id> under project root.
// When both --feature-dir and --dir are set they must agree.
func resolveValidateSpecFeatureDir(args []string) (string, error) {
	featureDirFlag := strings.TrimSpace(optionValue(args, "--feature-dir", ""))
	dirFlag := strings.TrimSpace(optionValue(args, "--dir", ""))
	switch {
	case featureDirFlag != "" && dirFlag != "" && featureDirFlag != dirFlag:
		return "", fmt.Errorf("validate spec accepts either --feature-dir or --dir, not conflicting values")
	case featureDirFlag != "":
		return featureDirFlag, nil
	case dirFlag != "":
		return dirFlag, nil
	}
	feature := strings.TrimSpace(optionValue(args, "--feature", ""))
	if feature != "" {
		return filepath.Join(optionValue(args, "--project-root", "."), ".specify", "features", feature), nil
	}
	return "", nil
}

func runCognition(args []string, stdout, stderr io.Writer, cliVersion string) int {
	if len(args) > 0 && strings.EqualFold(args[0], "closeout") && (len(args) == 1 || args[1] == "--help" || args[1] == "-h") {
		env := NewEnvelope("ok", "project cognition closeout usage")
		env.Data["usage"] = "specify-runtime cognition closeout <binding begin|seal|check|apply|inspect|repair|replay> [options]"
		env.Data["binding_capability"] = "cognition.closeout.binding.v1"
		return writeEnvelope(stdout, env)
	}
	if len(args) >= 2 && strings.EqualFold(args[0], "closeout") && strings.EqualFold(args[1], "binding") {
		return runCognitionCloseoutBindingCLI(args[2:], stdout)
	}
	if len(args) >= 2 && strings.EqualFold(args[0], "closeout") && strings.EqualFold(args[1], "inspect") {
		return runCognitionCloseoutInspectCLI(args[2:], stdout)
	}
	if len(args) >= 2 && strings.EqualFold(args[0], "closeout") && strings.EqualFold(args[1], "repair") {
		return runCognitionCloseoutRepairCLI(args[2:], stdout)
	}
	if len(args) > 0 && strings.EqualFold(strings.TrimSpace(args[0]), "identity-repair") {
		return runCognitionIdentityRepairCLI(args[1:], stdout)
	}
	if len(args) >= 2 && strings.EqualFold(strings.TrimSpace(args[0]), "closeout") && strings.EqualFold(strings.TrimSpace(args[1]), "replay") {
		return runCognitionCloseoutReplayCLI(args[2:], stdout)
	}
	if len(args) > 0 && strings.EqualFold(strings.TrimSpace(args[0]), "scoped-register") {
		if code, handled := runCognitionScopedRegistrationOwnerCheck(args[1:], stdout); handled {
			return code
		}
	}
	if len(args) >= 2 && strings.EqualFold(strings.TrimSpace(args[0]), "closeout") && strings.EqualFold(strings.TrimSpace(args[1]), "apply") {
		return runCognitionCloseoutApplyCLI(args[2:], stdout)
	}
	if len(args) > 0 && strings.EqualFold(strings.TrimSpace(args[0]), "closeout-apply") {
		return runCognitionCloseoutApplyCLI(args[1:], stdout)
	}
	if containsHelpFlag(args) {
		return cognitioncli.Run(args, stdout, stderr, cliVersion)
	}
	// Shared hard-gate receipt for all mutation workflows (implement/quick/fast/debug/review).
	if len(args) > 0 && strings.EqualFold(strings.TrimSpace(args[0]), "mutation-receipt") {
		return runMutationCognitionReceiptCLI(args[1:], stdout)
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
	decoder := json.NewDecoder(bytes.NewReader(trimmed))
	decoder.UseNumber()
	if err := decoder.Decode(&payload); err != nil {
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
	if len(args) > 0 && (args[0] == "query" || args[0] == "compass" || args[0] == "lexicon") {
		env.Extra = payload
	}
	if len(args) > 0 && args[0] == "closeout-plan" {
		addCloseoutBindingPlan(env.Data, args)
	}
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

func runCognitionScopedRegistrationOwnerCheck(args []string, stdout io.Writer) (int, bool) {
	root := optionValue(args, "--project-root", ".")
	paths, err := runtimepaths.ResolvePaths(root)
	if err != nil {
		return writeEnvelope(stdout, blockedEnvelope("scoped registration blocked", err.Error())), true
	}
	input := optionValue(args, "--input-json", "")
	if strings.TrimSpace(input) == "" {
		return writeEnvelope(stdout, blockedEnvelope("scoped registration blocked", "--input-json is required")), true
	}
	raw, err := readScopedRegistrationInput(paths.Root, input)
	if err != nil {
		return writeEnvelope(stdout, blockedEnvelope("scoped registration blocked", err.Error())), true
	}
	request, canonical, err := scopedregistration.Parse(raw)
	if err != nil {
		return writeEnvelope(stdout, blockedEnvelope("scoped registration blocked", err.Error())), true
	}
	if err := preflightScopedVerifiedEvidenceCoverage(request); err != nil {
		return writeEnvelope(stdout, blockedEnvelope("scoped registration blocked", err.Error())), true
	}
	var payload scopedregistration.Payload
	var doBindingForReceipt *DoCognitionBinding
	runLocked := func() error {
		return update.WithLockedRuntime(paths, func(_ *update.LockedRuntime) error {
			basis, err := buildScopedRegistrationProofBasis(paths.Root, request)
			if err != nil {
				return err
			}
			var applyErr error
			payload, applyErr = scopedregistration.ApplyWithProofBasis(context.Background(), paths, request, canonical, basis, &scopedregistration.Guards{
				BeforeCommit: func() error {
					if strings.TrimSpace(request.Proof.Kind) == "do_native" {
						return scopedRegistrationProofSourceUnchanged(paths.Root, basis)
					}
					current, err := buildScopedRegistrationProofBasis(paths.Root, request)
					if err != nil {
						return err
					}
					if !sameScopedRegistrationProofBasis(basis, current) {
						return fmt.Errorf("native proof basis changed before scoped registration commit")
					}
					return nil
				},
			})
			if applyErr != nil {
				return applyErr
			}
			if scopedRegistrationAfterApplyHook != nil {
				if err := scopedRegistrationAfterApplyHook(payload); err != nil {
					return err
				}
			}
			if strings.TrimSpace(request.Proof.Kind) == "do_native" {
				if doBindingForReceipt == nil {
					return fmt.Errorf("Do native scoped registration lost its pre-update owner binding")
				}
				if err := scopedRegistrationProofSourceUnchanged(paths.Root, basis); err != nil {
					if driftErr := markScopedRegistrationPublicationDrift(paths, payload, request, err.Error()); driftErr != nil {
						return fmt.Errorf("native proof source changed after scoped registration publication: %w; additionally failed to mark scoped drift: %v", err, driftErr)
					}
					return fmt.Errorf("native proof source changed after scoped registration publication: %w", err)
				}
				state := "partial"
				scopeDir := filepath.Join(paths.Root, filepath.FromSlash(request.Proof.DoRef))
				_, err := recordMutationCognitionReceiptBound(scopeDir, "sp-do", request.Proof.DoRef, state, "scoped registration "+payload.Status, payload.RegistrationID, []string{"scoped-registration:" + payload.RegistrationID, "packet_sha256:" + payload.PacketSHA256}, changedPathsForDoReceipt(request), "", "", "", doBindingForReceipt)
				if err != nil {
					return err
				}
				if err := scopedRegistrationProofSourceUnchanged(paths.Root, basis); err != nil {
					if driftErr := markScopedRegistrationPublicationDrift(paths, payload, request, err.Error()); driftErr != nil {
						return fmt.Errorf("native proof source changed after scoped registration receipt publication: %w; additionally failed to mark scoped drift: %v", err, driftErr)
					}
					return fmt.Errorf("native proof source changed after scoped registration receipt publication: %w", err)
				}
				return nil
			}
			current, err := buildScopedRegistrationProofBasis(paths.Root, request)
			if err != nil || !sameScopedRegistrationProofBasis(basis, current) {
				reason := "native proof basis changed during scoped registration"
				if err != nil {
					reason = err.Error()
				}
				if driftErr := markScopedRegistrationPublicationDrift(paths, payload, request, reason); driftErr != nil {
					if err != nil {
						return fmt.Errorf("native proof changed during scoped registration: %w; additionally failed to mark scoped drift: %v", err, driftErr)
					}
					return fmt.Errorf("native proof basis changed during scoped registration; additionally failed to mark scoped drift: %v", driftErr)
				}
				if err != nil {
					return fmt.Errorf("native proof changed during scoped registration: %w", err)
				}
				return fmt.Errorf("native proof basis changed during scoped registration")
			}
			return nil
		})
	}
	var lockedErr error
	if strings.TrimSpace(request.Proof.Kind) == "do_native" {
		id, err := doCognitionScope(paths.Root, request.Proof.DoRef)
		if err != nil {
			lockedErr = err
		} else {
			release, err := doSessionLock(paths.Root, id)
			if err != nil {
				lockedErr = err
			} else {
				defer release()
				doBindingForReceipt, lockedErr = doCurrentCognitionBinding(paths.Root, id)
				if lockedErr == nil {
					lockedErr = doRegisterOwnerMetadataWritesLocked(paths.Root, id, "cognition", scopedRegistrationDoCognitionWriterPaths(paths, request.Proof.DoRef))
				}
				if lockedErr == nil {
					lockedErr = runLocked()
				}
			}
		}
	} else {
		lockedErr = runLocked()
	}
	if lockedErr != nil {
		env := blockedEnvelope("scoped registration blocked", lockedErr.Error())
		env.Data["data"] = payload
		return writeEnvelope(stdout, env), true
	}
	envStatus := "ok"
	if scopedRegistrationHasDebt(payload.ValidationDebt, "affected_closure_truncated") {
		envStatus = "warn"
	}
	env := NewEnvelope(envStatus, "project cognition scoped registration completed")
	encoded, err := json.Marshal(payload)
	if err != nil {
		return writeEnvelope(stdout, blockedEnvelope("scoped registration blocked", err.Error())), true
	}
	var data map[string]any
	decoder := json.NewDecoder(bytes.NewReader(encoded))
	decoder.UseNumber()
	if err := decoder.Decode(&data); err != nil {
		return writeEnvelope(stdout, blockedEnvelope("scoped registration blocked", err.Error())), true
	}
	env.Data = data
	return writeEnvelope(stdout, env), true
}

func scopedRegistrationProofSourceUnchanged(root string, basis scopedregistration.ProofBasis) error {
	for ref, digest := range basis.Source {
		if !strings.HasPrefix(digest, "file:") {
			continue
		}
		parts := strings.Split(digest, ":")
		if len(parts) < 2 {
			continue
		}
		want := strings.ToLower(strings.TrimSpace(parts[1]))
		if len(want) != 64 {
			continue
		}
		data, err := secureProjectReadFile(root, ref)
		if err != nil {
			return fmt.Errorf("read native proof source %s: %w", ref, err)
		}
		if got := fileContentSHA256(data); got != want {
			return fmt.Errorf("native proof source %s drifted: got %s want %s", ref, got, want)
		}
	}
	return nil
}

func markScopedRegistrationPublicationDrift(paths runtimepaths.Paths, payload scopedregistration.Payload, request scopedregistration.Request, reason string) error {
	if strings.TrimSpace(payload.ActiveGenerationID) == "" || strings.TrimSpace(payload.RegistrationID) == "" {
		return nil
	}
	st, err := store.OpenExisting(paths)
	if err != nil {
		return err
	}
	defer st.Close()
	if _, err := st.MarkClaimsStale(context.Background(), payload.Registered["claims"], "scoped_registration_postcommit_source_drift:"+payload.RegistrationID, payload.RegistrationID+":postcommit-drift"); err != nil {
		return err
	}
	status, err := runtimepaths.ReadStatus(paths)
	if err != nil {
		return err
	}
	changed := scopedRegistrationChangedPaths(request)
	debt := runtimepaths.DebtRecord{ID: "debt-" + payload.RegistrationID, Kind: "scoped_registration_postcommit_source_drift", Paths: changed, Reason: reason, UpdateID: payload.RegistrationID, OriginCommand: "cognition scoped-register"}
	status.Dirty = true
	status.Freshness = runtimepaths.StaleFreshness
	status.Readiness = runtimepaths.BlockedReadiness
	status.DirtyDebts = append(status.DirtyDebts, debt)
	status.DirtyScopePaths = uniqueSortedTrimmed(append(status.DirtyScopePaths, changed...))
	status.StalePaths = uniqueSortedTrimmed(append(status.StalePaths, changed...))
	status.DirtyReasons = uniqueSortedTrimmed(append(status.DirtyReasons, reason))
	status.StaleReasons = uniqueSortedTrimmed(append(status.StaleReasons, reason))
	status.LastUpdatePartialReasons = uniqueSortedTrimmed(append(status.LastUpdatePartialReasons, reason))
	return runtimepaths.WriteStatus(paths, status)
}

func scopedRegistrationDoCognitionWriterPaths(paths runtimepaths.Paths, doRef string) []string {
	ref := normalizeCloseoutPath(doRef)
	files := []string{
		".specify/project-cognition/status.json",
		".specify/project-cognition/project-cognition.db",
		".specify/project-cognition/project-cognition.db-wal",
		".specify/project-cognition/project-cognition.db-shm",
		".specify/project-cognition/project-cognition.db-journal",
		".specify/project-cognition/.update.lock",
		".specify/project-cognition/validate-build-receipt.json",
	}
	if ref != "" {
		files = append(files, path.Join(ref, mutationCognitionReceiptFileName))
	}
	return uniqueSortedTrimmed(files)
}

func changedPathsForDoReceipt(request scopedregistration.Request) []string {
	return scopedRegistrationChangedPaths(request)
}

func scopedRegistrationHasDebt(debts []string, want string) bool {
	for _, debt := range debts {
		if strings.TrimSpace(debt) == want {
			return true
		}
	}
	return false
}

func preflightScopedVerifiedEvidenceCoverage(request scopedregistration.Request) error {
	coveredPaths := map[string]bool{}
	for _, path := range scopedRegistrationChangedPaths(request) {
		coveredPaths[path] = true
	}
	for _, hash := range request.Source.SourceHashes {
		if path := normalizeCloseoutPath(hash.Path); path != "" {
			coveredPaths[path] = true
		}
	}
	evidencePaths := map[string]string{}
	for _, evidence := range request.Delta.Evidence {
		if strings.TrimSpace(evidence.SourceKind) == "file" {
			evidencePaths[evidence.ID] = normalizeCloseoutPath(evidence.SourcePath)
		}
	}
	for _, row := range request.Delta.Claims {
		if row.RequestedState != "verified" {
			continue
		}
		for _, evidenceID := range row.SupportingEvidenceIDs {
			path := evidencePaths[evidenceID]
			if path != "" && !coveredPaths[path] {
				return fmt.Errorf("verified claim %s evidence %s is not covered by native source proof", row.ID, evidenceID)
			}
		}
	}
	return nil
}

func markScopedRegistrationBlocked(paths runtimepaths.Paths, generationID string) error {
	generationID = strings.TrimSpace(generationID)
	if generationID == "" {
		return nil
	}
	st, err := store.OpenExisting(paths)
	if err != nil {
		return err
	}
	defer st.Close()
	return st.MarkRuntimeMetadataBlocked(context.Background(), generationID)
}

func verifyScopedRegistrationNativeProof(root string, request scopedregistration.Request) error {
	_, err := buildScopedRegistrationProofBasis(root, request)
	return err
}

func buildScopedRegistrationProofBasis(root string, request scopedregistration.Request) (scopedregistration.ProofBasis, error) {
	switch strings.TrimSpace(request.Proof.Kind) {
	case "closeout_binding":
		binding, err := requireStrongCloseoutBinding(root, request.Proof.Workflow, request.Proof.Scope, request.Proof.BindingID, "")
		if err != nil {
			return scopedregistration.ProofBasis{}, err
		}
		if err := scopedRegistrationBindingCoversPaths(binding.OwnedDelta, scopedRegistrationChangedPaths(request), "native closeout binding owned_delta"); err != nil {
			return scopedregistration.ProofBasis{}, err
		}
		return scopedregistration.ProofBasis{
			Kind:                   "closeout_binding",
			BindingID:              binding.ID,
			Workflow:               binding.Workflow,
			Scope:                  binding.Scope,
			WorkID:                 binding.WorkID,
			AttemptID:              binding.AttemptID,
			SourceRevision:         binding.AttemptID,
			Source:                 binding.Source,
			OwnedDelta:             binding.OwnedDelta,
			Digest:                 binding.Digest,
			AcceptedOutputSHA256:   binding.AcceptedOutputSHA256,
			DependencyRefs:         binding.DependencyRefs,
			RequiredDependencyRefs: binding.RequiredDependencyRefs,
		}, nil
	case "do_native":
		id, err := doCognitionScope(root, request.Proof.DoRef)
		if err != nil {
			return scopedregistration.ProofBasis{}, err
		}
		binding, err := doCurrentCognitionBinding(root, id)
		if err != nil {
			return scopedregistration.ProofBasis{}, err
		}
		if err := scopedRegistrationBindingCoversPaths(binding.ChangedPaths, scopedRegistrationChangedPaths(request), "native Do proof changed paths"); err != nil {
			return scopedregistration.ProofBasis{}, err
		}
		source, err := scopedRegistrationDoSourceProof(root, request.Proof.DoRef, binding)
		if err != nil {
			return scopedregistration.ProofBasis{}, err
		}
		return scopedregistration.ProofBasis{
			Kind:           "do_native",
			BindingID:      binding.SessionID,
			Workflow:       "sp-do",
			Scope:          request.Proof.DoRef,
			WorkID:         "work-" + binding.SessionID,
			AttemptID:      fmt.Sprintf("do-definition-%d:%s", binding.DefinitionEpoch, binding.DefinitionDigest),
			SourceRevision: binding.SourceFingerprint,
			Source:         source,
			OwnedDelta:     binding.ChangedPaths,
			Digest:         binding.SourceFingerprint,
		}, nil
	default:
		return scopedregistration.ProofBasis{}, fmt.Errorf("unsupported proof.kind %q", request.Proof.Kind)
	}
}

func scopedRegistrationDoSourceProof(root, proofRef string, binding *DoCognitionBinding) (map[string]string, error) {
	source := map[string]string{proofRef: "do-source-fingerprint:" + binding.SourceFingerprint}
	for _, changed := range binding.ChangedPaths {
		path := normalizeCloseoutPath(changed)
		if path == "" {
			continue
		}
		data, err := secureProjectReadFile(root, path)
		if err != nil {
			return nil, fmt.Errorf("read Do-owned source %s for scoped registration proof: %w", path, err)
		}
		source[path] = "file:" + fileContentSHA256(data) + ":do-native"
	}
	return source, nil
}

func scopedRegistrationBindingCoversPaths(ownedPaths, changed []string, label string) error {
	owned := map[string]bool{}
	for _, path := range ownedPaths {
		owned[normalizeCloseoutPath(path)] = true
	}
	for _, path := range changed {
		if path != "" && !owned[path] {
			return fmt.Errorf("%s does not cover changed path %s", label, path)
		}
	}
	return nil
}

func sameScopedRegistrationProofBasis(left, right scopedregistration.ProofBasis) bool {
	return string(canonicalScopedRegistrationProofBasis(left)) == string(canonicalScopedRegistrationProofBasis(right))
}

func canonicalScopedRegistrationProofBasis(value scopedregistration.ProofBasis) []byte {
	data, _ := json.Marshal(value)
	var normalized any
	decoder := json.NewDecoder(bytes.NewReader(data))
	decoder.UseNumber()
	if err := decoder.Decode(&normalized); err != nil {
		return data
	}
	canonical, err := json.Marshal(normalized)
	if err != nil {
		return data
	}
	return canonical
}

func scopedRegistrationChangedPaths(request scopedregistration.Request) []string {
	seen := map[string]bool{}
	out := []string{}
	add := func(value string) {
		path := normalizeCloseoutPath(value)
		if path != "" && !seen[path] {
			seen[path] = true
			out = append(out, path)
		}
	}
	for _, change := range request.Delta.ChangedPaths {
		add(change.Path)
		add(change.OldPath)
	}
	for _, row := range request.Delta.PathIndex {
		add(row.Path)
	}
	sort.Strings(out)
	return out
}

func readScopedRegistrationInput(root, input string) ([]byte, error) {
	input = strings.TrimSpace(input)
	if input == "-" {
		return io.ReadAll(os.Stdin)
	}
	if strings.HasPrefix(input, "@") {
		ref := strings.TrimSpace(strings.TrimPrefix(input, "@"))
		if ref == "" {
			return nil, fmt.Errorf("@path must not be empty")
		}
		return secureProjectReadFile(root, filepath.ToSlash(ref))
	}
	return []byte(input), nil
}

func normalizeCloseoutPath(value string) string {
	value = filepath.ToSlash(strings.TrimSpace(value))
	for strings.HasPrefix(value, "./") {
		value = strings.TrimPrefix(value, "./")
	}
	return strings.TrimRight(value, "/")
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
		if typed == nil {
			return typed
		}
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
		"api.ensure",
		"api.list",
		"api.pack",
		"api.schema",
		"api.show",
		"artifact.catalog",
		"artifact.checklist",
		"artifact.delete",
		"artifact.list",
		"artifact.patch",
		"artifact.patch-batch",
		"artifact.prepare",
		"artifact.prune",
		"artifact.registry",
		"artifact.restore",
		"artifact.scaffold",
		"artifact.show",
		"artifact.show-many",
		"assets.route",
		"assets.explain",
		"assets.check",
		"assets.migrate.plan",
		"assets.migrate.apply",
		"assets.catalog.find",
		"assets.catalog.get",
		"assets.catalog.put",
		"assets.catalog.check",
		"board.owner",
		"board.branch-policy",
		"board.feature-bootstrap",
		"board.reconcile",
		"board.show",
		"artifact.submit",
		"cognition.build-from-scan",
		"cognition.archive-incompatible-store",
		"cognition.changes",
		"cognition.claim-reconcile.apply",
		"cognition.claim-reconcile.prepare",
		"cognition.clear-dirty",
		"cognition.closeout",
		"cognition.closeout.apply",
		"cognition.closeout.inspect",
		"cognition.closeout.repair",
		"cognition.closeout.replay",
		"cognition.closeout.recovery.v1",
		"cognition.closeout.binding.v1",
		"cognition.closeout.binding.begin",
		"cognition.closeout.binding.seal",
		"cognition.closeout.binding.check",
		"cognition.worker-delta.v1",
		"cognition.closeout-plan",
		"cognition.compass",
		"cognition.complete-refresh",
		"cognition.confirm-ignore",
		"cognition.mutation-receipt",
		"cognition.delta.append",
		"cognition.delta.begin",
		"cognition.delta.status",
		"cognition.discover",
		"cognition.expand",
		"cognition.expansion.snapshot.v2",
		"cognition.claim-evidence.page.v1",
		"cognition.catalog.snapshot.v1",
		"cognition.generate-ignore",
		"cognition.init-empty",
		"cognition.identity-repair",
		"cognition.identity-repair.apply",
		"cognition.identity-repair.plan",
		"cognition.lexicon",
		"cognition.mark-dirty",
		"cognition.query",
		"cognition.read",
		"cognition.record-refresh",
		"cognition.run",
		"cognition.scan-accept",
		"cognition.scan-checkpoint",
		"cognition.scan-formats",
		"cognition.scan-lease",
		"cognition.scan-packet",
		"cognition.scan-policy-confirm",
		"cognition.scan-policy-stage",
		"cognition.scan-prepare",
		"cognition.scan-requeue",
		"cognition.scan-set",
		"cognition.scan-status",
		"cognition.scan-yield",
		"cognition.semantic-audit",
		"cognition.semantic-audit-resume",
		"cognition.semantic-intake",
		"cognition.scoped-register",
		"cognition.scoped-registration.v1",
		"cognition.status",
		"cognition.scope-availability.v2",
		"cognition.update",
		"cognition.validate-build",
		"cognition.validate-scan",
		"design.approve",
		"design.adopt",
		"design.adoption",
		"design.change",
		"design.direction-confirm",
		"design.diff",
		"design.impact",
		"design.export",
		"design.import",
		"design.iterate",
		"design.lint",
		"design.preview",
		"design.preview-manifest",
		"design.preview-lint",
		"design.prompt",
		"design.profiles",
		"design.register",
		"design.resolve",
		"design.ui-target",
		"design.ui-target-lint",
		"deep-research.audit-accept",
		"deep-research.audit-prepare",
		"deep-research.init",
		"deep-research.not-needed",
		"deep-research.publish",
		"deep-research.status",
		"deep-research.synthesize",
		"deep-research.track-accept",
		"deep-research.track-lease",
		"deep-research.track-prepare",
		"deep-research.track-reject",
		"deep-research.track-submit",
		"deep-research.track-yield",
		"deep-research.validate",
		"deep-research.verify-handoff",
		"e2e.init",
		"e2e.status",
		"e2e.compact",
		"e2e.task-show",
		"e2e.scope-add",
		"e2e.task-start",
		"e2e.task-submit",
		"e2e.review-start",
		"e2e.review-submit",
		"e2e.task-accept",
		"e2e.reopen",
		"e2e.close",
		"test-design.audit-prepare",
		"test-design.handoff",
		"test-design.gap-reconcile",
		"test-design.init",
		"test-design.lane-accept",
		"test-design.lane-checkpoint",
		"test-design.lane-lease",
		"test-design.lane-prepare",
		"test-design.lane-yield",
		"test-design.projection-build",
		"test-design.projection-verify",
		"test-design.publish",
		"test-design.recover",
		"test-design.status",
		"test-design.synthesize",
		"test-design.universe-build",
		"test-design.validate",
		"discussion.archive",
		"discussion.bind-consumer",
		"discussion.checkpoint",
		"discussion.close",
		"discussion.confirm-handoff",
		"discussion.init",
		"discussion.import-material",
		"discussion.list",
		"discussion.mark-consumed",
		"discussion.mark-ready",
		"discussion.resolve",
		"discussion.read-material",
		"discussion.resume",
		"discussion.status",
		"discussion.validate-handoff",
		"discussion.write-handoff",
		"doctor.check",
		"do.start",
		"do.prepare",
		"do.next",
		"do.complete",
		"do.record",
		"do.validate",
		"do.finish",
		"do.resume",
		"do.show",
		"playbook.find",
		"playbook.show",
		"playbook.update",
		"playbook.validate",
		"playbook.metrics",
		"evidence.allocate",
		"evidence.import",
		"evidence.register",
		"evidence.show",
		"evidence.smoothness-manifest",
		"evidence.smoothness-validate",
		"evidence.source-continuity-manifest",
		"evidence.source-continuity-adapter-catalog",
		"evidence.source-continuity-adapter-bridge",
		"evidence.source-continuity-adapter-probe",
		"evidence.source-continuity-adapter-plan",
		"evidence.source-continuity-adapter-execution",
		"evidence.source-continuity-validate",
		"evidence.visual-compare",
		"evidence.verify",
		"execution.announce",
		"execution.checkpoint",
		"execution.complete",
		"execution.control",
		"execution.guard",
		"execution.overview",
		"execution.show",
		"hook.extension-plan",
		"hook.validate-artifacts",
		"hook.validate-commit",
		"hook.validate-state",
		"implement.closeout",
		"implement.deferral-confirm",
		"implement.deferral-propose",
		"implement.packet-compile",
		"implement.result-merge",
		"implement.resume-audit",
		"implement.task-accept",
		"implement.task-next",
		"implement.task-reopen",
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
		"result.path",
		"result.submit",
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
		"learning.applicability.v1",
		"learning.capture",
		"learning.capture-auto",
		"learning.list",
		"learning.metrics",
		"learning.promote",
		"learning.review",
		"learning.show",
		"learning.start",
		"learning.status",
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
		"quick.checkpoint-confirm",
		"quick.checkpoint-show",
		"quick.checkpoint-stage",
		"quick.allow-inline",
		"quick.close",
		"quick.cognition-closeout",
		"quick.item-accept",
		"quick.item-start",
		"quick.item-status",
		"quick.list",
		"quick.packet-compile",
		quickShadowCapability,
		"quick.preflight",
		"quick.resume",
		"quick.status",
		"tasks.build",
		"tasks.finalize",
		"tasks.handoff",
		"tasks.rebind",
		"tasks.remove",
		"tasks.set-root",
		"tasks.upsert",
		"validate.spec",
		"workflow.block",
		"workflow.closeout",
		"workflow.complete-stage",
		"workflow.enter",
		"workflow.ensure",
		"workflow.next",
		"workflow.reopen",
		"workflow.reconcile-blocker",
		"workflow.resolve",
		"workflow.show",
		"workflow.transition",
		"work.abandon",
		"work.begin",
		"work.block",
		"work.unblock",
		"work.claim",
		"work.checkpoint",
		"work.finish",
		"work.interrupt",
		"work.resume",
		"work.scope-add",
		"work.show",
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
	if summary, ok := assetCapabilitySummary(id); ok {
		return summary
	}
	if descriptor, ok := e2eCapabilityDescriptor(id); ok {
		return descriptor["summary"].(string)
	}
	switch id {
	case "do.prepare":
		return "Prepare exact parameterized method inputs without creating workflow state."
	case "do.next":
		return "Return frozen next-action packets after checking current dependency evidence."
	case "do.complete":
		return "Validate, persist the verified method and close knowledge with resumable owner stages."
	case "playbook.metrics":
		return "Read observed attempts, failures and timing by exact task/environment/evidence group."
	case "do.start":
		return "Freeze a project operation, required checks, method revision, source fingerprints, and Work ownership."
	case "do.record":
		return "Checkpoint native-tool starts and observed outcomes without executing the operation inside the runtime."
	case "do.validate":
		return "Verify required operation evidence, source bindings, current outputs, and mutation closeout."
	case "do.finish":
		return "Close execution and knowledge persistence separately with revision checks."
	case "do.resume":
		return "Recover or explicitly replan a failed operation while preserving definition epochs, attempts, and scoped ownership."
	case "do.show":
		return "Read one operation session or resolve an unambiguous active Work binding."
	case "playbook.find":
		return "Find bounded project method cards using applicability filters and aliases."
	case "playbook.show":
		return "Expand selected method sections with current source drift information."
	case "playbook.update":
		return "Publish an execution-verified method revision or retain an unverified proposal."
	case "playbook.validate":
		return "Validate method structure, current applicability, and source fingerprints."
	case quickShadowCapability:
		return quickShadowSummary
	case "api.handshake":
		return "Publish runtime protocol, version, and capability ids."
	case "api.ensure":
		return "Check whether one compact capability requirement set is present on this runtime."
	case "api.list":
		return "List compact capability cards for agent discovery."
	case "api.pack":
		return "Return a bounded compact descriptor pack for selected capabilities."
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
	case "artifact.patch-batch":
		return "Patch one leased artifact with a bounded atomic batch of JSON-pointer, Markdown-section, or frontmatter operations."
	case "artifact.list":
		return "List registered artifact instances without returning full content."
	case "artifact.show-many":
		return "Execute multiple bounded artifact reads in one compact envelope."
	case "discussion.bind-consumer":
		return "Pin a confirmed source with --intake before Spec compilation, or finalize its compiled coverage into a ready feature pointer."
	case "discussion.resolve":
		return "Resolve one explicit discussion focus or downstream consumer binding without guessing among parallel discussions."
	case "discussion.checkpoint":
		return "Persist a durable discussion checkpoint and semantic turn_packet fields."
	case "discussion.import-material":
		return "Import a complete UTF-8 source snapshot and derive bounded reading units."
	case "discussion.read-material":
		return "Return one complete source unit and atomically record its delivery receipt."
	case "discussion.write-handoff":
		return "Materialize the canonical discussion handoff contract from a semantic draft."
	case "review.target-bind":
		return "Atomically bind a compact reviewed runtime target, its exact identity evidence, snapshot, and digests."
	case "cognition.semantic-audit":
		return "Build a semantic routing audit and optionally persist its canonical input/output pair atomically."
	case "cognition.confirm-ignore":
		return "Activate only user-confirmed starter cognition-ignore suggestions."
	case "cognition.scan-formats":
		return "Inventory repository-specific file-format cohorts before scan boundary decisions."
	case "cognition.scan-policy-stage":
		return "Validate and stage an Agent-authored cohort policy for user review."
	case "cognition.scan-policy-confirm":
		return "Bind user confirmation to one exact staged scan-policy digest."
	case "evidence.visual-compare":
		return "Materialize a task-bound visual comparison report from compact observed differences and captures."
	case "evidence.smoothness-manifest":
		return "Materialize a task-bound Smoothness Lab manifest from the current immutable task contract."
	case "evidence.smoothness-validate":
		return "Validate Smoothness Lab observations and materialize a passing task-bound report."
	case "evidence.source-continuity-manifest":
		return "Materialize a task-bound Source Continuity Lab manifest from the current immutable UI contract."
	case "evidence.source-continuity-adapter-catalog":
		return "List the embedded generic Source Continuity provider packs and their byte-bound registry identity."
	case "evidence.source-continuity-adapter-bridge":
		return "Map the live session tool inventory to provider bindings and atomically materialize inventory, probe, and plan artifacts."
	case "evidence.source-continuity-adapter-probe":
		return "Route available tool bindings through the provider registry and atomically materialize a complete Adapter Plan."
	case "evidence.source-continuity-adapter-plan":
		return "Materialize a generic capability-routed Source Continuity Adapter Plan with a bounded action space and evidence ownership."
	case "evidence.source-continuity-adapter-execution":
		return "Compile the current Adapter Plan into deterministic per-provider execution packets without executable command fields."
	case "evidence.source-continuity-validate":
		return "Validate adapter observations for source discovery, target reachability, business outcomes, side effects, final states, and asset fidelity."
	case "design.change":
		return "Create a scoped UI design-change workspace and draft index record."
	case "design.direction-confirm":
		return "Record an explicit non-consumable direction checkpoint for one exact draft concept round."
	case "design.import":
		return "Import an external image into one immutable draft design round."
	case "design.prompt":
		return "Prepare the runtime-owned prompt and generation binding for one draft image round."
	case "design.iterate":
		return "Create a digest-pinned successor of one immutable UI design change."
	case "design.resolve":
		return "Discover active UI design candidates for one scope without adopting them."
	case "design.diff":
		return "Compare immutable UI design changes by lineage, scope, decisions, and handoff contracts."
	case "design.impact":
		return "Preview scope-bounded consumer reconciliation without changing workflow artifacts."
	case "design.register":
		return "Register an approved change-local UI contract as immutable consumption truth."
	case "design.adopt":
		return "Record a compare-and-swap consumer adoption of one exact UI design binding."
	case "design.adoption":
		return "Verify a post-Specify UI design overlay against the unchanged source specification."
	case "deep-research.init":
		return "Initialize a runtime-owned, source-bound Deep Research workspace."
	case "deep-research.status":
		return "Show resumable Deep Research state, freshness, track counts, and next action."
	case "deep-research.track-prepare":
		return "Freeze bounded research tracks that cover every selected capability."
	case "deep-research.track-lease":
		return "Lease one pending research track to an independent worker."
	case "deep-research.track-submit":
		return "Validate and materialize one track result plus canonical evidence objects."
	case "deep-research.track-accept":
		return "Accept a digest-bound track result after evidence and source verification."
	case "deep-research.track-reject":
		return "Preserve a submitted result as a rejection record and requeue its one allowed retry."
	case "deep-research.track-yield":
		return "Release a track lease while preserving its resumable attempt history."
	case "deep-research.synthesize":
		return "Close capability, evidence, contradiction, spike, and planning-handoff coverage."
	case "deep-research.audit-prepare":
		return "Freeze an independent audit request over the exact accepted research corpus."
	case "deep-research.audit-accept":
		return "Record an identity-separated audit result for every required research check."
	case "deep-research.validate":
		return "Validate source freshness, canonical closure, evidence integrity, and audit acceptance."
	case "deep-research.publish":
		return "Publish a digest-bound, Plan-consumable Deep Research handoff."
	case "deep-research.verify-handoff":
		return "Fail closed unless the published handoff and every bound artifact remain current."
	case "deep-research.not-needed":
		return "Publish an evidence-backed no-research-needed disposition without inventing findings."
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
	case "test-design.init":
		return "Initialize a runtime-owned project or feature test-design workspace."
	case "test-design.recover":
		return "CAS-reenter the current test-design root from its runtime-owned boundary without inline payload reconstruction."
	case "test-design.status":
		return "Show resumable test-design state, lane counts, exact recovery action, and next action."
	case "test-design.universe-build":
		return "Freeze and validate the current test universe against its declared sources."
	case "test-design.lane-prepare":
		return "Create bounded discovery lanes from leader-authored structured input."
	case "test-design.lane-checkpoint":
		return "Validate and persist one packet-local cumulative worker checkpoint."
	case "test-design.lane-lease":
		return "Lease one pending test-design lane and return its runtime-owned packet."
	case "test-design.lane-yield":
		return "Release a leased lane while preserving its accepted checkpoint cursor."
	case "test-design.lane-accept":
		return "Validate and accept one worker proposal without granting global completeness."
	case "test-design.gap-reconcile":
		return "CAS-upsert leader-confirmed worker gap proposals and reconcile their TO/COV links."
	case "test-design.synthesize":
		return "Join accepted discovery proposals into the canonical test-intelligence bundle."
	case "test-design.audit-prepare":
		return "Create an independent audit lane bound to exact source and artifact digests."
	case "test-design.validate":
		return "Validate freshness, traceability, data hygiene, audit closure, and claim status."
	case "test-design.publish":
		return "Publish one consumer-neutral, pointer-only binding for a validated test-design bundle."
	case "test-design.projection-build":
		return "Derive a digest-bound consumer projection and return its exact verification action."
	case "test-design.projection-verify":
		return "Verify the complete projection chain and return to the selected consumer."
	case "test-design.handoff":
		return "Atomically publish the Tasks pointer handoff and continue to publication before Tasks."
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
	case "execution.control":
		return "Own the announced-to-completed Activity lifecycle, atomic file and semantic-resource guard, checkpoints, recovery, and actual-change completion audit."
	case "execution.announce":
		return "Announce one Activity, candidate file scope, semantic resources, and Git baseline before mutation."
	case "execution.checkpoint":
		return "Advance an Activity phase and atomically persist its lease, next action, and observed paths."
	case "execution.guard":
		return "Atomically claim confirmed file and semantic scope, including audited causal packet amendments, against one exact execution overview snapshot."
	case "execution.show":
		return "Read one registered Activity with its Work, write intents, semantic resources, and lifecycle receipts."
	case "execution.complete":
		return "Audit actual Git changes and passing validation before atomically completing Activity and Work."
	case "execution.overview":
		return "Join open task state, nonterminal Runs, live Work identities, write scope, and coordination anomalies into one repository view."
	case "cognition.run":
		return "Run the namespaced project cognition command surface."
	case "cognition.scoped-register", "cognition.scoped-registration.v1":
		return "Atomically register bounded current cognition facts into the active generation without whole-graph replacement."
	case "cognition.expansion.snapshot.v2":
		return "Read an immutable expansion only while its complete graph and runtime-status snapshot remains current."
	case "cognition.scope-availability.v2":
		return "Reassess exact task read/write/dependency scope separately from visible global cognition debt."
	case "cognition.claim-evidence.page.v1":
		return "Read bounded claim-evidence pages with exact counts and snapshot-bound continuation."
	case "cognition.catalog.snapshot.v1":
		return "Page the alias catalog with graph, status, and request revision checks."
	case "cognition.archive-incompatible-store":
		return "Archive an incompatible cognition database using an optimistic SHA-256 guard and reset runtime status."
	case "artifact.show":
		return "Read compact or full artifact views."
	case "validate.spec":
		return "Validate core specification artifacts."
	case "workflow.show":
		return "Read the current typed workflow state."
	case "workflow.ensure":
		return "Show the typed workflow state or create it idempotently when absent."
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
	case "workflow.reconcile-blocker":
		return "Remove proven-stale blocker subcauses while preserving the unresolved blocker and its audit."
	case "workflow.block":
		return "Persist one structured workflow blocker."
	case "workflow.resolve":
		return "Resolve a persisted workflow blocker with evidence and optionally reopen a strict earlier stage atomically."
	case "workflow.closeout":
		return "Atomically bind passed human acceptance to terminal workflow state."
	case "cognition.mutation-receipt":
		return "Record a durable project-cognition mutation closeout receipt required before implement/quick/review terminal close."
	case "cognition.closeout.apply":
		return "Run the shared mutation closeout sequence: bounded update, build validation, eligible finalization, and runtime-bound receipt."
	case "cognition.closeout.inspect":
		return "Inspect exact pending closeout intents and their recovery routes without changing state."
	case "cognition.closeout.repair":
		return "Repair verification on an uncommitted intent with digest checks, preserved input, and a durable replacement."
	case "cognition.closeout":
		return "Operate the shared project-cognition closeout namespace, including digest-bound replay."
	case "cognition.closeout.replay":
		return "Replay one exact digest-bound pending intent, or the intent bound to a legacy blocked scope receipt."
	case "cognition.closeout.recovery.v1":
		return "Recover an exact current cognition closeout intent without replacing its source basis."
	case "cognition.closeout.binding.v1", "cognition.closeout.binding.begin", "cognition.closeout.binding.seal", "cognition.closeout.binding.check":
		return "Bind exact native Work, source bytes, actual owned delta, dependencies, validation observations and accepted-output versions."
		return "Require exact pending-intent recovery before a standalone receipt or terminal workflow close."
	case "cognition.worker-delta.v1":
		return "Preserve versioned worker cognition candidates, submission history and exact result acceptance for leader closeout planning."
	case "cognition.identity-repair.plan":
		return "Prepare a digest-bound bounded path identity repair from current validation evidence."
	case "cognition.identity-repair":
		return "Operate the bounded project-cognition identity-repair plan/apply namespace."
	case "cognition.identity-repair.apply":
		return "Apply a current-evidence-bound path identity repair and revalidate query readiness."
	case "implement.result-merge":
		return "Merge a leader-submitted WorkerTaskResult with validation_results into task lifecycle state."
	case "tasks.rebind":
		return "Refresh Test Design bindings and pending UI contracts while preserving accepted/deferred task history."
	case "implement.task-start":
		return "Atomically claim a task's expected write scope before starting its implementation lifecycle."
	case "implement.task-reopen":
		return "Reopen one non-acceptance-ready implemented task with revision guards and immutable audit history."
	case "board.show":
		return "List the durable repository Work Board with task ownership and declared write intents."
	case "quick.preflight":
		return "Provide the Quick-scoped compatibility view over unfinished tasks, Work ownership, and legacy overlap signals."
	case "board.owner":
		return "Find active or recovery-held work whose declared write scope overlaps one path."
	case "board.reconcile":
		return "Interrupt expired work leases and preserve dirty scopes behind recovery holds."
	case "board.branch-policy":
		return "Keep the current feature branch when another live task or dirty recovery hold exists."
	case "board.feature-bootstrap":
		return "Register the exact feature directory before creation and return its branch policy."
	case "work.begin":
		return "Register one agent task and its planned write scope on the shared Work Board."
	case "work.claim":
		return "Atomically claim one modifying workflow's complete write scope before source writes."
	case "work.scope-add":
		return "Atomically expand a revision-bound task write scope after conflict checking."
	case "work.checkpoint":
		return "Renew a task lease and record its next action and observed changed paths."
	case "work.block":
		return "Mark active work blocked without releasing its declared write scope."
	case "work.unblock":
		return "Resume live blocked work under the same owner and fence without interrupting the session."
	case "work.finish":
		return "Complete one task and release its write scope while retaining history."
	case "work.abandon":
		return "Abandon one task and release its write scope while retaining history."
	case "work.interrupt":
		return "Fence a confirmed-ended owner session and preserve dirty scope for immediate recovery."
	case "work.resume":
		return "Resume interrupted work under a new fence after conflict checking."
	case "work.show":
		return "Read one Work Board item and its declared write intents."
	default:
		return "Runtime capability."
	}
}
