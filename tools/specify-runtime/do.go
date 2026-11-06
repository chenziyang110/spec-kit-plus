package main

import (
	"bytes"
	"context"
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path"
	"path/filepath"
	"reflect"
	"regexp"
	"runtime"
	"sort"
	"strconv"
	"strings"
	"time"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/filelock"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runcontrol"
)

var doIDPattern = regexp.MustCompile(`^[a-zA-Z0-9][a-zA-Z0-9_-]{0,95}$`)

func runDo(args []string, stdout io.Writer) int {
	if len(args) == 0 || args[0] == "--help" || args[0] == "help" {
		_, _ = fmt.Fprintln(stdout, "usage: specify-runtime do prepare|start|next|record|validate|finish|complete|resume|show [session-id] [--input-json <json|->] [--project-root <root>] [--format json]\nprepare is read-only; start rechecks and freezes its input. next supplies frozen native-tool packets. complete validates and saves the method without rerunning tools. show --active resolves live Work; --section method|definition|definitions|definition:<epoch>|attempts|attempt:<id>|metrics expands selected detail. resume supports observed failure recovery or explicit unstarted adjustment. Runtime records tool observations; it never executes the operation.")
		return 0
	}
	for _, arg := range args[1:] {
		if arg == "--help" {
			return runDo(nil, stdout)
		}
	}
	command := args[0]
	parseArgs := append([]string(nil), args[1:]...)
	for i, arg := range parseArgs {
		if arg == "--active" && (i+1 == len(parseArgs) || strings.HasPrefix(parseArgs[i+1], "--")) {
			parseArgs = append(parseArgs[:i+1], append([]string{"true"}, parseArgs[i+1:]...)...)
			break
		}
	}
	parsed, err := parseCoordinationCommandArgs(parseArgs, -1, "--project-root", "--format", "--input-json", "--active", "--section", "--adapter-id")
	if err != nil {
		return doError(stdout, err, "")
	}
	if err = parsed.validateJSONFormat(); err != nil {
		return doError(stdout, err, "")
	}
	active := parsed.option("--active", "")
	if active != "" && (command != "show" || active != "true" || len(parsed.positionals) != 0 || parsed.option("--section", "") != "") {
		return doError(stdout, fmt.Errorf("--active is a standalone show selector and cannot choose a detail section"), "")
	}
	if parsed.option("--adapter-id", "") != "" && active != "true" {
		return doError(stdout, fmt.Errorf("--adapter-id filters only do show --active"), "")
	}
	if parsed.option("--section", "") != "" && command != "show" {
		return doError(stdout, fmt.Errorf("--section is only supported by do show"), "")
	}
	initial := command == "start" || command == "prepare"
	if (initial && len(parsed.positionals) != 0) || (!initial && active != "true" && len(parsed.positionals) != 1) {
		return doError(stdout, fmt.Errorf("start uses session_id in input; other operations require exactly one session id or show --active"), "")
	}
	if (command == "show" || command == "validate" || command == "next") && parsed.option("--input-json", "") != "" {
		return doError(stdout, fmt.Errorf("read-only show and validate do not accept mutation input"), "")
	}
	root, err := filepath.Abs(parsed.option("--project-root", "."))
	if err != nil {
		return doError(stdout, err, "")
	}
	if command == "show" && active == "true" {
		return doShowActive(root, stdout, parsed.option("--adapter-id", ""))
	}
	id := ""
	if len(parsed.positionals) == 1 {
		id = parsed.positionals[0]
	}
	if !initial && !doIDPattern.MatchString(id) {
		return doError(stdout, fmt.Errorf("an exact valid session id is required"), "")
	}
	if initial {
		if id != "" {
			return doError(stdout, fmt.Errorf("start takes its optional session_id in --input-json"), "")
		}
		var input doStartInput
		if err := doReadInput(parsed.option("--input-json", ""), &input); err != nil {
			return doError(stdout, err, "", "do-"+command+"-input")
		}
		if command == "prepare" {
			data, err := doPrepare(root, input)
			if err != nil {
				return doError(stdout, err, "", "do-prepare-input")
			}
			env := NewEnvelope("ok", "operation inputs prepared; no session or Work created")
			env.Data = data
			return writeEnvelope(stdout, env)
		}
		session, err := doStart(root, input)
		if err != nil {
			return doError(stdout, err, input.SessionID)
		}
		return doSessionEnvelope(stdout, session, "operation plan frozen; execute only through authorized native tools", nil)
	}
	if command == "next" {
		session, _, err := loadDoSession(root, id)
		if err != nil {
			return doError(stdout, err, id)
		}
		data, err := doNext(root, session)
		if err != nil {
			return doError(stdout, err, id)
		}
		return doSessionEnvelope(stdout, session, "next frozen operation packets; record started before calling tools", nil, data)
	}
	if command == "complete" {
		var input doCompleteInput
		if err := doReadInput(parsed.option("--input-json", ""), &input); err != nil {
			return doError(stdout, err, id)
		}
		session, err := doComplete(root, id, input)
		if err != nil {
			return doError(stdout, err, id)
		}
		return doSessionEnvelope(stdout, session, "operation and method closeout completed", nil)
	}
	if command == "show" || command == "validate" || (command == "resume" && parsed.option("--input-json", "") == "") {
		session, _, err := loadDoSession(root, id)
		if err != nil {
			return doError(stdout, err, id)
		}
		if command == "validate" {
			validation := doValidate(root, session, true)
			return doSessionEnvelope(stdout, session, "operation evidence checked; tool observations remain agent-observed", &validation)
		}
		section := parsed.option("--section", "")
		if section != "" {
			if command != "show" {
				return doError(stdout, fmt.Errorf("--section is only supported by do show"), id)
			}
			extra := map[string]any{}
			switch section {
			case "method":
				extra["method_definition"] = doMethodDefinition(session)
				extra["method_digest"] = doMethodDigest(session)
				extra["parameters"] = session.Parameters
			case "metrics":
				extra["metrics"] = doSessionMetrics(session)
			case "definition":
				extra["definition"] = session.Definition
			case "definitions":
				doEnsureDefinitionHistory(&session)
				cards := []map[string]any{}
				for _, epoch := range session.DefinitionHistory {
					cards = append(cards, map[string]any{"epoch": epoch.Epoch, "definition_digest": epoch.DefinitionDigest, "frozen_at": epoch.FrozenAt, "current": epoch.Epoch == doCurrentDefinitionEpoch(session), "show_argv": []string{"specify-runtime", "do", "show", session.ID, "--section", fmt.Sprintf("definition:%d", epoch.Epoch), "--format", "json"}})
				}
				extra["definitions"] = cards
			case "attempts":
				extra["attempts"] = session.Attempts
			default:
				if strings.HasPrefix(section, "definition:") {
					epochID, err := strconv.Atoi(strings.TrimPrefix(section, "definition:"))
					doEnsureDefinitionHistory(&session)
					if err != nil || epochID < 1 || epochID > len(session.DefinitionHistory) {
						return doError(stdout, fmt.Errorf("definition epoch not found"), id)
					}
					extra["definition_snapshot"] = session.DefinitionHistory[epochID-1]
					break
				}
				if !strings.HasPrefix(section, "attempt:") {
					return doError(stdout, fmt.Errorf("section must be method, definition, definitions, definition:<epoch>, attempts, attempt:<id>, or metrics"), id)
				}
				found := false
				for _, attempt := range session.Attempts {
					if attempt.ID == strings.TrimPrefix(section, "attempt:") {
						extra["attempt"] = attempt
						found = true
						break
					}
				}
				if !found {
					return doError(stdout, fmt.Errorf("attempt section not found"), id)
				}
			}
			return doSessionEnvelope(stdout, session, "selected operation detail", nil, extra)
		}
		return doSessionEnvelope(stdout, session, "operation state; inspect interrupted side effects before retrying", nil)
	}
	if command != "record" && command != "finish" && command != "resume" {
		return doError(stdout, fmt.Errorf("unknown do subcommand %q", command), id)
	}
	release, err := doSessionLock(root, id)
	if err != nil {
		return doError(stdout, err, id)
	}
	defer release()
	session, digest, err := loadDoSession(root, id)
	if err != nil {
		return doError(stdout, err, id)
	}
	switch command {
	case "record":
		var input doRecordInput
		if err = doReadInput(parsed.option("--input-json", ""), &input); err == nil {
			session, err = doRecord(root, session, digest, input)
		}
	case "finish":
		var input doFinishInput
		if err = doReadInput(parsed.option("--input-json", ""), &input); err == nil {
			session, err = doFinish(root, session, digest, input)
		}
	case "resume":
		var input doResumeInput
		if err = doReadInput(parsed.option("--input-json", ""), &input); err == nil {
			session, err = doResume(root, session, digest, input)
		}
	}
	if err != nil {
		return doError(stdout, err, id)
	}
	return doSessionEnvelope(stdout, session, "operation checkpoint saved", nil)
}

func doReadInput(raw string, target any) error {
	if strings.TrimSpace(raw) == "" {
		return fmt.Errorf("--input-json is required (inline JSON or - for stdin)")
	}
	var reader io.Reader = strings.NewReader(raw)
	if raw == "-" {
		reader = os.Stdin
	} else if strings.HasPrefix(raw, "@") {
		return fmt.Errorf("use inline JSON or stdin, not an authoring file")
	}
	data, err := io.ReadAll(io.LimitReader(reader, 256*1024+1))
	if err != nil {
		return err
	}
	if len(data) > 256*1024 {
		return fmt.Errorf("input exceeds 256 KiB")
	}
	if err := playbookRejectDuplicateKeys(data); err != nil {
		return err
	}
	decoder := json.NewDecoder(bytes.NewReader(data))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(target); err != nil {
		return fmt.Errorf("invalid do input: %w", playbookDescribeJSONError(data, target, err))
	}
	var extra any
	if err := decoder.Decode(&extra); err != io.EOF {
		return fmt.Errorf("input must contain exactly one JSON value")
	}
	return nil
}

func doError(stdout io.Writer, err error, id string, schemas ...string) int {
	env := NewEnvelope("blocked", "operation cannot advance")
	resume := "correct the input and retry the same operation; no session was created"
	if doIDPattern.MatchString(id) {
		resume = "inspect the exact session and preserve prior attempts"
	}
	env.Blockers = append(env.Blockers, map[string]any{"code": "do-operation-blocked", "owner": "agent", "cause": err.Error(), "resume_point": resume})
	var inputError *playbookJSONInputError
	if errors.As(err, &inputError) {
		env.Data["validation_errors"] = inputError.Issues
	}
	if len(schemas) > 0 {
		env.Data["schema_argv"] = []string{"specify-runtime", "api", "schema", schemas[0], "--format", "json"}
		if inputError == nil {
			if match := regexp.MustCompile(`pointer=([^\s]+)`).FindStringSubmatch(err.Error()); match != nil {
				pointer := match[1]
				if strings.HasPrefix(pointer, "/steps/") || strings.HasPrefix(pointer, "/checks/") || strings.HasPrefix(pointer, "/parameters/") || pointer == "/owner" {
					pointer = "/definition" + pointer
				}
				env.Data["validation_errors"] = []playbookJSONIssue{{InstancePath: pointer, Keyword: "semantic", Message: strings.TrimSpace(strings.SplitN(err.Error(), "pointer=", 2)[0])}}
			}
		}
	}
	if doIDPattern.MatchString(id) {
		env.ShowArgv = []string{"specify-runtime", "do", "show", id, "--format", "json"}
	}
	return writeEnvelope(stdout, env)
}

func doSessionEnvelope(stdout io.Writer, session DoSession, summary string, validation *DoValidation, extra ...map[string]any) int {
	env := NewEnvelope("ok", summary)
	terminal := session.ExecutionOutcome == "passed" && (session.KnowledgeStatus == "saved" || session.KnowledgeStatus == "not_applicable")
	env.Data["active"] = !terminal
	env.Data["terminal"] = terminal
	env.Data["can_stop"] = terminal || session.Blocker != nil
	latest := doLatestAttempts(session)
	attempts := []map[string]any{}
	for _, step := range session.Definition.Steps {
		if attempt, ok := latest[step.ID]; ok {
			attempts = append(attempts, map[string]any{"id": attempt.ID, "target_id": attempt.TargetID, "kind": attempt.Kind, "status": attempt.Status})
		}
	}
	for _, check := range session.Definition.Checks {
		if attempt, ok := latest[check.ID]; ok {
			attempts = append(attempts, map[string]any{"id": attempt.ID, "target_id": attempt.TargetID, "kind": attempt.Kind, "status": attempt.Status})
		}
	}
	env.Data["session"] = map[string]any{"id": session.ID, "revision": session.Revision, "goal": session.Goal, "definition_digest": session.DefinitionDigest, "method_binding": session.MethodBinding, "work_id": session.WorkID, "work_fence": session.WorkFence, "write_scope": session.WriteScope, "output_scope": session.OutputScope, "execution_outcome": session.ExecutionOutcome, "knowledge_status": session.KnowledgeStatus, "blocker": session.Blocker, "attempt_count": len(session.Attempts), "latest_attempts": attempts, "validation": session.Validation, "knowledge": session.Knowledge}
	env.Data["session_id"] = session.ID
	env.Data["revision"] = session.Revision
	env.Data["work_id"] = session.WorkID
	env.Data["work_fence"] = session.WorkFence
	env.Data["definition_digest"] = session.DefinitionDigest
	env.Data["definition_epoch"] = doCurrentDefinitionEpoch(session)
	if session.TemplateDefinition != nil {
		env.Data["method_digest"] = doMethodDigest(session)
		env.Data["method_argv"] = []string{"specify-runtime", "do", "show", session.ID, "--section", "method", "--format", "json"}
	}
	env.Data["definition_argv"] = []string{"specify-runtime", "do", "show", session.ID, "--section", "definition", "--format", "json"}
	env.Data["definitions_argv"] = []string{"specify-runtime", "do", "show", session.ID, "--section", "definitions", "--format", "json"}
	env.Data["attempts_argv"] = []string{"specify-runtime", "do", "show", session.ID, "--section", "attempts", "--format", "json"}
	env.Data["evidence_origin"] = "agent_tool_observation"
	env.Data["runtime_execution_verified"] = false
	env.ShowArgv = []string{"specify-runtime", "do", "show", session.ID, "--format", "json"}
	if validation != nil {
		env.Data["validation"] = validation
		env.Data["ready_to_finish"] = validation.Status == "passed"
		if validation.Status != "passed" {
			env.Status = "blocked"
			for _, blocker := range validation.Blockers {
				env.Blockers = append(env.Blockers, blocker)
			}
		}
	}
	if !terminal {
		env.NextArgv = []string{"specify-runtime", "do", "next", session.ID, "--format", "json"}
	}
	for _, fields := range extra {
		for key, value := range fields {
			env.Data[key] = value
		}
	}
	return writeEnvelope(stdout, env)
}

func doShowActive(root string, stdout io.Writer, adapters ...string) int {
	env := NewEnvelope("ok", "live Do sessions resolved from Work Board")
	env.Data["active"] = false
	view, err := runcontrol.OpenViewForRepository(context.Background(), root)
	if err != nil {
		if os.IsNotExist(err) || errors.Is(err, runcontrol.ErrNotFound) {
			return writeEnvelope(stdout, env)
		}
		return doError(stdout, err, "")
	}
	defer view.Close()
	items, err := view.ListWork(context.Background(), runcontrol.ListWorkParams{Statuses: []runcontrol.WorkStatus{runcontrol.WorkActive, runcontrol.WorkBlocked, runcontrol.WorkInterrupted}})
	if err != nil {
		return doError(stdout, err, "")
	}
	ids := []string{}
	for _, item := range items {
		if len(adapters) > 0 && adapters[0] != "" && item.AdapterID != adapters[0] {
			continue
		}
		if strings.HasPrefix(item.TaskRef, "do:") && filepath.Clean(item.WorkspaceRoot) == filepath.Clean(root) {
			id := strings.TrimPrefix(item.TaskRef, "do:")
			if doIDPattern.MatchString(id) {
				ids = append(ids, id)
			}
		}
	}
	sort.Strings(ids)
	if len(ids) == 0 {
		return writeEnvelope(stdout, env)
	}
	if len(ids) > 1 {
		env.Status = "blocked"
		env.Data["active"] = true
		env.Data["ambiguous"] = true
		env.Data["session_ids"] = ids
		env.Blockers = append(env.Blockers, "multiple active Do sessions; select an exact id, never latest")
		return writeEnvelope(stdout, env)
	}
	session, _, err := loadDoSession(root, ids[0])
	if err != nil {
		return doError(stdout, err, ids[0])
	}
	return doSessionEnvelope(stdout, session, "current Do session", nil)
}

func doSessionRef(id string) string { return path.Join(".specify/do/sessions", id, "session.json") }
func doDigest(value any) string {
	raw, _ := json.Marshal(value)
	sum := sha256.Sum256(raw)
	return hex.EncodeToString(sum[:])
}
func doBytesDigest(raw []byte) string { sum := sha256.Sum256(raw); return hex.EncodeToString(sum[:]) }
func doNow() string                   { return time.Now().UTC().Format(time.RFC3339Nano) }

func loadDoSession(root, id string) (DoSession, string, error) {
	var session DoSession
	if !doIDPattern.MatchString(id) {
		return session, "", fmt.Errorf("invalid session id")
	}
	raw, err := doReadCheckpoint(root, doSessionRef(id))
	if err != nil {
		return session, "", err
	}
	if len(raw) > doSessionSizeLimit {
		return session, "", fmt.Errorf("session exceeds size limit")
	}
	if err = json.Unmarshal(raw, &session); err != nil {
		return session, "", err
	}
	if (session.SchemaVersion != doSessionSchema && session.SchemaVersion != doLegacySessionSchema) || session.ID != id || session.Revision < 1 {
		return session, "", fmt.Errorf("invalid session identity or schema")
	}
	digest, err := playbookDefinitionDigest(session.Definition)
	if err != nil || digest != session.DefinitionDigest {
		return session, "", fmt.Errorf("frozen operation definition was changed")
	}
	if err := doValidateDefinitionHistory(root, session); err != nil {
		return session, "", err
	}
	if err := doVerifyInstanceBinding(root, session); err != nil {
		return session, "", err
	}
	var fields map[string]json.RawMessage
	if err := json.Unmarshal(raw, &fields); err != nil {
		return session, "", err
	}
	if session.SchemaVersion == doSessionSchema {
		if _, inline := fields["baseline_json"]; inline {
			return session, "", fmt.Errorf("referenced workspace baseline cannot also be stored inline")
		}
	} else {
		_, referenced := fields["baseline_ref"]
		_, bound := fields["baseline_sha256"]
		if referenced || bound {
			return session, "", fmt.Errorf("legacy session cannot carry a workspace baseline reference")
		}
	}
	if err := doHydrateBaseline(root, &session); err != nil {
		return session, "", err
	}
	if session.Requests == nil {
		session.Requests = map[string]string{}
	}
	return session, doBytesDigest(raw), nil
}

func doSessionLock(root, id string) (func(), error) {
	if !doIDPattern.MatchString(id) {
		return nil, fmt.Errorf("invalid session id")
	}
	lock, err := secureProjectPath(root, path.Join(".specify/runtime/receipts/do-locks", id+".lock"))
	if err != nil {
		return nil, err
	}
	if err = os.MkdirAll(filepath.Dir(lock), 0o700); err != nil {
		return nil, err
	}
	return filelock.Acquire(lock)
}

func doWriteSession(root string, session DoSession, expected string, extra []fileTransactionUpdate) error {
	target, err := secureProjectPath(root, doSessionRef(session.ID))
	if err != nil {
		return err
	}
	raw, err := doSerializeSession(session)
	if err != nil {
		return err
	}
	updates := append([]fileTransactionUpdate{}, extra...)
	updates = append(updates, fileTransactionUpdate{Path: target, Content: raw, Perm: 0o600})
	conditions := []fileTransactionPrecondition{{Path: target, ExpectedSHA256: expected, MustNotExist: expected == ""}}
	for _, update := range extra {
		conditions = append(conditions, fileTransactionPrecondition{Path: update.Path, MustNotExist: true})
	}
	var verify func() error
	if session.SchemaVersion == doSessionSchema {
		baselineTarget, err := secureProjectPath(root, session.BaselineRef)
		if err != nil {
			return err
		}
		if expected == "" {
			updates = append(updates, fileTransactionUpdate{Path: baselineTarget, Content: []byte(session.BaselineJSON), Perm: 0o600})
			conditions = append(conditions, fileTransactionPrecondition{Path: baselineTarget, MustNotExist: true})
		} else {
			// Never rewrite the sidecar. Its bounded digest check is a CAS
			// prerequisite under the same transaction lock as session.json.
			// Avoid generic file preconditions, which read without a size bound.
			verify = func() error {
				raw, err := doReadBaseline(root, session.BaselineRef)
				if err != nil {
					return err
				}
				if doBytesDigest(raw) != session.BaselineSHA256 {
					return fmt.Errorf("immutable workspace baseline digest mismatch")
				}
				return nil
			}
		}
	}
	_, err = applyFileTransactionWithVerification(root, "do-session", updates, conditions, verify)
	return err
}

func doPath(root, relative string, allowDot bool) (string, error) {
	if strings.ContainsRune(relative, '\x00') || strings.Contains(relative, "\\") || path.IsAbs(relative) || filepath.IsAbs(relative) || strings.Contains(relative, ":") {
		return "", fmt.Errorf("path must be project-relative")
	}
	clean := path.Clean(relative)
	if clean == ".." || strings.HasPrefix(clean, "../") || (!allowDot && clean == ".") {
		return "", fmt.Errorf("invalid project-relative path %q", relative)
	}
	for _, part := range strings.Split(clean, "/") {
		if strings.EqualFold(part, ".git") {
			return "", fmt.Errorf("Git metadata is not operation scope")
		}
	}
	if strings.ContainsAny(clean, "*?[]") {
		return "", fmt.Errorf("use exact paths or directories, not globs")
	}
	_, err := secureProjectPath(root, clean)
	return clean, err
}

func doWorkflowStatePath(relative string) bool {
	folded := strings.ToLower(relative)
	return folded == ".specify" || strings.HasPrefix(folded, ".specify/") || folded == ".planning" || strings.HasPrefix(folded, ".planning/")
}

func doScopeContains(scope []string, p string) bool {
	if runtime.GOOS == "windows" {
		p = strings.ToLower(p)
	}
	for _, s := range scope {
		if runtime.GOOS == "windows" {
			s = strings.ToLower(s)
		}
		if p == s || strings.HasPrefix(p, strings.TrimSuffix(s, "/")+"/") {
			return true
		}
	}
	return false
}

func doStart(root string, input doStartInput) (DoSession, error) {
	if input.Command != nil {
		return DoSession{}, fmt.Errorf("command is prepare-only; pass the canonical start_input returned by do prepare")
	}
	var empty DoSession
	if strings.TrimSpace(input.AgentID) == "" || strings.TrimSpace(input.AdapterID) == "" {
		return empty, fmt.Errorf("agent_id and adapter_id are required")
	}
	input.AgentID = strings.TrimSpace(input.AgentID)
	input.AdapterID = strings.TrimSpace(input.AdapterID)
	if input.Context == nil {
		input.Context = map[string]string{}
	}
	input.Context["os"] = runtime.GOOS
	input.Context["arch"] = runtime.GOARCH
	if input.MethodBinding != nil {
		doc, err := loadPlaybookDocument(root, input.MethodBinding.ID)
		if err != nil {
			return empty, err
		}
		if doc.Revision != input.MethodBinding.Revision || doc.ContentDigest != input.MethodBinding.ContentDigest {
			return empty, fmt.Errorf("method binding is stale or mismatched")
		}
		if input.Definition.Goal == "" {
			input.Definition = doc.Definition
		}
	}
	if len(input.SourceFiles) > 0 {
		input.Definition.SourceFiles = append(input.Definition.SourceFiles, input.SourceFiles...)
	}
	if err := validatePlaybookDefinition(root, input.Definition); err != nil {
		return empty, err
	}
	input.Definition = playbookNormalizeDefinition(input.Definition)
	template := input.Definition
	resolved, parameters, err := resolvePlaybookDefinition(root, template, input.Parameters)
	if err != nil {
		return empty, err
	}
	input.Definition = resolved
	input.Parameters = parameters
	if input.MethodBinding != nil && input.MethodBinding.ID != playbookID(input.Definition) {
		return empty, fmt.Errorf("method binding belongs to a different operation identity")
	}
	if gaps := playbookCompatibility(input.Definition, input.Context); len(gaps) > 0 {
		return empty, fmt.Errorf("incompatible method: %s", strings.Join(gaps, "; "))
	}
	if strings.TrimSpace(input.Goal) == "" {
		input.Goal = input.Definition.Goal
	}
	if input.Goal != input.Definition.Goal {
		return empty, fmt.Errorf("goal must equal the frozen definition goal")
	}
	id := input.SessionID
	if id == "" {
		var suffix [8]byte
		if _, err := rand.Read(suffix[:]); err != nil {
			return empty, err
		}
		id = "do-" + hex.EncodeToString(suffix[:])
	}
	if !doIDPattern.MatchString(id) {
		return empty, fmt.Errorf("invalid session id")
	}
	release, err := doSessionLock(root, id)
	if err != nil {
		return empty, err
	}
	defer release()
	if _, err := secureProjectReadFile(root, doSessionRef(id)); err == nil {
		existing, _, readErr := loadDoSession(root, id)
		if readErr != nil {
			return empty, readErr
		}
		requestedDigest, digestErr := playbookDefinitionDigest(input.Definition)
		requestedTemplateDigest, _ := playbookDefinitionDigest(template)
		if doMethodDigest(existing) != requestedTemplateDigest {
			return empty, fmt.Errorf("session_id already binds a different method template")
		}
		if digestErr != nil || existing.DefinitionDigest != requestedDigest || existing.Goal != input.Goal || !reflect.DeepEqual(existing.Parameters, input.Parameters) || !reflect.DeepEqual(existing.MethodBinding, input.MethodBinding) || !reflect.DeepEqual(uniqueSortedTrimmed(existing.WriteScope), uniqueSortedTrimmed(input.WriteScope)) || !reflect.DeepEqual(uniqueSortedTrimmed(existing.OutputScope), uniqueSortedTrimmed(input.OutputScope)) || !reflect.DeepEqual(existing.Context, input.Context) {
			return empty, fmt.Errorf("session_id already binds a different operation; resume it or choose a new id")
		}
		view, viewErr := runcontrol.OpenViewForRepository(context.Background(), root)
		if viewErr != nil {
			return empty, viewErr
		}
		defer view.Close()
		work, _, workErr := view.GetWork(context.Background(), existing.WorkID)
		if workErr != nil {
			return empty, workErr
		}
		if work.TaskRef != "do:"+id || work.Fence != existing.WorkFence || work.AgentID != input.AgentID || work.AdapterID != input.AdapterID {
			return empty, fmt.Errorf("session_id belongs to another Work owner or fence; resume it explicitly or choose a new id")
		}
		return existing, nil
	} else if !os.IsNotExist(err) {
		return empty, err
	}
	for _, set := range [][]string{input.WriteScope, input.OutputScope} {
		for i, value := range set {
			clean, err := doPath(root, value, false)
			if err != nil {
				return empty, err
			}
			if doWorkflowStatePath(clean) {
				return empty, fmt.Errorf("runtime/workflow state is not product or output scope")
			}
			set[i] = clean
		}
	}
	if err := doValidateOperationScopes(input.Definition, input.WriteScope, input.OutputScope); err != nil {
		return empty, err
	}
	sources, fingerprint, sourceRevision, dirty, err := doCaptureSource(root, input.Definition, input.WriteScope)
	if err != nil {
		return empty, err
	}
	baseline, err := runcontrol.CaptureWorkspaceBaseline(context.Background(), root)
	if err != nil {
		return empty, err
	}
	baselineJSON, err := runcontrol.EncodeWorkspaceBaseline(baseline)
	if err != nil {
		return empty, err
	}
	digest, err := playbookDefinitionDigest(input.Definition)
	if err != nil {
		return empty, err
	}
	now := doNow()
	session := DoSession{SchemaVersion: doSessionSchema, ID: id, Revision: 1, Goal: input.Goal, Definition: input.Definition, DefinitionDigest: digest, MethodBinding: input.MethodBinding, Context: input.Context, InitialSources: sources, BaselineJSON: baselineJSON, BaselineRef: doBaselineRef(id), BaselineSHA256: doBytesDigest([]byte(baselineJSON)), WriteScope: input.WriteScope, OutputScope: input.OutputScope, WorkID: "work-" + id, WorkFence: 1, ExecutionOutcome: "pending", KnowledgeStatus: "pending", Attempts: []DoAttempt{}, Requests: map[string]string{}, CreatedAt: now, UpdatedAt: now}
	if len(template.Parameters) > 0 {
		session.TemplateDefinition = &template
		session.TemplateDigest, _ = playbookDefinitionDigest(template)
		session.Parameters = parameters
	}
	doInitializeDefinitionEpoch(&session, sources, fingerprint, sourceRevision, dirty)
	// The deterministic checkpoint and baseline safety limits must pass before
	// registration can leave an active Work claim with no readable session.
	if _, err := doSerializeSession(session); err != nil {
		return empty, err
	}
	if _, err := secureProjectPath(root, doSessionRef(id)); err != nil {
		return empty, err
	}
	baselineTarget, err := secureProjectPath(root, session.BaselineRef)
	if err != nil {
		return empty, err
	}
	if _, err := os.Lstat(baselineTarget); err == nil {
		return empty, fmt.Errorf("immutable workspace baseline already exists without its session; inspect transaction recovery before retrying")
	} else if !os.IsNotExist(err) {
		return empty, err
	}
	workScope := append(append([]string{}, input.WriteScope...), input.OutputScope...)
	workScope = append(workScope, path.Dir(doSessionRef(id)))
	intents := []runcontrol.WriteIntentSpec{}
	seen := map[string]bool{}
	for _, p := range workScope {
		if !seen[p] {
			seen[p] = true
			intents = append(intents, runcontrol.WriteIntentSpec{Path: p, Operation: runcontrol.WriteModify, Confidence: runcontrol.IntentConfirmed, Reason: "frozen Do operation scope"})
		}
	}
	store, err := runcontrol.OpenForRepository(context.Background(), root)
	if err != nil {
		return empty, err
	}
	defer store.Close()
	if _, err = store.ReconcileRepositoryWork(context.Background(), time.Now().UTC()); err != nil {
		return empty, err
	}
	work, _, err := store.BeginWork(context.Background(), runcontrol.BeginWorkParams{WorkID: "work-" + id, TaskRef: "do:" + id, Summary: input.Goal, AgentID: input.AgentID, AdapterID: input.AdapterID, WorkspaceRoot: root, BaseCommit: baseline.HeadCommit, NextAction: "record a started attempt before native execution", LeaseUntil: time.Now().UTC().Add(30 * time.Minute), WriteIntents: intents})
	if err != nil {
		return empty, err
	}
	session.WorkID, session.WorkFence = work.WorkID, work.Fence
	if err = doWriteSession(root, session, "", nil); err != nil {
		return empty, fmt.Errorf("session publication failed; Work %s preserves its scope, inspect before recovery: %w", work.WorkID, err)
	}
	return session, nil
}

func doCaptureSource(root string, definition PlaybookDefinition, writeScopes ...[]string) (map[string]string, string, string, []string, error) {
	sources, err := playbookSourceFingerprint(root, definition)
	if err != nil {
		return nil, "", "", nil, err
	}
	for _, scopes := range writeScopes {
		for _, scope := range scopes {
			target, err := secureProjectPath(root, scope)
			if err != nil {
				return nil, "", "", nil, err
			}
			if _, err := os.Stat(target); os.IsNotExist(err) {
				sources[scope] = doBytesDigest([]byte("missing owned source"))
				continue
			} else if err != nil {
				return nil, "", "", nil, err
			}
			err = filepath.WalkDir(target, func(file string, entry os.DirEntry, walkErr error) error {
				if walkErr != nil {
					return walkErr
				}
				if len(sources) > 512 {
					return fmt.Errorf("owned source scope exceeds 512 files; narrow the operation")
				}
				rel, err := filepath.Rel(root, file)
				if err != nil {
					return err
				}
				rel = filepath.ToSlash(rel)
				if _, err := secureProjectPath(root, rel); err != nil {
					return err
				}
				if entry.IsDir() {
					return nil
				}
				info, err := entry.Info()
				if err != nil {
					return err
				}
				if !info.Mode().IsRegular() || info.Size() > 16*1024*1024 {
					return fmt.Errorf("owned source must be a bounded regular file")
				}
				raw, err := os.ReadFile(file)
				if err != nil {
					return err
				}
				sources[rel] = doDigest(map[string]any{"bytes": doBytesDigest(raw), "mode": info.Mode().Perm()})
				return nil
			})
			if err != nil {
				return nil, "", "", nil, err
			}
		}
	}
	head, err := runcontrol.ReadHeadCommit(context.Background(), root)
	if err != nil {
		head = "unborn"
	}
	dirty, err := runcontrol.InspectWorkspaceChanges(context.Background(), root)
	if err != nil {
		return nil, "", "", nil, err
	}
	relevant := []string{}
	for _, p := range dirty {
		for source := range sources {
			if p == source || strings.HasPrefix(p, source+"/") {
				relevant = append(relevant, p)
				break
			}
		}
	}
	sort.Strings(relevant)
	fingerprint := doDigest(map[string]any{"files": sources, "source_revision": head, "dirty_paths": relevant})
	return sources, fingerprint, head, relevant, nil
}

func doRequireWork(root string, session DoSession) error {
	store, err := runcontrol.OpenForRepository(context.Background(), root)
	if err != nil {
		return err
	}
	defer store.Close()
	work, _, err := store.GetWork(context.Background(), session.WorkID)
	if err != nil {
		return err
	}
	if work.Fence != session.WorkFence || work.TaskRef != "do:"+session.ID || work.Status != runcontrol.WorkActive {
		return fmt.Errorf("Work ownership is not active or its fence changed; use Work recovery before mutating the session")
	}
	_, err = store.RenewWorkLease(context.Background(), runcontrol.RenewWorkLeaseParams{WorkID: work.WorkID, Fence: work.Fence, LeaseUntil: time.Now().UTC().Add(30 * time.Minute)})
	return err
}

func doRecord(root string, session DoSession, oldDigest string, input doRecordInput) (DoSession, error) {
	if !doIDPattern.MatchString(input.RequestID) {
		return session, fmt.Errorf("valid request_id is required")
	}
	requestDigest := doDigest(input)
	if previous, ok := session.Requests[input.RequestID]; ok {
		if previous == requestDigest {
			return session, nil
		}
		return session, fmt.Errorf("request_id was reused with a different payload")
	}
	if input.ExpectedRevision != session.Revision {
		return session, fmt.Errorf("session revision conflict")
	}
	if session.ExecutionOutcome == "passed" {
		return session, fmt.Errorf("execution already passed; resume knowledge capture without rerunning")
	}
	if len(input.Events) == 0 || len(input.Events) > 32 {
		return session, fmt.Errorf("record needs 1 to 32 events")
	}
	if err := doRequireWork(root, session); err != nil {
		return session, err
	}
	existing := map[string]bool{}
	for _, attempt := range session.Attempts {
		existing[attempt.ID] = true
	}
	extra := []fileTransactionUpdate{}
	for _, event := range input.Events {
		var err error
		var writes []fileTransactionUpdate
		session, writes, err = doApplyRecordEvent(root, session, event, existing)
		if err != nil {
			return session, err
		}
		extra = append(extra, writes...)
	}
	session.Requests[input.RequestID] = requestDigest
	session.Revision++
	session.UpdatedAt = doNow()
	session.Validation = nil
	if len(session.Attempts) > 512 || len(session.Requests) > 1024 {
		return session, fmt.Errorf("session record limit reached; split unrelated work into a new session")
	}
	err := doWriteSession(root, session, oldDigest, extra)
	return session, err
}

func doResume(root string, session DoSession, oldDigest string, input doResumeInput) (DoSession, error) {
	if input.ExternalChanges != nil {
		return doResumeExternalChanges(root, session, oldDigest, input)
	}
	if input.Replan != nil {
		return doReplan(root, session, oldDigest, input)
	}
	if input.Recovery.EvidenceSHA256 != "" {
		return session, fmt.Errorf("recovery evidence_sha256 is runtime-owned")
	}
	requestDigest := doDigest(input)
	if previous, ok := session.ResumeReceipts[requestDigest]; ok {
		raw, err := secureProjectReadFile(root, doRecoveryEvidenceRef(session, input))
		if err != nil || doBytesDigest(raw) != previous {
			return session, fmt.Errorf("replayed recovery evidence is missing or changed")
		}
		return session, nil
	}
	if session.Blocker != nil && input.AttemptID == "" {
		return doResolveBlocker(root, session, oldDigest, input)
	}
	if input.ExpectedRevision != session.Revision {
		return session, fmt.Errorf("session revision conflict")
	}
	if session.ExecutionOutcome == "passed" && input.AttemptID != "" {
		return session, fmt.Errorf("execution already passed; repair knowledge persistence without reopening prior attempts")
	}
	if session.Blocker != nil {
		return session, fmt.Errorf("resolve the external blocker before resuming individual attempts")
	}
	index := -1
	for i := range session.Attempts {
		if session.Attempts[i].ID == input.AttemptID {
			index = i
			break
		}
	}
	if index < 0 && (input.AttemptID != "" || input.WorkFence == 0) {
		return session, fmt.Errorf("unknown attempt")
	}
	if index >= 0 && session.Attempts[index].Status != "running" && session.Attempts[index].Status != "interrupted" && session.Attempts[index].Status != "failed" {
		return session, fmt.Errorf("only an interrupted or failed attempt needs recovery")
	}
	recovery, extra, err := doPrepareRecovery(root, session, input)
	if err != nil {
		return session, err
	}
	session, err = doAdoptRecoveredWorkFence(root, session, input.WorkFence, false)
	if err != nil {
		return session, err
	}
	if index >= 0 {
		attempt := &session.Attempts[index]
		attempt.Recovery = &recovery
		if attempt.Status == "running" {
			attempt.Status = "interrupted"
		}
		session.ExecutionOutcome = attempt.Status
	}
	doRememberResume(&session, requestDigest, recovery.EvidenceSHA256)
	session.Revision++
	session.UpdatedAt = doNow()
	return session, doWriteSession(root, session, oldDigest, extra)
}

func doFinish(root string, session DoSession, oldDigest string, input doFinishInput) (DoSession, error) {
	if input.Blocker != nil {
		return doBlockFinish(root, session, oldDigest, input)
	}
	if session.Blocker != nil {
		return session, fmt.Errorf("resolve the recorded external blocker before success closeout")
	}
	if input.KnowledgeStatus == "" {
		input.KnowledgeStatus = "pending"
	}
	if input.KnowledgeStatus != "saved" && input.Knowledge != nil {
		return session, fmt.Errorf("only saved knowledge may carry its verified receipt")
	}
	if session.ExecutionOutcome == "passed" && ((input.KnowledgeStatus == "pending") || (session.KnowledgeStatus == input.KnowledgeStatus && reflect.DeepEqual(session.Knowledge, input.Knowledge))) {
		validation := doValidate(root, session, true)
		if validation.Status != "passed" {
			return session, fmt.Errorf("previous completion is stale: %s", strings.Join(validation.Blockers, "; "))
		}
		if session.KnowledgeStatus != "pending" {
			if err := doReleaseFinishedWork(root, session); err != nil {
				return session, err
			}
		}
		return session, nil
	}
	if input.ExpectedRevision != session.Revision {
		return session, fmt.Errorf("session revision conflict")
	}
	validation := doValidate(root, session, true)
	if validation.Status != "passed" {
		return session, fmt.Errorf("validation incomplete: %s", strings.Join(validation.Blockers, "; "))
	}
	if err := doRequireWork(root, session); err != nil {
		return session, err
	}
	if input.KnowledgeStatus == "" {
		input.KnowledgeStatus = "pending"
	}
	if input.KnowledgeStatus != "pending" && input.KnowledgeStatus != "saved" && input.KnowledgeStatus != "not_applicable" {
		return session, fmt.Errorf("invalid knowledge_status")
	}
	if input.KnowledgeStatus == "saved" {
		if input.Knowledge == nil {
			return session, fmt.Errorf("knowledge receipt required")
		}
		if err := doVerifyKnowledge(root, session, *input.Knowledge); err != nil {
			return session, err
		}
	}
	if input.KnowledgeStatus == "not_applicable" && input.Knowledge != nil {
		return session, fmt.Errorf("not_applicable cannot carry a fabricated knowledge receipt")
	}
	session.ExecutionOutcome = "passed"
	session.KnowledgeStatus = input.KnowledgeStatus
	session.Knowledge = input.Knowledge
	session.Validation = &validation
	session.Revision++
	session.UpdatedAt = doNow()
	if err := doWriteSession(root, session, oldDigest, nil); err != nil {
		return session, err
	}
	if input.KnowledgeStatus != "pending" {
		if err := doReleaseFinishedWork(root, session); err != nil {
			return session, err
		}
	}
	return session, nil
}

func doReleaseFinishedWork(root string, session DoSession) error {
	store, err := runcontrol.OpenForRepository(context.Background(), root)
	if err != nil {
		return err
	}
	defer store.Close()
	work, _, err := store.GetWork(context.Background(), session.WorkID)
	if err != nil {
		return err
	}
	if work.Fence != session.WorkFence || work.TaskRef != "do:"+session.ID {
		return fmt.Errorf("completion work identity mismatch")
	}
	if work.Status == runcontrol.WorkCompleted {
		return nil
	}
	_, err = store.TransitionWork(context.Background(), runcontrol.TransitionWorkParams{WorkID: work.WorkID, ExpectedRevision: work.Revision, Fence: session.WorkFence, Target: runcontrol.WorkCompleted, Reason: "Do required operation checks and knowledge closeout completed"})
	return err
}

func doVerifyKnowledge(root string, session DoSession, receipt DoKnowledgeReceipt) error {
	if receipt.Path != path.Join(".specify/playbooks", receipt.MethodID, "usage", session.ID+".json") {
		return fmt.Errorf("knowledge receipt must be the canonical runtime-owned usage receipt")
	}
	p, err := doPath(root, receipt.Path, false)
	if err != nil {
		return err
	}
	raw, err := secureProjectReadFile(root, p)
	if err != nil {
		return err
	}
	if receipt.SHA256 != doBytesDigest(raw) {
		return fmt.Errorf("knowledge receipt digest mismatch")
	}
	var data map[string]json.RawMessage
	if err = json.Unmarshal(raw, &data); err != nil {
		return err
	}
	var sid, digest, method string
	var revision int
	_ = json.Unmarshal(data["session_id"], &sid)
	_ = json.Unmarshal(data["definition_digest"], &digest)
	_ = json.Unmarshal(data["method_id"], &method)
	_ = json.Unmarshal(data["revision"], &revision)
	if sid != session.ID || digest != doMethodDigest(session) || method != receipt.MethodID || revision != receipt.Revision {
		return fmt.Errorf("knowledge receipt is not bound to this execution and method revision")
	}
	document, err := loadPlaybookRevision(root, receipt.MethodID, receipt.Revision)
	if err != nil {
		return err
	}
	definitionDigest, err := playbookDefinitionDigest(document.Definition)
	if err != nil || document.Revision != receipt.Revision || definitionDigest != doMethodDigest(session) {
		return fmt.Errorf("knowledge receipt no longer binds the published definition")
	}
	var verification DoPlaybookValidationReceipt
	if err := json.Unmarshal(data["verification"], &verification); err != nil || session.Validation == nil || verification.SessionID != session.ID || verification.EvidenceDigest != session.Validation.EvidenceDigest || verification.SourceFingerprint != session.Validation.SourceFingerprint || verification.DefinitionDigest != doMethodDigest(session) || verification.Outcome != "passed" {
		return fmt.Errorf("knowledge verification does not match the finished operation")
	}
	if session.TemplateDefinition != nil && (verification.InstanceDigest != session.DefinitionDigest || !reflect.DeepEqual(verification.Parameters, session.Parameters)) {
		return fmt.Errorf("knowledge verification instance parameters mismatch")
	}
	return nil
}

func validateDoSessionForPlaybook(root, sessionID, methodID string, baseRevision int, baseDigest, definitionDigest string) (DoPlaybookValidationReceipt, error) {
	var result DoPlaybookValidationReceipt
	session, _, err := loadDoSession(root, sessionID)
	if err != nil {
		return result, err
	}
	if session.ExecutionOutcome != "passed" || session.Validation == nil {
		return result, fmt.Errorf("method publication requires execution-passed Do finish, not a supplied pass flag")
	}
	if err := doVerifyInstanceBinding(root, session); err != nil {
		return result, err
	}
	if doMethodDigest(session) != definitionDigest {
		return result, fmt.Errorf("session did not execute the exact proposed definition")
	}
	if session.MethodBinding == nil {
		if baseRevision != 0 || baseDigest != "" {
			return result, fmt.Errorf("new method session cannot update an existing revision")
		}
	} else if session.MethodBinding.ID != methodID || session.MethodBinding.Revision != baseRevision || session.MethodBinding.ContentDigest != baseDigest {
		return result, fmt.Errorf("session method base binding mismatch")
	}
	validation := doValidate(root, session, true)
	if validation.Status != "passed" {
		return result, fmt.Errorf("session evidence is no longer valid: %s", strings.Join(validation.Blockers, "; "))
	}
	if validation.EvidenceDigest != session.Validation.EvidenceDigest || validation.SourceFingerprint != session.Validation.SourceFingerprint {
		return result, fmt.Errorf("session verification receipt changed")
	}
	sources, err := playbookSourceFingerprint(root, doMethodDefinition(session))
	if err != nil {
		return result, err
	}
	result = DoPlaybookValidationReceipt{SessionID: sessionID, MethodID: methodID, BaseRevision: baseRevision, BaseDigest: baseDigest, DefinitionDigest: definitionDigest, SourceFingerprint: validation.SourceFingerprint, Sources: sources, EvidenceDigest: validation.EvidenceDigest, Outcome: "passed", VerifiedAt: validation.VerifiedAt}
	if session.TemplateDefinition != nil {
		result.InstanceDigest, result.Parameters = session.DefinitionDigest, session.Parameters
	}
	return result, nil
}

// Only typed runtime owners call these before their writes. Scope registration
// is exact audit metadata, never a generic authority to edit memory or methods.
func doRegisterPlaybookWrites(root, sessionID string, paths []string) error {
	return doRegisterOwnerMetadataWrites(root, sessionID, "playbook", paths)
}

func doRegisterLearningWrites(root, sessionID string, paths []string) error {
	return doRegisterOwnerMetadataWrites(root, sessionID, "learning", paths)
}

func doRegisterPlaybookProposalWrites(root, sessionID string, paths []string) error {
	return doRegisterOwnerMetadataWrites(root, sessionID, "playbook-proposal", paths)
}

func doRegisterOwnerMetadataWrites(root, sessionID, owner string, paths []string) error {
	release, err := doSessionLock(root, sessionID)
	if err != nil {
		return err
	}
	defer release()
	return doRegisterOwnerMetadataWritesLocked(root, sessionID, owner, paths)
}

// The specialized owner must already hold the Do session lock for its whole
// publication. This entrypoint keeps registration in that same critical section
// without recursively acquiring the lock or releasing Work before owner writes.
func doRegisterOwnerMetadataWritesLocked(root, sessionID, owner string, paths []string) error {
	session, digest, err := loadDoSession(root, sessionID)
	if err != nil {
		return err
	}
	if session.KnowledgeStatus != "pending" || (owner != "playbook-proposal" && owner != "cognition" && session.ExecutionOutcome != "passed") {
		return fmt.Errorf("owner metadata writes require a passed session awaiting knowledge capture")
	}
	if owner == "cognition" {
		if validation := doValidate(root, session, false); validation.Status != "passed" || len(validation.ChangedSourcePaths) == 0 {
			return fmt.Errorf("cognition metadata requires a verified source-writing operation")
		}
	}
	if owner == "playbook-proposal" {
		if _, err := doAdoptRecoveredWorkFence(root, session, 0, true); err != nil {
			return err
		}
	} else {
		if err := doRequireWork(root, session); err != nil {
			return err
		}
	}
	metadata := append([]string{}, session.MetadataWriteScope...)
	for _, p := range paths {
		clean, err := doPath(root, p, false)
		if err != nil {
			return err
		}
		if !doOwnerMetadataPath(owner, clean) {
			return fmt.Errorf("only exact %s-owner metadata files may be registered", owner)
		}
		if owner == "playbook-proposal" && strings.Split(clean, "/")[2] != playbookID(session.Definition) {
			return fmt.Errorf("proposal metadata must belong to this operation identity")
		}
		target, err := secureProjectPath(root, clean)
		if err != nil {
			return err
		}
		if info, err := os.Stat(target); err == nil && !info.Mode().IsRegular() {
			return fmt.Errorf("metadata registration requires exact regular files")
		} else if err != nil && !os.IsNotExist(err) {
			return err
		}
		metadata = append(metadata, clean)
	}
	metadata = uniqueSortedTrimmed(metadata)
	if doDigest(metadata) == doDigest(session.MetadataWriteScope) {
		return nil
	}
	store, err := runcontrol.OpenForRepository(context.Background(), root)
	if err != nil {
		return err
	}
	defer store.Close()
	work, intents, err := store.GetWork(context.Background(), session.WorkID)
	if err != nil {
		return err
	}
	specs := []runcontrol.WriteIntentSpec{}
	seen := map[string]bool{}
	for _, intent := range intents {
		if intent.Status == runcontrol.WriteIntentActive {
			specs = append(specs, runcontrol.WriteIntentSpec{Path: intent.Path, Operation: intent.Operation, Reason: intent.Reason, Confidence: runcontrol.IntentConfirmed})
			seen[intent.Path] = true
		}
	}
	for _, p := range metadata {
		if !seen[p] {
			specs = append(specs, runcontrol.WriteIntentSpec{Path: p, Operation: runcontrol.WriteModify, Reason: "runtime-owned " + owner + " publication", Confidence: runcontrol.IntentConfirmed})
		}
	}
	if _, _, err = store.ClaimWorkIntents(context.Background(), runcontrol.ClaimWorkIntentsParams{WorkID: work.WorkID, ExpectedRevision: work.Revision, Fence: session.WorkFence, Specs: specs}); err != nil {
		return err
	}
	session.MetadataWriteScope = metadata
	session.Revision++
	session.UpdatedAt = doNow()
	return doWriteSession(root, session, digest, nil)
}

func doOwnerMetadataPath(owner, p string) bool {
	if owner == "cognition" {
		switch p {
		case ".specify/project-cognition/status.json", ".specify/project-cognition/project-cognition.db", ".specify/project-cognition/project-cognition.db-wal", ".specify/project-cognition/project-cognition.db-shm", ".specify/project-cognition/project-cognition.db-journal", ".specify/project-cognition/.update.lock", ".specify/project-cognition/validate-build-receipt.json":
			return true
		}
		if path.Base(p) == mutationCognitionReceiptFileName {
			return true // exact replay scope computed from a validated existing intent
		}
		if path.Dir(p) == ".specify/project-cognition/closeout-intents" && strings.HasSuffix(p, ".json") && validCloseoutIntentID(strings.TrimSuffix(path.Base(p), ".json")) {
			return true
		}
		parts := strings.Split(p, "/")
		return len(parts) >= 5 && parts[0] == ".specify" && parts[1] == "project-cognition" && parts[2] == "delta-sessions" && strings.HasPrefix(parts[3], "delta-") && (parts[4] == "session.json" || (len(parts) == 6 && parts[4] == "events" && strings.HasSuffix(parts[5], ".json")))
	}
	if owner == "playbook-proposal" {
		parts := strings.Split(p, "/")
		return len(parts) == 5 && parts[0] == ".specify" && parts[1] == "playbooks" && playbookIDPattern.MatchString(parts[2]) && parts[3] == "proposals" && strings.HasSuffix(parts[4], ".json") && playbookDigestPattern.MatchString(strings.TrimSuffix(parts[4], ".json"))
	}
	if owner == "playbook" {
		return strings.HasPrefix(p, ".specify/playbooks/") && (path.Ext(p) == ".json" || path.Ext(p) == ".md")
	}
	if owner != "learning" {
		return false
	}
	switch p {
	case ".specify/memory/project-rules.md", ".specify/memory/learnings/INDEX.md", ".specify/memory/learnings/confirmed.md",
		".planning/learnings/.learning.lock", ".planning/learnings/candidates.md", ".planning/learnings/review.md",
		".planning/learnings/review-state.json", ".planning/learnings/metrics.json", ".planning/learnings/auto-capture.json":
		return true
	}
	return path.Dir(p) == ".specify/memory/learnings" && strings.HasPrefix(path.Base(p), "learn-") && path.Ext(p) == ".md"
}
