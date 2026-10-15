package main

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/workerdelta"
)

// This opt-in producer/consumer proof uses actual Python API output, verifies
// its immutable input bindings, and copies only declared fixture files. It does
// not synthesize Python history or mutate the original producer project.
func TestWorkerCognitionPythonProducedCanonicalReadAndPlanner(t *testing.T) {
	inputPath := os.Getenv("SPECIFY_WORKER_PYTHON_INTEROP_INPUT")
	if inputPath == "" {
		t.Skip("explicit digest-bound Python producer fixture is required")
	}
	expectedSHA := os.Getenv("SPECIFY_WORKER_PYTHON_INTEROP_SHA256")
	inputRaw := mustReadWorkerBytes(t, inputPath)
	if expectedSHA == "" || workerdelta.Digest(inputRaw) != expectedSHA {
		t.Fatal("interop producer input digest mismatch")
	}
	input, err := workerdelta.Decode(inputRaw)
	if err != nil {
		t.Fatal(err)
	}
	original, ok := input["project_root"].(string)
	if !ok || !filepath.IsAbs(original) {
		t.Fatal("producer root must be explicit and absolute")
	}
	root := t.TempDir()
	checks := map[string]string{}
	for _, field := range []string{"canonical_inputs", "source_inputs"} {
		rows, ok := input[field].([]any)
		if !ok || len(rows) == 0 {
			t.Fatal("producer denominator missing")
		}
		for _, raw := range rows {
			fact, ok := raw.(map[string]any)
			if !ok {
				t.Fatal("invalid producer binding")
			}
			path, _ := fact["path"].(string)
			digest, _ := fact["sha256"].(string)
			relative, err := filepath.Rel(original, path)
			if err != nil || relative == ".." || strings.HasPrefix(relative, ".."+string(filepath.Separator)) || filepath.IsAbs(relative) {
				t.Fatal("producer path escapes fixture")
			}
			bytes := mustReadWorkerBytes(t, path)
			if workerdelta.Digest(bytes) != digest {
				t.Fatalf("producer changed: %s", path)
			}
			destination := filepath.Join(root, relative)
			if err := os.MkdirAll(filepath.Dir(destination), 0755); err != nil {
				t.Fatal(err)
			}
			if err := os.WriteFile(destination, bytes, 0644); err != nil {
				t.Fatal(err)
			}
			checks[path] = digest
		}
	}
	scope, _ := input["scope"].(string)
	workflow, _ := input["workflow"].(string)
	paths := anyStringSlice(input["changed_paths"])
	stored := readWorkerStored(t, filepath.Join(root, filepath.FromSlash(scope), "worker-results", "T001.json"))
	if len(stored["submission_history"].([]any)) != 2 {
		t.Fatal("Python actual attempts lost")
	}
	candidate, _, err := readImplementTaskResultWithInput([]string{"--result-file", scope + "/worker-results/T001.json"}, root)
	if err != nil {
		t.Fatal(err)
	}
	if _, _, err := normalizeImplementTaskResult(candidate, "T001"); err != nil {
		t.Fatal(err)
	}
	payload := workerPlanner(t, root, workflow, scope, paths)
	if len(payload.WorkerCognition.Events) != 2 || len(payload.WorkerCognition.AcceptedDeltas) != 1 || len(payload.WorkerCognition.CandidateDeltas) != 1 || payload.WorkerCognition.Events[0].Status != "failed" || payload.WorkerCognition.Events[1].Status != "success" || !payload.WorkerCognition.Events[1].Accepted {
		t.Fatalf("Go did not consume actual Python current acceptance %#v", payload.WorkerCognition)
	}
	for path, digest := range checks {
		if workerdelta.Digest(mustReadWorkerBytes(t, path)) != digest {
			t.Fatal("Go consumer mutated original producer")
		}
	}
}
