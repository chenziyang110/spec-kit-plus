package main

import (
	"bytes"
	"encoding/json"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"runtime"
	"strings"
	"testing"
)

func playbookFixture(t *testing.T) (string, doStartInput) {
	t.Helper()
	root, input := doFixture(t)
	input.Definition.Aliases = []string{"打包", "package the fixture"}
	input.Definition.Applicability = map[string][]string{"os": {runtime.GOOS}, "arch": {runtime.GOARCH}}
	input.Definition = playbookNormalizeDefinition(input.Definition)
	return root, input
}

func playbookExecuteFixture(t *testing.T, root string, input doStartInput) DoSession {
	t.Helper()
	session, err := doStart(root, input)
	if err != nil {
		t.Fatal(err)
	}
	session = doRunFixture(t, root, session)
	_, oldDigest, err := loadDoSession(root, session.ID)
	if err != nil {
		t.Fatal(err)
	}
	session, err = doFinish(root, session, oldDigest, doFinishInput{ExpectedRevision: session.Revision, KnowledgeStatus: "pending"})
	if err != nil {
		t.Fatal(err)
	}
	return session
}

func playbookPublishFixture(t *testing.T, root string, session DoSession, baseDigest string) map[string]any {
	t.Helper()
	result, err := updatePlaybook(root, PlaybookUpdateRequest{BaseDigest: baseDigest, Definition: session.Definition, SessionID: session.ID, ChangeSummary: "Capture the verified local operation"})
	if err != nil {
		t.Fatal(err)
	}
	return result
}

func playbookFinishFixture(t *testing.T, root string, sessionID string, result map[string]any) {
	t.Helper()
	session, digest, err := loadDoSession(root, sessionID)
	if err != nil {
		t.Fatal(err)
	}
	raw, _ := json.Marshal(result["knowledge_receipt"])
	var knowledge DoKnowledgeReceipt
	if err := json.Unmarshal(raw, &knowledge); err != nil {
		t.Fatal(err)
	}
	finished, err := doFinish(root, session, digest, doFinishInput{ExpectedRevision: session.Revision, KnowledgeStatus: "saved", Knowledge: &knowledge})
	if err != nil {
		t.Fatal(err)
	}
	if finished.ExecutionOutcome != "passed" || finished.KnowledgeStatus != "saved" {
		t.Fatal(finished)
	}
}

func TestPlaybookUnverifiedProposalNeverCreatesCurrentAuthority(t *testing.T) {
	root, input := playbookFixture(t)
	request := PlaybookUpdateRequest{Definition: input.Definition, ChangeSummary: "Propose a reusable operation"}
	result, err := updatePlaybook(root, request)
	if err != nil {
		t.Fatal(err)
	}
	if result["status"] != "proposed" {
		t.Fatal(result)
	}
	id := result["id"].(string)
	if _, err := loadPlaybookDocument(root, id); !os.IsNotExist(err) {
		t.Fatalf("proposal published current authority: %v", err)
	}
	show, err := showPlaybook(root, id, "all", "", result["proposal_digest"].(string))
	if err != nil || show["status"] != "proposed" || show["claim_ready"] != false {
		t.Fatalf("proposal show = %#v, %v", show, err)
	}
	second, err := updatePlaybook(root, request)
	if err != nil || second["status"] != "proposal_exists" {
		t.Fatalf("proposal repeated = %#v, %v", second, err)
	}
	if len(second["changed_paths"].([]string)) != 0 {
		t.Fatal("duplicate proposal wrote new files")
	}
	request.Definition.Goal = "Reuse the candidate after a future verified execution"
	latest, err := updatePlaybook(root, request)
	if err != nil {
		t.Fatal(err)
	}
	before := playbookSnapshotFiles(t, filepath.Join(root, ".specify", "playbooks"))
	found, err := findPlaybooks(root, []string{"--query", "打包"})
	if err != nil {
		t.Fatal(err)
	}
	items := found["items"].([]map[string]any)
	if len(items) != 1 || items[0]["id"] != id || items[0]["status"] != "proposed" || items[0]["revision"] != 0 || items[0]["source_status"] != "unverified" || items[0]["requires_revalidation"] != true {
		t.Fatalf("unverified recall = %#v", found)
	}
	if items[0]["proposal_digest"] != latest["proposal_digest"] || !reflect.DeepEqual(items[0]["show_argv"], latest["show_argv"]) {
		t.Fatalf("proposal recall is not pinned to its latest candidate: %#v", items[0])
	}
	if !reflect.DeepEqual(before, playbookSnapshotFiles(t, filepath.Join(root, ".specify", "playbooks"))) {
		t.Fatal("proposal recall mutated stored candidates")
	}
}

func TestPlaybookVerifiedPublicationRecallAndReadOnlyDisclosure(t *testing.T) {
	root, input := playbookFixture(t)
	if _, err := updatePlaybook(root, PlaybookUpdateRequest{Definition: input.Definition, ChangeSummary: "Initial candidate"}); err != nil {
		t.Fatal(err)
	}
	session := playbookExecuteFixture(t, root, input)
	result := playbookPublishFixture(t, root, session, "")
	if result["status"] != "created" || result["provenance"] != "agent_tool_observation" || result["claim_ready"] != false {
		t.Fatal(result)
	}
	id := result["id"].(string)
	document, err := loadPlaybookDocument(root, id)
	if err != nil {
		t.Fatal(err)
	}
	if document.Revision != 1 || document.Verification.SessionID != session.ID {
		t.Fatal(document)
	}
	canonical, _ := playbookCanonicalPath(root, id)
	before, _ := os.ReadFile(canonical)
	history, _ := playbookStorePath(root, id, "revisions/000001.json")
	historical, _ := os.ReadFile(history)
	if !bytes.Equal(before, historical) {
		t.Fatal("immutable revision differs from published bytes")
	}
	markdownPath, _ := playbookStorePath(root, id, "PLAYBOOK.md")
	markdown, _ := os.ReadFile(markdownPath)
	if !bytes.Contains(markdown, []byte(document.ContentDigest)) || !bytes.Contains(markdown, []byte("Generated from playbook.json")) {
		t.Fatal("Markdown does not identify its canonical source")
	}
	filesBefore := playbookSnapshotFiles(t, filepath.Join(root, ".specify", "playbooks"))
	found, err := findPlaybooks(root, []string{"--query", "帮我打包"})
	if err != nil {
		t.Fatal(err)
	}
	items := found["items"].([]map[string]any)
	if len(items) != 1 || items[0]["id"] != id || items[0]["status"] != "verified" {
		t.Fatalf("alias recall = %#v", found)
	}
	if !reflect.DeepEqual(items[0]["show_argv"], playbookShowArgv(id, "summary", 1, "")) {
		t.Fatal("recall did not pin the exact revision")
	}
	if _, ok := items[0]["steps"]; ok {
		t.Fatal("find eagerly expanded steps")
	}
	summary, err := showPlaybook(root, id, "summary", "", "")
	if err != nil {
		t.Fatal(err)
	}
	if _, ok := summary["definition"]; ok {
		t.Fatal("summary eagerly disclosed full method")
	}
	if summary["expand_argv"] == nil {
		t.Fatal("summary missing exact expansion routes")
	}
	if !reflect.DeepEqual(summary["expand_argv"].(map[string][]string)["all"], playbookShowArgv(id, "all", 1, "")) {
		t.Fatal("expansion did not pin the exact revision")
	}
	expanded, err := showPlaybook(root, id, "steps", "", "")
	if err != nil || len(expanded["steps"].([]PlaybookStep)) != 1 {
		t.Fatalf("steps = %#v, %v", expanded, err)
	}
	validation, err := validatePlaybookInput(root, []string{"--id", id})
	if err != nil || validation["execution_verified"] != false {
		t.Fatalf("validation asserted execution: %#v, %v", validation, err)
	}
	if !reflect.DeepEqual(filesBefore, playbookSnapshotFiles(t, filepath.Join(root, ".specify", "playbooks"))) {
		t.Fatal("read operations mutated method state")
	}
	playbookFinishFixture(t, root, session.ID, result)
}

func TestPlaybookRepeatedExecutionIsIdempotentAndDoesNotReviseMethod(t *testing.T) {
	root, input := playbookFixture(t)
	first := playbookExecuteFixture(t, root, input)
	result := playbookPublishFixture(t, root, first, "")
	id := result["id"].(string)
	document, _ := loadPlaybookDocument(root, id)
	canonical, _ := playbookCanonicalPath(root, id)
	before, _ := os.ReadFile(canonical)
	replayed := playbookPublishFixture(t, root, first, "")
	if replayed["status"] != "already_recorded" {
		t.Fatal(replayed)
	}
	playbookFinishFixture(t, root, first.ID, replayed)
	input.SessionID = "repeat"
	input.MethodBinding = &DoMethodBinding{ID: id, Revision: document.Revision, ContentDigest: document.ContentDigest}
	second := playbookExecuteFixture(t, root, input)
	secondResult := playbookPublishFixture(t, root, second, document.ContentDigest)
	if secondResult["status"] != "no_change" || secondResult["revision"] != 1 {
		t.Fatal(secondResult)
	}
	after, _ := os.ReadFile(canonical)
	if !bytes.Equal(before, after) {
		t.Fatal("successful reuse rewrote the method")
	}
	usage := playbookUsageSummary(root, document)
	if usage["verified_sessions"] != 2 {
		t.Fatal(usage)
	}
	playbookFinishFixture(t, root, second.ID, secondResult)
	// A later improvement keeps the same method identity but must execute its
	// exact stronger acceptance definition before becoming the next revision.
	input.SessionID = "improved"
	input.Definition = playbookNormalizeDefinition(input.Definition)
	input.Definition.Checks[0].JSONPointer = ""
	input.Definition.Checks[0].ExpectedJSON = json.RawMessage(`{"ok":true}`)
	input.Definition.Checks[0].ExpectedResult = "the complete report equals the accepted result"
	third := playbookExecuteFixture(t, root, input)
	thirdResult := playbookPublishFixture(t, root, third, document.ContentDigest)
	if thirdResult["status"] != "updated" || thirdResult["revision"] != 2 || thirdResult["id"] != id {
		t.Fatalf("third execution did not evolve the same method: %#v", thirdResult)
	}
	oldRevision, err := loadPlaybookRevision(root, id, 1)
	if err != nil || oldRevision.ContentDigest != document.ContentDigest {
		t.Fatalf("method evolution lost the old revision: %v", err)
	}
	for _, prior := range []DoSession{first, second} {
		if _, found, err := readPlaybookUsage(root, id, prior.ID); err != nil || !found {
			t.Fatalf("method evolution lost the prior session receipt: %s %v", prior.ID, err)
		}
	}
	playbookFinishFixture(t, root, third.ID, thirdResult)
	priorSession, _, err := loadDoSession(root, first.ID)
	if err != nil || priorSession.Knowledge == nil {
		t.Fatalf("old session receipt unavailable: %v", err)
	}
	if err := doVerifyKnowledge(root, priorSession, *priorSession.Knowledge); err != nil {
		t.Fatalf("new current revision invalidated a correctly pinned historical receipt: %v", err)
	}
}

func TestPlaybookRevisionCASAndImmutableHistory(t *testing.T) {
	root, input := playbookFixture(t)
	first := playbookExecuteFixture(t, root, input)
	result := playbookPublishFixture(t, root, first, "")
	id := result["id"].(string)
	document, _ := loadPlaybookDocument(root, id)
	playbookFinishFixture(t, root, first.ID, result)
	oldHistory, _ := playbookStorePath(root, id, "revisions/000001.json")
	oldBytes, _ := os.ReadFile(oldHistory)
	changed := input.Definition
	changed.Title = "A clearer title for the verified operation"
	if playbookID(changed) != id {
		t.Fatal("editorial change created a new method identity")
	}
	_, err := updatePlaybook(root, PlaybookUpdateRequest{Definition: changed, BaseDigest: strings.Repeat("0", 64), ChangeSummary: "Improve the title"})
	if err == nil || !strings.Contains(err.Error(), "revision_conflict") {
		t.Fatalf("missing stale-base rejection: %v", err)
	}
	candidate, err := updatePlaybook(root, PlaybookUpdateRequest{Definition: changed, BaseDigest: document.ContentDigest, ChangeSummary: "Candidate improvement still requires a new execution"})
	if err != nil || candidate["status"] != "proposed" {
		t.Fatalf("candidate improvement = %#v %v", candidate, err)
	}
	summary, err := showPlaybook(root, id, "summary", "", "")
	if err != nil {
		t.Fatal(err)
	}
	pending, ok := summary["pending_proposal"].(map[string]any)
	if !ok || pending["proposal_digest"] != candidate["proposal_digest"] || pending["verification_required"] != true {
		t.Fatalf("current summary hid the next verifiable improvement: %#v", summary)
	}
	if _, ok := pending["definition"]; ok {
		t.Fatal("candidate summary eagerly expanded an unverified definition")
	}
	input.SessionID = "revised"
	input.Definition = changed
	input.MethodBinding = &DoMethodBinding{ID: id, Revision: document.Revision, ContentDigest: document.ContentDigest}
	second := playbookExecuteFixture(t, root, input)
	updated := playbookPublishFixture(t, root, second, document.ContentDigest)
	if updated["revision"] != 2 || updated["status"] != "updated" {
		t.Fatal(updated)
	}
	newOldBytes, _ := os.ReadFile(oldHistory)
	if !bytes.Equal(oldBytes, newOldBytes) {
		t.Fatal("new revision overwrote historical evidence")
	}
	old, err := showPlaybook(root, id, "all", "1", "")
	if err != nil || old["definition"].(PlaybookDefinition).Title != document.Definition.Title {
		t.Fatalf("old revision = %#v %v", old, err)
	}
	currentSummary, err := showPlaybook(root, id, "summary", "", "")
	if err != nil {
		t.Fatal(err)
	}
	if _, ok := currentSummary["pending_proposal"]; ok {
		t.Fatal("an old-base proposal was advertised for the new current revision")
	}
	playbookFinishFixture(t, root, second.ID, updated)
}

func TestPlaybookHardApplicabilityAndSourceChangeRequireLiveEvidence(t *testing.T) {
	root, input := playbookFixture(t)
	session := playbookExecuteFixture(t, root, input)
	result := playbookPublishFixture(t, root, session, "")
	id := result["id"].(string)
	document, _ := loadPlaybookDocument(root, id)
	otherOS := "windows"
	if runtime.GOOS == otherOS {
		otherOS = "linux"
	}
	contextRaw, _ := json.Marshal(map[string]string{"os": otherOS})
	found, err := findPlaybooks(root, []string{"--query", "打包", "--context-json", string(contextRaw)})
	if err != nil || len(found["items"].([]map[string]any)) != 0 || found["excluded_by_applicability"] != 1 {
		t.Fatalf("wrong environment selected: %#v %v", found, err)
	}
	if err := os.WriteFile(filepath.Join(root, "source.txt"), []byte("changed source\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	if status := playbookSourceStatus(root, document); status != "changed" {
		t.Fatalf("source status=%s", status)
	}
	found, err = findPlaybooks(root, []string{"--query", "打包"})
	if err != nil {
		t.Fatal(err)
	}
	card := found["items"].([]map[string]any)[0]
	if card["requires_revalidation"] != true || card["source_status"] != "changed" {
		t.Fatal(card)
	}
	// The old run cannot authorize a different method simply because its summary
	// says success; its definition and source evidence are pinned independently.
	changed := input.Definition
	changed.Title = "Changed title after execution"
	_, err = updatePlaybook(root, PlaybookUpdateRequest{Definition: changed, BaseDigest: document.ContentDigest, SessionID: session.ID, ChangeSummary: "Try to reuse old success"})
	if err == nil {
		t.Fatal("accepted old session evidence for unexecuted method")
	}
}

func TestPlaybookCannotPublishFromNarrationOrSourceChangedAfterRun(t *testing.T) {
	root, input := playbookFixture(t)
	_, err := updatePlaybook(root, PlaybookUpdateRequest{Definition: input.Definition, SessionID: "fake-passed-session", ChangeSummary: "This supposedly passed"})
	if err == nil {
		t.Fatal("accepted a fake execution receipt")
	}
	session, err := doStart(root, input)
	if err != nil {
		t.Fatal(err)
	}
	_, err = updatePlaybook(root, PlaybookUpdateRequest{Definition: input.Definition, SessionID: session.ID, ChangeSummary: "Publish before actual execution"})
	if err == nil {
		t.Fatal("accepted an unexecuted active session")
	}
	session = doRunFixture(t, root, session)
	_, digest, _ := loadDoSession(root, session.ID)
	session, err = doFinish(root, session, digest, doFinishInput{ExpectedRevision: session.Revision, KnowledgeStatus: "pending"})
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "source.txt"), []byte("new source after checks\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	_, err = updatePlaybook(root, PlaybookUpdateRequest{Definition: input.Definition, SessionID: session.ID, ChangeSummary: "Publish old checks"})
	if err == nil {
		t.Fatal("source mutation after verification accepted")
	}
	if _, err := loadPlaybookDocument(root, playbookID(input.Definition)); !os.IsNotExist(err) {
		t.Fatalf("failed publication created current method: %v", err)
	}
}

func TestPlaybookSchemaRejectsUnknownDuplicateUnorderedAndAllOptional(t *testing.T) {
	root, input := playbookFixture(t)
	raw, _ := json.Marshal(input.Definition)
	for _, invalid := range []string{string(raw[:len(raw)-1]) + `,"unknown":true}`, string(raw[:len(raw)-1]) + `,"operation":"build"}`, string(raw) + ` {}`} {
		var definition PlaybookDefinition
		if decodePlaybookJSON([]byte(invalid), &definition) == nil {
			t.Fatal("accepted ambiguous or unknown JSON fields")
		}
	}
	definition := playbookNormalizeDefinition(input.Definition)
	definition.Steps[0].DependsOn = []string{"report"}
	if validatePlaybookDefinition(root, definition) == nil {
		t.Fatal("accepted forward dependency/cycle")
	}
	definition = playbookNormalizeDefinition(input.Definition)
	definition.Checks[0].Required = false
	if validatePlaybookDefinition(root, definition) == nil {
		t.Fatal("accepted all optional verification")
	}
	definition = playbookNormalizeDefinition(input.Definition)
	definition.Checks[0].Kind = "junit"
	definition.Checks[0].ExpectedJSON = nil
	definition.Checks[0].JSONPointer = ""
	definition.Checks[0].MinCases = 0
	if validatePlaybookDefinition(root, definition) == nil {
		t.Fatal("accepted zero-test JUnit success contract")
	}
	firstDigest, _ := playbookDefinitionDigest(input.Definition)
	definition = playbookNormalizeDefinition(input.Definition)
	definition.Steps[0].Argv = []string{"git", "version", "--build-options"}
	secondDigest, _ := playbookDefinitionDigest(definition)
	if firstDigest == secondDigest {
		t.Fatal("changed argv did not invalidate frozen definition")
	}
}

func TestPlaybookSensitiveInputIsRejectedWithoutMutatingExecutableBindings(t *testing.T) {
	root, input := playbookFixture(t)
	for _, argv := range [][]string{{"tool", "--token", "literal-value"}, {"tool", "--token=literal-value"}, {"tool", "ghp_AbcDef1234567890InjectedCredential"}} {
		definition := playbookNormalizeDefinition(input.Definition)
		definition.Steps[0].Argv = argv
		if _, err := updatePlaybook(root, PlaybookUpdateRequest{Definition: definition, ChangeSummary: "Propose method"}); err == nil {
			t.Fatal("accepted sensitive executable content")
		}
	}
	if _, err := os.Stat(filepath.Join(root, ".specify/playbooks")); !os.IsNotExist(err) {
		t.Fatal("rejected secret input wrote method storage")
	}
	definition := playbookNormalizeDefinition(input.Definition)
	definition.Steps[0].Argv = []string{"tool", "--token", "${BUILD_TOKEN}"}
	if err := validatePlaybookDefinition(root, definition); err != nil {
		t.Fatalf("safe binding rejected: %v", err)
	}
	if definition.Steps[0].Argv[2] != "${BUILD_TOKEN}" {
		t.Fatal("sanitizer rewrote executable argv")
	}
}

func TestPlaybookProjectPathsCannotEscapeOrTraverseLinks(t *testing.T) {
	root, input := playbookFixture(t)
	for _, source := range []string{"../source.txt", "/etc/passwd", `C:\Users\person\file`, ".git/config", ".specify/playbooks/another/playbook.json", ".env"} {
		definition := playbookNormalizeDefinition(input.Definition)
		definition.SourceFiles = []string{source}
		if validatePlaybookDefinition(root, definition) == nil {
			t.Fatalf("accepted unsafe source path %q", source)
		}
	}
	outside := t.TempDir()
	if err := os.Symlink(outside, filepath.Join(root, "linked")); err != nil {
		t.Skipf("symlinks unavailable: %v", err)
	}
	definition := playbookNormalizeDefinition(input.Definition)
	definition.SourceFiles = []string{"linked/source.txt"}
	if validatePlaybookDefinition(root, definition) == nil {
		t.Fatal("accepted symlink source traversal")
	}
	if err := os.MkdirAll(filepath.Join(root, ".specify/playbooks"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(outside, filepath.Join(root, ".specify/playbooks", playbookID(input.Definition))); err != nil {
		t.Fatal(err)
	}
	if _, err := updatePlaybook(root, PlaybookUpdateRequest{Definition: input.Definition, ChangeSummary: "Propose safe method"}); err == nil {
		t.Fatal("wrote through a linked method directory")
	}
}

func TestPlaybookEmptyRecallAndValidationDoNotCreateStorage(t *testing.T) {
	root, input := playbookFixture(t)
	var output bytes.Buffer
	if code := runPlaybook([]string{"find", "--query", "打包", "--project-root", root, "--format", "json"}, &output); code != 0 {
		t.Fatalf("%d %s", code, output.String())
	}
	raw, _ := json.Marshal(input.Definition)
	output.Reset()
	if code := runPlaybook([]string{"validate", "--input-json", string(raw), "--project-root", root, "--format", "json"}, &output); code != 0 {
		t.Fatalf("%d %s", code, output.String())
	}
	if _, err := os.Stat(filepath.Join(root, ".specify/playbooks")); !os.IsNotExist(err) {
		t.Fatal("read-only command created method storage")
	}
}

func TestPlaybookDerivedIndexCannotHideCanonicalMethods(t *testing.T) {
	root, input := playbookFixture(t)
	session := playbookExecuteFixture(t, root, input)
	result := playbookPublishFixture(t, root, session, "")
	index := filepath.Join(root, ".specify/playbooks/index.json")
	if err := os.WriteFile(index, []byte(`{"schema_version":1,"derived":true,"entries":[]}`), 0o644); err != nil {
		t.Fatal(err)
	}
	found, err := findPlaybooks(root, []string{"--query", "打包"})
	if err != nil || len(found["items"].([]map[string]any)) != 1 {
		t.Fatalf("index became authority: %#v %v", found, err)
	}
	if found["items"].([]map[string]any)[0]["id"] != result["id"] {
		t.Fatal(found)
	}
}

func TestPlaybookPublishedSchemasMatchRuntime(t *testing.T) {
	for filename, schema := range map[string]map[string]any{"playbook-definition.schema.json": playbookDefinitionInputSchema(), "playbook-update.schema.json": playbookUpdateInputSchema()} {
		raw, err := os.ReadFile(filepath.Join("..", "..", "templates", "artifacts", filename))
		if err != nil {
			t.Fatal(err)
		}
		var actual, expected any
		if err := json.Unmarshal(raw, &actual); err != nil {
			t.Fatal(err)
		}
		encoded, _ := json.Marshal(schema)
		_ = json.Unmarshal(encoded, &expected)
		if !reflect.DeepEqual(actual, expected) {
			t.Fatalf("published %s drifted from runtime input contract", filename)
		}
	}
}

func TestPlaybookCorruptCurrentCannotFallBackToProposal(t *testing.T) {
	root, input := playbookFixture(t)
	result, err := updatePlaybook(root, PlaybookUpdateRequest{Definition: input.Definition, ChangeSummary: "Initial candidate"})
	if err != nil {
		t.Fatal(err)
	}
	canonical, _ := playbookCanonicalPath(root, result["id"].(string))
	if err := os.WriteFile(canonical, []byte("{}\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	found, err := findPlaybooks(root, []string{"--query", "打包"})
	if err != nil {
		t.Fatal(err)
	}
	if len(found["items"].([]map[string]any)) != 0 || len(found["warnings"].([]string)) == 0 {
		t.Fatalf("corrupt current became an unverified fallback: %#v", found)
	}
}

func TestPlaybookCLIConsumesBoundedStdinAndDoesNotCreateAuthoringFiles(t *testing.T) {
	root, input := playbookFixture(t)
	for _, command := range []string{"validate", "update"} {
		var value any = input.Definition
		if command == "update" {
			value = PlaybookUpdateRequest{Definition: input.Definition, ChangeSummary: "Candidate from structured stdin"}
		}
		raw, err := playbookMarshal(value)
		if err != nil {
			t.Fatal(err)
		}
		path := filepath.Join(t.TempDir(), "stdin.json")
		if err := os.WriteFile(path, raw, 0o600); err != nil {
			t.Fatal(err)
		}
		file, err := os.Open(path)
		if err != nil {
			t.Fatal(err)
		}
		previous := os.Stdin
		os.Stdin = file
		var output bytes.Buffer
		code := runPlaybook([]string{command, "--project-root", root, "--input-json", "-", "--format", "json"}, &output)
		os.Stdin = previous
		file.Close()
		if code != 0 {
			t.Fatalf("%s stdin failed: %s", command, output.String())
		}
		if _, err := os.Stat(filepath.Join(root, "-")); !os.IsNotExist(err) {
			t.Fatal("stdin was treated as an authoring path")
		}
	}
}

func TestPlaybookCLIResolvesRelativeRootForSessionOwnedSourceScope(t *testing.T) {
	root, input := playbookFixture(t)
	input.WriteScope = []string{"source.txt"}
	session := playbookExecuteFixture(t, root, input)
	previous, err := os.Getwd()
	if err != nil {
		t.Fatal(err)
	}
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() {
		if err := os.Chdir(previous); err != nil {
			t.Error(err)
		}
	})
	raw, _ := playbookMarshal(PlaybookUpdateRequest{Definition: session.Definition, SessionID: session.ID, ChangeSummary: "Capture from the default project root"})
	var output bytes.Buffer
	if code := runPlaybook([]string{"update", "--input-json", string(raw)}, &output); code != 0 {
		t.Fatalf("default-root publication failed: %s", output.String())
	}
	var env Envelope
	if err := json.Unmarshal(output.Bytes(), &env); err != nil {
		t.Fatal(err)
	}
	if env.Data["status"] != "created" {
		t.Fatal(output.String())
	}
	playbookFinishFixture(t, root, session.ID, env.Data)
}

func TestPlaybookFailedAndBlockedSessionCanPreserveOnlyAnUnverifiedProposal(t *testing.T) {
	root, input := playbookFixture(t)
	input.Definition.Steps[0].Argv = []string{"git", "--spec-kit-test-invalid-option"}
	session, err := doStart(root, input)
	if err != nil {
		t.Fatal(err)
	}
	session = doRecordFixture(t, root, session, "start-failing-command", doRecordEvent{AttemptID: "run-1", TargetID: "run", Kind: "step", Event: "started"})
	started := doNow()
	command := exec.Command(input.Definition.Steps[0].Argv[0], input.Definition.Steps[0].Argv[1:]...)
	command.Dir = root
	output, executionError := command.CombinedOutput()
	exit, ok := executionError.(*exec.ExitError)
	if !ok {
		t.Fatalf("failure fixture did not fail as expected: %v", executionError)
	}
	code := exit.ExitCode()
	session = doRecordFixture(t, root, session, "complete-failing-command", doRecordEvent{AttemptID: "run-1", TargetID: "run", Kind: "step", Event: "completed", Status: "failed", EvidenceOrigin: "agent_tool_observation", ToolCallID: "actual-invalid-git-option", Argv: input.Definition.Steps[0].Argv, Cwd: ".", StartedAt: started, FinishedAt: doNow(), ExitCode: &code, Summary: strings.TrimSpace(string(output))})
	candidate := playbookNormalizeDefinition(session.Definition)
	candidate.Steps[0].Argv = []string{"git", "--version"}
	request := PlaybookUpdateRequest{Definition: candidate, SessionID: session.ID, ChangeSummary: "Candidate fix still needs execution", ProposalOnly: true}
	result, err := updatePlaybook(root, request)
	if err != nil || result["status"] != "proposed" {
		t.Fatalf("failed execution could not retain an unverified candidate: %#v %v", result, err)
	}
	if _, err := loadPlaybookDocument(root, result["id"].(string)); !os.IsNotExist(err) {
		t.Fatalf("failed execution published current: %v", err)
	}
	request.ProposalOnly = false
	if _, err := updatePlaybook(root, request); err == nil {
		t.Fatal("a failure proposal weakened the verified publication gate")
	}
	session, digest, err := loadDoSession(root, session.ID)
	if err != nil {
		t.Fatal(err)
	}
	if strings.Contains(strings.Join(doValidate(root, session, true).Blockers, " "), "unclaimed changed path") {
		t.Fatal("proposal metadata became an unclaimed source mutation")
	}
	if err := os.MkdirAll(filepath.Join(root, "out"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "out/access.txt"), []byte("dependency access is unavailable; external owner must restore access\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	blocker := DoBlocker{Owner: "external", Category: "dependency", Cause: "dependency access unavailable", NextAction: "external owner restores access", UnblockCriteria: "fresh access check succeeds", ResumePoint: "run", AttemptedRecovery: []string{"checked current access response"}, EvidenceRefs: []string{"out/access.txt"}}
	session, err = doFinish(root, session, digest, doFinishInput{ExpectedRevision: session.Revision, Blocker: &blocker})
	if err != nil {
		t.Fatal(err)
	}
	request.ProposalOnly = true
	request.Definition.Title = "Candidate retained while external access is blocked"
	blockedProposal, err := updatePlaybook(root, request)
	if err != nil || blockedProposal["status"] != "proposed" {
		t.Fatalf("blocked execution could not retain its candidate: %#v %v", blockedProposal, err)
	}
	if _, err := loadPlaybookDocument(root, result["id"].(string)); !os.IsNotExist(err) {
		t.Fatalf("blocked execution published current: %v", err)
	}
}

func TestPlaybookSavedKnowledgeReceiptIsRevalidatedOnCompletionReplay(t *testing.T) {
	root, input := playbookFixture(t)
	session := playbookExecuteFixture(t, root, input)
	result := playbookPublishFixture(t, root, session, "")
	playbookFinishFixture(t, root, session.ID, result)
	session, sessionDigest, err := loadDoSession(root, session.ID)
	if err != nil || session.Knowledge == nil {
		t.Fatalf("saved session unavailable: %v", err)
	}
	usagePath := filepath.Join(root, filepath.FromSlash(session.Knowledge.Path))
	original, err := os.ReadFile(usagePath)
	if err != nil {
		t.Fatal(err)
	}
	for _, mutation := range []string{"changed", "missing"} {
		if mutation == "changed" {
			err = os.WriteFile(usagePath, append(append([]byte{}, original...), ' '), 0o644)
		} else {
			err = os.Remove(usagePath)
		}
		if err != nil {
			t.Fatal(err)
		}
		_, err = doFinish(root, session, sessionDigest, doFinishInput{ExpectedRevision: session.Revision, KnowledgeStatus: "saved", Knowledge: session.Knowledge})
		if err == nil {
			t.Fatalf("completion replay accepted %s usage receipt", mutation)
		}
		if err := os.WriteFile(usagePath, original, 0o644); err != nil {
			t.Fatal(err)
		}
	}
	if _, err := doFinish(root, session, sessionDigest, doFinishInput{ExpectedRevision: session.Revision, KnowledgeStatus: "saved", Knowledge: session.Knowledge}); err != nil {
		t.Fatalf("exact receipt restoration did not recover idempotent completion: %v", err)
	}
}

func TestPlaybookSourceWritesAreExplicitLocalScopeAndPartOfTheMethodDigest(t *testing.T) {
	root, input := playbookFixture(t)
	original := input.Definition
	originalDigest, _ := playbookDefinitionDigest(original)
	changed := playbookNormalizeDefinition(original)
	changed.Steps[0].SideEffect = "local_write"
	changed.Steps[0].SourceWrites = []string{"source.txt", "generated"}
	if err := validatePlaybookDefinition(root, changed); err != nil {
		t.Fatalf("bounded source write rejected: %v", err)
	}
	changedDigest, _ := playbookDefinitionDigest(changed)
	if changedDigest == originalDigest || playbookID(changed) != playbookID(original) {
		t.Fatal("source write permission must alter the definition digest, not stable method identity")
	}
	for _, invalid := range []struct{ effect, target string }{{"read", "source.txt"}, {"external_mutation", "source.txt"}, {"local_write", "."}, {"local_write", "../escape"}, {"local_write", "generated/**"}, {"local_write", ".specify/config.json"}, {"local_write", ".planning/learnings/index.json"}} {
		definition := playbookNormalizeDefinition(changed)
		definition.Steps[0].SideEffect = invalid.effect
		definition.Steps[0].SourceWrites = []string{invalid.target}
		if err := validatePlaybookDefinition(root, definition); err == nil {
			t.Fatalf("invalid source write scope accepted: %#v", invalid)
		}
	}
	raw, _ := json.Marshal(changed)
	var fields map[string]any
	_ = json.Unmarshal(raw, &fields)
	fields["checks"].([]any)[0].(map[string]any)["source_writes"] = []string{"source.txt"}
	raw, _ = json.Marshal(fields)
	var parsed PlaybookDefinition
	if err := decodePlaybookJSON(raw, &parsed); err == nil {
		t.Fatal("a verification check acquired source mutation authority")
	}
}

func TestPlaybookSourceMutationPublishesOnlyAfterFinalChecksAndCognitionCloseout(t *testing.T) {
	root, _, session := doSourceMutationFixture(t)
	request := PlaybookUpdateRequest{Definition: session.Definition, SessionID: session.ID, ChangeSummary: "Preserve the verified source generation operation"}
	if _, err := updatePlaybook(root, request); err == nil {
		t.Fatal("source mutation published before execution and cognition closeout")
	}
	validation := doValidate(root, session, true)
	if validation.CognitionCloseout != "required" || len(validation.ChangedSourcePaths) != 2 {
		t.Fatalf("source mutation did not expose its exact cognition scope: %#v", validation)
	}
	scope := filepath.Dir(filepath.Join(root, filepath.FromSlash(doSessionRef(session.ID))))
	if _, err := recordMutationCognitionReceiptWithPaths(scope, "sp-do", ".specify/do/sessions/"+session.ID, "mark-dirty", "generated source remains explicit cognition debt in this empty project", "", validation.ChangedSourcePaths, validation.ChangedSourcePaths); err != nil {
		t.Fatal(err)
	}
	session, digest, err := loadDoSession(root, session.ID)
	if err != nil {
		t.Fatal(err)
	}
	session, err = doFinish(root, session, digest, doFinishInput{ExpectedRevision: session.Revision, KnowledgeStatus: "pending"})
	if err != nil {
		t.Fatal(err)
	}
	result := playbookPublishFixture(t, root, session, "")
	document, err := loadPlaybookDocument(root, result["id"].(string))
	if err != nil {
		t.Fatal(err)
	}
	current, err := playbookSourceFingerprint(root, session.Definition)
	if err != nil || !reflect.DeepEqual(current, document.SourceFingerprint) || !reflect.DeepEqual(current, document.Verification.Sources) {
		t.Fatalf("method publication mixed initial and final source bases: %#v %v", document, err)
	}
	if document.Verification.SourceFingerprint != session.Validation.SourceFingerprint || len(document.Definition.Steps[0].SourceWrites) != 2 {
		t.Fatal("source permission or final verification binding was lost")
	}
	playbookFinishFixture(t, root, session.ID, result)
}

func playbookSnapshotFiles(t *testing.T, root string) map[string]string {
	t.Helper()
	files := map[string]string{}
	err := filepath.WalkDir(root, func(p string, entry os.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if !entry.IsDir() {
			raw, err := os.ReadFile(p)
			if err != nil {
				return err
			}
			files[p] = fileContentSHA256(raw)
		}
		return nil
	})
	if err != nil {
		t.Fatal(err)
	}
	return files
}
