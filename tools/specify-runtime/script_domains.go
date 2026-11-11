package main

import (
	"bytes"
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"time"
	"unicode"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/filelock"
	runtimecmd "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/specvalidate"
)

func runDiscussion(args []string, stdout io.Writer) int {
	projectRoot := optionValue(args, "--project-root", ".")
	if hasFlag(args, "--help") || hasFlag(args, "-h") {
		env := NewEnvelope("ok", "discussion command help")
		env.Data["commands"] = []string{
			"list",
			"init",
			"resolve",
			"status",
			"resume",
			"checkpoint",
			"import-material",
			"read-material",
			"validate-handoff",
			"write-handoff",
			"bind-consumer",
			"confirm-handoff",
			"mark-ready",
			"mark-consumed",
			"close",
			"archive",
		}
		env.Data["input_json"] = "inline JSON, @path, or - (stdin). On Windows PowerShell prefer @path or stdin because inline quoting often strips double quotes."
		env.Data["checkpoint"] = map[string]any{
			"usage":          "specify-runtime discussion checkpoint <slug> --expected-state-sha256 <sha256> --input-json <object|@path|-> [--summary <text>] [--phase <phase>] [--user-goal <text>] [--decision <text>]... [--recommendation <text>]",
			"persists":       append([]string{"summary", "lifecycle_phase"}, discussionCheckpointPacketKeys...),
			"unknown_fields": "rejected with invalid error (not silently dropped)",
		}
		env.Data["write_handoff"] = map[string]any{
			"usage":  "specify-runtime discussion write-handoff <slug> --expected-state-sha256 <sha256> --input-json <object|@path|->",
			"schema": "specify-runtime api schema discussion-write-handoff-input --format json",
		}
		env.Data["bind_consumer"] = map[string]any{
			"usage":  "specify-runtime discussion bind-consumer <slug> --feature-dir <feature-dir> --review-digest <digest> [--intake] --input-json <transition-fields>",
			"intake": "pins the confirmed source as pending before specification compilation; default binding validates the compiled specification before becoming ready",
		}
		return writeEnvelope(stdout, env)
	}
	mode := positionalArg(args, 0, "list")
	slug := positionalArg(args, 1, "")
	value := positionalArg(args, 2, "")
	includeAll := hasFlag(args, "--all")
	switch mode {
	case "import-material", "read-material":
		return runDiscussionMaterial(args, stdout, mode, slug, projectRoot)
	case "init":
		if hasFlag(args, "--slug") {
			topic := slug
			slug = optionValue(args, "--slug", topic)
			value = topic
		} else if value == "" {
			value = slug
		}
	case "resume":
		mode = "resume-context"
	case "resolve":
		intent := strings.ToLower(strings.TrimSpace(optionValue(args, "--intent", "continue")))
		selectedSlug := strings.TrimSpace(optionValue(args, "--slug", slug))
		service := discussionService{projectRoot: projectRoot}
		data, resolved, err := service.resolve(intent, selectedSlug)
		if err != nil {
			return writeEnvelope(stdout, scriptDomainError("discussion", err))
		}
		status := "ok"
		summary := "discussion selection resolved"
		if !resolved {
			status = "blocked"
			summary = "discussion selection is ambiguous or unavailable"
		}
		env := NewEnvelope(status, summary)
		env.Data = data
		if candidates, ok := data["candidates"].([]any); ok {
			env.Items = candidates
		}
		return writeEnvelope(stdout, env)
	case "checkpoint":
		changes, err := resolveDiscussionCheckpointInput(args, projectRoot, value)
		if err != nil {
			return writeEnvelope(stdout, discussionCheckpointError(slug, err))
		}
		encoded, err := json.Marshal(changes)
		if err != nil {
			return writeEnvelope(stdout, discussionCheckpointError(slug, err))
		}
		value = string(encoded)
	case "validate-handoff":
		value = optionValue(args, "--mode", defaultString(value, "ready"))
	case "write-handoff":
		if hasFlag(args, "--input") || value != "" {
			return writeEnvelope(stdout, scriptDomainError("discussion", fmt.Errorf("write-handoff does not accept agent-authored input files via --input or positional paths; pass the draft with --input-json (inline, @path, or - for stdin)")))
		}
		if !hasFlag(args, "--input-json") || strings.TrimSpace(optionValue(args, "--input-json", "")) == "" {
			return writeEnvelope(stdout, scriptDomainError("discussion", fmt.Errorf("write-handoff requires --input-json (inline, @path, or - for stdin)")))
		}
		raw, err := resolveAgentJSONInputBytes(optionValue(args, "--input-json", ""), projectRoot, "discussion write-handoff")
		if err != nil {
			return writeEnvelope(stdout, scriptDomainError("discussion", err))
		}
		mode = "write-handoff-json"
		value = string(raw)
	case "bind-consumer":
		if hasFlag(args, "--input") || value != "" {
			return writeEnvelope(stdout, scriptDomainError("discussion", fmt.Errorf("bind-consumer does not accept agent-authored input files via --input or positional paths; pass transition fields with --input-json (inline, @path, or - for stdin)")))
		}
		featureDir := strings.TrimSpace(optionValue(args, "--feature-dir", ""))
		if featureDir == "" || !hasFlag(args, "--input-json") || strings.TrimSpace(optionValue(args, "--input-json", "")) == "" {
			return writeEnvelope(stdout, scriptDomainError("discussion", fmt.Errorf("bind-consumer requires --feature-dir and --input-json (inline, @path, or - for stdin)")))
		}
		raw, err := resolveAgentJSONInputBytes(optionValue(args, "--input-json", ""), projectRoot, "discussion bind-consumer")
		if err != nil {
			return writeEnvelope(stdout, scriptDomainError("discussion", err))
		}
		input, err := decodeDiscussionHandoffPayload(raw)
		if err != nil {
			return writeEnvelope(stdout, scriptDomainError("discussion", err))
		}
		service := discussionService{
			projectRoot:          projectRoot,
			expectedReviewDigest: strings.TrimSpace(optionValue(args, "--review-digest", "")),
			consumerIntake:       hasFlag(args, "--intake"),
		}
		var data map[string]any
		err = service.withMutationLock("bind-consumer", slug, func() error {
			var bindErr error
			data, bindErr = service.bindConsumer(slug, featureDir, input)
			return bindErr
		})
		if err != nil {
			return writeEnvelope(stdout, scriptDomainError("discussion", err))
		}
		env := NewEnvelope("ok", "discussion consumer binding completed")
		env.Data = data
		if pathValue, ok := data["consumer_handoff_path"].(string); ok {
			env.ShowArgv = []string{"specify-runtime", "artifact", "show", "--path", pathValue, "--view", "summary", "--format", "json"}
		}
		return writeEnvelope(stdout, env)
	case "confirm-handoff":
		value = optionValue(args, "--digest", value)
	case "mark-consumed":
		value = optionValue(args, "--feature-dir", value)
	case "close":
		value = optionValue(args, "--status", value)
	}
	service := discussionService{
		projectRoot:         projectRoot,
		expectedStateSHA256: strings.TrimSpace(optionValue(args, "--expected-state-sha256", "")),
	}
	env, err := service.run(mode, slug, value, includeAll)
	if err != nil {
		if mode == "checkpoint" {
			return writeEnvelope(stdout, discussionCheckpointError(slug, err))
		}
		return writeEnvelope(stdout, scriptDomainError("discussion", err))
	}
	return writeEnvelope(stdout, env)
}

func runQuick(args []string, stdout io.Writer) int {
	projectRoot := optionValue(args, "--project-root", ".")
	if hasFlag(args, "--help") || hasFlag(args, "-h") {
		env := NewEnvelope("ok", "quick command help")
		env.Data["commands"] = []string{
			"list",
			"preflight",
			"status",
			"resume",
			"close",
			"archive",
			"cognition-closeout",
			"checkpoint-stage",
			"checkpoint-confirm",
			"checkpoint-show",
			"item-start",
			"allow-inline",
			"item-accept",
			"item-status",
			"packet-compile",
		}
		env.Data["close_usage"] = "specify-runtime quick close <id> resolved|blocked"
		env.Data["preflight_usage"] = "specify-runtime quick preflight [<id>] [--current-work-id <work-id>] --format json"
		env.Data["item_start_usage"] = "specify-runtime quick item-start <id> --item Qn [--current-work-id <work-id> --current-work-fence <fence>] --format json"
		env.Data["item_start_requires"] = "active matching Work identity plus an all-or-none confirmed claim over the complete Q write_scope before in_progress"
		env.Data["cognition_closeout_usage"] = "specify-runtime quick cognition-closeout <id> --result-state ready|no_op|mark-dirty|partial [--reason <text>] [--evidence-json <array>] [--update-id <id>] [--binding-id <sealed-joined-Quick-binding-for-mark-dirty>] --format json"
		env.Data["item_accept_usage"] = "specify-runtime quick item-accept <id> --item Qn --evidence <text> [--allow-inline --reason <spawn_failed:...>] --format json"
		env.Data["item_accept_requires"] = "matching worker-results/<lane-id>.json from result submit, or prior allow-inline / --allow-inline after spawn/tool failure; docs-only is invalid"
		env.Data["allow_inline_usage"] = "specify-runtime quick allow-inline <id> --item Qn --reason 'spawn_failed: ...' --format json"
		addQuickHelpOutputContracts(env.Data)
		return writeEnvelope(stdout, env)
	}
	mode := positionalArg(args, 0, "list")
	quickID := positionalArg(args, 1, "")
	if mode == "resume" {
		mode = "status"
	}
	service := quickService{projectRoot: projectRoot}
	switch strings.ToLower(strings.TrimSpace(mode)) {
	case "preflight":
		env, err := service.runPreflight(quickID, args)
		if err != nil {
			return writeEnvelope(stdout, scriptDomainError("quick", err))
		}
		return writeEnvelope(stdout, env)
	case "checkpoint-stage", "checkpoint-confirm", "checkpoint-show":
		env, err := service.runCheckpoint(mode, quickID, args)
		if err != nil {
			return writeEnvelope(stdout, scriptDomainError("quick", err))
		}
		return writeEnvelope(stdout, env)
	case "item-start", "allow-inline", "item-accept", "item-status", "packet-compile":
		env, err := service.runExecution(mode, quickID, args)
		if err != nil {
			return writeEnvelope(stdout, scriptDomainError("quick", err))
		}
		return writeEnvelope(stdout, env)
	case "cognition-closeout":
		env, err := service.runCognitionCloseout(quickID, args)
		if err != nil {
			return writeEnvelope(stdout, scriptDomainError("quick", err))
		}
		return writeEnvelope(stdout, env)
	}
	targetStatus := optionValue(args, "--status", positionalArg(args, 2, ""))
	includeAll := hasFlag(args, "--all")
	if strings.EqualFold(mode, "close") && strings.TrimSpace(targetStatus) == "" {
		return writeEnvelope(stdout, scriptDomainError("quick", fmt.Errorf("close requires status resolved or blocked; example: specify-runtime quick close %s resolved", firstNonEmpty(quickID, "<id>"))))
	}
	env, err := service.run(mode, quickID, targetStatus, includeAll)
	if err != nil {
		return writeEnvelope(stdout, scriptDomainError("quick", err))
	}
	return writeEnvelope(stdout, env)
}

func runPRDScan(args []string, stdout io.Writer) int {
	projectRoot := optionValue(args, "--project-root", ".")
	operation := positionalArg(args, 0, "")
	if strings.HasPrefix(operation, "record-") {
		runID := positionalArg(args, 1, "")
		surface := optionValue(args, "--surface", "")
		service := prdService{projectRoot: projectRoot}
		var data map[string]any
		var err error
		switch operation {
		case "record-upsert":
			var record map[string]any
			record, err = readAgentJSONObject(args, projectRoot, "prd-scan record-upsert")
			if err == nil {
				data, err = service.upsertRecord(runID, surface, optionValue(args, "--expected-sha256", ""), record)
			}
		case "record-remove":
			data, err = service.removeRecord(runID, surface, optionValue(args, "--record-id", ""), optionValue(args, "--expected-sha256", ""))
		case "record-show":
			data, err = service.showRecord(runID, surface, optionValue(args, "--record-id", ""))
		case "record-list":
			limit, parseErr := parseArtifactPositiveInt(optionValue(args, "--limit", "100"), "--limit")
			if parseErr != nil {
				err = parseErr
			} else {
				data, err = service.listRecords(runID, surface, limit)
			}
		default:
			err = fmt.Errorf("unknown PRD record operation %q", operation)
		}
		if err != nil {
			return writeEnvelope(stdout, scriptDomainError("prd", err))
		}
		env := NewEnvelope("ok", "prd record command completed")
		env.Data = data
		return writeEnvelope(stdout, env)
	}
	mode := "init-scan"
	if hasFlag(args, "--status") {
		mode = "status-scan"
	}
	runSlug := positionalArg(args, 0, "prd-run")
	if runSlug == "init" || runSlug == "init-scan" || runSlug == "status" || runSlug == "status-scan" || runSlug == "finalize" || runSlug == "finalize-scan" {
		mode = runSlug
		runSlug = positionalArg(args, 1, "prd-run")
	}
	service := prdService{projectRoot: projectRoot}
	env, err := service.runScan(mode, runSlug)
	if err != nil {
		return writeEnvelope(stdout, scriptDomainError("prd", err))
	}
	return writeEnvelope(stdout, env)
}

func runPRDBuild(args []string, stdout io.Writer) int {
	projectRoot := optionValue(args, "--project-root", ".")
	operation := positionalArg(args, 0, "")
	if operation == "scaffold" {
		runID := positionalArg(args, 1, "")
		service := prdService{projectRoot: projectRoot}
		data, err := service.scaffoldBuild(runID)
		if err != nil {
			return writeEnvelope(stdout, scriptDomainError("prd", err))
		}
		env := NewEnvelope("ok", "prd build scaffold completed")
		env.Data = data
		return writeEnvelope(stdout, env)
	}
	mode := "status-build"
	runID := positionalArg(args, 0, "")
	if runID == "status-build" {
		runID = positionalArg(args, 1, "")
	}
	service := prdService{projectRoot: projectRoot}
	env, err := service.runBuild(mode, runID)
	if err != nil {
		return writeEnvelope(stdout, scriptDomainError("prd", err))
	}
	return writeEnvelope(stdout, env)
}

func scriptDomainError(domain string, err error) Envelope {
	status := "blocked"
	code := domain + "-state-error"
	message := domain + " state command failed"
	if err != nil {
		text := strings.ToLower(err.Error())
		switch {
		case strings.Contains(text, "unknown fields"),
			strings.Contains(text, "must be a json object"),
			strings.Contains(text, "requires --input-json"),
			strings.Contains(text, "does not accept agent-authored"),
			strings.Contains(text, "invalid checkpoint lifecycle phase"):
			status = "invalid"
			code = domain + "-input-invalid"
			message = domain + " input is invalid"
		}
	}
	env := NewEnvelope(status, message)
	env.Blockers = append(env.Blockers, err.Error())
	env.Data["error_code"] = code
	bindRunControlStoreAccess(&env, err)
	return env
}

func discussionCheckpointError(slug string, err error) Envelope {
	env := scriptDomainError("discussion", err)
	env.Data["checkpoint_saved"] = false
	env.Data["pending_progress"] = "retain-in-memory"
	if env.Status == "invalid" {
		env.Data["recovery_kind"] = "inspect-schema-and-retry"
		env.ShowArgv = []string{
			"specify-runtime", "api", "schema", "discussion-checkpoint-input", "--format", "json",
		}
		return env
	}

	if discussionCheckpointNeedsResolveRetry(err) {
		env.Data["recovery_kind"] = "resolve-session-and-retry"
		env.NextArgv = []string{
			"specify-runtime", "discussion", "resolve", "--intent", "continue",
		}
		if strings.TrimSpace(slug) != "" {
			env.NextArgv = append(env.NextArgv, "--slug", slug)
		}
		env.NextArgv = append(env.NextArgv, "--format", "json")
		return env
	}

	env.Data["recovery_kind"] = "report-blocker"
	return env
}

func discussionCheckpointNeedsResolveRetry(err error) bool {
	if err == nil {
		return false
	}
	text := strings.ToLower(err.Error())
	return strings.Contains(text, "discussion focus binding is stale") ||
		strings.Contains(text, "state_sha256") ||
		strings.Contains(text, "--expected-state-sha256 from discussion resolve or resume")
}

func positionalArg(args []string, index int, fallback string) string {
	values := make([]string, 0, len(args))
	for i := 0; i < len(args); i++ {
		if strings.HasPrefix(args[i], "--") {
			if scriptOptionTakesValue(args[i]) && i+1 < len(args) {
				i++
			}
			continue
		}
		if args[i] == "-h" {
			continue
		}
		values = append(values, args[i])
	}
	if index >= len(values) || strings.TrimSpace(values[index]) == "" {
		return fallback
	}
	return strings.TrimSpace(values[index])
}

func scriptOptionTakesValue(name string) bool {
	switch name {
	case "--project-root",
		"--format",
		"--slug",
		"--intent",
		"--summary",
		"--phase",
		"--decision",
		"--recommendation",
		"--mode",
		"--input",
		"--input-json",
		"--digest",
		"--review-digest",
		"--expected-state-sha256",
		"--current-work-id",
		"--current-work-fence",
		"--feature-dir",
		"--surface",
		"--record-id",
		"--expected-sha256",
		"--limit",
		"--status":
		return true
	default:
		return false
	}
}

func nowUTCString() string {
	return time.Now().UTC().Truncate(time.Second).Format(time.RFC3339)
}

func writeScriptJSONFile(path string, payload any) error {
	raw, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	return atomicWriteFile(path, append(raw, '\n'), 0o644)
}

func writeScriptTextFile(path, content string) error {
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	return atomicWriteFile(path, []byte(content), 0o644)
}

func writeFileIfMissing(path, content string) error {
	if _, err := os.Stat(path); err == nil {
		return nil
	} else if !os.IsNotExist(err) {
		return err
	}
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	return writeCreateOnly(path, []byte(content))
}

func canonicalJSON(value any) ([]byte, error) {
	var buf bytes.Buffer
	encoder := json.NewEncoder(&buf)
	encoder.SetEscapeHTML(false)
	if err := encoder.Encode(value); err != nil {
		return nil, err
	}
	return bytes.TrimSpace(buf.Bytes()), nil
}

func slugifyScript(value, fallback string, maxLen int) string {
	var builder strings.Builder
	previousDash := false
	for _, r := range strings.ToLower(strings.TrimSpace(value)) {
		if r > unicode.MaxASCII {
			continue
		}
		if (r >= 'a' && r <= 'z') || (r >= '0' && r <= '9') {
			builder.WriteRune(r)
			previousDash = false
			continue
		}
		if !previousDash {
			builder.WriteByte('-')
			previousDash = true
		}
	}
	slug := strings.Trim(builder.String(), "-")
	if slug == "" {
		slug = fallback
	}
	if maxLen > 0 && len(slug) > maxLen {
		slug = strings.TrimRight(slug[:maxLen], "-")
	}
	if slug == "" {
		return fallback
	}
	return slug
}

func absProjectRoot(projectRoot string) (string, error) {
	root, err := filepath.Abs(projectRoot)
	if err != nil {
		return "", err
	}
	return filepath.EvalSymlinks(root)
}

func safeProjectContainedPath(projectRoot, raw string) (string, error) {
	root, err := absProjectRoot(projectRoot)
	if err != nil {
		return "", err
	}
	if strings.TrimSpace(raw) == "" {
		return "", fmt.Errorf("path is required")
	}
	candidate := filepath.FromSlash(raw)
	if !filepath.IsAbs(candidate) && filepath.VolumeName(candidate) == "" {
		candidate = filepath.Join(root, candidate)
	}
	resolved, err := filepath.Abs(candidate)
	if err != nil {
		return "", err
	}
	rel, err := filepath.Rel(root, resolved)
	if err != nil || rel == ".." || strings.HasPrefix(rel, ".."+string(filepath.Separator)) {
		return "", fmt.Errorf("path must stay inside the project root")
	}
	return resolved, nil
}

func relativeToProject(projectRoot, path string) (string, error) {
	root, err := absProjectRoot(projectRoot)
	if err != nil {
		return "", err
	}
	rel, err := filepath.Rel(root, path)
	if err != nil {
		return "", err
	}
	return filepath.ToSlash(rel), nil
}

type discussionService struct {
	projectRoot          string
	expectedStateSHA256  string
	expectedReviewDigest string
	consumerIntake       bool
}

var discussionMutationBarrierForTest func(mode, slug string)

var discussionIncompleteStatuses = map[string]bool{"active": true, "blocked": true, "handoff-ready": true}
var discussionTerminalStatuses = map[string]bool{"completed": true, "abandoned": true}
var discussionLifecyclePhases = map[string]bool{"explore": true, "ground": true, "decide": true, "prepare": true, "review": true, "ready": true, "consumed": true, "closed": true}
var discussionMutationModes = map[string]bool{
	"archive":            true,
	"bind-consumer":      true,
	"checkpoint":         true,
	"close":              true,
	"confirm-handoff":    true,
	"init":               true,
	"mark-consumed":      true,
	"mark-ready":         true,
	"rebuild-index":      true,
	"write-handoff-json": true,
}

func (service discussionService) run(mode, slug, value string, includeAll bool) (Envelope, error) {
	var data map[string]any
	normalizedMode := strings.ToLower(strings.TrimSpace(mode))
	action := func() error {
		var err error
		switch normalizedMode {
		case "init":
			data, err = service.initialize(slug, value)
		case "list":
			data, err = service.list(includeAll)
		case "status":
			data, err = service.status(slug)
		case "resume-context":
			data, err = service.resume(slug)
		case "checkpoint":
			var changes map[string]any
			if err = json.Unmarshal([]byte(defaultString(value, "{}")), &changes); err != nil || changes == nil {
				if err == nil {
					err = fmt.Errorf("checkpoint payload must be an object")
				}
				return err
			}
			data, err = service.checkpoint(slug, changes)
		case "write-handoff-json":
			payload, parseErr := decodeDiscussionHandoffPayload([]byte(value))
			if parseErr != nil {
				return parseErr
			}
			data, err = service.writeHandoff(slug, payload)
		case "validate-handoff":
			data, err = service.validateHandoff(slug, defaultString(value, "ready"))
		case "confirm-handoff":
			data, err = service.confirmHandoff(slug, value)
		case "mark-ready":
			data, err = service.markReady(slug)
		case "mark-consumed":
			data, err = service.markConsumed(slug, value)
		case "close":
			data, err = service.close(slug, strings.ToLower(value))
		case "archive":
			data, err = service.archive(slug)
		case "rebuild-index":
			data, err = service.writeIndex()
		default:
			return fmt.Errorf("unknown mode: %s", mode)
		}
		return err
	}
	if discussionMutationModes[normalizedMode] {
		if err := service.withMutationLock(normalizedMode, slug, action); err != nil {
			return Envelope{}, err
		}
	} else {
		if err := action(); err != nil {
			return Envelope{}, err
		}
	}
	env := NewEnvelope("ok", "discussion state command completed")
	env.Data = data
	return env, nil
}

func (service discussionService) withMutationLock(mode, slug string, action func() error) error {
	projectRoot, err := filepath.Abs(service.projectRoot)
	if err != nil {
		return fmt.Errorf("cannot resolve discussion project root: %w", err)
	}
	lockDir, err := secureProjectPath(projectRoot, ".specify/runtime/discussion")
	if err != nil {
		return fmt.Errorf("cannot resolve discussion lock directory: %w", err)
	}
	if err := os.MkdirAll(lockDir, 0o755); err != nil {
		return fmt.Errorf("cannot create discussion lock directory: %w", err)
	}
	lockPath, err := secureProjectPath(projectRoot, ".specify/runtime/discussion/mutation.lock")
	if err != nil {
		return fmt.Errorf("cannot resolve discussion mutation lock: %w", err)
	}
	if err := ensureDiscussionMutationLockByte(lockPath); err != nil {
		return err
	}
	release, err := filelock.Acquire(lockPath)
	if err != nil {
		return fmt.Errorf("cannot acquire discussion mutation lock: %w", err)
	}
	defer release()
	if discussionMutationBarrierForTest != nil {
		discussionMutationBarrierForTest(mode, slug)
	}
	return action()
}

func ensureDiscussionMutationLockByte(lockPath string) error {
	lockFile, err := os.OpenFile(lockPath, os.O_CREATE|os.O_RDWR, 0o600)
	if err != nil {
		return fmt.Errorf("cannot initialize discussion mutation lock: %w", err)
	}
	info, err := lockFile.Stat()
	if err == nil && info.Size() == 0 {
		_, err = lockFile.WriteAt([]byte{0}, 0)
	}
	closeErr := lockFile.Close()
	if err != nil {
		return fmt.Errorf("cannot initialize discussion mutation lock byte: %w", err)
	}
	if closeErr != nil {
		return fmt.Errorf("cannot close discussion mutation lock: %w", closeErr)
	}
	return nil
}

func decodeDiscussionHandoffPayload(raw []byte) (map[string]any, error) {
	const maxDiscussionHandoffBytes = 16 * 1024 * 1024
	if len(raw) == 0 {
		return nil, fmt.Errorf("handoff input must not be empty")
	}
	if len(raw) > maxDiscussionHandoffBytes {
		return nil, fmt.Errorf("handoff input exceeds %d bytes", maxDiscussionHandoffBytes)
	}
	return decodeAgentJSONObject(raw, "handoff")
}

// discussionCheckpointPacketKeys are turn_packet fields agents may update via checkpoint.
var discussionCheckpointPacketKeys = specvalidate.DiscussionCheckpointFields()

var discussionCheckpointMetaKeys = map[string]bool{
	"summary":         true,
	"lifecycle_phase": true,
	"phase":           true, // alias for lifecycle_phase
}

var discussionCheckpointEnumFields = map[string]map[string]bool{
	"truth_pass_status":         {"not-needed": true, "needed": true, "in-progress": true, "complete": true, "blocked": true},
	"discussion_compass_status": {"current": true, "stale": true, "missing": true},
	"ui_discussion_status":      {"not_applicable": true, "offered": true, "accepted": true, "skipped": true, "completed": true, "deferred": true},
}

var discussionCheckpointEnumFieldOrder = []string{
	"truth_pass_status",
	"discussion_compass_status",
	"ui_discussion_status",
}

var discussionAdviceConfidenceLevels = map[string]bool{
	"blocked": true,
	"high":    true,
	"low":     true,
	"medium":  true,
	"none":    true,
}

var discussionCheckpointStringListFields = []string{
	"confirmed_decisions",
	"changed_recommendations",
	"next_discussion_paths",
	"allowed_actions",
	"artifact_refs",
}

var discussionCheckpointArrayFields = []string{
	"blocking_unknowns",
	"soft_unknowns",
	"conflicts",
	"open_assumptions",
	"open_questions",
	"verified_fact_refs",
}

var discussionCheckpointObjectFields = []string{
	"context_boundary",
	"implementation_target",
	"downstream_instructions",
	"discussion_decision_digest",
	"design_context",
}

var discussionSourceEvidenceStatuses = map[string]bool{
	"assumption":     true,
	"confirmed":      true,
	"conflict":       true,
	"inferred":       true,
	"missing":        true,
	"proven":         true,
	"stale-advisory": true,
	"verified":       true,
}

var discussionSourceMaterialStatuses = map[string]bool{
	"conflict":    true,
	"inspected":   true,
	"partial":     true,
	"pending":     true,
	"stale":       true,
	"unavailable": true,
}

var discussionSourceMaterialSensitivities = map[string]bool{
	"restricted": true,
	"safe":       true,
	"sanitized":  true,
}

func resolveDiscussionCheckpointInput(args []string, projectRoot, positional string) (map[string]any, error) {
	changes := map[string]any{}
	switch {
	case hasFlag(args, "--input-json"):
		raw, err := resolveAgentJSONInputBytes(optionValue(args, "--input-json", ""), projectRoot, "discussion checkpoint")
		if err != nil {
			return nil, err
		}
		decoded, err := decodeAgentJSONObject(raw, "discussion checkpoint")
		if err != nil {
			return nil, err
		}
		changes = decoded
	case !hasFlag(args, "--summary") && strings.TrimSpace(positional) != "":
		decoded, err := decodeAgentJSONObject([]byte(positional), "discussion checkpoint")
		if err != nil {
			return nil, err
		}
		changes = decoded
	}

	if hasFlag(args, "--summary") {
		changes["summary"] = optionValue(args, "--summary", "")
	}
	if phase := strings.TrimSpace(optionValue(args, "--phase", "")); phase != "" {
		changes["lifecycle_phase"] = strings.ToLower(phase)
	}
	if decisions := optionValues(args, "--decision"); len(decisions) > 0 {
		changes["confirmed_decisions"] = decisions
	}
	if recommendation := strings.TrimSpace(optionValue(args, "--recommendation", "")); recommendation != "" {
		changes["current_recommendation"] = recommendation
	}
	if goal := strings.TrimSpace(optionValue(args, "--user-goal", "")); goal != "" {
		changes["user_goal"] = goal
	}
	return changes, nil
}

func validateDiscussionCheckpointFields(changes map[string]any) error {
	known := map[string]bool{}
	for key := range discussionCheckpointMetaKeys {
		known[key] = true
	}
	for _, key := range discussionCheckpointPacketKeys {
		known[key] = true
	}
	unknown := []string{}
	for key := range changes {
		if !known[key] {
			unknown = append(unknown, key)
		}
	}
	sort.Strings(unknown)
	if len(unknown) > 0 {
		accepted := append([]string{}, discussionCheckpointPacketKeys...)
		accepted = append(accepted, "summary", "lifecycle_phase", "phase")
		sort.Strings(accepted)
		return fmt.Errorf(
			"discussion checkpoint unknown fields: %s; accepted fields: %s (unknown fields are rejected instead of silently dropped)",
			strings.Join(unknown, ", "),
			strings.Join(accepted, ", "),
		)
	}
	if value, ok := changes["advice_confidence"]; ok {
		if err := validateDiscussionCheckpointAdviceConfidence(value); err != nil {
			return err
		}
	}
	if value, ok := changes["source_evidence"]; ok {
		errors := []map[string]string{}
		validateObjectList(value, []string{"source_type", "evidence_status", "source", "claim"}, "source_evidence", &errors)
		if len(errors) > 0 {
			return fmt.Errorf("%s", strings.Join(discussionErrorCodes(errors), ", "))
		}
	}
	return nil
}

func validateDiscussionCheckpointAdviceConfidence(value any) error {
	if confidence := mapValue(value); confidence != nil {
		if !discussionAdviceConfidenceLevels[strings.TrimSpace(stringValue(confidence["level"]))] {
			return fmt.Errorf("discussion checkpoint advice_confidence.level must be none, low, medium, high, or blocked")
		}
		if strings.TrimSpace(stringValue(confidence["reason"])) == "" {
			return fmt.Errorf("discussion checkpoint advice_confidence.reason is required")
		}
		return nil
	}
	if !discussionAdviceConfidenceLevels[strings.TrimSpace(stringValue(value))] {
		return fmt.Errorf("discussion checkpoint advice_confidence must be none, low, medium, high, or blocked")
	}
	return nil
}

func validateDiscussionCheckpointSemantics(changes map[string]any) error {
	errors := []string{}
	for _, field := range []string{"user_goal", "turn_class", "current_decision_frame", "current_recommendation", "next_gate"} {
		if value, exists := changes[field]; exists && strings.TrimSpace(stringValue(value)) == "" {
			errors = append(errors, field+" must be a non-empty string")
		}
	}
	for _, field := range discussionCheckpointEnumFieldOrder {
		allowed := discussionCheckpointEnumFields[field]
		if value, exists := changes[field]; exists && !allowed[strings.TrimSpace(stringValue(value))] {
			errors = append(errors, field+" has an invalid value")
		}
	}

	if confidence, exists := changes["advice_confidence"]; exists {
		if object := mapValue(confidence); object != nil {
			if !discussionAdviceConfidenceLevels[strings.TrimSpace(stringValue(object["level"]))] {
				errors = append(errors, "advice_confidence.level has an invalid value")
			}
			if strings.TrimSpace(stringValue(object["reason"])) == "" {
				errors = append(errors, "advice_confidence.reason is required")
			}
		} else if !discussionAdviceConfidenceLevels[strings.TrimSpace(stringValue(confidence))] {
			errors = append(errors, "advice_confidence has an invalid value")
		}
	}

	for _, field := range discussionCheckpointStringListFields {
		value, exists := changes[field]
		if !exists {
			continue
		}
		if !discussionNonEmptyStringArray(value) {
			errors = append(errors, field+" must be an array of non-empty strings")
		}
	}

	for _, field := range discussionCheckpointArrayFields {
		if value, exists := changes[field]; exists {
			if _, ok := value.([]any); !ok {
				errors = append(errors, field+" must be an array")
			}
		}
	}
	for _, field := range discussionCheckpointObjectFields {
		if value, exists := changes[field]; exists && mapValue(value) == nil {
			errors = append(errors, field+" must be an object")
		}
	}

	if value, exists := changes["requirements_snapshot"]; exists {
		requirements := mapValue(value)
		if requirements == nil {
			errors = append(errors, "requirements_snapshot must be an object")
		} else {
			if err := validateDiscussionSourceRequirementShapes(requirements); err != nil {
				errors = append(errors, err.Error())
			}
			for _, field := range []string{"actors", "scenarios", "constraints", "success_criteria", "design_direction", "optimal_solution_approach", "non_goals"} {
				if item, exists := requirements[field]; exists && !discussionNonEmptyStringArray(item) {
					errors = append(errors, "requirements_snapshot."+field+" must be an array of non-empty strings")
				}
			}
			if scopeValue, exists := requirements["scope"]; exists {
				scope := mapValue(scopeValue)
				if scope == nil {
					errors = append(errors, "requirements_snapshot.scope must be an object")
				} else {
					for _, field := range []string{"in", "out", "deferred"} {
						if item, exists := scope[field]; exists && !discussionNonEmptyStringArray(item) {
							errors = append(errors, "requirements_snapshot.scope."+field+" must be an array of non-empty strings")
						}
					}
				}
			}
		}
	}

	if value, exists := changes["source_evidence"]; exists {
		structured := []map[string]string{}
		validateObjectList(value, []string{"source_type", "evidence_status", "source", "claim"}, "source_evidence", &structured)
		for index, item := range listValue(value) {
			evidence := mapValue(item)
			if evidence != nil && !discussionSourceEvidenceStatuses[strings.TrimSpace(stringValue(evidence["evidence_status"]))] {
				structured = append(structured, discussionError("invalid_source_evidence_status", fmt.Sprintf("source_evidence[%d].evidence_status is invalid", index)))
			}
		}
		appendDiscussionStructuredMessages(&errors, structured)
	}
	if value, exists := changes["source_materials"]; exists {
		normalizeDiscussionSourceMaterialDigests(value)
		structured := []map[string]string{}
		validateSourceMaterials(value, "in_progress", &structured)
		appendDiscussionStructuredMessages(&errors, structured)
	}
	if value, exists := changes["must_preserve"]; exists {
		structured := []map[string]string{}
		validateDiscussionMustPreserve(value, &structured)
		appendDiscussionStructuredMessages(&errors, structured)
	}
	for _, field := range []string{"blocking_unknowns", "soft_unknowns"} {
		if value, exists := changes[field]; exists {
			structured := []map[string]string{}
			validateDiscussionUnknownRecords(value, field, &structured)
			appendDiscussionStructuredMessages(&errors, structured)
		}
	}
	if value, exists := changes["conflicts"]; exists {
		structured := []map[string]string{}
		validateDiscussionConflictRecords(value, &structured)
		appendDiscussionStructuredMessages(&errors, structured)
	}

	if len(errors) > 0 {
		return fmt.Errorf("discussion checkpoint invalid semantic fields: %s", strings.Join(errors, "; "))
	}
	return nil
}

func appendDiscussionStructuredMessages(errors *[]string, structured []map[string]string) {
	for _, item := range structured {
		*errors = append(*errors, item["message"])
	}
}

func discussionNonEmptyStringArray(value any) bool {
	items, ok := value.([]any)
	if !ok {
		return false
	}
	for _, item := range items {
		if _, ok := item.(string); !ok || strings.TrimSpace(stringValue(item)) == "" {
			return false
		}
	}
	return true
}

func (service discussionService) root() (string, error) {
	return secureProjectPath(service.projectRoot, ".specify/discussions")
}

func (service discussionService) state(slug, topic string) map[string]any {
	ts := nowUTCString()
	if strings.TrimSpace(topic) == "" {
		topic = slug
	}
	return map[string]any{
		"version":           float64(3),
		"status_family":     "discussion",
		"slug":              slug,
		"topic":             topic,
		"status":            "active",
		"lifecycle_phase":   "explore",
		"summary":           topic,
		"created_at":        ts,
		"updated_at":        ts,
		"closed_at":         nil,
		"archived_at":       nil,
		"blocker_reason":    nil,
		"latest_checkpoint": nil,
		"next_command":      "none",
		"turn_packet": map[string]any{
			"version":                 float64(2),
			"discussion_slug":         slug,
			"lifecycle_phase":         "explore",
			"turn_class":              "product_intent",
			"user_goal":               topic,
			"current_decision_frame":  topic,
			"requirements_snapshot":   map[string]any{"target_need": topic, "actors": []any{}, "scenarios": []any{}, "scope": map[string]any{"in": []any{}, "out": []any{}, "deferred": []any{}}, "success_criteria": []any{}, "constraints": []any{}, "design_direction": []any{}, "optimal_solution_approach": []any{}, "non_goals": []any{}},
			"implementation_target":   map[string]any{"actual_project": nil, "target_root": nil, "target_paths": []any{}, "required_target_paths_to_verify": []any{}},
			"source_evidence":         []any{},
			"source_materials":        []any{},
			"blocking_unknowns":       []any{},
			"soft_unknowns":           []any{},
			"conflicts":               []any{},
			"downstream_instructions": map[string]any{"settled_decisions": []any{}, "preserved_assumptions": []any{}, "conflicts_requiring_return": []any{}, "capability_map": []any{}, "dependencies": []any{}, "planning_constraints": []any{}, "deferred_scope": []any{}, "reopen_conditions": []any{}},
			"discussion_decision_digest": map[string]any{
				"locked_direction": []any{}, "rejected_alternatives": []any{}, "accepted_tradeoffs": []any{}, "experience_commitments": []any{}, "design_system_requirements": []any{}, "design_system_status": "not-applicable", "design_risk_level": "none", "review_criteria_carried_forward": []any{}, "must_not_dilute": []any{},
			},
			"must_preserve":             []any{},
			"truth_pass_status":         "not-needed",
			"verified_project_facts":    []any{},
			"evidence_checked":          []any{},
			"advice_confidence":         "none",
			"discussion_compass_status": "missing",
			"next_discussion_paths":     []any{},
			"ui_discussion_status":      "not_applicable",
			"design_context":            map[string]any{"ui_involved": false},
			"artifact_refs":             []any{},
			"topic_ownership":           defaultDiscussionTopicOwnership(slug, topic),
			"confirmed_decisions":       []any{},
			"changed_recommendations":   []any{},
			"context_boundary": map[string]any{
				"status": "not-started", "current_project_root": nil, "current_project_roles": []any{},
				"target_project_root": nil, "target_project_roles": []any{}, "reference_sources": []any{},
				"external_systems": []any{}, "boundary_blockers": []any{}, "path_status": "unknown", "boundary_confidence": "unknown",
			},
			"verified_fact_refs":     []any{},
			"open_assumptions":       []any{},
			"open_questions":         []any{},
			"current_recommendation": "Shape the goal and context boundary.",
			"allowed_actions":        []any{"discuss", "ground", "checkpoint", "close"},
			"persistence_mode":       "frontstage-only",
			"next_gate":              "context-boundary",
		},
		"handoff": map[string]any{
			"review_status":        "not-started",
			"quality_gate_status":  "draft",
			"review_digest":        nil,
			"contract_path":        nil,
			"recommended_consumer": "continue-discussion",
		},
		"consumption": map[string]any{
			"status":        "not_consumed",
			"consumed_at":   nil,
			"consumer_path": nil,
		},
	}
}

func defaultDiscussionTopicOwnership(slug, topic string) map[string]any {
	owned := strings.TrimSpace(topic)
	if owned == "" {
		owned = slug
	}
	return map[string]any{
		"owner_slug":    slug,
		"anchor":        slug,
		"owned_scope":   []any{owned},
		"routed_topics": []any{},
	}
}

var discussionTopicRoutes = map[string]bool{
	"continue_current": true,
	"branch_new":       true,
	"link_existing":    true,
	"defer":            true,
}

func normalizeDiscussionTopicOwnership(value any, slug, topic string) (map[string]any, error) {
	ownership := mapValue(value)
	if ownership == nil {
		ownership = defaultDiscussionTopicOwnership(slug, topic)
	} else {
		ownership = cloneAnyMap(ownership)
	}
	if owner := strings.TrimSpace(stringValue(ownership["owner_slug"])); owner != "" && owner != slug {
		return nil, fmt.Errorf("topic_ownership.owner_slug must match discussion slug")
	}
	ownership["owner_slug"] = slug
	if strings.TrimSpace(stringValue(ownership["anchor"])) == "" {
		ownership["anchor"] = slug
	}
	ownedScope, ok := ownership["owned_scope"].([]any)
	if !ok || len(ownedScope) == 0 {
		return nil, fmt.Errorf("topic_ownership.owned_scope must be a non-empty array")
	}
	for index, item := range ownedScope {
		if strings.TrimSpace(stringValue(item)) == "" {
			return nil, fmt.Errorf("topic_ownership.owned_scope[%d] must be non-empty", index)
		}
	}
	routes, ok := ownership["routed_topics"].([]any)
	if !ok {
		return nil, fmt.Errorf("topic_ownership.routed_topics must be an array")
	}
	for index, item := range routes {
		route := mapValue(item)
		if route == nil {
			return nil, fmt.Errorf("topic_ownership.routed_topics[%d] must be an object", index)
		}
		if strings.TrimSpace(stringValue(route["topic"])) == "" {
			return nil, fmt.Errorf("topic_ownership.routed_topics[%d].topic is required", index)
		}
		action := strings.TrimSpace(stringValue(route["route"]))
		if !discussionTopicRoutes[action] {
			return nil, fmt.Errorf("topic_ownership.routed_topics[%d].route must be continue_current, branch_new, link_existing, or defer", index)
		}
		if (action == "branch_new" || action == "link_existing") && strings.TrimSpace(stringValue(route["target_slug"])) == "" {
			return nil, fmt.Errorf("topic_ownership.routed_topics[%d].target_slug is required for %s", index, action)
		}
	}
	return ownership, nil
}

func normalizeDiscussionState(state map[string]any) {
	if intValue(state["version"]) < 3 {
		state["version"] = float64(3)
	}
	packet := mapValue(state["turn_packet"])
	if packet == nil {
		return
	}
	ensureDiscussionTurnPacketDefaults(packet, stringValue(state["slug"]), firstNonEmpty(stringValue(state["topic"]), stringValue(state["summary"]), stringValue(state["slug"])))
	ownership, err := normalizeDiscussionTopicOwnership(
		packet["topic_ownership"],
		stringValue(state["slug"]),
		firstNonEmpty(stringValue(state["topic"]), stringValue(state["summary"])),
	)
	if err == nil {
		packet["topic_ownership"] = ownership
	}
}

func ensureDiscussionTurnPacketDefaults(packet map[string]any, slug, topic string) {
	packet["version"] = float64(2)
	if strings.TrimSpace(stringValue(packet["discussion_slug"])) == "" {
		packet["discussion_slug"] = slug
	}
	if strings.TrimSpace(stringValue(packet["lifecycle_phase"])) == "" {
		packet["lifecycle_phase"] = "explore"
	}
	if strings.TrimSpace(stringValue(packet["turn_class"])) == "" {
		packet["turn_class"] = "product_intent"
	}
	if strings.TrimSpace(stringValue(packet["user_goal"])) == "" {
		packet["user_goal"] = topic
	}
	if strings.TrimSpace(stringValue(packet["current_decision_frame"])) == "" {
		packet["current_decision_frame"] = topic
	}
	defaults := map[string]any{
		"requirements_snapshot": map[string]any{"target_need": topic, "actors": []any{}, "scenarios": []any{}, "constraints": []any{}, "success_criteria": []any{}, "design_direction": []any{}, "optimal_solution_approach": []any{}, "non_goals": []any{}, "scope": map[string]any{"in": []any{}, "out": []any{}, "deferred": []any{}}},
		"implementation_target": map[string]any{"actual_project": nil, "target_root": nil, "target_paths": []any{}, "required_target_paths_to_verify": []any{}},
		"context_boundary": map[string]any{
			"status": "not-started", "current_project_root": nil, "current_project_roles": []any{},
			"target_project_root": nil, "target_project_roles": []any{}, "reference_sources": []any{},
			"external_systems": []any{}, "boundary_blockers": []any{}, "path_status": "unknown", "boundary_confidence": "unknown",
		},
		"source_evidence":            []any{},
		"source_materials":           []any{},
		"blocking_unknowns":          []any{},
		"soft_unknowns":              []any{},
		"conflicts":                  []any{},
		"downstream_instructions":    map[string]any{"settled_decisions": []any{}, "preserved_assumptions": []any{}, "conflicts_requiring_return": []any{}, "capability_map": []any{}, "dependencies": []any{}, "planning_constraints": []any{}, "deferred_scope": []any{}, "reopen_conditions": []any{}},
		"discussion_decision_digest": map[string]any{"locked_direction": []any{}, "rejected_alternatives": []any{}, "accepted_tradeoffs": []any{}, "experience_commitments": []any{}, "design_system_requirements": []any{}, "design_system_status": "not-applicable", "design_risk_level": "none", "review_criteria_carried_forward": []any{}, "must_not_dilute": []any{}},
		"must_preserve":              []any{},
		"truth_pass_status":          "not-needed",
		"verified_project_facts":     []any{},
		"evidence_checked":           []any{},
		"advice_confidence":          "none",
		"discussion_compass_status":  "missing",
		"next_discussion_paths":      []any{},
		"ui_discussion_status":       "not_applicable",
		"design_context":             map[string]any{"ui_involved": false},
		"artifact_refs":              []any{},
	}
	for key, value := range defaults {
		if existing, exists := packet[key]; exists {
			if existingMap := mapValue(existing); existingMap != nil {
				if defaultMap := mapValue(value); defaultMap != nil {
					mergeDiscussionDefaults(existingMap, defaultMap)
				}
			}
		} else {
			packet[key] = cloneAny(value)
		}
	}
	packet["source_materials"] = normalizeDiscussionSourceMaterials(listValue(packet["source_materials"]))
}

func mergeDiscussionDefaults(target, defaults map[string]any) {
	for key, value := range defaults {
		if existing, exists := target[key]; exists {
			if existingMap := mapValue(existing); existingMap != nil {
				if defaultMap := mapValue(value); defaultMap != nil {
					mergeDiscussionDefaults(existingMap, defaultMap)
				}
			}
			continue
		}
		if value == nil {
			target[key] = nil
		} else {
			target[key] = cloneAny(value)
		}
	}
}

func normalizeDiscussionSourceMaterials(items []any) []any {
	normalized := make([]any, 0, len(items))
	for _, item := range items {
		material := mapValue(item)
		if material == nil {
			normalized = append(normalized, item)
			continue
		}
		copy := cloneAnyMap(material)
		if strings.TrimSpace(stringValue(copy["material_type"])) == "" && strings.TrimSpace(stringValue(copy["source_type"])) != "" {
			copy["material_type"] = copy["source_type"]
			delete(copy, "source_type")
		}
		if strings.TrimSpace(stringValue(copy["locator"])) == "" && strings.TrimSpace(stringValue(copy["source"])) != "" {
			copy["locator"] = copy["source"]
			delete(copy, "source")
		}
		if digest, err := discussionSourceMaterialDigest(copy); err == nil {
			copy["material_digest"] = digest
		}
		normalized = append(normalized, copy)
	}
	return normalized
}

func (service discussionService) initialize(requestedSlug, topic string) (map[string]any, error) {
	root, err := service.root()
	if err != nil {
		return nil, err
	}
	if err := os.MkdirAll(root, 0o755); err != nil {
		return nil, err
	}
	base := slugifyScript(firstNonEmpty(requestedSlug, topic), "discussion", 72)
	existing, err := service.workspaceCandidates(true)
	if err != nil {
		return nil, err
	}
	names := map[string]bool{}
	for _, candidate := range existing {
		names[filepath.Base(candidate.path)] = true
	}
	slug := base
	for suffix := 2; names[slug]; suffix++ {
		slug = fmt.Sprintf("%s-%d", base, suffix)
	}
	workspace := filepath.Join(root, slug)
	if err := os.Mkdir(workspace, 0o755); err != nil {
		return nil, err
	}
	state := service.state(slug, firstNonEmpty(topic, requestedSlug, slug))
	if err := service.persistState(workspace, state); err != nil {
		return nil, err
	}
	if err := writeScriptTextFile(filepath.Join(workspace, "discussion-log.jsonl"), ""); err != nil {
		return nil, err
	}
	if _, err := service.writeIndex(); err != nil {
		return nil, err
	}
	binding, err := service.focusBinding(workspace, state)
	if err != nil {
		return nil, err
	}
	return map[string]any{"discussion": service.record(workspace, state, false), "slug": slug, "workspace_path": workspace, "binding": binding}, nil
}

type discussionCandidate struct {
	path     string
	archived bool
}

func (service discussionService) workspaceCandidates(includeArchived bool) ([]discussionCandidate, error) {
	root, err := service.root()
	if err != nil {
		return nil, err
	}
	var result []discussionCandidate
	if entries, err := os.ReadDir(root); err == nil {
		for _, entry := range entries {
			if entry.IsDir() && entry.Name() != "archive" {
				result = append(result, discussionCandidate{path: filepath.Join(root, entry.Name())})
			}
		}
	} else if !os.IsNotExist(err) {
		return nil, err
	}
	archiveRoot := filepath.Join(root, "archive")
	if includeArchived {
		if entries, err := os.ReadDir(archiveRoot); err == nil {
			for _, entry := range entries {
				if entry.IsDir() {
					result = append(result, discussionCandidate{path: filepath.Join(archiveRoot, entry.Name()), archived: true})
				}
			}
		} else if !os.IsNotExist(err) {
			return nil, err
		}
	}
	return result, nil
}

func (service discussionService) loadState(workspace string) (map[string]any, bool, error) {
	jsonPath := filepath.Join(workspace, "discussion-state.json")
	raw, err := os.ReadFile(jsonPath)
	if err == nil {
		var state map[string]any
		if err := json.Unmarshal(raw, &state); err != nil {
			return nil, false, err
		}
		if handoff, ok := state["handoff"].(map[string]any); ok {
			if _, exists := handoff["contract_path"]; !exists {
				handoff["contract_path"] = firstAny(handoff["json_path"], handoff["markdown_path"])
			}
			delete(handoff, "json_path")
			delete(handoff, "markdown_path")
		}
		normalizeDiscussionState(state)
		if err := validateDiscussionState(state); err != nil {
			return nil, false, err
		}
		return state, false, nil
	}
	if !os.IsNotExist(err) {
		return nil, false, err
	}
	raw, err = os.ReadFile(filepath.Join(workspace, "discussion-state.md"))
	if err != nil {
		return nil, false, fmt.Errorf("discussion state not found: %s", filepath.Base(workspace))
	}
	return service.legacyState(filepath.Base(workspace), string(raw)), true, nil
}

func (service discussionService) legacyState(workspaceName, text string) map[string]any {
	fields := extractMarkdownFields(text)
	slug := firstNonEmpty(fields["slug"], workspaceName)
	topic := firstNonEmpty(fields["current_topic"], fields["summary"], slug)
	state := service.state(slug, topic)
	status := strings.ToLower(firstNonEmpty(fields["status"], "active"))
	if !discussionIncompleteStatuses[status] && !discussionTerminalStatuses[status] {
		status = "active"
	}
	state["status"] = status
	state["summary"] = firstNonEmpty(fields["summary"], topic)
	state["updated_at"] = firstNonEmpty(fields["updated_at"], stringValue(state["updated_at"]))
	state["closed_at"] = noneIfPlaceholder(fields["closed_at"])
	state["archived_at"] = noneIfPlaceholder(fields["archived_at"])
	phase := firstNonEmpty(fields["lifecycle_phase"], legacyDiscussionPhase(fields["current_stage"], status))
	state["lifecycle_phase"] = phase
	packet := state["turn_packet"].(map[string]any)
	packet["lifecycle_phase"] = phase
	packet["current_decision_frame"] = firstNonEmpty(fields["current_decision_frame"], stringValue(state["summary"]))
	state["next_command"] = firstNonEmpty(fields["next_command"], "none")
	handoff := state["handoff"].(map[string]any)
	handoff["review_status"] = firstNonEmpty(fields["handoff_review_status"], "not-started")
	handoff["quality_gate_status"] = firstNonEmpty(fields["quality_gate_status"], "draft")
	handoff["contract_path"] = noneIfPlaceholder(firstNonEmpty(fields["handoff_contract"], fields["handoff_to_specify_json"], fields["handoff_to_specify"]))
	consumption := state["consumption"].(map[string]any)
	consumption["status"] = firstNonEmpty(fields["handoff_consumption_status"], "not_consumed")
	consumption["consumed_at"] = noneIfPlaceholder(fields["consumed_at"])
	consumption["consumer_path"] = noneIfPlaceholder(fields["consumed_by_feature_dir"])
	return state
}

func (service discussionService) persistState(workspace string, state map[string]any) error {
	normalizeDiscussionState(state)
	if err := validateDiscussionState(state); err != nil {
		return err
	}
	if err := writeScriptJSONFile(filepath.Join(workspace, "discussion-state.json"), state); err != nil {
		return err
	}
	return writeScriptTextFile(filepath.Join(workspace, "discussion-state.md"), renderDiscussionMarkdown(state))
}

func validateDiscussionState(state map[string]any) error {
	if intValue(state["version"]) != 3 || state["status_family"] != "discussion" {
		return fmt.Errorf("unsupported discussion state version")
	}
	phase := stringValue(state["lifecycle_phase"])
	if !discussionLifecyclePhases[phase] {
		return fmt.Errorf("invalid discussion lifecycle phase: %s", phase)
	}
	status := stringValue(state["status"])
	if !discussionIncompleteStatuses[status] && !discussionTerminalStatuses[status] {
		return fmt.Errorf("invalid discussion status: %s", status)
	}
	packet, ok := state["turn_packet"].(map[string]any)
	if !ok || packet["discussion_slug"] != state["slug"] {
		return fmt.Errorf("discussion turn packet does not match state slug")
	}
	if _, err := normalizeDiscussionTopicOwnership(packet["topic_ownership"], stringValue(state["slug"]), stringValue(state["topic"])); err != nil {
		return err
	}
	semantic := map[string]any{}
	for _, key := range discussionCheckpointPacketKeys {
		if value, exists := packet[key]; exists {
			semantic[key] = value
		}
	}
	if err := validateDiscussionCheckpointSemantics(semantic); err != nil {
		return err
	}
	return nil
}

func renderDiscussionMarkdown(state map[string]any) string {
	handoff := mapValue(state["handoff"])
	consumption := mapValue(state["consumption"])
	packet := mapValue(state["turn_packet"])
	ownership := mapValue(packet["topic_ownership"])
	lines := []string{
		"# Discussion State: " + stringValue(state["topic"]), "",
		"## Session", "",
		"- active_command: sp-discussion",
		"- state_surface: discussion-state",
		"- status: " + stringValue(state["status"]),
		"- lifecycle_phase: " + stringValue(state["lifecycle_phase"]),
		"- slug: " + stringValue(state["slug"]),
		"- updated_at: " + stringValue(state["updated_at"]),
		"- closed_at: " + noneText(state["closed_at"]),
		"- archived_at: " + noneText(state["archived_at"]),
		"- summary: " + stringValue(state["summary"]), "",
		"## Decision Context", "",
		"- current_decision_frame: " + stringValue(packet["current_decision_frame"]),
		"- topic_owner_slug: " + stringValue(ownership["owner_slug"]),
		"- topic_anchor: " + stringValue(ownership["anchor"]),
		"- confirmed_decisions: " + discussionCompactList(packet["confirmed_decisions"]),
		"- open_questions: " + discussionCompactList(packet["open_questions"]),
		"- blocking_unknown_count: " + fmt.Sprint(derivedDiscussionHardUnknownCount(packet)),
		"- open_conflict_count: " + fmt.Sprint(derivedDiscussionOpenConflictCount(packet)),
		"- current_recommendation: " + stringValue(packet["current_recommendation"]),
		"- next_gate: " + stringValue(packet["next_gate"]),
		"- blocker_reason: " + noneText(state["blocker_reason"]), "",
		"## Requirements Snapshot", "",
		"- target_need: " + stringValue(mapValue(packet["requirements_snapshot"])["target_need"]),
		"- scope_in: " + discussionCompactList(mapValue(mapValue(packet["requirements_snapshot"])["scope"])["in"]),
		"- success_criteria: " + discussionCompactList(mapValue(packet["requirements_snapshot"])["success_criteria"]),
		"- optimal_solution_approach: " + discussionCompactList(mapValue(packet["requirements_snapshot"])["optimal_solution_approach"]), "",
		"## Evidence Snapshot", "",
		"- truth_pass_status: " + stringValue(packet["truth_pass_status"]),
		"- advice_confidence: " + stringValue(packet["advice_confidence"]),
		"- evidence_checked: " + discussionCompactList(packet["evidence_checked"]),
		"- source_evidence: " + discussionCompactList(packet["source_evidence"]),
		"- source_materials: " + discussionSourceMaterialsSummary(packet["source_materials"]),
		"- latest_snapshot_sha256: " + noneText(mapValue(state["latest_checkpoint"])["snapshot_sha256"]), "",
		"## Handoff", "",
		"- handoff_review_status: " + stringValue(handoff["review_status"]),
		"- quality_gate_status: " + stringValue(handoff["quality_gate_status"]),
		"- handoff_review_digest: " + noneText(handoff["review_digest"]),
		"- handoff_contract: " + noneText(handoff["contract_path"]),
		"- recommended_consumer: " + stringValue(handoff["recommended_consumer"]), "",
		"## Consumption", "",
		"- handoff_consumption_status: " + stringValue(consumption["status"]),
		"- consumed_at: " + noneText(consumption["consumed_at"]),
		"- consumed_by_feature_dir: " + noneText(consumption["consumer_path"]),
		"- next_command: " + stringValue(state["next_command"]), "",
		"Canonical machine state: `discussion-state.json`.", "",
	}
	return strings.Join(lines, "\n")
}

func discussionCompactList(value any) string {
	items := listValue(value)
	if len(items) == 0 {
		return "none"
	}
	parts := make([]string, 0, len(items))
	for _, item := range items {
		text := strings.TrimSpace(stringValue(item))
		if object := mapValue(item); object != nil {
			text = firstNonEmpty(stringValue(object["id"]), stringValue(object["claim"]), stringValue(object["summary"]), stringValue(object["question"]))
		}
		if text != "" {
			parts = append(parts, text)
		}
	}
	if len(parts) == 0 {
		return fmt.Sprint(len(items)) + " item(s)"
	}
	return strings.Join(parts, "; ")
}

func discussionSourceMaterialsSummary(value any) string {
	items := listValue(value)
	if len(items) == 0 {
		return "none"
	}
	parts := make([]string, 0, len(items))
	for _, item := range items {
		material := mapValue(item)
		if material == nil {
			continue
		}
		id := firstNonEmpty(stringValue(material["id"]), "MAT-???")
		status := firstNonEmpty(stringValue(material["inspection_status"]), "unknown")
		if stringValue(material["sensitivity"]) == "restricted" {
			parts = append(parts, id+"("+status+") [restricted]")
			continue
		}
		summary := strings.TrimSpace(stringValue(material["summary"]))
		if len(summary) > 72 {
			summary = summary[:72] + "..."
		}
		if summary == "" {
			parts = append(parts, id+"("+status+")")
		} else {
			parts = append(parts, id+"("+status+"): "+summary)
		}
	}
	if len(parts) == 0 {
		return fmt.Sprint(len(items)) + " material(s)"
	}
	return strings.Join(parts, "; ")
}

func (service discussionService) record(workspace string, state map[string]any, archived bool) map[string]any {
	consumption := mapValue(state["consumption"])
	handoff := mapValue(state["handoff"])
	packet := mapValue(state["turn_packet"])
	stateSHA, _ := discussionStateSHA256(workspace)
	return map[string]any{
		"slug":                       state["slug"],
		"workspace":                  filepath.Base(workspace),
		"workspace_path":             workspace,
		"status":                     state["status"],
		"lifecycle_phase":            state["lifecycle_phase"],
		"summary":                    state["summary"],
		"topic":                      state["topic"],
		"current_decision_frame":     packet["current_decision_frame"],
		"topic_ownership":            packet["topic_ownership"],
		"state_sha256":               stateSHA,
		"updated_at":                 state["updated_at"],
		"closed_at":                  state["closed_at"],
		"archived_at":                state["archived_at"],
		"next_command":               firstAny(state["next_command"], "none"),
		"recommended_consumer":       handoff["recommended_consumer"],
		"review_digest":              handoff["review_digest"],
		"handoff_consumption_status": consumption["status"],
		"consumed_at":                consumption["consumed_at"],
		"consumed_by_feature_dir":    consumption["consumer_path"],
		"archived":                   archived,
	}
}

func discussionStateSHA256(workspace string) (string, error) {
	jsonPath := filepath.Join(workspace, "discussion-state.json")
	if _, err := os.Stat(jsonPath); err == nil {
		return fileSHA256(jsonPath)
	} else if !os.IsNotExist(err) {
		return "", err
	}
	return fileSHA256(filepath.Join(workspace, "discussion-state.md"))
}

func (service discussionService) focusBinding(workspace string, state map[string]any) (map[string]any, error) {
	stateSHA, err := discussionStateSHA256(workspace)
	if err != nil {
		return nil, err
	}
	packet := mapValue(state["turn_packet"])
	return map[string]any{
		"binding_kind":           "discussion_focus",
		"discussion_slug":        state["slug"],
		"selected_slug":          state["slug"],
		"state_sha256":           stateSHA,
		"topic":                  state["topic"],
		"current_decision_frame": packet["current_decision_frame"],
		"topic_ownership":        packet["topic_ownership"],
	}, nil
}

func (service discussionService) requireExpectedStateSHA(workspace string) error {
	current, err := discussionStateSHA256(workspace)
	if err != nil {
		return err
	}
	expected := strings.TrimSpace(service.expectedStateSHA256)
	if expected != "" {
		if expected != current {
			return fmt.Errorf("discussion focus binding is stale or belongs to a different discussion: expected state_sha256 %s, current %s", expected, current)
		}
		return nil
	}
	records, err := service.scan()
	if err != nil {
		return err
	}
	incomplete := 0
	for _, record := range records {
		if record["archived"] != true && discussionIncompleteStatuses[stringValue(record["status"])] {
			incomplete++
		}
	}
	if incomplete > 1 {
		return fmt.Errorf("multiple incomplete discussions require --expected-state-sha256 from discussion resolve or resume")
	}
	return nil
}

func (service discussionService) scan() ([]map[string]any, error) {
	candidates, err := service.workspaceCandidates(true)
	if err != nil {
		return nil, err
	}
	records := []map[string]any{}
	for _, candidate := range candidates {
		state, _, err := service.loadState(candidate.path)
		if err != nil {
			continue
		}
		records = append(records, service.record(candidate.path, state, candidate.archived))
	}
	sort.Slice(records, func(i, j int) bool {
		left := stringValue(records[i]["updated_at"]) + stringValue(records[i]["slug"])
		right := stringValue(records[j]["updated_at"]) + stringValue(records[j]["slug"])
		return left > right
	})
	return records, nil
}

func (service discussionService) writeIndex() (map[string]any, error) {
	root, err := service.root()
	if err != nil {
		return nil, err
	}
	records, err := service.scan()
	if err != nil {
		return nil, err
	}
	payload := map[string]any{"version": float64(2), "generated_at": nowUTCString(), "discussions": records}
	if err := writeScriptJSONFile(filepath.Join(root, "index.json"), payload); err != nil {
		return nil, err
	}
	return payload, nil
}

func (service discussionService) list(includeAll bool) (map[string]any, error) {
	records, err := service.scan()
	if err != nil {
		return nil, err
	}
	if !includeAll {
		filtered := records[:0]
		for _, record := range records {
			if record["archived"] != true && discussionIncompleteStatuses[stringValue(record["status"])] {
				filtered = append(filtered, record)
			}
		}
		records = filtered
	}
	return map[string]any{"discussions": records}, nil
}

type discussionResolutionCandidate struct {
	workspace string
	state     map[string]any
	record    map[string]any
	source    map[string]any
}

func (service discussionService) resolutionCandidates(intent, requestedSlug string) ([]discussionResolutionCandidate, error) {
	workspaces, err := service.workspaceCandidates(false)
	if err != nil {
		return nil, err
	}
	candidates := []discussionResolutionCandidate{}
	for _, candidate := range workspaces {
		state, _, loadErr := service.loadState(candidate.path)
		if loadErr != nil {
			return nil, loadErr
		}
		slug := stringValue(state["slug"])
		if requestedSlug != "" && slug != requestedSlug && filepath.Base(candidate.path) != requestedSlug {
			continue
		}
		if intent == "continue" {
			if discussionIncompleteStatuses[stringValue(state["status"])] {
				candidates = append(candidates, discussionResolutionCandidate{
					workspace: candidate.path,
					state:     state,
					record:    service.record(candidate.path, state, false),
				})
			}
			continue
		}
		if state["status"] != "handoff-ready" ||
			state["lifecycle_phase"] != "ready" ||
			stringValue(mapValue(state["consumption"])["status"]) != "not_consumed" {
			continue
		}
		if stringValue(mapValue(state["handoff"])["recommended_consumer"]) != intent {
			continue
		}
		validation, validationErr := service.validateHandoff(slug, "ready")
		if validationErr != nil {
			return nil, validationErr
		}
		if validation["valid"] != true {
			continue
		}
		_, sourcePath, pathErr := service.handoffPaths(slug)
		if pathErr != nil {
			return nil, pathErr
		}
		source, readErr := readJSONMap(sourcePath)
		if readErr != nil {
			return nil, readErr
		}
		stateHandoff := mapValue(state["handoff"])
		if source["status"] != "handoff-ready" ||
			stringValue(source["recommended_consumer"]) != intent ||
			stringValue(stateHandoff["review_digest"]) != stringValue(source["review_digest"]) ||
			stringValue(stateHandoff["contract_path"]) != stringValue(source["source_contract"]) {
			continue
		}
		record := service.record(candidate.path, state, false)
		record["source_contract"] = source["source_contract"]
		record["review_digest"] = source["review_digest"]
		candidates = append(candidates, discussionResolutionCandidate{
			workspace: candidate.path,
			state:     state,
			record:    record,
			source:    source,
		})
	}
	sort.Slice(candidates, func(i, j int) bool {
		left := stringValue(candidates[i].record["updated_at"]) + stringValue(candidates[i].record["slug"])
		right := stringValue(candidates[j].record["updated_at"]) + stringValue(candidates[j].record["slug"])
		return left > right
	})
	return candidates, nil
}

func (service discussionService) resolve(intent, requestedSlug string) (map[string]any, bool, error) {
	intent = strings.ToLower(strings.TrimSpace(intent))
	if intent != "continue" && intent != "sp-specify" && intent != "sp-quick" {
		return nil, false, fmt.Errorf("discussion resolve --intent must be continue, sp-specify, or sp-quick")
	}
	if requestedSlug != "" && !safeSegment(requestedSlug) {
		return nil, false, fmt.Errorf("discussion resolve --slug must be a safe discussion slug")
	}
	candidates, err := service.resolutionCandidates(intent, requestedSlug)
	if err != nil {
		return nil, false, err
	}
	items := make([]any, 0, len(candidates))
	for _, candidate := range candidates {
		items = append(items, candidate.record)
	}
	data := map[string]any{
		"intent":     intent,
		"resolved":   false,
		"resolution": "none",
		"candidates": items,
	}
	if len(candidates) == 0 {
		if requestedSlug != "" {
			data["resolution"] = "explicit_slug_not_eligible"
		}
		return data, false, nil
	}
	if len(candidates) > 1 {
		data["resolution"] = "ambiguous"
		return data, false, nil
	}
	selected := candidates[0]
	binding, err := service.focusBinding(selected.workspace, selected.state)
	if err != nil {
		return nil, false, err
	}
	if intent != "continue" {
		binding["consumer"] = map[string]any{
			"source_contract":      selected.source["source_contract"],
			"review_digest":        selected.source["review_digest"],
			"recommended_consumer": selected.source["recommended_consumer"],
		}
	}
	data["resolved"] = true
	data["resolution"] = "resolved"
	data["discussion"] = selected.record
	data["binding"] = binding
	return data, true, nil
}

func (service discussionService) findWorkspace(slug string, includeArchived bool) (string, bool, error) {
	if !safeSegment(slug) {
		return "", false, fmt.Errorf("a safe discussion slug is required")
	}
	candidates, err := service.workspaceCandidates(includeArchived)
	if err != nil {
		return "", false, err
	}
	matches := []discussionCandidate{}
	for _, candidate := range candidates {
		state, _, err := service.loadState(candidate.path)
		if err != nil {
			return "", false, err
		}
		if filepath.Base(candidate.path) == slug || state["slug"] == slug {
			matches = append(matches, candidate)
		}
	}
	if len(matches) == 0 {
		return "", false, fmt.Errorf("discussion not found: %s", slug)
	}
	if len(matches) > 1 {
		return "", false, fmt.Errorf("discussion slug is ambiguous: %s", slug)
	}
	return matches[0].path, matches[0].archived, nil
}

func (service discussionService) status(slug string) (map[string]any, error) {
	workspace, archived, err := service.findWorkspace(slug, true)
	if err != nil {
		return nil, err
	}
	state, _, err := service.loadState(workspace)
	if err != nil {
		return nil, err
	}
	discussion := mergeMap(service.record(workspace, state, archived), state)
	binding, err := service.focusBinding(workspace, state)
	if err != nil {
		return nil, err
	}
	return map[string]any{"discussion": discussion, "binding": binding}, nil
}

func (service discussionService) resume(slug string) (map[string]any, error) {
	workspace, archived, err := service.findWorkspace(slug, false)
	if err != nil {
		return nil, err
	}
	if archived {
		return nil, fmt.Errorf("archived discussion cannot be resumed")
	}
	state, legacy, err := service.loadState(workspace)
	if err != nil {
		return nil, err
	}
	events, err := readDiscussionEvents(filepath.Join(workspace, "discussion-log.jsonl"))
	if err != nil {
		return nil, err
	}
	if checkpoint := mapValue(state["latest_checkpoint"]); checkpoint != nil {
		if id := stringValue(checkpoint["event_id"]); id != "" {
			for i := len(events) - 1; i >= 0; i-- {
				if events[i]["event_id"] == id {
					events = events[i+1:]
					break
				}
			}
		}
	}
	binding, err := service.focusBinding(workspace, state)
	if err != nil {
		return nil, err
	}
	return map[string]any{"discussion": service.record(workspace, state, false), "turn_packet": state["turn_packet"], "recent_events": events, "legacy_state": legacy, "binding": binding}, nil
}

func (service discussionService) checkpoint(slug string, changes map[string]any) (map[string]any, error) {
	workspace, archived, err := service.findWorkspace(slug, false)
	if err != nil {
		return nil, err
	}
	if archived {
		return nil, fmt.Errorf("archived discussion cannot be checkpointed")
	}
	if err := validateDiscussionCheckpointFields(changes); err != nil {
		return nil, err
	}
	if err := validateDiscussionCheckpointSemantics(changes); err != nil {
		return nil, err
	}
	state, _, err := service.loadState(workspace)
	if err != nil {
		return nil, err
	}
	if err := service.requireExpectedStateSHA(workspace); err != nil {
		return nil, err
	}
	if _, hasPhase := changes["lifecycle_phase"]; !hasPhase {
		if alias := strings.TrimSpace(stringValue(changes["phase"])); alias != "" {
			changes["lifecycle_phase"] = strings.ToLower(alias)
		}
	}
	phase := firstNonEmpty(stringValue(changes["lifecycle_phase"]), stringValue(state["lifecycle_phase"]))
	if !discussionLifecyclePhases[phase] || phase == "ready" || phase == "consumed" || phase == "closed" {
		return nil, fmt.Errorf("invalid checkpoint lifecycle phase: %s", phase)
	}
	packet := mapValue(state["turn_packet"])
	if packet == nil {
		packet = map[string]any{}
		state["turn_packet"] = packet
	}
	if err := validateDiscussionMaterialCheckpoint(packet, changes); err != nil {
		return nil, err
	}
	if value, exists := changes["topic_ownership"]; exists {
		ownership, ownershipErr := normalizeDiscussionTopicOwnership(value, slug, stringValue(state["topic"]))
		if ownershipErr != nil {
			return nil, ownershipErr
		}
		changes["topic_ownership"] = ownership
	}
	changedFields := []any{}
	for _, key := range discussionCheckpointPacketKeys {
		if value, exists := changes[key]; exists {
			if key == "source_materials" {
				normalizeDiscussionSourceMaterialDigests(value)
			}
			packet[key] = value
			changedFields = append(changedFields, key)
		}
	}
	if err := service.validateSourceReadCoverage(slug, packet, false); err != nil {
		return nil, err
	}
	ts := nowUTCString()
	eventID, err := randomHex(16)
	if err != nil {
		return nil, err
	}
	summary := strings.TrimSpace(firstNonEmpty(stringValue(changes["summary"]), stringValue(state["summary"])))
	packet["lifecycle_phase"] = phase
	packet["persistence_mode"] = "durable-checkpoint"
	state["summary"] = summary
	state["lifecycle_phase"] = phase
	state["updated_at"] = ts
	normalizeDiscussionState(state)
	packet = mapValue(state["turn_packet"])
	snapshot := discussionSemanticSnapshot(packet)
	snapshotSHA, err := discussionSnapshotDigest(snapshot)
	if err != nil {
		return nil, err
	}
	sort.Slice(changedFields, func(i, j int) bool { return stringValue(changedFields[i]) < stringValue(changedFields[j]) })
	state["latest_checkpoint"] = map[string]any{"event_id": eventID, "timestamp": ts, "snapshot_sha256": snapshotSHA, "changed_fields": changedFields}
	event := map[string]any{
		"version":         float64(2),
		"event_id":        eventID,
		"timestamp":       ts,
		"kind":            "durable-checkpoint",
		"lifecycle_phase": phase,
		"summary":         summary,
		"snapshot_sha256": snapshotSHA,
		"changed_fields":  changedFields,
	}
	raw, _ := canonicalJSON(event)
	logPath := filepath.Join(workspace, "discussion-log.jsonl")
	file, err := os.OpenFile(logPath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0o644)
	if err != nil {
		return nil, err
	}
	if _, err := file.Write(append(raw, '\n')); err != nil {
		_ = file.Close()
		return nil, err
	}
	if err := file.Close(); err != nil {
		return nil, err
	}
	if err := service.persistState(workspace, state); err != nil {
		return nil, err
	}
	if _, err := service.writeIndex(); err != nil {
		return nil, err
	}
	binding, err := service.focusBinding(workspace, state)
	if err != nil {
		return nil, err
	}
	return map[string]any{"discussion": mergeMap(service.record(workspace, state, false), state), "event": event, "turn_packet": packet, "binding": binding}, nil
}

func discussionSemanticSnapshot(packet map[string]any) map[string]any {
	return specvalidate.DiscussionSemanticSnapshot(packet)
}

func discussionSnapshotDigest(snapshot map[string]any) (string, error) {
	return specvalidate.DiscussionSnapshotDigest(snapshot)
}

func discussionCanonicalDigest(value any) (string, error) {
	raw, err := canonicalJSON(value)
	if err != nil {
		return "", err
	}
	raw = bytes.TrimSuffix(raw, []byte{'\n'})
	sum := sha256.Sum256(raw)
	return hex.EncodeToString(sum[:]), nil
}

func (service discussionService) writeHandoff(slug string, input map[string]any) (map[string]any, error) {
	workspace, archived, err := service.findWorkspace(slug, false)
	if err != nil {
		return nil, err
	}
	if archived {
		return nil, fmt.Errorf("archived discussion cannot write a handoff")
	}
	state, _, err := service.loadState(workspace)
	if err != nil {
		return nil, err
	}
	if err := service.requireExpectedStateSHA(workspace); err != nil {
		return nil, err
	}
	packet := mapValue(state["turn_packet"])
	ensureDiscussionTurnPacketDefaults(packet, slug, stringValue(state["topic"]))
	checkpoint := mapValue(state["latest_checkpoint"])
	if checkpoint == nil || strings.TrimSpace(stringValue(checkpoint["snapshot_sha256"])) == "" {
		return nil, fmt.Errorf("missing_semantic_checkpoint: run discussion checkpoint with a complete semantic snapshot before write-handoff")
	}
	currentSnapshotSHA, err := discussionSnapshotDigest(discussionSemanticSnapshot(packet))
	if err != nil {
		return nil, err
	}
	if stringValue(checkpoint["snapshot_sha256"]) != currentSnapshotSHA {
		return nil, fmt.Errorf("stale_semantic_checkpoint: latest checkpoint snapshot does not match current discussion state")
	}
	payload, err := service.renderHandoffInput(input)
	if err != nil {
		return nil, err
	}
	payload["version"] = float64(5)
	payload["handoff_kind"] = "discussion_requirement_contract"
	payload["status"] = "draft"
	payload["entry_source"] = "sp-discussion"
	payload["discussion_slug"] = slug
	payload["source_contract"] = fmt.Sprintf(".specify/discussions/%s/handoff-to-specify.json", slug)
	payload["handoff_integrity"] = "not-checked"
	ownership, err := normalizeDiscussionTopicOwnership(packet["topic_ownership"], slug, stringValue(state["topic"]))
	if err != nil {
		return nil, err
	}
	payload["topic_ownership"] = ownership
	packet["lifecycle_phase"] = "review"
	packet["persistence_mode"] = "lifecycle-transition"
	packet["allowed_actions"] = []any{"review-handoff", "request-changes", "mark-ready"}
	packet["next_gate"] = "handoff-draft-validation"
	overlayDiscussionHandoffFromState(payload, packet)
	normalizeDiscussionSourceMaterialDigests(payload["source_materials"])
	normalizeDiscussionState(state)
	payload["discussion_snapshot_digest"] = currentSnapshotSHA
	payload["hard_unknown_count"] = float64(derivedDiscussionHardUnknownCount(payload))
	payload["open_conflict_count"] = float64(derivedDiscussionOpenConflictCount(payload))
	if intValue(payload["hard_unknown_count"]) == 0 && intValue(payload["open_conflict_count"]) == 0 {
		payload["coverage_status"] = "complete"
		payload["planning_gate_status"] = "ready"
	} else {
		payload["coverage_status"] = "blocked_by_handoff_integrity"
		payload["planning_gate_status"] = "blocked_by_handoff_integrity"
		return nil, fmt.Errorf("discussion handoff is not ready: blocking_unknowns and conflicts must be resolved before write-handoff")
	}
	quality := mapValue(payload["quality_gate"])
	if quality == nil {
		quality = map[string]any{}
		payload["quality_gate"] = quality
	}
	if stringValue(quality["self_reviewed_at"]) != "" {
		quality["status"] = "self_reviewed"
	} else {
		quality["status"] = "draft"
	}
	quality["user_review_required"] = true
	quality["user_confirmed_at"] = nil
	quality["confirmed_digest"] = nil
	digest, err := computeDiscussionReviewDigest(payload)
	if err != nil {
		return nil, err
	}
	payload["review_digest"] = digest
	preflightErrors := []map[string]string{}
	service.validateHandoffFields(payload, slug, "draft", state, &preflightErrors)
	if len(preflightErrors) > 0 {
		return nil, fmt.Errorf("discussion handoff draft is invalid: %s", strings.Join(discussionErrorCodes(preflightErrors), ", "))
	}
	jsonPath := filepath.Join(workspace, "handoff-to-specify.json")
	if err := writeScriptJSONFile(jsonPath, payload); err != nil {
		return nil, err
	}
	ts := nowUTCString()
	state["status"] = "active"
	state["lifecycle_phase"] = "review"
	state["updated_at"] = ts
	packet = mapValue(state["turn_packet"])
	packet["context_boundary"] = payload["context_boundary"]
	handoff := mapValue(state["handoff"])
	if quality["status"] == "self_reviewed" {
		handoff["review_status"] = "self-reviewed"
	} else {
		handoff["review_status"] = "draft"
	}
	handoff["quality_gate_status"] = quality["status"]
	handoff["review_digest"] = digest
	handoff["contract_path"] = payload["source_contract"]
	handoff["recommended_consumer"] = firstAny(payload["recommended_consumer"], "continue-discussion")
	state["next_command"] = "none"
	if err := service.persistState(workspace, state); err != nil {
		return nil, err
	}
	if _, err := service.writeIndex(); err != nil {
		return nil, err
	}
	binding, err := service.focusBinding(workspace, state)
	if err != nil {
		return nil, err
	}
	return map[string]any{"discussion": mergeMap(service.record(workspace, state, false), state), "review_digest": digest, "json_path": jsonPath, "binding": binding}, nil
}

func (service discussionService) renderHandoffInput(input map[string]any) (map[string]any, error) {
	templatePath, err := secureProjectPath(service.projectRoot, ".specify/templates/discussion-handoff-template.json")
	if err != nil {
		return nil, fmt.Errorf("discussion handoff template path is unsafe: %w", err)
	}
	raw, err := os.ReadFile(templatePath)
	if err != nil {
		return nil, fmt.Errorf("discussion handoff template is unavailable: %w", err)
	}
	template, err := decodeDiscussionHandoffPayload(raw)
	if err != nil {
		return nil, fmt.Errorf("discussion handoff template is invalid: %w", err)
	}
	if err := validateDiscussionHandoffTemplate(template); err != nil {
		return nil, err
	}
	return mergeDiscussionHandoffTemplate(template, input), nil
}

func validateDiscussionHandoffTemplate(template map[string]any) error {
	if intValue(template["version"]) != 5 || stringValue(template["handoff_kind"]) != "discussion_requirement_contract" {
		return fmt.Errorf("discussion handoff template must use version 5 discussion_requirement_contract")
	}
	if stringValue(template["status"]) != "draft" || stringValue(template["planning_gate_status"]) != "blocked_by_incomplete_coverage" {
		return fmt.Errorf("discussion handoff template must preserve blocked draft readiness")
	}
	quality := mapValue(template["quality_gate"])
	if stringValue(quality["status"]) != "draft" || quality["user_review_required"] != true || quality["user_confirmed_at"] != nil || quality["confirmed_digest"] != nil {
		return fmt.Errorf("discussion handoff template quality gate must require unconfirmed human review")
	}
	for _, consumer := range []string{"sp-specify", "sp-quick"} {
		entry := mapValue(mapValue(template["consumer_eligibility"])[consumer])
		if stringValue(entry["status"]) != "blocked" {
			return fmt.Errorf("discussion handoff template consumer %s must default to blocked", consumer)
		}
	}
	return nil
}

func overlayDiscussionHandoffFromState(payload, packet map[string]any) {
	payload["agent_requirement_contract"] = cloneAny(packet["requirements_snapshot"])
	delete(payload, "requirements_snapshot")
	for _, key := range []string{
		"implementation_target",
		"source_evidence",
		"source_materials",
		"blocking_unknowns",
		"soft_unknowns",
		"conflicts",
		"downstream_instructions",
		"discussion_decision_digest",
		"must_preserve",
		"truth_pass_status",
		"verified_project_facts",
		"evidence_checked",
		"advice_confidence",
		"ui_discussion_status",
		"artifact_refs",
	} {
		if value, exists := packet[key]; exists {
			payload[key] = cloneAny(value)
		}
	}
	if value, exists := packet["context_boundary"]; exists {
		payload["context_boundary"] = cloneAny(value)
	}
	if digest := mapValue(payload["discussion_decision_digest"]); digest != nil {
		digest["design_context"] = cloneAny(packet["design_context"])
	}
}

func mergeDiscussionHandoffTemplate(template, input map[string]any) map[string]any {
	result := cloneAnyMap(template)
	for key, value := range input {
		incoming, incomingObject := value.(map[string]any)
		existing, existingObject := result[key].(map[string]any)
		if incomingObject && existingObject {
			result[key] = mergeDiscussionHandoffTemplate(existing, incoming)
			continue
		}
		result[key] = cloneAny(value)
	}
	return result
}

func (service discussionService) bindConsumer(slug, featureDir string, input map[string]any) (map[string]any, error) {
	allowed := map[string]bool{"semantic_delta": true, "required_refs": true, "blockers": true, "recovery": true}
	for key := range input {
		if !allowed[key] {
			return nil, fmt.Errorf("bind-consumer input contains unsupported field %q", key)
		}
	}
	for _, field := range []string{"semantic_delta", "required_refs", "blockers"} {
		if _, ok := input[field].([]any); !ok {
			return nil, fmt.Errorf("bind-consumer %s must be an array", field)
		}
	}
	if recovery := input["recovery"]; recovery != nil {
		if _, ok := recovery.(map[string]any); !ok {
			return nil, fmt.Errorf("bind-consumer recovery must be an object or null")
		}
	}
	validation, err := service.validateHandoff(slug, "ready")
	if err != nil {
		return nil, err
	}
	if validation["valid"] != true {
		return nil, fmt.Errorf("discussion handoff is not ready for consumer binding")
	}
	sourceWorkspace, sourcePath, err := service.handoffPaths(slug)
	if err != nil {
		return nil, err
	}
	source, err := readJSONMap(sourcePath)
	if err != nil {
		return nil, fmt.Errorf("discussion handoff is not valid JSON")
	}
	if source["status"] != "handoff-ready" {
		return nil, fmt.Errorf("discussion source contract is not handoff-ready")
	}
	sourceState, _, err := service.loadState(sourceWorkspace)
	if err != nil {
		return nil, err
	}
	if sourceState["status"] != "handoff-ready" ||
		sourceState["lifecycle_phase"] != "ready" ||
		stringValue(mapValue(sourceState["consumption"])["status"]) != "not_consumed" {
		return nil, fmt.Errorf("discussion state is not an unconsumed handoff-ready lineage")
	}
	if stringValue(source["recommended_consumer"]) != "sp-specify" {
		return nil, fmt.Errorf("discussion handoff does not select sp-specify")
	}
	reviewDigest := stringValue(source["review_digest"])
	stateHandoff := mapValue(sourceState["handoff"])
	if stringValue(stateHandoff["recommended_consumer"]) != "sp-specify" ||
		stringValue(stateHandoff["review_digest"]) != reviewDigest {
		return nil, fmt.Errorf("discussion state and handoff contract lineage do not match")
	}
	expectedDigest := strings.TrimSpace(service.expectedReviewDigest)
	if expectedDigest == "" {
		return nil, fmt.Errorf("discussion consumer binding requires --review-digest from discussion resolve")
	}
	if expectedDigest != reviewDigest {
		return nil, fmt.Errorf("discussion consumer binding review digest does not match the resolved discussion")
	}
	stateSHA, err := discussionStateSHA256(sourceWorkspace)
	if err != nil {
		return nil, err
	}
	featurePath, displayFeature, err := hookFeaturePath(service.projectRoot, featureDir)
	if err != nil {
		return nil, err
	}
	info, err := os.Stat(featurePath)
	if err != nil || !info.IsDir() {
		return nil, fmt.Errorf("feature directory does not exist")
	}
	blockers := input["blockers"].([]any)
	status := "ready"
	nextAction := "/sp.plan"
	if len(blockers) > 0 {
		status = "blocked"
		nextAction = "/sp.specify"
	}
	if service.consumerIntake {
		status = "pending"
		nextAction = "/sp.specify"
	}
	sourceContract := fmt.Sprintf(".specify/discussions/%s/handoff-to-specify.json", slug)
	payload := map[string]any{
		"version":              3,
		"status":               status,
		"entry_source":         "sp-discussion",
		"discussion_slug":      slug,
		"source_contract":      sourceContract,
		"review_digest":        source["review_digest"],
		"recommended_consumer": source["recommended_consumer"],
		"state_sha256":         stateSHA,
		"semantic_delta":       input["semantic_delta"],
		"required_refs":        input["required_refs"],
		"blockers":             blockers,
		"next_action":          nextAction,
		"recovery":             input["recovery"],
	}
	target := filepath.Join(featurePath, "brainstorming", "handoff-to-specify.json")
	if _, statErr := os.Stat(target); statErr == nil {
		existing, readErr := readJSONMap(target)
		if readErr != nil {
			return nil, fmt.Errorf("feature consumer handoff already exists but is invalid; refusing to overwrite")
		}
		// create-feature installs an unbound scaffold (pending + null binding fields).
		// Treat that as first-bind eligible, not as a foreign discussion contract.
		if !isUnboundConsumerHandoff(existing) {
			if stringValue(existing["discussion_slug"]) != slug ||
				stringValue(existing["source_contract"]) != sourceContract ||
				stringValue(existing["review_digest"]) != reviewDigest {
				return nil, fmt.Errorf("feature consumer handoff is already bound to a different discussion contract")
			}
		}
		if service.consumerIntake && existing["status"] == "ready" {
			return nil, fmt.Errorf("intake cannot downgrade an already ready consumer binding")
		}
	} else if !errors.Is(statErr, os.ErrNotExist) {
		return nil, fmt.Errorf("feature consumer handoff cannot be inspected: %w", statErr)
	}
	if !service.consumerIntake {
		spec, err := readJSONMap(filepath.Join(featurePath, "spec-contract.json"))
		if err != nil {
			return nil, fmt.Errorf("consumer binding requires a compiled spec-contract.json: %w", err)
		}
		if err := specvalidate.ValidateSourceRequirementCoverageAgainstHandoff(spec, source); err != nil {
			return nil, fmt.Errorf("compiled specification lost Discussion source requirements: %w", err)
		}
	}
	if err := writeScriptJSONFile(target, payload); err != nil {
		return nil, err
	}
	digest, err := fileSHA256(target)
	if err != nil {
		return nil, err
	}
	relativePath := filepath.ToSlash(filepath.Join(displayFeature, "brainstorming", "handoff-to-specify.json"))
	return map[string]any{
		"consumer_handoff_path":   relativePath,
		"consumer_handoff_sha256": digest,
		"discussion_slug":         slug,
		"review_digest":           source["review_digest"],
		"recommended_consumer":    source["recommended_consumer"],
		"state_sha256":            stateSHA,
		"status":                  status,
		"next_action":             nextAction,
	}, nil
}

// isUnboundConsumerHandoff reports whether a feature-local handoff pointer is
// still a create-feature scaffold (or otherwise unbound) and may receive a
// first bind-consumer write. A pointer with any of discussion_slug,
// source_contract, or review_digest set is treated as already bound.
func isUnboundConsumerHandoff(existing map[string]any) bool {
	if existing == nil {
		return true
	}
	slug := strings.TrimSpace(stringValue(existing["discussion_slug"]))
	source := strings.TrimSpace(stringValue(existing["source_contract"]))
	digest := strings.TrimSpace(stringValue(existing["review_digest"]))
	return slug == "" && source == "" && digest == ""
}

func computeDiscussionReviewDigest(payload map[string]any) (string, error) {
	return specvalidate.DiscussionReviewDigest(payload)
}

func (service discussionService) validateHandoff(slug, mode string) (map[string]any, error) {
	workspace, jsonPath, err := service.handoffPaths(slug)
	if err != nil {
		return nil, err
	}
	validationMode := strings.ToLower(strings.TrimSpace(mode))
	if validationMode == "" {
		validationMode = "ready"
	}
	if validationMode != "draft" && validationMode != "ready" {
		return nil, fmt.Errorf("handoff validation mode must be draft or ready")
	}
	errors := []map[string]string{}
	raw, err := os.ReadFile(jsonPath)
	if err != nil {
		errors = append(errors, discussionError("missing_handoff_json", "handoff JSON is missing"))
		return discussionValidationPayload(workspace, errors, nil, validationMode), nil
	}
	var payload map[string]any
	if err := json.Unmarshal(raw, &payload); err != nil {
		errors = append(errors, discussionError("invalid_handoff_json", "handoff JSON is not valid JSON"))
		return discussionValidationPayload(workspace, errors, nil, validationMode), nil
	}
	state, _, stateErr := service.loadState(workspace)
	if stateErr != nil {
		errors = append(errors, discussionError("invalid_discussion_state", stateErr.Error()))
		return discussionValidationPayload(workspace, errors, payload, validationMode), nil
	}
	service.validateHandoffFields(payload, slug, validationMode, state, &errors)
	return discussionValidationPayload(workspace, errors, payload, validationMode), nil
}

func (service discussionService) handoffPaths(slug string) (string, string, error) {
	workspace, _, err := service.findWorkspace(slug, false)
	if err != nil {
		return "", "", err
	}
	return workspace, filepath.Join(workspace, "handoff-to-specify.json"), nil
}

func (service discussionService) validateHandoffFields(payload map[string]any, slug, mode string, state map[string]any, errors *[]map[string]string) {
	expected := map[string]any{"version": float64(5), "handoff_kind": "discussion_requirement_contract", "entry_source": "sp-discussion", "discussion_slug": slug, "source_contract": fmt.Sprintf(".specify/discussions/%s/handoff-to-specify.json", slug), "coverage_status": "complete", "planning_gate_status": "ready", "hard_unknown_count": float64(0), "open_conflict_count": float64(0)}
	for field, value := range expected {
		if payload[field] != value {
			*errors = append(*errors, discussionError("invalid_"+field, fmt.Sprintf("%s must be %q", field, value)))
		}
	}
	if strings.TrimSpace(stringValue(payload["handoff_goal"])) == "" {
		*errors = append(*errors, discussionError("missing_handoff_goal", "handoff_goal is required"))
	}
	validateRequirementsSnapshot(payload["agent_requirement_contract"], errors)
	validateImplementationTarget(payload["implementation_target"], errors)
	validateHandoffTopicOwnership(payload["topic_ownership"], slug, errors)
	validateBoundary(payload["context_boundary"], errors)
	validateObjectList(payload["source_evidence"], []string{"source_type", "evidence_status", "source", "claim"}, "source_evidence", errors)
	if len(listValue(payload["source_evidence"])) == 0 {
		*errors = append(*errors, discussionError("empty_source_evidence", "source_evidence must record at least one checked claim"))
	}
	validateDiscussionSourceEvidence(payload["source_evidence"], errors)
	validateSourceEvidenceMaterialCoverage(payload["source_evidence"], payload["source_materials"], errors)
	validateSourceMaterials(payload["source_materials"], payload["coverage_status"], errors)
	if err := service.validateSourceReadCoverage(slug, payload, true); err != nil {
		*errors = append(*errors, discussionError("incomplete_source_reading_or_requirements", err.Error()))
	}
	validateDiscussionMustPreserve(payload["must_preserve"], errors)
	if len(listValue(payload["must_preserve"])) == 0 {
		*errors = append(*errors, discussionError("empty_must_preserve", "Must-Preserve coverage is required"))
	}
	validateDiscussionUnknownRecords(payload["blocking_unknowns"], "blocking_unknowns", errors)
	validateDiscussionUnknownRecords(payload["soft_unknowns"], "soft_unknowns", errors)
	validateDiscussionConflictRecords(payload["conflicts"], errors)
	derivedHardUnknowns := derivedDiscussionHardUnknownCount(payload)
	if intValue(payload["hard_unknown_count"]) != derivedHardUnknowns {
		*errors = append(*errors, discussionError("derived_hard_unknown_count_mismatch", "hard_unknown_count must equal unresolved blocking_unknowns"))
	}
	derivedConflicts := derivedDiscussionOpenConflictCount(payload)
	if intValue(payload["open_conflict_count"]) != derivedConflicts {
		*errors = append(*errors, discussionError("derived_open_conflict_count_mismatch", "open_conflict_count must equal unresolved conflicts"))
	}
	validateDiscussionSnapshotDigest(payload, state, errors)
	validateDiscussionDownstreamInstructions(payload["downstream_instructions"], errors)
	validateDiscussionDecisionDigest(payload["discussion_decision_digest"], errors)
	service.validateConsumers(payload, errors)
	service.validateReviewDigest(payload, mode, errors)
}

func validateDiscussionSourceEvidence(value any, errors *[]map[string]string) {
	for index, item := range listValue(value) {
		evidence := mapValue(item)
		if evidence == nil {
			continue
		}
		status := strings.TrimSpace(stringValue(evidence["evidence_status"]))
		if status != "" && !discussionSourceEvidenceStatuses[status] {
			*errors = append(*errors, discussionError("invalid_source_evidence_status", fmt.Sprintf("source_evidence[%d].evidence_status is invalid", index)))
		} else if status == "missing" || status == "conflict" || status == "stale-advisory" {
			*errors = append(*errors, discussionError("unresolved_source_evidence", fmt.Sprintf("source_evidence[%d] is not ready for handoff", index)))
		}
	}
}

func validateDiscussionMustPreserve(value any, errors *[]map[string]string) {
	required := []string{"id", "type", "claim", "source", "downstream_requirement", "blocking_level", "owner", "latest_resolve_phase", "status"}
	validateObjectList(value, required, "must_preserve", errors)
	seen := map[string]bool{}
	for index, item := range listValue(value) {
		record := mapValue(item)
		if record == nil {
			continue
		}
		id := strings.TrimSpace(stringValue(record["id"]))
		matched, _ := regexp.MatchString(`^(MP|CA)-[0-9]{3}$`, id)
		if !matched {
			*errors = append(*errors, discussionError("invalid_must_preserve_id", fmt.Sprintf("must_preserve[%d].id must match MP-### or CA-###", index)))
		}
		if id != "" && seen[id] {
			*errors = append(*errors, discussionError("duplicate_must_preserve_id", fmt.Sprintf("must_preserve[%d].id duplicates %s", index, id)))
		}
		seen[id] = true
		blockingLevel := strings.TrimSpace(stringValue(record["blocking_level"]))
		if blockingLevel != "hard" && blockingLevel != "soft" {
			*errors = append(*errors, discussionError("invalid_must_preserve_blocking_level", fmt.Sprintf("must_preserve[%d].blocking_level is invalid", index)))
		}
		status := strings.ToLower(strings.TrimSpace(stringValue(record["status"])))
		if status != "active" && status != "confirmed" && status != "resolved" && status != "deferred" && status != "superseded" && status != "dropped" {
			*errors = append(*errors, discussionError("invalid_must_preserve_status", fmt.Sprintf("must_preserve[%d].status is invalid", index)))
		}
		if status == "resolved" && strings.TrimSpace(stringValue(record["resolution_evidence"])) == "" {
			*errors = append(*errors, discussionError("incomplete_must_preserve_resolution", fmt.Sprintf("must_preserve[%d].resolution_evidence is required", index)))
		}
		if status == "deferred" && strings.TrimSpace(stringValue(record["stop_and_reopen_condition"])) == "" {
			*errors = append(*errors, discussionError("incomplete_must_preserve_deferral", fmt.Sprintf("must_preserve[%d].stop_and_reopen_condition is required", index)))
		}
		if status == "superseded" && strings.TrimSpace(stringValue(record["superseded_by"])) == "" {
			*errors = append(*errors, discussionError("incomplete_must_preserve_supersession", fmt.Sprintf("must_preserve[%d].superseded_by is required", index)))
		}
		if status == "dropped" && strings.TrimSpace(stringValue(record["user_decision_source"])) == "" {
			*errors = append(*errors, discussionError("incomplete_must_preserve_drop", fmt.Sprintf("must_preserve[%d].user_decision_source is required", index)))
		}
	}
}

var discussionClosedItemStatuses = map[string]bool{
	"closed": true, "resolved": true, "deferred": true, "superseded": true, "dropped": true,
}

func discussionItemIsOpen(item any) bool {
	record := mapValue(item)
	if record == nil {
		return true
	}
	status := strings.ToLower(strings.TrimSpace(stringValue(record["status"])))
	return status == "" || !discussionClosedItemStatuses[status]
}

func validateDiscussionUnknownRecords(value any, label string, errors *[]map[string]string) {
	items, ok := value.([]any)
	if !ok {
		*errors = append(*errors, discussionError("invalid_"+label, label+" must be a list"))
		return
	}
	for index, item := range items {
		record := mapValue(item)
		if record == nil {
			if label == "blocking_unknowns" {
				*errors = append(*errors, discussionError("invalid_"+label+"_item", fmt.Sprintf("%s[%d] must be a structured object", label, index)))
			}
			continue
		}
		for _, field := range []string{"id", "question", "owner", "status", "latest_resolve_phase"} {
			if strings.TrimSpace(stringValue(record[field])) == "" {
				*errors = append(*errors, discussionError("incomplete_"+label+"_item", fmt.Sprintf("%s[%d].%s is required", label, index, field)))
			}
		}
		status := strings.ToLower(strings.TrimSpace(stringValue(record["status"])))
		if status != "open" && status != "resolved" && status != "closed" && status != "deferred" && status != "superseded" && status != "dropped" {
			*errors = append(*errors, discussionError("invalid_"+label+"_status", fmt.Sprintf("%s[%d].status is invalid", label, index)))
		}
		if (status == "resolved" || status == "closed") && strings.TrimSpace(stringValue(record["resolution_evidence"])) == "" {
			*errors = append(*errors, discussionError("incomplete_"+label+"_resolution", fmt.Sprintf("%s[%d].resolution_evidence is required", label, index)))
		}
		if status == "deferred" && strings.TrimSpace(stringValue(record["stop_and_reopen_condition"])) == "" {
			*errors = append(*errors, discussionError("incomplete_"+label+"_deferral", fmt.Sprintf("%s[%d].stop_and_reopen_condition is required", label, index)))
		}
		if status == "superseded" && strings.TrimSpace(stringValue(record["superseded_by"])) == "" {
			*errors = append(*errors, discussionError("incomplete_"+label+"_supersession", fmt.Sprintf("%s[%d].superseded_by is required", label, index)))
		}
		if status == "dropped" && strings.TrimSpace(stringValue(record["user_decision_source"])) == "" {
			*errors = append(*errors, discussionError("incomplete_"+label+"_drop", fmt.Sprintf("%s[%d].user_decision_source is required", label, index)))
		}
	}
}

func validateDiscussionConflictRecords(value any, errors *[]map[string]string) {
	items, ok := value.([]any)
	if !ok {
		*errors = append(*errors, discussionError("invalid_conflicts", "conflicts must be a list"))
		return
	}
	for index, item := range items {
		record := mapValue(item)
		if record == nil {
			*errors = append(*errors, discussionError("invalid_conflicts_item", fmt.Sprintf("conflicts[%d] must be an object", index)))
			continue
		}
		for _, field := range []string{"id", "claim", "status"} {
			if strings.TrimSpace(stringValue(record[field])) == "" {
				*errors = append(*errors, discussionError("incomplete_conflicts_item", fmt.Sprintf("conflicts[%d].%s is required", index, field)))
			}
		}
		status := strings.ToLower(strings.TrimSpace(stringValue(record["status"])))
		if status != "open" && status != "resolved" && status != "closed" && status != "deferred" && status != "superseded" && status != "dropped" {
			*errors = append(*errors, discussionError("invalid_conflicts_status", fmt.Sprintf("conflicts[%d].status is invalid", index)))
		}
		if discussionClosedItemStatuses[status] {
			if strings.TrimSpace(stringValue(record["resolution"])) == "" || strings.TrimSpace(stringValue(record["resolution_evidence"])) == "" {
				*errors = append(*errors, discussionError("incomplete_conflicts_resolution", fmt.Sprintf("conflicts[%d] requires resolution and resolution_evidence", index)))
			}
		}
	}
}

func validateDiscussionDownstreamInstructions(value any, errors *[]map[string]string) {
	downstream := mapValue(value)
	if downstream == nil {
		*errors = append(*errors, discussionError("missing_downstream_instructions", "downstream_instructions is required"))
		return
	}
	if _, exists := downstream["recommended_sequence"]; exists {
		*errors = append(*errors, discussionError("legacy_recommended_sequence", "recommended_sequence is not allowed"))
	}
	fields := []string{"settled_decisions", "preserved_assumptions", "conflicts_requiring_return", "capability_map", "dependencies", "planning_constraints", "deferred_scope", "reopen_conditions"}
	for _, field := range fields {
		if _, ok := downstream[field].([]any); !ok {
			*errors = append(*errors, discussionError("invalid_downstream_instructions", "downstream_instructions."+field+" must be a list"))
		}
	}
	if len(listValue(downstream["settled_decisions"])) == 0 {
		*errors = append(*errors, discussionError("empty_settled_decisions", "downstream_instructions.settled_decisions must not be empty"))
	}
}

func validateDiscussionDecisionDigest(value any, errors *[]map[string]string) {
	digest := mapValue(value)
	if digest == nil {
		*errors = append(*errors, discussionError("missing_discussion_decision_digest", "discussion_decision_digest is required"))
		return
	}
	fields := []string{"locked_direction", "rejected_alternatives", "accepted_tradeoffs", "experience_commitments", "design_system_requirements", "review_criteria_carried_forward", "must_not_dilute"}
	for _, field := range fields {
		if _, ok := digest[field].([]any); !ok {
			*errors = append(*errors, discussionError("invalid_discussion_decision_digest", "discussion_decision_digest."+field+" must be a list"))
		}
	}
	for _, field := range []string{"locked_direction", "review_criteria_carried_forward"} {
		if len(listValue(digest[field])) == 0 {
			*errors = append(*errors, discussionError("incomplete_discussion_decision_digest", "discussion_decision_digest."+field+" must not be empty"))
		}
	}
	if strings.TrimSpace(stringValue(digest["design_system_status"])) == "" {
		*errors = append(*errors, discussionError("incomplete_discussion_decision_digest", "discussion_decision_digest.design_system_status is required"))
	}
	risk := strings.TrimSpace(stringValue(digest["design_risk_level"]))
	if risk != "none" && risk != "low" && risk != "medium" && risk != "high" {
		*errors = append(*errors, discussionError("invalid_discussion_decision_digest", "discussion_decision_digest.design_risk_level is invalid"))
	}
	if mapValue(digest["design_context"]) == nil {
		*errors = append(*errors, discussionError("incomplete_discussion_decision_digest", "discussion_decision_digest.design_context is required"))
	}
}

func validateRequirementsSnapshot(value any, errors *[]map[string]string) {
	requirements := mapValue(value)
	if requirements == nil {
		*errors = append(*errors, discussionError("missing_requirements_snapshot", "requirements_snapshot is required"))
		return
	}
	if strings.TrimSpace(stringValue(requirements["target_need"])) == "" {
		*errors = append(*errors, discussionError("missing_requirements_target_need", "requirements_snapshot.target_need is required"))
	}
	scope := mapValue(requirements["scope"])
	if scope == nil || len(listValue(scope["in"])) == 0 || !discussionNonEmptyStringArray(scope["in"]) {
		*errors = append(*errors, discussionError("missing_requirements_scope", "requirements_snapshot.scope.in is required"))
	}
	for _, field := range []string{"actors", "scenarios", "success_criteria", "optimal_solution_approach"} {
		if len(listValue(requirements[field])) == 0 || !discussionNonEmptyStringArray(requirements[field]) {
			*errors = append(*errors, discussionError("missing_requirements_"+field, "requirements_snapshot."+field+" is required"))
		}
	}
	for _, field := range []string{"constraints", "design_direction", "non_goals"} {
		if items, ok := requirements[field].([]any); !ok {
			*errors = append(*errors, discussionError("invalid_requirements_"+field, "requirements_snapshot."+field+" must be an array of non-empty strings"))
		} else if len(items) > 0 && !discussionNonEmptyStringArray(items) {
			*errors = append(*errors, discussionError("invalid_requirements_"+field, "requirements_snapshot."+field+" must be an array of non-empty strings"))
		}
	}
	if scope != nil {
		for _, field := range []string{"out", "deferred"} {
			if items, ok := scope[field].([]any); !ok {
				*errors = append(*errors, discussionError("invalid_requirements_scope_"+field, "requirements_snapshot.scope."+field+" must be an array of non-empty strings"))
			} else if len(items) > 0 && !discussionNonEmptyStringArray(items) {
				*errors = append(*errors, discussionError("invalid_requirements_scope_"+field, "requirements_snapshot.scope."+field+" must be an array of non-empty strings"))
			}
		}
	}
}

func validateImplementationTarget(value any, errors *[]map[string]string) {
	target := mapValue(value)
	if target == nil {
		*errors = append(*errors, discussionError("missing_implementation_target", "implementation_target is required"))
		return
	}
	if strings.TrimSpace(stringValue(target["target_root"])) == "" &&
		strings.TrimSpace(stringValue(target["actual_project"])) == "" &&
		strings.TrimSpace(stringValue(target["target_project_root"])) == "" {
		*errors = append(*errors, discussionError("missing_implementation_target_root", "implementation_target must identify the actual project or target_root"))
	}
	if len(listValue(target["target_paths"])) == 0 && len(listValue(target["required_target_paths_to_verify"])) == 0 {
		*errors = append(*errors, discussionError("missing_implementation_target_paths", "implementation_target must name target paths or required verification paths"))
	}
	for _, field := range []string{"target_paths", "required_target_paths_to_verify"} {
		if items, ok := target[field].([]any); !ok {
			*errors = append(*errors, discussionError("invalid_implementation_target_paths", "implementation_target."+field+" must be an array of non-empty strings"))
		} else if len(items) > 0 && !discussionNonEmptyStringArray(items) {
			*errors = append(*errors, discussionError("invalid_implementation_target_paths", "implementation_target."+field+" must be an array of non-empty strings"))
		}
	}
}

func validateSourceEvidenceMaterialCoverage(evidenceValue, materialsValue any, errors *[]map[string]string) {
	materials := listValue(materialsValue)
	if len(materials) == 0 {
		return
	}
	materialIDs := map[string]bool{}
	referenced := map[string]bool{}
	for _, item := range materials {
		if id := stringValue(mapValue(item)["id"]); id != "" {
			materialIDs[id] = true
		}
	}
	for index, item := range listValue(evidenceValue) {
		evidence := mapValue(item)
		if evidence == nil {
			continue
		}
		materialID := strings.TrimSpace(stringValue(evidence["material_id"]))
		if materialID == "" {
			continue
		}
		if !materialIDs[materialID] {
			*errors = append(*errors, discussionError("unknown_source_evidence_material", fmt.Sprintf("source_evidence[%d].material_id references unknown material %s", index, materialID)))
			continue
		}
		referenced[materialID] = true
	}
	for id := range materialIDs {
		if !referenced[id] {
			*errors = append(*errors, discussionError("unreferenced_source_material", id+" must be referenced by source_evidence.material_id"))
		}
	}
}

func validateSourceMaterials(value any, coverageStatus any, errors *[]map[string]string) {
	materials, ok := value.([]any)
	if !ok {
		*errors = append(*errors, discussionError("missing_source_materials", "source_materials must be a list"))
		return
	}
	if len(materials) == 0 {
		return
	}
	seen := map[string]bool{}
	for index, item := range materials {
		material := mapValue(item)
		if material == nil {
			*errors = append(*errors, discussionError("invalid_source_materials_item", fmt.Sprintf("source_materials[%d] must be an object", index)))
			continue
		}
		for _, field := range []string{"id", "material_type", "locator", "summary", "inspection_status", "claims", "coverage_gaps", "sensitivity"} {
			if _, ok := material[field]; !ok {
				*errors = append(*errors, discussionError("incomplete_source_materials_item", fmt.Sprintf("source_materials[%d] missing %s", index, field)))
			}
		}
		if matched, _ := regexp.MatchString(`^MAT-[0-9]{3,}$`, stringValue(material["id"])); !matched {
			*errors = append(*errors, discussionError("invalid_source_materials_id", fmt.Sprintf("source_materials[%d].id must match MAT-###", index)))
		}
		id := stringValue(material["id"])
		if seen[id] {
			*errors = append(*errors, discussionError("duplicate_source_materials_id", fmt.Sprintf("source_materials[%d].id duplicates %s", index, id)))
		}
		seen[id] = true
		for _, field := range []string{"material_type", "locator", "summary", "sensitivity"} {
			if strings.TrimSpace(stringValue(material[field])) == "" {
				*errors = append(*errors, discussionError("empty_source_materials_"+field, fmt.Sprintf("source_materials[%d].%s must be non-empty", index, field)))
			}
		}
		if !discussionNonEmptyStringArray(material["claims"]) {
			*errors = append(*errors, discussionError("invalid_source_materials_claims", fmt.Sprintf("source_materials[%d].claims must be an array of non-empty strings", index)))
		}
		if gaps, ok := material["coverage_gaps"].([]any); !ok {
			*errors = append(*errors, discussionError("invalid_source_materials_coverage_gaps", fmt.Sprintf("source_materials[%d].coverage_gaps must be an array of non-empty strings", index)))
		} else if len(gaps) > 0 && !discussionNonEmptyStringArray(gaps) {
			*errors = append(*errors, discussionError("invalid_source_materials_coverage_gaps", fmt.Sprintf("source_materials[%d].coverage_gaps must be an array of non-empty strings", index)))
		}
		status := stringValue(material["inspection_status"])
		if !discussionSourceMaterialStatuses[status] {
			*errors = append(*errors, discussionError("invalid_source_materials_status", fmt.Sprintf("source_materials[%d].inspection_status is invalid", index)))
		}
		if sensitivity := stringValue(material["sensitivity"]); !discussionSourceMaterialSensitivities[sensitivity] {
			*errors = append(*errors, discussionError("invalid_source_materials_sensitivity", fmt.Sprintf("source_materials[%d].sensitivity is invalid", index)))
		}
		if contentSHA, exists := material["content_sha256"]; exists && contentSHA != nil {
			matched, _ := regexp.MatchString(`^[a-f0-9]{64}$`, stringValue(contentSHA))
			if !matched {
				*errors = append(*errors, discussionError("invalid_source_materials_content_sha256", fmt.Sprintf("source_materials[%d].content_sha256 must be a sha256 digest", index)))
			}
		}
		if coverageStatus == "complete" && (status != "inspected" || len(listValue(material["coverage_gaps"])) > 0) {
			*errors = append(*errors, discussionError("unresolved_source_materials", fmt.Sprintf("source_materials[%d] must be inspected with no coverage gaps before handoff-ready", index)))
		}
		expectedDigest, digestErr := discussionSourceMaterialDigest(material)
		if digestErr != nil {
			*errors = append(*errors, discussionError("invalid_source_materials_digest", digestErr.Error()))
		} else if stringValue(material["material_digest"]) != expectedDigest {
			*errors = append(*errors, discussionError("source_materials_digest_mismatch", fmt.Sprintf("source_materials[%d].material_digest does not match protected material content", index)))
		}
	}
}

func normalizeDiscussionSourceMaterialDigests(value any) {
	materials, ok := value.([]any)
	if !ok {
		return
	}
	for _, item := range materials {
		material := mapValue(item)
		if material == nil {
			continue
		}
		digest, err := discussionSourceMaterialDigest(material)
		if err == nil {
			material["material_digest"] = digest
		}
	}
}

func discussionSourceMaterialDigest(material map[string]any) (string, error) {
	protected := cloneAnyMap(material)
	delete(protected, "material_digest")
	return discussionCanonicalDigest(protected)
}

func derivedDiscussionHardUnknownCount(payload map[string]any) int {
	count := 0
	for _, item := range listValue(payload["blocking_unknowns"]) {
		if discussionItemIsOpen(item) {
			count++
		}
	}
	return count
}

func derivedDiscussionOpenConflictCount(payload map[string]any) int {
	count := 0
	for _, item := range listValue(payload["conflicts"]) {
		if discussionItemIsOpen(item) {
			count++
		}
	}
	downstream := mapValue(payload["downstream_instructions"])
	count += len(listValue(downstream["conflicts_requiring_return"]))
	return count
}

func validateDiscussionSnapshotDigest(payload map[string]any, state map[string]any, errors *[]map[string]string) {
	checkpoint := mapValue(state["latest_checkpoint"])
	if checkpoint == nil || strings.TrimSpace(stringValue(checkpoint["snapshot_sha256"])) == "" {
		*errors = append(*errors, discussionError("missing_semantic_checkpoint", "latest_checkpoint.snapshot_sha256 is required before handoff"))
		return
	}
	packet := mapValue(state["turn_packet"])
	if packet == nil {
		*errors = append(*errors, discussionError("invalid_discussion_snapshot", "state turn_packet is required"))
		return
	}
	snapshot := discussionSemanticSnapshot(packet)
	currentDigest, err := discussionSnapshotDigest(snapshot)
	if err != nil {
		*errors = append(*errors, discussionError("invalid_discussion_snapshot", err.Error()))
		return
	}
	if stringValue(checkpoint["snapshot_sha256"]) != currentDigest {
		*errors = append(*errors, discussionError("stale_semantic_checkpoint", "latest_checkpoint.snapshot_sha256 must match the current discussion semantic snapshot"))
	}
	if strings.TrimSpace(stringValue(payload["discussion_snapshot_digest"])) == "" {
		*errors = append(*errors, discussionError("missing_discussion_snapshot_digest", "discussion_snapshot_digest is required"))
	} else if stringValue(payload["discussion_snapshot_digest"]) != currentDigest {
		*errors = append(*errors, discussionError("discussion_snapshot_digest_mismatch", "discussion_snapshot_digest must match the current discussion semantic snapshot"))
	}
}

func validateHandoffTopicOwnership(value any, slug string, errors *[]map[string]string) {
	ownership, err := normalizeDiscussionTopicOwnership(value, slug, slug)
	if err != nil {
		*errors = append(*errors, discussionError("invalid_topic_ownership", err.Error()))
		return
	}
	if stringValue(mapValue(value)["owner_slug"]) != slug {
		*errors = append(*errors, discussionError("invalid_topic_owner", "topic_ownership.owner_slug must match discussion_slug"))
		return
	}
	if stringValue(ownership["owner_slug"]) != slug {
		*errors = append(*errors, discussionError("invalid_topic_owner", "topic ownership must remain bound to its source discussion"))
	}
}

func validateBoundary(value any, errors *[]map[string]string) {
	boundary := mapValue(value)
	if boundary == nil || boundary["status"] != "locked" {
		*errors = append(*errors, discussionError("unlocked_context_boundary", "context boundary must be locked"))
		return
	}
	validateObjectList(boundary["current_project_roles"], []string{"role", "scope", "evidence_source", "notes"}, "current_project_roles", errors)
	if len(listValue(boundary["current_project_roles"])) == 0 {
		*errors = append(*errors, discussionError("empty_current_project_roles", "context_boundary.current_project_roles must not be empty"))
	}
	if stringValue(boundary["target_project_root"]) != "" {
		validateObjectList(boundary["target_project_roles"], []string{"role", "scope", "evidence_source", "notes"}, "target_project_roles", errors)
		if len(listValue(boundary["target_project_roles"])) == 0 {
			*errors = append(*errors, discussionError("empty_target_project_roles", "context_boundary.target_project_roles must not be empty when target_project_root is set"))
		}
	}
}

func validateObjectList(value any, fields []string, label string, errors *[]map[string]string) {
	items, ok := value.([]any)
	if !ok {
		*errors = append(*errors, discussionError("invalid_"+label, label+" must be a list"))
		return
	}
	required := map[string]bool{}
	for _, field := range fields {
		required[field] = true
	}
	for i, item := range items {
		object := mapValue(item)
		if object == nil {
			*errors = append(*errors, discussionError("invalid_"+label+"_item", fmt.Sprintf("%s[%d] must be an object", label, i)))
			continue
		}
		missing := []string{}
		for field := range required {
			if _, ok := object[field]; !ok {
				missing = append(missing, field)
				continue
			}
			if strings.TrimSpace(stringValue(object[field])) == "" {
				missing = append(missing, field)
			}
		}
		sort.Strings(missing)
		if len(missing) > 0 {
			*errors = append(*errors, discussionError("incomplete_"+label+"_item", fmt.Sprintf("%s[%d] missing %s", label, i, strings.Join(missing, ", "))))
		}
	}
}

func (service discussionService) validateConsumers(payload map[string]any, errors *[]map[string]string) {
	eligibility := mapValue(payload["consumer_eligibility"])
	if eligibility == nil {
		*errors = append(*errors, discussionError("invalid_consumer_eligibility", "consumer_eligibility must be an object"))
		return
	}
	ready := map[string]bool{}
	for _, name := range []string{"sp-specify", "sp-quick"} {
		if consumer := mapValue(eligibility[name]); consumer != nil && consumer["status"] == "ready" {
			ready[name] = true
		}
	}
	if len(ready) == 0 {
		*errors = append(*errors, discussionError("no_ready_consumer", "at least one consumer must be ready"))
	}
	if !ready[stringValue(payload["recommended_consumer"])] {
		*errors = append(*errors, discussionError("invalid_recommended_consumer", "recommended_consumer must be ready"))
	}
}

func (service discussionService) validateReviewDigest(payload map[string]any, mode string, errors *[]map[string]string) {
	digest := stringValue(payload["review_digest"])
	computed, err := computeDiscussionReviewDigest(payload)
	if err != nil || digest == "" || digest != computed {
		*errors = append(*errors, discussionError("review_digest_mismatch", "review_digest does not match protected content"))
	}
	quality := mapValue(payload["quality_gate"])
	if quality == nil {
		*errors = append(*errors, discussionError("missing_quality_gate", "quality gate is required"))
		return
	}
	status := stringValue(quality["status"])
	if !(status == "self_reviewed" || status == "self-reviewed" || status == "user_confirmed" || status == "user-confirmed") || stringValue(quality["self_reviewed_at"]) == "" {
		*errors = append(*errors, discussionError("handoff_not_self_reviewed", "quality gate must record agent self-review"))
	}
	if mode == "draft" {
		return
	}
	if status != "user_confirmed" && status != "user-confirmed" {
		*errors = append(*errors, discussionError("handoff_not_user_confirmed", "quality gate must record user confirmation"))
		return
	}
	if stringValue(quality["user_confirmed_at"]) == "" {
		*errors = append(*errors, discussionError("incomplete_quality_gate", "self-review and user confirmation evidence are required"))
	}
	if quality["confirmed_digest"] != digest {
		*errors = append(*errors, discussionError("review_digest_confirmation_mismatch", "confirmation does not match review_digest"))
	}
}

func discussionValidationPayload(workspace string, errors []map[string]string, payload map[string]any, mode string) map[string]any {
	codes := []any{}
	for _, item := range errors {
		codes = append(codes, item["code"])
	}
	var digest any
	if payload != nil {
		digest = payload["review_digest"]
	}
	return map[string]any{"valid": len(errors) == 0, "validation_mode": mode, "workspace_path": workspace, "review_digest": digest, "error_codes": codes, "errors": mapsToAny(errors)}
}

func discussionError(code, message string) map[string]string {
	return map[string]string{"code": code, "message": message}
}

func (service discussionService) confirmHandoff(slug, reviewDigest string) (map[string]any, error) {
	expected := strings.TrimSpace(reviewDigest)
	if expected == "" {
		return nil, fmt.Errorf("review digest is required")
	}
	validation, err := service.validateHandoff(slug, "draft")
	if err != nil {
		return nil, err
	}
	if validation["valid"] != true {
		return nil, fmt.Errorf("discussion handoff draft is not reviewable: %s", strings.Join(anyStrings(validation["error_codes"]), ", "))
	}
	if validation["review_digest"] != expected {
		return nil, fmt.Errorf("review digest does not match the current handoff revision")
	}
	workspace, jsonPath, err := service.handoffPaths(slug)
	if err != nil {
		return nil, err
	}
	state, _, err := service.loadState(workspace)
	if err != nil {
		return nil, err
	}
	payload, err := readJSONMap(jsonPath)
	if err != nil {
		return nil, err
	}
	quality := mapValue(payload["quality_gate"])
	if quality["status"] == "user_confirmed" && stringValue(quality["user_confirmed_at"]) != "" && quality["confirmed_digest"] == expected {
		return map[string]any{"discussion": mergeMap(service.record(workspace, state, false), state), "review_digest": expected, "json_path": jsonPath}, nil
	}
	quality["status"] = "user_confirmed"
	quality["user_confirmed_at"] = nowUTCString()
	quality["confirmed_digest"] = expected
	if err := writeScriptJSONFile(jsonPath, payload); err != nil {
		return nil, err
	}
	ts := nowUTCString()
	state["status"] = "active"
	state["lifecycle_phase"] = "review"
	state["updated_at"] = ts
	packet := mapValue(state["turn_packet"])
	packet["lifecycle_phase"] = "review"
	packet["persistence_mode"] = "lifecycle-transition"
	packet["allowed_actions"] = []any{"mark-ready", "request-changes", "review-handoff"}
	packet["next_gate"] = "handoff-ready-validation"
	handoff := mapValue(state["handoff"])
	handoff["review_status"] = "user-confirmed"
	handoff["quality_gate_status"] = "user_confirmed"
	handoff["review_digest"] = expected
	handoff["contract_path"] = payload["source_contract"]
	handoff["recommended_consumer"] = firstAny(payload["recommended_consumer"], "continue-discussion")
	state["next_command"] = "none"
	if err := service.persistState(workspace, state); err != nil {
		return nil, err
	}
	if _, err := service.writeIndex(); err != nil {
		return nil, err
	}
	return map[string]any{"discussion": mergeMap(service.record(workspace, state, false), state), "review_digest": expected, "json_path": jsonPath}, nil
}

func (service discussionService) markReady(slug string) (map[string]any, error) {
	validation, err := service.validateHandoff(slug, "ready")
	if err != nil {
		return nil, err
	}
	if validation["valid"] != true {
		return nil, fmt.Errorf("discussion handoff is not ready: %s", strings.Join(anyStrings(validation["error_codes"]), ", "))
	}
	workspace, jsonPath, err := service.handoffPaths(slug)
	if err != nil {
		return nil, err
	}
	state, _, err := service.loadState(workspace)
	if err != nil {
		return nil, err
	}
	payload, err := readJSONMap(jsonPath)
	if err != nil {
		return nil, err
	}
	payload["status"] = "handoff-ready"
	payload["handoff_integrity"] = "validated"
	if err := writeScriptJSONFile(jsonPath, payload); err != nil {
		return nil, err
	}
	ts := nowUTCString()
	state["status"] = "handoff-ready"
	state["lifecycle_phase"] = "ready"
	state["updated_at"] = ts
	packet := mapValue(state["turn_packet"])
	packet["lifecycle_phase"] = "ready"
	packet["persistence_mode"] = "lifecycle-transition"
	packet["allowed_actions"] = []any{"consume", "request-changes", "close"}
	packet["next_gate"] = "downstream-consumption"
	state["handoff"] = map[string]any{"review_status": "user-confirmed", "quality_gate_status": "user_confirmed", "review_digest": validation["review_digest"], "contract_path": fmt.Sprintf(".specify/discussions/%s/handoff-to-specify.json", slug), "recommended_consumer": payload["recommended_consumer"]}
	state["next_command"] = payload["recommended_consumer"]
	if err := service.persistState(workspace, state); err != nil {
		return nil, err
	}
	if _, err := service.writeIndex(); err != nil {
		return nil, err
	}
	return map[string]any{"discussion": mergeMap(service.record(workspace, state, false), state), "validation": validation}, nil
}

func (service discussionService) markConsumed(slug, consumerPathValue string) (map[string]any, error) {
	workspace, archived, err := service.findWorkspace(slug, false)
	if err != nil {
		return nil, err
	}
	if archived {
		return nil, fmt.Errorf("archived discussion cannot be consumed")
	}
	state, _, err := service.loadState(workspace)
	if err != nil {
		return nil, err
	}
	if state["status"] != "handoff-ready" || state["lifecycle_phase"] != "ready" {
		return nil, fmt.Errorf("only a validated handoff-ready discussion can be consumed")
	}
	sourceContract, reviewDigest, recommendedConsumer, stateSHA, err := service.currentReadyDiscussionLineage(workspace, slug, state)
	if err != nil {
		return nil, err
	}
	consumerPath, err := safeProjectContainedPath(service.projectRoot, consumerPathValue)
	if err != nil {
		return nil, err
	}
	evidencePath, err := consumerEvidencePath(consumerPath)
	if err != nil {
		return nil, err
	}
	if err := service.validateConsumerEvidence(slug, sourceContract, reviewDigest, recommendedConsumer, stateSHA, evidencePath); err != nil {
		return nil, err
	}
	ts := nowUTCString()
	state["status"] = "completed"
	state["lifecycle_phase"] = "consumed"
	state["updated_at"] = ts
	state["closed_at"] = ts
	state["next_command"] = "none"
	packet := mapValue(state["turn_packet"])
	packet["lifecycle_phase"] = "consumed"
	packet["persistence_mode"] = "lifecycle-transition"
	packet["allowed_actions"] = []any{"archive"}
	packet["next_gate"] = "archive"
	consumerRel, err := relativeToProject(service.projectRoot, consumerPath)
	if err != nil {
		return nil, err
	}
	evidenceRel, err := relativeToProject(service.projectRoot, evidencePath)
	if err != nil {
		return nil, err
	}
	state["consumption"] = map[string]any{
		"status":               "consumed",
		"consumed_at":          ts,
		"consumer_path":        consumerRel,
		"evidence_path":        evidenceRel,
		"review_digest":        reviewDigest,
		"source_contract":      sourceContract,
		"recommended_consumer": recommendedConsumer,
		"state_sha256":         stateSHA,
	}
	if err := service.persistState(workspace, state); err != nil {
		return nil, err
	}
	if _, err := service.writeIndex(); err != nil {
		return nil, err
	}
	return map[string]any{"discussion": mergeMap(service.record(workspace, state, false), state)}, nil
}

func (service discussionService) currentReadyDiscussionLineage(workspace, slug string, state map[string]any) (string, string, string, string, error) {
	if stringValue(mapValue(state["consumption"])["status"]) != "not_consumed" {
		return "", "", "", "", fmt.Errorf("discussion state is not an unconsumed handoff-ready lineage")
	}
	validation, err := service.validateHandoff(slug, "ready")
	if err != nil {
		return "", "", "", "", err
	}
	if validation["valid"] != true {
		return "", "", "", "", fmt.Errorf("discussion handoff is not ready: %s", strings.Join(anyStrings(validation["error_codes"]), ", "))
	}
	_, sourcePath, err := service.handoffPaths(slug)
	if err != nil {
		return "", "", "", "", err
	}
	source, err := readJSONMap(sourcePath)
	if err != nil {
		return "", "", "", "", fmt.Errorf("discussion handoff is not valid JSON")
	}
	expectedContract := fmt.Sprintf(".specify/discussions/%s/handoff-to-specify.json", slug)
	reviewDigest := stringValue(mapValue(state["handoff"])["review_digest"])
	if reviewDigest == "" {
		return "", "", "", "", fmt.Errorf("ready discussion is missing a reviewed digest")
	}
	stateHandoff := mapValue(state["handoff"])
	recommendedConsumer := stringValue(stateHandoff["recommended_consumer"])
	if recommendedConsumer == "" {
		return "", "", "", "", fmt.Errorf("ready discussion is missing a selected consumer")
	}
	if recommendedConsumer != "sp-specify" && recommendedConsumer != "sp-quick" {
		return "", "", "", "", fmt.Errorf("ready discussion selected unsupported consumer %q", recommendedConsumer)
	}
	if stringValue(stateHandoff["contract_path"]) != expectedContract {
		return "", "", "", "", fmt.Errorf("discussion state and source handoff lineage do not match")
	}
	if source["status"] != "handoff-ready" ||
		stringValue(source["source_contract"]) != expectedContract ||
		stringValue(source["review_digest"]) != reviewDigest ||
		stringValue(source["recommended_consumer"]) != recommendedConsumer {
		return "", "", "", "", fmt.Errorf("discussion state and source handoff lineage do not match")
	}
	stateSHA, err := discussionStateSHA256(workspace)
	if err != nil {
		return "", "", "", "", err
	}
	return expectedContract, reviewDigest, recommendedConsumer, stateSHA, nil
}

func (service discussionService) validateConsumerEvidence(slug, sourceContract, digest, recommendedConsumer, stateSHA, evidencePath string) error {
	if strings.EqualFold(filepath.Ext(evidencePath), ".md") {
		if recommendedConsumer != "sp-quick" {
			return fmt.Errorf("formal discussion consumption requires the compiled specification and its JSON consumer binding, not Markdown Quick evidence")
		}
		raw, err := os.ReadFile(evidencePath)
		if err != nil {
			return err
		}
		fields := extractScalarFields(string(raw))
		if fields["source_discussion_slug"] != slug ||
			fields["source_contract"] != sourceContract ||
			fields["review_digest"] != digest ||
			fields["recommended_consumer"] != recommendedConsumer ||
			fields["state_sha256"] != stateSHA {
			return fmt.Errorf("consumer evidence does not reference the reviewed discussion")
		}
		return nil
	}
	payload, err := readJSONMap(evidencePath)
	if err != nil {
		return fmt.Errorf("consumer evidence is not valid JSON")
	}
	mismatched := []string{}
	for field, want := range map[string]string{
		"discussion_slug":      slug,
		"source_contract":      sourceContract,
		"review_digest":        digest,
		"recommended_consumer": recommendedConsumer,
		"state_sha256":         stateSHA,
	} {
		if payload[field] != want {
			mismatched = append(mismatched, field)
		}
	}
	sort.Strings(mismatched)
	if len(mismatched) > 0 {
		return fmt.Errorf("consumer evidence does not reference the reviewed discussion: %s", strings.Join(mismatched, ", "))
	}
	if recommendedConsumer == "sp-specify" {
		if payload["status"] != "ready" {
			return fmt.Errorf("formal consumer binding is not ready; finalize the compiled specification with bind-consumer before mark-consumed")
		}
		if err := specvalidate.ValidateSourceRequirementCoverage(filepath.Dir(filepath.Dir(evidencePath))); err != nil {
			return fmt.Errorf("consumer specification source coverage is incomplete: %w", err)
		}
	}
	return nil
}

func (service discussionService) close(slug, statusValue string) (map[string]any, error) {
	if !discussionTerminalStatuses[statusValue] {
		return nil, fmt.Errorf("close requires status completed or abandoned")
	}
	workspace, archived, err := service.findWorkspace(slug, false)
	if err != nil {
		return nil, err
	}
	if archived {
		return nil, fmt.Errorf("archived discussion cannot be closed")
	}
	state, _, err := service.loadState(workspace)
	if err != nil {
		return nil, err
	}
	ts := nowUTCString()
	state["status"] = statusValue
	state["lifecycle_phase"] = "closed"
	state["updated_at"] = ts
	state["closed_at"] = ts
	state["next_command"] = "none"
	packet := mapValue(state["turn_packet"])
	packet["lifecycle_phase"] = "closed"
	packet["persistence_mode"] = "lifecycle-transition"
	packet["allowed_actions"] = []any{"archive"}
	packet["next_gate"] = "archive"
	if err := service.persistState(workspace, state); err != nil {
		return nil, err
	}
	if _, err := service.writeIndex(); err != nil {
		return nil, err
	}
	return map[string]any{"discussion": mergeMap(service.record(workspace, state, false), state)}, nil
}

func (service discussionService) archive(slug string) (map[string]any, error) {
	workspace, archived, err := service.findWorkspace(slug, false)
	if err != nil {
		return nil, err
	}
	if archived {
		return nil, fmt.Errorf("discussion is already archived")
	}
	state, _, err := service.loadState(workspace)
	if err != nil {
		return nil, err
	}
	if !discussionTerminalStatuses[stringValue(state["status"])] || state["closed_at"] == nil {
		return nil, fmt.Errorf("only closed completed or abandoned discussions can be archived")
	}
	root, err := service.root()
	if err != nil {
		return nil, err
	}
	archiveRoot := filepath.Join(root, "archive")
	if err := os.MkdirAll(archiveRoot, 0o755); err != nil {
		return nil, err
	}
	destination := filepath.Join(archiveRoot, filepath.Base(workspace))
	if _, err := os.Stat(destination); err == nil {
		return nil, fmt.Errorf("archive destination already exists: %s", filepath.Base(destination))
	} else if !os.IsNotExist(err) {
		return nil, err
	}
	if err := os.Rename(workspace, destination); err != nil {
		return nil, err
	}
	ts := nowUTCString()
	state["archived_at"] = ts
	state["updated_at"] = ts
	if err := service.persistState(destination, state); err != nil {
		return nil, err
	}
	if _, err := service.writeIndex(); err != nil {
		return nil, err
	}
	return map[string]any{"discussion": mergeMap(service.record(destination, state, true), state)}, nil
}

type quickService struct {
	projectRoot string
}

func (service quickService) run(mode, quickID, targetStatus string, includeAll bool) (Envelope, error) {
	root, err := service.root()
	if err != nil {
		return Envelope{}, err
	}
	tasks, err := service.scan(root)
	if err != nil {
		return Envelope{}, err
	}
	if _, err := service.writeIndex(root, tasks); err != nil {
		return Envelope{}, err
	}
	var data map[string]any
	switch strings.ToLower(strings.TrimSpace(mode)) {
	case "rebuild-index":
		data, err = service.writeIndex(root, tasks)
	case "list":
		selected := []map[string]any{}
		for _, task := range tasks {
			if includeAll || isQuickUnfinished(task) {
				selected = append(selected, task)
			}
		}
		sort.Slice(selected, func(i, j int) bool {
			left := stringValue(selected[i]["id"]) + stringValue(selected[i]["workspace"])
			right := stringValue(selected[j]["id"]) + stringValue(selected[j]["workspace"])
			return left < right
		})
		data = map[string]any{"tasks": selected}
	case "status":
		var task map[string]any
		task, err = matchQuickTask(tasks, quickID)
		if err == nil {
			data = map[string]any{
				"task":               task,
				"cognition_closeout": service.cognitionCloseoutStatus(stringValue(task["workspace_path"])),
			}
		}
	case "close":
		var task map[string]any
		task, err = matchQuickTask(tasks, quickID)
		if err == nil {
			err = service.closeTask(task, strings.ToLower(strings.TrimSpace(targetStatus)))
		}
		if err == nil {
			tasks, err = service.scan(root)
		}
		if err == nil {
			_, err = service.writeIndex(root, tasks)
		}
		if err == nil {
			task, err = matchQuickTask(tasks, quickID)
			data = map[string]any{
				"task":               task,
				"cognition_closeout": service.cognitionCloseoutStatus(stringValue(task["workspace_path"])),
			}
		}
	case "archive":
		var task map[string]any
		task, err = matchQuickTask(tasks, quickID)
		var archived map[string]any
		if err == nil {
			archived, err = service.archiveTask(root, task)
		}
		if err == nil {
			tasks, err = service.scan(root)
		}
		if err == nil {
			_, err = service.writeIndex(root, tasks)
		}
		if err == nil {
			task, err = matchQuickTask(tasks, stringValue(archived["workspace"]))
			data = map[string]any{"task": task}
		}
	default:
		err = fmt.Errorf("unknown mode: %s", mode)
	}
	if err != nil {
		return Envelope{}, err
	}
	env := NewEnvelope("ok", "quick state command completed")
	env.Data = data
	return env, nil
}

func (service quickService) root() (string, error) {
	return secureProjectPath(service.projectRoot, ".planning/quick")
}

func (service quickService) scan(root string) ([]map[string]any, error) {
	tasks := []map[string]any{}
	add := func(parent string, archived bool) error {
		entries, err := os.ReadDir(parent)
		if os.IsNotExist(err) {
			return nil
		}
		if err != nil {
			return err
		}
		for _, entry := range entries {
			if !entry.IsDir() || entry.Name() == "archive" {
				continue
			}
			task, err := service.readTask(filepath.Join(parent, entry.Name()), archived)
			if err != nil {
				return err
			}
			if task != nil {
				tasks = append(tasks, task)
			}
		}
		return nil
	}
	if err := add(root, false); err != nil {
		return nil, err
	}
	if err := add(filepath.Join(root, "archive"), true); err != nil {
		return nil, err
	}
	return tasks, nil
}

func (service quickService) readTask(workspace string, archived bool) (map[string]any, error) {
	statusPath := filepath.Join(workspace, "STATUS.md")
	raw, err := os.ReadFile(statusPath)
	if os.IsNotExist(err) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	frontmatter, body := parseFrontmatter(string(raw))
	id, slug := deriveQuickIdentity(filepath.Base(workspace), frontmatter)
	status := strings.ToLower(firstNonEmpty(frontmatter["status"], "gathering"))
	title := firstNonEmpty(frontmatter["title"], frontmatter["trigger"], slug)
	return map[string]any{"id": id, "slug": slug, "workspace": filepath.Base(workspace), "workspace_path": workspace, "status": status, "title": title, "current_focus": extractQuickCurrentFocus(body), "next_action": extractQuickNextAction(body), "updated": frontmatter["updated"], "closed_at": frontmatter["closed_at"], "archived_at": frontmatter["archived_at"], "archived": archived}, nil
}

func (service quickService) writeIndex(root string, tasks []map[string]any) (map[string]any, error) {
	payload := map[string]any{"version": float64(1), "generated_at": nowUTCString(), "tasks": tasks}
	return payload, writeScriptJSONFile(filepath.Join(root, "index.json"), payload)
}

func matchQuickTask(tasks []map[string]any, quickID string) (map[string]any, error) {
	if strings.TrimSpace(quickID) == "" {
		return nil, fmt.Errorf("quick id is required")
	}
	matches := []map[string]any{}
	for _, task := range tasks {
		if task["id"] == quickID || task["workspace"] == quickID {
			matches = append(matches, task)
		}
	}
	if len(matches) == 0 {
		return nil, fmt.Errorf("quick task not found: %s", quickID)
	}
	if len(matches) > 1 {
		return nil, fmt.Errorf("quick id is ambiguous: %s", quickID)
	}
	return matches[0], nil
}

func isQuickUnfinished(task map[string]any) bool {
	return task["archived"] != true && strings.ToLower(stringValue(task["status"])) != "resolved"
}

func (service quickService) closeTask(task map[string]any, statusValue string) error {
	if statusValue != "resolved" && statusValue != "blocked" {
		return fmt.Errorf("close requires status resolved or blocked; example: specify-runtime quick close %s resolved", firstNonEmpty(stringValue(task["id"]), "<id>"))
	}
	workspacePath := stringValue(task["workspace_path"])
	if err := service.validateCloseAgainstConfirmation(workspacePath, statusValue); err != nil {
		return err
	}
	if err := service.validateCognitionCloseoutForClose(workspacePath, statusValue); err != nil {
		return err
	}
	return service.updateStatusFile(workspacePath, func(frontmatter map[string]string) {
		ts := nowUTCString()
		frontmatter["status"] = statusValue
		frontmatter["updated"] = ts
		frontmatter["closed_at"] = ts
	})
}

func (service quickService) runCognitionCloseout(quickID string, args []string) (Envelope, error) {
	root, err := service.root()
	if err != nil {
		return Envelope{}, err
	}
	tasks, err := service.scan(root)
	if err != nil {
		return Envelope{}, err
	}
	task, err := matchQuickTask(tasks, quickID)
	if err != nil {
		return Envelope{}, err
	}
	resultState := firstNonEmpty(optionValue(args, "--result-state", ""), optionValue(args, "--status", ""))
	if strings.TrimSpace(resultState) == "" {
		return Envelope{}, fmt.Errorf("cognition-closeout requires --result-state ready|no_op|mark-dirty|partial|needs_rebuild|blocked")
	}
	reason := optionValue(args, "--reason", "")
	updateID := optionValue(args, "--update-id", "")
	evidence := []string{}
	if raw := strings.TrimSpace(optionValue(args, "--evidence-json", "")); raw != "" {
		if err := json.Unmarshal([]byte(raw), &evidence); err != nil {
			return Envelope{}, fmt.Errorf("--evidence-json must be a JSON string array: %w", err)
		}
	}
	payload, err := service.recordCognitionCloseout(stringValue(task["workspace_path"]), resultState, reason, updateID, evidence, strings.TrimSpace(optionValue(args, "--binding-id", "")))
	if err != nil {
		return Envelope{}, err
	}
	env := NewEnvelope("ok", "quick cognition closeout recorded")
	env.Data = payload
	env.Data["task"] = task
	env.Data["cognition_closeout"] = service.cognitionCloseoutStatus(stringValue(task["workspace_path"]))
	if payload["allowed_close"] == true {
		env.NextArgv = []string{"specify-runtime", "quick", "close", stringValue(task["id"]), "resolved"}
	} else {
		env.ShowArgv = mutationCognitionRecoveryArgv(stringValue(task["workspace_path"]), "sp-quick", nil)
	}
	return env, nil
}

func (service quickService) archiveTask(root string, task map[string]any) (map[string]any, error) {
	if task["archived"] == true {
		return nil, fmt.Errorf("quick task is already archived")
	}
	status := strings.ToLower(stringValue(task["status"]))
	if status != "resolved" && status != "blocked" {
		return nil, fmt.Errorf("only resolved or blocked quick tasks can be archived")
	}
	if strings.TrimSpace(stringValue(task["closed_at"])) == "" {
		return nil, fmt.Errorf("quick task must be closed before archive")
	}
	archiveRoot := filepath.Join(root, "archive")
	if err := os.MkdirAll(archiveRoot, 0o755); err != nil {
		return nil, err
	}
	source := filepath.Join(root, stringValue(task["workspace"]))
	destination := filepath.Join(archiveRoot, stringValue(task["workspace"]))
	if _, err := os.Stat(destination); err == nil {
		return nil, fmt.Errorf("archive destination already exists: %s", filepath.Base(destination))
	} else if !os.IsNotExist(err) {
		return nil, err
	}
	if err := os.Rename(source, destination); err != nil {
		return nil, err
	}
	if err := service.updateStatusFile(destination, func(frontmatter map[string]string) {
		ts := nowUTCString()
		frontmatter["archived_at"] = ts
		frontmatter["updated"] = ts
	}); err != nil {
		return nil, err
	}
	archived, err := service.readTask(destination, true)
	if err == nil && archived != nil {
		archived["archived"] = true
	}
	return archived, err
}

func (service quickService) updateStatusFile(workspace string, updater func(map[string]string)) error {
	statusPath := filepath.Join(workspace, "STATUS.md")
	raw, err := os.ReadFile(statusPath)
	if err != nil {
		return err
	}
	frontmatter, body := parseFrontmatter(string(raw))
	updater(frontmatter)
	return writeScriptTextFile(statusPath, emitFrontmatter(frontmatter, body))
}

type prdService struct {
	projectRoot string
}

var scanDirectorySurfaces = map[string]string{"workspace": ".", "evidence": "evidence", "scan_packets": "scan-packets", "worker_results": "worker-results", "master": "master", "exports": "exports"}
var scanFileSurfaces = map[string]string{"workflow_state": "workflow-state.md", "prd_scan": "prd-scan.md", "coverage_ledger": "coverage-ledger.md"}
var baseScanJSONSurfaces = map[string]string{"coverage_ledger_json": "coverage-ledger.json", "capability_ledger_json": "capability-ledger.json", "artifact_contracts_json": "artifact-contracts.json", "reconstruction_checklist_json": "reconstruction-checklist.json"}
var heavyScanJSONSurfaces = map[string]struct {
	path    string
	payload map[string]any
}{
	"entrypoint_ledger_json":     {"entrypoint-ledger.json", map[string]any{"entrypoints": []any{}}},
	"config_contracts_json":      {"config-contracts.json", map[string]any{"configs": []any{}}},
	"protocol_contracts_json":    {"protocol-contracts.json", map[string]any{"protocols": []any{}}},
	"state_machines_json":        {"state-machines.json", map[string]any{"machines": []any{}}},
	"error_semantics_json":       {"error-semantics.json", map[string]any{"errors": []any{}}},
	"verification_surfaces_json": {"verification-surfaces.json", map[string]any{"surfaces": []any{}}},
}
var baseBuildSurfaces = map[string]string{"master_pack": "master/master-pack.md", "package_readme": "exports/README.md", "prd_export": "exports/prd.md", "reconstruction_appendix": "exports/reconstruction-appendix.md", "data_model": "exports/data-model.md", "integration_contracts": "exports/integration-contracts.md", "runtime_behaviors": "exports/runtime-behaviors.md"}
var heavyBuildExportSurfaces = map[string]string{"config_contracts": "exports/config-contracts.md", "protocol_contracts": "exports/protocol-contracts.md", "state_machines": "exports/state-machines.md", "error_semantics": "exports/error-semantics.md", "verification_surface": "exports/verification-surface.md", "reconstruction_risks": "exports/reconstruction-risks.md"}
var prdScanSurfaceKeys = []string{"workspace", "evidence", "scan_packets", "worker_results", "master", "exports", "workflow_state", "prd_scan", "coverage_ledger", "coverage_ledger_json", "capability_ledger_json", "artifact_contracts_json", "reconstruction_checklist_json", "entrypoint_ledger_json", "config_contracts_json", "protocol_contracts_json", "state_machines_json", "error_semantics_json", "verification_surfaces_json"}
var prdBuildSurfaceKeys = []string{"workspace", "master", "exports", "workflow_state", "master_pack", "package_readme", "prd_export", "reconstruction_appendix", "data_model", "integration_contracts", "runtime_behaviors", "config_contracts", "protocol_contracts", "state_machines", "error_semantics", "verification_surface", "reconstruction_risks"}

func (service prdService) runScan(mode, runSlug string) (Envelope, error) {
	canonical, payloadMode, err := canonicalPRDMode(mode)
	if err != nil {
		return Envelope{}, err
	}
	var data map[string]any
	if canonical == "init-scan" {
		activeCommand := "sp-prd-scan"
		data, err = service.initRun(runSlug, activeCommand, payloadMode)
	} else if canonical == "finalize-scan" {
		data, err = service.finalizeRun(runSlug, payloadMode)
	} else if canonical == "status-scan" {
		data, err = service.statusScan(runSlug, payloadMode)
	} else {
		err = fmt.Errorf("unknown prd scan mode: %s", mode)
	}
	if err != nil {
		return Envelope{}, err
	}
	env := NewEnvelope("ok", "prd scan state command completed")
	env.Data = data
	return env, nil
}

func (service prdService) runBuild(mode, runID string) (Envelope, error) {
	canonical, payloadMode, err := canonicalPRDMode(mode)
	if err != nil {
		return Envelope{}, err
	}
	if canonical != "status-build" {
		return Envelope{}, fmt.Errorf("unknown prd build mode: %s", mode)
	}
	data, err := service.statusBuild(runID, payloadMode)
	if err != nil {
		return Envelope{}, err
	}
	env := NewEnvelope("ok", "prd build state command completed")
	env.Data = data
	return env, nil
}

func canonicalPRDMode(mode string) (string, string, error) {
	switch strings.ToLower(strings.TrimSpace(mode)) {
	case "init":
		return "init-scan", "init", nil
	case "status":
		return "status-scan", "status", nil
	case "finalize":
		return "finalize-scan", "finalize", nil
	case "init-scan":
		return "init-scan", "init-scan", nil
	case "finalize-scan":
		return "finalize-scan", "finalize-scan", nil
	case "status-scan":
		return "status-scan", "status-scan", nil
	case "status-build":
		return "status-build", "status-build", nil
	default:
		return "", "", fmt.Errorf("unknown mode: %s", mode)
	}
}

func (service prdService) initRun(requestedSlug, activeCommand, payloadMode string) (map[string]any, error) {
	date := time.Now().UTC().Format("060102")
	slug := slugifyScript(requestedSlug, "prd-run", 0)
	workspace := date + "-" + slug
	runDir, err := secureProjectPath(service.projectRoot, filepath.ToSlash(filepath.Join(".specify", "prd-runs", workspace)))
	if err != nil {
		return nil, err
	}
	if err := os.MkdirAll(runDir, 0o755); err != nil {
		return nil, err
	}
	if err := writeFileIfMissing(filepath.Join(runDir, "workflow-state.md"), scanWorkflowState(workspace, slug, activeCommand)); err != nil {
		return nil, err
	}
	if err := initPRDScanArtifacts(runDir); err != nil {
		return nil, err
	}
	if err := service.seedPRDStatusIfMissing(workspace); err != nil {
		return nil, err
	}
	surfaces := service.surfaceStatus(runDir)
	recordDigests, err := service.recordDigests(runDir)
	if err != nil {
		return nil, err
	}
	statusPath, err := service.statusPath()
	if err != nil {
		return nil, err
	}
	return map[string]any{
		"mode":           payloadMode,
		"date":           date,
		"slug":           slug,
		"workspace":      workspace,
		"workspace_path": runDir,
		"status_file":    statusPath,
		"freshness": map[string]any{
			"status_file_exists": true,
			"freshness":          "missing",
			"latest_run":         workspace,
			"current_run":        workspace,
		},
		"surfaces":       surfaces,
		"record_digests": recordDigests,
		"complete":       allSurfaces(surfaces, prdScanSurfaceKeys),
	}, nil
}

func (service prdService) finalizeRun(runID, payloadMode string) (map[string]any, error) {
	runDir, err := service.resolveRunDir(runID)
	if err != nil {
		return nil, err
	}
	statusPath, err := service.statusPath()
	if err != nil {
		return nil, err
	}
	if err := validatePRDRunArtifacts(runDir, "prd-scan"); err != nil {
		return nil, err
	}
	status, _, err := service.loadStatusDocument()
	if err != nil {
		return nil, fmt.Errorf("load PRD status before finalize: %w", err)
	}
	if status.ManualForceStale || len(status.ManualForceStaleReasons) > 0 {
		return nil, fmt.Errorf("PRD status is manually forced stale; clear the stale condition through the owning CLI before finalizing")
	}
	snapshot, err := currentPRDGitSnapshot(service.projectRoot)
	if err != nil {
		return nil, err
	}
	payload := map[string]any{
		"version":                          float64(1),
		"status_family":                    "prd",
		"freshness":                        "fresh",
		"last_refresh_commit":              snapshot.commit,
		"last_refresh_branch":              snapshot.branch,
		"last_refresh_at":                  nowUTCString(),
		"last_refresh_scope":               snapshot.scope,
		"last_refresh_basis":               snapshot.basis,
		"last_refresh_changed_files_basis": stringSliceToAny(snapshot.changedFiles),
		"manual_force_stale":               false,
		"manual_force_stale_reasons":       []any{},
		"latest_run":                       filepath.Base(runDir),
	}
	if err := writeScriptJSONFile(statusPath, payload); err != nil {
		return nil, err
	}
	freshness, err := service.freshnessPayload(filepath.Base(runDir))
	if err != nil {
		return nil, err
	}
	return map[string]any{
		"mode":           payloadMode,
		"workspace":      filepath.Base(runDir),
		"workspace_path": runDir,
		"status_file":    statusPath,
		"finalized":      true,
		"freshness":      freshness,
	}, nil
}

func (service prdService) statusScan(runID, payloadMode string) (map[string]any, error) {
	runDir, err := service.resolveRunDir(runID)
	if err != nil {
		return nil, err
	}
	surfaces := service.surfaceStatus(runDir)
	recordDigests, err := service.recordDigests(runDir)
	if err != nil {
		return nil, err
	}
	statusPath, err := service.statusPath()
	if err != nil {
		return nil, err
	}
	freshness, err := service.freshnessPayload(filepath.Base(runDir))
	if err != nil {
		return nil, err
	}
	return map[string]any{"mode": payloadMode, "workspace": filepath.Base(runDir), "workspace_path": runDir, "status_file": statusPath, "freshness": freshness, "surfaces": surfaces, "record_digests": recordDigests, "complete": allSurfaces(surfaces, prdScanSurfaceKeys)}, nil
}

func (service prdService) statusBuild(runID, payloadMode string) (map[string]any, error) {
	runDir, err := service.resolveRunDir(runID)
	if err != nil {
		return nil, err
	}
	surfaces := service.surfaceStatus(runDir)
	statusPath, err := service.statusPath()
	if err != nil {
		return nil, err
	}
	freshness, err := service.freshnessPayload(filepath.Base(runDir))
	if err != nil {
		return nil, err
	}
	surfaceComplete := allSurfaces(surfaces, prdBuildSurfaceKeys)
	complete := false
	errors := []string{}
	readiness := "blocked"
	semanticStatus := "blocked"
	var recovery any
	if surfaceComplete {
		if err := validatePRDStageArtifacts(service.projectRoot, runDir, "prd-build"); err != nil {
			errors = append(errors, err.Error())
			recovery = prdBuildRecovery("prd-build", "Repair the canonical PRD build artifact set through its owning CLI until validation passes, then rerun build status.", filepath.Base(runDir))
		} else {
			complete = true
			readiness = "complete"
			semanticStatus = "ready"
		}
	} else {
		if err := validatePRDStageArtifacts(service.projectRoot, runDir, "prd-build-ready"); err != nil {
			errors = append(errors, err.Error())
			recovery = prdBuildRecovery("prd-scan", "Repair and finalize the canonical PRD scan package through prd-scan before starting or resuming prd-build.", filepath.Base(runDir))
		} else {
			readiness = "ready-to-build"
			semanticStatus = "ready"
		}
	}
	return map[string]any{
		"mode":             payloadMode,
		"workspace":        filepath.Base(runDir),
		"workspace_path":   runDir,
		"status_file":      statusPath,
		"freshness":        freshness,
		"surfaces":         surfaces,
		"surface_complete": surfaceComplete,
		"complete":         complete,
		"status":           semanticStatus,
		"readiness":        readiness,
		"errors":           errors,
		"recovery":         recovery,
	}, nil
}

func prdBuildRecovery(stage, action, runID string) map[string]any {
	return map[string]any{
		"stage":         stage,
		"action":        action,
		"next_action":   action,
		"rerun_command": []string{"specify-runtime", "prd-build", "status-build", runID},
	}
}

func (service prdService) resolveRunDir(runID string) (string, error) {
	if strings.TrimSpace(runID) == "" {
		return "", fmt.Errorf("run id is required")
	}
	if filepath.IsAbs(runID) || filepath.VolumeName(runID) != "" {
		return filepath.Abs(runID)
	}
	return secureProjectPath(service.projectRoot, filepath.ToSlash(filepath.Join(".specify", "prd-runs", runID)))
}

func (service prdService) expectedSurfaces() map[string]string {
	surfaces := map[string]string{}
	for key, value := range scanDirectorySurfaces {
		surfaces[key] = value
	}
	for key, value := range scanFileSurfaces {
		surfaces[key] = value
	}
	for key, value := range baseScanJSONSurfaces {
		surfaces[key] = value
	}
	for key, value := range heavyScanJSONSurfaces {
		surfaces[key] = value.path
	}
	for key, value := range baseBuildSurfaces {
		surfaces[key] = value
	}
	for key, value := range heavyBuildExportSurfaces {
		surfaces[key] = value
	}
	return surfaces
}

func (service prdService) surfaceStatus(runDir string) map[string]any {
	result := map[string]any{}
	for key, relative := range service.expectedSurfaces() {
		path := runDir
		if relative != "." {
			path = filepath.Join(runDir, filepath.FromSlash(relative))
		}
		info, err := os.Stat(path)
		if relative == "." {
			result[key] = err == nil && info.IsDir()
		} else if filepath.Ext(relative) != "" {
			result[key] = err == nil && !info.IsDir()
		} else {
			result[key] = err == nil && info.IsDir()
		}
	}
	return result
}

func initPRDScanArtifacts(runDir string) error {
	for _, dirname := range []string{"evidence", "scan-packets", "worker-results", "master", "exports"} {
		if err := os.MkdirAll(filepath.Join(runDir, dirname), 0o755); err != nil {
			return err
		}
	}
	if err := writeFileIfMissing(filepath.Join(runDir, "prd-scan.md"), "# PRD Scan\n\n## Reconstruction Summary\n\n- Status: initialized\n"); err != nil {
		return err
	}
	if err := writeFileIfMissing(filepath.Join(runDir, "coverage-ledger.md"), "# Coverage Ledger\n\n| Surface | Status | Evidence | Notes |\n| --- | --- | --- | --- |\n| Repository overview | pending |  |  |\n"); err != nil {
		return err
	}
	for key, relative := range baseScanJSONSurfaces {
		payload := map[string]any{}
		switch key {
		case "coverage_ledger_json":
			payload = map[string]any{"version": float64(1), "rows": []any{}}
		case "capability_ledger_json":
			payload = map[string]any{"capabilities": []any{}}
		case "artifact_contracts_json":
			payload = map[string]any{"artifacts": []any{}}
		case "reconstruction_checklist_json":
			payload = map[string]any{"checks": []any{}}
		}
		raw, _ := json.MarshalIndent(payload, "", "  ")
		if err := writeFileIfMissing(filepath.Join(runDir, relative), string(raw)+"\n"); err != nil {
			return err
		}
	}
	for _, surface := range heavyScanJSONSurfaces {
		raw, _ := json.MarshalIndent(surface.payload, "", "  ")
		if err := writeFileIfMissing(filepath.Join(runDir, surface.path), string(raw)+"\n"); err != nil {
			return err
		}
	}
	return nil
}

func (service prdService) seedPRDStatusIfMissing(workspace string) error {
	path, err := service.statusPath()
	if err != nil {
		return err
	}
	if _, err := os.Stat(path); err == nil {
		return nil
	} else if !os.IsNotExist(err) {
		return err
	}
	payload := map[string]any{"version": float64(1), "status_family": "prd", "freshness": "missing", "last_refresh_commit": "uninitialized", "last_refresh_branch": "uninitialized", "last_refresh_at": nowUTCString(), "last_refresh_scope": "full", "last_refresh_basis": "prd-scan-init", "last_refresh_changed_files_basis": []any{}, "manual_force_stale": false, "manual_force_stale_reasons": []any{}, "latest_run": workspace}
	raw, _ := json.MarshalIndent(payload, "", "  ")
	return writeFileIfMissing(path, string(raw)+"\n")
}

func (service prdService) freshnessPayload(workspace string) (map[string]any, error) {
	status, raw, err := service.loadStatusDocument()
	if err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return map[string]any{"status_file_exists": false, "freshness": "missing", "latest_run": service.latestRunID(), "current_run": workspace}, nil
		}
		return nil, err
	}
	if status.Freshness != "fresh" {
		baselineChangedFiles, _ := raw["last_refresh_changed_files_basis"].([]any)
		return map[string]any{
			"status_file_exists":         true,
			"freshness":                  firstNonEmpty(status.Freshness, "missing"),
			"latest_run":                 firstNonEmpty(status.LatestRun, service.latestRunID()),
			"current_run":                workspace,
			"baseline_commit":            status.LastRefreshCommit,
			"baseline_branch":            status.LastRefreshBranch,
			"baseline_basis":             status.LastRefreshBasis,
			"baseline_scope":             status.LastRefreshScope,
			"baseline_changed_files":     append([]any{}, baselineChangedFiles...),
			"manual_force_stale":         status.ManualForceStale,
			"manual_force_stale_reasons": append([]any{}, status.ManualForceStaleReasons...),
		}, nil
	}
	freshness, currentChangedFiles, err := evaluatePRDFreshness(service.projectRoot, status)
	if err != nil {
		return nil, err
	}
	currentSnapshot, err := currentPRDGitSnapshot(service.projectRoot)
	if err != nil {
		return nil, err
	}
	baselineChangedFiles, _ := raw["last_refresh_changed_files_basis"].([]any)
	return map[string]any{
		"status_file_exists":         true,
		"freshness":                  freshness,
		"latest_run":                 firstNonEmpty(status.LatestRun, service.latestRunID()),
		"current_run":                workspace,
		"baseline_commit":            status.LastRefreshCommit,
		"baseline_branch":            status.LastRefreshBranch,
		"baseline_basis":             status.LastRefreshBasis,
		"baseline_scope":             status.LastRefreshScope,
		"baseline_changed_files":     append([]any{}, baselineChangedFiles...),
		"current_commit":             currentSnapshot.commit,
		"current_branch":             currentSnapshot.branch,
		"current_basis":              currentSnapshot.basis,
		"current_scope":              currentSnapshot.scope,
		"current_changed_files":      stringSliceToAny(currentChangedFiles),
		"manual_force_stale":         status.ManualForceStale,
		"manual_force_stale_reasons": append([]any{}, status.ManualForceStaleReasons...),
		"non_git_fallback":           currentSnapshot.fallback,
	}, nil
}

func (service prdService) statusPath() (string, error) {
	return secureProjectPath(service.projectRoot, ".specify/prd/status.json")
}

func (service prdService) loadStatusDocument() (prdStatusDocument, map[string]any, error) {
	statusPath, err := service.statusPath()
	if err != nil {
		return prdStatusDocument{}, nil, err
	}
	return loadPRDStatusDocument(statusPath)
}

func (service prdService) latestRunID() string {
	runsDir, err := secureProjectPath(service.projectRoot, ".specify/prd-runs")
	if err != nil {
		return ""
	}
	entries, err := os.ReadDir(runsDir)
	if err != nil {
		return ""
	}
	names := []string{}
	for _, entry := range entries {
		if entry.IsDir() {
			names = append(names, entry.Name())
		}
	}
	sort.Strings(names)
	if len(names) == 0 {
		return ""
	}
	return names[len(names)-1]
}

func scanWorkflowState(workspace, slug, activeCommand string) string {
	return strings.Join([]string{
		"---",
		fmt.Sprintf("id: %q", workspace),
		fmt.Sprintf("slug: %q", slug),
		"status: \"initialized\"",
		fmt.Sprintf("created_at: %q", nowUTCString()),
		"---",
		"# PRD Workflow State", "",
		"## Current Command", "",
		fmt.Sprintf("- active_command: `%s`", activeCommand),
		"- status: `active`", "",
		"## Phase Mode", "",
		"- phase_mode: `analysis-only`",
		"- summary: reconstruction scan package initialization", "",
		"## Allowed Artifact Writes", "",
		strings.Join(artifactBullets(workspace, []string{"workflow_state", "prd_scan", "coverage_ledger", "coverage_ledger_json", "capability_ledger_json", "artifact_contracts_json", "reconstruction_checklist_json", "entrypoint_ledger_json", "config_contracts_json", "protocol_contracts_json", "state_machines_json", "error_semantics_json", "verification_surfaces_json", "scan_packets", "worker_results", "evidence"}), "\n"), "",
		"## Forbidden Actions", "",
		"- edit source code",
		"- implement product changes",
		"- write final PRD exports", "",
		"## Next Action", "",
		"- initialize reconstruction evidence harvest", "",
		"## Next Command", "",
		"- `/sp.prd-build`", "",
		"## Authoritative Files", "",
		strings.Join(artifactBullets(workspace, []string{"workflow_state", "prd_scan", "coverage_ledger_json", "artifact_contracts_json", "reconstruction_checklist_json", "entrypoint_ledger_json", "config_contracts_json", "protocol_contracts_json", "state_machines_json", "error_semantics_json", "verification_surfaces_json"}), "\n"), "",
		"## Open Unknowns", "",
		"- None recorded yet.", "",
	}, "\n")
}

func artifactBullets(workspace string, keys []string) []string {
	service := prdService{}
	surfaces := service.expectedSurfaces()
	bullets := []string{}
	for _, key := range keys {
		relative := surfaces[key]
		suffix := ""
		if filepath.Ext(relative) == "" && relative != "." {
			suffix = "/"
		}
		bullets = append(bullets, fmt.Sprintf("- `.specify/prd-runs/%s/%s%s`", workspace, relative, suffix))
	}
	return bullets
}

func parseFrontmatter(text string) (map[string]string, string) {
	if !strings.HasPrefix(text, "---\n") && !strings.HasPrefix(text, "---\r\n") {
		return map[string]string{}, text
	}
	lines := strings.Split(text, "\n")
	end := -1
	for i := 1; i < len(lines); i++ {
		if strings.TrimSpace(strings.TrimSuffix(lines[i], "\r")) == "---" {
			end = i
			break
		}
	}
	if end < 0 {
		return map[string]string{}, text
	}
	frontmatter := map[string]string{}
	for _, raw := range lines[1:end] {
		line := strings.TrimSpace(raw)
		if line == "" || strings.HasPrefix(line, "#") || !strings.Contains(line, ":") {
			continue
		}
		parts := strings.SplitN(line, ":", 2)
		frontmatter[strings.TrimSpace(parts[0])] = strings.Trim(strings.TrimSpace(parts[1]), `"'`)
	}
	body := strings.Join(lines[end+1:], "\n")
	return frontmatter, body
}

type prdGitSnapshot struct {
	commit       string
	branch       string
	basis        string
	scope        string
	changedFiles []string
	fallback     bool
}

func evaluatePRDFreshness(projectRoot string, status prdStatusDocument) (string, []string, error) {
	current, err := currentPRDGitSnapshot(projectRoot)
	if err != nil {
		return "", nil, err
	}
	if status.ManualForceStale {
		return "full-stale", current.changedFiles, nil
	}
	if current.fallback {
		if status.LastRefreshCommit == current.commit && status.LastRefreshBranch == current.branch && status.LastRefreshBasis == current.basis && reflectStringSlices(normalizePRDChangedFiles(status.LastRefreshChangedFilesBasis), current.changedFiles) {
			return "fresh", current.changedFiles, nil
		}
		return "full-stale", current.changedFiles, nil
	}
	if strings.HasPrefix(status.LastRefreshBasis, "non-git-fallback") {
		return "full-stale", current.changedFiles, nil
	}
	if status.LastRefreshBranch != current.branch {
		return "full-stale", current.changedFiles, nil
	}
	currentChangedFiles, err := prdChangedFilesSince(projectRoot, status.LastRefreshCommit)
	if err != nil {
		return "", nil, err
	}
	baseline := normalizePRDChangedFiles(status.LastRefreshChangedFilesBasis)
	if reflectStringSlices(baseline, currentChangedFiles) {
		return "fresh", currentChangedFiles, nil
	}
	affected := symmetricPRDChangedFiles(baseline, currentChangedFiles)
	if len(affected) == 0 {
		affected = currentChangedFiles
	}
	return classifyPRDFreshness(affected), currentChangedFiles, nil
}

func currentPRDGitSnapshot(projectRoot string) (prdGitSnapshot, error) {
	if !isGitWorkTree(projectRoot) {
		changedFiles, digest, err := prdFallbackSnapshot(projectRoot)
		if err != nil {
			return prdGitSnapshot{}, err
		}
		return prdGitSnapshot{
			commit:       "non-git-unavailable",
			branch:       "non-git-unavailable",
			basis:        "non-git-fallback:" + digest,
			scope:        "full",
			changedFiles: changedFiles,
			fallback:     true,
		}, nil
	}
	commit, err := runGitValue(projectRoot, "rev-parse", "HEAD")
	if err != nil {
		return prdGitSnapshot{}, err
	}
	branch, err := runGitValue(projectRoot, "rev-parse", "--abbrev-ref", "HEAD")
	if err != nil {
		return prdGitSnapshot{}, err
	}
	changedFiles, err := prdChangedFiles(projectRoot)
	if err != nil {
		return prdGitSnapshot{}, err
	}
	scope := "full"
	if len(changedFiles) > 0 {
		scope = "targeted"
	}
	return prdGitSnapshot{
		commit:       firstNonEmpty(commit, "git-commit-unavailable"),
		branch:       firstNonEmpty(branch, "git-branch-unavailable"),
		basis:        "git-head+worktree",
		scope:        scope,
		changedFiles: changedFiles,
	}, nil
}

func isGitWorkTree(projectRoot string) bool {
	output, err := runtimecmd.CommandCombinedOutput("", nil, "git", "-C", projectRoot, "rev-parse", "--is-inside-work-tree")
	if err != nil {
		return false
	}
	if !strings.EqualFold(strings.TrimSpace(string(output)), "true") {
		return false
	}
	return runtimecmd.CommandRun("", nil, "git", "-C", projectRoot, "rev-parse", "--verify", "HEAD") == nil
}

func runGitValue(projectRoot string, args ...string) (string, error) {
	output, err := runtimecmd.CommandCombinedOutput("", nil, "git", append([]string{"-C", projectRoot}, args...)...)
	if err != nil {
		return "", fmt.Errorf("git %s failed: %s", strings.Join(args, " "), strings.TrimSpace(string(output)))
	}
	return strings.TrimSpace(string(output)), nil
}

func prdChangedFiles(projectRoot string) ([]string, error) {
	return prdGitChangedFiles(projectRoot, "")
}

func prdChangedFilesSince(projectRoot, baselineCommit string) ([]string, error) {
	return prdGitChangedFiles(projectRoot, strings.TrimSpace(baselineCommit))
}

func prdGitChangedFiles(projectRoot, baselineCommit string) ([]string, error) {
	commands := [][]string{}
	if baselineCommit != "" {
		commands = append(commands, []string{"diff", "-z", "--name-only", "--relative", baselineCommit + "..HEAD"})
	}
	commands = append(commands,
		[]string{"diff", "-z", "--name-only", "--relative", "HEAD"},
		[]string{"ls-files", "-z", "--others", "--exclude-standard"},
	)
	sets := [][]string{}
	for _, args := range commands {
		lines, err := gitCommandNULPaths(projectRoot, args...)
		if err != nil {
			return nil, fmt.Errorf("git %s failed: %w", strings.Join(args, " "), err)
		}
		sets = append(sets, lines)
	}
	seen := map[string]bool{}
	all := []string{}
	for _, values := range sets {
		for _, value := range values {
			value = filepath.ToSlash(strings.TrimSpace(value))
			if value == "" || classifyPRDChangedPath(value) == "ignore" {
				continue
			}
			if !seen[value] {
				seen[value] = true
				all = append(all, value)
			}
		}
	}
	sort.Strings(all)
	return all, nil
}

func symmetricPRDChangedFiles(left, right []string) []string {
	leftSet := map[string]bool{}
	rightSet := map[string]bool{}
	for _, path := range left {
		leftSet[path] = true
	}
	for _, path := range right {
		rightSet[path] = true
	}
	changed := []string{}
	for path := range leftSet {
		if !rightSet[path] {
			changed = append(changed, path)
		}
	}
	for path := range rightSet {
		if !leftSet[path] {
			changed = append(changed, path)
		}
	}
	sort.Strings(changed)
	return changed
}

func classifyPRDFreshness(paths []string) string {
	freshness := "fresh"
	for _, path := range paths {
		switch classifyPRDChangedPath(path) {
		case "full-stale":
			return "full-stale"
		case "targeted-stale":
			freshness = "targeted-stale"
		}
	}
	return freshness
}

func classifyPRDChangedPath(path string) string {
	normalized := strings.ToLower(strings.Trim(filepath.ToSlash(path), "/"))
	name := normalized
	if index := strings.LastIndex(normalized, "/"); index >= 0 {
		name = normalized[index+1:]
	}
	lockfiles := map[string]bool{
		"bun.lock": true, "bun.lockb": true, "cargo.lock": true, "composer.lock": true,
		"go.sum": true, "package-lock.json": true, "pnpm-lock.yaml": true,
		"poetry.lock": true, "uv.lock": true, "yarn.lock": true,
	}
	fullRoot := map[string]bool{
		"agents.md": true, "project-handbook.md": true, "cargo.toml": true,
		"go.mod": true, "package.json": true, "pyproject.toml": true, "setup.cfg": true,
	}
	if fullRoot[normalized] || lockfiles[name] {
		return "full-stale"
	}
	fullExact := map[string]bool{
		"src/specify_cli/__init__.py": true, "src/specify_cli/agents.py": true,
		"src/specify_cli/launcher.py": true, "src/specify_cli/workflow_markers.py": true,
	}
	if fullExact[normalized] {
		return "full-stale"
	}
	for _, prefix := range []string{
		".github/workflows/", "scripts/bash/", "scripts/powershell/",
		"src/specify_cli/execution/", "src/specify_cli/hooks/", "src/specify_cli/integrations/",
		"src/specify_cli/orchestration/", "src/specify_cli/shared_hooks/", "templates/commands/",
		"templates/command-partials/", "templates/passive-skills/", "templates/project-map/",
		"templates/worker-prompts/",
	} {
		if strings.HasPrefix(normalized, prefix) {
			return "full-stale"
		}
	}
	if normalized == "readme.md" {
		return "targeted-stale"
	}
	for _, prefix := range []string{"docs/", "src/", "templates/", "tests/"} {
		if strings.HasPrefix(normalized, prefix) {
			return "targeted-stale"
		}
	}
	return "ignore"
}

func prdFallbackSnapshot(projectRoot string) ([]string, string, error) {
	root, err := filepath.Abs(projectRoot)
	if err != nil {
		return nil, "", err
	}
	files := []string{}
	err = filepath.WalkDir(root, func(path string, entry os.DirEntry, walkErr error) error {
		if walkErr != nil {
			return walkErr
		}
		rel, relErr := filepath.Rel(root, path)
		if relErr != nil {
			return relErr
		}
		rel = filepath.ToSlash(rel)
		if entry.IsDir() {
			if rel != "." && (rel == ".git" || rel == ".specify" || rel == ".planning" || rel == "node_modules" || rel == ".venv") {
				return filepath.SkipDir
			}
			return nil
		}
		if classifyPRDChangedPath(rel) != "ignore" {
			files = append(files, rel)
		}
		return nil
	})
	if err != nil {
		return nil, "", err
	}
	sort.Strings(files)
	digest := sha256.New()
	for _, rel := range files {
		digest.Write([]byte(rel))
		digest.Write([]byte{0})
		raw, readErr := os.ReadFile(filepath.Join(root, filepath.FromSlash(rel)))
		if readErr != nil {
			return nil, "", readErr
		}
		digest.Write(raw)
		digest.Write([]byte{0})
	}
	return files, hex.EncodeToString(digest.Sum(nil)), nil
}

func normalizePRDChangedFiles(raw []any) []string {
	values := []string{}
	for _, item := range raw {
		text := strings.TrimSpace(fmt.Sprint(item))
		if text != "" {
			values = append(values, filepath.ToSlash(text))
		}
	}
	sort.Strings(values)
	return values
}

func reflectStringSlices(left, right []string) bool {
	if len(left) != len(right) {
		return false
	}
	for index := range left {
		if left[index] != right[index] {
			return false
		}
	}
	return true
}

func emitFrontmatter(frontmatter map[string]string, body string) string {
	order := []string{"id", "slug", "title", "status", "trigger", "updated", "closed_at", "archived_at"}
	var output []string
	output = append(output, "---")
	seen := map[string]bool{}
	for _, key := range order {
		if strings.TrimSpace(frontmatter[key]) != "" {
			output = append(output, fmt.Sprintf("%s: %q", key, strings.TrimSpace(frontmatter[key])))
			seen[key] = true
		}
	}
	keys := []string{}
	for key := range frontmatter {
		if !seen[key] {
			keys = append(keys, key)
		}
	}
	sort.Strings(keys)
	for _, key := range keys {
		if strings.TrimSpace(frontmatter[key]) != "" {
			output = append(output, fmt.Sprintf("%s: %q", key, strings.TrimSpace(frontmatter[key])))
		}
	}
	output = append(output, "---")
	text := strings.Join(output, "\n") + "\n" + body
	if !strings.HasSuffix(text, "\n") {
		text += "\n"
	}
	return text
}

func deriveQuickIdentity(dirname string, frontmatter map[string]string) (string, string) {
	id := strings.TrimSpace(frontmatter["id"])
	slug := strings.TrimSpace(frontmatter["slug"])
	if id != "" && slug != "" {
		return id, slug
	}
	re := regexp.MustCompile(`^([0-9]{6,8}-[0-9]{3,})-(.+)$`)
	match := re.FindStringSubmatch(dirname)
	if len(match) == 3 {
		if id == "" {
			id = match[1]
		}
		if slug == "" {
			slug = match[2]
		}
	} else if id == "" {
		id = dirname
	}
	if slug == "" {
		slug = dirname
	}
	return id, slug
}

func extractNamedField(body, fieldName string) string {
	prefix := strings.ToLower(fieldName) + ":"
	for _, raw := range strings.Split(body, "\n") {
		stripped := strings.TrimSpace(raw)
		if strings.HasPrefix(strings.ToLower(stripped), prefix) {
			return strings.TrimSpace(stripped[len(prefix):])
		}
	}
	return ""
}

func extractQuickNextAction(body string) string {
	if value := extractNamedField(body, "next_action"); value != "" {
		return value
	}
	return extractSectionFirstValue(body, `^##+\s*next action\s*$`, "")
}

func extractQuickCurrentFocus(body string) string {
	if value := extractNamedField(body, "current_focus"); value != "" {
		return value
	}
	return extractSectionFirstValue(body, `^##+\s*current focus\s*$`, "goal:,next_action:")
}

func extractSectionFirstValue(body, headingPattern, skipPrefixes string) string {
	heading := regexp.MustCompile("(?i)" + headingPattern)
	anyHeading := regexp.MustCompile(`^##+\s+`)
	skips := strings.Split(skipPrefixes, ",")
	inSection := false
	for _, line := range strings.Split(body, "\n") {
		trimmed := strings.TrimSpace(line)
		if !inSection {
			inSection = heading.MatchString(trimmed)
			continue
		}
		if anyHeading.MatchString(trimmed) {
			break
		}
		cleaned := strings.TrimSpace(strings.TrimLeft(trimmed, "-*"))
		if cleaned == "" {
			continue
		}
		lower := strings.ToLower(cleaned)
		skip := false
		for _, prefix := range skips {
			if prefix != "" && strings.HasPrefix(lower, prefix) {
				skip = true
			}
		}
		if !skip {
			return cleaned
		}
	}
	return ""
}

func extractMarkdownFields(text string) map[string]string {
	result := map[string]string{}
	re := regexp.MustCompile(`^\s*-\s*([A-Za-z0-9_]+)\s*:\s*(.*?)\s*$`)
	for _, line := range strings.Split(text, "\n") {
		match := re.FindStringSubmatch(line)
		if len(match) == 3 {
			result[strings.ToLower(strings.TrimSpace(match[1]))] = strings.Trim(strings.TrimSpace(match[2]), `"'`+"`")
		}
	}
	return result
}

func extractScalarFields(text string) map[string]string {
	result := map[string]string{}
	re := regexp.MustCompile(`(?m)^\s*([a-zA-Z0-9_]+):\s*([^\r\n#]+)`)
	for _, match := range re.FindAllStringSubmatch(text, -1) {
		result[match[1]] = strings.Trim(strings.TrimSpace(match[2]), `"'`)
	}
	return result
}

func legacyDiscussionPhase(stage, status string) string {
	if status == "handoff-ready" {
		return "ready"
	}
	if discussionTerminalStatuses[status] {
		return "closed"
	}
	mapping := map[string]string{"context-intake": "explore", "product-framing": "explore", "context-grounding": "ground", "question-loop": "decide", "technical-options": "decide", "readiness-summary": "prepare", "ui-interaction-discussion": "decide", "handoff-preview": "prepare", "handoff-assessment": "prepare", "handoff-draft": "prepare", "handoff-self-review": "review", "handoff-review": "review", "handoff-ready": "ready"}
	if value := mapping[stage]; value != "" {
		return value
	}
	return "explore"
}

func readDiscussionEvents(path string) ([]map[string]any, error) {
	raw, err := os.ReadFile(path)
	if os.IsNotExist(err) {
		return []map[string]any{}, nil
	}
	if err != nil {
		return nil, err
	}
	events := []map[string]any{}
	for index, line := range strings.Split(string(raw), "\n") {
		if strings.TrimSpace(line) == "" {
			continue
		}
		var event map[string]any
		if err := json.Unmarshal([]byte(line), &event); err != nil {
			return nil, fmt.Errorf("invalid discussion event at line %d", index+1)
		}
		events = append(events, event)
	}
	return events, nil
}

func consumerEvidencePath(consumerPath string) (string, error) {
	if info, err := os.Stat(consumerPath); err == nil && !info.IsDir() {
		return consumerPath, nil
	}
	for _, candidate := range []string{filepath.Join(consumerPath, "brainstorming", "handoff-to-specify.json"), filepath.Join(consumerPath, "handoff-to-specify.json"), filepath.Join(consumerPath, "STATUS.md")} {
		if info, err := os.Stat(candidate); err == nil && !info.IsDir() {
			return candidate, nil
		}
	}
	return "", fmt.Errorf("consumer evidence is missing")
}

func readJSONMap(path string) (map[string]any, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var payload map[string]any
	if err := json.Unmarshal(raw, &payload); err != nil {
		return nil, err
	}
	if payload == nil {
		return nil, fmt.Errorf("JSON payload must be an object")
	}
	return payload, nil
}

func randomHex(size int) (string, error) {
	bytes := make([]byte, size)
	if _, err := rand.Read(bytes); err != nil {
		return "", err
	}
	return hex.EncodeToString(bytes), nil
}

func firstNonEmpty(values ...string) string {
	for _, value := range values {
		if strings.TrimSpace(value) != "" {
			return strings.TrimSpace(value)
		}
	}
	return ""
}

func defaultString(value, fallback string) string {
	if strings.TrimSpace(value) == "" {
		return fallback
	}
	return value
}

func noneIfPlaceholder(value string) any {
	trimmed := strings.TrimSpace(value)
	if trimmed == "" || strings.EqualFold(trimmed, "none") || strings.Contains(trimmed, "[") {
		return nil
	}
	return trimmed
}

func noneText(value any) string {
	if value == nil || stringValue(value) == "" {
		return "none"
	}
	return stringValue(value)
}

func stringValue(value any) string {
	switch typed := value.(type) {
	case string:
		return typed
	case nil:
		return ""
	default:
		return fmt.Sprint(typed)
	}
}

func intValue(value any) int {
	switch typed := value.(type) {
	case float64:
		return int(typed)
	case int:
		return typed
	default:
		return 0
	}
}

func mapValue(value any) map[string]any {
	if typed, ok := value.(map[string]any); ok {
		return typed
	}
	return nil
}

func listValue(value any) []any {
	if typed, ok := value.([]any); ok {
		return typed
	}
	return nil
}

func firstAny(values ...any) any {
	for _, value := range values {
		if value != nil && stringValue(value) != "" {
			return value
		}
	}
	return nil
}

func mergeMap(left, right map[string]any) map[string]any {
	result := map[string]any{}
	for key, value := range left {
		result[key] = value
	}
	for key, value := range right {
		result[key] = value
	}
	return result
}

func cloneAnyMap(value map[string]any) map[string]any {
	raw, _ := json.Marshal(value)
	var cloned map[string]any
	_ = json.Unmarshal(raw, &cloned)
	return cloned
}

func mapsToAny(values []map[string]string) []any {
	result := make([]any, len(values))
	for i, value := range values {
		result[i] = value
	}
	return result
}

func discussionErrorCodes(values []map[string]string) []string {
	result := make([]string, 0, len(values))
	for _, value := range values {
		result = append(result, value["code"])
	}
	sort.Strings(result)
	return result
}

func anyStrings(value any) []string {
	values := []string{}
	for _, item := range listValue(value) {
		values = append(values, stringValue(item))
	}
	return values
}

func allSurfaces(surfaces map[string]any, keys []string) bool {
	for _, key := range keys {
		if surfaces[key] != true {
			return false
		}
	}
	return true
}
