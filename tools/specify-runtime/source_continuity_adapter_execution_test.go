package main

import (
	"encoding/json"
	"path/filepath"
	"strings"
	"testing"
)

func TestSourceContinuityToolInventoryBridgeMaterializesRegistryPlan(t *testing.T) {
	root, featureRef, feature := sourceContinuityLabProject(t)
	manifestRef, _ := materializeSourceContinuityLabManifest(t, root, featureRef)
	raw, err := json.Marshal(sourceContinuityToolInventoryInput())
	if err != nil {
		t.Fatal(err)
	}
	exit, env := runTaskRuntimeCommand(t, []string{
		"evidence", "source-continuity-adapter-bridge", "--project-root", root,
		"--feature-dir", featureRef, "--task-id", sourceContinuityLabTaskID,
		"--manifest", manifestRef, "--input-json", string(raw), "--format", "json",
	})
	if exit != 0 || env.Status != "ok" {
		t.Fatalf("tool inventory bridge failed: exit=%d env=%#v", exit, env)
	}
	inventoryRef := anyString(env.Data["tool_inventory_ref"])
	if inventoryRef != "implementation-review/source-continuity/source-continuity-tool-inventory-T901.json" {
		t.Fatalf("tool inventory ref = %q", inventoryRef)
	}
	inventoryPath := filepath.Join(feature, filepath.FromSlash(inventoryRef))
	inventory := readImplementJSONFile(t, inventoryPath)
	if inventory["schema"] != "spec-kit-source-continuity-tool-inventory-v1" || inventory["status"] != "ready" {
		t.Fatalf("tool inventory report = %#v", inventory)
	}
	visual := requireObjectValue(t, inventory["visual_capabilities"])
	if visual["image_generation"] != "available" || visual["image_inspection"] != "available" || visual["image_editing"] != "unavailable" {
		t.Fatalf("visual capabilities = %#v", visual)
	}
	probePath := filepath.Join(feature, filepath.FromSlash(anyString(env.Data["adapter_probe_ref"])))
	probe := readImplementJSONFile(t, probePath)
	bridge := requireObjectValue(t, probe["inventory_bridge"])
	if bridge["mode"] != "tool-inventory" || bridge["inventory_ref"] != inventoryRef || bridge["inventory_sha256"] != optionalFileSHA256(inventoryPath) {
		t.Fatalf("probe inventory bridge = %#v", bridge)
	}
	plan := readImplementJSONFile(t, filepath.Join(feature, filepath.FromSlash(anyString(env.Data["adapter_plan_ref"]))))
	selection := requireObjectValue(t, plan["selection"])
	if selection["mode"] != "registry-probe" || len(listValue(plan["assignments"])) != 10 {
		t.Fatalf("bridged adapter plan = %#v", plan)
	}
	for _, value := range listValue(plan["adapters"]) {
		adapter := requireObjectValue(t, value)
		if _, authored := adapter["provider_ids"]; authored {
			t.Fatalf("plan adapter leaked bridge-only provider ids: %#v", adapter)
		}
	}
}

func TestSourceContinuityToolInventoryBridgeRejectsContractInjection(t *testing.T) {
	root, featureRef, _ := sourceContinuityLabProject(t)
	manifestRef, _ := materializeSourceContinuityLabManifest(t, root, featureRef)
	input := sourceContinuityToolInventoryInput()
	tool := requireObjectValue(t, listValue(input["tools"])[0])
	tool["provider_ids"] = []any{"behavior-driver"}
	tool["actions"] = []any{"shell-exec"}
	raw, err := json.Marshal(input)
	if err != nil {
		t.Fatal(err)
	}
	exit, env := runTaskRuntimeCommand(t, []string{
		"evidence", "source-continuity-adapter-bridge", "--project-root", root,
		"--feature-dir", featureRef, "--task-id", sourceContinuityLabTaskID,
		"--manifest", manifestRef, "--input-json", string(raw), "--format", "json",
	})
	if exit != 2 || env.Status != "error" || !strings.Contains(strings.Join(anyStringSlice(env.Data["diagnostics"]), "\n"), "invalid-tool-inventory-entry") {
		t.Fatalf("tool inventory contract injection unexpectedly passed: exit=%d env=%#v", exit, env)
	}
}

func TestSourceContinuityAdapterExecutionCompilesProviderPackets(t *testing.T) {
	root, featureRef, feature := sourceContinuityLabProject(t)
	manifestRef, _ := materializeSourceContinuityLabManifest(t, root, featureRef)
	bridgeRaw, err := json.Marshal(sourceContinuityToolInventoryInput())
	if err != nil {
		t.Fatal(err)
	}
	exit, bridgeEnv := runTaskRuntimeCommand(t, []string{
		"evidence", "source-continuity-adapter-bridge", "--project-root", root,
		"--feature-dir", featureRef, "--task-id", sourceContinuityLabTaskID,
		"--manifest", manifestRef, "--input-json", string(bridgeRaw), "--format", "json",
	})
	if exit != 0 || bridgeEnv.Status != "ok" {
		t.Fatalf("adapter bridge failed: exit=%d env=%#v", exit, bridgeEnv)
	}
	exit, env := runTaskRuntimeCommand(t, []string{
		"evidence", "source-continuity-adapter-execution", "--project-root", root,
		"--feature-dir", featureRef, "--task-id", sourceContinuityLabTaskID,
		"--manifest", manifestRef,
		"--adapter-plan", anyString(bridgeEnv.Data["adapter_plan_ref"]),
		"--adapter-plan-sha256", anyString(bridgeEnv.Data["adapter_plan_sha256"]),
		"--format", "json",
	})
	if exit != 0 || env.Status != "ok" {
		t.Fatalf("adapter execution compile failed: exit=%d env=%#v", exit, env)
	}
	executionRef := anyString(env.Data["adapter_execution_ref"])
	if executionRef != "implementation-review/source-continuity/source-continuity-adapter-execution-T901.json" {
		t.Fatalf("adapter execution ref = %q", executionRef)
	}
	executionPath := filepath.Join(feature, filepath.FromSlash(executionRef))
	execution := readImplementJSONFile(t, executionPath)
	if execution["schema"] != "spec-kit-source-continuity-adapter-execution-v1" || execution["status"] != "ready" {
		t.Fatalf("adapter execution manifest = %#v", execution)
	}
	packets := listValue(execution["packets"])
	if len(packets) != 3 {
		t.Fatalf("adapter execution packets = %#v, want three selected adapters", packets)
	}
	foundTarget := false
	for _, value := range packets {
		packet := requireObjectValue(t, value)
		for _, forbidden := range []string{"command", "argv", "env", "script", "install"} {
			if _, exists := packet[forbidden]; exists {
				t.Fatalf("execution packet exposes forbidden field %q: %#v", forbidden, packet)
			}
		}
		if packet["adapter_id"] == "target-runtime" {
			foundTarget = true
			if len(listValue(packet["lanes"])) != 5 || len(listValue(packet["evidence_requirements"])) != 3 {
				t.Fatalf("target execution packet coverage = %#v", packet)
			}
			targets := requireObjectValue(t, packet["binding_targets"])
			if len(listValue(targets["surface_binding_ids"])) != 2 || len(listValue(targets["action_binding_ids"])) != 3 || len(listValue(targets["asset_binding_ids"])) != 1 {
				t.Fatalf("target execution binding targets = %#v", targets)
			}
			if len(listValue(packet["stop_conditions"])) == 0 || len(listValue(packet["preconditions"])) == 0 {
				t.Fatalf("target execution safety contract = %#v", packet)
			}
		}
	}
	if !foundTarget {
		t.Fatalf("target runtime packet missing: %#v", packets)
	}
	if env.Data["adapter_execution_sha256"] != optionalFileSHA256(executionPath) {
		t.Fatalf("adapter execution digest = %#v", env.Data)
	}
}

func TestSourceContinuityToolInventoryBridgeSupportsQuick(t *testing.T) {
	quickID := "260828-tool-inventory"
	input := sourceContinuityQuickInput()
	decision := requireObjectValue(t, input["decision"])
	items := listValue(decision["items"])
	requireObjectValue(t, items[0])["write_scope"] = []any{"src/**"}
	requireObjectValue(t, decision["ui_confirmation"])["source_continuity"] = sourceContinuityLabContract()
	root, workspace := stageConfirmedQuickExecutionTestWorkspace(t, quickID, input)
	quickEnv := runScriptDomainEnvelope(t, runQuick, []string{"--project-root", root, "item-start", quickID, "--item", "Q1"})
	if quickEnv.Status != "ok" {
		t.Fatalf("quick item start failed: %#v", quickEnv)
	}
	exit, manifestEnv := runTaskRuntimeCommand(t, []string{
		"evidence", "source-continuity-manifest", "--project-root", root,
		"--quick-id", quickID, "--item-id", "Q1", "--format", "json",
	})
	if exit != 0 || manifestEnv.Status != "ok" {
		t.Fatalf("quick manifest failed: exit=%d env=%#v", exit, manifestEnv)
	}
	raw, err := json.Marshal(sourceContinuityToolInventoryInput())
	if err != nil {
		t.Fatal(err)
	}
	exit, env := runTaskRuntimeCommand(t, []string{
		"evidence", "source-continuity-adapter-bridge", "--project-root", root,
		"--quick-id", quickID, "--item-id", "Q1",
		"--manifest", anyString(manifestEnv.Data["manifest_ref"]),
		"--input-json", string(raw), "--format", "json",
	})
	if exit != 0 || env.Status != "ok" {
		t.Fatalf("quick tool inventory bridge failed: exit=%d env=%#v", exit, env)
	}
	if anyString(env.Data["tool_inventory_ref"]) != "source-continuity/source-continuity-tool-inventory-Q1.json" {
		t.Fatalf("quick tool inventory ref = %#v", env.Data)
	}
	inventory := readImplementJSONFile(t, filepath.Join(workspace, filepath.FromSlash(anyString(env.Data["tool_inventory_ref"]))))
	if inventory["status"] != "ready" || inventory["subject_id"] != "Q1" {
		t.Fatalf("quick tool inventory = %#v", inventory)
	}
}

func sourceContinuityToolInventoryInput() map[string]any {
	return map[string]any{
		"schema": "spec-kit-source-continuity-tool-inventory-input-v1",
		"source": map[string]any{
			"kind": "live-session", "captured_by": "agent-observation", "freshness": "current",
		},
		"tools": []any{
			map[string]any{
				"id": "source-observer", "tool_ref": "tool://source-observer",
				"signals": []any{"source-resource-inspection", "image-inspection", "image-generation"},
				"roles":   []any{"source"}, "execution_mode": "agent-tool",
				"available": true, "unavailable_reason": "",
			},
			map[string]any{
				"id": "source-behavior", "tool_ref": "runner://source-behavior",
				"signals": []any{"desktop-automation"}, "roles": []any{"source"},
				"execution_mode": "external-runner", "available": true, "unavailable_reason": "",
			},
			map[string]any{
				"id": "target-runtime", "tool_ref": "app://target-runtime",
				"signals": []any{"dom-accessibility-inspection", "browser-automation", "screenshot-capture", "image-inspection"},
				"roles":   []any{"target"}, "execution_mode": "app-connector",
				"available": true, "unavailable_reason": "",
			},
		},
		"policy": map[string]any{
			"allow_manual_attested": false, "preferred_tool_ids": []any{},
		},
	}
}
