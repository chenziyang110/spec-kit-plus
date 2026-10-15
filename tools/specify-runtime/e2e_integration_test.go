package main

import (
	"bytes"
	"encoding/base64"
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"runtime"
	"sort"
	"strings"
	"testing"
)

func e2ePublicCall(t *testing.T, args ...string) (int, map[string]any) {
	t.Helper()
	var out, stderr bytes.Buffer
	code := Run(args, &out, &stderr, "dev")
	var result map[string]any
	if err := json.Unmarshal(out.Bytes(), &result); err != nil {
		t.Fatalf("%v: exit=%d stderr=%s invalid envelope: %v: %s", args, code, stderr.String(), err, out.String())
	}
	return code, result
}

func TestE2EPublicDiscoveryAndPublishedSchemasAreExecutable(t *testing.T) {
	expected := []string{"e2e.init", "e2e.status", "e2e.task-show", "e2e.compact", "e2e.scope-add", "e2e.task-start", "e2e.task-submit", "e2e.review-start", "e2e.review-submit", "e2e.task-accept", "e2e.reopen", "e2e.close"}
	code, response := e2ePublicCall(t, "api", "ensure", "--capabilities", strings.Join(expected, ","), "--format", "json")
	if code != 0 {
		t.Fatalf("E2E cannot be negotiated: %v", response)
	}
	present := stringSliceFromAny(response["data"].(map[string]any)["present"])
	sort.Strings(expected)
	sort.Strings(present)
	if !reflect.DeepEqual(present, expected) {
		t.Fatalf("E2E capabilities: got %v want %v", present, expected)
	}
	code, response = e2ePublicCall(t, "api", "pack", "--capabilities", "e2e.init,e2e.scope-add,e2e.task-submit,e2e.review-submit", "--include-schema", "--format", "json")
	if code != 0 {
		t.Fatalf("E2E schemas cannot be expanded: %v", response)
	}
	items := response["items"].([]any)
	if len(items) != 4 {
		t.Fatalf("input schemas missing: %v", response)
	}
	for _, raw := range items {
		item := raw.(map[string]any)
		schema := item["schema"].(map[string]any)
		if schema["additionalProperties"] != false || item["side_effect"] == "" || !strings.Contains(item["usage"].(string), "--run-id") {
			t.Fatalf("incomplete runtime contract: %v", item)
		}
		if item["id"] == "e2e.init" {
			root := t.TempDir()
			e2eTestFile(t, root, "request.md", "Cover the declared web save operation, including all seven stage outputs.")
			plan := schema["examples"].([]any)[0]
			code, result := e2ePublicCall(t, "e2e", "init", "--project-root", root, "--run-id", "schema-example", "--leader-id", "leader", "--input-json", e2eTestJSON(t, plan), "--format", "json")
			if code != 0 {
				t.Fatalf("published example is not accepted by the real owner: %v", result)
			}
			code, result = e2ePublicCall(t, "e2e", "task-start", "--project-root", root, "--run-id", "schema-example", "--task-id", "S2", "--worker-id", "worker", "--expected-revision", "1", "--format", "json")
			if code == 0 {
				t.Fatalf("published example let stage 2 bypass stage 1: %v", result)
			}
		}
	}
}

func TestE2EStateHasOneMutationOwner(t *testing.T) {
	root := e2eTestInit(t, "execution")
	stateRef := ".planning/e2e/run-1/state.json"
	statePath := filepath.Join(root, filepath.FromSlash(stateRef))
	before, err := os.ReadFile(statePath)
	if err != nil {
		t.Fatal(err)
	}
	code, result := e2ePublicCall(t, "artifact", "show", "--path", stateRef, "--project-root", root, "--format", "json")
	if code != 0 {
		t.Fatalf("runtime state is not inspectable: %v", result)
	}
	for _, ref := range []string{stateRef, ".planning/e2e/run-1/snapshots/new.json", ".planning/e2e/run-1/future.json"} {
		metadata, found := LookupArtifactType(ref)
		if !found || metadata.Owner != "specify-runtime e2e" || !reflect.DeepEqual(metadata.Operations, []string{"show", "list"}) {
			t.Fatalf("E2E path is not protected by the shared registry: %s: %#v", ref, metadata)
		}
		code, result = e2ePublicCall(t, "artifact", "prepare", "--path", ref, "--project-root", root, "--format", "json")
		if code == 0 || result["data"].(map[string]any)["owner"] != "specify-runtime e2e" {
			t.Fatalf("generic writer did not route to the real E2E owner: %s: %v", ref, result)
		}
	}
	for _, integration := range []string{"codex", "claude", "generic"} {
		if _, err := buildResultHandoffPath(root, resultPathRequest{CommandName: "e2e", IntegrationKey: integration, TaskID: "S1"}); err == nil || !strings.Contains(err.Error(), "e2e task-submit") {
			t.Fatalf("generic result channel did not reject E2E for %s: %v", integration, err)
		}
	}
	after, err := os.ReadFile(statePath)
	if err != nil || !bytes.Equal(before, after) {
		t.Fatalf("generic access changed runtime state: %v", err)
	}
}

func TestE2EOwnerCannotBeBypassedWithAnotherResultCommand(t *testing.T) {
	root := t.TempDir()
	e2eTestFile(t, root, "request.md", "Cover the declared operation.")
	e2eTestFile(t, root, ".specify/integration.json", `{"integration":"claude"}`)
	e2eTestData(t, root, "init", "--run-id", "worker-results", "--leader-id", "leader", "--input-json", e2eTestJSON(t, e2eTestPlan("execution")))
	statePath := filepath.Join(root, ".planning", "e2e", "worker-results", "state.json")
	before, err := os.ReadFile(statePath)
	if err != nil {
		t.Fatal(err)
	}
	withCwd(t, root)
	workspaces := []string{".planning/e2e"}
	if runtime.GOOS == "windows" || runtime.GOOS == "darwin" {
		workspaces = append(workspaces, ".Planning/E2E")
	}
	for _, workspace := range workspaces {
		code, result := e2ePublicCall(t, "result", "submit", "--command", "quick", "--workspace", workspace, "--lane-id", "state", "--result-json", `{"task_id":"fixture","status":"success","summary":"A result must not replace another workflow's state."}`, "--format", "json")
		if code == 0 || !strings.Contains(e2eTestJSON(t, result), "E2E state") {
			t.Fatalf("another result channel bypassed E2E ownership through %s: %v", workspace, result)
		}
	}
	after, err := os.ReadFile(statePath)
	if err != nil || !bytes.Equal(before, after) {
		t.Fatalf("E2E state was overwritten by another result channel: %v", err)
	}
}

func TestE2ERawEvidenceReadIsLosslessAndReadOnly(t *testing.T) {
	root := e2eTestInit(t, "execution")
	wanted := []byte{0x89, 'P', 'N', 'G', 0, 0xff, '\n'}
	e2eTestFile(t, root, "request.md", string(wanted))
	started := e2eTestMutation(t, root, "task-start", "--task-id", "S1", "--worker-id", "worker")
	packet := started["packet"].(map[string]any)
	binding := packet["inputs"].([]any)[0].(map[string]any)
	ref := binding["archive_ref"].(string)
	code, result := e2ePublicCall(t, "artifact", "show", "--path", ref, "--project-root", root, "--view", "full", "--format", "json")
	if code != 0 {
		t.Fatalf("raw evidence is not inspectable: %v", result)
	}
	data := result["data"].(map[string]any)
	actual, err := base64.StdEncoding.DecodeString(data["content_base64"].(string))
	if err != nil || !bytes.Equal(wanted, actual) || data["content_encoding"] != "base64" || data["type_id"] != "e2e-raw-evidence" || data["sha256"] != binding["sha256"] {
		t.Fatalf("raw evidence was treated as text or JSON: %v: %v", err, result)
	}
	code, result = e2ePublicCall(t, "artifact", "show", "--path", ref, "--project-root", root, "--json-pointer", "/", "--format", "json")
	if code == 0 || !strings.Contains(e2eTestJSON(t, result), "raw evidence does not support") {
		t.Fatalf("raw evidence advertised JSON queries: %v", result)
	}
	code, result = e2ePublicCall(t, "artifact", "prepare", "--path", ref, "--project-root", root, "--format", "json")
	if code == 0 || result["data"].(map[string]any)["owner"] != "specify-runtime e2e" {
		t.Fatalf("raw evidence lost E2E mutation ownership: %v", result)
	}
}
