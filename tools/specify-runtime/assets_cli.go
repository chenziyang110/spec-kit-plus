package main

import (
	"bytes"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"strings"
)

type assetCLIPaths []string

func (paths *assetCLIPaths) String() string { return strings.Join(*paths, ",") }
func (paths *assetCLIPaths) Set(value string) error {
	if strings.TrimSpace(value) == "" {
		return fmt.Errorf("asset paths must not be empty")
	}
	*paths = append(*paths, value)
	return nil
}

func runAssets(args []string, stdout io.Writer) int {
	if len(args) == 0 {
		return writeEnvelope(stdout, assetCLIUsage("", "missing assets subcommand"))
	}
	if args[0] == "help" || args[0] == "--help" || args[0] == "-h" {
		_, _ = fmt.Fprintln(stdout, "specify-runtime assets commands: route, explain, check, migrate plan, migrate apply, catalog find|get|put|check")
		_, _ = fmt.Fprintln(stdout, "Use assets <command> --help or api show assets.<command> --format json for the exact contract.")
		return 0
	}
	command := args[0]
	args = args[1:]
	if command == "migrate" || command == "catalog" {
		if len(args) == 0 || strings.HasPrefix(args[0], "-") {
			return writeEnvelope(stdout, assetCLIUsage(command, "specify an assets "+command+" operation"))
		}
		command += "." + args[0]
		args = args[1:]
	}
	if _, ok := assetCapabilitySummary("assets." + command); !ok {
		return writeEnvelope(stdout, assetCLIUsage(command, "unknown assets command"))
	}
	if len(args) == 1 && (args[0] == "--help" || args[0] == "-h") {
		return runAPIShow([]string{"assets." + command, "--format", "json"}, stdout)
	}
	flags := flag.NewFlagSet("assets "+command, flag.ContinueOnError)
	flags.SetOutput(io.Discard)
	projectRoot := flags.String("project-root", ".", "project root")
	format := flags.String("format", "json", "JSON envelope")
	policy := flags.String("policy", "", "explicit project-relative policy")
	var route AssetRouteRequest
	var check AssetCheckRequest
	var paths, deletedPaths assetCLIPaths
	var catalog AssetCatalogRequest
	var inputJSON, expectDigest string
	switch command {
	case "route", "explain":
		flags.StringVar(&route.Purpose, "purpose", "", "architecture|decision|guide|reference|report|asset|temporary|source")
		flags.StringVar(&route.Path, "path", "", "exact project-relative path")
		flags.StringVar(&route.Slug, "slug", "", "lower-case kebab-case name")
		flags.StringVar(&route.TaskID, "task-id", "", "task scope")
		flags.StringVar(&route.WorkerID, "worker-id", "", "worker scope")
		flags.StringVar(&route.Date, "date", "", "report date YYYY-MM-DD")
		flags.StringVar(&route.Retention, "retention", "", "temporary retention intent")
		flags.StringVar(&route.FeatureID, "feature", "", "existing workflow owner hint")
		flags.StringVar(&route.ChangeID, "change", "", "existing design owner hint")
	case "check":
		flags.Var(&paths, "path", "exact path (repeatable)")
		flags.Var(&deletedPaths, "deleted-path", "explicit intentional deletion (repeatable)")
		flags.BoolVar(&check.Staged, "staged", false, "check index contents")
		flags.StringVar(&check.Base, "from-ref", "", "base commit; requires to-ref")
		flags.StringVar(&check.Head, "to-ref", "", "target commit; requires from-ref")
		flags.BoolVar(&check.IncludeUntracked, "include-untracked", false, "include untracked worktree files")
		flags.BoolVar(&check.PathOnly, "path-only", false, "preflight paths without claiming content checks")
	case "migrate.plan", "migrate.apply":
		flags.StringVar(&inputJSON, "input-json", "", "bounded JSON object, @path, or - for stdin")
		if command == "migrate.apply" {
			flags.StringVar(&expectDigest, "expect-digest", "", "exact reviewed plan digest")
		}
	default:
		flags.StringVar(&inputJSON, "input-json", "", "bounded JSON object, @path, or - for stdin")
		flags.BoolVar(&catalog.Enabled, "enable", false, "explicitly enable an already installed AssetKit adapter")
		flags.StringVar(&catalog.Python, "python", "", "existing Python executable")
		flags.StringVar(&catalog.Query, "query", "", "bounded find query")
		flags.StringVar(&catalog.Reference, "reference", "", "exact get reference")
		flags.StringVar(&catalog.Path, "path", "", "existing retained media path")
		flags.StringVar(&catalog.Use, "use", "", "media use")
		flags.StringVar(&catalog.SourceKind, "source-kind", "", "provenance kind")
		flags.StringVar(&catalog.SourceRef, "source-ref", "", "provenance reference")
		flags.StringVar(&catalog.License, "license", "", "license label")
		flags.StringVar(&catalog.Since, "since", "", "explicit AssetKit check baseline")
		flags.IntVar(&catalog.ExpectRevision, "expect-revision", 0, "expected AssetKit revision")
		flags.IntVar(&catalog.TimeoutSeconds, "timeout-seconds", 0, "adapter timeout, 1..60 seconds")
		flags.IntVar(&catalog.MaxOutputBytes, "max-output-bytes", 0, "adapter output limit, 1024..65536")
	}
	if err := parseAssetCLIFlags(flags, args, command == "check"); err != nil {
		return writeEnvelope(stdout, assetCLIUsage(command, err.Error()))
	}
	if *format != "json" || strings.TrimSpace(*projectRoot) == "" {
		return writeEnvelope(stdout, assetCLIUsage(command, "assets requires a nonempty project-root and --format json"))
	}
	service := NewAssetService(*projectRoot)
	switch command {
	case "route", "explain":
		route.PolicyPath = *policy
		if command == "explain" {
			return writeEnvelope(stdout, service.Explain(route))
		}
		return writeEnvelope(stdout, service.Route(route))
	case "check":
		check.Paths, check.DeletedPaths, check.PolicyPath = paths, deletedPaths, *policy
		return writeEnvelope(stdout, service.Check(check))
	case "migrate.plan":
		var request AssetMigrationPlanRequest
		if err := decodeAssetCLIInput(inputJSON, *projectRoot, &request); err != nil {
			return writeEnvelope(stdout, assetCLIUsage(command, err.Error()))
		}
		if err := mergeAssetCLIPolicy(&request.PolicyPath, *policy); err != nil {
			return writeEnvelope(stdout, assetCLIUsage(command, err.Error()))
		}
		return writeEnvelope(stdout, service.MigrationPlan(request))
	case "migrate.apply":
		var request AssetMigrationApplyRequest
		if err := decodeAssetCLIInput(inputJSON, *projectRoot, &request); err != nil {
			return writeEnvelope(stdout, assetCLIUsage(command, err.Error()))
		}
		if strings.TrimSpace(expectDigest) == "" || (request.ExpectedDigest != "" && request.ExpectedDigest != expectDigest) {
			return writeEnvelope(stdout, assetCLIUsage(command, "apply requires --expect-digest matching the reviewed plan; conflicting JSON digest is rejected"))
		}
		if *policy != "" && *policy != request.Plan.Request.PolicyPath {
			return writeEnvelope(stdout, assetCLIUsage(command, "apply must retain the policy bound into the reviewed plan"))
		}
		request.ExpectedDigest = expectDigest
		return writeEnvelope(stdout, service.MigrationApply(request))
	default:
		operation := strings.TrimPrefix(command, "catalog.")
		if inputJSON != "" {
			var mixed string
			flags.Visit(func(f *flag.Flag) {
				if f.Name != "project-root" && f.Name != "format" && f.Name != "input-json" && f.Name != "policy" {
					mixed = f.Name
				}
			})
			if mixed != "" {
				return writeEnvelope(stdout, assetCLIUsage(command, "use JSON or catalog field flags, not both (found --"+mixed+")"))
			}
			if err := decodeAssetCLIInput(inputJSON, *projectRoot, &catalog); err != nil {
				return writeEnvelope(stdout, assetCLIUsage(command, err.Error()))
			}
		}
		if catalog.Operation != "" && catalog.Operation != operation {
			return writeEnvelope(stdout, assetCLIUsage(command, "JSON operation must match the invoked catalog operation"))
		}
		if err := mergeAssetCLIPolicy(&catalog.PolicyPath, *policy); err != nil {
			return writeEnvelope(stdout, assetCLIUsage(command, err.Error()))
		}
		catalog.Operation = operation
		return writeEnvelope(stdout, service.Catalog(catalog))
	}
}

// Reject ambiguous repeated scalar options before flag.Parse can silently make
// the last value win. Only the two explicit check path lists are repeatable.
func parseAssetCLIFlags(flags *flag.FlagSet, args []string, repeatPaths bool) error {
	seen := map[string]bool{}
	for index := 0; index < len(args); index++ {
		arg := args[index]
		if arg == "--" {
			break
		}
		if !strings.HasPrefix(arg, "-") || arg == "-" {
			continue
		}
		name := strings.TrimLeft(arg, "-")
		name, _, inline := strings.Cut(name, "=")
		f := flags.Lookup(name)
		if f == nil {
			return fmt.Errorf("unknown option --%s", name)
		}
		if seen[name] && !(repeatPaths && (name == "path" || name == "deleted-path")) {
			return fmt.Errorf("duplicate option --%s", name)
		}
		seen[name] = true
		boolean, isBoolean := f.Value.(interface{ IsBoolFlag() bool })
		if !inline && !(isBoolean && boolean.IsBoolFlag()) {
			index++
		}
	}
	if err := flags.Parse(args); err != nil {
		return err
	}
	if flags.NArg() != 0 {
		return fmt.Errorf("unexpected positional arguments: use named options for exact inputs")
	}
	return nil
}

func decodeAssetCLIInput(input, projectRoot string, result any) error {
	if strings.TrimSpace(input) == "" {
		return fmt.Errorf("--input-json is required; use inline JSON, @path, or - for stdin")
	}
	raw, err := resolveAgentJSONInputBytes(input, projectRoot, "assets")
	if err != nil {
		return err
	}
	if trimmed := bytes.TrimSpace(raw); len(trimmed) == 0 || trimmed[0] != '{' {
		return fmt.Errorf("assets input must be one JSON object")
	}
	if err := assetRejectDuplicateJSONKeys(raw); err != nil {
		return err
	}
	decoder := json.NewDecoder(bytes.NewReader(raw))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(result); err != nil {
		return fmt.Errorf("invalid assets input: %w", err)
	}
	if err := decoder.Decode(new(any)); err != io.EOF {
		return fmt.Errorf("assets input must contain exactly one JSON object")
	}
	return nil
}

func mergeAssetCLIPolicy(target *string, explicit string) error {
	if explicit == "" {
		return nil
	}
	if *target != "" && *target != explicit {
		return fmt.Errorf("JSON policy_path conflicts with --policy")
	}
	*target = explicit
	return nil
}

func assetCLIUsage(command, message string) Envelope {
	env := NewEnvelope("usage-error", message)
	if _, ok := assetCapabilitySummary("assets." + command); ok {
		env.ShowArgv = []string{"specify-runtime", "api", "show", "assets." + command, "--format", "json"}
	}
	return env
}

func assetCapabilitySummary(id string) (string, bool) {
	summaries := map[string]string{
		"assets.route":         "Recommend one ordinary document or media destination without writing files or activating a workflow.",
		"assets.explain":       "Explain asset placement, ownership and naming precedence without side effects.",
		"assets.check":         "Check explicit paths, worktree changes, the index or an exact commit delta against asset policy.",
		"assets.migrate.plan":  "Prepare a digest-bound, read-only migration plan over explicit moves and reference scope.",
		"assets.migrate.apply": "Apply one reviewed migration plan under revalidated preconditions and recoverable journaling.",
		"assets.catalog.find":  "Optionally query an existing project-local AssetKit catalog with bounded output.",
		"assets.catalog.get":   "Optionally read one exact reference from an existing project-local AssetKit catalog.",
		"assets.catalog.put":   "Optionally register compliant retained media with its existing AssetKit ledger owner.",
		"assets.catalog.check": "Optionally run an existing AssetKit naming check against an explicit Git baseline.",
	}
	summary, ok := summaries[id]
	return summary, ok
}

func bindAssetCapability(id string, capability map[string]any) {
	if _, ok := assetCapabilitySummary(id); !ok {
		return
	}
	common := " [--policy <project-relative-json>] [--project-root <path>] --format json"
	switch id {
	case "assets.route", "assets.explain":
		capability["side_effect"] = "read-only"
		capability["usage"] = "specify-runtime " + strings.ReplaceAll(id, ".", " ") + " (--path <relative-path> | --purpose <architecture|decision|guide|reference|report|asset|temporary|source> --slug <name>) [--task-id <id>] [--worker-id <id>] [--date <YYYY-MM-DD>] [--retention <session|Nd>] [--feature <id>] [--change <id>]" + common
		capability["input_contract"] = "Returns create-new, reuse-existing, owner-required or conflict. Existing artifact registry, protected/control paths and native source contracts precede ordinary naming. Temporary names require task-id and worker-id. Routing neither reserves nor writes a path; recheck before writing. Retention describes intent and does not delete files."
	case "assets.check":
		capability["side_effect"] = "read-only"
		capability["usage"] = "specify-runtime assets check [--path <relative-path> ...] [--deleted-path <relative-path> ...] [--path-only] [--staged | --from-ref <base-commit> --to-ref <target-commit>] [--include-untracked]" + common
		capability["input_contract"] = "No selector checks tracked working-tree changes; include-untracked adds visible untracked files. Staged reads index content and index policy. A paired from-ref/to-ref checks exact target-tree content and policy, never dirty worktree bytes. Explicit missing paths fail unless declared deleted. Path-only preflights names without claiming content/link verification. Persistent Markdown cannot reference temporary or missing project files; deletions also check bounded inbound references. Reports stay on stdout and no workflow or audit ledger is created."
	case "assets.migrate.plan":
		capability["side_effect"] = "read-only"
		capability["usage"] = "specify-runtime assets migrate plan --input-json <object|@path|->" + common
		capability["input_contract"] = "Object with moves:[{from,to}], optional policy_path, reference_paths, reference_search_roots and reference_scope_complete. Only supported ordinary documents/media may move. The returned data.plan binds paths, policy, source/reference hashes and declared coverage; inspect unsupported/unknown inbound references before applying. The planner writes no plan file and never claims external dependency completeness."
	case "assets.migrate.apply":
		capability["side_effect"] = "writes-ordinary-assets-and-recovery-journal"
		capability["usage"] = "specify-runtime assets migrate apply --input-json <object|@path|-> --expect-digest <reviewed-sha256> [--project-root <path>] --format json"
		capability["input_contract"] = "Object {plan:<exact data.plan from planner>}; the explicit expected digest must match the unchanged plan. Revalidates the policy, read set, references, collisions, protected/native boundaries and path safety under the shared transaction lock. Moves and supported Markdown link edits either complete or retain recovery evidence; inspect a blocked recovery result before retrying. Ordinary passive checks never invoke this command."
	default:
		operation := strings.TrimPrefix(id, "assets.catalog.")
		capability["side_effect"] = "optional-assetkit-process; may-update-assetkit-cache"
		if operation == "put" {
			capability["side_effect"] = "optional-assetkit-ledger-and-cache-write"
		}
		fields := map[string]string{
			"find": "--query <query>", "get": "--reference <path-or-id>",
			"put":   "--path <retained-media> --use <purpose> [--source-kind <kind> --source-ref <reference>] [--license <label>] [--expect-revision <revision>]",
			"check": "--since <real-git-baseline>",
		}
		capability["usage"] = "specify-runtime assets catalog " + operation + " ([--enable] " + fields[operation] + " | --input-json <object|@path|->) [--python <executable>] [--timeout-seconds <1..60>] [--max-output-bytes <1024..65536>]" + common
		capability["input_contract"] = "Disabled by default; only explicit enable or policy assetkit.enabled starts an already installed .assets/ak.py. JSON fields use snake_case and may not be mixed with catalog field flags. Uses fixed argv and bounded time/output, never installs AssetKit or creates a competing ledger. Backend responses are untrusted data. A timeout/error from put may have mutated the existing ledger and is never retried automatically."
	}
}
