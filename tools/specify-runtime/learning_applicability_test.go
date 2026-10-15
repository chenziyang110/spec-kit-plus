package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
)

func learningApplicabilityFixture(t *testing.T) (string, []string) {
	t.Helper()
	root := t.TempDir()
	mustWriteLearningTest(t, filepath.Join(root, "src", "watcher", "watcher.go"), "package watcher\nconst IgnoreLogs = true\n")
	mustWriteLearningTest(t, filepath.Join(root, "src", "queue", "queue.go"), "package queue\nconst Retry = true\n")
	mustWriteLearningTest(t, filepath.Join(root, "constraints.json"), `{"watcher_mode":"ignore-logs"}`)
	args := []string{"capture", "--project-root", root, "--command", "spx-debug", "--type", "tooling_trap", "--summary", "Exclude generated logs to stop watcher restart loops", "--evidence", "A restart loop reproduced; excluding generated logs recovered the watcher.", "--recurrence-key", "debug.watcher-recovery", "--component", "src/watcher", "--source-file", "src/watcher/watcher.go", "--constraint-file", "constraints.json", "--evidence-kind", "recovery", "--context", "operation_owner=Watcher", "--format", "json"}
	return root, args
}

func learningApplicabilityShow(t *testing.T, root string, contexts ...string) map[string]any {
	t.Helper()
	args := []string{"show", "--project-root", root, "--ref", "debug.watcher-recovery", "--format", "json"}
	for _, context := range contexts {
		args = append(args, "--context", context)
	}
	env := runLearningEnvelopeTest(t, args)
	if env.Status != "ok" {
		t.Fatalf("show failed: %#v", env)
	}
	return mapStringAny(env.Data["applicability"])
}

func assertLearningApplicability(t *testing.T, proof map[string]any, state string, reasons ...string) {
	t.Helper()
	if proof["version"] != learningApplicabilityVersion || proof["state"] != state || proof["applicable"] != (state == "applicable") || proof["read_only"] != true {
		t.Fatalf("unexpected applicability: %#v", proof)
	}
	for _, reason := range reasons {
		if !learningContainsString(anyStringSlice(proof["reason_codes"]), reason) {
			t.Fatalf("missing %s in %#v", reason, proof)
		}
	}
}

func learningApplicabilityTree(t *testing.T, root string) map[string]string {
	t.Helper()
	result := map[string]string{}
	err := filepath.Walk(root, func(path string, info os.FileInfo, err error) error {
		if err != nil || info.IsDir() {
			return err
		}
		raw, err := os.ReadFile(path)
		if err != nil {
			return err
		}
		sum := sha256.Sum256(raw)
		result[path] = fmt.Sprintf("%x:%d:%d", sum, info.Size(), info.ModTime().UnixNano())
		return nil
	})
	if err != nil {
		t.Fatal(err)
	}
	return result
}

func TestLearningApplicabilityCaptureReadLifecycleAndSourceBinding(t *testing.T) {
	root, args := learningApplicabilityFixture(t)
	capture := runLearningEnvelopeTest(t, args)
	if capture.Status != "ok" || capture.Data["status"] != "candidate" {
		t.Fatalf("capture: %#v", capture)
	}
	entry := mapStringAny(capture.Data["entry"])
	binding, valid := decodeLearningApplicabilityBinding(entry["applicability_binding"])
	if !valid || binding.Component != "src/watcher" || len(binding.Sources) != 1 || len(binding.Constraints) != 1 {
		t.Fatalf("binding dropped or malformed: %#v", entry)
	}
	source, _ := os.ReadFile(filepath.Join(root, "src", "watcher", "watcher.go"))
	want := sha256.Sum256(source)
	if binding.Sources[0].SHA256 != hex.EncodeToString(want[:]) || binding.Sources[0].Bytes != int64(len(source)) {
		t.Fatal("source digest was not derived from live bytes")
	}
	before := learningApplicabilityTree(t, root)
	proof := learningApplicabilityShow(t, root, "component=src/watcher", "constraint_file=constraints.json")
	assertLearningApplicability(t, proof, "applicable")
	if len(proof["checks"].([]any)) != 2 || proof["binding_digest"] != binding.Digest {
		t.Fatalf("read proof did not retain the binding: %#v", proof)
	}
	for _, command := range []string{"start", "list"} {
		env := runLearningEnvelopeTest(t, []string{command, "--project-root", root, "--command", "spx-debug", "--context", "component=src/watcher", "--context", "constraint_file=constraints.json", "--format", "json"})
		items := anyMapSlice(env.Data["items"])
		if env.Status != "ok" || len(items) != 1 || items[0]["status"] != "candidate" {
			t.Fatalf("read lifecycle changed: %#v", env)
		}
		assertLearningApplicability(t, mapStringAny(items[0]["applicability"]), "applicable")
		if _, exists := mapStringAny(items[0]["applicability"])["checks"]; exists {
			t.Fatal("compact read expanded source evidence")
		}
		if !strings.Contains(strings.Join(anyStringSlice(items[0]["show_argv"]), " "), "constraint_file=constraints.json") {
			t.Fatal("show handoff dropped constraint context")
		}
	}
	if !reflect.DeepEqual(before, learningApplicabilityTree(t, root)) {
		t.Fatal("start/list/show changed files, lifecycle, or timestamps")
	}
	for _, target := range []string{"learning", "rule"} {
		env := runLearningEnvelopeTest(t, []string{"promote", "--project-root", root, "--recurrence-key", "debug.watcher-recovery", "--target", target, "--format", "json"})
		if env.Status != "ok" {
			t.Fatalf("explicit %s promotion failed: %#v", target, env)
		}
		assertLearningApplicability(t, learningApplicabilityShow(t, root, "component=src/watcher"), "applicable")
	}
}

func TestLearningApplicabilityWrongOwnerCurrentBytesConstraintsAndLegacy(t *testing.T) {
	for _, scenario := range []struct {
		name, context, state, reason string
		change                       string
	}{
		{"missing-context", "", "degraded", "task_component_missing", ""},
		{"wrong-component-positive-owner-match", "component=src/queue", "rejected", "component_mismatch", ""},
		{"source-same-size-changed", "component=src/watcher", "rejected", "source_changed", "source"},
		{"constraint-same-size-changed", "component=src/watcher", "rejected", "constraint_changed", "constraint"},
		{"missing-source", "component=src/watcher", "degraded", "source_unavailable", "missing-source"},
	} {
		t.Run(scenario.name, func(t *testing.T) {
			root, args := learningApplicabilityFixture(t)
			runLearningEnvelopeTest(t, args)
			switch scenario.change {
			case "source":
				mustWriteLearningTest(t, filepath.Join(root, "src", "watcher", "watcher.go"), "package watcher\nconst IgnoreLogs = null\n")
			case "constraint":
				mustWriteLearningTest(t, filepath.Join(root, "constraints.json"), `{"watcher_mode":"retain-logs"}`)
			case "missing-source":
				if err := os.Remove(filepath.Join(root, "src", "watcher", "watcher.go")); err != nil {
					t.Fatal(err)
				}
			}
			before := learningApplicabilityTree(t, root)
			proof := learningApplicabilityShow(t, root, scenario.context, "operation_owner=Watcher")
			assertLearningApplicability(t, proof, scenario.state, scenario.reason)
			if !reflect.DeepEqual(before, learningApplicabilityTree(t, root)) {
				t.Fatal("negative applicability read mutated storage")
			}
		})
	}
	root, args := learningApplicabilityFixture(t)
	runLearningEnvelopeTest(t, args)
	assertLearningApplicability(t, learningApplicabilityShow(t, root, "component=src/watcher", "constraint_file=other.json"), "rejected", "constraint_context_mismatch")
	legacy := []string{"capture", "--project-root", root, "--command", "debug", "--type", "tooling_trap", "--summary", "Exclude generated logs", "--evidence", "Loop recovered", "--recurrence-key", "debug.watcher-recovery", "--format", "json"}
	runLearningEnvelopeTest(t, legacy)
	assertLearningApplicability(t, learningApplicabilityShow(t, root, "component=src/watcher"), "degraded", "binding_missing")
}

// This regression uses only the pre-existing public Learning owner API. Its
// pre-change behavior returns no applicability refusal after same-size drift.
func TestLearningApplicabilityRegressionRefusesChangedSourceBytes(t *testing.T) {
	root := t.TempDir()
	mustWriteLearningTest(t, filepath.Join(root, "src", "owner", "owner.go"), "version-one")
	mustWriteLearningTest(t, filepath.Join(root, "rules.json"), "constraint-one")
	capture := runLearningEnvelopeTest(t, []string{"capture", "--project-root", root, "--command", "debug", "--type", "tooling_trap", "--summary", "Versioned parser recovery", "--evidence", "Rejected malformed input then recovered", "--recurrence-key", "debug.byte-drift", "--component", "src/owner", "--source-file", "src/owner/owner.go", "--constraint-file", "rules.json", "--evidence-kind", "failure"})
	if capture.Status != "ok" {
		t.Fatalf("capture: %#v", capture)
	}
	mustWriteLearningTest(t, filepath.Join(root, "src", "owner", "owner.go"), "version-two")
	show := runLearningEnvelopeTest(t, []string{"show", "--project-root", root, "--ref", "debug.byte-drift", "--context", "component=src/owner"})
	proof, ok := show.Data["applicability"].(map[string]any)
	if !ok || proof["applicable"] != false || proof["state"] != "rejected" {
		t.Fatalf("changed-version failed evidence was not refused: %#v", show.Data)
	}
	if !learningContainsString(anyStringSlice(proof["reason_codes"]), "failed_evidence_source_changed") {
		t.Fatalf("changed-version failure reason was lost: %#v", proof)
	}
}

func TestLearningApplicabilityCounterevidenceAndRecurrenceCannotOverride(t *testing.T) {
	root, args := learningApplicabilityFixture(t)
	mustWriteLearningTest(t, filepath.Join(root, "counterexample.txt"), "The same exclusion lost required audit events in a current reproduced counterexample.")
	args = append(args, "--counterevidence-file", "counterexample.txt")
	runLearningEnvelopeTest(t, args)
	assertLearningApplicability(t, learningApplicabilityShow(t, root, "component=src/watcher"), "rejected", "counterevidence_present")
	rootOnlyArgs := args[:len(args)-2]
	second := runLearningEnvelopeTest(t, rootOnlyArgs)
	if intFromAny(mapStringAny(second.Data["entry"])["occurrence_count"]) != 2 || second.Data["status"] != "candidate" {
		t.Fatal("recurrence unexpectedly changed lifecycle")
	}
	assertLearningApplicability(t, learningApplicabilityShow(t, root, "component=src/watcher"), "rejected", "counterevidence_present")
	start := runLearningEnvelopeTest(t, []string{"start", "--project-root", root, "--command", "debug", "--context", "component=src/watcher"})
	if len(anyMapSlice(start.Data["promotion_ready"])) != 0 {
		t.Fatalf("recurrence overrode counterevidence readiness: %#v", start.Data)
	}
	mustWriteLearningTest(t, filepath.Join(root, "counterexample.txt"), "A second current counterexample disproved the recovery.")
	assertLearningApplicability(t, learningApplicabilityShow(t, root, "component=src/watcher"), "rejected", "counterevidence_changed")
	if err := os.Remove(filepath.Join(root, "counterexample.txt")); err != nil {
		t.Fatal(err)
	}
	assertLearningApplicability(t, learningApplicabilityShow(t, root, "component=src/watcher"), "degraded", "counterevidence_unavailable")
	mustWriteLearningTest(t, filepath.Join(root, "current-counterexample.txt"), "A reproduced current failure contradicts this recovery.")
	assertLearningApplicability(t, learningApplicabilityShow(t, root, "component=src/watcher", "counterevidence_file=current-counterexample.txt"), "rejected", "task_counterevidence_present")
	assertLearningApplicability(t, learningApplicabilityShow(t, root, "component=src/watcher", "counterevidence_file=missing.txt"), "degraded", "task_counterevidence_unverifiable")
}

func TestLearningApplicabilityCaptureRefusesUnownedUnsafeAndIncompleteBindings(t *testing.T) {
	for _, scenario := range []struct{ name, flag, value string }{
		{"wrong-owner", "--source-file", "src/queue/queue.go"},
		{"escaping-source", "--source-file", "../outside.go"},
		{"absolute-source", "--source-file", "C:/Users/alice/private.go"},
		{"private-store", "--source-file", ".specify/project-cognition/project-cognition.db"},
		{"ordinary-success", "--evidence-kind", "success"},
		{"missing-constraints", "--constraint-file", ""},
	} {
		t.Run(scenario.name, func(t *testing.T) {
			root, args := learningApplicabilityFixture(t)
			for i := range args {
				if args[i] == scenario.flag {
					args[i+1] = scenario.value
				}
			}
			env := runLearningEnvelopeTest(t, args)
			if env.Status != "blocked" {
				t.Fatalf("invalid applicability capture accepted: %#v", env)
			}
			if strings.Contains(strings.Join(anyStringSlice(env.Blockers), " "), "alice") {
				t.Fatalf("unsafe source error leaked raw path: %#v", env)
			}
			if len(readLearningEntriesIfPresent(filepath.Join(root, ".planning", "learnings", "candidates.md"))) != 0 {
				t.Fatal("invalid binding persisted a candidate")
			}
		})
	}
}

func TestLearningApplicabilityMalformedBindingIsConservativelySanitized(t *testing.T) {
	entry := map[string]any{"applicability_binding": map[string]any{"version": "legacy", "component": "person@example.com", "raw": "token=secret-value"}}
	safe := sanitizeLearningEntryWithPolicy(entry, builtinLearningPolicy())
	raw, _ := json.Marshal(safe)
	if strings.Contains(string(raw), "person@example.com") || strings.Contains(string(raw), "secret-value") {
		t.Fatalf("invalid binding leaked raw values: %s", raw)
	}
	root := t.TempDir()
	proof := (learningService{projectRoot: root}).checkLearningApplicability(safe, nil, builtinLearningPolicy())
	assertLearningApplicability(t, proof, "degraded", "binding_invalid")
}

func TestLearningApplicabilityRecurrenceAcrossComponentsRetainsConflict(t *testing.T) {
	root, args := learningApplicabilityFixture(t)
	runLearningEnvelopeTest(t, args)
	for i := range args {
		if args[i] == "--component" {
			args[i+1] = "src/queue"
		}
		if args[i] == "--source-file" {
			args[i+1] = "src/queue/queue.go"
		}
	}
	runLearningEnvelopeTest(t, args)
	assertLearningApplicability(t, learningApplicabilityShow(t, root, "component=src/queue"), "rejected", "recurrence_component_conflict")
}

func TestLearningApplicabilityReadDetectsSourceOwnerIndirection(t *testing.T) {
	root, args := learningApplicabilityFixture(t)
	runLearningEnvelopeTest(t, args)
	source := filepath.Join(root, "src", "watcher", "watcher.go")
	external := filepath.Join(t.TempDir(), "watcher.go")
	mustWriteLearningTest(t, external, "external source")
	if err := os.Remove(source); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(external, source); err != nil {
		t.Skipf("native symlink creation unavailable: %v", err)
	}
	assertLearningApplicability(t, learningApplicabilityShow(t, root, "component=src/watcher"), "degraded", "source_unavailable")
}

func TestLearningApplicabilityAutoCaptureRealSignalReadOnlyDryRunAndVersionedDuplicate(t *testing.T) {
	root, _ := learningApplicabilityFixture(t)
	workspace := ".planning/quick/demo"
	status := filepath.Join(root, filepath.FromSlash(workspace), "STATUS.md")
	mustWriteLearningTest(t, status, "---\nstatus: resolved\n---\n\n## Execution\n\n```yaml\nretry_attempts: 1\nblocker_reason: generated logs restarted the watcher\nrecovery_action: exclude generated logs\n```\n\n## Validation\n\n```yaml\ncompleted_checks:\n  - watcher restart reproduction and scoped checks passed\n```\n")
	args := []string{"capture-auto", "--project-root", root, "--command", "spx-quick", "--workspace", workspace, "--component", "src/watcher", "--source-file", "src/watcher/watcher.go", "--constraint-file", "constraints.json", "--evidence-kind", "recovery", "--format", "json"}
	before := learningApplicabilityTree(t, root)
	dryRun := runLearningEnvelopeTest(t, append(append([]string{}, args...), "--dry-run"))
	if dryRun.Status != "ok" || dryRun.Data["status"] != "dry-run" || len(anyMapSlice(dryRun.Data["assessed"])) != 1 {
		t.Fatalf("real recovery dry-run: %#v", dryRun)
	}
	if !reflect.DeepEqual(before, learningApplicabilityTree(t, root)) {
		t.Fatal("auto dry-run mutated runtime/lifecycle files")
	}
	capture := runLearningEnvelopeTest(t, args)
	items := anyMapSlice(capture.Data["captured"])
	if capture.Status != "ok" || len(items) != 1 {
		t.Fatalf("real recovery auto-capture: %#v", capture)
	}
	if _, valid := decodeLearningApplicabilityBinding(mapStringAny(items[0]["entry"])["applicability_binding"]); !valid {
		t.Fatal("auto-capture lost its applicability binding")
	}
	duplicate := runLearningEnvelopeTest(t, args)
	if duplicate.Data["status"] != "duplicate-snapshot" {
		t.Fatalf("bound identical snapshot not deduplicated: %#v", duplicate)
	}
	mustWriteLearningTest(t, filepath.Join(root, "src", "watcher", "watcher.go"), "package watcher\nconst IgnoreLogs = false\n")
	changed := runLearningEnvelopeTest(t, args)
	if changed.Data["status"] == "duplicate-snapshot" || changed.Data["fingerprint"] == capture.Data["fingerprint"] {
		t.Fatal("auto-capture fingerprint ignored source-version binding")
	}
	// Ordinary completed work has no reusable correction signal and must not
	// create a new lesson or fabricate an assessment to prove Learning ran.
	mustWriteLearningTest(t, status, "---\nstatus: resolved\n---\n\n## Execution\n\n```yaml\nretry_attempts: 0\n```\n")
	before = learningApplicabilityTree(t, root)
	ordinary := runLearningEnvelopeTest(t, args)
	if ordinary.Data["status"] != "no-op" || len(anyMapSlice(ordinary.Data["captured"])) != 0 || !reflect.DeepEqual(before, learningApplicabilityTree(t, root)) {
		t.Fatalf("ordinary success manufactured a Learning write: %#v", ordinary)
	}
}

func TestLearningApplicabilityConfiguredSensitiveSourceNeverPersistsRawValue(t *testing.T) {
	root, args := learningApplicabilityFixture(t)
	mustWriteLearningTest(t, filepath.Join(root, ".specify", "config.json"), `{"project_learning":{"detectors":{"sensitive_terms":["internal-client"]}}}`)
	mustWriteLearningTest(t, filepath.Join(root, "src", "watcher", "internal-client.go"), "package watcher")
	for i := range args {
		if args[i] == "--source-file" {
			args[i+1] = "src/watcher/internal-client.go"
		}
	}
	env := runLearningEnvelopeTest(t, args)
	raw, _ := json.Marshal(env)
	if env.Status != "blocked" || strings.Contains(string(raw), "internal-client") {
		t.Fatalf("sensitive source capture was not safely refused: %s", raw)
	}
}

func TestLearningApplicabilityCandidateCounterexampleCannotHideBehindConfirmedLayer(t *testing.T) {
	root, args := learningApplicabilityFixture(t)
	runLearningEnvelopeTest(t, args)
	runLearningEnvelopeTest(t, []string{"promote", "--project-root", root, "--recurrence-key", "debug.watcher-recovery", "--target", "learning"})
	mustWriteLearningTest(t, filepath.Join(root, "counterexample.txt"), "A newly reproduced case contradicts the confirmed watcher recovery.")
	runLearningEnvelopeTest(t, append(args, "--counterevidence-file", "counterexample.txt"))
	proof := learningApplicabilityShow(t, root, "component=src/watcher")
	assertLearningApplicability(t, proof, "rejected", "lifecycle_binding_conflict")
	paths, _ := (learningService{projectRoot: root}).paths()
	if len(readLearningEntriesIfPresent(paths.candidates)) != 1 || len(readLearningEntriesIfPresent(paths.confirmedLearnings)) != 1 {
		t.Fatal("applicability resolution silently changed candidate/confirmed lifecycle")
	}
}

func TestLearningApplicabilityProjectionMismatchAndIndexOnlyCannotAssertCurrentTruth(t *testing.T) {
	root, args := learningApplicabilityFixture(t)
	capture := runLearningEnvelopeTest(t, args)
	paths, _ := (learningService{projectRoot: root}).paths()
	detail := filepath.Join(root, filepath.FromSlash(stringFromAny(capture.Data["detail_path"])))
	preamble, entries, err := readLearningEntries(detail)
	if err != nil {
		t.Fatal(err)
	}
	delete(entries[0], "applicability_binding")
	if err := writeLearningEntries(detail, preamble, entries); err != nil {
		t.Fatal(err)
	}
	assertLearningApplicability(t, learningApplicabilityShow(t, root, "component=src/watcher"), "degraded", "binding_projection_mismatch")
	if err := os.Remove(paths.candidates); err != nil {
		t.Fatal(err)
	}
	if err := os.Remove(detail); err != nil {
		t.Fatal(err)
	}
	assertLearningApplicability(t, learningApplicabilityShow(t, root, "component=src/watcher"), "degraded", "record_evidence_missing")
}

func TestLearningApplicabilityStartCandidateAnnotationsRespectCatalogConflict(t *testing.T) {
	root, args := learningApplicabilityFixture(t)
	runLearningEnvelopeTest(t, args)
	runLearningEnvelopeTest(t, []string{"promote", "--project-root", root, "--recurrence-key", "debug.watcher-recovery", "--target", "learning"})
	for i := range args {
		if args[i] == "--component" {
			args[i+1] = "src/queue"
		}
		if args[i] == "--source-file" {
			args[i+1] = "src/queue/queue.go"
		}
	}
	args = append(args, "--signal", "high")
	for i := 0; i < 2; i++ {
		capture := runLearningEnvelopeTest(t, args)
		if capture.Status != "ok" || capture.Data["status"] != "candidate" {
			t.Fatalf("component B candidate %d: %#v", i+1, capture)
		}
	}
	before := learningApplicabilityTree(t, root)
	start := runLearningEnvelopeTest(t, []string{"start", "--project-root", root, "--command", "debug", "--context", "component=src/queue", "--context", "operation_owner=Watcher"})
	if start.Status != "ok" {
		t.Fatalf("start: %#v", start)
	}
	list := runLearningEnvelopeTest(t, []string{"list", "--project-root", root, "--command", "debug", "--context", "component=src/queue", "--context", "operation_owner=Watcher"})
	for _, env := range []Envelope{start, list} {
		items := anyMapSlice(env.Data["items"])
		if len(items) != 1 {
			t.Fatalf("missing catalog conflict card: %#v", env.Data)
		}
		assertLearningApplicability(t, mapStringAny(items[0]["applicability"]), "rejected", "lifecycle_binding_conflict")
	}
	assertLearningApplicability(t, learningApplicabilityShow(t, root, "component=src/queue"), "rejected", "lifecycle_binding_conflict")
	if ready := anyMapSlice(start.Data["promotion_ready"]); len(ready) != 0 {
		t.Fatalf("rejected catalog binding advertised positive promotion readiness: %#v", ready)
	}
	confirmation := anyMapSlice(start.Data["needs_confirmation"])
	if len(confirmation) != 1 {
		t.Fatalf("high-signal candidate conflict annotation was lost: %#v", start.Data)
	}
	assertLearningApplicability(t, mapStringAny(confirmation[0]["applicability"]), "rejected", "lifecycle_binding_conflict")
	if !reflect.DeepEqual(before, learningApplicabilityTree(t, root)) {
		t.Fatal("conflict start/list/show changed files, timestamps, or lifecycle")
	}
	paths, _ := (learningService{projectRoot: root}).paths()
	candidates := readLearningEntriesIfPresent(paths.candidates)
	confirmed := readLearningEntriesIfPresent(paths.confirmedLearnings)
	if len(candidates) != 1 || intFromAny(candidates[0]["occurrence_count"]) != 2 || len(confirmed) != 1 || confirmed[0]["status"] != "confirmed" {
		t.Fatalf("reads changed candidate/confirmed lifecycle: candidates=%#v confirmed=%#v", candidates, confirmed)
	}
}
