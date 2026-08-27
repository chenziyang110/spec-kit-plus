package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestSourceContinuityAdapterCatalogIsGenericAndDeterministic(t *testing.T) {
	exit, env := runTaskRuntimeCommand(t, []string{
		"evidence", "source-continuity-adapter-catalog", "--format", "json",
	})
	if exit != 0 || env.Status != "ok" {
		t.Fatalf("adapter catalog failed: exit=%d env=%#v", exit, env)
	}
	if env.Data["schema"] != "spec-kit-source-continuity-adapter-registry-v1" {
		t.Fatalf("adapter catalog schema = %#v", env.Data["schema"])
	}
	if digest := anyString(env.Data["registry_sha256"]); !reviewSHA256RE.MatchString(digest) {
		t.Fatalf("adapter catalog digest = %#v", digest)
	}
	providers := listValue(env.Data["providers"])
	if len(providers) != 3 {
		t.Fatalf("adapter providers = %#v, want three atomic provider packs", providers)
	}
	rendered, err := json.Marshal(env.Data)
	if err != nil {
		t.Fatal(err)
	}
	lower := strings.ToLower(string(rendered))
	for _, forbidden := range []string{"qt", "tauri", "react", "flutter", "swiftui"} {
		if strings.Contains(lower, forbidden) {
			t.Fatalf("generic adapter catalog contains platform/framework name %q: %s", forbidden, lower)
		}
	}

	exit, second := runTaskRuntimeCommand(t, []string{
		"evidence", "source-continuity-adapter-catalog", "--format", "json",
	})
	if exit != 0 || second.Data["registry_sha256"] != env.Data["registry_sha256"] {
		t.Fatalf("adapter catalog is not deterministic: first=%#v second=%#v", env.Data, second.Data)
	}
}

func TestSourceContinuityAdapterProbeMaterializesFormalPlan(t *testing.T) {
	root, featureRef, feature := sourceContinuityLabProject(t)
	manifestRef, manifestSHA := materializeSourceContinuityLabManifest(t, root, featureRef)
	raw, err := json.Marshal(sourceContinuityAdapterProbeInput())
	if err != nil {
		t.Fatal(err)
	}
	exit, env := runTaskRuntimeCommand(t, []string{
		"evidence", "source-continuity-adapter-probe", "--project-root", root,
		"--feature-dir", featureRef, "--task-id", sourceContinuityLabTaskID,
		"--manifest", manifestRef, "--input-json", string(raw), "--format", "json",
	})
	if exit != 0 || env.Status != "ok" {
		t.Fatalf("formal adapter probe failed: exit=%d env=%#v", exit, env)
	}
	probeRef := anyString(env.Data["adapter_probe_ref"])
	planRef := anyString(env.Data["adapter_plan_ref"])
	if probeRef != "implementation-review/source-continuity/source-continuity-adapter-probe-T901.json" || planRef != sourceContinuityAdapterPlanRef(sourceContinuityLabTaskID) {
		t.Fatalf("formal adapter refs = probe %q plan %q", probeRef, planRef)
	}
	probePath := filepath.Join(feature, filepath.FromSlash(probeRef))
	planPath := filepath.Join(feature, filepath.FromSlash(planRef))
	probe := readImplementJSONFile(t, probePath)
	plan := readImplementJSONFile(t, planPath)
	if probe["schema"] != "spec-kit-source-continuity-adapter-probe-v1" || probe["status"] != "ready" || len(listValue(probe["assignments"])) != 10 {
		t.Fatalf("formal adapter probe = %#v", probe)
	}
	selection := requireObjectValue(t, plan["selection"])
	if selection["mode"] != "registry-probe" || selection["probe_ref"] != probeRef || selection["probe_sha256"] != optionalFileSHA256(probePath) || selection["registry_sha256"] != probe["registry_sha256"] {
		t.Fatalf("registry-bound plan selection = %#v", selection)
	}
	if env.Data["adapter_probe_sha256"] != optionalFileSHA256(probePath) || env.Data["adapter_plan_sha256"] != optionalFileSHA256(planPath) {
		t.Fatalf("adapter probe digests = %#v", env.Data)
	}
	binding := requireObjectValue(t, env.Data["adapter_binding"])
	composite := requireObjectValue(t, binding["adapter"])
	if !strings.HasPrefix(anyString(composite["id"]), "adapter-plan:") || len(listValue(composite["capabilities"])) != 5 {
		t.Fatalf("adapter probe binding = %#v", binding)
	}

	observation := readSourceContinuityLabObservation(t, "passing-observation.json", manifestSHA)
	bindSourceContinuityAdapterPlanToObservation(observation, planRef, anyString(env.Data["adapter_plan_sha256"]), composite)
	adapterByEvidence := map[string]string{}
	for _, value := range listValue(plan["assignments"]) {
		assignment := requireObjectValue(t, value)
		side := anyString(assignment["side"])
		capability := anyString(assignment["capability"])
		kind := sourceContinuityAdapterCapabilityEvidence[capability]
		key := side + ":" + kind
		if adapterByEvidence[key] == "" {
			adapterByEvidence[key] = anyString(assignment["adapter_id"])
		}
	}
	for _, value := range listValue(observation["evidence_refs"]) {
		row := requireObjectValue(t, value)
		row["adapter_id"] = adapterByEvidence[anyString(row["side"])+":"+anyString(row["kind"])]
	}
	bindSourceContinuityLabEvidence(t, root, observation)
	observedRaw, err := json.Marshal(observation)
	if err != nil {
		t.Fatal(err)
	}
	exit, reportEnv := runTaskRuntimeCommand(t, []string{
		"evidence", "source-continuity-validate", "--project-root", root,
		"--feature-dir", featureRef, "--task-id", sourceContinuityLabTaskID,
		"--manifest", manifestRef, "--adapter-plan", planRef,
		"--input-json", string(observedRaw), "--format", "json",
	})
	if exit != 0 || reportEnv.Status != "ok" {
		t.Fatalf("registry-probed plan did not validate observations: exit=%d env=%#v", exit, reportEnv)
	}
}

func TestSourceContinuityAdapterProbeReportsRecoverableCoverageGaps(t *testing.T) {
	root, featureRef, feature := sourceContinuityLabProject(t)
	manifestRef, _ := materializeSourceContinuityLabManifest(t, root, featureRef)
	input := sourceContinuityAdapterProbeInput()
	bindings := listValue(input["bindings"])
	input["bindings"] = []any{bindings[0], bindings[2]}
	raw, err := json.Marshal(input)
	if err != nil {
		t.Fatal(err)
	}
	exit, env := runTaskRuntimeCommand(t, []string{
		"evidence", "source-continuity-adapter-probe", "--project-root", root,
		"--feature-dir", featureRef, "--task-id", sourceContinuityLabTaskID,
		"--manifest", manifestRef, "--input-json", string(raw), "--format", "json",
	})
	if exit != 2 || env.Status != "error" {
		t.Fatalf("incomplete adapter probe unexpectedly passed: exit=%d env=%#v", exit, env)
	}
	diagnostics := strings.Join(anyStringSlice(env.Data["diagnostics"]), "\n")
	for _, marker := range []string{"missing-adapter-lane:source.action-execution", "missing-adapter-lane:source.side-effect-observation"} {
		if !strings.Contains(diagnostics, marker) {
			t.Fatalf("adapter probe diagnostics missing %q: %s", marker, diagnostics)
		}
	}
	if len(env.NextArgv) == 0 || !strings.Contains(strings.Join(env.NextArgv, " "), "source-continuity-adapter-catalog") {
		t.Fatalf("adapter probe recovery action = %#v", env.NextArgv)
	}
	probeRef := anyString(env.Data["adapter_probe_ref"])
	probe := readImplementJSONFile(t, filepath.Join(feature, filepath.FromSlash(probeRef)))
	if probe["status"] != "blocked" || len(listValue(probe["unresolved_gaps"])) == 0 {
		t.Fatalf("blocked adapter probe report = %#v", probe)
	}
	if _, err := os.Stat(filepath.Join(feature, filepath.FromSlash(sourceContinuityAdapterPlanRef(sourceContinuityLabTaskID)))); !os.IsNotExist(err) {
		t.Fatalf("blocked probe must not materialize a plan: %v", err)
	}
}

func TestSourceContinuityAdapterProbeRejectsProviderContractInjection(t *testing.T) {
	root, featureRef, _ := sourceContinuityLabProject(t)
	manifestRef, _ := materializeSourceContinuityLabManifest(t, root, featureRef)
	input := sourceContinuityAdapterProbeInput()
	bindings := listValue(input["bindings"])
	first := requireObjectValue(t, bindings[0])
	first["actions"] = []any{"shell-exec"}
	second := requireObjectValue(t, bindings[1])
	second["provider_ids"] = []any{"unknown-provider"}
	raw, err := json.Marshal(input)
	if err != nil {
		t.Fatal(err)
	}
	exit, env := runTaskRuntimeCommand(t, []string{
		"evidence", "source-continuity-adapter-probe", "--project-root", root,
		"--feature-dir", featureRef, "--task-id", sourceContinuityLabTaskID,
		"--manifest", manifestRef, "--input-json", string(raw), "--format", "json",
	})
	if exit != 2 || env.Status != "error" {
		t.Fatalf("provider contract injection unexpectedly passed: exit=%d env=%#v", exit, env)
	}
	diagnostics := strings.Join(anyStringSlice(env.Data["diagnostics"]), "\n")
	for _, marker := range []string{"invalid-adapter-probe-binding", "unknown-adapter-provider:unknown-provider"} {
		if !strings.Contains(diagnostics, marker) {
			t.Fatalf("provider injection diagnostics missing %q: %s", marker, diagnostics)
		}
	}
}

func TestSourceContinuityAdapterProbeSupportsQuickAndPreferredBinding(t *testing.T) {
	quickID := "260828-adapter-probe"
	input := sourceContinuityQuickInput()
	decision := requireObjectValue(t, input["decision"])
	items := listValue(decision["items"])
	requireObjectValue(t, items[0])["write_scope"] = []any{"src/**"}
	requireObjectValue(t, decision["ui_confirmation"])["source_continuity"] = sourceContinuityLabContract()
	root, workspace := stageConfirmedQuickExecutionTestWorkspace(t, quickID, input)
	quickEnv := runScriptDomainEnvelope(t, runQuick, []string{
		"--project-root", root, "item-start", quickID, "--item", "Q1",
	})
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
	probeInput := sourceContinuityAdapterProbeInput()
	bindings := listValue(probeInput["bindings"])
	bindings = append(bindings, map[string]any{
		"id": "target-runtime-secondary", "provider_ids": []any{"behavior-driver"},
		"roles": []any{"target"}, "tool_ref": "runner://target-secondary",
		"execution_mode": "external-runner", "available": true, "unavailable_reason": "",
	})
	probeInput["bindings"] = bindings
	policy := requireObjectValue(t, probeInput["policy"])
	policy["preferred_binding_ids"] = []any{"target-runtime-secondary", "target-runtime"}
	raw, err := json.Marshal(probeInput)
	if err != nil {
		t.Fatal(err)
	}
	exit, env := runTaskRuntimeCommand(t, []string{
		"evidence", "source-continuity-adapter-probe", "--project-root", root,
		"--quick-id", quickID, "--item-id", "Q1",
		"--manifest", anyString(manifestEnv.Data["manifest_ref"]),
		"--input-json", string(raw), "--format", "json",
	})
	if exit != 0 || env.Status != "ok" {
		t.Fatalf("quick adapter probe failed: exit=%d env=%#v", exit, env)
	}
	probeRef := anyString(env.Data["adapter_probe_ref"])
	if probeRef != "source-continuity/source-continuity-adapter-probe-Q1.json" {
		t.Fatalf("quick adapter probe ref = %q", probeRef)
	}
	probe := readImplementJSONFile(t, filepath.Join(workspace, filepath.FromSlash(probeRef)))
	assignments := listValue(probe["assignments"])
	foundPreferred := false
	for _, value := range assignments {
		row := requireObjectValue(t, value)
		if row["side"] == "target" && row["capability"] == "action-execution" {
			foundPreferred = row["adapter_id"] == "target-runtime-secondary"
		}
	}
	if !foundPreferred {
		t.Fatalf("preferred binding was not selected: %#v", assignments)
	}
	plan := readImplementJSONFile(t, filepath.Join(workspace, filepath.FromSlash(anyString(env.Data["adapter_plan_ref"]))))
	selection := requireObjectValue(t, plan["selection"])
	if selection["mode"] != "registry-probe" || selection["probe_ref"] != probeRef {
		t.Fatalf("quick registry-bound plan = %#v", plan)
	}
}

func sourceContinuityAdapterProbeInput() map[string]any {
	return map[string]any{
		"schema": "spec-kit-source-continuity-adapter-probe-input-v1",
		"bindings": []any{
			map[string]any{
				"id": "source-observer", "provider_ids": []any{"structure-observer", "visual-asset-observer"},
				"roles": []any{"source"}, "tool_ref": "tool://source-observer",
				"execution_mode": "agent-tool", "available": true, "unavailable_reason": "",
			},
			map[string]any{
				"id": "source-behavior", "provider_ids": []any{"behavior-driver"},
				"roles": []any{"source"}, "tool_ref": "runner://source-behavior",
				"execution_mode": "external-runner", "available": true, "unavailable_reason": "",
			},
			map[string]any{
				"id": "target-runtime", "provider_ids": []any{"structure-observer", "behavior-driver", "visual-asset-observer"},
				"roles": []any{"target"}, "tool_ref": "app://target-runtime",
				"execution_mode": "app-connector", "available": true, "unavailable_reason": "",
			},
		},
		"policy": map[string]any{
			"allow_manual_attested": false,
			"preferred_binding_ids": []any{},
		},
	}
}
