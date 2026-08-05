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
	"os/exec"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"time"
	"unicode"
)

func runDiscussion(args []string, stdout io.Writer) int {
	projectRoot := optionValue(args, "--project-root", ".")
	if hasFlag(args, "--help") || hasFlag(args, "-h") {
		env := NewEnvelope("ok", "discussion command help")
		env.Data["commands"] = []string{
			"list",
			"init",
			"status",
			"resume",
			"checkpoint",
			"validate-handoff",
			"write-handoff",
			"bind-consumer",
			"confirm-handoff",
			"mark-ready",
			"mark-consumed",
			"close",
			"archive",
		}
		return writeEnvelope(stdout, env)
	}
	mode := positionalArg(args, 0, "list")
	slug := positionalArg(args, 1, "")
	value := positionalArg(args, 2, "")
	includeAll := hasFlag(args, "--all")
	switch mode {
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
	case "checkpoint":
		if !hasFlag(args, "--summary") && value != "" {
			break
		}
		changes := map[string]any{"summary": optionValue(args, "--summary", "")}
		if phase := strings.TrimSpace(optionValue(args, "--phase", "")); phase != "" {
			changes["lifecycle_phase"] = strings.ToLower(phase)
		}
		if decisions := optionValues(args, "--decision"); len(decisions) > 0 {
			changes["confirmed_decisions"] = decisions
		}
		if recommendation := strings.TrimSpace(optionValue(args, "--recommendation", "")); recommendation != "" {
			changes["current_recommendation"] = recommendation
		}
		encoded, err := json.Marshal(changes)
		if err != nil {
			return writeEnvelope(stdout, scriptDomainError("discussion", err))
		}
		value = string(encoded)
	case "validate-handoff":
		value = optionValue(args, "--mode", defaultString(value, "ready"))
	case "write-handoff":
		if hasFlag(args, "--input") || value != "" {
			return writeEnvelope(stdout, scriptDomainError("discussion", fmt.Errorf("write-handoff does not accept agent-authored input files; pass the draft inline with --input-json")))
		}
		if !hasFlag(args, "--input-json") || strings.TrimSpace(optionValue(args, "--input-json", "")) == "" {
			return writeEnvelope(stdout, scriptDomainError("discussion", fmt.Errorf("write-handoff requires --input-json")))
		}
		mode = "write-handoff-json"
		value = optionValue(args, "--input-json", "")
	case "bind-consumer":
		if hasFlag(args, "--input") || value != "" {
			return writeEnvelope(stdout, scriptDomainError("discussion", fmt.Errorf("bind-consumer does not accept agent-authored input files; pass transition fields inline with --input-json")))
		}
		featureDir := strings.TrimSpace(optionValue(args, "--feature-dir", ""))
		if featureDir == "" || !hasFlag(args, "--input-json") || strings.TrimSpace(optionValue(args, "--input-json", "")) == "" {
			return writeEnvelope(stdout, scriptDomainError("discussion", fmt.Errorf("bind-consumer requires --feature-dir and --input-json")))
		}
		input, err := decodeDiscussionHandoffPayload([]byte(optionValue(args, "--input-json", "")))
		if err != nil {
			return writeEnvelope(stdout, scriptDomainError("discussion", err))
		}
		service := discussionService{projectRoot: projectRoot}
		data, err := service.bindConsumer(slug, featureDir, input)
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
	service := discussionService{projectRoot: projectRoot}
	env, err := service.run(mode, slug, value, includeAll)
	if err != nil {
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
			"status",
			"resume",
			"close",
			"archive",
			"checkpoint-stage",
			"checkpoint-confirm",
			"checkpoint-show",
			"item-start",
			"item-accept",
			"item-status",
			"packet-compile",
		}
		return writeEnvelope(stdout, env)
	}
	mode := positionalArg(args, 0, "list")
	quickID := positionalArg(args, 1, "")
	if mode == "resume" {
		mode = "status"
	}
	service := quickService{projectRoot: projectRoot}
	switch strings.ToLower(strings.TrimSpace(mode)) {
	case "checkpoint-stage", "checkpoint-confirm", "checkpoint-show":
		env, err := service.runCheckpoint(mode, quickID, args)
		if err != nil {
			return writeEnvelope(stdout, scriptDomainError("quick", err))
		}
		return writeEnvelope(stdout, env)
	case "item-start", "item-accept", "item-status", "packet-compile":
		env, err := service.runExecution(mode, quickID, args)
		if err != nil {
			return writeEnvelope(stdout, scriptDomainError("quick", err))
		}
		return writeEnvelope(stdout, env)
	}
	targetStatus := optionValue(args, "--status", positionalArg(args, 2, ""))
	includeAll := hasFlag(args, "--all")
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
	env := NewEnvelope("blocked", domain+" state command failed")
	env.Blockers = append(env.Blockers, err.Error())
	env.Data["error_code"] = domain + "-state-error"
	return env
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
		"--summary",
		"--phase",
		"--decision",
		"--recommendation",
		"--mode",
		"--input",
		"--input-json",
		"--digest",
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
	projectRoot string
}

var discussionIncompleteStatuses = map[string]bool{"active": true, "blocked": true, "handoff-ready": true}
var discussionTerminalStatuses = map[string]bool{"completed": true, "abandoned": true}
var discussionLifecyclePhases = map[string]bool{"explore": true, "ground": true, "decide": true, "prepare": true, "review": true, "ready": true, "consumed": true, "closed": true}

func (service discussionService) run(mode, slug, value string, includeAll bool) (Envelope, error) {
	var data map[string]any
	var err error
	switch strings.ToLower(strings.TrimSpace(mode)) {
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
			return Envelope{}, err
		}
		data, err = service.checkpoint(slug, changes)
	case "write-handoff-json":
		payload, parseErr := decodeDiscussionHandoffPayload([]byte(value))
		if parseErr != nil {
			return Envelope{}, parseErr
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
		return Envelope{}, fmt.Errorf("unknown mode: %s", mode)
	}
	if err != nil {
		return Envelope{}, err
	}
	env := NewEnvelope("ok", "discussion state command completed")
	env.Data = data
	return env, nil
}

func decodeDiscussionHandoffPayload(raw []byte) (map[string]any, error) {
	const maxDiscussionHandoffBytes = 16 * 1024 * 1024
	if len(raw) == 0 {
		return nil, fmt.Errorf("handoff input must not be empty")
	}
	if len(raw) > maxDiscussionHandoffBytes {
		return nil, fmt.Errorf("handoff input exceeds %d bytes", maxDiscussionHandoffBytes)
	}
	var payload map[string]any
	if err := json.Unmarshal(raw, &payload); err != nil {
		return nil, fmt.Errorf("handoff input must be a JSON object: %w", err)
	}
	if payload == nil {
		return nil, fmt.Errorf("handoff input must be a JSON object")
	}
	return payload, nil
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
		"version":           float64(2),
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
			"version":                 float64(1),
			"discussion_slug":         slug,
			"lifecycle_phase":         "explore",
			"turn_class":              "product_intent",
			"user_goal":               topic,
			"current_decision_frame":  topic,
			"confirmed_decisions":     []any{},
			"changed_recommendations": []any{},
			"context_boundary":        map[string]any{"status": "not-started"},
			"verified_fact_refs":      []any{},
			"open_assumptions":        []any{},
			"open_questions":          []any{},
			"current_recommendation":  "Shape the goal and context boundary.",
			"allowed_actions":         []any{"discuss", "ground", "checkpoint", "close"},
			"persistence_mode":        "frontstage-only",
			"next_gate":               "context-boundary",
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
	return map[string]any{"discussion": service.record(workspace, state, false), "slug": slug, "workspace_path": workspace}, nil
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
	if err := validateDiscussionState(state); err != nil {
		return err
	}
	if err := writeScriptJSONFile(filepath.Join(workspace, "discussion-state.json"), state); err != nil {
		return err
	}
	return writeScriptTextFile(filepath.Join(workspace, "discussion-state.md"), renderDiscussionMarkdown(state))
}

func validateDiscussionState(state map[string]any) error {
	if intValue(state["version"]) != 2 || state["status_family"] != "discussion" {
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
	return nil
}

func renderDiscussionMarkdown(state map[string]any) string {
	handoff := mapValue(state["handoff"])
	consumption := mapValue(state["consumption"])
	packet := mapValue(state["turn_packet"])
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
		"- current_recommendation: " + stringValue(packet["current_recommendation"]),
		"- next_gate: " + stringValue(packet["next_gate"]),
		"- blocker_reason: " + noneText(state["blocker_reason"]), "",
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

func (service discussionService) record(workspace string, state map[string]any, archived bool) map[string]any {
	consumption := mapValue(state["consumption"])
	return map[string]any{
		"slug":                       state["slug"],
		"workspace":                  filepath.Base(workspace),
		"workspace_path":             workspace,
		"status":                     state["status"],
		"lifecycle_phase":            state["lifecycle_phase"],
		"summary":                    state["summary"],
		"updated_at":                 state["updated_at"],
		"closed_at":                  state["closed_at"],
		"archived_at":                state["archived_at"],
		"next_command":               firstAny(state["next_command"], "none"),
		"handoff_consumption_status": consumption["status"],
		"consumed_at":                consumption["consumed_at"],
		"consumed_by_feature_dir":    consumption["consumer_path"],
		"archived":                   archived,
	}
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
	return map[string]any{"discussion": discussion}, nil
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
	return map[string]any{"discussion": service.record(workspace, state, false), "turn_packet": state["turn_packet"], "recent_events": events, "legacy_state": legacy}, nil
}

func (service discussionService) checkpoint(slug string, changes map[string]any) (map[string]any, error) {
	workspace, archived, err := service.findWorkspace(slug, false)
	if err != nil {
		return nil, err
	}
	if archived {
		return nil, fmt.Errorf("archived discussion cannot be checkpointed")
	}
	state, _, err := service.loadState(workspace)
	if err != nil {
		return nil, err
	}
	phase := firstNonEmpty(stringValue(changes["lifecycle_phase"]), stringValue(state["lifecycle_phase"]))
	if !discussionLifecyclePhases[phase] || phase == "ready" || phase == "consumed" || phase == "closed" {
		return nil, fmt.Errorf("invalid checkpoint lifecycle phase: %s", phase)
	}
	packet := mapValue(state["turn_packet"])
	for _, key := range []string{"confirmed_decisions", "changed_recommendations", "context_boundary", "verified_fact_refs", "open_assumptions", "open_questions", "current_recommendation", "allowed_actions", "next_gate", "current_decision_frame"} {
		if value, exists := changes[key]; exists {
			packet[key] = value
		}
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
	state["latest_checkpoint"] = map[string]any{"event_id": eventID, "timestamp": ts}
	event := map[string]any{"version": float64(1), "event_id": eventID, "timestamp": ts, "kind": "durable-checkpoint", "lifecycle_phase": phase, "summary": summary, "confirmed_decisions": packet["confirmed_decisions"], "open_questions": packet["open_questions"]}
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
	return map[string]any{"discussion": mergeMap(service.record(workspace, state, false), state), "event": event}, nil
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
	payload, err := service.renderHandoffInput(input)
	if err != nil {
		return nil, err
	}
	payload["version"] = float64(4)
	payload["handoff_kind"] = "discussion_requirement_contract"
	payload["status"] = "draft"
	payload["entry_source"] = "sp-discussion"
	payload["discussion_slug"] = slug
	payload["source_contract"] = fmt.Sprintf(".specify/discussions/%s/handoff-to-specify.json", slug)
	payload["handoff_integrity"] = "not-checked"
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
	jsonPath := filepath.Join(workspace, "handoff-to-specify.json")
	if err := writeScriptJSONFile(jsonPath, payload); err != nil {
		return nil, err
	}
	ts := nowUTCString()
	state["status"] = "active"
	state["lifecycle_phase"] = "review"
	state["updated_at"] = ts
	packet := mapValue(state["turn_packet"])
	packet["lifecycle_phase"] = "review"
	packet["context_boundary"] = payload["context_boundary"]
	packet["persistence_mode"] = "lifecycle-transition"
	packet["allowed_actions"] = []any{"review-handoff", "request-changes", "mark-ready"}
	packet["next_gate"] = "handoff-draft-validation"
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
	return map[string]any{"discussion": mergeMap(service.record(workspace, state, false), state), "review_digest": digest, "json_path": jsonPath}, nil
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
	if intValue(template["version"]) != 4 || stringValue(template["handoff_kind"]) != "discussion_requirement_contract" {
		return fmt.Errorf("discussion handoff template must use version 4 discussion_requirement_contract")
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
	_, sourcePath, err := service.handoffPaths(slug)
	if err != nil {
		return nil, err
	}
	source, err := readJSONMap(sourcePath)
	if err != nil {
		return nil, fmt.Errorf("discussion handoff is not valid JSON")
	}
	if stringValue(source["recommended_consumer"]) != "sp-specify" {
		return nil, fmt.Errorf("discussion handoff does not select sp-specify")
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
	sourceContract := fmt.Sprintf(".specify/discussions/%s/handoff-to-specify.json", slug)
	reviewDigest := stringValue(source["review_digest"])
	payload := map[string]any{
		"version":         3,
		"status":          status,
		"entry_source":    "sp-discussion",
		"discussion_slug": slug,
		"source_contract": sourceContract,
		"review_digest":   source["review_digest"],
		"semantic_delta":  input["semantic_delta"],
		"required_refs":   input["required_refs"],
		"blockers":        blockers,
		"next_action":     nextAction,
		"recovery":        input["recovery"],
	}
	target := filepath.Join(featurePath, "brainstorming", "handoff-to-specify.json")
	if _, statErr := os.Stat(target); statErr == nil {
		existing, readErr := readJSONMap(target)
		if readErr != nil {
			return nil, fmt.Errorf("feature consumer handoff already exists but is invalid; refusing to overwrite")
		}
		if stringValue(existing["discussion_slug"]) != slug ||
			stringValue(existing["source_contract"]) != sourceContract ||
			stringValue(existing["review_digest"]) != reviewDigest {
			return nil, fmt.Errorf("feature consumer handoff is already bound to a different discussion contract")
		}
	} else if !errors.Is(statErr, os.ErrNotExist) {
		return nil, fmt.Errorf("feature consumer handoff cannot be inspected: %w", statErr)
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
		"status":                  status,
		"next_action":             nextAction,
	}, nil
}

func computeDiscussionReviewDigest(payload map[string]any) (string, error) {
	protected := cloneAnyMap(payload)
	for _, field := range []string{"review_digest", "status", "handoff_integrity", "updated_at", "quality_gate"} {
		delete(protected, field)
	}
	raw, err := canonicalJSON(protected)
	if err != nil {
		return "", err
	}
	sum := sha256.Sum256(raw)
	return hex.EncodeToString(sum[:]), nil
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
	service.validateHandoffFields(payload, slug, validationMode, &errors)
	return discussionValidationPayload(workspace, errors, payload, validationMode), nil
}

func (service discussionService) handoffPaths(slug string) (string, string, error) {
	workspace, _, err := service.findWorkspace(slug, false)
	if err != nil {
		return "", "", err
	}
	return workspace, filepath.Join(workspace, "handoff-to-specify.json"), nil
}

func (service discussionService) validateHandoffFields(payload map[string]any, slug, mode string, errors *[]map[string]string) {
	expected := map[string]any{"version": float64(4), "handoff_kind": "discussion_requirement_contract", "entry_source": "sp-discussion", "discussion_slug": slug, "source_contract": fmt.Sprintf(".specify/discussions/%s/handoff-to-specify.json", slug), "coverage_status": "complete", "planning_gate_status": "ready", "hard_unknown_count": float64(0), "open_conflict_count": float64(0)}
	for field, value := range expected {
		if payload[field] != value {
			*errors = append(*errors, discussionError("invalid_"+field, fmt.Sprintf("%s must be %q", field, value)))
		}
	}
	if strings.TrimSpace(stringValue(payload["handoff_goal"])) == "" {
		*errors = append(*errors, discussionError("missing_handoff_goal", "handoff_goal is required"))
	}
	validateBoundary(payload["context_boundary"], errors)
	validateObjectList(payload["source_evidence"], []string{"source_type", "evidence_status", "source", "claim"}, "source_evidence", errors)
	validateObjectList(payload["must_preserve"], []string{"id", "type", "claim", "source", "downstream_requirement", "blocking_level", "owner", "latest_resolve_phase", "status"}, "must_preserve", errors)
	if len(listValue(payload["must_preserve"])) == 0 {
		*errors = append(*errors, discussionError("empty_must_preserve", "Must-Preserve coverage is required"))
	}
	downstream := mapValue(payload["downstream_instructions"])
	if downstream == nil {
		*errors = append(*errors, discussionError("missing_planning_constraints", "planning_constraints are required"))
	} else if _, ok := downstream["planning_constraints"]; !ok {
		*errors = append(*errors, discussionError("missing_planning_constraints", "planning_constraints are required"))
	} else if _, ok := downstream["recommended_sequence"]; ok {
		*errors = append(*errors, discussionError("legacy_recommended_sequence", "recommended_sequence is not allowed"))
	}
	service.validateConsumers(payload, errors)
	service.validateReviewDigest(payload, mode, errors)
}

func validateBoundary(value any, errors *[]map[string]string) {
	boundary := mapValue(value)
	if boundary == nil || boundary["status"] != "locked" {
		*errors = append(*errors, discussionError("unlocked_context_boundary", "context boundary must be locked"))
		return
	}
	validateObjectList(boundary["current_project_roles"], []string{"role", "scope", "evidence_source", "notes"}, "current_project_roles", errors)
	if stringValue(boundary["target_project_root"]) != "" {
		validateObjectList(boundary["target_project_roles"], []string{"role", "scope", "evidence_source", "notes"}, "target_project_roles", errors)
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
	reviewDigest := stringValue(mapValue(state["handoff"])["review_digest"])
	if reviewDigest == "" {
		return nil, fmt.Errorf("ready discussion is missing a reviewed digest")
	}
	consumerPath, err := safeProjectContainedPath(service.projectRoot, consumerPathValue)
	if err != nil {
		return nil, err
	}
	evidencePath, err := consumerEvidencePath(consumerPath)
	if err != nil {
		return nil, err
	}
	if err := service.validateConsumerEvidence(slug, reviewDigest, evidencePath); err != nil {
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
	state["consumption"] = map[string]any{"status": "consumed", "consumed_at": ts, "consumer_path": consumerRel, "evidence_path": evidenceRel, "review_digest": reviewDigest}
	if err := service.persistState(workspace, state); err != nil {
		return nil, err
	}
	if _, err := service.writeIndex(); err != nil {
		return nil, err
	}
	return map[string]any{"discussion": mergeMap(service.record(workspace, state, false), state)}, nil
}

func (service discussionService) validateConsumerEvidence(slug, digest, evidencePath string) error {
	expectedContract := fmt.Sprintf(".specify/discussions/%s/handoff-to-specify.json", slug)
	if strings.EqualFold(filepath.Ext(evidencePath), ".md") {
		raw, err := os.ReadFile(evidencePath)
		if err != nil {
			return err
		}
		fields := extractScalarFields(string(raw))
		if fields["source_discussion_slug"] != slug || fields["review_digest"] != digest {
			return fmt.Errorf("consumer evidence does not reference the reviewed discussion")
		}
		if fields["source_contract"] != expectedContract {
			return fmt.Errorf("consumer evidence does not bind the source contract")
		}
		return nil
	}
	payload, err := readJSONMap(evidencePath)
	if err != nil {
		return fmt.Errorf("consumer evidence is not valid JSON")
	}
	mismatched := []string{}
	for field, want := range map[string]string{"discussion_slug": slug, "source_contract": expectedContract, "review_digest": digest} {
		if payload[field] != want {
			mismatched = append(mismatched, field)
		}
	}
	sort.Strings(mismatched)
	if len(mismatched) > 0 {
		return fmt.Errorf("consumer evidence does not reference the reviewed discussion: %s", strings.Join(mismatched, ", "))
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
		data = map[string]any{"task": task}
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
			data = map[string]any{"task": task}
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
		return fmt.Errorf("close requires status resolved or blocked")
	}
	workspacePath := stringValue(task["workspace_path"])
	if err := service.validateCloseAgainstConfirmation(workspacePath, statusValue); err != nil {
		return err
	}
	return service.updateStatusFile(workspacePath, func(frontmatter map[string]string) {
		ts := nowUTCString()
		frontmatter["status"] = statusValue
		frontmatter["updated"] = ts
		frontmatter["closed_at"] = ts
	})
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
		if payloadMode == "init" {
			activeCommand = "sp-prd"
		}
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
	cmd := exec.Command("git", "-C", projectRoot, "rev-parse", "--is-inside-work-tree")
	output, err := cmd.CombinedOutput()
	if err != nil {
		return false
	}
	if !strings.EqualFold(strings.TrimSpace(string(output)), "true") {
		return false
	}
	head := exec.Command("git", "-C", projectRoot, "rev-parse", "--verify", "HEAD")
	return head.Run() == nil
}

func runGitValue(projectRoot string, args ...string) (string, error) {
	cmd := exec.Command("git", append([]string{"-C", projectRoot}, args...)...)
	output, err := cmd.CombinedOutput()
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
