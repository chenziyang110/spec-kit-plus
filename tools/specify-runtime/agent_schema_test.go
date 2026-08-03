package main

import (
	"bytes"
	"strings"
	"testing"
)

func TestAPISchemaExpandsWorkflowBlockInputContract(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Run(
		[]string{"api", "schema", "workflow-block-input", "--format", "json"},
		&stdout,
		&stderr,
		"test",
	)
	if code != 0 {
		t.Fatalf("api schema exit code = %d; stdout=%s stderr=%s", code, stdout.String(), stderr.String())
	}
	payload := decodeJSONObject(t, stdout.Bytes())
	data := requireObject(t, payload, "data")
	schema := requireObject(t, data, "schema")
	properties := requireObject(t, schema, "properties")
	humanActionRequired := requireObject(t, properties, "human_action_required")
	types, ok := humanActionRequired["type"].([]any)
	if !ok || len(types) != 2 || types[0] != "boolean" || types[1] != "null" {
		t.Fatalf("human_action_required type = %#v, want [boolean null]", humanActionRequired["type"])
	}
	required, ok := schema["required"].([]any)
	if !ok || len(required) != 10 {
		t.Fatalf("workflow block required fields = %#v, want 10 fields", schema["required"])
	}
	if show := requireStringArray(t, payload, "show_argv"); len(show) < 4 || show[1] != "api" || show[2] != "show" {
		t.Fatalf("schema show_argv = %#v, want runtime capability expansion", show)
	}
}

func TestAPISchemaRejectsUnknownSchema(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Run([]string{"api", "schema", "missing", "--format", "json"}, &stdout, &stderr, "test")
	if code != 2 {
		t.Fatalf("unknown api schema exit code = %d, want 2; stdout=%s", code, stdout.String())
	}
	payload := decodeJSONObject(t, stdout.Bytes())
	if payload["status"] != "usage-error" {
		t.Fatalf("unknown api schema status = %#v, want usage-error", payload["status"])
	}
}

func TestAPIShowExpandsEveryAdvertisedCapability(t *testing.T) {
	for _, capabilityID := range defaultCapabilities() {
		t.Run(capabilityID, func(t *testing.T) {
			var stdout, stderr bytes.Buffer
			code := Run([]string{"api", "show", capabilityID, "--format", "json"}, &stdout, &stderr, "test")
			if code != 0 {
				t.Fatalf("api show %s exit code = %d; stdout=%s stderr=%s", capabilityID, code, stdout.String(), stderr.String())
			}
			payload := decodeJSONObject(t, stdout.Bytes())
			capability := requireObject(t, requireObject(t, payload, "data"), "capability")
			if capability["id"] != capabilityID {
				t.Fatalf("api show %s capability = %#v", capabilityID, capability)
			}
		})
	}
}

func TestAPIShowArtifactScaffoldPublishesSchemaAndCatalogRoute(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Run([]string{"api", "show", "--id", "artifact.scaffold", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("api show artifact.scaffold exit code = %d; stdout=%s stderr=%s", code, stdout.String(), stderr.String())
	}
	payload := decodeJSONObject(t, stdout.Bytes())
	capability := requireObject(t, requireObject(t, payload, "data"), "capability")
	if capability["input_schema"] != "artifact-scaffold-input" {
		t.Fatalf("artifact scaffold capability = %#v", capability)
	}
	if show := requireStringArray(t, payload, "show_argv"); show[3] != "artifact-scaffold-input" {
		t.Fatalf("artifact scaffold show_argv = %#v", show)
	}
	if next := requireStringArray(t, payload, "next_argv"); len(next) < 3 || next[1] != "artifact" || next[2] != "catalog" {
		t.Fatalf("artifact scaffold next_argv = %#v", next)
	}
}

func TestAPIShowEvidenceRegisterPublishesInlineAndCanonicalObjectModes(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Run([]string{"api", "show", "evidence.register", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("api show evidence.register exit code = %d; stdout=%s stderr=%s", code, stdout.String(), stderr.String())
	}
	payload := decodeJSONObject(t, stdout.Bytes())
	capability := requireObject(t, requireObject(t, payload, "data"), "capability")
	usage, _ := capability["usage"].(string)
	if !strings.Contains(usage, "--content") || !strings.Contains(usage, "--object") {
		t.Fatalf("evidence register capability = %#v", capability)
	}
	contract, _ := capability["input_contract"].(string)
	if !strings.Contains(contract, "exactly one") {
		t.Fatalf("evidence register input contract = %#v", capability)
	}
}

func TestAPIShowHookExtensionPlanPublishesRuntimeOwnedConfigContract(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Run([]string{"api", "show", "hook.extension-plan", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("api show hook.extension-plan exit code = %d; stdout=%s stderr=%s", code, stdout.String(), stderr.String())
	}
	payload := decodeJSONObject(t, stdout.Bytes())
	capability := requireObject(t, requireObject(t, payload, "data"), "capability")
	usage, _ := capability["usage"].(string)
	if !strings.Contains(usage, "hook extension-plan --event") {
		t.Fatalf("hook extension-plan capability = %#v", capability)
	}
	contract, _ := capability["input_contract"].(string)
	if !strings.Contains(contract, "runtime reads and filters") || !strings.Contains(contract, "agents consume only") {
		t.Fatalf("hook extension-plan input contract = %#v", capability)
	}
}

func TestAPIShowDiscussionBindConsumerPublishesDerivedPointerContract(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Run([]string{"api", "show", "discussion.bind-consumer", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("api show discussion.bind-consumer exit code = %d; stdout=%s stderr=%s", code, stdout.String(), stderr.String())
	}
	payload := decodeJSONObject(t, stdout.Bytes())
	capability := requireObject(t, requireObject(t, payload, "data"), "capability")
	usage, _ := capability["usage"].(string)
	if !strings.Contains(usage, "discussion bind-consumer") || !strings.Contains(usage, "--input-json") {
		t.Fatalf("discussion bind-consumer capability = %#v", capability)
	}
	contract, _ := capability["input_contract"].(string)
	if !strings.Contains(contract, "runtime binds") || !strings.Contains(contract, "review digest") {
		t.Fatalf("discussion bind-consumer input contract = %#v", capability)
	}
}

func TestAPIShowReviewTargetBindPublishesCompactDerivedContract(t *testing.T) {
	var stdout bytes.Buffer
	var stderr bytes.Buffer
	code := Run([]string{"api", "show", "review.target-bind", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("api show review.target-bind exit code = %d; stdout=%s stderr=%s", code, stdout.String(), stderr.String())
	}
	env := decodeEnvelope(t, stdout.Bytes())
	capability := env.Data["capability"].(map[string]any)
	usage := capability["usage"].(string)
	if !strings.Contains(usage, "review target-bind") || !strings.Contains(usage, "--input-json") {
		t.Fatalf("review target-bind capability = %#v", capability)
	}
	contract := capability["input_contract"].(string)
	if !strings.Contains(contract, "runtime derives ready status") || !strings.Contains(contract, "identity path and bytes") {
		t.Fatalf("review target-bind input contract = %#v", capability)
	}
}

func TestAPIShowSemanticAuditPublishesAtomicPersistenceContract(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Run([]string{"api", "show", "cognition.semantic-audit", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("api show cognition.semantic-audit exit code = %d; stdout=%s stderr=%s", code, stdout.String(), stderr.String())
	}
	payload := decodeJSONObject(t, stdout.Bytes())
	capability := requireObject(t, requireObject(t, payload, "data"), "capability")
	usage, _ := capability["usage"].(string)
	contract, _ := capability["input_contract"].(string)
	if !strings.Contains(usage, "--persist-dir") || !strings.Contains(contract, "writes registered semantic-audit-input.json and semantic-audit-output.json together") || !strings.Contains(contract, "must not recreate") {
		t.Fatalf("semantic audit persistence capability = %#v", capability)
	}
}

func TestAPIShowVisualComparePublishesDerivedReportContract(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Run([]string{"api", "show", "evidence.visual-compare", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("api show evidence.visual-compare exit code = %d; stdout=%s stderr=%s", code, stdout.String(), stderr.String())
	}
	payload := decodeJSONObject(t, stdout.Bytes())
	capability := requireObject(t, requireObject(t, payload, "data"), "capability")
	usage, _ := capability["usage"].(string)
	contract, _ := capability["input_contract"].(string)
	if !strings.Contains(usage, "evidence visual-compare") || !strings.Contains(contract, "runtime derives approved design and handoff bindings") || !strings.Contains(contract, "from task-index.json") {
		t.Fatalf("visual compare capability = %#v", capability)
	}
}

func TestAPIShowPRDRecordUpsertPublishesRecordOwnedContract(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Run([]string{"api", "show", "prd-scan.record-upsert", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("api show prd-scan.record-upsert exit code = %d; stdout=%s stderr=%s", code, stdout.String(), stderr.String())
	}
	payload := decodeJSONObject(t, stdout.Bytes())
	capability := requireObject(t, requireObject(t, payload, "data"), "capability")
	usage, _ := capability["usage"].(string)
	contract, _ := capability["input_contract"].(string)
	if !strings.Contains(usage, "record-upsert") || !strings.Contains(usage, "--expected-sha256") || !strings.Contains(contract, "runtime owns the registered outer document") {
		t.Fatalf("PRD record upsert capability = %#v", capability)
	}
}

func TestAPIShowPRDBuildScaffoldPublishesTemplateOwnershipContract(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Run([]string{"api", "show", "prd-build.scaffold", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("api show prd-build.scaffold exit code = %d; stdout=%s stderr=%s", code, stdout.String(), stderr.String())
	}
	payload := decodeJSONObject(t, stdout.Bytes())
	capability := requireObject(t, requireObject(t, payload, "data"), "capability")
	usage, _ := capability["usage"].(string)
	contract, _ := capability["input_contract"].(string)
	if !strings.Contains(usage, "prd-build scaffold") || !strings.Contains(contract, "expands installed PRD templates") || !strings.Contains(contract, "patch only semantic sections") {
		t.Fatalf("PRD build scaffold capability = %#v", capability)
	}
}

func TestAPIShowRunSupervisePublishesForcedWorkspaceEnvironmentContract(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Run([]string{"api", "show", "run.supervise", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("api show run.supervise exit code = %d; stdout=%s stderr=%s", code, stdout.String(), stderr.String())
	}
	payload := decodeJSONObject(t, stdout.Bytes())
	capability := requireObject(t, requireObject(t, payload, "data"), "capability")
	usage, _ := capability["usage"].(string)
	contract, _ := capability["input_contract"].(string)
	if !strings.Contains(usage, "run supervise") || !strings.Contains(contract, "forces child cwd") || !strings.Contains(contract, "SPECIFY_RUN_*") || !strings.Contains(contract, "WSLENV") {
		t.Fatalf("run supervise capability = %#v", capability)
	}
}

func TestAPIShowRunLaunchPublishesSingleCallAdapterContract(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Run([]string{"api", "show", "run.launch", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("api show run.launch exit code = %d; stdout=%s stderr=%s", code, stdout.String(), stderr.String())
	}
	payload := decodeJSONObject(t, stdout.Bytes())
	capability := requireObject(t, requireObject(t, payload, "data"), "capability")
	usage, _ := capability["usage"].(string)
	contract, _ := capability["input_contract"].(string)
	if !strings.Contains(usage, "run launch") || !strings.Contains(contract, "single call") || !strings.Contains(contract, "queues") || !strings.Contains(contract, "forces child cwd") {
		t.Fatalf("run launch capability = %#v", capability)
	}
}

func TestAPIShowRunControlResultAndCandidateFlowReplacesDirectIntegrationWording(t *testing.T) {
	tests := []struct {
		capabilityID      string
		wantUsage         []string
		wantContract      []string
		forbidUsage       []string
		forbidContract    []string
	}{
		{
			capabilityID:   "result.list",
			wantUsage:      []string{"result list", "--run-id"},
			wantContract:   []string{"append-only", "result history"},
			forbidUsage:    []string{"run integrate"},
			forbidContract: []string{"direct integration"},
		},
		{
			capabilityID:   "result.show",
			wantUsage:      []string{"result show", "--result-id"},
			wantContract:   []string{"immutable", "sealed result"},
			forbidUsage:    []string{"run integrate"},
			forbidContract: []string{"direct integration"},
		},
		{
			capabilityID:   "result.reopen",
			wantUsage:      []string{"result reopen", "--basis-result-id"},
			wantContract:   []string{"reopen", "supersession"},
			forbidUsage:    []string{"run integrate"},
			forbidContract: []string{"direct integration"},
		},
		{
			capabilityID:   "result.depend",
			wantUsage:      []string{"result depend", "--upstream-result-id"},
			wantContract:   []string{"dependency", "result graph"},
			forbidUsage:    []string{"run integrate"},
			forbidContract: []string{"direct integration"},
		},
		{
			capabilityID:   "candidate.build",
			wantUsage:      []string{"candidate build", "--result-id"},
			wantContract:   []string{"multiple results", "candidate"},
			forbidUsage:    []string{"direct integrate"},
			forbidContract: []string{"direct integration"},
		},
		{
			capabilityID:   "candidate.show",
			wantUsage:      []string{"candidate show", "--candidate-id"},
			wantContract:   []string{"immutable", "candidate"},
			forbidUsage:    []string{"run integrate"},
			forbidContract: []string{"direct integration"},
		},
		{
			capabilityID:   "candidate.review",
			wantUsage:      []string{"candidate review", "literal argv"},
			wantContract:   []string{"literal argv", "review target-bind"},
			forbidUsage:    []string{"run integrate"},
			forbidContract: []string{"direct integration"},
		},
		{
			capabilityID:   "accept.receipt",
			wantUsage:      []string{"accept receipt", "--input-json"},
			wantContract:   []string{"explicit accept receipt", "human acceptance"},
			forbidUsage:    []string{"run integrate"},
			forbidContract: []string{"direct integration"},
		},
		{
			capabilityID:   "cas.publish",
			wantUsage:      []string{"cas publish", "--expected-sha256"},
			wantContract:   []string{"cas", "publish"},
			forbidUsage:    []string{"run integrate"},
			forbidContract: []string{"direct integration"},
		},
		{
			capabilityID:   "sync.safe",
			wantUsage:      []string{"sync safe", "--target-ref"},
			wantContract:   []string{"safe sync", "separate"},
			forbidUsage:    []string{"run integrate"},
			forbidContract: []string{"direct integration"},
		},
	}

	for _, test := range tests {
		t.Run(test.capabilityID, func(t *testing.T) {
			var stdout, stderr bytes.Buffer
			code := Run([]string{"api", "show", test.capabilityID, "--format", "json"}, &stdout, &stderr, "test")
			if code != 0 {
				t.Fatalf("api show %s exit code = %d; stdout=%s stderr=%s", test.capabilityID, code, stdout.String(), stderr.String())
			}
			payload := decodeJSONObject(t, stdout.Bytes())
			capability := requireObject(t, requireObject(t, payload, "data"), "capability")
			usage, _ := capability["usage"].(string)
			contract, _ := capability["input_contract"].(string)
			for _, fragment := range test.wantUsage {
				if !strings.Contains(usage, fragment) {
					t.Fatalf("%s usage = %q, missing %q", test.capabilityID, usage, fragment)
				}
			}
			for _, fragment := range test.wantContract {
				if !strings.Contains(contract, fragment) {
					t.Fatalf("%s input contract = %q, missing %q", test.capabilityID, contract, fragment)
				}
			}
			for _, fragment := range test.forbidUsage {
				if strings.Contains(usage, fragment) {
					t.Fatalf("%s usage = %q, contains forbidden legacy wording %q", test.capabilityID, usage, fragment)
				}
			}
			for _, fragment := range test.forbidContract {
				if strings.Contains(contract, fragment) {
					t.Fatalf("%s input contract = %q, contains forbidden legacy wording %q", test.capabilityID, contract, fragment)
				}
			}
		})
	}
}

func TestAPISchemaExpandsArtifactScaffoldInputContract(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Run([]string{"api", "schema", "--id", "artifact-scaffold-input", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("api schema artifact scaffold exit code = %d; stdout=%s stderr=%s", code, stdout.String(), stderr.String())
	}
	payload := decodeJSONObject(t, stdout.Bytes())
	schema := requireObject(t, requireObject(t, payload, "data"), "schema")
	properties := requireObject(t, schema, "properties")
	if _, ok := properties["path"]; !ok {
		t.Fatalf("artifact scaffold schema properties = %#v", properties)
	}
	if aliases, ok := schema["x-compatibility-aliases"].(map[string]any); !ok || aliases["out"] != "path" {
		t.Fatalf("artifact scaffold compatibility aliases = %#v", schema["x-compatibility-aliases"])
	}
}
