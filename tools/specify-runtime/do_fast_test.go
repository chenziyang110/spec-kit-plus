package main

import (
	"bytes"
	"encoding/json"
	"io/fs"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
)

func doFastTree(t *testing.T, root string) map[string]string {
	t.Helper()
	result := map[string]string{}
	err := filepath.WalkDir(root, func(file string, entry fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if !entry.IsDir() {
			relative, _ := filepath.Rel(root, file)
			relative = filepath.ToSlash(relative)
			// The existing owner uses SQLite mode=ro/query_only. SQLite may
			// create its transient WAL/shared-memory files even for a view;
			// compare the database and every durable file without altering it.
			if relative == ".specify/runtime/run-control/run-control.sqlite-shm" {
				return nil
			}
			raw, err := os.ReadFile(file)
			if err != nil {
				return err
			}
			if relative == ".specify/runtime/run-control/run-control.sqlite-wal" && len(raw) == 0 {
				return nil
			}
			result[relative] = doBytesDigest(raw)
		}
		return nil
	})
	if err != nil {
		t.Fatal(err)
	}
	return result
}

func doFastTreeChanges(before, after map[string]string) []string {
	changes := []string{}
	for file, digest := range before {
		if after[file] != digest {
			changes = append(changes, file)
		}
	}
	for file := range after {
		if _, ok := before[file]; !ok {
			changes = append(changes, "+"+file)
		}
	}
	return changes
}

func TestDoFastPrepareReadOnlyCanonicalTemplate(t *testing.T) {
	root, input := parameterFixture(t)
	input.Context = map[string]string{"shell": "fixture-shell"}
	input.SourceFiles = []string{"source.txt"}
	input.OutputScope = []string{"out/./"}
	beforeInput := doDigest(input)
	before := doFastTree(t, root)
	data, err := doPrepare(root, input)
	if err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(before, doFastTree(t, root)) || doDigest(input) != beforeInput {
		t.Fatal("prepare changed caller input or workspace")
	}
	prepared := data["start_input"].(doStartInput)
	if prepared.Definition.Checks[0].ResultPath != "{{param:report}}" || len(prepared.SourceFiles) != 0 || prepared.Goal != input.Definition.Goal || !reflect.DeepEqual(prepared.OutputScope, []string{"out"}) {
		t.Fatal("prepare lost canonical template inputs", prepared)
	}
	again, err := doPrepare(root, prepared)
	if err != nil || doDigest(again) != doDigest(data) {
		t.Fatal("prepare is not deterministic", err)
	}
	session, err := doStart(root, prepared)
	if err != nil || session.DefinitionDigest != data["definition_digest"] || session.TemplateDigest != data["method_digest"] {
		t.Fatal("prepared input does not bind the started instance", err)
	}
	before = doFastTree(t, root)
	if _, err := doPrepare(root, prepared); err != nil {
		t.Fatal("matching existing session refused", err)
	}
	prepared.AgentID = "foreign-owner"
	if _, err := doPrepare(root, prepared); err == nil {
		t.Fatal("prepare ignored a foreign owner")
	}
	if !reflect.DeepEqual(before, doFastTree(t, root)) {
		t.Fatal("prepare wrote through its existing-session inspection", doFastTreeChanges(before, doFastTree(t, root)))
	}
}

func TestDoFastPrepareRejectsInvalidInputsWithoutState(t *testing.T) {
	root, input := parameterFixture(t)
	for _, mutate := range []func(*doStartInput){
		func(input *doStartInput) { input.Parameters = map[string]string{"report": "../outside.json"} },
		func(input *doStartInput) { input.OutputScope = []string{".specify/runtime"} },
		func(input *doStartInput) { input.Definition.SourceFiles = []string{"missing.source"} },
		func(input *doStartInput) { input.Context = map[string]string{"arbitrary": "unsupported"} },
		func(input *doStartInput) { input.Goal = "unbound goal" },
	} {
		candidate := input
		mutate(&candidate)
		before := doFastTree(t, root)
		if _, err := doPrepare(root, candidate); err == nil {
			t.Fatal("prepare accepted an invalid start input")
		}
		if !reflect.DeepEqual(before, doFastTree(t, root)) {
			t.Fatal("rejected preparation wrote state")
		}
	}
}

func TestDoFastNextUsesFrozenActionsAndRequiresActualObservations(t *testing.T) {
	root, session := doNativeFixture(t, "file")
	before := doFastTree(t, root)
	data, err := doNext(root, session)
	if err != nil {
		t.Fatal(err)
	}
	ready := data["ready"].([]map[string]any)
	if len(ready) != 1 || ready[0]["target_id"] != "run" || data["complete_ready"] != false {
		t.Fatal(data)
	}
	event := ready[0]["completion_event"].(doRecordEvent)
	if event.NativeAction == nil || event.NativeObservation != nil || event.ToolCallID != "" || event.Status != "" || event.StartedAt != "" || event.FinishedAt != "" || event.ExitCode != nil || len(event.Argv) > 0 || event.Cwd != "" || len(event.ResultRefs) > 0 {
		t.Fatal("next invented observation or process facts", event)
	}
	started := ready[0]["started_input"].(doRecordInput)
	if started.ExpectedRevision != session.Revision || started.Events[0].NativeAction != nil {
		t.Fatal("started input was not executable", started)
	}
	if !reflect.DeepEqual(before, doFastTree(t, root)) {
		t.Fatal("next wrote state", doFastTreeChanges(before, doFastTree(t, root)))
	}
	_, digest, _ := loadDoSession(root, session.ID)
	session, err = doRecord(root, session, digest, started)
	if err != nil {
		t.Fatal(err)
	}
	data, err = doNext(root, session)
	if err != nil || len(data["running"].([]map[string]any)) != 1 || len(data["ready"].([]map[string]any)) != 0 {
		t.Fatal("running action was restarted", data, err)
	}
	_, digest, _ = loadDoSession(root, session.ID)
	if _, err := doRecord(root, session, digest, doRecordInput{ExpectedRevision: session.Revision, RequestID: "missing-real-observation", Events: []doRecordEvent{event}}); err == nil {
		t.Fatal("completion skeleton alone was accepted as execution")
	}
	tampered := session
	tampered.Definition = doReplanCopyDefinition(t, session.Definition)
	tampered.Definition.Steps[0].NativeAction.Tool = "unfrozen.tool"
	if _, err := doNext(root, tampered); err == nil {
		t.Fatal("next accepted an unfrozen caller action")
	}
}

func TestDoFastNextRefreshesStaleDependencyAndExposesCloseout(t *testing.T) {
	root, session := doStartFixture(t)
	session = doRunFixture(t, root, session)
	data, err := doNext(root, session)
	if err != nil || data["complete_ready"] != true || len(data["ready"].([]map[string]any)) != 0 {
		t.Fatal("complete operation has no closeout input", data, err)
	}
	if err := os.WriteFile(filepath.Join(root, "out/report.json"), []byte(`{"ok":false}`), 0o644); err != nil {
		t.Fatal(err)
	}
	data, err = doNext(root, session)
	if err != nil {
		t.Fatal(err)
	}
	ready := data["ready"].([]map[string]any)
	if data["complete_ready"] != false || len(ready) != 1 || ready[0]["target_id"] != "report" {
		t.Fatal("tampered artifact remained accepted", data)
	}
}

func TestDoFastCompleteRequiresExecutionAndIsIdempotent(t *testing.T) {
	root, session := doStartFixture(t)
	before, _ := os.ReadFile(filepath.Join(root, filepath.FromSlash(doSessionRef(session.ID))))
	if _, err := doComplete(root, session.ID, doCompleteInput{ExpectedRevision: session.Revision, ChangeSummary: "Capture verified operation"}); err == nil {
		t.Fatal("complete invented execution")
	}
	after, _ := os.ReadFile(filepath.Join(root, filepath.FromSlash(doSessionRef(session.ID))))
	if string(before) != string(after) {
		t.Fatal("failed complete changed the execution checkpoint")
	}
	session = doRunFixture(t, root, session)
	input := doCompleteInput{ExpectedRevision: session.Revision, ChangeSummary: "Capture verified operation"}
	if _, err := doComplete(root, session.ID, doCompleteInput{ExpectedRevision: session.Revision - 1, ChangeSummary: input.ChangeSummary}); err == nil {
		t.Fatal("fresh closeout ignored revision conflict")
	}
	completed, err := doComplete(root, session.ID, input)
	if err != nil || completed.ExecutionOutcome != "passed" || completed.KnowledgeStatus != "saved" || completed.Knowledge == nil {
		t.Fatal("complete did not save execution and method", completed, err)
	}
	beforeTree := doFastTree(t, root)
	replayed, err := doComplete(root, session.ID, input)
	if err != nil || replayed.Revision != completed.Revision || !reflect.DeepEqual(beforeTree, doFastTree(t, root)) {
		t.Fatal("complete retry duplicated state or usage", err)
	}
	data, err := doNext(root, completed)
	if err != nil || data["terminal"] != true || len(data["ready"].([]map[string]any)) != 0 {
		t.Fatal("saved completion remains executable", data, err)
	}
	for relative := range doFastTree(t, root) {
		if strings.HasPrefix(relative, ".planning/learnings/") || strings.HasPrefix(relative, ".specify/memory/learning") {
			t.Fatal("complete created routine Learning", relative)
		}
	}
	if err := os.WriteFile(filepath.Join(root, "out/report.json"), []byte(`{"ok":false}`), 0o644); err != nil {
		t.Fatal(err)
	}
	if _, err := doComplete(root, session.ID, input); err == nil {
		t.Fatal("idempotent completion bypassed current evidence checks")
	}
	if _, err := doNext(root, completed); err == nil {
		t.Fatal("next presented stale saved evidence as terminal success")
	}
}

func TestDoFastCompleteKnowledgeFailureCanRetryWithoutReexecution(t *testing.T) {
	root, session := doStartFixture(t)
	session = doRunFixture(t, root, session)
	originalAttempts := doDigest(session.Attempts)
	input := doCompleteInput{ExpectedRevision: session.Revision, ChangeSummary: "token=hunter2"}
	if _, err := doComplete(root, session.ID, input); err == nil || !strings.Contains(err.Error(), "knowledge remains pending") {
		t.Fatal("expected bounded knowledge rejection", err)
	}
	pending, _, err := loadDoSession(root, session.ID)
	if err != nil || pending.ExecutionOutcome != "passed" || pending.KnowledgeStatus != "pending" || doDigest(pending.Attempts) != originalAttempts {
		t.Fatal("knowledge failure lost execution", pending, err)
	}
	input.ChangeSummary = "Capture the verified operation after correcting summary"
	completed, err := doComplete(root, session.ID, input)
	if err != nil || completed.KnowledgeStatus != "saved" || doDigest(completed.Attempts) != originalAttempts {
		t.Fatal("knowledge retry required reexecution", completed, err)
	}
}

func TestDoFastCompleteResumesPublishedReceiptAndReusesParameterizedMethod(t *testing.T) {
	root, input := parameterFixture(t)
	first := runParameterFixture(t, root, input)
	publication, err := updatePlaybook(root, PlaybookUpdateRequest{Definition: doMethodDefinition(first), SessionID: first.ID, ChangeSummary: "Publish before simulated interrupted closeout"})
	if err != nil {
		t.Fatal(err)
	}
	usagePath := publication["knowledge_receipt"].(map[string]any)["path"].(string)
	usageBefore, _ := os.ReadFile(filepath.Join(root, filepath.FromSlash(usagePath)))
	completed, err := doComplete(root, first.ID, doCompleteInput{ExpectedRevision: first.Revision, ChangeSummary: "Resume published method closeout"})
	if err != nil || completed.KnowledgeStatus != "saved" {
		t.Fatal(completed, err)
	}
	usageAfter, _ := os.ReadFile(filepath.Join(root, filepath.FromSlash(usagePath)))
	if string(usageBefore) != string(usageAfter) {
		t.Fatal("published usage was duplicated or rewritten")
	}
	document, err := loadPlaybookDocument(root, publication["id"].(string))
	if err != nil || document.Definition.Checks[0].ResultPath != "{{param:report}}" {
		t.Fatal("concrete arguments replaced reusable template", err)
	}
	input.SessionID = "reuse-fast"
	input.Definition = PlaybookDefinition{}
	input.MethodBinding = &DoMethodBinding{ID: document.ID, Revision: document.Revision, ContentDigest: document.ContentDigest}
	input.Parameters = map[string]string{"report": "out/second.json"}
	prepared, err := doPrepare(root, input)
	if err != nil {
		t.Fatal(err)
	}
	second := runParameterFixture(t, root, prepared["start_input"].(doStartInput))
	completed, err = doComplete(root, second.ID, doCompleteInput{ExpectedRevision: second.Revision, ChangeSummary: "Reuse another report path"})
	if err != nil || completed.KnowledgeStatus != "saved" || completed.Knowledge.Revision != document.Revision || completed.TemplateDigest != first.TemplateDigest || completed.DefinitionDigest == first.DefinitionDigest {
		t.Fatal("parameter reuse changed template identity", completed, err)
	}
	var receipt map[string]json.RawMessage
	raw, _ := os.ReadFile(filepath.Join(root, filepath.FromSlash(completed.Knowledge.Path)))
	if err := json.Unmarshal(raw, &receipt); err != nil || len(receipt["verification"]) == 0 {
		t.Fatal("saved usage lacks exact verification", err)
	}
	input.MethodBinding.Revision++
	if _, err := doPrepare(root, input); err == nil {
		t.Fatal("prepare accepted stale method binding")
	}
}

func TestDoFastPublicPrepareStartNextCompleteProtocol(t *testing.T) {
	root, input := doFixture(t)
	input.Definition = playbookNormalizeDefinition(input.Definition)
	raw, _ := json.Marshal(input)
	var output bytes.Buffer
	if code := runDo([]string{"prepare", "--project-root", root, "--input-json", string(raw)}, &output); code != 0 {
		t.Fatalf("prepare: %d %s", code, output.String())
	}
	var envelope struct {
		Data map[string]json.RawMessage `json:"data"`
	}
	if err := json.Unmarshal(output.Bytes(), &envelope); err != nil || len(envelope.Data["start_input"]) == 0 {
		t.Fatal("prepare has no consumable start_input", err)
	}
	output.Reset()
	if code := runDo([]string{"start", "--project-root", root, "--input-json", string(envelope.Data["start_input"])}, &output); code != 0 {
		t.Fatalf("start: %d %s", code, output.String())
	}
	output.Reset()
	if code := runDo([]string{"next", input.SessionID, "--project-root", root}, &output); code != 0 {
		t.Fatalf("next: %d %s", code, output.String())
	}
	if err := json.Unmarshal(output.Bytes(), &envelope); err != nil {
		t.Fatal(err)
	}
	var ready []struct {
		StartedInput doRecordInput `json:"started_input"`
	}
	if err := json.Unmarshal(envelope.Data["ready"], &ready); err != nil || len(ready) != 1 || ready[0].StartedInput.Events[0].TargetID != "run" {
		t.Fatal("public next lacks its started packet", err)
	}
	session, _, err := loadDoSession(root, input.SessionID)
	if err != nil {
		t.Fatal(err)
	}
	session = doRunFixture(t, root, session)
	raw, _ = json.Marshal(doCompleteInput{ExpectedRevision: session.Revision, ChangeSummary: "Capture public fast protocol"})
	output.Reset()
	if code := runDo([]string{"complete", session.ID, "--project-root", root, "--input-json", string(raw)}, &output); code != 0 {
		t.Fatalf("complete: %d %s", code, output.String())
	}
	if !bytes.Contains(output.Bytes(), []byte(`"knowledge_status":"saved"`)) || !bytes.Contains(output.Bytes(), []byte(`"terminal":true`)) {
		t.Fatal("public complete did not save and close", output.String())
	}
}

func TestDoFastNextAndCompleteRejectChangedWorkFence(t *testing.T) {
	root, input := playbookFixture(t)
	session := playbookExecuteFixture(t, root, input)
	_, digest, err := loadDoSession(root, session.ID)
	if err != nil {
		t.Fatal(err)
	}
	session.WorkFence++ // Simulate a detached checkpoint, not Work recovery.
	if err := doWriteSession(root, session, digest, nil); err != nil {
		t.Fatal(err)
	}
	if _, err := doNext(root, session); err == nil {
		t.Fatal("next ignored a changed Work fence")
	}
	if _, err := doComplete(root, session.ID, doCompleteInput{ExpectedRevision: session.Revision, ChangeSummary: "Attempt detached closeout"}); err == nil {
		t.Fatal("complete published through a changed Work fence")
	}
	canonical, _ := playbookCanonicalPath(root, playbookID(session.Definition))
	if _, err := os.Stat(canonical); !os.IsNotExist(err) {
		t.Fatal("fenced completion published a method")
	}
}

func TestDoFastRetryRejectsUnknownAndChangedRecoveryEvidence(t *testing.T) {
	root, session := doNativeFixture(t, "file")
	session = doRecordFixture(t, root, session, "start-unknown", doRecordEvent{AttemptID: "unknown-write", TargetID: "run", Kind: "step", Event: "started"})
	event := doNativeEvent(session, "run", "step", "unknown-write", "unknown-native-call", "interrupted", "unknown", `null`)
	session = doRecordFixture(t, root, session, "complete-unknown", event)
	data, err := doNext(root, session)
	if err != nil || len(data["ready"].([]map[string]any)) != 0 || data["complete_ready"] != false {
		t.Fatal("unknown effect became retry-ready", data, err)
	}
	if err := os.MkdirAll(filepath.Join(root, "out"), 0o755); err != nil {
		t.Fatal(err)
	}
	evidencePath := filepath.Join(root, "out", "inspection.txt")
	evidence := []byte("Observed file tool has settled and output directory has no outstanding write")
	if err := os.WriteFile(evidencePath, evidence, 0o644); err != nil {
		t.Fatal(err)
	}
	_, digest, _ := loadDoSession(root, session.ID)
	session, err = doResume(root, session, digest, doResumeInput{ExpectedRevision: session.Revision, AttemptID: "unknown-write", Recovery: DoRecovery{Reason: "Inspected file state after unknown response", EvidenceRef: "out/inspection.txt", NativeActionSettled: true, SideEffectsInspected: true}})
	if err != nil {
		t.Fatal(err)
	}
	data, err = doNext(root, session)
	if err != nil || len(data["ready"].([]map[string]any)) != 1 {
		t.Fatal("settled action did not become retry-ready", data, err)
	}
	retry := data["ready"].([]map[string]any)[0]["started_input"].(doRecordInput)
	for _, change := range []string{"modify", "delete"} {
		if change == "modify" {
			err = os.WriteFile(evidencePath, []byte("changed inspection evidence"), 0o644)
		} else {
			err = os.Remove(evidencePath)
		}
		if err != nil {
			t.Fatal(err)
		}
		before, _ := os.ReadFile(filepath.Join(root, filepath.FromSlash(doSessionRef(session.ID))))
		data, err := doNext(root, session)
		if err != nil || len(data["ready"].([]map[string]any)) != 0 {
			t.Fatal("changed recovery evidence remained retry-ready", change, data, err)
		}
		var output bytes.Buffer
		raw, _ := json.Marshal(retry)
		if code := runDo([]string{"record", session.ID, "--project-root", root, "--input-json", string(raw)}, &output); code == 0 {
			t.Fatal("public started route accepted stale recovery", change, output.String())
		}
		after, _ := os.ReadFile(filepath.Join(root, filepath.FromSlash(doSessionRef(session.ID))))
		if string(before) != string(after) {
			t.Fatal("rejected recovery retry mutated its session")
		}
		if change == "modify" {
			if err := os.WriteFile(evidencePath, evidence, 0o644); err != nil {
				t.Fatal(err)
			}
		}
	}
}
