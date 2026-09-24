package main

import (
	"bytes"
	"encoding/json"
	"os"
	"reflect"
	"strings"
	"testing"
)

// Whole-runtime regression tests. These intentionally use the actual Run route,
// real Git/file fixture and existing confirmation writer; they are not decoder
// unit tests and must not be counted as run by a selected-source decoder check.
func TestQuickShadowCLIStateReadyAfterAcceptedPrerequisite(t *testing.T) {
	service, doc := shadowTestRepo(t)
	doc.Execution.WorkItemStatus[0].Status = "accepted"
	doc.Execution.WorkItemStatus[0].AcceptanceEvidence = []string{"synthetic prerequisite evidence"}
	doc.Execution.WorkItemStatus[1].Status = "ready"
	shadowTestWrite(t, service.projectRoot, doc)
	before := shadowTestFiles(t, service.projectRoot)
	code, env := runQuickShadowEntry(t, "quick", "context-shadow", "--workspace", doc.Workspace,
		"--item", "Q2", "--project-root", service.projectRoot, "--format", "json")
	if code != 0 || env.Data["authorizes_execution"] != false || len(env.NextArgv) != 0 {
		t.Fatal("normal ready successor was rejected or execution was authorized", code, env)
	}
	if !reflect.DeepEqual(before, shadowTestFiles(t, service.projectRoot)) {
		t.Fatal("ready diagnostic started work or changed files")
	}
	// A ready label by itself cannot satisfy the existing prerequisite gate.
	doc.Execution.WorkItemStatus[0].Status = "pending"
	shadowTestWrite(t, service.projectRoot, doc)
	code, env = runQuickShadowEntry(t, "quick", "context-shadow", "--workspace", doc.Workspace,
		"--item", "Q2", "--project-root", service.projectRoot)
	if code != 10 {
		t.Fatal("ready label bypassed prerequisite verification", env)
	}
	if _, ok := env.Data["report"]; ok {
		t.Fatal("unmet dependencies produced a report")
	}
}

func TestQuickShadowCLIStateExactNumbersReachOutput(t *testing.T) {
	service, doc := shadowTestRepo(t)
	doc.Decision.UIConfirmation["source_id"] = json.Number("9007199254740993")
	doc.Decision.UIConfirmation["threshold"] = json.Number("0.12345678901234567890123456789")
	shadowTestWrite(t, service.projectRoot, doc)
	before := shadowTestFiles(t, service.projectRoot)
	var out, stderr bytes.Buffer
	code := Run([]string{"quick", "context-shadow", "--workspace", doc.Workspace,
		"--item", "Q1", "--project-root", service.projectRoot}, &out, &stderr, "test")
	if code != 0 {
		t.Fatalf("exact bound numbers were rejected: %d %s", code, out.String())
	}
	decoder := json.NewDecoder(bytes.NewReader(out.Bytes()))
	decoder.UseNumber() // Test the wire values, not a second lossy test-side read.
	var env Envelope
	if err := decoder.Decode(&env); err != nil {
		t.Fatal(err)
	}
	report := env.Data["report"].(map[string]any)
	owner := report["owner_packet"].(map[string]any)
	ui := owner["ui_confirmation"].(map[string]any)
	if ui["source_id"].(json.Number).String() != "9007199254740993" ||
		ui["threshold"].(json.Number).String() != "0.12345678901234567890123456789" ||
		owner["confirmation_digest"] != doc.ConfirmationDigest || report["authorizes_execution"] != false {
		t.Fatal("exact state or non-authority contract changed", env)
	}
	if !reflect.DeepEqual(before, shadowTestFiles(t, service.projectRoot)) {
		t.Fatal("read rewrote confirmation evidence")
	}
}

func TestQuickShadowCLIStateAliasesCannotClearBlockers(t *testing.T) {
	service, doc := shadowTestRepo(t)
	filename := shadowTestWrite(t, service.projectRoot, doc)
	original, err := os.ReadFile(filename)
	if err != nil {
		t.Fatal(err)
	}
	cases := [][]byte{
		bytes.Replace(original, []byte(`"confirmation_state": "confirmed"`), []byte(`"confirmation_state":"staged","Confirmation_State":"confirmed"`), 1),
		bytes.Replace(original, []byte(`"status": "pending"`), []byte(`"status":"blocked","Status":"pending"`), 1),
		bytes.Replace(original, []byte(`"decision":`), []byte(`"Decision":`), 1),
	}
	for _, raw := range cases {
		if bytes.Equal(raw, original) {
			t.Fatal("regression fixture did not change the selected wire field")
		}
		if err := os.WriteFile(filename, raw, 0600); err != nil {
			t.Fatal(err)
		}
		before := shadowTestFiles(t, service.projectRoot)
		code, env := runQuickShadowEntry(t, "quick", "context-shadow", "--workspace", doc.Workspace,
			"--item", "Q1", "--project-root", service.projectRoot)
		if code != 10 || len(env.NextArgv) != 0 || env.Data["authorizes_execution"] != false {
			t.Fatal("ambiguous state produced a successful report", code, env)
		}
		if _, ok := env.Data["report"]; ok {
			t.Fatal("partial report escaped after alias rejection")
		}
		found := false
		for _, value := range env.Blockers {
			text, _ := value.(string)
			found = found || strings.Contains(text, "quick_shadow_field_alias")
		}
		if !found || !reflect.DeepEqual(before, shadowTestFiles(t, service.projectRoot)) {
			t.Fatal("alias diagnostic was hidden or source was repaired", env)
		}
	}
}
