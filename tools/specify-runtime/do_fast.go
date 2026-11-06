package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"reflect"
	"runtime"
	"strings"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runcontrol"
)

type doCompleteInput struct {
	ExpectedRevision int    `json:"expected_revision"`
	ChangeSummary    string `json:"change_summary"`
}

// Preparing never starts Work or takes a write lock. The returned template is
// still checked by start against the live method, sources, scopes, and owner.
func doPrepare(root string, input doStartInput) (map[string]any, error) {
	var err error
	input, err = doExpandCommand(root, input)
	if err != nil {
		return nil, err
	}
	input.AgentID, input.AdapterID = strings.TrimSpace(input.AgentID), strings.TrimSpace(input.AdapterID)
	if input.AgentID == "" || input.AdapterID == "" {
		return nil, fmt.Errorf("agent_id and adapter_id are required")
	}
	if input.SessionID != "" && !doIDPattern.MatchString(input.SessionID) {
		return nil, fmt.Errorf("invalid session id")
	}
	contextRaw, err := json.Marshal(input.Context)
	if err != nil {
		return nil, err
	}
	input.Context, err = playbookReadContext(string(contextRaw))
	if err != nil {
		return nil, err
	}
	input.Context["os"], input.Context["arch"] = runtime.GOOS, runtime.GOARCH
	if input.MethodBinding != nil {
		document, err := loadPlaybookDocument(root, input.MethodBinding.ID)
		if err != nil {
			return nil, err
		}
		if document.Revision != input.MethodBinding.Revision || document.ContentDigest != input.MethodBinding.ContentDigest {
			return nil, fmt.Errorf("method binding is stale or mismatched")
		}
		binding := *input.MethodBinding
		input.MethodBinding = &binding
		if input.Definition.Goal == "" {
			input.Definition = document.Definition
		}
	}
	input.Definition.SourceFiles = append(append([]string{}, input.Definition.SourceFiles...), input.SourceFiles...)
	input.SourceFiles = nil // Already in the canonical template; start must not append twice.
	if err := doPrepareDefinitionIssues(root, input.Definition); err != nil {
		return nil, err
	}
	if err := validatePlaybookDefinition(root, input.Definition); err != nil {
		return nil, err
	}
	input.Definition = playbookNormalizeDefinition(input.Definition)
	resolved, parameters, err := resolvePlaybookDefinition(root, input.Definition, input.Parameters)
	if err != nil {
		return nil, err
	}
	input.Parameters = parameters
	if input.MethodBinding != nil && input.MethodBinding.ID != playbookID(resolved) {
		return nil, fmt.Errorf("method binding belongs to a different operation identity")
	}
	if gaps := playbookCompatibility(resolved, input.Context); len(gaps) > 0 {
		return nil, fmt.Errorf("incompatible method: %s", strings.Join(gaps, "; "))
	}
	if strings.TrimSpace(input.Goal) == "" {
		input.Goal = resolved.Goal
	}
	if input.Goal != resolved.Goal {
		return nil, fmt.Errorf("goal must equal the frozen definition goal")
	}
	input.WriteScope, input.OutputScope = append([]string{}, input.WriteScope...), append([]string{}, input.OutputScope...)
	for _, scope := range [][]string{input.WriteScope, input.OutputScope} {
		for index, relative := range scope {
			clean, err := doPath(root, relative, false)
			if err != nil {
				return nil, err
			}
			if doWorkflowStatePath(clean) {
				return nil, fmt.Errorf("runtime/workflow state is not product or output scope")
			}
			scope[index] = clean
		}
	}
	input.WriteScope, input.OutputScope = uniqueSortedTrimmed(input.WriteScope), uniqueSortedTrimmed(input.OutputScope)
	if err := doValidateOperationScopes(resolved, input.WriteScope, input.OutputScope); err != nil {
		return nil, err
	}
	_, fingerprint, _, _, err := doCaptureSource(root, resolved, input.WriteScope)
	if err != nil {
		return nil, err
	}
	definitionDigest, err := playbookDefinitionDigest(resolved)
	if err != nil {
		return nil, err
	}
	methodDigest, err := playbookDefinitionDigest(input.Definition)
	if err != nil {
		return nil, err
	}
	if input.SessionID != "" {
		if _, err := secureProjectReadFile(root, doSessionRef(input.SessionID)); err == nil {
			existing, _, err := loadDoSession(root, input.SessionID)
			if err != nil {
				return nil, err
			}
			if existing.DefinitionDigest != definitionDigest || doMethodDigest(existing) != methodDigest || existing.Goal != input.Goal || !reflect.DeepEqual(existing.MethodBinding, input.MethodBinding) || !reflect.DeepEqual(existing.Parameters, parameters) || !reflect.DeepEqual(existing.Context, input.Context) || !reflect.DeepEqual(uniqueSortedTrimmed(existing.WriteScope), input.WriteScope) || !reflect.DeepEqual(uniqueSortedTrimmed(existing.OutputScope), input.OutputScope) {
				return nil, fmt.Errorf("session_id already binds a different operation; resume it or choose a new id")
			}
			if err := doReadWorkOwner(root, existing, input.AgentID, input.AdapterID, false); err != nil {
				return nil, err
			}
		} else if !os.IsNotExist(err) {
			return nil, err
		}
	}
	data := map[string]any{"start_input": input, "definition_digest": definitionDigest, "method_digest": methodDigest, "source_fingerprint": fingerprint, "start_argv": []string{"specify-runtime", "do", "start", "--input-json", "-", "--format", "json"}}
	if len(resolved.ExternalInputs) > 0 {
		data["protected_inputs"] = map[string]any{"bindings": resolved.ExternalInputs, "ready": true, "persistence": "binding names, environment names and digests only; no resolved paths or contents", "execution": "use do next protected_execution with the bundled protected process helper; child output is discarded"}
	}
	return data, nil
}

func doReadWorkOwner(root string, session DoSession, agentID, adapterID string, requireActive bool) error {
	view, err := runcontrol.OpenViewForRepository(context.Background(), root)
	if err != nil {
		return err
	}
	defer view.Close()
	work, _, err := view.GetWork(context.Background(), session.WorkID)
	if err != nil {
		return err
	}
	if work.TaskRef != "do:"+session.ID || work.Fence != session.WorkFence || (agentID != "" && work.AgentID != agentID) || (adapterID != "" && work.AdapterID != adapterID) || (requireActive && work.Status != runcontrol.WorkActive) {
		return fmt.Errorf("Work owner or fence changed; use explicit Work recovery")
	}
	return nil
}

// The skeleton supplies only known protocol facts. Execution status, tool-call
// identity, timestamps, return values and outputs must come from the real tool.
func doCompletionSkeleton(action doAction, attemptID string) (doRecordEvent, []string) {
	event := doRecordEvent{AttemptID: attemptID, TargetID: action.id, Kind: action.kind, Event: "completed", EvidenceOrigin: "agent_tool_observation"}
	required := []string{"status", "tool_call_id", "started_at", "finished_at"}
	if action.nativeAction != nil {
		event.NativeAction = normalizePlaybookNativeAction(action.nativeAction)
		required = append(required, "native_observation")
	} else {
		event.Argv, event.Cwd = append([]string{}, action.argv...), action.cwd
		if len(action.argv) > 0 {
			required = append(required, "exit_code")
		}
	}
	if action.check != nil && action.check.Kind != "exit_code" && action.check.Kind != "observation" {
		required = append(required, "result_refs")
	}
	return event, required
}

func doRetryRecoveryReady(root string, attempt DoAttempt) error {
	if attempt.Status != "failed" && attempt.Status != "interrupted" {
		return nil
	}
	if attempt.Recovery == nil {
		return fmt.Errorf("inspect actual effects and record recovery before retry")
	}
	if err := doRecoveryMatchesAttempt(attempt, *attempt.Recovery); err != nil {
		return err
	}
	if err := doVerifyRecoveryEvidence(root, *attempt.Recovery); err != nil {
		return fmt.Errorf("retry recovery evidence is no longer valid: %w", err)
	}
	return nil
}

func doNext(root string, session DoSession) (map[string]any, error) {
	// Reject detached or edited caller objects; readiness is for one persisted
	// checkpoint and does not silently jump to a newer revision.
	current, _, err := loadDoSession(root, session.ID)
	if err != nil {
		return nil, err
	}
	if doDigest(current) != doDigest(session) {
		return nil, fmt.Errorf("session checkpoint changed; reload before requesting next actions")
	}
	if session.Context["os"] != runtime.GOOS || session.Context["arch"] != runtime.GOARCH {
		return nil, fmt.Errorf("the current runtime platform differs from the frozen operation context")
	}
	terminal := session.ExecutionOutcome == "passed" && (session.KnowledgeStatus == "saved" || session.KnowledgeStatus == "not_applicable")
	if err := doReadWorkOwner(root, session, "", "", !terminal); err != nil {
		return nil, err
	}
	data := map[string]any{"session_id": session.ID, "revision": session.Revision, "definition_digest": session.DefinitionDigest, "definition_epoch": doCurrentDefinitionEpoch(session), "terminal": terminal, "ready": []map[string]any{}, "running": []map[string]any{}, "blocked": []map[string]any{}, "complete_ready": false}
	if terminal {
		if validation := doValidate(root, session, true); validation.Status != "passed" {
			return nil, fmt.Errorf("previous completion is stale: %s", strings.Join(validation.Blockers, "; "))
		}
		return data, nil
	}
	if session.Blocker != nil {
		data["blocked"] = []map[string]any{{"cause": session.Blocker.Cause, "resume_argv": []string{"specify-runtime", "do", "resume", session.ID, "--format", "json"}}}
		return data, nil
	}
	_, fingerprint, _, _, err := doCaptureSource(root, session.Definition, session.WriteScope)
	if err != nil {
		return nil, err
	}
	latest := doLatestAttempts(session)
	ready, running, blocked := []map[string]any{}, []map[string]any{}, []map[string]any{}
	roots := []string{}
	for _, step := range session.Definition.Steps {
		if step.Required {
			roots = append(roots, step.ID)
		}
	}
	for _, check := range session.Definition.Checks {
		if check.Required {
			roots = append(roots, check.ID)
		}
	}
	requiredClosure := doDependencyClosure(doDefinitionDependencies(session.Definition), roots)
	ids := []string{}
	for _, step := range session.Definition.Steps {
		ids = append(ids, step.ID)
	}
	for _, check := range session.Definition.Checks {
		ids = append(ids, check.ID)
	}
	for _, id := range ids {
		kind := "step"
		if _, ok := doActionDefinition(session.Definition, id).(PlaybookCheck); ok {
			kind = "check"
		}
		action, _ := doFindAction(session, kind, id)
		previous, exists := latest[id]
		if exists && previous.Status == "running" {
			event, facts := doCompletionSkeleton(action, previous.ID)
			entry := map[string]any{"target_id": id, "kind": kind, "action": doActionDefinition(session.Definition, id), "completion_event": event, "completion_required": facts}
			if doProtectedAction(session, action) && previous.SourceFingerprint != fingerprint {
				blocked = append(blocked, map[string]any{"target_id": id, "cause": "protected attempt inputs changed; inspect and recover the registered attempt before executing"})
				continue
			}
			if err := doProtectedNext(root, session, action, previous.ID, fingerprint, entry); err != nil {
				return nil, err
			}
			running = append(running, entry)
			continue
		}
		if exists {
			if err := doRetryRecoveryReady(root, previous); err != nil {
				blocked = append(blocked, map[string]any{"target_id": id, "attempt_id": previous.ID, "cause": err.Error()})
				continue
			}
		}
		if !requiredClosure[id] || session.ExecutionOutcome == "passed" {
			continue
		}
		if exists && previous.Status == "passed" && doDependencyReady(root, session, latest, id, fingerprint) == nil {
			continue
		}
		cause := ""
		for _, dependency := range action.dependencies {
			if err := doDependencyReady(root, session, latest, dependency, fingerprint); err != nil {
				cause = err.Error()
				break
			}
		}
		if cause != "" {
			blocked = append(blocked, map[string]any{"target_id": id, "cause": cause})
			continue
		}
		key := doDigest([]any{session.ID, session.Revision, session.DefinitionDigest, id})[:24]
		attemptID := "a-" + key
		event, facts := doCompletionSkeleton(action, attemptID)
		started := doRecordInput{ExpectedRevision: session.Revision, RequestID: "start-" + key, Events: []doRecordEvent{{AttemptID: attemptID, TargetID: id, Kind: kind, Event: "started"}}}
		entry := map[string]any{"target_id": id, "kind": kind, "action": doActionDefinition(session.Definition, id), "started_input": started, "completion_event": event, "completion_required": facts}
		if err := doProtectedNext(root, session, action, attemptID, fingerprint, entry); err != nil {
			return nil, err
		}
		ready = append(ready, entry)
	}
	data["ready"], data["running"], data["blocked"] = ready, running, blocked
	if len(ready) == 0 && len(running) == 0 && len(blocked) == 0 {
		validation := doValidate(root, session, true)
		if validation.Status == "passed" {
			data["complete_ready"] = true
			data["complete_input"] = map[string]any{"expected_revision": session.Revision}
			data["complete_required"] = []string{"change_summary"}
			data["complete_argv"] = []string{"specify-runtime", "do", "complete", session.ID, "--input-json", "-", "--format", "json"}
		} else {
			for _, cause := range validation.Blockers {
				blocked = append(blocked, map[string]any{"cause": cause})
			}
			data["blocked"] = blocked
		}
	}
	return data, nil
}

// Each session mutation has its own short lock. Publication owns the playbook
// lock and may register metadata writes under the Do lock, so nesting the two
// would deadlock. Existing finish and publication validators close every join.
func doComplete(root, id string, input doCompleteInput) (DoSession, error) {
	var session DoSession
	if input.ExpectedRevision < 1 || strings.TrimSpace(input.ChangeSummary) == "" || len(input.ChangeSummary) > 2048 {
		return session, fmt.Errorf("expected_revision and a bounded change_summary are required")
	}
	release, err := doSessionLock(root, id)
	if err != nil {
		return session, err
	}
	session, digest, err := loadDoSession(root, id)
	if err == nil {
		session, err = doFinish(root, session, digest, doFinishInput{ExpectedRevision: input.ExpectedRevision, KnowledgeStatus: "pending"})
	}
	if err == nil && session.KnowledgeStatus == "pending" {
		err = doRequireWork(root, session)
	}
	release()
	if err != nil || session.KnowledgeStatus != "pending" {
		return session, err
	}
	request := PlaybookUpdateRequest{Definition: doMethodDefinition(session), SessionID: id, ChangeSummary: input.ChangeSummary}
	if session.MethodBinding != nil {
		request.ID, request.BaseDigest = session.MethodBinding.ID, session.MethodBinding.ContentDigest
	}
	publication, err := updatePlaybook(root, request)
	if err != nil {
		return session, fmt.Errorf("execution passed; knowledge remains pending, retry complete: %w", err)
	}
	raw, err := json.Marshal(publication["knowledge_receipt"])
	if err != nil {
		return session, err
	}
	var receipt DoKnowledgeReceipt
	if err := decodePlaybookJSON(raw, &receipt); err != nil {
		return session, fmt.Errorf("publication returned no usable knowledge receipt: %w", err)
	}
	release, err = doSessionLock(root, id)
	if err != nil {
		return session, err
	}
	defer release()
	session, digest, err = loadDoSession(root, id)
	if err != nil {
		return session, err
	}
	return doFinish(root, session, digest, doFinishInput{ExpectedRevision: session.Revision, KnowledgeStatus: "saved", Knowledge: &receipt})
}
