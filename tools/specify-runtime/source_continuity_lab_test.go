package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
)

const sourceContinuityLabTaskID = "T901"

func TestSourceContinuityLabMaterializesManifestAndPassingReport(t *testing.T) {
	root, featureRef, feature := sourceContinuityLabProject(t)
	manifestRef, manifestSHA := materializeSourceContinuityLabManifest(t, root, featureRef)

	manifest := readImplementJSONFile(t, filepath.Join(feature, filepath.FromSlash(manifestRef)))
	if manifest["schema"] != "spec-kit-source-continuity-lab-manifest-v1" || manifest["task_id"] != sourceContinuityLabTaskID {
		t.Fatalf("source continuity manifest = %#v", manifest)
	}
	contract := requireObjectValue(t, manifest["source_continuity"])
	coverage := requireObjectValue(t, contract["coverage"])
	if len(listValue(coverage["surface_ids"])) != 2 || len(listValue(coverage["interaction_ids"])) != 3 || len(listValue(coverage["component_ids"])) != 1 {
		t.Fatalf("manifest coverage = %#v", coverage)
	}

	observation := readSourceContinuityLabObservation(t, "passing-observation.json", manifestSHA)
	bindSourceContinuityLabEvidence(t, root, observation)
	raw, err := json.Marshal(observation)
	if err != nil {
		t.Fatal(err)
	}
	exit, env := runTaskRuntimeCommand(t, []string{
		"evidence", "source-continuity-validate", "--project-root", root,
		"--feature-dir", featureRef, "--task-id", sourceContinuityLabTaskID,
		"--manifest", manifestRef, "--input-json", string(raw), "--format", "json",
	})
	if exit != 0 || env.Status != "ok" {
		t.Fatalf("source continuity validation failed: exit=%d env=%#v", exit, env)
	}
	reportRef := anyString(env.Data["report_ref"])
	reportPath := filepath.Join(feature, filepath.FromSlash(reportRef))
	report := readImplementJSONFile(t, reportPath)
	if report["schema"] != "spec-kit-source-continuity-lab-report-v1" || report["verdict"] != "passed" {
		t.Fatalf("source continuity report = %#v", report)
	}
	metrics := requireObjectValue(t, report["metrics"])
	for _, field := range []string{"source_discovery_coverage", "target_surface_reachability", "action_operability", "business_outcome_parity", "asset_fidelity"} {
		if metrics[field] != float64(1) {
			t.Fatalf("report metric %s = %#v, want 1", field, metrics[field])
		}
	}
	if env.Data["report_sha256"] != optionalFileSHA256(reportPath) {
		t.Fatalf("report digest = %#v", env.Data)
	}
	patch := requireObjectValue(t, env.Data["ui_verification_patch"])
	if patch["source_continuity_lab_report_ref"] != reportRef || patch["source_continuity_lab_report_sha256"] != env.Data["report_sha256"] {
		t.Fatalf("ui verification patch = %#v", patch)
	}

	exit, generic := runTaskRuntimeCommand(t, []string{
		"artifact", "prepare", "--project-root", root,
		"--path", sourceContinuityLabCanonicalPath(root, feature, reportRef), "--format", "json",
	})
	if exit != 2 || generic.Data["owner"] != "specify-runtime evidence source-continuity-manifest / source-continuity-validate" {
		t.Fatalf("generic report mutation should block: exit=%d env=%#v", exit, generic)
	}
}

func TestSourceContinuityLabRejectsShallowTargetAndCharacterIcon(t *testing.T) {
	root, featureRef, _ := sourceContinuityLabProject(t)
	manifestRef, manifestSHA := materializeSourceContinuityLabManifest(t, root, featureRef)
	observation := readSourceContinuityLabObservation(t, "shallow-target-observation.json", manifestSHA)
	bindSourceContinuityLabEvidence(t, root, observation)
	raw, err := json.Marshal(observation)
	if err != nil {
		t.Fatal(err)
	}
	exit, env := runTaskRuntimeCommand(t, []string{
		"evidence", "source-continuity-validate", "--project-root", root,
		"--feature-dir", featureRef, "--task-id", sourceContinuityLabTaskID,
		"--manifest", manifestRef, "--input-json", string(raw), "--format", "json",
	})
	if exit != 2 || env.Status != "error" {
		t.Fatalf("shallow target unexpectedly passed: exit=%d env=%#v", exit, env)
	}
	diagnostics := strings.Join(anyStringSlice(env.Data["diagnostics"]), "\n")
	for _, code := range []string{
		"target-surface-unreachable",
		"action-coverage-mismatch",
		"target-action-unreachable",
		"business-outcome-mismatch",
		"asset-character-substitution",
		"asset-fidelity-mismatch",
	} {
		if !strings.Contains(diagnostics, code) {
			t.Fatalf("diagnostics missing %q: %s", code, diagnostics)
		}
	}
}

func TestSourceContinuityLabRejectsAdapterDiscoveredCandidateOutsideContract(t *testing.T) {
	root, featureRef, _ := sourceContinuityLabProject(t)
	manifestRef, manifestSHA := materializeSourceContinuityLabManifest(t, root, featureRef)
	observation := readSourceContinuityLabObservation(t, "passing-observation.json", manifestSHA)
	bindSourceContinuityLabEvidence(t, root, observation)
	discovery := requireObjectValue(t, observation["discovery"])
	discovery["unexpected_candidates"] = []any{map[string]any{
		"id": "legacy-system-tray", "kind": "surface",
		"source_ref": "legacy/runtime#system-tray", "reason": "Runtime adapter discovered an undeclared tray menu.",
	}}
	raw, err := json.Marshal(observation)
	if err != nil {
		t.Fatal(err)
	}
	exit, env := runTaskRuntimeCommand(t, []string{
		"evidence", "source-continuity-validate", "--project-root", root,
		"--feature-dir", featureRef, "--task-id", sourceContinuityLabTaskID,
		"--manifest", manifestRef, "--input-json", string(raw), "--format", "json",
	})
	if exit != 2 || env.Status != "error" {
		t.Fatalf("unbound discovery unexpectedly passed: exit=%d env=%#v", exit, env)
	}
	diagnostics := strings.Join(anyStringSlice(env.Data["diagnostics"]), "\n")
	if !strings.Contains(diagnostics, "unbound-source-candidate") {
		t.Fatalf("unexpected discovery diagnostics = %s", diagnostics)
	}
}

func TestSourceContinuityLabRejectsIncompleteAdapterAndEvidence(t *testing.T) {
	root, featureRef, _ := sourceContinuityLabProject(t)
	manifestRef, manifestSHA := materializeSourceContinuityLabManifest(t, root, featureRef)
	observation := readSourceContinuityLabObservation(t, "passing-observation.json", manifestSHA)
	bindSourceContinuityLabEvidence(t, root, observation)
	adapter := requireObjectValue(t, observation["adapter"])
	adapter["capabilities"] = []any{"surface-enumeration"}
	observation["evidence_refs"] = []any{}
	raw, err := json.Marshal(observation)
	if err != nil {
		t.Fatal(err)
	}
	exit, env := runTaskRuntimeCommand(t, []string{
		"evidence", "source-continuity-validate", "--project-root", root,
		"--feature-dir", featureRef, "--task-id", sourceContinuityLabTaskID,
		"--manifest", manifestRef, "--input-json", string(raw), "--format", "json",
	})
	if exit != 2 || env.Status != "error" {
		t.Fatalf("incomplete adapter unexpectedly passed: exit=%d env=%#v", exit, env)
	}
	diagnostics := strings.Join(anyStringSlice(env.Data["diagnostics"]), "\n")
	for _, marker := range []string{"missing-adapter-capability", "missing-source-structure-snapshot", "missing-target-runtime-diagnostics", "action-evidence-unbound", "asset-evidence-unbound"} {
		if !strings.Contains(diagnostics, marker) {
			t.Fatalf("incomplete adapter diagnostics missing %q: %s", marker, diagnostics)
		}
	}
}

func TestSourceContinuityLabRejectsUnregisteredEvidenceReferences(t *testing.T) {
	root, featureRef, _ := sourceContinuityLabProject(t)
	manifestRef, manifestSHA := materializeSourceContinuityLabManifest(t, root, featureRef)
	observation := readSourceContinuityLabObservation(t, "passing-observation.json", manifestSHA)
	raw, err := json.Marshal(observation)
	if err != nil {
		t.Fatal(err)
	}
	exit, env := runTaskRuntimeCommand(t, []string{
		"evidence", "source-continuity-validate", "--project-root", root,
		"--feature-dir", featureRef, "--task-id", sourceContinuityLabTaskID,
		"--manifest", manifestRef, "--input-json", string(raw), "--format", "json",
	})
	if exit != 2 || env.Status != "error" {
		t.Fatalf("unregistered evidence references unexpectedly passed: exit=%d env=%#v", exit, env)
	}
	diagnostics := strings.Join(anyStringSlice(env.Data["diagnostics"]), "\n")
	if !strings.Contains(diagnostics, "unverified-evidence-ref") {
		t.Fatalf("unregistered evidence diagnostics = %s", diagnostics)
	}
}

func TestSourceContinuityLabManifestReportsNotApplicableTask(t *testing.T) {
	root := t.TempDir()
	featureRef := filepath.ToSlash(filepath.Join(".specify", "features", "010-no-source-continuity"))
	feature := filepath.Join(root, filepath.FromSlash(featureRef))
	if err := os.MkdirAll(feature, 0o755); err != nil {
		t.Fatal(err)
	}
	writeTaskRuntimeFixture(t, filepath.Join(feature, "task-index.json"), map[string]any{
		"version": 2, "status": "ready",
		"tasks": []any{map[string]any{"id": "T902", "ui_contract": map[string]any{"fidelity_level": "none"}}},
	})
	exit, env := runTaskRuntimeCommand(t, []string{
		"evidence", "source-continuity-manifest", "--project-root", root,
		"--feature-dir", featureRef, "--task-id", "T902", "--format", "json",
	})
	if exit != 0 || env.Status != "ok" || env.Data["applicable"] != false || env.Data["status"] != "not-applicable" {
		t.Fatalf("not-applicable source continuity manifest = exit %d env %#v", exit, env)
	}
}

func TestSourceContinuityLabHelperBoundaries(t *testing.T) {
	if sourceContinuityLabRatio(0, 0) != 1 {
		t.Fatal("empty continuity universe must be complete")
	}
	if values := sourceContinuityLabStringList("not-an-array"); len(values) != 0 {
		t.Fatalf("malformed continuity list = %#v", values)
	}
	if object := requireSourceContinuityLabObject(map[string]any{}, "missing"); len(object) != 0 {
		t.Fatalf("missing continuity object = %#v", object)
	}
	if err := validateSourceContinuityLabArtifactOwner("not/a/registered/path.json"); err == nil {
		t.Fatal("unregistered feature lab path should fail ownership")
	}
	if err := validateQuickSourceContinuityLabArtifactOwner("not/a/registered/path.json"); err == nil {
		t.Fatal("unregistered quick lab path should fail ownership")
	}
}

func TestSourceContinuityLabTargetSnapshotHandlesBroadAndGlobScopes(t *testing.T) {
	root := t.TempDir()
	productPath := filepath.Join(root, "src", "app.ts")
	runtimePath := filepath.Join(root, ".planning", "quick", "state.json")
	if err := os.MkdirAll(filepath.Dir(productPath), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Dir(runtimePath), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(productPath, []byte("v1\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(runtimePath, []byte("runtime-v1\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	broadBefore, err := sourceContinuityLabTargetSnapshot(root, []string{"."})
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(runtimePath, []byte("runtime-v2\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	broadAfterRuntime, err := sourceContinuityLabTargetSnapshot(root, []string{"."})
	if err != nil {
		t.Fatal(err)
	}
	if broadBefore != broadAfterRuntime {
		t.Fatal("runtime-owned state must not invalidate the target snapshot")
	}
	if err := os.WriteFile(productPath, []byte("v2\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	broadAfterProduct, err := sourceContinuityLabTargetSnapshot(root, []string{"."})
	if err != nil {
		t.Fatal(err)
	}
	if broadAfterProduct == broadBefore {
		t.Fatal("product changes must invalidate the target snapshot")
	}
	if _, err := sourceContinuityLabTargetSnapshot(root, []string{"src/*"}); err != nil {
		t.Fatalf("single-star write scope must resolve to its real directory: %v", err)
	}
	if _, err := sourceContinuityLabTargetSnapshot(root, []string{".planning/**"}); err == nil {
		t.Fatal("runtime-owned write scope must be rejected")
	}
}

func TestSourceContinuityAdapterPlanComposesGenericAdapters(t *testing.T) {
	root, featureRef, feature := sourceContinuityLabProject(t)
	manifestRef, _ := materializeSourceContinuityLabManifest(t, root, featureRef)
	input := sourceContinuityAdapterPlanInput()
	raw, err := json.Marshal(input)
	if err != nil {
		t.Fatal(err)
	}
	exit, env := runTaskRuntimeCommand(t, []string{
		"evidence", "source-continuity-adapter-plan", "--project-root", root,
		"--feature-dir", featureRef, "--task-id", sourceContinuityLabTaskID,
		"--manifest", manifestRef, "--input-json", string(raw), "--format", "json",
	})
	if exit != 0 || env.Status != "ok" {
		t.Fatalf("generic adapter plan failed: exit=%d env=%#v", exit, env)
	}
	planRef := anyString(env.Data["adapter_plan_ref"])
	planPath := filepath.Join(feature, filepath.FromSlash(planRef))
	plan := readImplementJSONFile(t, planPath)
	if plan["schema"] != "spec-kit-source-continuity-adapter-plan-v1" || plan["status"] != "ready" || plan["subject_id"] != sourceContinuityLabTaskID {
		t.Fatalf("adapter plan = %#v", plan)
	}
	if len(listValue(plan["required_lanes"])) != 10 || len(listValue(plan["assignments"])) != 10 || len(listValue(plan["adapters"])) != 3 {
		t.Fatalf("adapter plan coverage = %#v", plan)
	}
	if env.Data["adapter_plan_sha256"] != optionalFileSHA256(planPath) {
		t.Fatalf("adapter plan digest = %#v", env.Data)
	}
	binding := requireObjectValue(t, env.Data["adapter_binding"])
	composite := requireObjectValue(t, binding["adapter"])
	if !strings.HasPrefix(anyString(composite["id"]), "adapter-plan:") || len(listValue(composite["capabilities"])) != 5 {
		t.Fatalf("adapter binding = %#v", binding)
	}
	canonical := sourceContinuityLabCanonicalPath(root, feature, planRef)
	metadata, ok := LookupArtifactType(canonical)
	if !ok || metadata.TypeID != "feature-source-continuity-lab" {
		t.Fatalf("adapter plan owner = %#v ok=%t", metadata, ok)
	}
}

func TestSourceContinuityAdapterPlanRejectsCoverageGapAndUnsafeAction(t *testing.T) {
	root, featureRef, _ := sourceContinuityLabProject(t)
	manifestRef, _ := materializeSourceContinuityLabManifest(t, root, featureRef)
	input := sourceContinuityAdapterPlanInput()
	assignments := listValue(input["assignments"])
	input["assignments"] = assignments[1:]
	adapters := listValue(input["adapters"])
	first := requireObjectValue(t, adapters[0])
	first["actions"] = append(listValue(first["actions"]), "shell-exec")
	raw, err := json.Marshal(input)
	if err != nil {
		t.Fatal(err)
	}
	exit, env := runTaskRuntimeCommand(t, []string{
		"evidence", "source-continuity-adapter-plan", "--project-root", root,
		"--feature-dir", featureRef, "--task-id", sourceContinuityLabTaskID,
		"--manifest", manifestRef, "--input-json", string(raw), "--format", "json",
	})
	if exit != 2 || env.Status != "error" {
		t.Fatalf("unsafe incomplete adapter plan unexpectedly passed: exit=%d env=%#v", exit, env)
	}
	diagnostics := strings.Join(anyStringSlice(env.Data["diagnostics"]), "\n")
	for _, marker := range []string{"missing-adapter-lane", "unsupported-adapter-action"} {
		if !strings.Contains(diagnostics, marker) {
			t.Fatalf("adapter diagnostics missing %q: %s", marker, diagnostics)
		}
	}
}

func TestSourceContinuityLabBindsEvidenceToAdapterPlan(t *testing.T) {
	root, featureRef, _ := sourceContinuityLabProject(t)
	manifestRef, manifestSHA := materializeSourceContinuityLabManifest(t, root, featureRef)
	planRef, planSHA, composite := materializeSourceContinuityAdapterPlan(t, root, featureRef, manifestRef)
	observation := readSourceContinuityLabObservation(t, "passing-observation.json", manifestSHA)
	bindSourceContinuityAdapterPlanToObservation(observation, planRef, planSHA, composite)
	bindSourceContinuityLabEvidence(t, root, observation)
	raw, err := json.Marshal(observation)
	if err != nil {
		t.Fatal(err)
	}
	exit, env := runTaskRuntimeCommand(t, []string{
		"evidence", "source-continuity-validate", "--project-root", root,
		"--feature-dir", featureRef, "--task-id", sourceContinuityLabTaskID,
		"--manifest", manifestRef, "--adapter-plan", planRef,
		"--input-json", string(raw), "--format", "json",
	})
	if exit != 0 || env.Status != "ok" {
		t.Fatalf("plan-bound continuity observation failed: exit=%d env=%#v", exit, env)
	}
	reportPath := filepath.Join(root, filepath.FromSlash(featureRef), filepath.FromSlash(anyString(env.Data["report_ref"])))
	report := readImplementJSONFile(t, reportPath)
	if report["adapter_plan_ref"] != planRef || report["adapter_plan_sha256"] != planSHA || !reflect.DeepEqual(report["adapter"], composite) {
		t.Fatalf("plan-bound report = %#v", report)
	}

	evidenceRows := listValue(observation["evidence_refs"])
	for _, value := range evidenceRows {
		row := requireObjectValue(t, value)
		if row["side"] == "target" && row["kind"] == "runtime_diagnostics" {
			row["adapter_id"] = "asset-inspector"
		}
	}
	raw, err = json.Marshal(observation)
	if err != nil {
		t.Fatal(err)
	}
	exit, env = runTaskRuntimeCommand(t, []string{
		"evidence", "source-continuity-validate", "--project-root", root,
		"--feature-dir", featureRef, "--task-id", sourceContinuityLabTaskID,
		"--manifest", manifestRef, "--adapter-plan", planRef,
		"--input-json", string(raw), "--format", "json",
	})
	if exit != 2 || !strings.Contains(strings.Join(anyStringSlice(env.Data["diagnostics"]), "\n"), "evidence-adapter-assignment-mismatch") {
		t.Fatalf("adapter evidence laundering unexpectedly passed: exit=%d env=%#v", exit, env)
	}
}

func TestSourceContinuityLabRejectsMissingAdapterPlan(t *testing.T) {
	root, featureRef, _ := sourceContinuityLabProject(t)
	manifestRef, manifestSHA := materializeSourceContinuityLabManifest(t, root, featureRef)
	observation := readSourceContinuityLabObservation(t, "passing-observation.json", manifestSHA)
	bindSourceContinuityLabEvidence(t, root, observation)
	raw, err := json.Marshal(observation)
	if err != nil {
		t.Fatal(err)
	}
	exit, env := runTaskRuntimeCommand(t, []string{
		"evidence", "source-continuity-validate", "--project-root", root,
		"--feature-dir", featureRef, "--task-id", sourceContinuityLabTaskID,
		"--manifest", manifestRef, "--input-json", string(raw), "--format", "json",
	})
	if exit != 2 || env.Status != "error" || !strings.Contains(strings.Join(anyStringSlice(env.Data["diagnostics"]), "\n"), "missing-adapter-plan") {
		t.Fatalf("missing adapter plan unexpectedly passed: exit=%d env=%#v", exit, env)
	}
}

func TestSourceContinuityLabUIVerificationIsNormalizedAndRequiredForAcceptance(t *testing.T) {
	root, featureRef, feature := sourceContinuityLabProject(t)
	index := readImplementJSONFile(t, filepath.Join(feature, "task-index.json"))
	_, task, err := findImplementTask(index, sourceContinuityLabTaskID)
	if err != nil {
		t.Fatal(err)
	}
	lifecycle := map[string]any{"ui_verification": map[string]any{
		"covered_source_continuity_surface_ids":     []any{"DH-SURFACE-MAIN-001", "DH-SURFACE-DEEP-001"},
		"covered_source_continuity_interaction_ids": []any{"DH-INT-OPEN-DEEP-001", "DH-INT-EXPORT-001", "DH-INT-SHORTCUT-001"},
		"covered_source_continuity_component_ids":   []any{"DH-COMP-EXPORT-ICON-001"},
	}}
	if err := validateImplementTaskUIAcceptance(feature, task, lifecycle); err == nil || !strings.Contains(err.Error(), "source continuity lab report") {
		t.Fatalf("missing source continuity lab report should block acceptance: %v", err)
	}

	manifestRef, manifestSHA := materializeSourceContinuityLabManifest(t, root, featureRef)
	observation := readSourceContinuityLabObservation(t, "passing-observation.json", manifestSHA)
	bindSourceContinuityLabEvidence(t, root, observation)
	raw, err := json.Marshal(observation)
	if err != nil {
		t.Fatal(err)
	}
	exit, env := runTaskRuntimeCommand(t, []string{
		"evidence", "source-continuity-validate", "--project-root", root,
		"--feature-dir", featureRef, "--task-id", sourceContinuityLabTaskID,
		"--manifest", manifestRef, "--input-json", string(raw), "--format", "json",
	})
	if exit != 0 || env.Status != "ok" {
		t.Fatalf("source continuity validation failed: exit=%d env=%#v", exit, env)
	}
	patch := requireObjectValue(t, env.Data["ui_verification_patch"])
	normalized, err := normalizeUIVerification(patch)
	if err != nil {
		t.Fatalf("normalize source continuity ui verification: %v", err)
	}
	if normalized["source_continuity_lab_report_ref"] != env.Data["report_ref"] || normalized["source_continuity_lab_report_sha256"] != env.Data["report_sha256"] {
		t.Fatalf("normalized source continuity verification = %#v", normalized)
	}
	lifecycle["ui_verification"] = normalized
	if err := validateImplementTaskUIAcceptance(feature, task, lifecycle); err != nil {
		t.Fatalf("passing source continuity lab report should satisfy acceptance: %v", err)
	}

	normalized["source_continuity_lab_report_sha256"] = strings.Repeat("0", 64)
	if err := validateImplementTaskUIAcceptance(feature, task, lifecycle); err == nil || !strings.Contains(strings.ToLower(err.Error()), "sha-256") {
		t.Fatalf("tampered source continuity report should block acceptance: %v", err)
	}
}

func TestSourceContinuityLabSupportsQuickWorkItemsAndBlocksUnprovenAcceptance(t *testing.T) {
	quickID := "260827-source-continuity"
	input := sourceContinuityQuickInput()
	decision := requireObjectValue(t, input["decision"])
	items := listValue(decision["items"])
	firstItem := requireObjectValue(t, items[0])
	firstItem["write_scope"] = []any{"src/**"}
	ui := requireObjectValue(t, decision["ui_confirmation"])
	ui["source_continuity"] = sourceContinuityLabContract()
	root, workspace := stageConfirmedQuickExecutionTestWorkspace(t, quickID, input)

	env := runScriptDomainEnvelope(t, runQuick, []string{
		"--project-root", root, "item-start", quickID, "--item", "Q1",
	})
	if env.Status != "ok" {
		t.Fatalf("quick item start: %#v", env)
	}
	mustWriteQuickWorkerResult(t, workspace, "Q1", map[string]any{
		"task_id": "Q1", "status": "success", "summary": "implemented source-grounded UI",
		"changed_files": []any{"src/after-report.txt"},
		"ui_verification": map[string]any{
			"covered_source_continuity_surface_ids":     []any{"DH-SURFACE-MAIN-001", "DH-SURFACE-DEEP-001"},
			"covered_source_continuity_interaction_ids": []any{"DH-INT-OPEN-DEEP-001", "DH-INT-EXPORT-001", "DH-INT-SHORTCUT-001"},
			"covered_source_continuity_component_ids":   []any{"DH-COMP-EXPORT-ICON-001"},
		},
	})
	env = runScriptDomainEnvelope(t, runQuick, []string{
		"--project-root", root, "item-accept", quickID, "--item", "Q1", "--evidence", "target runs",
	})
	if env.Status != "blocked" || !strings.Contains(fmt.Sprint(env.Blockers), "source continuity lab report") {
		t.Fatalf("quick item without lab report should block: %#v", env)
	}

	exit, manifestEnv := runTaskRuntimeCommand(t, []string{
		"evidence", "source-continuity-manifest", "--project-root", root,
		"--quick-id", quickID, "--item-id", "Q1", "--format", "json",
	})
	if exit != 0 || manifestEnv.Status != "ok" {
		t.Fatalf("quick source continuity manifest failed: exit=%d env=%#v", exit, manifestEnv)
	}
	manifestRef := anyString(manifestEnv.Data["manifest_ref"])
	manifestSHA := anyString(manifestEnv.Data["manifest_sha256"])
	observation := readSourceContinuityLabObservation(t, "passing-observation.json", manifestSHA)
	bindSourceContinuityLabEvidence(t, root, observation)
	raw, err := json.Marshal(observation)
	if err != nil {
		t.Fatal(err)
	}
	exit, reportEnv := runTaskRuntimeCommand(t, []string{
		"evidence", "source-continuity-validate", "--project-root", root,
		"--quick-id", quickID, "--item-id", "Q1", "--manifest", manifestRef,
		"--input-json", string(raw), "--format", "json",
	})
	if exit != 0 || reportEnv.Status != "ok" {
		t.Fatalf("quick source continuity validation failed: exit=%d env=%#v", exit, reportEnv)
	}
	patch := requireObjectValue(t, reportEnv.Data["ui_verification_patch"])
	productPath := filepath.Join(root, "src", "after-report.txt")
	if err := os.MkdirAll(filepath.Dir(productPath), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(productPath, []byte("implementation changed after report\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	mustWriteQuickWorkerResult(t, workspace, "Q1", map[string]any{
		"task_id": "Q1", "status": "success", "summary": "implemented source-grounded UI",
		"changed_files":   []any{"src/after-report.txt"},
		"ui_verification": patch,
	})
	env = runScriptDomainEnvelope(t, runQuick, []string{
		"--project-root", root, "item-accept", quickID, "--item", "Q1", "--evidence", "source continuity lab passed",
	})
	if env.Status != "blocked" || !strings.Contains(fmt.Sprint(env.Blockers), "target snapshot") {
		t.Fatalf("quick item must reject a report predating implementation changes: %#v", env)
	}

	exit, manifestEnv = runTaskRuntimeCommand(t, []string{
		"evidence", "source-continuity-manifest", "--project-root", root,
		"--quick-id", quickID, "--item-id", "Q1", "--format", "json",
	})
	if exit != 0 || manifestEnv.Status != "ok" {
		t.Fatalf("refresh quick source continuity manifest failed: exit=%d env=%#v", exit, manifestEnv)
	}
	manifestRef = anyString(manifestEnv.Data["manifest_ref"])
	manifestSHA = anyString(manifestEnv.Data["manifest_sha256"])
	observation = readSourceContinuityLabObservation(t, "passing-observation.json", manifestSHA)
	bindSourceContinuityLabEvidence(t, root, observation)
	raw, err = json.Marshal(observation)
	if err != nil {
		t.Fatal(err)
	}
	exit, reportEnv = runTaskRuntimeCommand(t, []string{
		"evidence", "source-continuity-validate", "--project-root", root,
		"--quick-id", quickID, "--item-id", "Q1", "--manifest", manifestRef,
		"--input-json", string(raw), "--format", "json",
	})
	if exit != 0 || reportEnv.Status != "ok" {
		t.Fatalf("refresh quick source continuity report failed: exit=%d env=%#v", exit, reportEnv)
	}
	patch = requireObjectValue(t, reportEnv.Data["ui_verification_patch"])
	mustWriteQuickWorkerResult(t, workspace, "Q1", map[string]any{
		"task_id": "Q1", "status": "success", "summary": "implemented source-grounded UI",
		"changed_files":   []any{"src/after-report.txt"},
		"ui_verification": patch,
	})
	env = runScriptDomainEnvelope(t, runQuick, []string{
		"--project-root", root, "item-accept", quickID, "--item", "Q1", "--evidence", "source continuity lab passed",
	})
	if env.Status != "ok" {
		t.Fatalf("quick item with lab report should pass: %#v", env)
	}
	quick := quickService{projectRoot: root}
	accepted, err := quick.loadConfirmation(workspace)
	if err != nil {
		t.Fatal(err)
	}
	if err := validatePersistedQuickSourceContinuityLabReport(
		workspace,
		accepted,
		"Q1",
		anyString(reportEnv.Data["report_ref"]),
		anyString(reportEnv.Data["report_sha256"]),
	); err != nil {
		t.Fatalf("accepted Q item must preserve a revalidatable continuity report: %v", err)
	}
	reportRef := anyString(reportEnv.Data["report_ref"])
	canonical := filepath.ToSlash(filepath.Join(".planning", "quick", quickID, reportRef))
	metadata, ok := LookupArtifactType(canonical)
	if !ok || metadata.TypeID != "quick-source-continuity-lab" {
		t.Fatalf("quick lab artifact owner = %#v ok=%t", metadata, ok)
	}
	reportPath := filepath.Join(workspace, filepath.FromSlash(reportRef))
	reportBytes, err := os.ReadFile(reportPath)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(reportPath, append(reportBytes, ' '), 0o644); err != nil {
		t.Fatal(err)
	}
	env = runScriptDomainEnvelope(t, runQuick, []string{
		"--project-root", root, "close", quickID, "resolved",
	})
	if env.Status != "blocked" || !strings.Contains(strings.ToLower(fmt.Sprint(env.Blockers)), "source continuity lab report") {
		t.Fatalf("quick close must revalidate the accepted lab report: %#v", env)
	}
	if err := os.WriteFile(reportPath, reportBytes, 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.Remove(filepath.Join(workspace, quickConfirmationFileName)); err != nil {
		t.Fatal(err)
	}
	env = runScriptDomainEnvelope(t, runQuick, []string{
		"--project-root", root, "close", quickID, "resolved",
	})
	if env.Status != "blocked" || !strings.Contains(strings.ToLower(fmt.Sprint(env.Blockers)), "confirmation") {
		t.Fatalf("quick close must fail closed when confirmation is missing: %#v", env)
	}
}

func sourceContinuityLabProject(t *testing.T) (string, string, string) {
	t.Helper()
	root := t.TempDir()
	featureRef := filepath.ToSlash(filepath.Join(".specify", "features", "009-source-continuity-lab"))
	feature := filepath.Join(root, filepath.FromSlash(featureRef))
	if err := os.MkdirAll(feature, 0o755); err != nil {
		t.Fatal(err)
	}
	writeTaskRuntimeFixture(t, filepath.Join(feature, "task-index.json"), map[string]any{
		"version": 2,
		"status":  "ready",
		"tasks": []any{map[string]any{
			"id": sourceContinuityLabTaskID,
			"ui_contract": map[string]any{
				"fidelity_level": "high", "source_continuity": sourceContinuityLabContract(),
				"usability_validation": map[string]any{"smoothness_acceptance_ids": []any{}},
			},
		}},
	})
	return root, featureRef, feature
}

func sourceContinuityLabContract() map[string]any {
	return map[string]any{
		"schema": "spec-kit-ui-source-continuity-v1", "applicability": "required", "mode": "mixed",
		"reason": "A runnable legacy product, source code, and assets govern the migration.",
		"coverage": map[string]any{
			"surface_ids":     []any{"DH-SURFACE-MAIN-001", "DH-SURFACE-DEEP-001"},
			"interaction_ids": []any{"DH-INT-OPEN-DEEP-001", "DH-INT-EXPORT-001", "DH-INT-SHORTCUT-001"},
			"component_ids":   []any{"DH-COMP-EXPORT-ICON-001"},
		},
		"authority_refs": []any{"evidence://legacy/runtime", "evidence://legacy/source", "evidence://legacy/assets"},
		"surface_bindings": []any{
			map[string]any{"id": "SC-SURFACE-MAIN-001", "surface_id": "DH-SURFACE-MAIN-001", "source_refs": []any{"legacy/main-window"}, "discovery": "measured", "disposition": "adapt", "rationale": "Preserve the primary workspace."},
			map[string]any{"id": "SC-SURFACE-DEEP-001", "surface_id": "DH-SURFACE-DEEP-001", "source_refs": []any{"legacy/export-dialog"}, "discovery": "measured", "disposition": "preserve", "rationale": "Preserve the deep export dialog."},
		},
		"action_bindings": []any{
			map[string]any{"id": "SC-ACTION-OPEN-DEEP-001", "interaction_id": "DH-INT-OPEN-DEEP-001", "source_refs": []any{"legacy/menu#export"}, "user_promise": "Open export options.", "business_outcome": "The export dialog is available.", "side_effects": []any{}, "final_state": "The export dialog owns focus.", "verification": "Run the menu path in source and target."},
			map[string]any{"id": "SC-ACTION-EXPORT-001", "interaction_id": "DH-INT-EXPORT-001", "source_refs": []any{"legacy/exportAction"}, "user_promise": "Export the active document.", "business_outcome": "The selected file contains the current document.", "side_effects": []any{"write one export file", "remember the export directory"}, "final_state": "The exported path is visible and the workspace remains usable.", "verification": "Run source and target with equivalent safe data."},
			map[string]any{"id": "SC-ACTION-SHORTCUT-001", "interaction_id": "DH-INT-SHORTCUT-001", "source_refs": []any{"legacy/shortcut#Ctrl+E"}, "user_promise": "Open export from the keyboard.", "business_outcome": "The export dialog is available without pointer input.", "side_effects": []any{}, "final_state": "The export dialog owns focus.", "verification": "Run Ctrl+E in source and target."},
		},
		"asset_bindings": []any{map[string]any{
			"id": "SC-ASSET-EXPORT-001", "component_id": "DH-COMP-EXPORT-ICON-001", "semantic_role": "export action",
			"source_refs": []any{"legacy/assets/export.svg"}, "target_strategy": "preserve", "target_ref": "src/assets/export.svg",
			"provenance": "project-owned", "fallback": "Visible Export label and accessible name.", "placeholder_policy": "forbid-character-substitution",
		}},
		"unresolved_gaps": []any{},
	}
}

func sourceContinuityAdapterPlanInput() map[string]any {
	adapters := []any{
		map[string]any{
			"id": "structure-reader", "version": "1.0.0",
			"roles":          []any{"source", "target"},
			"capabilities":   []any{"surface-enumeration"},
			"actions":        []any{"enumerate-surfaces", "capture-structure"},
			"evidence_kinds": []any{"structure_snapshot"},
			"execution_mode": "agent-tool", "tool_ref": "tool://structure-reader",
			"write_policy": "read-only", "network_policy": "denied",
		},
		map[string]any{
			"id": "behavior-runner", "version": "1.0.0",
			"roles":          []any{"source", "target"},
			"capabilities":   []any{"action-execution", "side-effect-observation"},
			"actions":        []any{"enumerate-actions", "activate-action", "observe-side-effects", "capture-runtime"},
			"evidence_kinds": []any{"runtime_diagnostics"},
			"execution_mode": "external-runner", "tool_ref": "runner://behavior",
			"write_policy": "isolated-test-data", "network_policy": "declared-read-only",
		},
		map[string]any{
			"id": "asset-inspector", "version": "1.0.0",
			"roles":          []any{"source", "target"},
			"capabilities":   []any{"asset-inspection", "visual-capture"},
			"actions":        []any{"enumerate-assets", "capture-visual"},
			"evidence_kinds": []any{"visual_capture"},
			"execution_mode": "manual-attested", "tool_ref": "guide://asset-inspection",
			"write_policy": "read-only", "network_policy": "denied",
		},
	}
	adapterByCapability := map[string]string{
		"surface-enumeration":     "structure-reader",
		"action-execution":        "behavior-runner",
		"side-effect-observation": "behavior-runner",
		"asset-inspection":        "asset-inspector",
		"visual-capture":          "asset-inspector",
	}
	assignments := []any{}
	for _, side := range []string{"source", "target"} {
		for _, capability := range sourceContinuityLabCapabilities {
			assignments = append(assignments, map[string]any{
				"side": side, "capability": capability,
				"adapter_id":       adapterByCapability[capability],
				"selection_reason": "Selected for the declared capability and evidence contract.",
			})
		}
	}
	return map[string]any{
		"schema":   "spec-kit-source-continuity-adapter-plan-input-v1",
		"adapters": adapters, "assignments": assignments, "unresolved_gaps": []any{},
	}
}

func materializeSourceContinuityLabManifest(t *testing.T, root, featureRef string) (string, string) {
	t.Helper()
	exit, env := runTaskRuntimeCommand(t, []string{
		"evidence", "source-continuity-manifest", "--project-root", root,
		"--feature-dir", featureRef, "--task-id", sourceContinuityLabTaskID, "--format", "json",
	})
	if exit != 0 || env.Status != "ok" {
		t.Fatalf("source continuity manifest failed: exit=%d env=%#v", exit, env)
	}
	return anyString(env.Data["manifest_ref"]), anyString(env.Data["manifest_sha256"])
}

func materializeSourceContinuityAdapterPlan(t *testing.T, root, featureRef, manifestRef string) (string, string, map[string]any) {
	t.Helper()
	raw, err := json.Marshal(sourceContinuityAdapterPlanInput())
	if err != nil {
		t.Fatal(err)
	}
	exit, env := runTaskRuntimeCommand(t, []string{
		"evidence", "source-continuity-adapter-plan", "--project-root", root,
		"--feature-dir", featureRef, "--task-id", sourceContinuityLabTaskID,
		"--manifest", manifestRef, "--input-json", string(raw), "--format", "json",
	})
	if exit != 0 || env.Status != "ok" {
		t.Fatalf("materialize adapter plan: exit=%d env=%#v", exit, env)
	}
	binding := requireObjectValue(t, env.Data["adapter_binding"])
	return anyString(env.Data["adapter_plan_ref"]), anyString(env.Data["adapter_plan_sha256"]), requireObjectValue(t, binding["adapter"])
}

func bindSourceContinuityAdapterPlanToObservation(observation map[string]any, planRef, planSHA string, composite map[string]any) {
	observation["adapter_plan_ref"] = planRef
	observation["adapter_plan_sha256"] = planSHA
	observation["adapter"] = cloneJSONValue(composite)
	adapterByKind := map[string]string{
		"structure_snapshot":  "structure-reader",
		"runtime_diagnostics": "behavior-runner",
		"visual_capture":      "asset-inspector",
	}
	for _, value := range listValue(observation["evidence_refs"]) {
		row, _ := value.(map[string]any)
		row["adapter_id"] = adapterByKind[anyString(row["kind"])]
	}
}

func readSourceContinuityLabObservation(t *testing.T, name, manifestSHA string) map[string]any {
	t.Helper()
	path := filepath.Join("..", "..", "tests", "fixtures", "source-continuity-lab", name)
	raw, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	var payload map[string]any
	if err := json.Unmarshal(raw, &payload); err != nil {
		t.Fatal(err)
	}
	payload["manifest_sha256"] = manifestSHA
	return payload
}

func bindSourceContinuityLabEvidence(t *testing.T, root string, observation map[string]any) {
	t.Helper()
	refMap := map[string]string{}
	for _, value := range listValue(observation["evidence_refs"]) {
		row := requireObjectValue(t, value)
		oldRef := anyString(row["ref"])
		side := anyString(row["side"])
		kind := anyString(row["kind"])
		adapterID := anyString(row["adapter_id"])
		provenance := "test-fixture"
		if adapterID != "" {
			provenance = "adapter:" + adapterID
		}
		code, payload := runEvidenceCommand(t, root, []string{
			"register", "--project-root", root,
			"--content", side + ":" + kind + ":fixture\n",
			"--scope", "review", "--source", "source-continuity-lab-" + side + "-" + kind,
			"--provenance", provenance, "--mime", "text/plain",
		})
		if code != 0 {
			t.Fatalf("register source continuity evidence: %#v", payload)
		}
		data := requireEvidenceObject(t, payload, "data")
		newRef := evidenceTestString(data["record_ref"])
		row["ref"] = newRef
		refMap[oldRef] = newRef
	}
	for _, field := range []string{"action_results", "asset_results"} {
		for _, value := range listValue(observation[field]) {
			row := requireObjectValue(t, value)
			for _, refField := range []string{"source_evidence_ref", "target_evidence_ref"} {
				if replacement := refMap[anyString(row[refField])]; replacement != "" {
					row[refField] = replacement
				}
			}
		}
	}
}
