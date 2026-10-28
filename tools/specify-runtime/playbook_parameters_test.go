package main

import (
	"encoding/json"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
)

func parameterFixture(t *testing.T) (string, doStartInput) {
	root, input := playbookFixture(t)
	input.Definition.Parameters = map[string]PlaybookParameter{"report": {Kind: "path", Required: true, Example: "out/report.json"}}
	input.Definition.Checks[0].ResultPath = "{{param:report}}"
	input.Parameters = map[string]string{"report": "out/report.json"}
	return root, input
}

func runParameterFixture(t *testing.T, root string, input doStartInput) DoSession {
	t.Helper()
	session, err := doStart(root, input)
	if err != nil {
		t.Fatal(err)
	}
	session = doRecordFixture(t, root, session, "start-run", doRecordEvent{AttemptID: "run-1", TargetID: "run", Kind: "step", Event: "started"})
	started := doNow()
	command := exec.Command("git", "--version")
	command.Dir = root
	output, err := command.CombinedOutput()
	if err != nil {
		t.Fatal(err)
	}
	finished := doNow()
	zero := 0
	session = doRecordFixture(t, root, session, "finish-run", doRecordEvent{AttemptID: "run-1", TargetID: "run", Kind: "step", Event: "completed", Status: "passed", EvidenceOrigin: "agent_tool_observation", ToolCallID: "parameter-real-git", Argv: []string{"git", "--version"}, Cwd: ".", StartedAt: started, FinishedAt: finished, ExitCode: &zero, Summary: strings.TrimSpace(string(output))})
	session = doRecordFixture(t, root, session, "start-report", doRecordEvent{AttemptID: "report-1", TargetID: "report", Kind: "check", Event: "started"})
	started = doNow()
	report := session.Definition.Checks[0].ResultPath
	if err := os.MkdirAll(filepath.Dir(filepath.Join(root, filepath.FromSlash(report))), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, filepath.FromSlash(report)), []byte(`{"ok":true}`), 0o644); err != nil {
		t.Fatal(err)
	}
	session = doRecordFixture(t, root, session, "finish-report", doRecordEvent{AttemptID: "report-1", TargetID: "report", Kind: "check", Event: "completed", Status: "passed", EvidenceOrigin: "agent_tool_observation", ToolCallID: "parameter-real-report-read", Argv: []string{}, Cwd: ".", StartedAt: started, FinishedAt: doNow(), ResultRefs: []DoResultRef{{Path: report, Kind: "json"}}})
	_, digest, err := loadDoSession(root, session.ID)
	if err != nil {
		t.Fatal(err)
	}
	session, err = doFinish(root, session, digest, doFinishInput{ExpectedRevision: session.Revision, KnowledgeStatus: "pending"})
	if err != nil {
		t.Fatal(err)
	}
	return session
}

func TestPlaybookParametersSeparateMethodRevisionAndInstanceEvidence(t *testing.T) {
	root, input := parameterFixture(t)
	first := runParameterFixture(t, root, input)
	if first.TemplateDefinition == nil || first.TemplateDigest == first.DefinitionDigest {
		t.Fatal("template and instance not separately bound")
	}
	publication, err := updatePlaybook(root, PlaybookUpdateRequest{Definition: doMethodDefinition(first), SessionID: first.ID, ChangeSummary: "Verify declared report parameter"})
	if err != nil {
		t.Fatal(err)
	}
	playbookFinishFixture(t, root, first.ID, publication)
	methodID := publication["id"].(string)
	canonical, _ := playbookCanonicalPath(root, methodID)
	before, err := os.ReadFile(canonical)
	if err != nil {
		t.Fatal(err)
	}
	input.SessionID = "second-parameter"
	input.Parameters = map[string]string{"report": "out/另一个报告.json"}
	input.Definition = PlaybookDefinition{}
	input.MethodBinding = &DoMethodBinding{ID: methodID, Revision: 1, ContentDigest: publication["content_digest"].(string)}
	second := runParameterFixture(t, root, input)
	if first.TemplateDigest != second.TemplateDigest || first.DefinitionDigest == second.DefinitionDigest {
		t.Fatal("different values must change only instance digest")
	}
	result, err := updatePlaybook(root, PlaybookUpdateRequest{Definition: doMethodDefinition(second), SessionID: second.ID, BaseDigest: input.MethodBinding.ContentDigest, ChangeSummary: "Reuse the verified template for another report path"})
	if err != nil {
		t.Fatal(err)
	}
	if result["status"] != "no_change" || result["revision"] != 1 {
		t.Fatal(result)
	}
	after, _ := os.ReadFile(canonical)
	if string(before) != string(after) {
		t.Fatal("parameter reuse rewrote method authority")
	}
	playbookFinishFixture(t, root, second.ID, result)
}

func TestPlaybookParametersRejectUnknownMissingUnsafeAndIdentityExpansion(t *testing.T) {
	root, input := parameterFixture(t)
	for _, values := range []map[string]string{{}, {"extra": "out/report.json"}, {"report": "../escape.json"}, {"report": ".specify/do/x"}, {"report": "out/file\n.json"}} {
		if _, _, err := resolvePlaybookDefinition(root, input.Definition, values); err == nil {
			t.Fatalf("accepted invalid bindings %#v", values)
		}
	}
	definition := input.Definition
	definition.Target = "{{param:report}}"
	if _, _, err := resolvePlaybookDefinition(root, definition, input.Parameters); err == nil {
		t.Fatal("identity parameterized")
	}
	definition = input.Definition
	definition.Steps = append([]PlaybookStep{}, definition.Steps...)
	definition.Steps[0].Argv = []string{"pwsh", "-Command", "{{param:report}}"}
	if _, _, err := resolvePlaybookDefinition(root, definition, input.Parameters); err == nil {
		t.Fatal("shell source parameterized")
	}
	definition = input.Definition
	definition.Steps = append([]PlaybookStep{}, definition.Steps...)
	definition.Steps[0].Argv = []string{"git", "--output={{param:report}}"}
	if _, _, err := resolvePlaybookDefinition(root, definition, input.Parameters); err == nil {
		t.Fatal("embedded argv interpolation accepted")
	}
}

func TestPlaybookParametersCannotPublishDifferentTemplateOrBorrowInstance(t *testing.T) {
	root, input := parameterFixture(t)
	session := runParameterFixture(t, root, input)
	changed := doMethodDefinition(session)
	changed.Title = "An unexecuted template title"
	if _, err := updatePlaybook(root, PlaybookUpdateRequest{Definition: changed, SessionID: session.ID, ChangeSummary: "unverified change"}); err == nil {
		t.Fatal("different template used old evidence")
	}
	copy := session
	copy.Parameters = map[string]string{"report": "out/other.json"}
	if err := doVerifyInstanceBinding(root, copy); err == nil {
		t.Fatal("changed values borrowed old execution")
	}
	copy = session
	copy.TemplateDigest = strings.Repeat("0", 64)
	if err := doVerifyInstanceBinding(root, copy); err == nil {
		t.Fatal("changed template digest accepted")
	}
}

func TestPlaybookParameterLegacyDigestAndExactUnicodeArgv(t *testing.T) {
	root, input := playbookFixture(t)
	originalDigest, _ := playbookDefinitionDigest(input.Definition)
	resolved, bindings, err := resolvePlaybookDefinition(root, input.Definition, nil)
	if err != nil {
		t.Fatal(err)
	}
	newDigest, _ := playbookDefinitionDigest(resolved)
	if newDigest != originalDigest || bindings != nil {
		t.Fatal("legacy method changed on resolve")
	}
	input.Definition.Parameters = map[string]PlaybookParameter{"label": {Kind: "string", Required: true, Example: "中文 标签", Pattern: `[^\r\n]+`}}
	input.Definition.Steps[0].Argv = []string{"tool", "{{param:label}}"}
	resolved, _, err = resolvePlaybookDefinition(root, input.Definition, map[string]string{"label": `中文 带"引号`})
	if err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(resolved.Steps[0].Argv, []string{"tool", `中文 带"引号`}) {
		t.Fatal(resolved.Steps[0].Argv)
	}
	raw, _ := json.Marshal(playbookNormalizeDefinition(input.Definition))
	var roundtrip PlaybookDefinition
	if err := json.Unmarshal(raw, &roundtrip); err != nil {
		t.Fatal(err)
	}
	if err := validatePlaybookDefinition(root, roundtrip); err != nil {
		t.Fatal(err)
	}
}

func TestPlaybookParametersPreserveExactJSONAndRejectUnusedSecrets(t *testing.T) {
	root, input := parameterFixture(t)
	input.Definition.Checks[0].ExpectedJSON = json.RawMessage(`9007199254740993`)
	resolved, _, err := resolvePlaybookDefinition(root, input.Definition, input.Parameters)
	if err != nil {
		t.Fatal(err)
	}
	if string(resolved.Checks[0].ExpectedJSON) != "9007199254740993" {
		t.Fatal("integer rounded", string(resolved.Checks[0].ExpectedJSON))
	}
	input.Definition.Parameters["unused"] = PlaybookParameter{Kind: "string", Required: true, Example: "plain", Pattern: ".+"}
	input.Parameters["unused"] = "ghp_abcdefghijklmnopqrstuvwxyz1234567890123456"
	if _, _, err := resolvePlaybookDefinition(root, input.Definition, input.Parameters); err == nil {
		t.Fatal("unused secret persisted")
	}
	parameter := input.Definition.Parameters["unused"]
	parameter.Example = input.Parameters["unused"]
	input.Definition.Parameters["unused"] = parameter
	if err := validatePlaybookDefinition(root, input.Definition); err == nil {
		t.Fatal("secret metadata persisted")
	}
	var decoded PlaybookParameter
	if err := json.Unmarshal([]byte(`{"kind":"path","example":"out/a.json","default":"out/a.json"}`), &decoded); err == nil {
		t.Fatal("parameter required flag missing accepted")
	}
	_, legacy := playbookFixture(t)
	legacy.Definition.Steps[0].Argv = []string{"git", "{{param:unknown}}"}
	if _, _, err := resolvePlaybookDefinition(root, legacy.Definition, nil); err == nil {
		t.Fatal("undeclared parameter token treated as literal")
	}
}

func TestPlaybookParametersPublishedAndUsageInstanceTamperingRejected(t *testing.T) {
	root, input := parameterFixture(t)
	session := runParameterFixture(t, root, input)
	result, err := updatePlaybook(root, PlaybookUpdateRequest{Definition: doMethodDefinition(session), SessionID: session.ID, ChangeSummary: "verify parameter binding"})
	if err != nil {
		t.Fatal(err)
	}
	id := result["id"].(string)
	doc, err := loadPlaybookDocument(root, id)
	if err != nil {
		t.Fatal(err)
	}
	doc.Verification.InstanceDigest = ""
	raw, _ := json.Marshal(doc)
	if _, err := decodePlaybookDocument(root, raw, id, 1); err == nil {
		t.Fatal("published instance binding removed")
	}
	usagePath, _ := playbookStorePath(root, id, "usage/"+session.ID+".json")
	usage, exists, err := readPlaybookUsage(root, id, session.ID)
	if err != nil || !exists {
		t.Fatal(err)
	}
	usage.Verification.Parameters = map[string]string{"report": "out/other.json"}
	raw, _ = json.Marshal(usage)
	if err := os.WriteFile(usagePath, raw, 0o644); err != nil {
		t.Fatal(err)
	}
	if _, _, err := readPlaybookUsage(root, id, session.ID); err == nil {
		t.Fatal("usage parameter tampering accepted")
	}
}
