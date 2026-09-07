package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestSourceContinuityManifestReportsStableTargetSnapshotForUnchangedProductSources(t *testing.T) {
	root, featureRef, feature := sourceContinuitySnapshotProject(t, []any{"src/**"})

	first := materializeSourceContinuitySnapshotManifest(t, root, featureRef, feature)
	second := materializeSourceContinuitySnapshotManifest(t, root, featureRef, feature)

	if first.targetSnapshot == "" {
		t.Fatal("manifest source.target_snapshot_sha256 is empty")
	}
	if second.targetSnapshot != first.targetSnapshot {
		t.Fatalf("target snapshot changed without product source changes: first=%s second=%s", first.targetSnapshot, second.targetSnapshot)
	}
	if !bytes.Equal(second.bytes, first.bytes) {
		t.Fatal("manifest bytes changed without product source changes")
	}
}

func TestSourceContinuityManifestUsesExpectedWriteScopeInsteadOfWholeProject(t *testing.T) {
	root, featureRef, feature := sourceContinuityLabProject(t)
	productPath := filepath.Join(root, "src", "app.ts")
	unrelatedPath := filepath.Join(root, "docs", "notes.md")
	for path, content := range map[string]string{
		productPath:   "export const stable = true;\n",
		unrelatedPath: "unrelated v1\n",
	} {
		if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	indexPath := filepath.Join(feature, "task-index.json")
	index := readImplementJSONFile(t, indexPath)
	_, task, err := findImplementTask(index, sourceContinuityLabTaskID)
	if err != nil {
		t.Fatal(err)
	}
	task["expected_write_scope"] = []any{"src/**"}
	task["write_scope"] = []any{"docs/**"}
	writeTaskRuntimeFixture(t, indexPath, index)

	first := materializeSourceContinuitySnapshotManifest(t, root, featureRef, feature)
	if err := os.WriteFile(unrelatedPath, []byte("unrelated v2\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	second := materializeSourceContinuitySnapshotManifest(t, root, featureRef, feature)
	if second.targetSnapshot != first.targetSnapshot {
		t.Fatalf("file outside expected_write_scope changed target snapshot: first=%s second=%s", first.targetSnapshot, second.targetSnapshot)
	}
	if err := os.WriteFile(productPath, []byte("export const stable = false;\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	third := materializeSourceContinuitySnapshotManifest(t, root, featureRef, feature)
	if third.targetSnapshot == first.targetSnapshot {
		t.Fatal("file inside expected_write_scope did not change target snapshot")
	}
}

func TestSourceContinuityManifestTargetSnapshotIgnoresRuntimeOwnedContinuityArtifacts(t *testing.T) {
	root, featureRef, feature := sourceContinuityLegacySnapshotProject(t, []any{"."})
	first := materializeSourceContinuitySnapshotManifest(t, root, featureRef, feature)

	bridgeInput, err := json.Marshal(sourceContinuityToolInventoryInput())
	if err != nil {
		t.Fatal(err)
	}
	exit, bridgeEnv := runTaskRuntimeCommand(t, []string{
		"evidence", "source-continuity-adapter-bridge", "--project-root", root,
		"--feature-dir", featureRef, "--task-id", sourceContinuityLabTaskID,
		"--manifest", first.ref, "--input-json", string(bridgeInput), "--format", "json",
	})
	if exit != 0 || bridgeEnv.Status != "ok" {
		t.Fatalf("source continuity bridge failed: exit=%d env=%#v", exit, bridgeEnv)
	}

	observation := readSourceContinuityLabObservation(t, "passing-observation.json", first.sha)
	binding := requireObjectValue(t, bridgeEnv.Data["adapter_binding"])
	bindSourceContinuityAdapterPlanToObservation(
		observation,
		anyString(bridgeEnv.Data["adapter_plan_ref"]),
		anyString(bridgeEnv.Data["adapter_plan_sha256"]),
		requireObjectValue(t, binding["adapter"]),
	)
	plan := readImplementJSONFile(t, filepath.Join(feature, filepath.FromSlash(anyString(bridgeEnv.Data["adapter_plan_ref"]))))
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
	exit, executionEnv := runTaskRuntimeCommand(t, []string{
		"evidence", "source-continuity-adapter-execution", "--project-root", root,
		"--feature-dir", featureRef, "--task-id", sourceContinuityLabTaskID,
		"--manifest", first.ref,
		"--adapter-plan", anyString(bridgeEnv.Data["adapter_plan_ref"]),
		"--adapter-plan-sha256", anyString(bridgeEnv.Data["adapter_plan_sha256"]),
		"--format", "json",
	})
	if exit != 0 || executionEnv.Status != "ok" {
		t.Fatalf("source continuity adapter execution failed: exit=%d env=%#v", exit, executionEnv)
	}
	bindSourceContinuityAdapterExecutionToObservation(observation, executionEnv)
	bindSourceContinuityLabEvidence(t, root, observation)
	rawObservation, err := json.Marshal(observation)
	if err != nil {
		t.Fatal(err)
	}
	exit, reportEnv := runTaskRuntimeCommand(t, []string{
		"evidence", "source-continuity-validate", "--project-root", root,
		"--feature-dir", featureRef, "--task-id", sourceContinuityLabTaskID,
		"--manifest", first.ref,
		"--adapter-plan", anyString(bridgeEnv.Data["adapter_plan_ref"]),
		"--adapter-execution", anyString(executionEnv.Data["adapter_execution_ref"]),
		"--input-json", string(rawObservation), "--format", "json",
	})
	if exit != 0 || reportEnv.Status != "ok" {
		t.Fatalf("source continuity validation failed: exit=%d env=%#v", exit, reportEnv)
	}
	index := readImplementJSONFile(t, filepath.Join(feature, "task-index.json"))
	_, currentTask, err := findImplementTask(index, sourceContinuityLabTaskID)
	if err != nil {
		t.Fatal(err)
	}
	if err := validatePersistedSourceContinuityLabReport(
		feature,
		currentTask,
		anyString(reportEnv.Data["report_ref"]),
		anyString(reportEnv.Data["report_sha256"]),
		anyString(bridgeEnv.Data["adapter_plan_ref"]),
		anyString(bridgeEnv.Data["adapter_plan_sha256"]),
		anyString(executionEnv.Data["adapter_execution_ref"]),
		anyString(executionEnv.Data["adapter_execution_sha256"]),
	); err != nil {
		t.Fatalf("persisted source continuity report rejected after full chain: %v", err)
	}

	second := materializeSourceContinuitySnapshotManifest(t, root, featureRef, feature)
	if second.targetSnapshot != first.targetSnapshot {
		t.Fatalf("runtime-owned continuity artifacts changed target snapshot: first=%s second=%s", first.targetSnapshot, second.targetSnapshot)
	}
	if !bytes.Equal(second.bytes, first.bytes) {
		t.Fatal("runtime-owned continuity artifacts changed manifest bytes")
	}
}

func TestSourceContinuityManifestRejectsAlternateRuntimeOwnedContinuityScope(t *testing.T) {
	root, featureRef, feature := sourceContinuityLabProject(t)
	runtimeOwnedDir := filepath.Join(feature, "implementation-review", "source-continuity")
	if err := os.MkdirAll(runtimeOwnedDir, 0o755); err != nil {
		t.Fatal(err)
	}
	alternateRuntimeOwnedScope := "src/../" + featureRef + "/implementation-review/source-continuity"
	sourceContinuitySnapshotSetTaskWriteScope(t, feature, []any{alternateRuntimeOwnedScope})

	exit, env := runTaskRuntimeCommand(t, []string{
		"evidence", "source-continuity-manifest", "--project-root", root,
		"--feature-dir", featureRef, "--task-id", sourceContinuityLabTaskID, "--format", "json",
	})
	detail := strings.ToLower(env.Summary + " " + fmt.Sprint(env.Blockers))
	if exit != 2 || env.Status != "usage-error" || !strings.Contains(detail, "runtime-owned") {
		t.Fatalf("alternate runtime-owned scope did not fail closed: exit=%d env=%#v", exit, env)
	}
	legacyRuntimeOwnedScope := "specs/009-source-continuity-lab/implementation-review/source-continuity/**"
	sourceContinuitySnapshotSetTaskWriteScope(t, feature, []any{legacyRuntimeOwnedScope})
	exit, env = runTaskRuntimeCommand(t, []string{
		"evidence", "source-continuity-manifest", "--project-root", root,
		"--feature-dir", featureRef, "--task-id", sourceContinuityLabTaskID, "--format", "json",
	})
	detail = strings.ToLower(env.Summary + " " + fmt.Sprint(env.Blockers))
	if exit != 2 || env.Status != "usage-error" || !strings.Contains(detail, "runtime-owned") {
		t.Fatalf("legacy runtime-owned scope did not fail closed: exit=%d env=%#v", exit, env)
	}
}

func TestSourceContinuityTargetSnapshotIgnoresLegacySpecsRuntimeRoot(t *testing.T) {
	root := t.TempDir()
	productPath := filepath.Join(root, "src", "app.ts")
	if err := os.MkdirAll(filepath.Dir(productPath), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(productPath, []byte("export const stable = true;\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	before, err := sourceContinuityLabTargetSnapshot(root, nil)
	if err != nil {
		t.Fatal(err)
	}
	runtimePath := filepath.Join(root, "specs", "009-source-continuity", "implementation-review", "source-continuity", "source-continuity-manifest-T017.json")
	if err := os.MkdirAll(filepath.Dir(runtimePath), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(runtimePath, []byte("{\"runtime_owned\":true}\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	after, err := sourceContinuityLabTargetSnapshot(root, nil)
	if err != nil {
		t.Fatal(err)
	}
	if after != before {
		t.Fatalf("legacy specs runtime artifact changed target snapshot: first=%s second=%s", before, after)
	}
}

func TestSourceContinuityTargetSnapshotKeepsProductNamedSourceContinuity(t *testing.T) {
	root := t.TempDir()
	productPath := filepath.Join(root, "src", "implementation-review", "source-continuity", "adapter.ts")
	if err := os.MkdirAll(filepath.Dir(productPath), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(productPath, []byte("export const version = 1;\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	before, err := sourceContinuityLabTargetSnapshot(root, []string{"src/**"})
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(productPath, []byte("export const version = 2;\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	after, err := sourceContinuityLabTargetSnapshot(root, []string{"src/**"})
	if err != nil {
		t.Fatal(err)
	}
	if after == before {
		t.Fatal("product-owned implementation-review/source-continuity path was incorrectly excluded")
	}
}

func TestSourceContinuityManifestTargetSnapshotChangesWhenProductSourceChanges(t *testing.T) {
	root, featureRef, feature := sourceContinuitySnapshotProject(t, []any{"src/**"})
	first := materializeSourceContinuitySnapshotManifest(t, root, featureRef, feature)

	productPath := filepath.Join(root, "src", "app.ts")
	if err := os.WriteFile(productPath, []byte("export const label = 'changed';\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	second := materializeSourceContinuitySnapshotManifest(t, root, featureRef, feature)
	if second.targetSnapshot == first.targetSnapshot {
		t.Fatalf("product source change did not change target snapshot: %s", second.targetSnapshot)
	}
	if bytes.Equal(second.bytes, first.bytes) {
		t.Fatal("product source change did not change manifest bytes")
	}
}

type sourceContinuitySnapshotManifest struct {
	ref            string
	sha            string
	targetSnapshot string
	bytes          []byte
	env            Envelope
}

func sourceContinuitySnapshotProject(t *testing.T, writeScope []any) (string, string, string) {
	t.Helper()
	return sourceContinuitySnapshotProjectAt(
		t,
		filepath.ToSlash(filepath.Join(".specify", "features", "009-source-continuity-lab")),
		writeScope,
	)
}

func sourceContinuityLegacySnapshotProject(t *testing.T, writeScope []any) (string, string, string) {
	t.Helper()
	return sourceContinuitySnapshotProjectAt(
		t,
		filepath.ToSlash(filepath.Join("specs", "009-source-continuity-lab")),
		writeScope,
	)
}

func sourceContinuitySnapshotProjectAt(t *testing.T, featureRef string, writeScope []any) (string, string, string) {
	t.Helper()
	root := t.TempDir()
	if err := os.MkdirAll(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	feature := filepath.Join(root, filepath.FromSlash(featureRef))
	if err := os.MkdirAll(feature, 0o755); err != nil {
		t.Fatal(err)
	}
	productPath := filepath.Join(root, "src", "app.ts")
	assetPath := filepath.Join(root, "src", "assets", "export.svg")
	if err := os.MkdirAll(filepath.Dir(assetPath), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(productPath, []byte("export const label = 'stable';\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(assetPath, []byte("<svg aria-label=\"Export\"></svg>\n"), 0o644); err != nil {
		t.Fatal(err)
	}

	writeTaskRuntimeFixture(t, filepath.Join(feature, "task-index.json"), map[string]any{
		"version": 2,
		"status":  "ready",
		"tasks": []any{map[string]any{
			"id":                   sourceContinuityLabTaskID,
			"expected_write_scope": writeScope,
			"ui_contract": map[string]any{
				"fidelity_level": "high", "source_continuity": sourceContinuityLabContract(),
				"usability_validation": map[string]any{"smoothness_acceptance_ids": []any{}},
			},
		}},
	})
	return root, featureRef, feature
}

func sourceContinuitySnapshotSetTaskWriteScope(t *testing.T, feature string, writeScope []any) {
	t.Helper()
	indexPath := filepath.Join(feature, "task-index.json")
	index := readImplementJSONFile(t, indexPath)
	_, task, err := findImplementTask(index, sourceContinuityLabTaskID)
	if err != nil {
		t.Fatal(err)
	}
	task["write_scope"] = writeScope
	writeTaskRuntimeFixture(t, indexPath, index)
}

func materializeSourceContinuitySnapshotManifest(t *testing.T, root, featureRef, feature string) sourceContinuitySnapshotManifest {
	t.Helper()
	exit, env := runTaskRuntimeCommand(t, []string{
		"evidence", "source-continuity-manifest", "--project-root", root,
		"--feature-dir", featureRef, "--task-id", sourceContinuityLabTaskID, "--format", "json",
	})
	if exit != 0 || env.Status != "ok" {
		t.Fatalf("source continuity manifest failed: exit=%d env=%#v", exit, env)
	}
	ref := anyString(env.Data["manifest_ref"])
	path := filepath.Join(feature, filepath.FromSlash(ref))
	raw, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	manifest := readImplementJSONFile(t, path)
	source := requireObjectValue(t, manifest["source"])
	return sourceContinuitySnapshotManifest{
		ref:            ref,
		sha:            anyString(env.Data["manifest_sha256"]),
		targetSnapshot: anyString(source["target_snapshot_sha256"]),
		bytes:          raw,
		env:            env,
	}
}
