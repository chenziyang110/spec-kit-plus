package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"path"
	"reflect"
	"regexp"
	"strings"
	"time"
	"unicode/utf8"
)

const doNativeJSONLimit = 64 * 1024
const doNativeSnapshotSchema = "spec-kit-do-native-observation-v1"

// Native actions describe an agent's actual tool call. The runtime neither
// invokes this tool nor grants authority over its target.
type PlaybookNativeAction struct {
	Kind      string          `json:"kind"`
	Tool      string          `json:"tool"`
	Target    string          `json:"target"`
	Arguments json.RawMessage `json:"arguments"`
}

type DoNativeObservation struct {
	Outcome string          `json:"outcome"`
	Result  json.RawMessage `json:"result"`
}

type doNativeSnapshot struct {
	SchemaVersion      string                `json:"schema_version"`
	SessionID          string                `json:"session_id"`
	AttemptID          string                `json:"attempt_id"`
	TargetID           string                `json:"target_id"`
	Kind               string                `json:"kind"`
	DefinitionDigest   string                `json:"definition_digest"`
	DefinitionEpoch    int                   `json:"definition_epoch"`
	SourceFingerprint  string                `json:"source_fingerprint"`
	DependencyAttempts map[string]string     `json:"dependency_attempts"`
	Action             *PlaybookNativeAction `json:"action"`
	ToolCallID         string                `json:"tool_call_id"`
	StartedAt          string                `json:"started_at"`
	VerifiedAsOf       string                `json:"verified_as_of"`
	Observation        DoNativeObservation   `json:"observation"`
}

func (action *PlaybookNativeAction) UnmarshalJSON(raw []byte) error {
	if err := playbookRequireJSONFields(raw, "kind", "tool", "target", "arguments"); err != nil {
		return err
	}
	type plain PlaybookNativeAction
	var decoded plain
	if err := decodePlaybookJSON(raw, &decoded); err != nil {
		return err
	}
	*action = PlaybookNativeAction(decoded)
	return nil
}

func (observation *DoNativeObservation) UnmarshalJSON(raw []byte) error {
	if err := playbookRequireJSONFields(raw, "outcome"); err != nil {
		return err
	}
	var fields map[string]json.RawMessage
	if err := json.Unmarshal(raw, &fields); err != nil {
		return err
	}
	// A tool may really return JSON null. Require presence without inventing a
	// non-null return value; the independent effect assertion still must pass.
	if _, present := fields["result"]; !present {
		return fmt.Errorf("native observation requires its actual result")
	}
	type plain DoNativeObservation
	var decoded plain
	if err := decodePlaybookJSON(raw, &decoded); err != nil {
		return err
	}
	*observation = DoNativeObservation(decoded)
	return nil
}

// Bound JSON structurally as well as by bytes. Canonicalization preserves JSON
// number semantics and rejects duplicate keys instead of silently choosing one.
func doNativeJSON(raw json.RawMessage, objectRequired bool) (json.RawMessage, error) {
	if len(raw) == 0 || len(raw) > doNativeJSONLimit || !utf8.Valid(raw) {
		return nil, fmt.Errorf("native JSON must be bounded UTF-8, at most 64 KiB")
	}
	if err := playbookRejectDuplicateKeys(raw); err != nil {
		return nil, fmt.Errorf("native JSON invalid: %w", err)
	}
	var value any
	decoder := json.NewDecoder(bytes.NewReader(raw))
	decoder.UseNumber()
	if err := decoder.Decode(&value); err != nil {
		return nil, fmt.Errorf("native JSON invalid: %w", err)
	}
	if objectRequired {
		if _, ok := value.(map[string]any); !ok {
			return nil, fmt.Errorf("native arguments must be a JSON object")
		}
	}
	nodes := 0
	var inspect func(any, int) error
	inspect = func(current any, depth int) error {
		nodes++
		// Leave room for the owning definition/session/snapshot envelope under
		// the existing whole-document depth limit of 32.
		if depth > 24 || nodes > 4096 {
			return fmt.Errorf("native JSON structural limits exceeded")
		}
		switch item := current.(type) {
		case map[string]any:
			if len(item) > 128 {
				return fmt.Errorf("native JSON object has too many fields")
			}
			for key, child := range item {
				if len(key) > 256 || strings.ContainsAny(key, "\x00\r\n") {
					return fmt.Errorf("native JSON key is invalid")
				}
				if err := inspect(child, depth+1); err != nil {
					return err
				}
			}
		case []any:
			if len(item) > 1024 {
				return fmt.Errorf("native JSON array has too many items")
			}
			for _, child := range item {
				if err := inspect(child, depth+1); err != nil {
					return err
				}
			}
		case string:
			if len(item) > 32768 || strings.ContainsRune(item, '\x00') {
				return fmt.Errorf("native JSON string is invalid")
			}
		}
		return nil
	}
	if err := inspect(value, 0); err != nil {
		return nil, err
	}
	canonical, err := json.Marshal(value)
	if err != nil || len(canonical) > doNativeJSONLimit {
		return nil, fmt.Errorf("canonical native JSON exceeds 64 KiB")
	}
	return canonical, nil
}

func normalizePlaybookNativeAction(action *PlaybookNativeAction) *PlaybookNativeAction {
	if action == nil {
		return nil
	}
	result := *action
	result.Arguments = append(json.RawMessage(nil), action.Arguments...)
	if normalized, err := doNativeJSON(action.Arguments, true); err == nil {
		result.Arguments = normalized
	}
	return &result
}

func doNativeSensitiveCheck(root string, value any) error {
	raw, err := json.Marshal(value)
	if err != nil {
		return err
	}
	var decoded any
	if err := json.Unmarshal(raw, &decoded); err != nil {
		return err
	}
	secretKey := regexp.MustCompile(`(?i)^(token|password|passwd|secret|api[-_]?key|access[-_]?token|authorization|client[-_]?secret)$`)
	boundVariable := regexp.MustCompile(`^\$\{[A-Z_][A-Z0-9_]*\}$`)
	var inspect func(any) error
	inspect = func(current any) error {
		switch item := current.(type) {
		case map[string]any:
			for key, child := range item {
				if secretKey.MatchString(key) {
					text, ok := child.(string)
					if !ok || !boundVariable.MatchString(text) {
						return fmt.Errorf("native sensitive field requires an environment binding, never a persisted secret")
					}
				}
				if err := inspect(child); err != nil {
					return err
				}
			}
		case []any:
			for _, child := range item {
				if err := inspect(child); err != nil {
					return err
				}
			}
		}
		return nil
	}
	if err := inspect(decoded); err != nil {
		return err
	}
	policy, _, err := (learningService{projectRoot: root}).loadLearningPolicy(false)
	if err != nil {
		return err
	}
	projection := regexp.MustCompile(`\$\{[A-Z_][A-Z0-9_]*\}`).ReplaceAllString(string(raw), "[REDACTED_SECRET]")
	if redacted := redactLearningTextWithPolicy(projection, policy); redacted.text != projection {
		return fmt.Errorf("native sensitive content rejected; sanitize the observation before recording")
	}
	return nil
}

func validatePlaybookNativeAction(root string, action *PlaybookNativeAction, argv []string, cwd, script string) error {
	if action == nil {
		return nil
	}
	if len(argv) != 0 || cwd != "" || script != "" {
		return fmt.Errorf("native action cannot carry process argv, cwd, or script_ref")
	}
	if action.Kind != "file" && action.Kind != "browser" && action.Kind != "desktop" && action.Kind != "connector" {
		return fmt.Errorf("native action kind must be file, browser, desktop, or connector")
	}
	for _, item := range []struct {
		text  string
		limit int
	}{{action.Tool, 256}, {action.Target, 2048}} {
		if item.text == "" || strings.TrimSpace(item.text) != item.text || len(item.text) > item.limit || strings.ContainsAny(item.text, "\x00\r\n") {
			return fmt.Errorf("native action requires bounded tool and target identities")
		}
	}
	if action.Kind == "file" {
		if _, err := playbookSafePath(root, action.Target, true); err != nil {
			return err
		}
	}
	if _, err := doNativeJSON(action.Arguments, true); err != nil {
		return err
	}
	return doNativeSensitiveCheck(root, action)
}

func doNativeActionsEqual(a, b *PlaybookNativeAction) bool {
	return reflect.DeepEqual(normalizePlaybookNativeAction(a), normalizePlaybookNativeAction(b))
}

func doNativeCheckAssertion(check PlaybookCheck, observation DoNativeObservation) error {
	if observation.Outcome != "succeeded" {
		return fmt.Errorf("native effect check has no successful independent observation")
	}
	var actual, expected any
	for _, item := range []struct {
		raw    []byte
		target *any
	}{{observation.Result, &actual}, {check.ExpectedJSON, &expected}} {
		decoder := json.NewDecoder(bytes.NewReader(item.raw))
		decoder.UseNumber()
		if err := decoder.Decode(item.target); err != nil {
			return fmt.Errorf("native effect assertion contains invalid JSON")
		}
	}
	actual, err := doJSONPointer(actual, check.JSONPointer)
	if err != nil || !reflect.DeepEqual(actual, expected) {
		return fmt.Errorf("native effect assertion failed for %s", check.ID)
	}
	return nil
}

func doNativeEffectKind(kind string) bool {
	return kind == "observation" || kind == "file" || kind == "json" || kind == "junit"
}

func doDefinitionDependencies(definition PlaybookDefinition) map[string][]string {
	dependencies := map[string][]string{}
	for _, step := range definition.Steps {
		dependencies[step.ID] = step.DependsOn
	}
	for _, check := range definition.Checks {
		dependencies[check.ID] = check.DependsOn
	}
	return dependencies
}

func doDependencyClosure(dependencies map[string][]string, roots []string) map[string]bool {
	closure := map[string]bool{}
	var visit func(string)
	visit = func(id string) {
		if closure[id] {
			return
		}
		closure[id] = true
		for _, dependency := range dependencies[id] {
			visit(dependency)
		}
	}
	for _, root := range roots {
		visit(root)
	}
	return closure
}

// A successful write response is not proof of the promised effect. Every
// native mutation in the full required closure needs a required typed effect
// check that actually depends on that mutation. An optional check cannot close
// this obligation, nor can an unrelated successful process.
func doValidateNativeCoverage(definition PlaybookDefinition) error {
	dependencies := doDefinitionDependencies(definition)
	roots := []string{}
	for _, step := range definition.Steps {
		if step.Required {
			roots = append(roots, step.ID)
		}
	}
	for _, check := range definition.Checks {
		if check.Required {
			roots = append(roots, check.ID)
		}
	}
	closure := doDependencyClosure(dependencies, roots)
	covered := map[string]bool{}
	for _, check := range definition.Checks {
		if !check.Required || !doNativeEffectKind(check.Kind) {
			continue
		}
		for id := range doDependencyClosure(dependencies, check.DependsOn) {
			covered[id] = true
		}
	}
	for _, step := range definition.Steps {
		if closure[step.ID] && step.NativeAction != nil && step.SideEffect != "read" && !covered[step.ID] {
			return fmt.Errorf("native mutation %s requires a dependent required observation/file/json/junit effect check", step.ID)
		}
	}
	return nil
}

func doCheckNeedsNativeIndependence(definition PlaybookDefinition, action doAction) bool {
	if action.check == nil || !doNativeEffectKind(action.check.Kind) {
		return false
	}
	if action.check.Kind == "observation" {
		return true
	}
	closure := doDependencyClosure(doDefinitionDependencies(definition), action.dependencies)
	for _, step := range definition.Steps {
		if closure[step.ID] && step.NativeAction != nil && step.SideEffect != "read" {
			return true
		}
	}
	return false
}

func doNativeCheckIndependence(session DoSession, action doAction, attempt DoAttempt, toolCallID, startedAt string) error {
	if !doCheckNeedsNativeIndependence(session.Definition, action) {
		return nil
	}
	if len(action.dependencies) == 0 {
		return fmt.Errorf("native effect check requires a concrete producer dependency")
	}
	started, err := time.Parse(time.RFC3339Nano, startedAt)
	if err != nil {
		return err
	}
	latest := doLatestAttempts(session)
	for _, previous := range session.Attempts {
		if previous.ID != attempt.ID && previous.ToolCallID == toolCallID {
			return fmt.Errorf("native effect check must use its own fresh tool call")
		}
	}
	var verifyProducer func(string, string) error
	visited := map[string]bool{}
	verifyProducer = func(dependency, boundAttempt string) error {
		producer, ok := latest[dependency]
		if !ok || producer.ID != boundAttempt || producer.Status != "passed" || producer.ToolCallID == toolCallID {
			return fmt.Errorf("native effect check must use an independent tool call after its exact producer")
		}
		if visited[dependency] {
			return nil
		}
		visited[dependency] = true
		finished, err := time.Parse(time.RFC3339Nano, producer.FinishedAt)
		if err != nil || started.Before(finished) {
			return fmt.Errorf("native effect observation predates its producer completion")
		}
		for id, bound := range producer.DependencyAttempts {
			if err := verifyProducer(id, bound); err != nil {
				return err
			}
		}
		return nil
	}
	for _, dependency := range action.dependencies {
		if err := verifyProducer(dependency, attempt.DependencyAttempts[dependency]); err != nil {
			return err
		}
	}
	return nil
}

func doNativeObservationRef(session DoSession, attemptID string) string {
	return path.Join(path.Dir(doSessionRef(session.ID)), "evidence", attemptID+"-native.json")
}

func doPrepareNativeObservation(root string, session DoSession, action doAction, attempt DoAttempt, event doRecordEvent) (string, string, []fileTransactionUpdate, error) {
	if action.nativeAction == nil {
		if event.NativeAction != nil || event.NativeObservation != nil {
			return "", "", nil, fmt.Errorf("process action cannot receive a native action observation")
		}
		return "", "", nil, doNativeCheckIndependence(session, action, attempt, event.ToolCallID, event.StartedAt)
	}
	if event.NativeAction == nil || event.NativeObservation == nil || !doNativeActionsEqual(attempt.NativeAction, event.NativeAction) {
		return "", "", nil, fmt.Errorf("native observation must match the frozen tool, target, kind, and arguments")
	}
	if err := validatePlaybookNativeAction(root, event.NativeAction, event.Argv, event.Cwd, ""); err != nil {
		return "", "", nil, err
	}
	if event.ExitCode != nil {
		return "", "", nil, fmt.Errorf("native observation cannot invent a process exit_code")
	}
	observation := *event.NativeObservation
	normalized, err := doNativeJSON(observation.Result, false)
	if err != nil {
		return "", "", nil, err
	}
	observation.Result = normalized
	if observation.Outcome != "succeeded" && observation.Outcome != "failed" && observation.Outcome != "unknown" {
		return "", "", nil, fmt.Errorf("native observation outcome must be succeeded, failed, or unknown")
	}
	if (observation.Outcome == "unknown") != (event.Status == "interrupted") || (event.Status == "passed" && observation.Outcome != "succeeded") {
		return "", "", nil, fmt.Errorf("native outcome conflicts with the observed attempt status")
	}
	if event.Status == "failed" && observation.Outcome == "succeeded" {
		if action.check == nil || action.check.Kind != "observation" || doNativeCheckAssertion(*action.check, observation) == nil {
			return "", "", nil, fmt.Errorf("successful native call requires a genuinely failing frozen effect assertion to record failure")
		}
	}
	if err := doNativeCheckIndependence(session, action, attempt, event.ToolCallID, event.StartedAt); err != nil {
		return "", "", nil, err
	}
	if action.check != nil && action.check.Kind == "observation" {
		if event.Status == "passed" {
			if err := doNativeCheckAssertion(*action.check, observation); err != nil {
				return "", "", nil, err
			}
		}
	}
	snapshot := doNativeSnapshot{SchemaVersion: doNativeSnapshotSchema, SessionID: session.ID, AttemptID: attempt.ID, TargetID: attempt.TargetID, Kind: attempt.Kind, DefinitionDigest: attempt.DefinitionDigest, DefinitionEpoch: attempt.DefinitionEpoch, SourceFingerprint: attempt.SourceFingerprint, DependencyAttempts: attempt.DependencyAttempts, Action: normalizePlaybookNativeAction(event.NativeAction), ToolCallID: event.ToolCallID, StartedAt: event.StartedAt, VerifiedAsOf: event.FinishedAt, Observation: observation}
	if err := doNativeSensitiveCheck(root, snapshot); err != nil {
		return "", "", nil, err
	}
	raw, err := json.Marshal(snapshot)
	if err != nil {
		return "", "", nil, err
	}
	ref := doNativeObservationRef(session, attempt.ID)
	target, err := secureProjectPath(root, ref)
	if err != nil {
		return "", "", nil, err
	}
	return ref, doBytesDigest(raw), []fileTransactionUpdate{{Path: target, Content: raw, Perm: 0o600}}, nil
}

func doReadNativeObservation(root string, session DoSession, attempt DoAttempt) (DoNativeObservation, error) {
	var empty DoNativeObservation
	if attempt.NativeAction == nil || attempt.NativeObservationRef != doNativeObservationRef(session, attempt.ID) || !playbookDigestPattern.MatchString(attempt.NativeObservationSHA256) {
		return empty, fmt.Errorf("native observation lacks its exact owned snapshot")
	}
	raw, err := secureProjectReadFile(root, attempt.NativeObservationRef)
	if err != nil || len(raw) > 3*doNativeJSONLimit || doBytesDigest(raw) != attempt.NativeObservationSHA256 {
		return empty, fmt.Errorf("native observation snapshot is missing or changed")
	}
	var snapshot doNativeSnapshot
	if err := decodePlaybookJSON(raw, &snapshot); err != nil {
		return empty, err
	}
	if snapshot.SchemaVersion != doNativeSnapshotSchema || snapshot.SessionID != session.ID || snapshot.AttemptID != attempt.ID || snapshot.TargetID != attempt.TargetID || snapshot.Kind != attempt.Kind || snapshot.DefinitionDigest != attempt.DefinitionDigest || snapshot.DefinitionEpoch != attempt.DefinitionEpoch || snapshot.SourceFingerprint != attempt.SourceFingerprint || !reflect.DeepEqual(snapshot.DependencyAttempts, attempt.DependencyAttempts) || snapshot.ToolCallID != attempt.ToolCallID || snapshot.StartedAt != attempt.StartedAt || snapshot.VerifiedAsOf != attempt.FinishedAt || !doNativeActionsEqual(snapshot.Action, attempt.NativeAction) {
		return empty, fmt.Errorf("native observation snapshot binding changed")
	}
	if _, err := doNativeJSON(snapshot.Observation.Result, false); err != nil {
		return empty, err
	}
	return snapshot.Observation, nil
}

func doValidateNativeAttempt(root string, session DoSession, action doAction, attempt DoAttempt) error {
	if action.nativeAction == nil {
		if attempt.NativeAction != nil || attempt.NativeObservationRef != "" || attempt.NativeObservationSHA256 != "" {
			return fmt.Errorf("process attempt contains foreign native observation metadata")
		}
		return doNativeCheckIndependence(session, action, attempt, attempt.ToolCallID, attempt.StartedAt)
	}
	if !doNativeActionsEqual(action.nativeAction, attempt.NativeAction) || len(attempt.Argv) != 0 || attempt.Cwd != "" || attempt.ExitCode != nil {
		return fmt.Errorf("native attempt identity or execution kind was altered")
	}
	observation, err := doReadNativeObservation(root, session, attempt)
	if err != nil {
		return err
	}
	if observation.Outcome != "succeeded" {
		return fmt.Errorf("native attempt lacks a successful observation")
	}
	if err := doNativeCheckIndependence(session, action, attempt, attempt.ToolCallID, attempt.StartedAt); err != nil {
		return err
	}
	if action.check != nil && action.check.Kind == "observation" {
		return doNativeCheckAssertion(*action.check, observation)
	}
	return nil
}

// Called only for a recorded native failure by the existing replan owner.
func doVerifyNativeFailure(root string, session DoSession, failed DoAttempt) error {
	action, err := doFindAction(session, failed.Kind, failed.TargetID)
	if err != nil || action.nativeAction == nil || !doNativeActionsEqual(action.nativeAction, failed.NativeAction) || failed.Status != "failed" {
		return fmt.Errorf("native replan needs its exact observed failed action")
	}
	observation, err := doReadNativeObservation(root, session, failed)
	if err != nil {
		return err
	}
	if observation.Outcome == "failed" {
		return nil
	}
	if observation.Outcome == "succeeded" && action.check != nil && action.check.Kind == "observation" && doNativeCheckAssertion(*action.check, observation) != nil {
		return doNativeCheckIndependence(session, action, failed, failed.ToolCallID, failed.StartedAt)
	}
	return fmt.Errorf("native replan requires a tool failure or failing frozen effect assertion")
}
