package main

import (
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"regexp"
	"strings"
)

var hookCommitMessagePattern = regexp.MustCompile(`(?i)^(feat|fix|docs|refactor|test|chore)(\([^)]+\))?:\s+\S`)

var hookExpectedWorkflowState = map[string]struct {
	activeCommand string
	phaseMode     string
}{
	"constitution":  {"sp-constitution", "planning-only"},
	"specify":       {"sp-specify", "planning-only"},
	"clarify":       {"sp-clarify", "planning-only"},
	"deep-research": {"sp-deep-research", "research-only"},
	"plan":          {"sp-plan", "design-only"},
	"tasks":         {"sp-tasks", "task-generation-only"},
	"review":        {"sp-review", "review-and-repair"},
	"accept":        {"sp-accept", "acceptance-only"},
	"analyze":       {"sp-analyze", "analysis-only"},
	"prd-scan":      {"sp-prd-scan", "analysis-only"},
	"prd-build":     {"sp-prd-build", "analysis-only"},
	"prd":           {"sp-prd", "analysis-only"},
}

var hookValidTrackerStatuses = map[string]bool{
	"gathering": true, "executing": true, "recovering": true, "replanning": true,
	"validating": true, "blocked": true, "resolved": true,
}

func runHook(args []string, stdout io.Writer) int {
	if len(args) == 0 {
		return writeEnvelope(stdout, NewEnvelope("usage-error", "missing hook subcommand"))
	}
	switch args[0] {
	case "validate-state":
		return writeEnvelope(stdout, validateHookState(args[1:]))
	case "validate-artifacts":
		return writeEnvelope(stdout, validateHookArtifacts(args[1:]))
	case "validate-commit":
		return writeEnvelope(stdout, validateHookCommit(args[1:]))
	default:
		return writeEnvelope(stdout, NewEnvelope("usage-error", fmt.Sprintf("unknown hook subcommand %q", args[0])))
	}
}

func validateHookState(args []string) Envelope {
	command := strings.ToLower(strings.TrimSpace(optionValue(args, "--command", "")))
	if command == "" {
		return NewEnvelope("usage-error", "--command is required")
	}
	featureDir := strings.TrimSpace(optionValue(args, "--feature-dir", ""))
	if featureDir == "" {
		return NewEnvelope("usage-error", "--feature-dir is required")
	}
	target, displayFeature, err := hookFeaturePath(optionValue(args, "--project-root", "."), featureDir)
	if err != nil {
		return hookBlocked(command, featureDir, err)
	}
	info, err := os.Stat(target)
	if err != nil || !info.IsDir() {
		return hookBlocked(command, featureDir, fmt.Errorf("feature directory does not exist"))
	}
	statePath := filepath.Join(target, "workflow-state.md")
	stateInfo, err := os.Stat(statePath)
	if err != nil {
		env := hookBlocked(command, displayFeature, fmt.Errorf("workflow-state.md is missing"))
		env.Data["autofix"] = hookAutofixMetadata(displayFeature, command)
		return env
	}
	if !stateInfo.Mode().IsRegular() {
		return hookBlocked(command, displayFeature, fmt.Errorf("workflow-state.md must be a regular file"))
	}
	content, err := os.ReadFile(statePath)
	if err != nil {
		return hookBlocked(command, displayFeature, err)
	}
	checkpoint := hookWorkflowCheckpoint(string(content))
	errors := hookStateErrors(command, checkpoint)
	if len(errors) > 0 {
		if hasFlag(args, "--autofix") {
			snippet := hookAutofixSnippet(command)
			if strings.TrimSpace(snippet) == "" {
				return hookBlocked(command, displayFeature, fmt.Errorf(strings.Join(errors, "; ")))
			}
			updated := strings.TrimRight(string(content), " \t\r\n")
			if !strings.Contains(updated, strings.TrimSpace(snippet)) {
				updated += "\n\n" + snippet
			}
			if err := atomicWriteFile(statePath, []byte(strings.TrimRight(updated, " \t\r\n")+"\n"), 0o644); err != nil {
				return hookBlocked(command, displayFeature, err)
			}
			repaired := NewEnvelope("repaired", "workflow state contract sections were appended")
			repaired.Data["command"] = command
			repaired.Data["feature_dir"] = displayFeature
			repaired.Data["validated_path"] = filepath.ToSlash(statePath)
			repaired.Data["checkpoint"] = hookWorkflowCheckpoint(updated)
			repaired.Data["autofix"] = hookAutofixMetadata(displayFeature, command)
			repaired.Data["writes"] = map[string]any{"workflow_state": filepath.ToSlash(statePath)}
			return repaired
		}
		env := hookBlocked(command, displayFeature, fmt.Errorf(strings.Join(errors, "; ")))
		env.Data["checkpoint"] = checkpoint
		env.Data["validated_path"] = filepath.ToSlash(statePath)
		env.Data["autofix"] = hookAutofixMetadata(displayFeature, command)
		return env
	}
	env := NewEnvelope("ok", "workflow state is available")
	env.Data["command"] = command
	env.Data["feature_dir"] = displayFeature
	env.Data["validated_path"] = filepath.ToSlash(statePath)
	env.Data["checkpoint"] = checkpoint
	env.Data["autofix_requested"] = hasFlag(args, "--autofix")
	return env
}

func validateHookArtifacts(args []string) Envelope {
	command := strings.ToLower(strings.TrimSpace(optionValue(args, "--command", "")))
	featureDir := strings.TrimSpace(optionValue(args, "--feature-dir", ""))
	if command == "" || featureDir == "" {
		return NewEnvelope("usage-error", "--command and --feature-dir are required")
	}
	root, displayFeature, err := hookFeaturePath(optionValue(args, "--project-root", "."), featureDir)
	if err != nil {
		return hookBlocked(command, featureDir, err)
	}
	required, supported := hookRequiredArtifacts(command)
	if !supported {
		return NewEnvelope("usage-error", fmt.Sprintf("unsupported hook command %q", command))
	}
	if command == "implement" {
		if workflow := NewWorkflowService(optionValue(args, "--project-root", ".")).Show(WorkflowShowRequest{FeatureDir: displayFeature}); workflow.Status == "ok" {
			required = append(append([]hookRequiredArtifact{}, required...), hookRequiredArtifact{path: "implementation-handoff.json", kind: "file"})
		}
	}
	missing := []string{}
	typeErrors := []string{}
	checked := []string{}
	for _, artifact := range required {
		path := filepath.Join(root, filepath.FromSlash(artifact.path))
		info, statErr := os.Stat(path)
		checked = append(checked, artifact.path)
		if statErr != nil {
			missing = append(missing, filepath.ToSlash(filepath.Join(displayFeature, artifact.path)))
			continue
		}
		switch artifact.kind {
		case "dir":
			if !info.IsDir() {
				typeErrors = append(typeErrors, "required artifact must be a directory: "+artifact.path)
			}
		default:
			if !info.Mode().IsRegular() {
				typeErrors = append(typeErrors, "required artifact must be a file: "+artifact.path)
				continue
			}
			if info.Size() == 0 {
				typeErrors = append(typeErrors, "required artifact must be non-empty: "+artifact.path)
			}
			if strings.HasSuffix(artifact.path, ".json") {
				if err := hookValidateJSONObject(path, artifact.path); err != nil {
					typeErrors = append(typeErrors, err.Error())
				}
			}
		}
	}
	if len(missing) > 0 || len(typeErrors) > 0 {
		env := hookBlocked(command, displayFeature, fmt.Errorf("required workflow artifacts are missing or invalid"))
		env.Data["missing"] = missing
		env.Data["errors"] = typeErrors
		return env
	}
	env := NewEnvelope("ok", "required workflow artifacts are present")
	env.Data["command"] = command
	env.Data["feature_dir"] = displayFeature
	env.Data["checked"] = checked
	return env
}

func validateHookCommit(args []string) Envelope {
	message := strings.TrimSpace(optionValue(args, "--commit-message", ""))
	if message == "" {
		return NewEnvelope("usage-error", "--commit-message is required")
	}
	intent := strings.TrimSpace(optionValue(args, "--commit-intent", "finalize"))
	if intent != "finalize" && intent != "external-evidence-checkpoint" {
		return NewEnvelope("usage-error", "--commit-intent must be finalize or external-evidence-checkpoint")
	}
	if !hookCommitMessagePattern.MatchString(message) {
		env := hookBlocked("commit", "", fmt.Errorf("commit message must follow conventional commit format"))
		env.Data["commit_intent"] = intent
		return env
	}
	featureDir := strings.TrimSpace(optionValue(args, "--feature-dir", ""))
	checkpointTasks := []string{}
	if featureDir != "" {
		featurePath, displayFeature, err := hookFeaturePath(optionValue(args, "--project-root", "."), featureDir)
		if err != nil {
			return hookBlocked("commit", featureDir, err)
		}
		featureDir = displayFeature
		if tracker, ok := hookReadImplementTracker(filepath.Join(featurePath, "implement-tracker.md")); ok {
			status := strings.ToLower(strings.TrimSpace(tracker["status"]))
			if !hookValidTrackerStatuses[status] {
				return hookBlocked("commit", featureDir, fmt.Errorf("implement-tracker status must be one of: blocked, executing, gathering, recovering, replanning, resolved, validating"))
			}
			if intent == "finalize" && status != "resolved" {
				return hookBlocked("commit", featureDir, fmt.Errorf("implement-tracker is still %s; commit should not finalize this workflow yet", status))
			}
			if intent == "external-evidence-checkpoint" {
				if status == "resolved" {
					return hookBlocked("commit", featureDir, fmt.Errorf("external-evidence-checkpoint requires a nonterminal implement-tracker"))
				}
				checkpointTasks = hookMandatoryExternalEvidenceTasks(featurePath)
				if len(checkpointTasks) == 0 {
					return hookBlocked("commit", featureDir, fmt.Errorf("external-evidence-checkpoint requires a task-local mandatory external or human verification blocker"))
				}
			}
		} else if intent == "external-evidence-checkpoint" {
			return hookBlocked("commit", featureDir, fmt.Errorf("external-evidence-checkpoint requires a nonterminal implement-tracker"))
		}
	} else if intent == "external-evidence-checkpoint" {
		return hookBlocked("commit", "", fmt.Errorf("external-evidence-checkpoint requires feature_dir and a task-local mandatory external blocker"))
	}
	env := NewEnvelope("ok", "commit boundary is valid")
	env.Data["commit_message"] = message
	env.Data["commit_intent"] = intent
	env.Data["workflow_finalized"] = intent == "finalize"
	env.Data["checkpoint_task_ids"] = checkpointTasks
	env.Data["feature_dir"] = filepath.ToSlash(featureDir)
	return env
}

func hookFeaturePath(projectRoot, featureDir string) (string, string, error) {
	root, err := filepath.Abs(projectRoot)
	if err != nil {
		return "", "", err
	}
	root, err = filepath.EvalSymlinks(root)
	if err != nil {
		return "", "", err
	}
	var target string
	if filepath.IsAbs(featureDir) || filepath.VolumeName(featureDir) != "" {
		target, err = filepath.Abs(featureDir)
		if err != nil {
			return "", "", err
		}
	} else {
		target = filepath.Join(root, filepath.FromSlash(featureDir))
	}
	target = filepath.Clean(target)
	rel, err := filepath.Rel(root, target)
	if err != nil || rel == "." || rel == ".." || strings.HasPrefix(rel, ".."+string(filepath.Separator)) {
		return "", "", fmt.Errorf("feature directory must stay inside the project")
	}
	display := filepath.ToSlash(rel)
	secure, err := secureProjectPath(root, display)
	if err != nil {
		return "", "", err
	}
	if !sameFilesystemPath(secure, target) {
		return "", "", fmt.Errorf("feature directory must resolve to the canonical project path")
	}
	return secure, display, nil
}

type hookRequiredArtifact struct {
	path string
	kind string
}

func hookRequiredArtifacts(command string) ([]hookRequiredArtifact, bool) {
	files := map[string][]string{
		"constitution":  {"workflow-state.md"},
		"specify":       {"spec-contract.json", "spec.md", "workflow-state.md"},
		"clarify":       {"spec.md", "alignment.md", "context.md", "references.md", "workflow-state.md", "clarification/evidence-index.json", "clarification/checkpoints.ndjson"},
		"deep-research": {"deep-research.md", "workflow-state.md"},
		"plan":          {"plan.md", "workflow-state.md"},
		"tasks":         {"tasks.md", "workflow-state.md"},
		"analyze":       {"workflow-state.md"},
		"implement":     {"implement-tracker.md"},
		"review":        {"review-state.json", "implementation-summary.md", "human-acceptance.json", "workflow-state.md"},
		"accept":        {"implementation-summary.md", "human-acceptance.json", "workflow-state.md"},
		"map-scan":      {"status.json", "coverage.json", "provisional/nodes.json", "provisional/edges.json", "provisional/observations.json"},
		"map-build":     {"status.json", "project-cognition.db"},
		"map-update":    {"status.json", "project-cognition.db"},
		"prd-scan":      {"workflow-state.md", "prd-scan.md", "coverage-ledger.md", "coverage-ledger.json", "capability-ledger.json", "artifact-contracts.json", "reconstruction-checklist.json"},
		"prd-build":     {"workflow-state.md", "prd-scan.md", "coverage-ledger.json", "capability-ledger.json", "artifact-contracts.json", "reconstruction-checklist.json", "master/master-pack.md", "exports/README.md", "exports/prd.md"},
		"prd":           {"workflow-state.md", "prd-scan.md", "coverage-ledger.md", "coverage-ledger.json", "capability-ledger.json", "artifact-contracts.json", "reconstruction-checklist.json"},
	}
	dirs := map[string][]string{
		"clarify":   {"clarification/handoffs"},
		"review":    {"review-evidence"},
		"map-scan":  {"evidence"},
		"prd-scan":  {"scan-packets", "evidence", "worker-results"},
		"prd-build": {"scan-packets", "evidence", "worker-results"},
		"prd":       {"scan-packets", "evidence", "worker-results"},
	}
	fileList, ok := files[command]
	if !ok {
		return nil, false
	}
	required := []hookRequiredArtifact{}
	for _, path := range fileList {
		required = append(required, hookRequiredArtifact{path: path, kind: "file"})
	}
	for _, path := range dirs[command] {
		required = append(required, hookRequiredArtifact{path: path, kind: "dir"})
	}
	return required, true
}

func hookStateErrors(command string, checkpoint map[string]any) []string {
	expected, supported := hookExpectedWorkflowState[command]
	if !supported {
		return []string{fmt.Sprintf("unsupported command_name %q for workflow.state.validate", command)}
	}
	errors := []string{}
	if stringHookField(checkpoint, "active_command") != expected.activeCommand {
		errors = append(errors, fmt.Sprintf("active_command mismatch: expected %s, got %s", expected.activeCommand, valueOrMissing(stringHookField(checkpoint, "active_command"))))
	}
	if command == "specify" && hookUsesFixedLifecycle(checkpoint) {
		for _, field := range []string{"current_stage", "current_domain", "next_action", "blocker_reason", "final_handoff_decision"} {
			if stringHookField(checkpoint, field) == "" {
				errors = append(errors, "workflow-state is missing Fixed Lifecycle State field: "+field)
			}
		}
	} else if stringHookField(checkpoint, "phase_mode") != expected.phaseMode {
		errors = append(errors, fmt.Sprintf("phase_mode mismatch: expected %s, got %s", expected.phaseMode, valueOrMissing(stringHookField(checkpoint, "phase_mode"))))
	}
	for _, field := range []string{"allowed_artifact_writes", "forbidden_actions", "authoritative_files"} {
		if list, _ := checkpoint[field].([]any); len(list) == 0 {
			errors = append(errors, "workflow-state is missing "+field)
		}
	}
	if stringHookField(checkpoint, "next_command") == "" {
		errors = append(errors, "workflow-state is missing next_command")
	}
	return errors
}

func hookWorkflowCheckpoint(content string) map[string]any {
	checkpoint := map[string]any{
		"active_command":          "",
		"phase_mode":              "",
		"status":                  "",
		"current_stage":           "",
		"current_domain":          "",
		"next_action":             "",
		"blocker_reason":          "",
		"final_handoff_decision":  "",
		"allowed_artifact_writes": []any{},
		"forbidden_actions":       []any{},
		"authoritative_files":     []any{},
		"next_command":            "",
	}
	hookParseFrontmatter(content, checkpoint)
	section := ""
	for _, raw := range strings.Split(content, "\n") {
		line := strings.TrimSpace(raw)
		if strings.HasPrefix(line, "## ") {
			section = strings.TrimSpace(strings.TrimPrefix(line, "## "))
			continue
		}
		if strings.HasPrefix(line, "- ") {
			item := strings.TrimSpace(strings.TrimPrefix(line, "- "))
			if strings.Contains(item, ":") {
				parts := strings.SplitN(item, ":", 2)
				key := strings.TrimSpace(parts[0])
				value := hookCleanScalar(parts[1])
				if key != "" {
					checkpoint[key] = value
				}
				continue
			}
			value := hookCleanScalar(item)
			switch strings.ToLower(section) {
			case "allowed artifact writes":
				checkpoint["allowed_artifact_writes"] = append(checkpoint["allowed_artifact_writes"].([]any), value)
			case "forbidden actions":
				checkpoint["forbidden_actions"] = append(checkpoint["forbidden_actions"].([]any), value)
			case "authoritative files":
				checkpoint["authoritative_files"] = append(checkpoint["authoritative_files"].([]any), value)
			case "next command":
				if checkpoint["next_command"] == "" {
					checkpoint["next_command"] = value
				}
			}
		}
	}
	return checkpoint
}

func hookParseFrontmatter(content string, checkpoint map[string]any) {
	lines := strings.Split(content, "\n")
	if len(lines) == 0 || strings.TrimSpace(lines[0]) != "---" {
		return
	}
	key := ""
	for i := 1; i < len(lines); i++ {
		line := strings.TrimRight(lines[i], "\r")
		if strings.TrimSpace(line) == "---" {
			return
		}
		if strings.HasPrefix(line, "  - ") && key != "" {
			switch key {
			case "allowed_artifact_writes", "forbidden_actions", "authoritative_files":
				checkpoint[key] = append(checkpoint[key].([]any), hookCleanScalar(strings.TrimPrefix(strings.TrimSpace(line), "- ")))
			}
			continue
		}
		if strings.Contains(line, ":") {
			parts := strings.SplitN(line, ":", 2)
			key = strings.TrimSpace(parts[0])
			value := hookCleanScalar(parts[1])
			switch key {
			case "active_command", "status", "phase_mode", "summary", "current_stage", "current_domain", "next_action", "blocker_reason", "final_handoff_decision", "next_command":
				checkpoint[key] = value
			case "allowed_artifact_writes", "forbidden_actions", "authoritative_files":
				checkpoint[key] = []any{}
			}
		}
	}
}

func hookAutofixSnippet(command string) string {
	switch command {
	case "specify":
		return hookAutofixSections([]string{"spec.md", "alignment.md", "context.md", "references.md", "specify-draft.md", "workflow-state.md", "checklists/requirements.md"}, []string{"edit source code", "edit tests", "fix build/tooling", "implement behavior", "run implementation-oriented fix loops"}, []string{"spec.md", "alignment.md", "context.md", "references.md", "specify-draft.md"}, "/sp.plan")
	case "plan", "deep-research":
		return hookAutofixSections([]string{"plan.md", "research.md", "data-model.md", "contracts/", "quickstart.md", "plan-contract.json", "workflow-state.md"}, []string{"edit source code", "edit tests", "implement behavior"}, []string{"spec-contract.json", "plan-contract.json"}, "/sp.tasks")
	case "tasks":
		return hookAutofixSections([]string{"tasks.md", "handoff-to-tasks.json", "task-index.json", "workflow-state.md"}, []string{"edit source code", "edit tests", "implement behavior"}, []string{"plan-contract.json", "task-index.json"}, "/sp.implement")
	case "review":
		return hookAutofixSections([]string{"review-state.json", "review-results/", "review-evidence/", "implementation-summary.md", "human-acceptance.json", "workflow-state.md"}, []string{"change approved product scope", "reuse stale review evidence", "push, deploy, or perform external writes without authority"}, []string{"implementation-handoff.json", "review-state.json", "review-evidence/"}, "/sp.accept")
	case "accept":
		return hookAutofixSections([]string{"human-acceptance.json", "workflow-state.md"}, []string{"edit production source code", "edit tests", "commit, push, deploy, or perform external writes", "silently run a repair workflow"}, []string{"implementation-summary.md", "human-acceptance.json", "workflow-state.md"}, "/sp.accept")
	default:
		return hookAutofixSections([]string{"workflow-state.md"}, []string{"edit source code"}, []string{"workflow-state.md"}, "/sp."+command)
	}
}

func hookAutofixSections(allowed, forbidden, authoritative []string, nextCommand string) string {
	return "## Allowed Artifact Writes\n\n" + hookMarkdownList(allowed) + "\n\n" +
		"## Forbidden Actions\n\n" + hookMarkdownList(forbidden) + "\n\n" +
		"## Authoritative Files\n\n" + hookMarkdownList(authoritative) + "\n\n" +
		"## Next Command\n\n- `" + nextCommand + "`\n"
}

func hookMarkdownList(items []string) string {
	lines := []string{}
	for _, item := range items {
		lines = append(lines, "- "+item)
	}
	return strings.Join(lines, "\n")
}

func hookAutofixMetadata(featureDir, command string) map[string]any {
	return map[string]any{
		"available": true,
		"command":   fmt.Sprintf("specify-runtime hook validate-state --command %s --feature-dir %q --autofix --format json", command, featureDir),
		"snippet":   hookAutofixSnippet(command),
	}
}

func hookValidateJSONObject(path, label string) error {
	raw, err := os.ReadFile(path)
	if err != nil {
		return fmt.Errorf("required JSON artifact is unreadable: %s", label)
	}
	var payload map[string]any
	if err := json.Unmarshal(raw, &payload); err != nil {
		return fmt.Errorf("required JSON artifact is malformed: %s", label)
	}
	if payload == nil {
		return fmt.Errorf("required JSON artifact must be an object: %s", label)
	}
	return nil
}

func hookReadImplementTracker(path string) (map[string]string, bool) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, false
	}
	checkpoint := hookWorkflowCheckpoint(string(raw))
	result := map[string]string{}
	for _, key := range []string{"status", "next_action"} {
		result[key] = stringHookField(checkpoint, key)
	}
	return result, true
}

func hookMandatoryExternalEvidenceTasks(featurePath string) []string {
	taskDir := filepath.Join(featurePath, "implementation-review", "tasks")
	entries, err := os.ReadDir(taskDir)
	if err != nil {
		return nil
	}
	taskIDs := []string{}
	for _, entry := range entries {
		if entry.IsDir() || !strings.HasSuffix(entry.Name(), ".json") {
			continue
		}
		raw, err := os.ReadFile(filepath.Join(taskDir, entry.Name()))
		if err != nil {
			continue
		}
		var payload map[string]any
		if err := json.Unmarshal(raw, &payload); err != nil || payload == nil {
			continue
		}
		if strings.ToLower(hookAnyStringField(payload, "status")) != "blocked" {
			continue
		}
		taskID := strings.ToUpper(strings.TrimSpace(hookAnyStringField(payload, "task_id")))
		if taskID == "" {
			taskID = strings.ToUpper(strings.TrimSuffix(entry.Name(), filepath.Ext(entry.Name())))
		}
		blockers, _ := payload["blockers"].([]any)
		for _, item := range blockers {
			blocker, _ := item.(map[string]any)
			if hookValidMandatoryExternalBlocker(blocker) {
				taskIDs = append(taskIDs, taskID)
				break
			}
		}
	}
	return taskIDs
}

func hookValidMandatoryExternalBlocker(blocker map[string]any) bool {
	if blocker == nil {
		return false
	}
	classification := hookAnyStringField(blocker, "classification")
	if classification != "external" && classification != "human-action" && classification != "verification_policy" {
		return false
	}
	owner := hookAnyStringField(blocker, "owner")
	if owner != "user" && owner != "maintainer" && owner != "external-system" {
		return false
	}
	if hookAnyStringField(blocker, "completion_impact") != "mandatory_for_completion" {
		return false
	}
	if hookAnyStringField(blocker, "exact_next_action") == "" || hookAnyStringField(blocker, "unblock_criteria") == "" {
		return false
	}
	if _, ok := blocker["implementation_can_continue"].(bool); !ok {
		return false
	}
	if (owner == "user" || owner == "maintainer") && hookAnyStringField(blocker, "approval_question") == "" {
		return false
	}
	switch evidence := blocker["evidence"].(type) {
	case string:
		return strings.TrimSpace(evidence) != ""
	case []any:
		if len(evidence) == 0 {
			return false
		}
		for _, item := range evidence {
			if text, ok := item.(string); !ok || strings.TrimSpace(text) == "" {
				return false
			}
		}
		return true
	default:
		return false
	}
}

func hookUsesFixedLifecycle(checkpoint map[string]any) bool {
	for _, field := range []string{"current_stage", "current_domain", "blocker_reason", "final_handoff_decision"} {
		if stringHookField(checkpoint, field) != "" {
			return true
		}
	}
	return false
}

func stringHookField(payload map[string]any, key string) string {
	value, _ := payload[key].(string)
	return strings.TrimSpace(value)
}

func hookAnyStringField(payload map[string]any, key string) string {
	if payload == nil {
		return ""
	}
	value, _ := payload[key].(string)
	return strings.TrimSpace(value)
}

func hookCleanScalar(value string) string {
	value = strings.TrimSpace(value)
	value = strings.Trim(value, "`")
	value = strings.Trim(value, `"'`)
	return strings.TrimSpace(value)
}

func valueOrMissing(value string) string {
	if strings.TrimSpace(value) == "" {
		return "missing"
	}
	return value
}

func hookBlocked(command, featureDir string, err error) Envelope {
	env := NewEnvelope("blocked", "workflow hook validation is blocked")
	env.Data["command"] = command
	env.Data["feature_dir"] = filepath.ToSlash(featureDir)
	env.Blockers = append(env.Blockers, map[string]any{
		"code":              "workflow-hook-invalid",
		"owner":             "agent",
		"cause":             err.Error(),
		"exact_next_action": "Repair the named workflow state or artifact, then rerun this runtime hook.",
	})
	return env
}
