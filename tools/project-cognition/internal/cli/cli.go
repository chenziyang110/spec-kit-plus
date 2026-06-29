package cli

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/build"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/buildgate"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/changes"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/closeout"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/delta"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/ignore"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/query"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/reference"
	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtimegate"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/scanset"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/store"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/update"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/validation"
)

const deltaGitProbeTimeout = 750 * time.Millisecond

type stringList []string

func (s *stringList) String() string {
	return strings.Join(*s, ",")
}

func (s *stringList) Set(value string) error {
	*s = append(*s, value)
	return nil
}

func Run(args []string, stdout io.Writer, stderr io.Writer, version string) int {
	if len(args) == 0 || args[0] == "--help" || args[0] == "-h" {
		printHelp(stdout, version)
		return 0
	}
	if args[0] == "--version" || args[0] == "version" {
		fmt.Fprintf(stdout, "project-cognition %s\n", version)
		return 0
	}

	paths, err := rt.ResolvePaths(".")
	if err != nil {
		fmt.Fprintf(stderr, "project-cognition: %v\n", err)
		return 1
	}

	switch args[0] {
	case "status", "check", "doctor":
		return statusCommand(args[1:], stdout, stderr, paths)
	case "init-empty":
		return initEmptyCommand(args[1:], stdout, stderr, paths)
	case "generate-ignore":
		return generateIgnoreCommand(args[1:], stdout, stderr, paths)
	case "scan-set":
		return scanSetCommand(args[1:], stdout, stderr, paths)
	case "mark-dirty":
		return markDirtyCommand(args[1:], stdout, stderr, paths)
	case "clear-dirty":
		return statusTransitionCommand(args[1:], stdout, stderr, paths, update.ClearDirty)
	case "record-refresh":
		return recordRefreshCommand(args[1:], stdout, stderr, paths)
	case "complete-refresh":
		return completeRefreshCommand(args[1:], stdout, stderr, paths)
	case "refresh-topics":
		return refreshTopicsCommand(args[1:], stdout, stderr, paths)
	case "validate-scan":
		return jsonOnlyCommand(args[1:], stdout, stderr, validation.ValidateScan(paths))
	case "validate-build":
		return jsonOnlyCommand(args[1:], stdout, stderr, validation.ValidateBuild(paths))
	case "build-from-scan", "import-scan", "rebuild-from-scan":
		return buildFromScanCommand(args[1:], stdout, stderr, paths)
	case "publish-runtime-metadata":
		return publishMetadataCommand(args[1:], stdout, stderr, paths)
	case "changes":
		return changesCommand(args[1:], stdout, stderr, paths)
	case "closeout-plan":
		return closeoutPlanCommand(args[1:], stdout, stderr, paths)
	case "update":
		return updateCommand(args[1:], stdout, stderr, paths)
	case "lexicon":
		return lexiconCommand(args[1:], stdout, stderr, paths)
	case "query":
		return queryCommand(args[1:], stdout, stderr, paths)
	case "semantic-intake":
		return semanticIntakeCommand(args[1:], stdout, stderr, paths)
	case "semantic-audit":
		return semanticAuditCommand(args[1:], stdout, stderr, paths)
	case "semantic-audit-resume":
		return semanticAuditResumeCommand(args[1:], stdout, stderr, paths)
	case "compass":
		return compassCommand(args[1:], stdout, stderr, paths)
	case "expand":
		return expandCommand(args[1:], stdout, stderr, paths)
	case "discover":
		return discoverCommand(args[1:], stdout, stderr)
	case "read":
		return readCommand(args[1:], stdout, stderr)
	case "rebuild":
		return rebuildCommand(args[1:], stdout, stderr, paths)
	case "delta":
		return deltaCommand(args[1:], stdout, stderr, paths)
	default:
		fmt.Fprintf(stderr, "unknown command: %s\n", args[0])
		return 2
	}
}

func printHelp(w io.Writer, version string) {
	fmt.Fprintf(w, "project-cognition %s\n\n", version)
	fmt.Fprintln(w, "Usage: project-cognition <command> [options]")
	fmt.Fprintln(w, "Commands: status, check, init-empty, generate-ignore, scan-set, mark-dirty, clear-dirty, record-refresh, complete-refresh, refresh-topics, validate-scan, validate-build, build-from-scan, import-scan, rebuild-from-scan, publish-runtime-metadata, changes, closeout-plan, update, lexicon, query, semantic-intake, semantic-audit, semantic-audit-resume, compass, expand, discover, read, doctor, rebuild, delta")
}

func statusCommand(args []string, stdout io.Writer, stderr io.Writer, paths rt.Paths) int {
	fs := flag.NewFlagSet("status", flag.ContinueOnError)
	fs.SetOutput(stderr)
	format := fs.String("format", "json", "Output format: json or text")
	if err := fs.Parse(args); err != nil {
		return 2
	}
	status, err := rt.ReadStatus(paths)
	if errors.Is(err, rt.ErrUnsupportedLegacy) {
		return writeJSON(stdout, rt.UnsupportedLegacyPayload(paths))
	}
	if err != nil {
		fmt.Fprintf(stderr, "project-cognition: %v\n", err)
		return 1
	}
	if *format != "json" {
		fmt.Fprintf(stdout, "%s %s\n", status.Freshness, status.Readiness)
		return 0
	}
	return writeJSON(stdout, status)
}

func initEmptyCommand(args []string, stdout io.Writer, stderr io.Writer, paths rt.Paths) int {
	fs := flag.NewFlagSet("init-empty", flag.ContinueOnError)
	fs.SetOutput(stderr)
	_ = fs.String("format", "json", "Output format")
	if err := fs.Parse(args); err != nil {
		return 2
	}
	paths = initEmptyPaths(paths)
	agreement, exists := runtimegate.CheckExisting(paths)
	if exists {
		if agreement.Status == "ok" {
			return writeJSON(stdout, map[string]any{
				"status":                  "ok",
				"readiness":               agreement.Readiness,
				"baseline_kind":           "",
				"active_generation_id":    agreement.StatusGenerationID,
				"status_path":             agreement.StatusPath,
				"graph_store_path":        agreement.GraphStorePath,
				"already_initialized":     true,
				"errors":                  []string{},
				"warnings":                []string{},
				"recommended_next_action": agreement.RecommendedNextAction,
			})
		}
		payload := runtimegate.BlockedPayload(paths, agreement)
		payload["already_initialized"] = false
		return writeErrorJSON(stdout, payload)
	}
	if !store.GreenfieldEmptyEligible(paths.Root) {
		return writeJSON(stdout, map[string]any{
			"status":              "declined",
			"readiness":           rt.NeedsRebuildReadiness,
			"baseline_kind":       "",
			"already_initialized": false,
			"status_path":         rt.RelativeRuntimePath(paths, paths.StatusPath),
			"graph_store_path":    ".specify/project-cognition/project-cognition.db",
			"errors":              []string{},
			"warnings":            []string{"project has non-scaffold files; greenfield empty baseline was not created"},
		})
	}
	st, err := store.Open(paths)
	if err != nil {
		return writeErrorJSON(stdout, map[string]any{"status": "blocked", "readiness": rt.BlockedReadiness, "errors": []string{err.Error()}, "warnings": []string{}})
	}
	defer st.Close()
	generationID, err := st.InitializeGreenfieldEmpty(context.Background())
	if err != nil {
		return writeErrorJSON(stdout, map[string]any{"status": "blocked", "readiness": rt.BlockedReadiness, "errors": []string{err.Error()}, "warnings": []string{}})
	}
	status := rt.DefaultStatus(paths)
	status.Status = "ok"
	status.Freshness = rt.ReadyFreshness
	status.Readiness = rt.ReadyReadiness
	status.RecommendedNextAction = "use_project_cognition"
	status.GraphReady = true
	status.ActiveGenerationID = generationID
	status.QueryContractVersion = 1
	status.UpdateContractVersion = 1
	status.BaselineKind = rt.BaselineKindGreenfieldEmpty
	if err := rt.WriteStatus(paths, status); err != nil {
		return writeErrorJSON(stdout, map[string]any{"status": "blocked", "readiness": rt.BlockedReadiness, "errors": []string{err.Error()}, "warnings": []string{}, "recovery_action": "rewrite_status_from_db_metadata"})
	}
	return writeJSON(stdout, map[string]any{
		"status":               "ok",
		"readiness":            rt.ReadyReadiness,
		"baseline_kind":        rt.BaselineKindGreenfieldEmpty,
		"active_generation_id": generationID,
		"status_path":          rt.RelativeRuntimePath(paths, paths.StatusPath),
		"graph_store_path":     ".specify/project-cognition/project-cognition.db",
		"already_initialized":  false,
		"errors":               []string{},
		"warnings":             []string{},
	})
}

func initEmptyPaths(paths rt.Paths) rt.Paths {
	cwd, err := os.Getwd()
	if err != nil {
		return paths
	}
	cwd, err = filepath.Abs(cwd)
	if err != nil {
		return paths
	}
	homeCaptured := false
	home, err := os.UserHomeDir()
	if err == nil {
		if home, err = filepath.Abs(home); err == nil {
			homeCaptured = samePath(paths.Root, home)
		}
	}
	rootCaptured := isFilesystemRoot(paths.Root)
	if samePath(cwd, paths.Root) || (!homeCaptured && !rootCaptured) {
		return paths
	}
	runtimeDir := filepath.Join(cwd, rt.SpecifyDir, rt.CognitionDir)
	return rt.Paths{
		Root:         cwd,
		RuntimeDir:   runtimeDir,
		StatusPath:   filepath.Join(runtimeDir, rt.StatusFileName),
		DatabasePath: filepath.Join(runtimeDir, rt.DBFileName),
	}
}

func generateIgnoreCommand(args []string, stdout io.Writer, stderr io.Writer, paths rt.Paths) int {
	fs := flag.NewFlagSet("generate-ignore", flag.ContinueOnError)
	fs.SetOutput(stderr)
	_ = fs.String("format", "json", "Output format")
	if err := fs.Parse(args); err != nil {
		return 2
	}
	paths = initEmptyPaths(paths)
	path, created, err := ignore.WriteStarterIgnoreFile(paths.Root)
	if err != nil {
		return writeErrorJSON(stdout, map[string]any{
			"status":   "error",
			"errors":   []string{err.Error()},
			"warnings": []string{},
		})
	}
	status := "exists"
	if created {
		status = "created"
	}
	return writeJSON(stdout, map[string]any{
		"status":          status,
		"path":            rt.RelativeRuntimePath(paths, path),
		"review_required": created,
		"errors":          []string{},
		"warnings":        []string{},
	})
}

func scanSetCommand(args []string, stdout io.Writer, stderr io.Writer, paths rt.Paths) int {
	fs := flag.NewFlagSet("scan-set", flag.ContinueOnError)
	fs.SetOutput(stderr)
	var scopes stringList
	fs.Var(&scopes, "scope", "Repository-relative file or directory scope")
	fs.Var(&scopes, "path", "Repository-relative file or directory scope")
	out := fs.String("out", scanset.DefaultOutputPath, "Repository-relative output file")
	maxBytes := fs.Int64("max-bytes", 0, "Skip files larger than this many bytes when greater than zero")
	_ = fs.String("format", "json", "Output format")
	if err := fs.Parse(args); err != nil {
		return 2
	}
	payload, err := scanset.Resolve(paths, scanset.Input{
		Scopes:   scopes,
		Out:      *out,
		MaxBytes: *maxBytes,
	})
	if err != nil {
		fmt.Fprintf(stderr, "project-cognition: %v\n", err)
		return 1
	}
	return writeCompactJSON(stdout, payload)
}

func isFilesystemRoot(path string) bool {
	cleaned := filepath.Clean(path)
	volume := filepath.VolumeName(cleaned)
	if volume != "" {
		return samePath(cleaned, volume+string(os.PathSeparator))
	}
	return cleaned == string(os.PathSeparator)
}

func samePath(left string, right string) bool {
	left = filepath.Clean(left)
	right = filepath.Clean(right)
	if os.PathSeparator == '\\' {
		return strings.EqualFold(left, right)
	}
	return left == right
}

func markDirtyCommand(args []string, stdout io.Writer, stderr io.Writer, paths rt.Paths) int {
	fs := flag.NewFlagSet("mark-dirty", flag.ContinueOnError)
	fs.SetOutput(stderr)
	reason := fs.String("reason", "", "Dirty reason")
	originCommand := fs.String("origin-command", "", "Origin command")
	originFeatureDir := fs.String("origin-feature-dir", "", "Origin feature directory")
	originLaneID := fs.String("origin-lane-id", "", "Origin lane id")
	packetFile := fs.String("packet-file", "", "Worker packet JSON")
	var scope stringList
	fs.Var(&scope, "scope", "Dirty scope path")
	_ = fs.String("format", "json", "Output format")
	if err := fs.Parse(args); err != nil {
		return 2
	}
	if *reason == "" && fs.NArg() > 0 {
		*reason = strings.Join(fs.Args(), " ")
	}
	status, err := update.MarkDirty(paths, update.DirtyInput{
		Reason:           *reason,
		OriginCommand:    *originCommand,
		OriginFeatureDir: *originFeatureDir,
		OriginLaneID:     *originLaneID,
		ScopePaths:       scope,
		PacketFile:       *packetFile,
	})
	return writeCommandResult(stdout, stderr, paths, status, err)
}

func statusTransitionCommand(args []string, stdout io.Writer, stderr io.Writer, paths rt.Paths, fn func(rt.Paths) (rt.Status, error)) int {
	fs := flag.NewFlagSet("transition", flag.ContinueOnError)
	fs.SetOutput(stderr)
	_ = fs.String("format", "json", "Output format")
	if err := fs.Parse(args); err != nil {
		return 2
	}
	status, err := fn(paths)
	return writeCommandResult(stdout, stderr, paths, status, err)
}

func recordRefreshCommand(args []string, stdout io.Writer, stderr io.Writer, paths rt.Paths) int {
	fs := flag.NewFlagSet("record-refresh", flag.ContinueOnError)
	fs.SetOutput(stderr)
	reason := fs.String("reason", "manual", "Refresh reason")
	_ = fs.String("format", "json", "Output format")
	if err := fs.Parse(args); err != nil {
		return 2
	}
	status, err := update.RecordRefresh(paths, *reason)
	return writeCommandResult(stdout, stderr, paths, status, err)
}

func completeRefreshCommand(args []string, stdout io.Writer, stderr io.Writer, paths rt.Paths) int {
	fs := flag.NewFlagSet("complete-refresh", flag.ContinueOnError)
	fs.SetOutput(stderr)
	_ = fs.String("format", "json", "Output format")
	if err := fs.Parse(args); err != nil {
		return 2
	}
	status, err := update.CompleteRefresh(paths, "map-build")
	return writeCommandResult(stdout, stderr, paths, status, err)
}

func refreshTopicsCommand(args []string, stdout io.Writer, stderr io.Writer, paths rt.Paths) int {
	fs := flag.NewFlagSet("refresh-topics", flag.ContinueOnError)
	fs.SetOutput(stderr)
	reason := fs.String("reason", "topic-refresh", "Refresh reason")
	_ = fs.String("format", "json", "Output format")
	if err := fs.Parse(args); err != nil {
		return 2
	}
	status, err := update.RefreshTopics(paths, fs.Args(), *reason)
	return writeCommandResult(stdout, stderr, paths, status, err)
}

func jsonOnlyCommand(args []string, stdout io.Writer, stderr io.Writer, payload any) int {
	fs := flag.NewFlagSet("json", flag.ContinueOnError)
	fs.SetOutput(stderr)
	_ = fs.String("format", "json", "Output format")
	if err := fs.Parse(args); err != nil {
		return 2
	}
	code := writeJSON(stdout, payload)
	if code != 0 {
		return code
	}
	if payloadBlocked(payload) {
		return 1
	}
	return 0
}

func buildFromScanCommand(args []string, stdout io.Writer, stderr io.Writer, paths rt.Paths) int {
	fs := flag.NewFlagSet("build-from-scan", flag.ContinueOnError)
	fs.SetOutput(stderr)
	_ = fs.String("format", "json", "Output format")
	if err := fs.Parse(args); err != nil {
		return 2
	}
	payload, err := build.Run(paths)
	if err != nil && payload.Status == "" {
		fmt.Fprintf(stderr, "project-cognition: %v\n", err)
		return 1
	}
	code := writeJSON(stdout, payload)
	if code != 0 {
		return code
	}
	if err != nil {
		return 1
	}
	if payloadBlocked(payload) {
		return 1
	}
	return 0
}

func payloadBlocked(payload any) bool {
	data, err := json.Marshal(payload)
	if err != nil {
		return false
	}
	var obj map[string]any
	if err := json.Unmarshal(data, &obj); err != nil {
		return false
	}
	return stringField(obj, "status") == "blocked" || stringField(obj, "readiness") == "blocked"
}

func stringField(obj map[string]any, key string) string {
	value, _ := obj[key].(string)
	return strings.TrimSpace(strings.ToLower(value))
}

func publishMetadataCommand(args []string, stdout io.Writer, stderr io.Writer, paths rt.Paths) int {
	fs := flag.NewFlagSet("publish-runtime-metadata", flag.ContinueOnError)
	fs.SetOutput(stderr)
	_ = fs.String("format", "json", "Output format")
	if err := fs.Parse(args); err != nil {
		return 2
	}
	st, err := store.OpenExisting(paths)
	if err != nil {
		return writeErrorJSON(stdout, map[string]any{"status": "error", "errors": []string{err.Error()}, "warnings": []string{}})
	}
	defer st.Close()
	activeGenerationID, err := st.ActiveGenerationID(context.Background())
	if err != nil {
		return writeErrorJSON(stdout, map[string]any{"status": "error", "errors": []string{err.Error()}, "warnings": []string{}})
	}
	if activeGenerationID == "" {
		return writeErrorJSON(stdout, map[string]any{"status": "error", "errors": []string{"project-cognition.db has no active generation"}, "warnings": []string{}})
	}
	activeGenerationKind, err := st.ActiveGenerationKind(context.Background())
	if err != nil {
		return writeErrorJSON(stdout, map[string]any{"status": "error", "errors": []string{err.Error()}, "warnings": []string{}})
	}
	baselineKind := normalizeBaselineKind(activeGenerationKind)
	status, err := rt.ReadStatus(paths)
	if errors.Is(err, rt.ErrUnsupportedLegacy) {
		return writeErrorJSON(stdout, rt.UnsupportedLegacyPayload(paths))
	}
	if err != nil {
		status = rt.DefaultStatus(paths)
	}
	sparse := buildgate.ValidateSparsePathIndex(paths, st.DB(), activeGenerationID)
	if len(sparse.Errors) > 0 {
		status.Status = "blocked"
		status.Readiness = rt.BlockedReadiness
		status.ActiveGenerationID = activeGenerationID
		status.BaselineKind = baselineKind
		if err := st.MarkRuntimeMetadataBlocked(context.Background(), activeGenerationID, func() error {
			if err := rt.WriteStatus(paths, status); err != nil {
				return fmt.Errorf("write blocked status: %w", err)
			}
			return nil
		}); err != nil {
			payload := map[string]any{
				"status":                    "blocked",
				"readiness":                 rt.BlockedReadiness,
				"active_generation_id":      activeGenerationID,
				"sparse_path_index_details": sparse.Details,
				"warnings":                  sparse.Warnings,
			}
			if strings.HasPrefix(err.Error(), "write blocked status:") {
				sparse.Errors = append(sparse.Errors, err.Error())
				payload["recovery_action"] = "rewrite_status_from_db_metadata"
				payload["errors"] = sparse.Errors
				code := writeJSON(stdout, payload)
				if code != 0 {
					return code
				}
				return 1
			}
			sparse.Errors = append(sparse.Errors, fmt.Sprintf("write blocked DB metadata: %v", err))
			payload["errors"] = sparse.Errors
			code := writeJSON(stdout, payload)
			if code != 0 {
				return code
			}
			return 1
		}
		code := writeJSON(stdout, map[string]any{
			"status":                    "blocked",
			"readiness":                 rt.BlockedReadiness,
			"active_generation_id":      activeGenerationID,
			"sparse_path_index_details": sparse.Details,
			"errors":                    sparse.Errors,
			"warnings":                  sparse.Warnings,
		})
		if code != 0 {
			return code
		}
		return 1
	}
	status.Status = "ok"
	status.Freshness = rt.ReadyFreshness
	status.Readiness = rt.ReadyReadiness
	status.RecommendedNextAction = "use_project_cognition"
	status.GraphReady = true
	status.ActiveGenerationID = activeGenerationID
	status.BaselineKind = baselineKind
	status.QueryContractVersion = 1
	status.UpdateContractVersion = 1
	meta, readyGenerationID, err := st.PublishRuntimeMetadata(context.Background(), activeGenerationID, baselineKind, func() error {
		if err := rt.WriteStatus(paths, status); err != nil {
			return fmt.Errorf("write ready status: %w", err)
		}
		return nil
	})
	if err != nil {
		payload := map[string]any{"status": "error", "errors": []string{err.Error()}, "warnings": []string{}}
		if strings.HasPrefix(err.Error(), "write ready status:") {
			payload["recovery_action"] = "rewrite_status_from_db_metadata"
			code := writeJSON(stdout, payload)
			if code != 0 {
				return code
			}
			return 1
		}
		return writeErrorJSON(stdout, payload)
	}
	if readyGenerationID != activeGenerationID {
		return writeErrorJSON(stdout, map[string]any{"status": "error", "errors": []string{fmt.Sprintf("ready DB metadata active generation mismatch: got %s, want %s", readyGenerationID, activeGenerationID)}, "warnings": []string{}})
	}
	return writeJSON(stdout, map[string]any{
		"status":               "ok",
		"metadata":             meta,
		"active_generation_id": activeGenerationID,
		"status_path":          status.StatusPath,
		"graph_store_path":     status.GraphStorePath,
		"errors":               []string{},
		"warnings":             []string{},
	})
}

func normalizeBaselineKind(kind string) string {
	switch strings.TrimSpace(kind) {
	case "", "full":
		return rt.BaselineKindBrownfieldFull
	default:
		return strings.TrimSpace(kind)
	}
}

func changesCommand(args []string, stdout io.Writer, stderr io.Writer, paths rt.Paths) int {
	fs := flag.NewFlagSet("changes", flag.ContinueOnError)
	fs.SetOutput(stderr)
	var changed stringList
	fs.Var(&changed, "changed-path", "Explicit changed path")
	fs.Var(&changed, "changed-paths", "Explicit changed path")
	since := fs.String("since", "", "Baseline commit")
	head := fs.String("head", "", "Head commit")
	includeWorkingTree := fs.Bool("include-working-tree", true, "Include working tree changes")
	includeUntracked := fs.Bool("include-untracked", true, "Include untracked paths")
	intent := fs.String("intent", "", "Agent intent")
	_ = fs.String("format", "json", "Output format")
	if err := fs.Parse(args); err != nil {
		return 2
	}
	payload, err := changes.Run(paths, changes.Input{
		Since:              *since,
		Head:               *head,
		IncludeWorkingTree: *includeWorkingTree,
		IncludeUntracked:   *includeUntracked,
		ExplicitPaths:      changed,
		Intent:             *intent,
	})
	return writeCommandResult(stdout, stderr, paths, payload, err)
}

func closeoutPlanCommand(args []string, stdout io.Writer, stderr io.Writer, paths rt.Paths) int {
	fs := flag.NewFlagSet("closeout-plan", flag.ContinueOnError)
	fs.SetOutput(stderr)
	var changed stringList
	fs.Var(&changed, "changed-path", "Explicit changed path")
	fs.Var(&changed, "changed-paths", "Explicit changed path")
	workflow := fs.String("workflow", "", "Workflow name")
	reason := fs.String("reason", "workflow-finalize", "Closeout reason")
	intent := fs.String("intent", "", "Agent intent")
	since := fs.String("since", "", "Baseline commit")
	head := fs.String("head", "", "Head commit")
	payloadPath := fs.String("payload-path", "", "Planned update payload path")
	deltaSession := fs.String("delta-session", "", "Delta session id")
	includeWorkingTree := fs.Bool("include-working-tree", true, "Include working tree changes")
	includeUntracked := fs.Bool("include-untracked", true, "Include untracked paths")
	_ = fs.String("format", "json", "Output format")
	if err := fs.Parse(args); err != nil {
		return 2
	}
	payload, err := closeout.Run(paths, closeout.Input{
		Workflow:           *workflow,
		Reason:             *reason,
		Intent:             *intent,
		Since:              *since,
		Head:               *head,
		IncludeWorkingTree: *includeWorkingTree,
		IncludeUntracked:   *includeUntracked,
		ExplicitPaths:      changed,
		DeltaSessionID:     *deltaSession,
		PayloadPath:        *payloadPath,
	})
	return writeCommandResult(stdout, stderr, paths, payload, err)
}

func updateCommand(args []string, stdout io.Writer, stderr io.Writer, paths rt.Paths) int {
	fs := flag.NewFlagSet("update", flag.ContinueOnError)
	fs.SetOutput(stderr)
	var changed stringList
	var scopes stringList
	var behaviorSurfaces stringList
	var generatedSurfaces stringList
	var stateContracts stringList
	var verification stringList
	var knownUnknowns stringList
	var confidenceNotes stringList
	var userDecisions stringList
	fs.Var(&changed, "changed-paths", "Changed path")
	fs.Var(&changed, "changed-path", "Changed path")
	fs.Var(&scopes, "scope", "Scope path")
	fs.Var(&behaviorSurfaces, "behavior-surface", "Behavior surface")
	fs.Var(&generatedSurfaces, "generated-surface", "Generated surface note")
	fs.Var(&stateContracts, "state-contract", "State contract")
	fs.Var(&verification, "verification", "Verification evidence")
	fs.Var(&knownUnknowns, "known-unknown", "Known unknown")
	fs.Var(&confidenceNotes, "confidence-note", "Confidence note")
	fs.Var(&userDecisions, "user-decision", "User decision")
	reason := fs.String("reason", "update", "Update reason")
	workflow := fs.String("workflow", "", "Workflow name")
	deltaSession := fs.String("delta-session", "", "Delta session id")
	commitRange := fs.String("commit-range", "", "Commit range base..head")
	payloadFile := fs.String("payload-file", "", "Structured update payload JSON file")
	_ = fs.String("format", "json", "Output format")
	if err := fs.Parse(args); err != nil {
		return 2
	}
	payload, err := update.RunUpdate(paths, update.UpdateInput{
		ChangedPaths:      changed,
		ScopePaths:        scopes,
		Reason:            *reason,
		DeltaSessionID:    *deltaSession,
		CommitRange:       *commitRange,
		PayloadFile:       *payloadFile,
		Workflow:          *workflow,
		BehaviorSurfaces:  behaviorSurfaces,
		GeneratedSurfaces: generatedSurfaces,
		StateContracts:    stateContracts,
		Verification:      verificationEvidenceFromCLI(verification),
		KnownUnknowns:     knownUnknowns,
		ConfidenceNotes:   confidenceNotes,
		UserDecisions:     userDecisions,
	})
	return writeCommandResult(stdout, stderr, paths, payload, err)
}

func verificationEvidenceFromCLI(values []string) []update.VerificationEvidence {
	out := make([]update.VerificationEvidence, 0, len(values))
	for _, value := range values {
		out = append(out, update.VerificationEvidence{Command: value, Result: verificationResultFromText(value)})
	}
	return out
}

func verificationResultFromText(value string) string {
	result := "recorded"
	lower := strings.ToLower(value)
	if strings.Contains(lower, "pass") {
		result = "passed"
	}
	if strings.Contains(lower, "fail") {
		result = "failed"
	}
	return result
}

func lexiconCommand(args []string, stdout io.Writer, stderr io.Writer, paths rt.Paths) int {
	fs := flag.NewFlagSet("lexicon", flag.ContinueOnError)
	fs.SetOutput(stderr)
	intent := fs.String("intent", "", "Intent")
	text := fs.String("query", "", "Query text")
	limit := fs.Int("limit", 10, "Limit")
	mode := fs.String("mode", "", "Lexicon mode")
	_ = fs.String("format", "json", "Output format")
	if err := fs.Parse(args); err != nil {
		return 2
	}
	payload, err := query.LexiconWithOptions(paths, query.LexiconInput{
		Intent: *intent,
		Query:  *text,
		Limit:  *limit,
		Mode:   *mode,
	})
	return writeCommandResult(stdout, stderr, paths, payload, err)
}

func queryCommand(args []string, stdout io.Writer, stderr io.Writer, paths rt.Paths) int {
	fs := flag.NewFlagSet("query", flag.ContinueOnError)
	fs.SetOutput(stderr)
	intent := fs.String("intent", "", "Intent")
	text := fs.String("query", "", "Query text")
	expanded := fs.String("expanded-query", "", "Expanded query")
	planJSON := fs.String("query-plan", "", "Query plan JSON or @file")
	planFile := fs.String("query-plan-file", "", "Query plan file")
	var pathHints stringList
	fs.Var(&pathHints, "paths", "Path hint")
	_ = fs.String("format", "json", "Output format")
	if err := fs.Parse(args); err != nil {
		return 2
	}
	plan, diagnostics, err := query.ParsePlanWithDiagnostics(*planJSON, *planFile)
	if err != nil {
		var planErr *query.PlanParseError
		if errors.As(err, &planErr) {
			fmt.Fprintf(stderr, "project-cognition: query plan diagnostics require repair\n")
			return writeErrorJSON(stdout, map[string]any{
				"status":         "error",
				"readiness":      rt.BlockedReadiness,
				"errors":         planErr.Errors,
				"warnings":       planErr.Warnings,
				"repair_hints":   planErr.RepairHints,
				"expected_shape": planErr.ExpectedShape,
			})
		}
		fmt.Fprintf(stderr, "project-cognition: %v\n", err)
		return 1
	}
	payload, err := query.Run(paths, query.QueryInput{Intent: *intent, Query: *text, ExpandedQuery: *expanded, Paths: pathHints, Plan: plan, PlanDiagnostics: diagnostics})
	return writeCommandResult(stdout, stderr, paths, payload, err)
}

func semanticIntakeCommand(args []string, stdout io.Writer, stderr io.Writer, paths rt.Paths) int {
	fs := flag.NewFlagSet("semantic-intake", flag.ContinueOnError)
	fs.SetOutput(stderr)
	inputFile := fs.String("input", "", "Semantic intake JSON input file")
	_ = fs.String("format", "json", "Output format")
	if err := fs.Parse(args); err != nil {
		return 2
	}

	var data []byte
	var err error
	if strings.TrimSpace(*inputFile) != "" {
		data, err = os.ReadFile(*inputFile)
		if err != nil {
			fmt.Fprintf(stderr, "project-cognition: read semantic-intake input: %v\n", err)
			return 1
		}
	} else {
		data, err = io.ReadAll(os.Stdin)
		if err != nil {
			fmt.Fprintf(stderr, "project-cognition: read semantic-intake stdin: %v\n", err)
			return 1
		}
	}
	request, err := query.ParseSemanticIntakeRequest(data)
	if err != nil {
		fmt.Fprintf(stderr, "project-cognition: %v\n", err)
		return 1
	}
	payload, err := query.RunSemanticIntake(paths, request)
	return writeCommandResult(stdout, stderr, paths, payload, err)
}

func semanticAuditCommand(args []string, stdout io.Writer, stderr io.Writer, paths rt.Paths) int {
	fs := flag.NewFlagSet("semantic-audit", flag.ContinueOnError)
	fs.SetOutput(stderr)
	inputFile := fs.String("input", "", "Semantic audit JSON input file")
	_ = fs.String("format", "json", "Output format")
	if err := fs.Parse(args); err != nil {
		return 2
	}

	var data []byte
	var err error
	if strings.TrimSpace(*inputFile) != "" {
		data, err = os.ReadFile(*inputFile)
		if err != nil {
			fmt.Fprintf(stderr, "project-cognition: read semantic-audit input: %v\n", err)
			return 1
		}
	} else {
		data, err = io.ReadAll(os.Stdin)
		if err != nil {
			fmt.Fprintf(stderr, "project-cognition: read semantic-audit stdin: %v\n", err)
			return 1
		}
	}
	request, err := query.ParseSemanticAuditRequest(data)
	if err != nil {
		fmt.Fprintf(stderr, "project-cognition: %v\n", err)
		return 1
	}
	payload, err := query.BuildSemanticAudit(request)
	return writeCommandResult(stdout, stderr, paths, payload, err)
}

func semanticAuditResumeCommand(args []string, stdout io.Writer, stderr io.Writer, paths rt.Paths) int {
	fs := flag.NewFlagSet("semantic-audit-resume", flag.ContinueOnError)
	fs.SetOutput(stderr)
	inputFile := fs.String("input", "", "Semantic audit resume validation JSON input file")
	_ = fs.String("format", "json", "Output format")
	if err := fs.Parse(args); err != nil {
		return 2
	}

	var data []byte
	var err error
	baseDir := "."
	if strings.TrimSpace(*inputFile) != "" {
		data, err = os.ReadFile(*inputFile)
		if err != nil {
			fmt.Fprintf(stderr, "project-cognition: read semantic-audit-resume input: %v\n", err)
			return 1
		}
		baseDir = filepath.Dir(*inputFile)
	} else {
		data, err = io.ReadAll(os.Stdin)
		if err != nil {
			fmt.Fprintf(stderr, "project-cognition: read semantic-audit-resume stdin: %v\n", err)
			return 1
		}
	}
	request, missingFileValidation, err := parseSemanticAuditResumeCLIRequest(data, baseDir)
	if err != nil {
		fmt.Fprintf(stderr, "project-cognition: %v\n", err)
		return 1
	}
	if missingFileValidation != nil {
		return writeJSON(stdout, *missingFileValidation)
	}
	payload, err := query.ValidateSemanticAuditResume(request)
	return writeCommandResult(stdout, stderr, paths, payload, err)
}

func parseSemanticAuditResumeCLIRequest(data []byte, baseDir string) (query.SemanticAuditResumeRequest, *query.SemanticAuditResumeValidation, error) {
	if request, err := query.ParseSemanticAuditResumeRequest(data); err == nil {
		return request, nil, nil
	}
	var envelope struct {
		Version            int                            `json:"version"`
		WorkflowState      query.SemanticAuditResumeState `json:"workflow_state"`
		SemanticAuditState query.SemanticAuditResumeState `json:"semantic_audit_state"`
	}
	if err := json.Unmarshal(data, &envelope); err != nil {
		return query.SemanticAuditResumeRequest{}, nil, fmt.Errorf("parse semantic-audit-resume request: %w", err)
	}
	state := envelope.SemanticAuditState
	if state.SemanticAuditInputPath == "" && envelope.WorkflowState.SemanticAuditInputPath != "" {
		state = envelope.WorkflowState
	}
	inputPath, err := resolveSemanticAuditResumePath(baseDir, state.SemanticAuditInputPath)
	if err != nil {
		validation := query.BuildSemanticAuditResumeMissingFileValidation(state)
		return query.SemanticAuditResumeRequest{}, &validation, nil
	}
	outputPath, err := resolveSemanticAuditResumePath(baseDir, state.SemanticAuditOutputPath)
	if err != nil {
		validation := query.BuildSemanticAuditResumeMissingFileValidation(state)
		return query.SemanticAuditResumeRequest{}, &validation, nil
	}
	inputData, err := os.ReadFile(inputPath)
	if err != nil {
		validation := query.BuildSemanticAuditResumeMissingFileValidation(state)
		return query.SemanticAuditResumeRequest{}, &validation, nil
	}
	outputData, err := os.ReadFile(outputPath)
	if err != nil {
		validation := query.BuildSemanticAuditResumeMissingFileValidation(state)
		return query.SemanticAuditResumeRequest{}, &validation, nil
	}
	auditInput, err := query.ParseSemanticAuditRequest(inputData)
	if err != nil {
		return query.SemanticAuditResumeRequest{}, nil, err
	}
	auditOutput, err := parseSemanticAuditOutputArtifact(outputData)
	if err != nil {
		return query.SemanticAuditResumeRequest{}, nil, err
	}
	version := envelope.Version
	if version == 0 {
		version = 1
	}
	return query.SemanticAuditResumeRequest{
		Version:             version,
		SemanticAuditInput:  auditInput,
		SemanticAuditOutput: auditOutput,
		SemanticAuditState:  state,
	}, nil, nil
}

func resolveSemanticAuditResumePath(baseDir string, value string) (string, error) {
	value = strings.TrimSpace(value)
	if value == "" || strings.EqualFold(value, "none") {
		return "", fmt.Errorf("semantic-audit-resume path is required")
	}
	if filepath.IsAbs(value) {
		return value, nil
	}
	if strings.TrimSpace(baseDir) == "" {
		baseDir = "."
	}
	return filepath.Join(baseDir, filepath.FromSlash(value)), nil
}

func parseSemanticAuditOutputArtifact(data []byte) (query.SemanticAuditArtifact, error) {
	var artifact query.SemanticAuditArtifact
	if err := json.Unmarshal(data, &artifact); err != nil {
		return query.SemanticAuditArtifact{}, fmt.Errorf("parse semantic-audit output: %w", err)
	}
	if artifact.ArtifactType != "" {
		return artifact, nil
	}
	var wrapped struct {
		SemanticAuditOutput query.SemanticAuditArtifact `json:"semantic_audit_output"`
	}
	if err := json.Unmarshal(data, &wrapped); err != nil {
		return query.SemanticAuditArtifact{}, fmt.Errorf("parse semantic-audit output: %w", err)
	}
	if wrapped.SemanticAuditOutput.ArtifactType == "" {
		return query.SemanticAuditArtifact{}, fmt.Errorf("parse semantic-audit output: artifact_type is required")
	}
	return wrapped.SemanticAuditOutput, nil
}

func compassCommand(args []string, stdout io.Writer, stderr io.Writer, paths rt.Paths) int {
	fs := flag.NewFlagSet("compass", flag.ContinueOnError)
	fs.SetOutput(stderr)
	intent := fs.String("intent", "", "Intent")
	text := fs.String("query", "", "Query text")
	semanticIntakeFile := fs.String("semantic-intake-file", "", "Semantic intake file")
	planFile := fs.String("query-plan-file", "", "Query plan file")
	_ = fs.String("format", "json", "Output format")
	if err := fs.Parse(args); err != nil {
		return 2
	}

	inputMode := "query"
	var plan query.Plan
	var diagnostics query.PlanDiagnostics
	if *planFile != "" {
		var err error
		plan, diagnostics, err = query.ParsePlanWithDiagnostics("", *planFile)
		if err != nil {
			var planErr *query.PlanParseError
			if errors.As(err, &planErr) {
				fmt.Fprintf(stderr, "project-cognition: query plan diagnostics require repair\n")
				return writeErrorJSON(stdout, map[string]any{
					"status":         "error",
					"readiness":      rt.BlockedReadiness,
					"errors":         planErr.Errors,
					"warnings":       planErr.Warnings,
					"repair_hints":   planErr.RepairHints,
					"expected_shape": planErr.ExpectedShape,
				})
			}
			fmt.Fprintf(stderr, "project-cognition: %v\n", err)
			return 1
		}
		inputMode = "query_plan"
	} else if *semanticIntakeFile != "" {
		intake, err := query.ParseSemanticIntakeFile(*semanticIntakeFile)
		if err != nil {
			fmt.Fprintf(stderr, "project-cognition: %v\n", err)
			return 1
		}
		plan.SemanticIntake = intake
		inputMode = "semantic_intake"
	}

	payload, err := query.Compass(paths, query.CompassInput{
		Intent:          *intent,
		Query:           *text,
		Plan:            plan,
		PlanDiagnostics: diagnostics,
		InputMode:       inputMode,
	})
	return writeCommandResult(stdout, stderr, paths, payload, err)
}

func expandCommand(args []string, stdout io.Writer, stderr io.Writer, paths rt.Paths) int {
	fs := flag.NewFlagSet("expand", flag.ContinueOnError)
	fs.SetOutput(stderr)
	id := fs.String("id", "", "Expansion id")
	section := fs.String("section", "related_paths", "Expansion section")
	_ = fs.String("format", "json", "Output format")
	if err := fs.Parse(args); err != nil {
		return 2
	}

	payload, err := query.Expand(paths, query.ExpandInput{ID: *id, Section: *section})
	return writeCommandResult(stdout, stderr, paths, payload, err)
}

func discoverCommand(args []string, stdout io.Writer, stderr io.Writer) int {
	fs := flag.NewFlagSet("discover", flag.ContinueOnError)
	fs.SetOutput(stderr)
	root := fs.String("root", ".", "Discovery root")
	_ = fs.String("format", "json", "Output format")
	if err := fs.Parse(args); err != nil {
		return 2
	}
	payload, err := reference.Discover(*root)
	if err != nil {
		fmt.Fprintf(stderr, "project-cognition: %v\n", err)
		return 1
	}
	return writeJSON(stdout, payload)
}

func readCommand(args []string, stdout io.Writer, stderr io.Writer) int {
	fs := flag.NewFlagSet("read", flag.ContinueOnError)
	fs.SetOutput(stderr)
	project := fs.String("project", ".", "Project path")
	slice := fs.String("slice", "overview", "Slice name")
	var graphs stringList
	fs.Var(&graphs, "include-graph", "Graph name")
	_ = fs.String("format", "json", "Output format")
	if err := fs.Parse(args); err != nil {
		return 2
	}
	payload, err := reference.Read(*project, *slice, graphs)
	if err != nil {
		fmt.Fprintf(stderr, "project-cognition: %v\n", err)
		return 1
	}
	return writeJSON(stdout, payload)
}

func rebuildCommand(args []string, stdout io.Writer, stderr io.Writer, paths rt.Paths) int {
	fs := flag.NewFlagSet("rebuild", flag.ContinueOnError)
	fs.SetOutput(stderr)
	format := fs.String("format", "text", "Output format")
	if err := fs.Parse(args); err != nil {
		return 2
	}
	payload := map[string]any{
		"status":                  "blocked",
		"readiness":               rt.NeedsRebuildReadiness,
		"recommended_next_action": "run_map_scan_build",
		"errors":                  []string{},
		"warnings":                []string{"Run sp-map-scan, then sp-map-build to rebuild project cognition."},
		"status_path":             paths.StatusPath,
	}
	if *format == "json" {
		return writeJSON(stdout, payload)
	}
	fmt.Fprintln(stdout, "Run /sp-map-scan, then /sp-map-build to rebuild project cognition.")
	return 0
}

func deltaCommand(args []string, stdout io.Writer, stderr io.Writer, paths rt.Paths) int {
	if len(args) == 0 {
		fmt.Fprintln(stderr, "project-cognition: delta subcommand is required")
		return 2
	}
	switch args[0] {
	case "begin":
		return deltaBeginCommand(args[1:], stdout, stderr, paths)
	case "append":
		return deltaAppendCommand(args[1:], stdout, stderr, paths)
	case "status":
		return deltaStatusCommand(args[1:], stdout, stderr, paths)
	default:
		fmt.Fprintf(stderr, "project-cognition: unknown delta subcommand: %s\n", args[0])
		return 2
	}
}

func deltaBeginCommand(args []string, stdout io.Writer, stderr io.Writer, paths rt.Paths) int {
	fs := flag.NewFlagSet("delta begin", flag.ContinueOnError)
	fs.SetOutput(stderr)
	originCommand := fs.String("origin-command", "", "Origin command")
	originFeatureDir := fs.String("origin-feature-dir", "", "Origin feature directory")
	originLaneID := fs.String("origin-lane-id", "", "Origin lane id")
	_ = fs.String("format", "json", "Output format")
	if err := fs.Parse(args); err != nil {
		return 2
	}

	gitMetadata := collectDeltaGitMetadata(paths.Root, deltaGitProbeTimeout, runGitCommand)
	session, err := delta.Begin(delta.BeginInput{
		Root:              paths.Root,
		RuntimeDir:        paths.RuntimeDir,
		OriginCommand:     *originCommand,
		OriginFeatureDir:  *originFeatureDir,
		OriginLaneID:      *originLaneID,
		BaseCommit:        gitMetadata.baseCommit,
		Branch:            gitMetadata.branch,
		InitialDirtyPaths: gitMetadata.initialDirty,
	})
	return writeCommandResult(stdout, stderr, paths, session, err)
}

type deltaGitMetadata struct {
	baseCommit   string
	branch       string
	initialDirty []string
}

type gitCommandRunner func(context.Context, string, ...string) (string, error)

func collectDeltaGitMetadata(root string, timeout time.Duration, run gitCommandRunner) deltaGitMetadata {
	if output, err := runGitProbe(root, timeout, run, "rev-parse", "--is-inside-work-tree"); err != nil || strings.TrimSpace(output) != "true" {
		return deltaGitMetadata{}
	}

	metadata := deltaGitMetadata{}
	if output, err := runGitProbe(root, timeout, run, "rev-parse", "HEAD"); err == nil {
		metadata.baseCommit = strings.TrimSpace(output)
	}
	if output, err := runGitProbe(root, timeout, run, "branch", "--show-current"); err == nil {
		metadata.branch = strings.TrimSpace(output)
	}
	if output, err := runGitProbe(root, timeout, run, "status", "--porcelain=v1", "-z", "--untracked-files=all"); err == nil {
		metadata.initialDirty = parseDeltaGitStatusZ(output)
	}
	return metadata
}

func runGitProbe(root string, timeout time.Duration, run gitCommandRunner, args ...string) (string, error) {
	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()
	return run(ctx, root, args...)
}

func runGitCommand(ctx context.Context, root string, args ...string) (string, error) {
	cmd := exec.Command("git", args...)
	cmd.Dir = root
	var stdout bytes.Buffer
	var stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr
	if err := cmd.Start(); err != nil {
		return "", err
	}
	done := make(chan error, 1)
	go func() {
		done <- cmd.Wait()
	}()
	select {
	case err := <-done:
		if err != nil {
			return "", err
		}
		return stdout.String(), nil
	case <-ctx.Done():
		if cmd.Process != nil {
			_ = cmd.Process.Kill()
		}
		return "", ctx.Err()
	}
}

func parseDeltaGitStatusZ(output string) []string {
	var paths []string
	fields := splitNUL(output)
	for i := 0; i < len(fields); i++ {
		field := fields[i]
		if len(field) < 4 {
			continue
		}
		code := strings.TrimSpace(field[:2])
		if code == "" {
			continue
		}
		path := field[3:]
		if (strings.HasPrefix(code, "R") || strings.HasPrefix(code, "C")) && i+1 < len(fields) {
			i++
		}
		path = filepath.ToSlash(strings.TrimSpace(path))
		if path != "" {
			paths = append(paths, path)
		}
	}
	return uniqueDeltaStrings(paths)
}

func splitNUL(output string) []string {
	raw := strings.Split(output, "\x00")
	fields := make([]string, 0, len(raw))
	for _, field := range raw {
		if field != "" {
			fields = append(fields, field)
		}
	}
	return fields
}

func uniqueDeltaStrings(values []string) []string {
	seen := map[string]bool{}
	out := make([]string, 0, len(values))
	for _, value := range values {
		if value == "" || seen[value] {
			continue
		}
		seen[value] = true
		out = append(out, value)
	}
	return out
}

func deltaAppendCommand(args []string, stdout io.Writer, stderr io.Writer, paths rt.Paths) int {
	fs := flag.NewFlagSet("delta append", flag.ContinueOnError)
	fs.SetOutput(stderr)
	sessionID := fs.String("session", "", "Delta session id")
	packetFile := fs.String("packet-file", "", "Worker packet JSON")
	eventType := fs.String("event-type", "event", "Delta event type")
	originCommand := fs.String("origin-command", "", "Origin command")
	originLaneID := fs.String("origin-lane-id", "", "Origin lane id")
	phase := fs.String("phase", "", "Workflow phase")
	confidence := fs.String("confidence", "", "Confidence")
	var changedPaths stringList
	var readPaths stringList
	var behaviorSurfaces stringList
	var knownUnknowns stringList
	var verification stringList
	var generatedSurfaces stringList
	fs.Var(&changedPaths, "changed-path", "Changed path")
	fs.Var(&readPaths, "read-path", "Read path")
	fs.Var(&behaviorSurfaces, "behavior-surface", "Behavior surface")
	fs.Var(&knownUnknowns, "known-unknown", "Known unknown")
	fs.Var(&verification, "verification", "Verification evidence")
	fs.Var(&generatedSurfaces, "generated-surface", "Generated surface note")
	_ = fs.String("format", "json", "Output format")
	if err := fs.Parse(args); err != nil {
		return 2
	}

	var event delta.Event
	var err error
	if *packetFile != "" {
		event, err = delta.AppendPacketFile(paths.RuntimeDir, *sessionID, *packetFile)
	} else {
		event, err = delta.Append(delta.AppendInput{
			RuntimeDir:        paths.RuntimeDir,
			SessionID:         *sessionID,
			EventType:         *eventType,
			OriginCommand:     *originCommand,
			OriginLaneID:      *originLaneID,
			Phase:             *phase,
			ChangedPaths:      changedPaths,
			ReadPaths:         readPaths,
			BehaviorSurfaces:  behaviorSurfaces,
			GeneratedSurfaces: generatedSurfaces,
			KnownUnknowns:     knownUnknowns,
			Verification:      verification,
			Confidence:        *confidence,
		})
	}
	return writeCommandResult(stdout, stderr, paths, event, err)
}

func deltaStatusCommand(args []string, stdout io.Writer, stderr io.Writer, paths rt.Paths) int {
	fs := flag.NewFlagSet("delta status", flag.ContinueOnError)
	fs.SetOutput(stderr)
	sessionID := fs.String("session", "", "Delta session id")
	_ = fs.String("format", "json", "Output format")
	if err := fs.Parse(args); err != nil {
		return 2
	}
	bundle, err := delta.Load(paths.RuntimeDir, *sessionID)
	return writeCommandResult(stdout, stderr, paths, bundle, err)
}

func writeCommandResult(stdout io.Writer, stderr io.Writer, paths rt.Paths, payload any, err error) int {
	if errors.Is(err, rt.ErrUnsupportedLegacy) {
		return writeJSON(stdout, rt.UnsupportedLegacyPayload(paths))
	}
	if err != nil {
		fmt.Fprintf(stderr, "project-cognition: %v\n", err)
		return 1
	}
	return writeJSON(stdout, payload)
}

func writeJSON(w io.Writer, payload any) int {
	encoder := json.NewEncoder(w)
	encoder.SetIndent("", "  ")
	if err := encoder.Encode(payload); err != nil {
		fmt.Fprintf(os.Stderr, "project-cognition: encode json: %v\n", err)
		return 1
	}
	return 0
}

func writeCompactJSON(w io.Writer, payload any) int {
	encoder := json.NewEncoder(w)
	if err := encoder.Encode(payload); err != nil {
		fmt.Fprintf(os.Stderr, "project-cognition: encode json: %v\n", err)
		return 1
	}
	return 0
}

func writeErrorJSON(w io.Writer, payload any) int {
	if code := writeJSON(w, payload); code != 0 {
		return code
	}
	return 1
}
