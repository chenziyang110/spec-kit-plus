package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
)

func TestEvidenceSmoothnessManifestDerivesReadyTaskContract(t *testing.T) {
	root, feature, featureRef := newSmoothnessLabFixture(t)

	stdout := bytes.Buffer{}
	stderr := bytes.Buffer{}
	exit := Run([]string{
		"evidence", "smoothness-manifest",
		"--project-root", root, "--feature-dir", featureRef,
		"--task-id", "T101", "--format", "json",
	}, &stdout, &stderr, "test")
	env := decodeSmoothnessLabEnvelope(t, stdout.Bytes(), stderr.String())
	if exit != 0 || env.Status != "ok" {
		t.Fatalf("smoothness manifest failed: exit=%d env=%#v stderr=%s", exit, env, stderr.String())
	}

	manifestRef := smoothnessLabString(env.Data["manifest_ref"])
	if manifestRef != "implementation-review/smoothness/smoothness-manifest-T101.json" {
		t.Fatalf("manifest_ref = %q", manifestRef)
	}
	manifest := readImplementJSONFile(t, filepath.Join(feature, filepath.FromSlash(manifestRef)))
	wantIDs := []string{"focus-continuity", "pending-cancel-feedback", "reduced-motion", "large-data-performance"}
	if manifest["schema"] != "spec-kit-smoothness-lab-manifest-v1" || manifest["task_id"] != "T101" {
		t.Fatalf("manifest identity = %#v", manifest)
	}
	if got := smoothnessLabStrings(manifest["smoothness_acceptance_ids"]); !reflect.DeepEqual(got, wantIDs) {
		t.Fatalf("smoothness_acceptance_ids = %#v, want %#v", got, wantIDs)
	}
	if got := smoothnessLabStrings(manifest["required_evidence"]); !reflect.DeepEqual(got, []string{"structure_snapshot", "visual_capture", "runtime_diagnostics"}) {
		t.Fatalf("required_evidence = %#v", got)
	}
	entrypoint := smoothnessLabObject(manifest["entrypoint"])
	if entrypoint["id"] != "EP-WEB-SETTINGS" || entrypoint["url"] != "http://127.0.0.1:4173/settings" {
		t.Fatalf("entrypoint = %#v", entrypoint)
	}
	if got := smoothnessLabStrings(manifest["viewports"]); !reflect.DeepEqual(got, []string{"desktop", "mobile"}) {
		t.Fatalf("default viewports = %#v", got)
	}
	budgets := smoothnessLabObject(manifest["performance_budgets"])
	for _, key := range []string{"inp_ms", "long_task_ms", "cls", "animation_dropped_frame_pct", "bundle_delta_kb"} {
		if _, ok := budgets[key]; !ok {
			t.Fatalf("missing default budget %q in %#v", key, budgets)
		}
	}
	source := smoothnessLabObject(manifest["source"])
	if source["task_index_sha256"] != smoothnessLabFileSHA256(filepath.Join(feature, "task-index.json")) {
		t.Fatalf("task-index digest = %#v", source)
	}
	if env.Data["manifest_sha256"] != smoothnessLabFileSHA256(filepath.Join(feature, filepath.FromSlash(manifestRef))) {
		t.Fatalf("manifest digest receipt = %#v", env.Data)
	}

	stdout.Reset()
	stderr.Reset()
	exit = Run([]string{
		"evidence", "smoothness-manifest",
		"--project-root", root, "--feature-dir", featureRef,
		"--task-id", "T102", "--format", "json",
	}, &stdout, &stderr, "test")
	env = decodeSmoothnessLabEnvelope(t, stdout.Bytes(), stderr.String())
	if exit != 0 || env.Status != "ok" || env.Data["applicable"] != false || env.Data["status"] != "not-applicable" {
		t.Fatalf("empty smoothness ids should be not-applicable: exit=%d env=%#v stderr=%s", exit, env, stderr.String())
	}
}

func TestEvidenceSmoothnessValidateRejectsInvalidLabResult(t *testing.T) {
	root, feature, featureRef := newSmoothnessLabFixture(t)
	manifestPath := filepath.Join(feature, "implementation-review", "smoothness", "smoothness-manifest-T101.json")
	manifest := smoothnessLabManifestPayload(t, feature, []string{
		"focus-continuity",
		"scroll-continuity",
		"pending-cancel-feedback",
		"duplicate-activation",
		"reduced-motion",
		"large-data-performance",
		"editing-input-continuity",
		"interruption-safe-motion",
	})
	writeSmoothnessLabJSON(t, manifestPath, manifest)

	result := map[string]any{
		"schema":          "spec-kit-smoothness-lab-result-v1",
		"manifest_sha256": strings.Repeat("0", 64),
		"covered_smoothness_acceptance_ids": []any{
			"focus-continuity",
			"extra-unapproved-check",
		},
		"evidence_refs": []any{
			map[string]any{"kind": "visual_capture", "ref": "evidence://visual/settings"},
		},
		"scenario_results": []any{
			map[string]any{"smoothness_acceptance_id": "focus-continuity", "verdict": "failed", "observations": map[string]any{"focus_retained": false}},
			map[string]any{"smoothness_acceptance_id": "scroll-continuity", "verdict": "failed", "observations": map[string]any{"scroll_delta_px": 240}},
			map[string]any{"smoothness_acceptance_id": "pending-cancel-feedback", "verdict": "failed", "observations": map[string]any{"feedback_before_completion": false}},
			map[string]any{"smoothness_acceptance_id": "duplicate-activation", "verdict": "failed", "observations": map[string]any{"side_effect_count": 2}},
			map[string]any{"smoothness_acceptance_id": "reduced-motion", "verdict": "failed", "observations": map[string]any{"reduced_motion_equivalent": false}},
			map[string]any{"smoothness_acceptance_id": "large-data-performance", "verdict": "failed", "observations": map[string]any{"rendered_rows": 100000}},
			map[string]any{"smoothness_acceptance_id": "editing-input-continuity", "verdict": "failed", "observations": map[string]any{"caret_preserved": false}},
			map[string]any{"smoothness_acceptance_id": "interruption-safe-motion", "verdict": "failed", "observations": map[string]any{"interruption_preserved_state": false}},
		},
		"performance": map[string]any{
			"inp_ms": 320, "long_task_ms": 120, "cls": 0.22,
			"animation_dropped_frame_pct": 18,
			"bundle_delta_kb":             44,
		},
	}
	inputRaw, err := json.Marshal(result)
	if err != nil {
		t.Fatal(err)
	}

	stdout := bytes.Buffer{}
	stderr := bytes.Buffer{}
	exit := Run([]string{
		"evidence", "smoothness-validate",
		"--project-root", root, "--feature-dir", featureRef,
		"--task-id", "T101", "--manifest", "implementation-review/smoothness/smoothness-manifest-T101.json",
		"--input-json", string(inputRaw), "--format", "json",
	}, &stdout, &stderr, "test")
	env := decodeSmoothnessLabEnvelope(t, stdout.Bytes(), stderr.String())
	if exit != 2 || env.Status != "error" {
		t.Fatalf("invalid smoothness result should fail validation: exit=%d env=%#v stderr=%s", exit, env, stderr.String())
	}
	for _, want := range []string{
		"stale-manifest",
		"smoothness-id-mismatch",
		"missing-structure-snapshot",
		"missing-runtime-diagnostics",
		"focus-continuity-failed",
		"scroll-continuity-failed",
		"pending-cancel-feedback-failed",
		"duplicate-activation-failed",
		"reduced-motion-failed",
		"large-data-performance-failed",
		"editing-input-continuity-failed",
		"interruption-safe-motion-failed",
		"inp-budget-exceeded",
		"long-task-budget-exceeded",
		"cls-budget-exceeded",
		"animation-budget-exceeded",
		"bundle-delta-budget-exceeded",
	} {
		if !strings.Contains(env.Summary, want) && !strings.Contains(stdout.String(), want) {
			t.Fatalf("validation diagnostics missing %q: env=%#v stdout=%s", want, env, stdout.String())
		}
	}
}

func TestEvidenceSmoothnessValidateMaterializesPassingReport(t *testing.T) {
	root, feature, featureRef := newSmoothnessLabFixture(t)
	manifestRef := "implementation-review/smoothness/smoothness-manifest-T101.json"
	manifestPath := filepath.Join(feature, filepath.FromSlash(manifestRef))
	manifest := smoothnessLabManifestPayload(t, feature, []string{"focus-continuity", "pending-cancel-feedback", "reduced-motion", "large-data-performance"})
	writeSmoothnessLabJSON(t, manifestPath, manifest)
	manifestSHA := smoothnessLabFileSHA256(manifestPath)
	result := map[string]any{
		"schema":          "spec-kit-smoothness-lab-result-v1",
		"manifest_sha256": manifestSHA,
		"covered_smoothness_acceptance_ids": []any{
			"focus-continuity",
			"pending-cancel-feedback",
			"reduced-motion",
			"large-data-performance",
		},
		"evidence_refs": []any{
			map[string]any{"kind": "structure_snapshot", "ref": "evidence://structure/settings"},
			map[string]any{"kind": "visual_capture", "ref": "evidence://visual/settings"},
			map[string]any{"kind": "runtime_diagnostics", "ref": "evidence://runtime/settings"},
		},
		"scenario_results": []any{
			map[string]any{"smoothness_acceptance_id": "focus-continuity", "verdict": "passed"},
			map[string]any{"smoothness_acceptance_id": "pending-cancel-feedback", "verdict": "passed"},
			map[string]any{"smoothness_acceptance_id": "reduced-motion", "verdict": "passed"},
			map[string]any{"smoothness_acceptance_id": "large-data-performance", "verdict": "passed"},
		},
		"performance": map[string]any{
			"inp_ms": 120, "long_task_ms": 42, "cls": 0.02,
			"animation_dropped_frame_pct": 1,
			"bundle_delta_kb":             0,
		},
	}
	inputRaw, err := json.Marshal(result)
	if err != nil {
		t.Fatal(err)
	}

	stdout := bytes.Buffer{}
	stderr := bytes.Buffer{}
	exit := Run([]string{
		"evidence", "smoothness-validate",
		"--project-root", root, "--feature-dir", featureRef,
		"--task-id", "T101", "--manifest", manifestRef,
		"--input-json", string(inputRaw), "--format", "json",
	}, &stdout, &stderr, "test")
	env := decodeSmoothnessLabEnvelope(t, stdout.Bytes(), stderr.String())
	if exit != 0 || env.Status != "ok" {
		t.Fatalf("passing smoothness result failed: exit=%d env=%#v stderr=%s", exit, env, stderr.String())
	}
	reportRef := smoothnessLabString(env.Data["report_ref"])
	if reportRef != "implementation-review/smoothness/smoothness-lab-T101.json" {
		t.Fatalf("report_ref = %q", reportRef)
	}
	reportPath := filepath.Join(feature, filepath.FromSlash(reportRef))
	report := readImplementJSONFile(t, reportPath)
	if report["schema"] != "spec-kit-smoothness-lab-report-v1" || report["task_id"] != "T101" || report["verdict"] != "passed" {
		t.Fatalf("report identity = %#v", report)
	}
	if got := smoothnessLabStrings(report["covered_smoothness_acceptance_ids"]); !reflect.DeepEqual(got, []string{"focus-continuity", "pending-cancel-feedback", "reduced-motion", "large-data-performance"}) {
		t.Fatalf("covered ids = %#v", got)
	}
	if report["manifest_sha256"] != manifestSHA || env.Data["report_sha256"] != smoothnessLabFileSHA256(reportPath) {
		t.Fatalf("report digests env=%#v report=%#v", env.Data, report)
	}
	patch := smoothnessLabObject(env.Data["ui_verification_patch"])
	if got := smoothnessLabStrings(patch["covered_smoothness_acceptance_ids"]); !reflect.DeepEqual(got, []string{"focus-continuity", "pending-cancel-feedback", "reduced-motion", "large-data-performance"}) {
		t.Fatalf("ui verification patch = %#v", patch)
	}
}

func newSmoothnessLabFixture(t *testing.T) (string, string, string) {
	t.Helper()
	root := t.TempDir()
	featureRef := ".specify/features/001-smoothness"
	feature := filepath.Join(root, filepath.FromSlash(featureRef))
	if err := os.MkdirAll(feature, 0o755); err != nil {
		t.Fatal(err)
	}
	taskIndex := map[string]any{
		"version": 2,
		"status":  "ready",
		"official_entrypoints": []any{
			map[string]any{"id": "EP-WEB-SETTINGS", "kind": "web", "route": "/settings", "url": "http://127.0.0.1:4173/settings"},
		},
		"tasks": []any{
			smoothnessLabTask("T101", []any{"focus-continuity", "pending-cancel-feedback", "reduced-motion", "large-data-performance"}),
			smoothnessLabTask("T102", []any{}),
		},
	}
	writeSmoothnessLabJSON(t, filepath.Join(feature, "task-index.json"), taskIndex)
	return root, feature, featureRef
}

func smoothnessLabTask(taskID string, smoothnessIDs []any) map[string]any {
	return map[string]any{
		"id":     taskID,
		"status": "ready",
		"title":  "Implement the smooth settings interaction",
		"ui_contract": map[string]any{
			"surface_catalog": []any{
				map[string]any{"id": "SURF-SETTINGS", "entrypoint_id": "EP-WEB-SETTINGS", "surface": "settings"},
			},
			"usability_validation": map[string]any{
				"risk_level":                    "medium",
				"methods":                       []any{"smoothness lab"},
				"critical_tasks":                []any{"Change settings without losing place or confidence"},
				"success_criteria":              []any{"Focus, pending feedback, reduced motion, and large data remain smooth"},
				"human_review_required":         false,
				"smoothness_acceptance_ids":     smoothnessIDs,
				"smoothness_acceptance_lab_ref": "implementation-review/smoothness/smoothness-manifest-" + taskID + ".json",
			},
			"interaction_matrix": []any{
				map[string]any{"id": "DH-FOCUS", "surface": "settings", "input": "keyboard", "trigger": "Tab", "focus_behavior": "retain-visible-focus"},
				map[string]any{"id": "DH-PENDING", "surface": "settings", "input": "pointer", "trigger": "Save", "pending_behavior": "show-cancelable-progress"},
			},
			"editing_matrix": []any{
				map[string]any{"id": "DH-EDIT", "surface": "settings", "input_methods": []any{"keyboard", "paste", "ime"}, "caret": "preserved"},
			},
			"motion_rules": map[string]any{"reduced_motion": "equivalent-nonanimated-feedback", "interruption": "cancel-safe"},
		},
	}
}

func smoothnessLabManifestPayload(t *testing.T, feature string, ids []string) map[string]any {
	t.Helper()
	return map[string]any{
		"schema":                    "spec-kit-smoothness-lab-manifest-v1",
		"task_id":                   "T101",
		"smoothness_acceptance_ids": smoothnessLabAnyStrings(ids),
		"required_evidence":         []any{"structure_snapshot", "visual_capture", "runtime_diagnostics"},
		"entrypoint":                map[string]any{"id": "EP-WEB-SETTINGS", "kind": "web", "route": "/settings", "url": "http://127.0.0.1:4173/settings"},
		"viewports":                 []any{"desktop", "mobile"},
		"performance_budgets": map[string]any{
			"inp_ms": 200, "long_task_ms": 50, "cls": 0.1,
			"animation_dropped_frame_pct": 5,
			"bundle_delta_kb":             0,
		},
		"source": map[string]any{
			"task_index_ref":    "task-index.json",
			"task_index_sha256": smoothnessLabFileSHA256(filepath.Join(feature, "task-index.json")),
		},
	}
}

func decodeSmoothnessLabEnvelope(t *testing.T, raw []byte, stderr string) Envelope {
	t.Helper()
	var env Envelope
	if err := json.Unmarshal(raw, &env); err != nil {
		t.Fatalf("decode smoothness response: %v\nstdout=%s\nstderr=%s", err, string(raw), stderr)
	}
	return env
}

func writeSmoothnessLabJSON(t *testing.T, path string, value any) {
	t.Helper()
	raw, err := json.MarshalIndent(value, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	raw = append(raw, '\n')
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, raw, 0o644); err != nil {
		t.Fatal(err)
	}
}

func smoothnessLabFileSHA256(path string) string {
	raw, err := os.ReadFile(path)
	if err != nil {
		return ""
	}
	sum := sha256.Sum256(raw)
	return hex.EncodeToString(sum[:])
}

func smoothnessLabObject(value any) map[string]any {
	obj, _ := value.(map[string]any)
	return obj
}

func smoothnessLabString(value any) string {
	text, _ := value.(string)
	return text
}

func smoothnessLabStrings(value any) []string {
	items, _ := value.([]any)
	out := make([]string, 0, len(items))
	for _, item := range items {
		out = append(out, smoothnessLabString(item))
	}
	return out
}

func smoothnessLabAnyStrings(values []string) []any {
	out := make([]any, 0, len(values))
	for _, value := range values {
		out = append(out, value)
	}
	return out
}
