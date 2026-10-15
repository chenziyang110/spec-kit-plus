package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path"
	"reflect"
	"strings"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runcontrol"
)

const doDefinitionEpochLimit = 32

func (input *doReplanInput) UnmarshalJSON(raw []byte) error {
	if err := playbookRequireJSONFields(raw, "request_id", "definition"); err != nil {
		return err
	}
	var fields map[string]json.RawMessage
	if err := json.Unmarshal(raw, &fields); err != nil {
		return err
	}
	for _, name := range []string{"write_scope", "output_scope"} {
		if value, present := fields[name]; present && bytes.Equal(bytes.TrimSpace(value), []byte("null")) {
			return fmt.Errorf("replan %s must be an array when supplied; omit it to inherit scope", name)
		}
	}
	type plain doReplanInput
	var value plain
	if err := decodePlaybookJSON(raw, &value); err != nil {
		return err
	}
	*input = doReplanInput(value)
	return nil
}

func (input doReplanInput) MarshalJSON() ([]byte, error) {
	value := map[string]any{"request_id": input.RequestID, "definition": input.Definition}
	if input.Mode != "" {
		value["mode"] = input.Mode
	}
	if input.RetainVerified {
		value["retain_verified"] = true
	}
	if input.WriteScope != nil {
		value["write_scope"] = input.WriteScope
	}
	if input.OutputScope != nil {
		value["output_scope"] = input.OutputScope
	}
	return json.Marshal(value)
}

func doCurrentDefinitionEpoch(session DoSession) int {
	if session.DefinitionEpoch == 0 {
		return 1 // Sessions created before typed replanning have one frozen epoch.
	}
	return session.DefinitionEpoch
}

func doAttemptInCurrentDefinition(session DoSession, attempt DoAttempt) bool {
	epoch := attempt.DefinitionEpoch
	if epoch == 0 {
		epoch = 1
	}
	return epoch == doCurrentDefinitionEpoch(session) && attempt.DefinitionDigest == session.DefinitionDigest
}

func doInitializeDefinitionEpoch(session *DoSession, sources map[string]string, fingerprint, revision string, dirty []string) {
	session.DefinitionEpoch = 1
	session.DefinitionHistory = []DoDefinitionEpoch{{Epoch: 1, Definition: session.Definition, DefinitionDigest: session.DefinitionDigest, Sources: sources, SourceFingerprint: fingerprint, SourceRevision: revision, DirtyPaths: append([]string{}, dirty...), WriteScope: append([]string{}, session.WriteScope...), OutputScope: append([]string{}, session.OutputScope...), FrozenAt: session.CreatedAt, BasisOrigin: "runtime_source_capture"}}
	session.DefinitionHistory[0].TemplateDefinition = session.TemplateDefinition
	session.DefinitionHistory[0].TemplateDigest = session.TemplateDigest
	session.DefinitionHistory[0].Parameters = session.Parameters
}

func doDefinitionEpochRef(sessionID string, epoch int) string {
	return path.Join(path.Dir(doSessionRef(sessionID)), "definitions", fmt.Sprintf("%06d.json", epoch))
}

func doDefinitionEpochBytes(epoch DoDefinitionEpoch) ([]byte, error) {
	raw, err := json.MarshalIndent(epoch, "", "  ")
	return append(raw, '\n'), err
}

// A legacy single-epoch session keeps its real original source map. There is no
// claim that a missing historical fingerprint was observed retrospectively.
func doEnsureDefinitionHistory(session *DoSession) {
	if len(session.DefinitionHistory) != 0 {
		return
	}
	session.DefinitionEpoch = 1
	session.DefinitionHistory = []DoDefinitionEpoch{{Epoch: 1, Definition: session.Definition, DefinitionDigest: session.DefinitionDigest, Sources: session.InitialSources, DirtyPaths: []string{}, WriteScope: append([]string{}, session.WriteScope...), OutputScope: append([]string{}, session.OutputScope...), FrozenAt: session.CreatedAt, BasisOrigin: "legacy_initial_sources"}}
}

// Definitions after the first replan have immutable files as well as the
// session history. Readers reject a removed/changed epoch, never repair it by
// treating the current method or an old passed attempt as a replacement.
func doValidateDefinitionHistory(root string, session DoSession) error {
	epoch := doCurrentDefinitionEpoch(session)
	if epoch < 1 || epoch > doDefinitionEpochLimit {
		return fmt.Errorf("invalid definition epoch")
	}
	if len(session.DefinitionHistory) == 0 {
		if epoch == 1 {
			return nil
		}
		return fmt.Errorf("definition history is missing")
	}
	if len(session.DefinitionHistory) != epoch {
		return fmt.Errorf("definition history does not cover the current epoch")
	}
	for i, item := range session.DefinitionHistory {
		digest, err := playbookDefinitionDigest(item.Definition)
		if err != nil || item.Epoch != i+1 || item.DefinitionDigest != digest || playbookID(item.Definition) != playbookID(session.Definition) || item.Definition.Goal != session.Goal {
			return fmt.Errorf("definition history identity or digest differs from its frozen epoch")
		}
		want, err := doDefinitionEpochBytes(item)
		binding := DoSession{Definition: item.Definition, DefinitionDigest: item.DefinitionDigest, TemplateDefinition: item.TemplateDefinition, TemplateDigest: item.TemplateDigest, Parameters: item.Parameters}
		if err := doVerifyInstanceBinding(root, binding); err != nil {
			return err
		}
		if err != nil {
			return err
		}
		raw, err := secureProjectReadFile(root, doDefinitionEpochRef(session.ID, item.Epoch))
		if os.IsNotExist(err) && epoch == 1 {
			continue // Initial sessions materialize their first file at first replan.
		}
		if err != nil || !bytes.Equal(raw, want) {
			return fmt.Errorf("immutable definition epoch %d is missing or changed", item.Epoch)
		}
	}
	current := session.DefinitionHistory[len(session.DefinitionHistory)-1]
	if current.TemplateDigest != session.TemplateDigest || !reflect.DeepEqual(current.Parameters, session.Parameters) || !reflect.DeepEqual(current.TemplateDefinition, session.TemplateDefinition) {
		return fmt.Errorf("current parameter template differs from its immutable epoch")
	}
	if current.DefinitionDigest != session.DefinitionDigest || !reflect.DeepEqual(uniqueSortedTrimmed(current.WriteScope), uniqueSortedTrimmed(session.WriteScope)) || !reflect.DeepEqual(uniqueSortedTrimmed(current.OutputScope), uniqueSortedTrimmed(session.OutputScope)) {
		return fmt.Errorf("current definition or scope differs from its epoch")
	}
	return doValidateRetainedBindings(session)
}

func doReplan(root string, session DoSession, oldDigest string, input doResumeInput) (DoSession, error) {
	if input.Replan == nil || !doIDPattern.MatchString(input.Replan.RequestID) {
		return session, fmt.Errorf("replan requires a valid request_id and replacement definition")
	}
	unstarted := input.Replan.Mode == "unstarted"
	if input.Replan.Mode != "" && input.Replan.Mode != "failed" && !unstarted {
		return session, fmt.Errorf("unknown replan mode")
	}
	if unstarted && (input.AttemptID != "" || !reflect.DeepEqual(input.Recovery, DoRecovery{})) {
		return session, fmt.Errorf("unstarted adjustment cannot carry fabricated recovery")
	}
	if input.Recovery.EvidenceSHA256 != "" {
		return session, fmt.Errorf("recovery evidence_sha256 is runtime-owned")
	}
	requestDigest := doDigest(input)
	if receipt, exists := session.ReplanReceipts[input.Replan.RequestID]; exists {
		if receipt.RequestDigest != requestDigest {
			return session, fmt.Errorf("replan request_id was reused with a different payload")
		}
		if receipt.EvidenceRef != "" {
			raw, err := secureProjectReadFile(root, receipt.EvidenceRef)
			if err != nil || doBytesDigest(raw) != receipt.EvidenceSHA256 {
				return session, fmt.Errorf("replayed replan recovery evidence is missing or changed")
			}
		} else if !unstarted {
			return session, fmt.Errorf("replayed failure recovery evidence is missing")
		}
		if err := doValidateDefinitionHistory(root, session); err != nil {
			return session, err
		}
		if receipt.DefinitionEpoch < 2 || receipt.DefinitionEpoch > len(session.DefinitionHistory) || session.DefinitionHistory[receipt.DefinitionEpoch-1].DefinitionDigest != receipt.DefinitionDigest {
			return session, fmt.Errorf("replan receipt does not bind its immutable definition epoch")
		}
		return session, nil
	}
	if input.ExpectedRevision != session.Revision {
		return session, fmt.Errorf("session revision conflict")
	}
	if session.KnowledgeStatus != "pending" || session.ExecutionOutcome == "passed" || session.Knowledge != nil {
		return session, fmt.Errorf("replan requires an unfinished operation awaiting knowledge capture")
	}
	if session.Blocker != nil {
		return session, fmt.Errorf("resolve the external blocker before replanning")
	}
	if doCurrentDefinitionEpoch(session) >= doDefinitionEpochLimit {
		return session, fmt.Errorf("definition epoch limit reached; preserve this session and start a separate operation")
	}
	if err := doValidateDefinitionHistory(root, session); err != nil {
		return session, err
	}
	index := -1
	for i, attempt := range session.Attempts {
		if attempt.Status != "passed" && attempt.Status != "failed" && attempt.Status != "interrupted" && attempt.Status != "running" {
			return session, fmt.Errorf("attempt %s has unknown effects and cannot be replanned", attempt.ID)
		}
		if attempt.Status == "running" || (attempt.Status == "interrupted" && attempt.Recovery == nil) {
			return session, fmt.Errorf("running or unknown effects require ordinary recovery before replan")
		}
		if attempt.ID == input.AttemptID && doAttemptInCurrentDefinition(session, attempt) {
			index = i
		}
	}
	var recovery DoRecovery
	var extra []fileTransactionUpdate
	var failed DoAttempt
	if !unstarted {
		if index < 0 {
			return session, fmt.Errorf("replan requires an exact failed attempt in the current definition epoch")
		}
		failed = session.Attempts[index]
		if latest, ok := doLatestAttempts(session)[failed.TargetID]; !ok || latest.ID != failed.ID {
			return session, fmt.Errorf("replan requires the latest unresolved failed attempt, not an earlier replaced result")
		}
		if failed.Status != "failed" || failed.EvidenceOrigin != "agent_tool_observation" || failed.ToolCallID == "" || failed.TimedOut || failed.Cancelled {
			return session, fmt.Errorf("replan requires an observed failure; interruption or a new suggestion is not a failed execution")
		}
		if err := doReplanVerifyFailure(root, session, failed); err != nil {
			return session, err
		}
		var err error
		recovery, extra, err = doPrepareRecovery(root, session, input)
		if err != nil {
			return session, err
		}
	}
	for i, attempt := range session.Attempts {
		if i == index || (attempt.Status != "failed" && attempt.Status != "interrupted") {
			continue
		}
		if attempt.Recovery == nil {
			return session, fmt.Errorf("attempt %s still needs side-effect recovery before replan", attempt.ID)
		}
		raw, err := secureProjectReadFile(root, attempt.Recovery.EvidenceRef)
		if err != nil || doBytesDigest(raw) != attempt.Recovery.EvidenceSHA256 {
			return session, fmt.Errorf("attempt %s recovery evidence is missing or changed", attempt.ID)
		}
	}
	definition := playbookNormalizeDefinition(input.Replan.Definition)
	if err := validatePlaybookDefinition(root, definition); err != nil {
		return session, err
	}
	template := definition
	definition, parameters, err := resolvePlaybookDefinition(root, template, session.Parameters)
	if err != nil {
		return session, err
	}
	if playbookID(definition) != playbookID(session.Definition) || definition.Goal != session.Goal {
		return session, fmt.Errorf("replan must preserve the operation identity and original goal")
	}
	if gaps := playbookCompatibility(definition, session.Context); len(gaps) != 0 {
		return session, fmt.Errorf("incompatible replacement definition: %s", strings.Join(gaps, "; "))
	}
	definitionDigest, err := playbookDefinitionDigest(definition)
	if err != nil {
		return session, err
	}
	if definitionDigest == session.DefinitionDigest {
		return session, fmt.Errorf("unchanged definition requires ordinary resume and retry, not replan")
	}
	if unstarted || input.Replan.RetainVerified {
		if err := doIncrementalContract(session.Definition, definition); err != nil {
			return session, err
		}
	}
	if unstarted {
		for _, attempt := range session.Attempts {
			if doAttemptInCurrentDefinition(session, attempt) || doRetainedAttempt(session, attempt) {
				if !reflect.DeepEqual(doActionDefinition(session.Definition, attempt.TargetID), doActionDefinition(definition, attempt.TargetID)) {
					return session, fmt.Errorf("unstarted adjustment cannot alter attempted action %s (prior %s, proposed %s)", attempt.TargetID, doDigest(doActionDefinition(session.Definition, attempt.TargetID)), doDigest(doActionDefinition(definition, attempt.TargetID)))
				}
			}
		}
	}
	writeScope, err := doReplanScope(root, session.WriteScope, input.Replan.WriteScope)
	if err != nil {
		return session, err
	}
	outputScope, err := doReplanScope(root, session.OutputScope, input.Replan.OutputScope)
	if err != nil {
		return session, err
	}
	if err := doValidateOperationScopes(definition, writeScope, outputScope); err != nil {
		return session, err
	}
	if err := doReplanRejectRetroactiveScope(root, session, writeScope, outputScope); err != nil {
		return session, err
	}
	sources, fingerprint, sourceRevision, dirty, err := doCaptureSource(root, definition, writeScope)
	if err != nil {
		return session, err
	}
	current, currentDigest, err := loadDoSession(root, session.ID)
	if err != nil || currentDigest != oldDigest || current.Revision != session.Revision || doDigest(current) != doDigest(session) {
		return session, fmt.Errorf("session revision conflict before replan scope registration")
	}
	session, err = doAdoptRecoveredWorkFence(root, session, input.WorkFence, false)
	if err != nil {
		return session, err
	}
	if err := doReplanClaimScopes(root, session, writeScope, outputScope); err != nil {
		return session, err
	}
	if _, currentFingerprint, _, _, err := doCaptureSource(root, definition, writeScope); err != nil || currentFingerprint != fingerprint {
		return session, fmt.Errorf("source changed while replan claimed its scope; inspect the new source before retrying")
	}
	doEnsureDefinitionHistory(&session)
	var retained []DoRetainedAttempt
	if input.Replan.RetainVerified {
		retained = doPlanRetained(root, session, definition, fingerprint)
	}
	session.Attempts = append([]DoAttempt{}, session.Attempts...)
	if !unstarted {
		session.Attempts[index].Recovery = &recovery
	}
	session.DefinitionEpoch = doCurrentDefinitionEpoch(session) + 1
	session.Definition = definition
	session.DefinitionDigest = definitionDigest
	if len(template.Parameters) > 0 {
		session.TemplateDefinition = &template
		session.TemplateDigest, _ = playbookDefinitionDigest(template)
		session.Parameters = parameters
	} else {
		session.TemplateDefinition = nil
		session.TemplateDigest = ""
		session.Parameters = nil
	}
	session.WriteScope, session.OutputScope = writeScope, outputScope
	session.ExecutionOutcome = "pending"
	session.Validation = nil
	session.UpdatedAt = doNow()
	session.Revision++
	epoch := DoDefinitionEpoch{Epoch: session.DefinitionEpoch, Definition: definition, DefinitionDigest: definitionDigest, Sources: sources, SourceFingerprint: fingerprint, SourceRevision: sourceRevision, DirtyPaths: dirty, WriteScope: writeScope, OutputScope: outputScope, FrozenAt: session.UpdatedAt, BasisOrigin: "runtime_source_capture", ReplanRequestID: input.Replan.RequestID, FailedAttemptID: failed.ID, Recovery: &recovery}
	epoch.TemplateDefinition, epoch.TemplateDigest, epoch.Parameters = session.TemplateDefinition, session.TemplateDigest, session.Parameters
	epoch.RetainedAttempts = retained
	if unstarted {
		epoch.Recovery = nil
	}
	session.DefinitionHistory = append(append([]DoDefinitionEpoch{}, session.DefinitionHistory...), epoch)
	receipts := make(map[string]DoReplanReceipt, len(session.ReplanReceipts)+1)
	for key, value := range session.ReplanReceipts {
		receipts[key] = value
	}
	receipts[input.Replan.RequestID] = DoReplanReceipt{RequestDigest: requestDigest, DefinitionEpoch: epoch.Epoch, DefinitionDigest: definitionDigest, EvidenceRef: recovery.EvidenceRef, EvidenceSHA256: recovery.EvidenceSHA256}
	session.ReplanReceipts = receipts
	for _, item := range session.DefinitionHistory {
		raw, err := doDefinitionEpochBytes(item)
		if err != nil {
			return session, err
		}
		ref := doDefinitionEpochRef(session.ID, item.Epoch)
		previous, err := secureProjectReadFile(root, ref)
		if err == nil {
			if !bytes.Equal(previous, raw) {
				return session, fmt.Errorf("immutable definition epoch %d was changed", item.Epoch)
			}
			continue
		}
		if !os.IsNotExist(err) {
			return session, err
		}
		target, err := secureProjectPath(root, ref)
		if err != nil {
			return session, err
		}
		extra = append(extra, fileTransactionUpdate{Path: target, Content: raw, Perm: 0o600})
	}
	return session, doWriteSession(root, session, oldDigest, extra)
}

func doReplanVerifyFailure(root string, session DoSession, failed DoAttempt) error {
	if failed.NativeAction != nil {
		return doVerifyNativeFailure(root, session, failed)
	}
	if len(failed.Argv) > 0 && failed.ExitCode != nil && *failed.ExitCode != 0 {
		return nil
	}
	action, err := doFindAction(session, failed.Kind, failed.TargetID)
	if err != nil || action.check == nil || (action.check.Kind != "json" && action.check.Kind != "junit") {
		return fmt.Errorf("a failed command needs its actual nonzero exit, or an inspection needs typed failing report evidence")
	}
	matched := false
	for _, ref := range failed.Results {
		if ref.Kind != action.check.Kind || ref.Path != action.check.ResultPath {
			continue
		}
		if matched || !doScopeContains([]string{path.Join(path.Dir(doSessionRef(session.ID)), "evidence")}, ref.SnapshotRef) {
			return fmt.Errorf("failed check must bind exactly one owned report snapshot")
		}
		matched = true
		raw, err := secureProjectReadFile(root, ref.SnapshotRef)
		if err != nil || int64(len(raw)) != ref.Size || doBytesDigest(raw) != ref.SnapshotSHA256 || ref.SHA256 != ref.SnapshotSHA256 {
			return fmt.Errorf("failed check report snapshot is missing or changed")
		}
	}
	if !matched {
		return fmt.Errorf("a failed inspection needs its exact typed report evidence before replan")
	}
	if doCheckEvidence(root, *action.check, failed.Results, true) == nil {
		return fmt.Errorf("the reported failure actually satisfies its frozen check; use ordinary retry")
	}
	return nil
}

func doReplanScope(root string, previous, requested []string) ([]string, error) {
	if requested == nil {
		return append([]string{}, previous...), nil
	}
	if len(requested) > 128 {
		return nil, fmt.Errorf("replan scope exceeds 128 exact paths")
	}
	result := []string{}
	seen := map[string]bool{}
	for _, raw := range requested {
		clean, err := doPath(root, raw, false)
		if err != nil {
			return nil, err
		}
		if doWorkflowStatePath(clean) {
			return nil, fmt.Errorf("runtime/workflow state is not product or output scope")
		}
		if !seen[clean] {
			seen[clean] = true
			result = append(result, clean)
		}
	}
	for _, p := range previous {
		if !seen[p] {
			return nil, fmt.Errorf("replan cannot shrink or replace an existing exact scope: %s", p)
		}
	}
	return uniqueSortedTrimmed(result), nil
}

func doValidateOperationScopes(definition PlaybookDefinition, writeScope, outputScope []string) error {
	sources := append([]string{}, definition.SourceFiles...)
	for _, step := range definition.Steps {
		if step.NativeAction != nil && step.NativeAction.Kind == "file" && step.SideEffect != "read" {
			target := step.NativeAction.Target
			if !doScopeContains(outputScope, target) && !doScopeContains(step.SourceWrites, target) {
				return fmt.Errorf("native file mutation target must be inside output_scope or this step's source_writes")
			}
		}
		if step.ScriptRef != "" {
			sources = append(sources, step.ScriptRef)
		}
		for _, p := range step.SourceWrites {
			if !doScopeContains(writeScope, p) {
				return fmt.Errorf("step %s source_writes must remain inside the explicit write_scope", step.ID)
			}
		}
	}
	for _, check := range definition.Checks {
		if check.ScriptRef != "" {
			sources = append(sources, check.ScriptRef)
		}
		if check.ResultPath != "" && !doScopeContains(outputScope, check.ResultPath) && !doScopeContains(writeScope, check.ResultPath) {
			return fmt.Errorf("check result %s must be in an explicit output/write scope", check.ResultPath)
		}
	}
	for _, output := range outputScope {
		for _, source := range sources {
			if doScopeContains([]string{output}, source) {
				return fmt.Errorf("output_scope overlaps a declared source file or script")
			}
		}
		for _, write := range writeScope {
			if doScopeContains([]string{output}, write) || doScopeContains([]string{write}, output) {
				return fmt.Errorf("output and source write scopes must not overlap")
			}
		}
	}
	return nil
}

func doReplanRejectRetroactiveScope(root string, session DoSession, writeScope, outputScope []string) error {
	changed, err := runcontrol.InspectWorkspaceDelta(context.Background(), root, session.BaselineJSON)
	if err != nil {
		return err
	}
	for _, p := range changed {
		if doScopeContains(session.WriteScope, p) || doScopeContains(session.OutputScope, p) {
			continue
		}
		if doScopeContains(writeScope, p) || doScopeContains(outputScope, p) {
			return fmt.Errorf("replan cannot retroactively authorize the already changed path %s; claim new scope before writing", p)
		}
	}
	return nil
}

func doReplanClaimScopes(root string, session DoSession, writeScope, outputScope []string) error {
	store, err := runcontrol.OpenForRepository(context.Background(), root)
	if err != nil {
		return err
	}
	defer store.Close()
	work, intents, err := store.GetWork(context.Background(), session.WorkID)
	if err != nil {
		return err
	}
	if work.Fence != session.WorkFence || work.Status != runcontrol.WorkActive || work.TaskRef != "do:"+session.ID {
		return fmt.Errorf("replan scope requires the same active Work owner and fence")
	}
	specs := []runcontrol.WriteIntentSpec{}
	seen := map[string]bool{}
	for _, intent := range intents {
		if intent.Status == runcontrol.WriteIntentActive {
			specs = append(specs, runcontrol.WriteIntentSpec{Path: intent.Path, Operation: intent.Operation, Reason: intent.Reason, Confidence: runcontrol.IntentConfirmed})
			seen[intent.Path] = true
		}
	}
	changed := false
	for _, p := range append(append([]string{}, writeScope...), outputScope...) {
		if !seen[p] {
			seen[p] = true
			changed = true
			specs = append(specs, runcontrol.WriteIntentSpec{Path: p, Operation: runcontrol.WriteModify, Reason: "typed Do replan adds exact operation scope", Confidence: runcontrol.IntentConfirmed})
		}
	}
	if !changed {
		return nil
	}
	_, _, err = store.ClaimWorkIntents(context.Background(), runcontrol.ClaimWorkIntentsParams{WorkID: work.WorkID, ExpectedRevision: work.Revision, Fence: session.WorkFence, Specs: specs})
	return err
}
