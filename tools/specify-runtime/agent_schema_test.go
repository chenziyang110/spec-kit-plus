package main

import (
	"bytes"
	"fmt"
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

func TestAPISchemaExpandsWorkflowReconcileBlockerContract(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Run([]string{"api", "schema", "workflow-reconcile-blocker-input", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("api schema reconcile blocker exit=%d stdout=%s stderr=%s", code, stdout.String(), stderr.String())
	}
	payload := decodeJSONObject(t, stdout.Bytes())
	schema := requireObject(t, requireObject(t, payload, "data"), "schema")
	properties := requireObject(t, schema, "properties")
	for _, field := range []string{"resolved_subcauses", "remaining_cause", "remaining_evidence", "remaining_scope", "exact_next_action", "unblock_criteria"} {
		if _, ok := properties[field].(map[string]any); !ok {
			t.Fatalf("reconcile blocker schema missing %s: %#v", field, schema)
		}
	}
	var showOut bytes.Buffer
	code = Run([]string{"api", "show", "workflow.reconcile-blocker", "--format", "json"}, &showOut, &stderr, "test")
	if code != 0 {
		t.Fatalf("api show reconcile blocker exit=%d stdout=%s stderr=%s", code, showOut.String(), stderr.String())
	}
	capability := requireObject(t, requireObject(t, decodeJSONObject(t, showOut.Bytes()), "data"), "capability")
	if capability["input_schema"] != "workflow-reconcile-blocker-input" || !strings.Contains(anyString(capability["input_contract"]), "stale text") {
		t.Fatalf("reconcile blocker capability = %#v", capability)
	}
}

func TestAPISchemaExpandsArtifactBatchInputContracts(t *testing.T) {
	for _, schemaID := range []string{"artifact-show-many-input", "artifact-patch-batch-input"} {
		var stdout, stderr bytes.Buffer
		code := Run([]string{"api", "schema", schemaID, "--format", "json"}, &stdout, &stderr, "test")
		if code != 0 {
			t.Fatalf("api schema %s exit code = %d; stdout=%s stderr=%s", schemaID, code, stdout.String(), stderr.String())
		}
		payload := decodeJSONObject(t, stdout.Bytes())
		data := requireObject(t, payload, "data")
		schema := requireObject(t, data, "schema")
		properties := requireObject(t, schema, "properties")
		switch schemaID {
		case "artifact-show-many-input":
			queries := requireObject(t, properties, "queries")
			if queries["type"] != "array" {
				t.Fatalf("%s queries = %#v", schemaID, queries)
			}
		case "artifact-patch-batch-input":
			operations := requireObject(t, properties, "operations")
			if operations["type"] != "array" {
				t.Fatalf("%s operations = %#v", schemaID, operations)
			}
		}
	}
}

func TestAPISchemaExpandsEveryDeepResearchPayloadContract(t *testing.T) {
	tests := []struct {
		schemaID    string
		capability  string
		requiredKey string
	}{
		{"deep-research-track-prepare-input", "deep-research.track-prepare", "tracks"},
		{"deep-research-track-submit-result", "deep-research.track-submit", "protocol"},
		{"deep-research-synthesis-input", "deep-research.synthesize", "planning_handoffs"},
		{"deep-research-audit-input", "deep-research.audit-accept", "checks"},
		{"deep-research-not-needed-input", "deep-research.not-needed", "capability_dispositions"},
	}
	for _, test := range tests {
		t.Run(test.schemaID, func(t *testing.T) {
			var stdout, stderr bytes.Buffer
			code := Run([]string{"api", "schema", test.schemaID, "--format", "json"}, &stdout, &stderr, "test")
			if code != 0 {
				t.Fatalf("api schema %s exit=%d stdout=%s stderr=%s", test.schemaID, code, stdout.String(), stderr.String())
			}
			payload := decodeJSONObject(t, stdout.Bytes())
			data := requireObject(t, payload, "data")
			if data["schema_id"] != test.schemaID {
				t.Fatalf("schema id = %#v", data["schema_id"])
			}
			schema := requireObject(t, data, "schema")
			if schema["type"] != "object" || schema["additionalProperties"] != false {
				t.Fatalf("schema boundary = %#v", schema)
			}
			properties := requireObject(t, schema, "properties")
			if _, ok := properties[test.requiredKey].(map[string]any); !ok {
				t.Fatalf("schema %s missing %s: %#v", test.schemaID, test.requiredKey, properties)
			}
			show := requireStringArray(t, payload, "show_argv")
			if len(show) < 4 || show[1] != "api" || show[2] != "show" || show[3] != test.capability {
				t.Fatalf("schema %s show argv = %#v", test.schemaID, show)
			}
		})
	}
}

func TestAPIShowDeepResearchPayloadCommandsPublishSchemas(t *testing.T) {
	want := map[string]string{
		"deep-research.track-prepare": "deep-research-track-prepare-input",
		"deep-research.track-submit":  "deep-research-track-submit-result",
		"deep-research.synthesize":    "deep-research-synthesis-input",
		"deep-research.audit-accept":  "deep-research-audit-input",
		"deep-research.not-needed":    "deep-research-not-needed-input",
	}
	for capabilityID, schemaID := range want {
		t.Run(capabilityID, func(t *testing.T) {
			var stdout, stderr bytes.Buffer
			code := Run([]string{"api", "show", capabilityID, "--format", "json"}, &stdout, &stderr, "test")
			if code != 0 {
				t.Fatalf("api show %s exit=%d stdout=%s stderr=%s", capabilityID, code, stdout.String(), stderr.String())
			}
			capability := requireObject(t, requireObject(t, decodeJSONObject(t, stdout.Bytes()), "data"), "capability")
			if capability["input_schema"] != schemaID {
				t.Fatalf("%s input_schema = %#v, want %s", capabilityID, capability["input_schema"], schemaID)
			}
			if show := requireStringArray(t, decodeJSONObject(t, stdout.Bytes()), "show_argv"); len(show) < 4 || show[2] != "schema" || show[3] != schemaID {
				t.Fatalf("%s schema argv = %#v", capabilityID, show)
			}
		})
	}
}

func TestAPIShowDeepResearchPlanHandoffCommandsPublishSourceReadiness(t *testing.T) {
	for _, capabilityID := range []string{
		"deep-research.init", "deep-research.status", "deep-research.validate",
		"deep-research.publish", "deep-research.verify-handoff",
	} {
		t.Run(capabilityID, func(t *testing.T) {
			var stdout, stderr bytes.Buffer
			code := Run([]string{"api", "show", capabilityID, "--format", "json"}, &stdout, &stderr, "test")
			if code != 0 {
				t.Fatalf("api show %s exit=%d stdout=%s stderr=%s", capabilityID, code, stdout.String(), stderr.String())
			}
			capability := requireObject(t, requireObject(t, decodeJSONObject(t, stdout.Bytes()), "data"), "capability")
			contract := strings.ToLower(anyString(capability["input_contract"]))
			for _, phrase := range []string{"planning-ready", "workflow", "blocked", "specify"} {
				if !strings.Contains(contract, phrase) {
					t.Fatalf("%s input_contract = %q, missing %q", capabilityID, contract, phrase)
				}
			}
			if capabilityID == "deep-research.init" || capabilityID == "deep-research.validate" || capabilityID == "deep-research.publish" {
				for _, phrase := range []string{"workflow lock", "precondition"} {
					if !strings.Contains(contract, phrase) {
						t.Fatalf("%s input_contract = %q, missing atomicity phrase %q", capabilityID, contract, phrase)
					}
				}
			}
		})
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
			for _, field := range []string{"summary", "usage", "side_effect", "input_contract"} {
				value, ok := capability[field].(string)
				if !ok || strings.TrimSpace(value) == "" {
					t.Fatalf("api show %s capability.%s = %#v", capabilityID, field, capability[field])
				}
			}
		})
	}
}

func TestAPIShowArtifactBatchCapabilitiesPublishContracts(t *testing.T) {
	for _, capabilityID := range []string{"artifact.show-many", "artifact.patch-batch"} {
		var stdout, stderr bytes.Buffer
		code := Run([]string{"api", "show", capabilityID, "--format", "json"}, &stdout, &stderr, "test")
		if code != 0 {
			t.Fatalf("api show %s exit code = %d; stdout=%s stderr=%s", capabilityID, code, stdout.String(), stderr.String())
		}
		payload := decodeJSONObject(t, stdout.Bytes())
		capability := requireObject(t, requireObject(t, payload, "data"), "capability")
		for _, field := range []string{"summary", "usage", "side_effect", "input_contract", "input_schema"} {
			value, ok := capability[field].(string)
			if !ok || strings.TrimSpace(value) == "" {
				t.Fatalf("api show %s capability.%s = %#v", capabilityID, field, capability[field])
			}
		}
	}
}

func TestAPIShowDesignDirectionConfirmPublishesNonConsumableCheckpointContract(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Run([]string{"api", "show", "design.direction-confirm", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("api show design.direction-confirm exit code = %d; stdout=%s stderr=%s", code, stdout.String(), stderr.String())
	}
	payload := decodeJSONObject(t, stdout.Bytes())
	capability := requireObject(t, requireObject(t, payload, "data"), "capability")
	for _, field := range []string{"summary", "usage", "side_effect", "input_contract"} {
		value, ok := capability[field].(string)
		if !ok || strings.TrimSpace(value) == "" {
			t.Fatalf("design.direction-confirm capability.%s = %#v", field, capability[field])
		}
	}
	contract := capability["input_contract"].(string)
	if !strings.Contains(contract, "non-consumable") || !strings.Contains(contract, "draft") || !strings.Contains(contract, ".direction.json") {
		t.Fatalf("design.direction-confirm input_contract = %q", contract)
	}

	metadata, ok := LookupArtifactType(".specify/design/changes/UD-0042/previews/round-01.direction.json")
	if !ok {
		t.Fatal("direction checkpoint artifact type is not registered")
	}
	if metadata.TypeID != "ui-design-direction-checkpoint" || metadata.Owner != "specify-runtime design direction-confirm" || metadata.Role != "derived" || metadata.Authority != "non-consumable" || strings.Join(metadata.Operations, ",") != "show,list" {
		t.Fatalf("direction checkpoint artifact metadata = %#v", metadata)
	}
	if artifactTypeAllows(metadata, "prepare") || artifactTypeAllows(metadata, "patch") {
		t.Fatalf("direction checkpoint must remain runtime-owned: %#v", metadata)
	}
}

func TestAPIShowDesignPreviewLintPublishesConceptLevel(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Run([]string{"api", "show", "design.preview-lint", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("api show design.preview-lint exit code = %d; stdout=%s stderr=%s", code, stdout.String(), stderr.String())
	}
	payload := decodeJSONObject(t, stdout.Bytes())
	capability := requireObject(t, requireObject(t, payload, "data"), "capability")
	usage := fmt.Sprint(capability["usage"])
	contract := fmt.Sprint(capability["input_contract"])
	if !strings.Contains(usage, "structural|concept|ready") || !strings.Contains(contract, "concept") {
		t.Fatalf("design.preview-lint concept contract missing: usage=%q input_contract=%q", usage, contract)
	}
}

func TestAPIShowDesignPromptPublishesGenerationContract(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Run([]string{"api", "show", "design.prompt", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("api show design.prompt exit code = %d; stdout=%s stderr=%s", code, stdout.String(), stderr.String())
	}
	payload := decodeJSONObject(t, stdout.Bytes())
	capability := requireObject(t, requireObject(t, payload, "data"), "capability")
	usage := fmt.Sprint(capability["usage"])
	contract := fmt.Sprint(capability["input_contract"])
	fileInput := fmt.Sprint(capability["file_input"])
	if !strings.Contains(usage, "design prompt") || !strings.Contains(contract, ".generation.json") {
		t.Fatalf("design.prompt contract missing: usage=%q input_contract=%q", usage, contract)
	}
	if !strings.Contains(usage, "--content") || strings.Contains(usage, "--force") || !strings.Contains(contract, "stdin") || !strings.Contains(contract, "create-only") {
		t.Fatalf("design.prompt must expose exact create-only stdin transport: usage=%q input_contract=%q", usage, contract)
	}
	if !strings.Contains(fileInput, "project-contained") || !strings.Contains(fileInput, "reparse") {
		t.Fatalf("design.prompt file input safety contract missing: %q", fileInput)
	}
	metadata, ok := LookupArtifactType(".specify/design/changes/UD-0042/previews/round-01.generation.json")
	if !ok || metadata.TypeID != "ui-design-generation-sidecar" || metadata.Owner != "specify-runtime design prompt" {
		t.Fatalf("generation sidecar artifact metadata = %#v, ok=%v", metadata, ok)
	}
	prompt, ok := LookupArtifactType(".specify/design/changes/UD-0042/previews/round-01.prompt.md")
	if !ok || prompt.TypeID != "ui-design-generation-prompt" || prompt.Owner != "specify-runtime design prompt" {
		t.Fatalf("generation prompt artifact metadata = %#v, ok=%v", prompt, ok)
	}
	receipt, ok := LookupArtifactType(".specify/design/changes/UD-0042/previews/round-01.concept.json")
	if !ok || receipt.TypeID != "ui-design-concept-receipt" || receipt.Owner != "specify-runtime design preview-lint" {
		t.Fatalf("concept receipt artifact metadata = %#v, ok=%v", receipt, ok)
	}
}

func TestAPIShowSourceContinuityManifestPublishesStableSnapshotContract(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Run([]string{"api", "show", "evidence.source-continuity-manifest", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("api show source continuity manifest exit code = %d; stdout=%s stderr=%s", code, stdout.String(), stderr.String())
	}
	payload := decodeJSONObject(t, stdout.Bytes())
	capability := requireObject(t, requireObject(t, payload, "data"), "capability")
	contract := fmt.Sprint(capability["input_contract"])
	for _, marker := range []string{"expected_write_scope", "runtime-owned", "byte-stable", "product source", "Explicit runtime-owned scopes are invalid"} {
		if !strings.Contains(contract, marker) {
			t.Fatalf("source continuity manifest snapshot contract missing %q: %s", marker, contract)
		}
	}
}

func TestAPIShowWorkflowResolvePublishesAtomicReopenContract(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Run([]string{"api", "show", "workflow.resolve", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("api show workflow.resolve exit code = %d; stdout=%s stderr=%s", code, stdout.String(), stderr.String())
	}
	capability := requireObject(t, requireObject(t, decodeJSONObject(t, stdout.Bytes()), "data"), "capability")
	usage, _ := capability["usage"].(string)
	contract, _ := capability["input_contract"].(string)
	for _, phrase := range []string{"--resolution-evidence", "--reopen-to", "--reopen-reason", "--reopen-evidence", "--invalidated-artifacts"} {
		if !strings.Contains(usage, phrase) {
			t.Fatalf("workflow.resolve usage = %q, missing %q", usage, phrase)
		}
	}
	for _, phrase := range []string{"all-or-none", "strict earlier stage", "blocker audit", "atomically"} {
		if !strings.Contains(contract, phrase) {
			t.Fatalf("workflow.resolve input_contract = %q, missing %q", contract, phrase)
		}
	}
}

func TestAPIShowTestDesignPublishesRecoveryAndConsumerReturnContracts(t *testing.T) {
	tests := []struct {
		capability string
		phrases    []string
	}{
		{capability: "test-design.status", phrases: []string{"recovery_action", "blocked", "stale", "agent-owned"}},
		{capability: "test-design.recover", phrases: []string{"runtime-owned", "CAS", "without inline input-json"}},
		{capability: "test-design.handoff", phrases: []string{"publish", "before Tasks", "next_argv"}},
		{capability: "test-design.projection-build", phrases: []string{"projection-verify", "next_argv"}},
		{capability: "test-design.projection-verify", phrases: []string{"selected consumer", "next_argv"}},
	}
	for _, test := range tests {
		t.Run(test.capability, func(t *testing.T) {
			var stdout, stderr bytes.Buffer
			code := Run([]string{"api", "show", test.capability, "--format", "json"}, &stdout, &stderr, "test")
			if code != 0 {
				t.Fatalf("api show %s exit=%d stdout=%s stderr=%s", test.capability, code, stdout.String(), stderr.String())
			}
			capability := requireObject(t, requireObject(t, decodeJSONObject(t, stdout.Bytes()), "data"), "capability")
			contract, _ := capability["input_contract"].(string)
			for _, phrase := range test.phrases {
				if !strings.Contains(contract, phrase) {
					t.Fatalf("%s input_contract=%q, missing %q", test.capability, contract, phrase)
				}
			}
		})
	}
}

func TestAPIPackReturnsCompactCapabilityDescriptors(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Run([]string{"api", "pack", "--capabilities", "artifact.patch,workflow.block", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("api pack exit code = %d; stdout=%s stderr=%s", code, stdout.String(), stderr.String())
	}
	payload := decodeJSONObject(t, stdout.Bytes())
	data := requireObject(t, payload, "data")
	if digest, ok := data["capability_set_sha256"].(string); !ok || len(digest) != 64 {
		t.Fatalf("api pack capability_set_sha256 = %#v", data["capability_set_sha256"])
	}
	items, ok := payload["items"].([]any)
	if !ok || len(items) != 2 {
		t.Fatalf("api pack items = %#v, want 2 entries", payload["items"])
	}
	first := requireObjectValue(t, items[0])
	if first["id"] != "artifact.patch" {
		t.Fatalf("api pack first item = %#v", first)
	}
	if _, ok := first["usage"].(string); !ok {
		t.Fatalf("api pack first item missing usage: %#v", first)
	}
	if first["schema_ref"] != "artifact-patch-input" {
		t.Fatalf("api pack first item schema_ref = %#v", first["schema_ref"])
	}
	if _, exists := first["schema"]; exists {
		t.Fatalf("api pack first item unexpectedly embedded schema: %#v", first)
	}
}

func TestAPIPackIncludesEmbeddedSchemaWhenRequested(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Run([]string{"api", "pack", "--capabilities", "workflow.block", "--include-schema", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("api pack --include-schema exit code = %d; stdout=%s stderr=%s", code, stdout.String(), stderr.String())
	}
	payload := decodeJSONObject(t, stdout.Bytes())
	items, ok := payload["items"].([]any)
	if !ok || len(items) != 1 {
		t.Fatalf("api pack items = %#v", payload["items"])
	}
	item := requireObjectValue(t, items[0])
	if item["schema_ref"] != "workflow-block-input" {
		t.Fatalf("api pack schema_ref = %#v", item["schema_ref"])
	}
	schema := requireObject(t, item, "schema")
	properties := requireObject(t, schema, "properties")
	if _, ok := properties["cause"]; !ok {
		t.Fatalf("api pack embedded schema = %#v", schema)
	}
	required, ok := schema["required"].([]any)
	if !ok || len(required) == 0 {
		t.Fatalf("api pack embedded schema required = %#v", schema["required"])
	}
}

func TestAPIPackRejectsUnknownDuplicateAndEmptyInput(t *testing.T) {
	for _, args := range [][]string{
		{"api", "pack", "--capabilities", "missing.capability", "--format", "json"},
		{"api", "pack", "--capabilities", "api.show,api.show", "--format", "json"},
		{"api", "pack", "--capabilities", "", "--format", "json"},
		{"api", "pack", "--format", "json"},
	} {
		var stdout, stderr bytes.Buffer
		code := Run(args, &stdout, &stderr, "test")
		if code != 2 {
			t.Fatalf("%v exit code = %d, want 2; stdout=%s stderr=%s", args, code, stdout.String(), stderr.String())
		}
	}
}

func TestAPIShowWorkBoardCapabilitiesPublishCoordinationContracts(t *testing.T) {
	for _, capabilityID := range []string{
		"quick.preflight",
		"board.show",
		"board.owner",
		"board.reconcile",
		"board.branch-policy",
		"board.feature-bootstrap",
		"work.begin",
		"work.show",
		"work.claim",
		"work.scope-add",
		"work.checkpoint",
		"work.block",
		"work.unblock",
		"work.finish",
		"work.abandon",
		"work.interrupt",
		"work.resume",
	} {
		t.Run(capabilityID, func(t *testing.T) {
			var stdout, stderr bytes.Buffer
			code := Run([]string{"api", "show", capabilityID, "--format", "json"}, &stdout, &stderr, "test")
			if code != 0 {
				t.Fatalf("api show %s exit code = %d; stdout=%s stderr=%s", capabilityID, code, stdout.String(), stderr.String())
			}
			payload := decodeJSONObject(t, stdout.Bytes())
			capability := requireObject(t, requireObject(t, payload, "data"), "capability")
			for _, field := range []string{"summary", "usage", "side_effect", "input_contract"} {
				value, ok := capability[field].(string)
				if !ok || strings.TrimSpace(value) == "" || value == "Runtime capability." {
					t.Fatalf("api show %s capability.%s = %#v, want a specific non-empty contract", capabilityID, field, capability[field])
				}
			}
		})
	}
}

func TestAPIShowBoardPublishesWritableCanonicalStoreAndAgentOwnedRecovery(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Run([]string{"api", "show", "board.show", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("api show board.show exit code = %d; stdout=%s stderr=%s", code, stdout.String(), stderr.String())
	}
	capability := requireObject(t, requireObject(t, decodeJSONObject(t, stdout.Bytes()), "data"), "capability")
	contract := anyString(capability["input_contract"])
	for _, phrase := range []string{".specify/runtime/run-control", "legacy Git-common", "agent-owned"} {
		if !strings.Contains(contract, phrase) {
			t.Fatalf("board.show input_contract = %q, missing %q", contract, phrase)
		}
	}
}

func TestAPIShowExecutionGuardPublishesAgentOwnedPacketScopeRecovery(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Run([]string{"api", "show", "execution.guard", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("api show execution.guard exit code = %d; stdout=%s stderr=%s", code, stdout.String(), stderr.String())
	}
	capability := requireObject(t, requireObject(t, decodeJSONObject(t, stdout.Bytes()), "data"), "capability")
	usage := anyString(capability["usage"])
	contract := anyString(capability["input_contract"])
	for _, phrase := range []string{"--expected-overview-revision", "--expected-overview-sha256", "--scope-amendments-json", "--reason"} {
		if !strings.Contains(usage, phrase) {
			t.Fatalf("execution.guard usage = %q, missing %q", usage, phrase)
		}
	}
	for _, phrase := range []string{"original packet", "agent-owned", "conflict", "late discovery", "independent"} {
		if !strings.Contains(contract, phrase) {
			t.Fatalf("execution.guard input_contract = %q, missing %q", contract, phrase)
		}
	}
}

func TestAPIShowExecutionCompletePublishesWorkflowControlPlaneAccounting(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Run([]string{"api", "show", "execution.complete", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("api show execution.complete exit code = %d; stdout=%s stderr=%s", code, stdout.String(), stderr.String())
	}
	capability := requireObject(t, requireObject(t, decodeJSONObject(t, stdout.Bytes()), "data"), "capability")
	contract := anyString(capability["input_contract"])
	for _, phrase := range []string{"workflow.json", "active Implement", "mutation receipt", "manual Implement", "legacy feature roots", "completion transaction", "authority release", "agent-owned", "workflow_control_plane_paths", "workflow_mutation_receipt_sha256", "workflow_audit_preserved"} {
		if !strings.Contains(contract, phrase) {
			t.Fatalf("execution.complete input_contract = %q, missing %q", contract, phrase)
		}
	}
}

func TestAPIShowWorkClaimPublishesSharedExecutionGate(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Run([]string{"api", "show", "work.claim", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("api show work.claim exit code = %d; stdout=%s stderr=%s", code, stdout.String(), stderr.String())
	}
	capability := requireObject(t, requireObject(t, decodeJSONObject(t, stdout.Bytes()), "data"), "capability")
	usage, _ := capability["usage"].(string)
	contract, _ := capability["input_contract"].(string)
	for _, phrase := range []string{"--current-work-id", "--current-work-fence", "--task-ref", "--write-scope-json"} {
		if !strings.Contains(usage, phrase) {
			t.Fatalf("work.claim usage = %q, missing %q", usage, phrase)
		}
	}
	for _, phrase := range []string{"Fast", "Debug", "Implement", "Quick", "all-or-none", "before source writes"} {
		if !strings.Contains(contract, phrase) {
			t.Fatalf("work.claim input_contract = %q, missing %q", contract, phrase)
		}
	}
}

func TestAPIShowQuickItemStartPublishesAtomicWorkClaimContract(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Run([]string{"api", "show", "quick.item-start", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("api show quick.item-start exit code = %d; stdout=%s stderr=%s", code, stdout.String(), stderr.String())
	}
	payload := decodeJSONObject(t, stdout.Bytes())
	capability := requireObject(t, requireObject(t, payload, "data"), "capability")
	usage, _ := capability["usage"].(string)
	contract, _ := capability["input_contract"].(string)
	if !strings.Contains(usage, "--current-work-id") || !strings.Contains(usage, "--current-work-fence") ||
		!strings.Contains(contract, "all-or-none") || !strings.Contains(contract, "task_ref") ||
		!strings.Contains(contract, "before changing the item to in_progress") {
		t.Fatalf("quick.item-start capability = %#v", capability)
	}
}

func TestAPIShowExecutionPacketCapabilitiesRequireCompiledReceiptDigest(t *testing.T) {
	for _, capabilityID := range []string{"execution.announce"} {
		t.Run(capabilityID, func(t *testing.T) {
			var stdout, stderr bytes.Buffer
			code := Run([]string{"api", "show", capabilityID, "--format", "json"}, &stdout, &stderr, "test")
			if code != 0 {
				t.Fatalf("api show %s exit code = %d; stdout=%s stderr=%s", capabilityID, code, stdout.String(), stderr.String())
			}
			capability := requireObject(t, requireObject(t, decodeJSONObject(t, stdout.Bytes()), "data"), "capability")
			usage, _ := capability["usage"].(string)
			contract, _ := capability["input_contract"].(string)
			if !strings.Contains(usage, "--work-packet-sha256 <sha256>") {
				t.Fatalf("api show %s usage = %q, want packet receipt digest", capabilityID, usage)
			}
			if !strings.Contains(contract, "exact compiled bytes") || !strings.Contains(contract, "sha256") {
				t.Fatalf("api show %s input_contract = %q, want exact-byte digest binding", capabilityID, contract)
			}
			for _, phrase := range []string{"exact future files", "final /**", "companion test", "validation commands", "workflow.json", "separately audited", "scope-amendment"} {
				if !strings.Contains(contract, phrase) {
					t.Fatalf("api show %s input_contract = %q, missing %q", capabilityID, contract, phrase)
				}
			}
		})
	}
}

func TestAPIShowImplementTaskStartPublishesConcreteCompanionScopeContract(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Run([]string{"api", "show", "implement.task-start", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("api show implement.task-start exit code = %d; stdout=%s stderr=%s", code, stdout.String(), stderr.String())
	}
	capability := requireObject(t, requireObject(t, decodeJSONObject(t, stdout.Bytes()), "data"), "capability")
	contract := anyString(capability["input_contract"])
	for _, phrase := range []string{"exact future files", "final /**", "companion test", "validation commands"} {
		if !strings.Contains(contract, phrase) {
			t.Fatalf("implement.task-start input_contract = %q, missing %q", contract, phrase)
		}
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
	if !strings.Contains(usage, "discussion bind-consumer") || !strings.Contains(usage, "--input-json") || !strings.Contains(usage, "--review-digest") {
		t.Fatalf("discussion bind-consumer capability = %#v", capability)
	}
	contract, _ := capability["input_contract"].(string)
	if !strings.Contains(contract, "runtime binds") || !strings.Contains(contract, "review digest") || !strings.Contains(contract, "always required") {
		t.Fatalf("discussion bind-consumer input contract = %#v", capability)
	}
}

func TestAPIShowDiscussionResolvePublishesExplicitSelectionContract(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Run([]string{"api", "show", "discussion.resolve", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("api show discussion.resolve exit code = %d; stdout=%s stderr=%s", code, stdout.String(), stderr.String())
	}
	payload := decodeJSONObject(t, stdout.Bytes())
	capability := requireObject(t, requireObject(t, payload, "data"), "capability")
	usage, _ := capability["usage"].(string)
	if !strings.Contains(usage, "discussion resolve") || !strings.Contains(usage, "--intent continue|sp-specify|sp-quick") || !strings.Contains(usage, "--slug") {
		t.Fatalf("discussion resolve usage = %#v", capability)
	}
	contract, _ := capability["input_contract"].(string)
	for _, fragment := range []string{
		"multiple candidates return blocked/ambiguous",
		"state_sha256",
		"source_contract",
		"recommended_consumer",
	} {
		if !strings.Contains(contract, fragment) {
			t.Fatalf("discussion resolve input contract = %q, missing %q", contract, fragment)
		}
	}
}

func TestAPISchemaImplementResultMergeInput(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Run([]string{"api", "schema", "implement-result-merge-input", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("api schema implement-result-merge-input exit=%d stdout=%s", code, stdout.String())
	}
	schema := requireObject(t, requireObject(t, decodeJSONObject(t, stdout.Bytes()), "data"), "schema")
	properties := requireObject(t, schema, "properties")
	if _, ok := properties["validation_results"]; !ok {
		t.Fatalf("schema missing validation_results: %#v", properties)
	}
	stdout.Reset()
	stderr.Reset()
	code = Run([]string{"api", "show", "implement.result-merge", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("api show implement.result-merge exit=%d stdout=%s", code, stdout.String())
	}
	capability := requireObject(t, requireObject(t, decodeJSONObject(t, stdout.Bytes()), "data"), "capability")
	if capability["input_schema"] != "implement-result-merge-input" {
		t.Fatalf("capability = %#v", capability)
	}
	contract, _ := capability["input_contract"].(string)
	if !strings.Contains(contract, "validation_results") {
		t.Fatalf("input_contract should document validation_results: %s", contract)
	}
}

func TestAPISchemaDiscussionWriteHandoffAndCheckpoint(t *testing.T) {
	for _, schemaID := range []string{"discussion-write-handoff-input", "discussion-checkpoint-input"} {
		var stdout, stderr bytes.Buffer
		code := Run([]string{"api", "schema", schemaID, "--format", "json"}, &stdout, &stderr, "test")
		if code != 0 {
			t.Fatalf("api schema %s exit code = %d; stdout=%s stderr=%s", schemaID, code, stdout.String(), stderr.String())
		}
		payload := decodeJSONObject(t, stdout.Bytes())
		schema := requireObject(t, requireObject(t, payload, "data"), "schema")
		if schema["type"] != "object" {
			t.Fatalf("%s schema = %#v", schemaID, schema)
		}
		properties := requireObject(t, schema, "properties")
		topicOwnership := requireObject(t, properties, "topic_ownership")
		topicProperties := requireObject(t, topicOwnership, "properties")
		if _, ok := topicProperties["owned_scope"]; !ok {
			t.Fatalf("%s topic_ownership missing owned_scope: %#v", schemaID, topicOwnership)
		}
		routedTopics := requireObject(t, topicProperties, "routed_topics")
		items := requireObject(t, routedTopics, "items")
		itemProperties := requireObject(t, items, "properties")
		route := requireObject(t, itemProperties, "route")
		enumValues, ok := route["enum"].([]any)
		if !ok || len(enumValues) != 4 {
			t.Fatalf("%s topic_ownership.route enum = %#v", schemaID, route["enum"])
		}
		for _, want := range []any{"continue_current", "branch_new", "link_existing", "defer"} {
			found := false
			for _, candidate := range enumValues {
				if candidate == want {
					found = true
					break
				}
			}
			if !found {
				t.Fatalf("%s topic_ownership.route enum missing %q: %#v", schemaID, want, enumValues)
			}
		}
		allOf, ok := items["allOf"].([]any)
		if !ok || len(allOf) == 0 {
			t.Fatalf("%s topic_ownership items missing target_slug conditional: %#v", schemaID, items)
		}
		foundTargetSlugGuard := false
		for _, clause := range allOf {
			clauseObj, ok := clause.(map[string]any)
			if !ok {
				continue
			}
			thenObj, ok := clauseObj["then"].(map[string]any)
			if !ok {
				continue
			}
			thenProps := requireObject(t, thenObj, "properties")
			targetSlug := requireObject(t, thenProps, "target_slug")
			if targetSlug["type"] != "string" || targetSlug["minLength"] != float64(1) {
				t.Fatalf("%s topic_ownership.target_slug guard = %#v", schemaID, targetSlug)
			}
			foundTargetSlugGuard = true
		}
		if !foundTargetSlugGuard {
			t.Fatalf("%s topic_ownership items missing branch/link target_slug type guard: %#v", schemaID, items)
		}
		if schemaID == "discussion-checkpoint-input" {
			for _, field := range []string{"requirements_snapshot", "implementation_target", "source_evidence", "source_materials", "blocking_unknowns", "conflicts", "downstream_instructions", "discussion_decision_digest", "must_preserve", "truth_pass_status", "advice_confidence", "discussion_compass_status", "design_context", "artifact_refs"} {
				if _, ok := properties[field]; !ok {
					t.Fatalf("%s missing semantic checkpoint field %q: %#v", schemaID, field, properties)
				}
			}
			sourceEvidence := requireObject(t, properties, "source_evidence")
			evidenceItems := requireObject(t, sourceEvidence, "items")
			evidenceProps := requireObject(t, evidenceItems, "properties")
			if _, ok := evidenceProps["material_id"]; !ok {
				t.Fatalf("%s source_evidence missing material_id: %#v", schemaID, sourceEvidence)
			}
			sourceMaterials := requireObject(t, properties, "source_materials")
			materialItems := requireObject(t, sourceMaterials, "items")
			materialProps := requireObject(t, materialItems, "properties")
			if _, ok := materialProps["material_digest"]; !ok {
				t.Fatalf("%s source_materials missing runtime material_digest: %#v", schemaID, sourceMaterials)
			}
		}
		if schemaID == "discussion-write-handoff-input" {
			if !strings.Contains(fmt.Sprint(schema["description"]), "current semantic checkpoint") {
				t.Fatalf("%s schema should explain checkpoint-derived handoff fields: %#v", schemaID, schema["description"])
			}
			for _, field := range []string{"agent_requirement_contract", "source_evidence", "source_materials", "hard_unknown_count", "open_conflict_count"} {
				entry := requireObject(t, properties, field)
				if entry["readOnly"] != true {
					t.Fatalf("%s field %q should be marked state-derived/readOnly: %#v", schemaID, field, entry)
				}
			}
		}
	}

	var stdout, stderr bytes.Buffer
	code := Run([]string{"api", "show", "discussion.write-handoff", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("api show discussion.write-handoff exit = %d stdout=%s", code, stdout.String())
	}
	capability := requireObject(t, requireObject(t, decodeJSONObject(t, stdout.Bytes()), "data"), "capability")
	if capability["input_schema"] != "discussion-write-handoff-input" {
		t.Fatalf("write-handoff capability = %#v", capability)
	}
	contract, _ := capability["input_contract"].(string)
	for _, fragment := range []string{"latest_checkpoint.snapshot_sha256", "discussion_snapshot_digest", "source_evidence/source_materials", "@path"} {
		if !strings.Contains(contract, fragment) {
			t.Fatalf("write-handoff input contract = %#v, missing %q", capability, fragment)
		}
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

func TestAPIShowSmoothnessLabPublishesDerivedManifestAndReportContracts(t *testing.T) {
	tests := []struct {
		capabilityID string
		usage        string
		contract     []string
	}{
		{
			capabilityID: "evidence.smoothness-manifest",
			usage:        "evidence smoothness-manifest",
			contract:     []string{"exact smoothness acceptance ids", "task-index.json", "stale task bindings are rejected"},
		},
		{
			capabilityID: "evidence.smoothness-validate",
			usage:        "evidence smoothness-validate",
			contract:     []string{"one passing observation per expected smoothness id", "task-bound budgets", "byte digest"},
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
			if !strings.Contains(usage, test.usage) {
				t.Fatalf("%s usage = %q", test.capabilityID, usage)
			}
			for _, want := range test.contract {
				if !strings.Contains(contract, want) {
					t.Fatalf("%s contract %q does not contain %q", test.capabilityID, contract, want)
				}
			}
		})
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
