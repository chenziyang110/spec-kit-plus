package main

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"runtime"
	"sort"
	"strconv"
	"strings"
	"testing"
	"time"

	runtimeconfig "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/config"
)

func TestLearningStartAndListAreReadOnlyCompact(t *testing.T) {
	root := t.TempDir()
	mustMkdirLearningTest(t, filepath.Join(root, ".specify"))

	start := runLearningEnvelopeTest(t, []string{"start", "--project-root", root, "--command", "spx-plan", "--format", "json"})
	if start.Status != "ok" {
		t.Fatalf("start status = %s blockers=%v", start.Status, start.Blockers)
	}
	if start.Data["command"] != "sp-plan" || start.Data["read_only"] != true {
		t.Fatalf("unexpected start payload: %#v", start.Data)
	}
	if _, err := os.Stat(filepath.Join(root, ".specify", "memory", "learnings", "INDEX.md")); !os.IsNotExist(err) {
		t.Fatalf("read-only start created learning index or returned unexpected stat err: %v", err)
	}

	list := runLearningEnvelopeTest(t, []string{"list", "--project-root", root, "--command", "plan", "--format", "json"})
	if list.Status != "ok" {
		t.Fatalf("list status = %s blockers=%v", list.Status, list.Blockers)
	}
	if list.Data["items"].([]any) == nil || len(list.Data["warnings"].([]any)) == 0 {
		t.Fatalf("missing compact list warnings/items: %#v", list.Data)
	}
}

func TestLearningCaptureShowPromoteLifecycle(t *testing.T) {
	root := t.TempDir()
	mustMkdirLearningTest(t, filepath.Join(root, ".specify"))

	capture := runLearningEnvelopeTest(t, []string{
		"capture", "--project-root", root,
		"--command", "debug",
		"--type", "tooling_trap",
		"--summary", "Watcher loops can masquerade as process-manager failures",
		"--evidence", "Repeated process fixes failed; excluding the log directory stopped restarts.",
		"--recurrence-key", "debug.watcher-loop",
		"--false-start", "job object cleanup",
		"--rejected-path", "process manager root cause",
		"--decisive-signal", "watcher ignore stopped restarts",
		"--context", "operation_owner=Watcher",
		"--format", "json",
	})
	if capture.Status != "ok" || capture.Data["status"] != "candidate" {
		t.Fatalf("capture failed: %#v", capture)
	}
	entry := capture.Data["entry"].(map[string]any)
	if entry["recurrence_key"] != "debug.watcher-loop" || entry["status"] != "candidate" {
		t.Fatalf("unexpected captured entry: %#v", entry)
	}
	if filepath.IsAbs(capture.Data["detail_path"].(string)) {
		t.Fatalf("detail path should be project-relative: %#v", capture.Data["detail_path"])
	}
	if _, err := os.Stat(filepath.Join(root, filepath.FromSlash(capture.Data["detail_path"].(string)))); err != nil {
		t.Fatalf("detail path missing: %v", err)
	}

	show := runLearningEnvelopeTest(t, []string{"show", "--project-root", root, "--ref", "debug.watcher-loop", "--format", "json"})
	if show.Data["ref"] != "debug.watcher-loop" || show.Data["status"] != "candidate" {
		t.Fatalf("unexpected show payload: %#v", show.Data)
	}
	if filepath.IsAbs(show.Data["detail_path"].(string)) || strings.Contains(show.Data["detail_path"].(string), root) {
		t.Fatalf("show detail path should be a safe relative ref: %#v", show.Data["detail_path"])
	}
	guidance := show.Data["guidance"].(map[string]any)
	if guidance["action"] == "" {
		t.Fatalf("show did not expose guidance action: %#v", guidance)
	}

	promote := runLearningEnvelopeTest(t, []string{"promote", "--project-root", root, "--recurrence-key", "debug.watcher-loop", "--target", "learning", "--format", "json"})
	if promote.Status != "ok" || promote.Data["status"] != "confirmed" {
		t.Fatalf("promote failed: %#v", promote)
	}
	confirmed := readLearningEntriesIfPresent(filepath.Join(root, ".specify", "memory", "learnings", "confirmed.md"))
	candidates := readLearningEntriesIfPresent(filepath.Join(root, ".planning", "learnings", "candidates.md"))
	if len(confirmed) != 1 || len(candidates) != 0 {
		t.Fatalf("promotion storage mismatch: confirmed=%d candidates=%d", len(confirmed), len(candidates))
	}
}

func TestLearningCaptureSanitizesSensitiveFieldsBeforePersistenceAndOutput(t *testing.T) {
	root := t.TempDir()
	mustMkdirLearningTest(t, filepath.Join(root, ".specify"))
	privateKey := "-----BEGIN PRIVATE KEY-----\nabc123\n-----END PRIVATE KEY-----"
	forbidden := []string{
		"secret=hunter2", "password=hunter2", "token=hunter2", "api_key=hunter2", "Authorization: Bearer abc.def.ghi",
		"ghp_1234567890abcdef", "sk-abcdefghijklmnopqrstuvwxyz1234567890", "AKIAIOSFODNN7EXAMPLE",
		"person@example.com", `C:\Users\alice\.ssh\id_rsa`, "/home/alice/.ssh/id_rsa", "/Users/alice/.ssh/id_rsa", "alice:secret@example.com", privateKey,
	}
	capture := runLearningEnvelopeTest(t, []string{
		"capture", "--project-root", root,
		"--command", "debug",
		"--type", "tooling_trap",
		"--summary", "secret=hunter2 leaked for person@example.com in C:\\Users\\alice\\.ssh\\id_rsa",
		"--problem", "Authorization: Bearer abc.def.ghi and https://alice:secret@example.com should not persist",
		"--action", "Rotate sk-abcdefghijklmnopqrstuvwxyz1234567890 and AKIAIOSFODNN7EXAMPLE from /home/alice/.aws/credentials",
		"--evidence", privateKey + "\napi_key=hunter2\npath=/Users/alice/project",
		"--recurrence-key", "debug.secret.hunter2.person@example.com.C:\\Users\\alice\\project",
		"--false-start", "used ghp_1234567890abcdef",
		"--rejected-path", "password=hunter2",
		"--decisive-signal", "token=hunter2",
		"--root-cause-family", "secret=hunter2",
		"--promotion-hint", "contact person@example.com",
		"--avoid", "Authorization=Bearer abc.def.ghi",
		"--trigger", "api_key=hunter2",
		"--success", "no email person@example.com",
		"--exception", "/Users/alice/project allowed only locally",
		"--format", "json",
	})
	if capture.Status != "ok" {
		t.Fatalf("capture failed: %#v", capture)
	}
	entry := capture.Data["entry"].(map[string]any)
	if entry["sensitivity"] != "sanitized" {
		t.Fatalf("expected sanitized sensitivity: %#v", entry)
	}
	assertStringSetLearningTest(t, anyStringSlice(entry["redaction_labels"]), []string{"credential", "email", "machine_path", "private_key"})
	for _, env := range []Envelope{
		capture,
		runLearningEnvelopeTest(t, []string{"list", "--project-root", root, "--command", "debug", "--format", "json"}),
		runLearningEnvelopeTest(t, []string{"show", "--project-root", root, "--ref", stringFromAny(entry["recurrence_key"]), "--format", "json"}),
		runLearningEnvelopeTest(t, []string{"start", "--project-root", root, "--command", "debug", "--format", "json"}),
	} {
		assertLearningJSONOmits(t, env, forbidden)
	}
	list := runLearningEnvelopeTest(t, []string{"list", "--project-root", root, "--command", "debug", "--format", "json"})
	card := list.Data["items"].([]any)[0].(map[string]any)
	if card["sensitivity"] != "sanitized" {
		t.Fatalf("summary card missing sensitivity metadata: %#v", card)
	}
	assertStringSetLearningTest(t, anyStringSlice(card["redaction_labels"]), []string{"credential", "email", "machine_path", "private_key"})
	show := runLearningEnvelopeTest(t, []string{"show", "--project-root", root, "--ref", stringFromAny(entry["recurrence_key"]), "--format", "json"})
	contentSafety := show.Data["content_safety"].(map[string]any)
	if contentSafety["sensitivity"] != "sanitized" {
		t.Fatalf("show content safety missing sanitized status: %#v", contentSafety)
	}
	assertStringSetLearningTest(t, anyStringSlice(contentSafety["redaction_labels"]), []string{"credential", "email", "machine_path", "private_key"})
	if filepath.IsAbs(show.Data["detail_path"].(string)) || strings.Contains(show.Data["detail_path"].(string), root) {
		t.Fatalf("show detail path should not leak root: %#v", show.Data["detail_path"])
	}
	for _, rel := range []string{
		filepath.Join(".planning", "learnings", "candidates.md"),
		filepath.Join(".specify", "memory", "learnings", "INDEX.md"),
		filepath.Join(".specify", "memory", "learnings"),
	} {
		path := filepath.Join(root, rel)
		info, err := os.Stat(path)
		if err != nil {
			t.Fatalf("stat %s: %v", path, err)
		}
		if info.IsDir() {
			entries, err := os.ReadDir(path)
			if err != nil {
				t.Fatalf("readdir %s: %v", path, err)
			}
			for _, entry := range entries {
				if !entry.IsDir() && strings.HasPrefix(entry.Name(), "learn-") {
					assertLearningFileOmits(t, filepath.Join(path, entry.Name()), forbidden)
				}
			}
			continue
		}
		assertLearningFileOmits(t, path, forbidden)
	}
}

func TestLearningDuplicateCaptureUnionsSafetyMetadataFromIncomingLists(t *testing.T) {
	root := t.TempDir()
	mustMkdirLearningTest(t, filepath.Join(root, ".specify"))
	first := runLearningEnvelopeTest(t, []string{
		"capture", "--project-root", root,
		"--command", "debug",
		"--type", "tooling_trap",
		"--summary", "duplicate starts safe",
		"--evidence", "safe evidence",
		"--recurrence-key", "debug.duplicate-safety-merge",
		"--format", "json",
	})
	if first.Status != "ok" {
		t.Fatalf("first capture failed: %#v", first)
	}
	second := runLearningEnvelopeTest(t, []string{
		"capture", "--project-root", root,
		"--command", "debug",
		"--type", "tooling_trap",
		"--summary", "duplicate remains safe text",
		"--evidence", "safe evidence",
		"--recurrence-key", "debug.duplicate-safety-merge",
		"--false-start", "retry used token=ghp_1234567890abcdef",
		"--success", "notify person@example.com",
		"--format", "json",
	})
	if second.Status != "ok" {
		t.Fatalf("second capture failed: %#v", second)
	}
	entry := second.Data["entry"].(map[string]any)
	if entry["sensitivity"] != "sanitized" {
		t.Fatalf("merged entry lost sanitized sensitivity: %#v", entry)
	}
	assertStringSetLearningTest(t, anyStringSlice(entry["redaction_labels"]), []string{"credential", "email"})
	stored := readLearningEntriesIfPresent(filepath.Join(root, ".planning", "learnings", "candidates.md"))
	if len(stored) != 1 || stored[0]["sensitivity"] != "sanitized" {
		t.Fatalf("stored duplicate lost sensitivity: %#v", stored)
	}
	assertStringSetLearningTest(t, anyStringSlice(stored[0]["redaction_labels"]), []string{"credential", "email"})
	list := runLearningEnvelopeTest(t, []string{"list", "--project-root", root, "--command", "debug", "--format", "json"})
	card := list.Data["items"].([]any)[0].(map[string]any)
	if card["sensitivity"] != "sanitized" {
		t.Fatalf("list card lost sanitized sensitivity: %#v", card)
	}
	assertStringSetLearningTest(t, anyStringSlice(card["redaction_labels"]), []string{"credential", "email"})
	show := runLearningEnvelopeTest(t, []string{"show", "--project-root", root, "--ref", "debug.duplicate-safety-merge", "--format", "json"})
	contentSafety := show.Data["content_safety"].(map[string]any)
	if contentSafety["sensitivity"] != "sanitized" {
		t.Fatalf("show lost sanitized sensitivity: %#v", contentSafety)
	}
	assertStringSetLearningTest(t, anyStringSlice(contentSafety["redaction_labels"]), []string{"credential", "email"})
}

func TestLearningCaptureSanitizesJSONCredentialAssignments(t *testing.T) {
	root := t.TempDir()
	mustMkdirLearningTest(t, filepath.Join(root, ".specify"))
	capture := runLearningEnvelopeTest(t, []string{
		"capture", "--project-root", root,
		"--command", "debug",
		"--type", "tooling_trap",
		"--summary", `JSON credentials should preserve key semantics`,
		"--evidence", `{"password":"hunter2","api_key":"opaque-value","authorization":"Bearer abc.def.ghi","safe":"kept"}`,
		"--recurrence-key", "debug.json-credential-assignment",
		"--format", "json",
	})
	if capture.Status != "ok" {
		t.Fatalf("capture failed: %#v", capture)
	}
	entry := capture.Data["entry"].(map[string]any)
	if entry["sensitivity"] != "sanitized" {
		t.Fatalf("json credentials were not marked sanitized: %#v", entry)
	}
	assertStringSetLearningTest(t, anyStringSlice(entry["redaction_labels"]), []string{"credential"})
	if entry["evidence"] != `{"password":"[REDACTED_SECRET]","api_key":"[REDACTED_SECRET]","authorization":"[REDACTED_SECRET]","safe":"kept"}` {
		t.Fatalf("json credential projection was not stable: %#v", entry["evidence"])
	}
	idempotent := redactLearningText(stringFromAny(entry["evidence"]))
	if idempotent.text != entry["evidence"] || !learningContainsString(idempotent.labels, "credential") {
		t.Fatalf("sanitized projection lost idempotence metadata: %#v", idempotent)
	}
	for _, env := range []Envelope{
		capture,
		runLearningEnvelopeTest(t, []string{"list", "--project-root", root, "--command", "debug", "--format", "json"}),
		runLearningEnvelopeTest(t, []string{"show", "--project-root", root, "--ref", "debug.json-credential-assignment", "--format", "json"}),
	} {
		assertLearningJSONOmits(t, env, []string{"hunter2", "opaque-value"})
	}
	assertLearningFileOmits(t, filepath.Join(root, ".planning", "learnings", "candidates.md"), []string{"hunter2", "opaque-value"})
}

func TestLearningBlockedEnvelopeSanitizesInvalidSensitiveInput(t *testing.T) {
	root := t.TempDir()
	mustMkdirLearningTest(t, filepath.Join(root, ".specify"))
	env := runLearningEnvelopeTest(t, []string{
		"list", "--project-root", root,
		"--status", "token=ghp_1234567890abcdef",
		"--format", "json",
	})
	if env.Status != "blocked" {
		t.Fatalf("invalid status should block: %#v", env)
	}
	assertLearningJSONOmits(t, env, []string{"ghp_1234567890abcdef"})
}

func TestLearningCaptureAutoQuickDuplicateAndExplicitPromotion(t *testing.T) {
	root := t.TempDir()
	workspace := filepath.Join(root, ".planning", "quick", "260724-001-demo")
	mustMkdirLearningTest(t, workspace)
	mustWriteLearningTest(t, filepath.Join(workspace, "STATUS.md"), `---
id: "260724-001"
title: "Demo quick task"
status: "blocked"
---

## Current Focus
goal: keep the worker result contract aligned
next_action: wait for runtime recovery

## Execution
execution_fallback: native worker runtime unavailable
blocker_reason: runtime unavailable
recovery_action: retry after runtime comes back
retry_attempts: 1

## Validation
completed_checks: []
`)

	first := runLearningEnvelopeTest(t, []string{"capture-auto", "--project-root", root, "--command", "quick", "--workspace", ".planning/quick/260724-001-demo", "--format", "json"})
	if first.Status != "ok" || first.Data["status"] != "captured" {
		t.Fatalf("first capture-auto failed: %#v", first)
	}
	captured := first.Data["captured"].([]any)
	if len(captured) != 1 {
		t.Fatalf("captured len = %d", len(captured))
	}
	stored := captured[0].(map[string]any)["entry"].(map[string]any)
	if stored["recurrence_key"] != "quick.leader-inline-fallback-preserves-runtime-unavailability-reason" {
		t.Fatalf("unexpected auto-captured key: %#v", stored)
	}

	second := runLearningEnvelopeTest(t, []string{"capture-auto", "--project-root", root, "--command", "quick", "--workspace", ".planning/quick/260724-001-demo", "--format", "json"})
	if second.Data["status"] != "duplicate-snapshot" {
		t.Fatalf("duplicate snapshot was not detected: %#v", second.Data)
	}

	directRule := runLearningEnvelopeTest(t, []string{"promote", "--project-root", root, "--recurrence-key", "quick.leader-inline-fallback-preserves-runtime-unavailability-reason", "--target", "rule", "--format", "json"})
	if directRule.Status != "blocked" {
		t.Fatalf("candidate direct rule promotion should be blocked: %#v", directRule)
	}
	learning := runLearningEnvelopeTest(t, []string{"promote", "--project-root", root, "--recurrence-key", "quick.leader-inline-fallback-preserves-runtime-unavailability-reason", "--target", "learning", "--format", "json"})
	if learning.Data["status"] != "confirmed" {
		t.Fatalf("learning promotion failed: %#v", learning.Data)
	}
	rule := runLearningEnvelopeTest(t, []string{"promote", "--project-root", root, "--recurrence-key", "quick.leader-inline-fallback-preserves-runtime-unavailability-reason", "--target", "rule", "--format", "json"})
	if rule.Data["status"] != "promoted-rule" {
		t.Fatalf("rule promotion failed: %#v", rule.Data)
	}
	rules := readLearningEntriesIfPresent(filepath.Join(root, ".specify", "memory", "project-rules.md"))
	if len(rules) != 1 || rules[0]["status"] != "promoted-rule" {
		t.Fatalf("rule storage mismatch: %#v", rules)
	}
}

func TestLearningAutoCaptureSemanticSignalsUseSafeKindsDigestAndMinimalRegistry(t *testing.T) {
	root := t.TempDir()
	featureDir := filepath.Join(root, "specs", "001-sensitive")
	mustMkdirLearningTest(t, featureDir)
	mustWriteLearningTest(t, filepath.Join(featureDir, "workflow-state.md"), `## Current
status: blocked
phase_mode: test
trigger_signals:
- user_correction: contact person@example.com with token=ghp_1234567890abcdef from C:\Users\alice\.ssh\id_rsa
`)
	forbidden := []string{"person@example.com", "ghp_1234567890abcdef", `C:\Users\alice\.ssh\id_rsa`}
	capture := runLearningEnvelopeTest(t, []string{"capture-auto", "--project-root", root, "--command", "plan", "--feature-dir", "specs/001-sensitive", "--format", "json"})
	if capture.Status != "ok" || capture.Data["status"] != "captured" {
		t.Fatalf("semantic auto-capture failed: %#v", capture)
	}
	if capture.Data["source_path"] != "specs/001-sensitive/workflow-state.md" {
		t.Fatalf("source path should be project-relative: %#v", capture.Data["source_path"])
	}
	assertLearningJSONOmits(t, capture, forbidden)
	captured := capture.Data["captured"].([]any)
	stored := captured[0].(map[string]any)["entry"].(map[string]any)
	if strings.Contains(stringFromAny(stored["recurrence_key"]), "person") || strings.Contains(stringFromAny(stored["recurrence_key"]), "ghp") || !strings.Contains(stringFromAny(stored["recurrence_key"]), ".digest-") {
		t.Fatalf("unsafe recurrence key: %#v", stored["recurrence_key"])
	}
	evidence := stringFromAny(stored["evidence"])
	if strings.Contains(evidence, root) || !strings.Contains(evidence, "feature_dir: specs/001-sensitive") {
		t.Fatalf("semantic evidence should use a project-relative feature ref: %q", evidence)
	}
	assertStringSetLearningTest(t, anyStringSlice(stored["trigger_signals"]), []string{"user_correction"})
	registryRaw, err := os.ReadFile(filepath.Join(root, ".planning", "learnings", "auto-capture.json"))
	if err != nil {
		t.Fatalf("read registry: %v", err)
	}
	if bytes.Contains(registryRaw, []byte("captured_entries")) {
		t.Fatalf("registry retained captured_entries: %s", string(registryRaw))
	}
	if !bytes.Contains(registryRaw, []byte(`"source_ref": "specs/001-sensitive/workflow-state.md"`)) {
		t.Fatalf("registry missing relative source_ref: %s", string(registryRaw))
	}
	for _, forbiddenValue := range forbidden {
		if bytes.Contains(registryRaw, []byte(forbiddenValue)) {
			t.Fatalf("registry leaked %q: %s", forbiddenValue, string(registryRaw))
		}
	}
}

func TestLearningCaptureAutoMigratesLegacyRegistryBeforeDuplicateCheck(t *testing.T) {
	root := t.TempDir()
	workspace := filepath.Join(root, ".planning", "quick", "260724-002-legacy-registry")
	mustMkdirLearningTest(t, workspace)
	mustWriteLearningTest(t, filepath.Join(workspace, "STATUS.md"), `---
id: "260724-002"
title: "Legacy registry"
status: "blocked"
---

## Current Focus
goal: keep registry minimal

## Execution
execution_fallback: native worker runtime unavailable
blocker_reason: runtime unavailable
recovery_action: retry after runtime comes back
`)
	service := learningService{projectRoot: root}
	sourcePath, suggestions, err := service.suggestQuickAutoCapture(".planning/quick/260724-002-legacy-registry")
	if err != nil {
		t.Fatalf("suggest quick: %v", err)
	}
	policy := builtinLearningPolicy()
	fingerprint, err := learningSnapshotFingerprint("sp-quick", service.learningSourceRef(sourcePath), suggestions, policy)
	if err != nil {
		t.Fatalf("fingerprint: %v", err)
	}
	legacyKey := "legacy.person@example.com.token=ghp_1234567890abcdef"
	legacySource := filepath.Join(root, ".planning", "quick", "260724-002-legacy-registry", "STATUS.md")
	mustWriteLearningTest(t, filepath.Join(root, ".planning", "learnings", "auto-capture.json"), `{
  "`+legacyKey+`": {
    "command": "sp-debug",
    "source_path": "`+strings.ReplaceAll(legacySource, `\`, `\\`)+`",
    "recurrence_keys": ["debug.person@example.com.token=ghp_1234567890abcdef"],
    "captured_entries": [{"summary":"token=ghp_1234567890abcdef", "evidence":"person@example.com"}],
    "unknown": "secret=hunter2",
    "captured_at": "2026-01-01T00:00:00Z"
  },
  "`+fingerprint+`": {
    "command": "sp-quick",
    "source_path": "`+strings.ReplaceAll(legacySource, `\`, `\\`)+`",
    "recurrence_keys": ["quick.leader-inline-fallback-preserves-runtime-unavailability-reason"],
    "captured_entries": [{"summary":"person@example.com"}],
	"captured_at": "person@example.com"
	},
	"invalid-command-entry": {
	  "command": "token=ghp_1234567890abcdef",
	  "source_path": "`+strings.ReplaceAll(legacySource, `\`, `\\`)+`",
	  "recurrence_keys": ["unsafe.person@example.com"],
	  "captured_at": "2026-01-03T00:00:00Z"
  }
}
`)
	duplicate := runLearningEnvelopeTest(t, []string{"capture-auto", "--project-root", root, "--command", "quick", "--workspace", ".planning/quick/260724-002-legacy-registry", "--format", "json"})
	if duplicate.Status != "ok" || duplicate.Data["status"] != "duplicate-snapshot" {
		t.Fatalf("duplicate capture-auto failed: %#v", duplicate)
	}
	raw, err := os.ReadFile(filepath.Join(root, ".planning", "learnings", "auto-capture.json"))
	if err != nil {
		t.Fatalf("read registry: %v", err)
	}
	assertLearningJSONOmits(t, json.RawMessage(raw), []string{"captured_entries", "source_path", "unknown", "person@example.com", "ghp_1234567890abcdef", "secret=hunter2", legacySource})
	var migrated map[string]any
	if err := json.Unmarshal(raw, &migrated); err != nil {
		t.Fatalf("decode migrated registry: %v", err)
	}
	if _, exists := migrated[legacyKey]; exists {
		t.Fatalf("legacy sensitive fingerprint key was retained: %s", string(raw))
	}
	if _, exists := migrated[fingerprint]; !exists {
		t.Fatalf("current fingerprint key should be retained for duplicate detection: %s", string(raw))
	}
	for key, value := range migrated {
		if len(key) != 64 || strings.Contains(key, "person") {
			t.Fatalf("registry key is not safe hex: %q", key)
		}
		entry := value.(map[string]any)
		if entry["source_ref"] != ".planning/quick/260724-002-legacy-registry/STATUS.md" {
			t.Fatalf("source_ref not project-relative: %#v", entry)
		}
		if _, exists := entry["captured_entries"]; exists {
			t.Fatalf("captured_entries retained: %#v", entry)
		}
	}
}

func TestLearningCaptureAutoMigratesRelativeRegistryRefFromProjectRoot(t *testing.T) {
	root := t.TempDir()
	workspace := filepath.Join(root, ".planning", "quick", "260724-003-relative-registry")
	mustMkdirLearningTest(t, workspace)
	mustWriteLearningTest(t, filepath.Join(workspace, "STATUS.md"), `---
id: "260724-003"
status: "blocked"
---

## Current Focus
goal: relative registry ref

## Execution
execution_fallback: native worker runtime unavailable
blocker_reason: runtime unavailable
recovery_action: retry after runtime comes back
`)
	mustWriteLearningTest(t, filepath.Join(root, ".planning", "learnings", "auto-capture.json"), `{
  "legacy-relative": {
    "command": "sp-quick",
    "source_ref": ".planning/quick/260724-003-relative-registry/STATUS.md",
    "recurrence_keys": ["quick.leader-inline-fallback-preserves-runtime-unavailability-reason"],
    "captured_at": "2026-01-01T00:00:00Z"
  }
}
`)
	previousCwd, err := os.Getwd()
	if err != nil {
		t.Fatalf("get cwd: %v", err)
	}
	otherCwd := t.TempDir()
	if err := os.Chdir(otherCwd); err != nil {
		t.Fatalf("chdir: %v", err)
	}
	defer func() {
		if err := os.Chdir(previousCwd); err != nil {
			t.Fatalf("restore cwd: %v", err)
		}
	}()
	capture := runLearningEnvelopeTest(t, []string{"capture-auto", "--project-root", root, "--command", "quick", "--workspace", ".planning/quick/260724-003-relative-registry", "--format", "json"})
	if capture.Status != "ok" {
		t.Fatalf("capture-auto failed: %#v", capture)
	}
	raw, err := os.ReadFile(filepath.Join(root, ".planning", "learnings", "auto-capture.json"))
	if err != nil {
		t.Fatalf("read registry: %v", err)
	}
	if !bytes.Contains(raw, []byte(`"source_ref": ".planning/quick/260724-003-relative-registry/STATUS.md"`)) {
		t.Fatalf("relative source_ref was not preserved against project root: %s", string(raw))
	}
	if bytes.Contains(raw, []byte(filepath.ToSlash(otherCwd))) || bytes.Contains(raw, []byte(otherCwd)) {
		t.Fatalf("registry source_ref resolved against process cwd: %s", string(raw))
	}
}

func TestLearningCaptureAutoMigratesExternalAbsoluteRegistryPathToBasename(t *testing.T) {
	root := t.TempDir()
	workspace := filepath.Join(root, ".planning", "quick", "260724-004-external-registry")
	mustMkdirLearningTest(t, workspace)
	mustWriteLearningTest(t, filepath.Join(workspace, "STATUS.md"), `---
id: "260724-004"
status: "blocked"
---

## Current Focus
goal: external registry path

## Execution
execution_fallback: native worker runtime unavailable
blocker_reason: runtime unavailable
recovery_action: retry after runtime comes back
`)
	externalDir := filepath.Join(t.TempDir(), "outside", "secret-dir")
	externalPath := filepath.Join(externalDir, "STATUS.md")
	mustWriteLearningTest(t, filepath.Join(root, ".planning", "learnings", "auto-capture.json"), `{
  "legacy-external": {
    "command": "sp-quick",
    "source_path": "`+strings.ReplaceAll(externalPath, `\`, `\\`)+`",
    "recurrence_keys": ["quick.leader-inline-fallback-preserves-runtime-unavailability-reason"],
    "captured_at": "2026-01-01T00:00:00Z"
  }
}
`)
	capture := runLearningEnvelopeTest(t, []string{"capture-auto", "--project-root", root, "--command", "quick", "--workspace", ".planning/quick/260724-004-external-registry", "--format", "json"})
	if capture.Status != "ok" {
		t.Fatalf("capture-auto failed: %#v", capture)
	}
	raw, err := os.ReadFile(filepath.Join(root, ".planning", "learnings", "auto-capture.json"))
	if err != nil {
		t.Fatalf("read registry: %v", err)
	}
	if bytes.Contains(raw, []byte(filepath.ToSlash(externalDir))) || bytes.Contains(raw, []byte(externalDir)) {
		t.Fatalf("external source path leaked directory: %s", string(raw))
	}
	if !bytes.Contains(raw, []byte(`"source_ref": "STATUS.md"`)) {
		t.Fatalf("external source path should collapse to basename: %s", string(raw))
	}
}

func TestLearningSourceRefTreatsForeignAbsoluteSyntaxAsExternal(t *testing.T) {
	service := learningService{projectRoot: t.TempDir()}
	cases := map[string]string{}
	if runtime.GOOS == "windows" {
		cases[`/home/alice/secret/STATUS.md`] = "STATUS.md"
		cases[`/Users/alice/secret/STATUS.md`] = "STATUS.md"
	} else {
		cases[`C:\Users\alice\secret\STATUS.md`] = "STATUS.md"
		cases[`\\server\share\secret\STATUS.md`] = "STATUS.md"
	}
	for input, want := range cases {
		if got := service.learningSourceRef(input); got != want {
			t.Fatalf("learningSourceRef(%q) = %q, want %q", input, got, want)
		}
	}
}

func TestSafeLearningBasenameRefIsPathSyntaxNeutral(t *testing.T) {
	for _, input := range []string{
		`C:\company\private\STATUS.md`,
		`//server/share/private/STATUS.md`,
		`/srv/private/STATUS.md`,
	} {
		if got := safeLearningBasenameRef(input); got != "STATUS.md" {
			t.Fatalf("safe basename for %q = %q, want STATUS.md", input, got)
		}
	}
}

func TestRedactLearningMachinePathsAcceptsWindowsSlashVariants(t *testing.T) {
	for _, input := range []string{`C:\Users\alice\project\file.txt`, `C:/Users/alice/project/file.txt`} {
		got := redactLearningText(input)
		if got.text != "<USER_HOME>/project/file.txt" || !learningContainsString(got.labels, "machine_path") {
			t.Fatalf("machine path %q was not canonically redacted: %#v", input, got)
		}
	}
}

func TestRedactLearningMachinePathsAcceptsRootHome(t *testing.T) {
	got := redactLearningText(`/root/project/file.txt`)
	if got.text != "<USER_HOME>/project/file.txt" || !learningContainsString(got.labels, "machine_path") {
		t.Fatalf("root home path was not canonically redacted: %#v", got)
	}
	bare := redactLearningText(`home is /root`)
	if bare.text != "home is <USER_HOME>" || !learningContainsString(bare.labels, "machine_path") {
		t.Fatalf("bare root home was not canonically redacted: %#v", bare)
	}
	ordinary := redactLearningText(`/rooted/project/file.txt`)
	if ordinary.text != `/rooted/project/file.txt` || learningContainsString(ordinary.labels, "machine_path") {
		t.Fatalf("non-home rooted path was over-redacted: %#v", ordinary)
	}
}

func TestRedactLearningTextRemovesBareJWT(t *testing.T) {
	token := "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.signaturevalue"
	got := redactLearningText("jwt=" + token)
	if strings.Contains(got.text, token) || !learningContainsString(got.labels, "credential") {
		t.Fatalf("bare JWT was not redacted: %#v", got)
	}
}

func TestSafeLearningPathRejectsExternalAndSymlinkEscape(t *testing.T) {
	root := t.TempDir()
	external := t.TempDir()
	if _, err := safeLearningPath(root, external); err == nil {
		t.Fatal("external absolute learning input should be rejected")
	}
	link := filepath.Join(root, "linked-external")
	if err := os.Symlink(external, link); err != nil {
		t.Skipf("symlink creation unavailable: %v", err)
	}
	if _, err := safeLearningPath(root, link); err == nil {
		t.Fatal("learning input crossing a symlink should be rejected")
	}
}

func TestLearningStartRanksContextMatchesAndProtectsStableQuota(t *testing.T) {
	root := t.TempDir()
	mustMkdirLearningTest(t, filepath.Join(root, ".specify"))
	for i := 0; i < 20; i++ {
		capture := runLearningEnvelopeTest(t, []string{"capture", "--project-root", root, "--command", "debug", "--type", "tooling_trap", "--summary", "generic candidate", "--evidence", "generic candidate evidence", "--recurrence-key", "debug.generic-candidate-" + strconv.Itoa(i), "--signal", "high", "--format", "json"})
		if capture.Status != "ok" {
			t.Fatalf("candidate %d capture failed: %#v", i, capture)
		}
		if got, want := stringFromAny(mapStringAny(capture.Data["entry"])["recurrence_key"]), "debug.generic-candidate-"+strconv.Itoa(i); got != want {
			t.Fatalf("candidate %d recurrence key=%q want=%q data=%#v", i, got, want, capture.Data)
		}
	}
	runLearningEnvelopeTest(t, []string{"capture", "--project-root", root, "--command", "debug", "--type", "tooling_trap", "--summary", "stable exact context", "--evidence", "stable exact context evidence", "--recurrence-key", "debug.zzz-stable-exact-context", "--context", "operation_owner=ExactOwner", "--format", "json"})
	runLearningEnvelopeTest(t, []string{"promote", "--project-root", root, "--recurrence-key", "debug.zzz-stable-exact-context", "--target", "learning", "--format", "json"})
	runLearningEnvelopeTest(t, []string{"promote", "--project-root", root, "--recurrence-key", "debug.zzz-stable-exact-context", "--target", "rule", "--format", "json"})
	runLearningEnvelopeTest(t, []string{"capture", "--project-root", root, "--command", "debug", "--type", "tooling_trap", "--summary", "confirmed generic", "--evidence", "confirmed generic evidence", "--recurrence-key", "debug.zzz-confirmed-generic", "--format", "json"})
	runLearningEnvelopeTest(t, []string{"promote", "--project-root", root, "--recurrence-key", "debug.zzz-confirmed-generic", "--target", "learning", "--format", "json"})

	start := runLearningEnvelopeTest(t, []string{"start", "--project-root", root, "--command", "debug", "--context", "operation_owner=ExactOwner", "--format", "json"})
	items := start.Data["items"].([]any)
	if len(items) != 20 {
		t.Fatalf("start returned %d items, want 20", len(items))
	}
	pagination := start.Data["pagination"].(map[string]any)
	if intFromAny(pagination["total"]) <= 20 || pagination["next_argv"] == nil {
		t.Fatalf("start did not expose full list continuation: %#v", pagination)
	}
	if intFromAny(pagination["next_cursor"]) != 0 || !learningAnySliceContains(pagination["next_argv"], "--cursor") || !learningAnySliceContains(pagination["next_argv"], "0") {
		t.Fatalf("start continuation should expand full list from cursor 0: %#v", pagination)
	}
	seenExact, seenStable := false, false
	for _, item := range items {
		card := item.(map[string]any)
		if card["ref"] == "debug.zzz-stable-exact-context" {
			seenExact = true
		}
		status := stringFromAny(card["status"])
		if status == "confirmed" || status == "promoted-rule" {
			seenStable = true
		}
	}
	if !seenExact || !seenStable {
		t.Fatalf("context/stable quota failed exact=%v stable=%v items=%#v", seenExact, seenStable, items)
	}
	noContextStart := runLearningEnvelopeTest(t, []string{"start", "--project-root", root, "--command", "debug", "--format", "json"})
	noContextStable := false
	for _, item := range noContextStart.Data["items"].([]any) {
		status := stringFromAny(item.(map[string]any)["status"])
		if status == "confirmed" || status == "promoted-rule" {
			noContextStable = true
		}
	}
	if !noContextStable {
		t.Fatalf("no-context start did not protect stable cards: %#v", noContextStart.Data["items"])
	}
	list := runLearningEnvelopeTest(t, []string{"list", "--project-root", root, "--command", "debug", "--context", "operation_owner=ExactOwner", "--limit", "20", "--format", "json"})
	listItems := list.Data["items"].([]any)
	if len(listItems) != 20 {
		t.Fatalf("explicit list returned %d items, want normal limit 20", len(listItems))
	}
	candidates := 0
	for _, item := range listItems {
		if item.(map[string]any)["status"] == "candidate" {
			candidates++
		}
	}
	if candidates <= 5 {
		t.Fatalf("explicit list appears to use start quota: candidates=%d items=%#v", candidates, listItems)
	}
}

func TestLearningLegacyEntriesDefaultSafeAndRedactOnRead(t *testing.T) {
	root := t.TempDir()
	mustMkdirLearningTest(t, filepath.Join(root, ".specify", "memory", "learnings"))
	entry := map[string]any{
		"id": "LRN-legacy", "summary": "legacy token=ghp_1234567890abcdef", "learning_type": "tooling_trap", "source_command": "sp-debug",
		"evidence": "contact person@example.com in /home/alice/project", "recurrence_key": "legacy.email.person@example.com", "default_scope": "cross-workflow",
		"applies_to": []any{"sp-debug"}, "signal_strength": "medium", "status": "confirmed", "first_seen": "2026-01-01T00:00:00Z", "last_seen": "2026-01-01T00:00:00Z", "occurrence_count": float64(1),
		"problem": "secret=abc", "recommended_action": "use C:\\Users\\alice\\project",
		"redaction_labels":           []any{"credential", "legacy_bad_label"},
		"token=ghp_1234567890abcdef": "legacy unknown field",
	}
	mustWriteLearningTest(t, filepath.Join(root, ".specify", "memory", "learnings", "confirmed.md"), renderLearningFile("# Confirmed", []map[string]any{entry}))
	list := runLearningEnvelopeTest(t, []string{"list", "--project-root", root, "--command", "debug", "--format", "json"})
	show := runLearningEnvelopeTest(t, []string{"show", "--project-root", root, "--ref", "legacy.email.person@example.com", "--format", "json"})
	assertLearningJSONOmits(t, list, []string{"ghp_1234567890abcdef", "person@example.com", "/home/alice/project", "secret=abc", `C:\Users\alice\project`})
	assertLearningJSONOmits(t, show, []string{"ghp_1234567890abcdef", "person@example.com", "/home/alice/project", "secret=abc", `C:\Users\alice\project`})
	contentSafety := show.Data["content_safety"].(map[string]any)
	if contentSafety["sensitivity"] != "sanitized" {
		t.Fatalf("legacy output did not default sensitivity safely: %#v", show.Data)
	}
	assertStringSetLearningTest(t, anyStringSlice(contentSafety["redaction_labels"]), []string{"credential", "email", "machine_path"})
	runLearningEnvelopeTest(t, []string{"capture", "--project-root", root, "--command", "debug", "--type", "tooling_trap", "--summary", "legacy merge", "--evidence", "safe evidence", "--recurrence-key", "legacy.email.person@example.com", "--confirm", "--format", "json"})
	assertLearningFileOmits(t, filepath.Join(root, ".specify", "memory", "learnings", "confirmed.md"), []string{"ghp_1234567890abcdef"})
}

func TestLearningMissingRefErrorsSanitizeRawInput(t *testing.T) {
	root := t.TempDir()
	mustMkdirLearningTest(t, filepath.Join(root, ".specify"))
	rawRef := "missing.person@example.com.token=ghp_1234567890abcdef.C:\\Users\\alice\\project"
	show := runLearningEnvelopeTest(t, []string{"show", "--project-root", root, "--ref", rawRef, "--format", "json"})
	if show.Status != "blocked" {
		t.Fatalf("show missing ref should be blocked: %#v", show)
	}
	promote := runLearningEnvelopeTest(t, []string{"promote", "--project-root", root, "--recurrence-key", rawRef, "--target", "learning", "--format", "json"})
	if promote.Status != "blocked" {
		t.Fatalf("promote missing ref should be blocked: %#v", promote)
	}
	assertLearningJSONOmits(t, show, []string{"person@example.com", "ghp_1234567890abcdef", `C:\Users\alice\project`})
	assertLearningJSONOmits(t, promote, []string{"person@example.com", "ghp_1234567890abcdef", `C:\Users\alice\project`})
}

func TestLearningListStartSanitizeFiltersContextAndArgv(t *testing.T) {
	root := t.TempDir()
	mustMkdirLearningTest(t, filepath.Join(root, ".specify"))
	for i := 0; i < 21; i++ {
		runLearningEnvelopeTest(t, []string{"capture", "--project-root", root, "--command", "debug", "--type", "tooling_trap", "--summary", "generic", "--evidence", "generic evidence", "--recurrence-key", "debug.filter-context-" + strconv.Itoa(i), "--context", "operation_owner=person@example.com", "--format", "json"})
	}
	forbidden := []string{"person@example.com", "ghp_1234567890abcdef", `C:\Users\alice\project`}
	list := runLearningEnvelopeTest(t, []string{"list", "--project-root", root, "--command", "debug", "--query", "person@example.com token=ghp_1234567890abcdef", "--context", "operation_owner=C:\\Users\\alice\\project", "--limit", "1", "--format", "json"})
	start := runLearningEnvelopeTest(t, []string{"start", "--project-root", root, "--command", "debug", "--context", "operation_owner=person@example.com", "--format", "json"})
	assertLearningJSONOmits(t, list, forbidden)
	assertLearningJSONOmits(t, start, forbidden)
	if _, exists := list.Data["sensitivity"]; exists {
		t.Fatalf("summaryList should not expose top-level sensitivity: %#v", list.Data)
	}
}

type learningAssessmentFixture struct {
	TextCases []struct {
		ID                string                              `json:"id"`
		Input             string                              `json:"input"`
		Policy            runtimeconfig.ProjectLearningConfig `json:"policy"`
		ExpectedOutput    string                              `json:"expected_output"`
		ExpectedLabels    []string                            `json:"expected_labels"`
		ExpectedContains  []string                            `json:"expected_contains"`
		ForbiddenContains []string                            `json:"forbidden_contains"`
	} `json:"text_cases"`
	AssessmentCases []struct {
		ID                  string                              `json:"id"`
		Source              string                              `json:"source"`
		LearningType        string                              `json:"learning_type"`
		SignalStrength      string                              `json:"signal_strength"`
		Occurrences         int                                 `json:"occurrences"`
		Summary             string                              `json:"summary"`
		Evidence            string                              `json:"evidence"`
		RecommendedAction   string                              `json:"recommended_action"`
		TriggerSignals      []string                            `json:"trigger_signals"`
		Policy              runtimeconfig.ProjectLearningConfig `json:"policy"`
		ExpectedValueTier   string                              `json:"expected_value_tier"`
		ExpectedReasonCodes []string                            `json:"expected_reason_codes"`
		ExpectedDecision    string                              `json:"expected_decision"`
	} `json:"assessment_cases"`
}

func TestLearningAssessmentFixtureContract(t *testing.T) {
	raw, err := os.ReadFile(filepath.Join("..", "..", "tests", "fixtures", "project_learning_assessment_v1.json"))
	if err != nil {
		t.Fatal(err)
	}
	var fixture learningAssessmentFixture
	if err := json.Unmarshal(raw, &fixture); err != nil {
		t.Fatal(err)
	}
	for _, tc := range fixture.TextCases {
		t.Run("text/"+tc.ID, func(t *testing.T) {
			policy := learningPolicyFromConfig(tc.Policy)
			redacted := redactLearningTextWithPolicy(tc.Input, policy)
			assertStringSetLearningTest(t, redacted.labels, tc.ExpectedLabels)
			if tc.ExpectedOutput != "" && redacted.text != tc.ExpectedOutput {
				t.Fatalf("redacted text=%q want exact %q", redacted.text, tc.ExpectedOutput)
			}
			for _, expected := range tc.ExpectedContains {
				if !strings.Contains(redacted.text, expected) {
					t.Fatalf("redacted text %q does not contain %q", redacted.text, expected)
				}
			}
			for _, forbidden := range tc.ForbiddenContains {
				if strings.Contains(redacted.text, forbidden) {
					t.Fatalf("redacted text leaks %q: %q", forbidden, redacted.text)
				}
			}
		})
	}
	for _, tc := range fixture.AssessmentCases {
		t.Run("assessment/"+tc.ID, func(t *testing.T) {
			policy := learningPolicyFromConfig(tc.Policy)
			entry := sanitizeLearningEntryWithPolicy(map[string]any{
				"summary": tc.Summary, "evidence": tc.Evidence, "problem": tc.Summary,
				"recommended_action": tc.RecommendedAction, "learning_type": tc.LearningType,
				"signal_strength": tc.SignalStrength, "occurrence_count": float64(tc.Occurrences),
				"trigger_signals": stringsToAny(tc.TriggerSignals),
			}, policy)
			entry = applyLearningAssessment(entry, tc.Source)
			if entry["learning_value_tier"] != tc.ExpectedValueTier {
				t.Fatalf("tier=%v want=%s entry=%#v", entry["learning_value_tier"], tc.ExpectedValueTier, entry)
			}
			assertStringSetLearningTest(t, anyStringSlice(entry["learning_value_reason_codes"]), tc.ExpectedReasonCodes)
			if entry["assessment_decision"] != tc.ExpectedDecision || stringFromAny(entry["assessment_reason"]) == "" {
				t.Fatalf("unexpected assessment decision: %#v", entry)
			}
		})
	}
}

func TestLearningAssessmentProjectionRejectsTamperedCanonicalFields(t *testing.T) {
	entry := applyLearningAssessment(sanitizeLearningEntry(map[string]any{
		"summary": "Preserve the reusable runtime boundary", "evidence": "The runtime boundary failed during validation",
		"problem": "The runtime boundary failed during validation", "recommended_action": "Validate the runtime boundary before retrying",
		"learning_type": "workflow_gap", "signal_strength": "high", "occurrence_count": float64(1),
	}), "manual")
	if learningAssessmentProjection(entry) == nil {
		t.Fatalf("canonical assessment was rejected: %#v", entry)
	}
	for name, mutate := range map[string]func(map[string]any){
		"unknown_reason": func(value map[string]any) { value["learning_value_reason_codes"] = []any{"not-canonical"} },
		"bad_risk":       func(value map[string]any) { value["sensitivity_risk_tier"] = "high" },
		"duplicate_label": func(value map[string]any) {
			value["sensitivity"] = "sanitized"
			value["redaction_labels"] = []any{"email", "email"}
			value["sensitivity_risk_tier"] = "moderate"
			value["assessment_decision"] = "capture-sanitized"
			value["assessment_reason"] = "valuable_after_abstraction"
		},
	} {
		t.Run(name, func(t *testing.T) {
			tampered := cloneLearningMap(entry)
			mutate(tampered)
			if projection := learningAssessmentProjection(tampered); projection != nil {
				t.Fatalf("tampered assessment projected as canonical: %#v", projection)
			}
		})
	}
}

func TestLearningSnapshotFingerprintCrossRuntimeGolden(t *testing.T) {
	suggestions := []learningSuggestion{{
		learningType: "tooling_trap", recurrenceKey: "sp-plan.runtime-boundary", signalStrength: "medium",
		summary: "Verify the runtime boundary first.", evidence: "The runner mismatch caused the failure.",
	}}
	got, err := learningSnapshotFingerprint("sp-plan", "specs/demo/workflow-state.md", suggestions, builtinLearningPolicy())
	if err != nil {
		t.Fatal(err)
	}
	const want = "47ba691a336c90c16cc5dc83101eea72bc29152ede042211b44158777200644e"
	if got != want {
		t.Fatalf("fingerprint=%s want=%s", got, want)
	}
}

func TestLearningPolicyDigestCrossRuntimeGolden(t *testing.T) {
	policy := learningPolicyFromConfig(runtimeconfig.ProjectLearningConfig{
		DeferredReviewDays: 14,
		Detectors: runtimeconfig.LearningDetectorsConfig{
			SecretPrefixes: []string{"Acme_"}, SensitiveKeyNames: []string{"customer_secret"},
			BusinessIDPrefixes: []string{"CUST-"}, SensitiveTerms: []string{"Project Zephyr"},
		},
	})
	const want = "bca349b678b400f54197abc387a0b0441ab3087fc7fb75c63c936753f4da98d1"
	if got := policy.digest(); got != want {
		t.Fatalf("policy digest=%s want=%s", got, want)
	}
}

func TestLearningPolicyDetectorOrderIsCanonicalAndOverlapSafe(t *testing.T) {
	left := learningPolicyFromConfig(runtimeconfig.ProjectLearningConfig{Detectors: runtimeconfig.LearningDetectorsConfig{
		SensitiveTerms: []string{"Project", "Project Zephyr"}, SecretPrefixes: []string{"acme_", "acme_live_"},
	}})
	right := learningPolicyFromConfig(runtimeconfig.ProjectLearningConfig{Detectors: runtimeconfig.LearningDetectorsConfig{
		SensitiveTerms: []string{"Project Zephyr", "Project"}, SecretPrefixes: []string{"acme_live_", "acme_"},
	}})
	if left.digest() != right.digest() {
		t.Fatalf("equivalent detector sets produced different digests: %s != %s", left.digest(), right.digest())
	}
	input := "Project Zephyr uses acme_live_ABC123 only in the runner."
	leftResult := redactLearningTextWithPolicy(input, left)
	rightResult := redactLearningTextWithPolicy(input, right)
	if leftResult.text != rightResult.text || strings.Contains(leftResult.text, "Zephyr") || strings.Contains(leftResult.text, "ABC123") {
		t.Fatalf("order-dependent or partial overlap redaction: left=%q right=%q", leftResult.text, rightResult.text)
	}
}

func TestLearningCaptureAutoDryRunDoesNotCreateRuntimeState(t *testing.T) {
	root := t.TempDir()
	workspace := filepath.Join(root, ".planning", "quick", "260804-001-dry-run")
	mustMkdirLearningTest(t, workspace)
	mustWriteLearningTest(t, filepath.Join(workspace, "STATUS.md"), `---
id: "260804-001"
status: "blocked"
---

## Execution
execution_fallback: native worker runtime unavailable
blocker_reason: runtime unavailable
recovery_action: retry after runtime comes back
retry_attempts: 1
`)

	dryRun := runLearningEnvelopeTest(t, []string{"capture-auto", "--project-root", root, "--command", "quick", "--workspace", ".planning/quick/260804-001-dry-run", "--dry-run", "--format", "json"})
	if dryRun.Status != "ok" || dryRun.Data["status"] != "dry-run" || dryRun.Data["dry_run"] != true {
		t.Fatalf("unexpected dry-run payload: %#v", dryRun)
	}
	assessed := dryRun.Data["assessed"].([]any)
	if len(assessed) == 0 || assessed[0].(map[string]any)["assessment"] == nil {
		t.Fatalf("dry-run did not return sanitized assessment: %#v", dryRun.Data)
	}
	for _, path := range []string{
		filepath.Join(root, ".planning", "learnings", "candidates.md"),
		filepath.Join(root, ".planning", "learnings", "auto-capture.json"),
		filepath.Join(root, ".planning", "learnings", "review-state.json"),
		filepath.Join(root, ".planning", "learnings", "metrics.json"),
		filepath.Join(root, ".specify", "memory", "learnings", "INDEX.md"),
	} {
		if _, err := os.Stat(path); !os.IsNotExist(err) {
			t.Fatalf("dry-run created %s or returned unexpected stat error: %v", path, err)
		}
	}
}

func TestLearningCaptureAutoDryRunPreservesExistingRuntimeBytes(t *testing.T) {
	root := t.TempDir()
	workspace := filepath.Join(root, ".planning", "quick", "260804-002-dry-run-existing")
	mustMkdirLearningTest(t, workspace)
	statusPath := filepath.Join(workspace, "STATUS.md")
	writeStatus := func(action string) {
		mustWriteLearningTest(t, statusPath, `---
id: "260804-002"
status: "blocked"
---

## Execution
execution_fallback: native worker runtime unavailable
blocker_reason: runtime unavailable during validation
recovery_action: `+action+`
retry_attempts: 2
`)
	}
	writeStatus("retry after restoring the runtime")
	seed := runLearningEnvelopeTest(t, []string{"capture-auto", "--project-root", root, "--command", "quick", "--workspace", ".planning/quick/260804-002-dry-run-existing", "--format", "json"})
	if seed.Status != "ok" {
		t.Fatalf("seed auto-capture failed: %#v", seed)
	}
	reviewState := filepath.Join(root, ".planning", "learnings", "review-state.json")
	mustWriteLearningTest(t, reviewState, `{"schema_version":1,"items":[]}`)
	writeStatus("restart the runtime and rerun scoped validation")
	paths := []string{
		filepath.Join(root, ".planning", "learnings", "candidates.md"),
		filepath.Join(root, ".planning", "learnings", "auto-capture.json"),
		reviewState,
		filepath.Join(root, ".planning", "learnings", "metrics.json"),
		filepath.Join(root, ".specify", "memory", "learnings", "INDEX.md"),
	}
	before := map[string][]byte{}
	for _, path := range paths {
		raw, err := os.ReadFile(path)
		if err != nil {
			t.Fatal(err)
		}
		before[path] = raw
	}
	dryRun := runLearningEnvelopeTest(t, []string{"capture-auto", "--project-root", root, "--command", "quick", "--workspace", ".planning/quick/260804-002-dry-run-existing", "--dry-run", "--format", "json"})
	if dryRun.Status != "ok" || dryRun.Data["status"] != "dry-run" {
		t.Fatalf("dry-run failed: %#v", dryRun)
	}
	for _, path := range paths {
		after, err := os.ReadFile(path)
		if err != nil {
			t.Fatal(err)
		}
		if !bytes.Equal(before[path], after) {
			t.Fatalf("dry-run mutated %s\nbefore=%s\nafter=%s", path, before[path], after)
		}
	}
}

func TestLearningInvalidPolicyReadFallbackAndWriteFailClosedWithoutRawLeak(t *testing.T) {
	root := t.TempDir()
	mustMkdirLearningTest(t, filepath.Join(root, ".specify"))
	rawSecret := "private-detector-value"
	mustWriteLearningTest(t, filepath.Join(root, ".specify", "config.json"), `{"project_learning":{"detectors":{"secret_prefixes":["`+rawSecret+`"],"regexes":[".*"]}}}`)

	start := runLearningEnvelopeTest(t, []string{"start", "--project-root", root, "--command", "plan", "--format", "json"})
	if start.Status != "ok" || !learningAnySliceContains(start.Data["warnings"], learningPolicyFallbackWarning) {
		t.Fatalf("read did not use warned built-in fallback: %#v", start)
	}
	capture := runLearningEnvelopeTest(t, []string{"capture", "--project-root", root, "--command", "debug", "--type", "tooling_trap", "--summary", "safe summary", "--evidence", "safe evidence", "--format", "json"})
	if capture.Status != "blocked" {
		t.Fatalf("invalid policy write should fail closed: %#v", capture)
	}
	assertLearningJSONOmits(t, capture, []string{rawSecret, ".*"})
	dryRun := runLearningEnvelopeTest(t, []string{"capture-auto", "--project-root", root, "--command", "quick", "--workspace", ".planning/quick/missing", "--dry-run", "--format", "json"})
	if dryRun.Status != "blocked" {
		t.Fatalf("invalid policy dry-run should fail closed before source inspection: %#v", dryRun)
	}
	assertLearningJSONOmits(t, dryRun, []string{rawSecret, ".*"})
	if _, err := os.Stat(filepath.Join(root, ".planning", "learnings")); !os.IsNotExist(err) {
		t.Fatalf("failed-closed capture created runtime state: %v", err)
	}
}

func TestLearningReviewStatusAgingAndDurableCaptureClear(t *testing.T) {
	root := t.TempDir()
	mustMkdirLearningTest(t, filepath.Join(root, ".specify"))
	deferred := runLearningEnvelopeTest(t, []string{"review", "--project-root", root, "--command", "debug", "--decision", "deferred", "--rationale", "Need a reusable recovery instruction", "--recurrence-key", "debug.review-aging", "--format", "json"})
	if deferred.Status != "ok" || deferred.Data["status"] != "deferred" {
		t.Fatalf("failed to persist deferred review: %#v", deferred)
	}
	statePath := filepath.Join(root, ".planning", "learnings", "review-state.json")
	var state map[string]any
	raw, err := os.ReadFile(statePath)
	if err != nil {
		t.Fatal(err)
	}
	if err := json.Unmarshal(raw, &state); err != nil {
		t.Fatal(err)
	}
	items := state["items"].([]any)
	items[0].(map[string]any)["review_after"] = time.Now().UTC().Add(-24 * time.Hour).Format(time.RFC3339)
	raw, _ = json.Marshal(state)
	mustWriteLearningTest(t, statePath, string(raw))
	agedBefore, err := os.ReadFile(statePath)
	if err != nil {
		t.Fatal(err)
	}

	status := runLearningEnvelopeTest(t, []string{"status", "--project-root", root, "--command", "debug", "--format", "json"})
	if status.Status != "ok" || status.Data["read_only"] != true || intFromAny(status.Data["overdue"]) != 1 {
		t.Fatalf("unexpected overdue status: %#v", status)
	}
	if _, exists := status.Data["items"]; exists {
		t.Fatalf("aggregate status exposed an items field: %#v", status.Data)
	}
	agedAfter, err := os.ReadFile(statePath)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(agedBefore, agedAfter) {
		t.Fatalf("status mutated durable review state\nbefore=%s\nafter=%s", agedBefore, agedAfter)
	}
	none := runLearningEnvelopeTest(t, []string{"review", "--project-root", root, "--command", "debug", "--decision", "none", "--format", "json"})
	if none.Status != "blocked" {
		t.Fatalf("none review should not bypass pending deferred state: %#v", none)
	}
	stillPending := runLearningEnvelopeTest(t, []string{"status", "--project-root", root, "--command", "debug", "--format", "json"})
	if intFromAny(stillPending.Data["pending"]) != 1 {
		t.Fatalf("none decision cleared durable deferred review: %#v", stillPending)
	}
	unmatched := runLearningEnvelopeTest(t, []string{"review", "--project-root", root, "--command", "debug", "--decision", "captured", "--recurrence-key", "debug.review-aging", "--format", "json"})
	if unmatched.Status != "blocked" {
		t.Fatalf("captured review without durable learning should block: %#v", unmatched)
	}
	capture := runLearningEnvelopeTest(t, []string{"capture", "--project-root", root, "--command", "debug", "--type", "recovery_path", "--summary", "Keep the scoped recovery sequence", "--evidence", "The scoped sequence restored the runtime", "--action", "Run scoped validation after recovery", "--recurrence-key", "debug.review-aging", "--format", "json"})
	if capture.Status != "ok" {
		t.Fatalf("matching durable capture failed: %#v", capture)
	}
	cleared := runLearningEnvelopeTest(t, []string{"status", "--project-root", root, "--command", "debug", "--format", "json"})
	if intFromAny(cleared.Data["pending"]) != 0 {
		t.Fatalf("matching durable capture did not clear deferred review: %#v", cleared)
	}
}

func TestLearningReviewRequiresFreshExactCaptureAndPreservesOtherPending(t *testing.T) {
	root := t.TempDir()
	mustMkdirLearningTest(t, filepath.Join(root, ".specify"))
	oldCapture := runLearningEnvelopeTest(t, []string{"capture", "--project-root", root, "--command", "debug", "--type", "recovery_path", "--summary", "Preserve recovery A", "--evidence", "Recovery A restored the exact runtime boundary", "--action", "Run recovery A before validation", "--recurrence-key", "debug.review-a", "--format", "json"})
	if oldCapture.Status != "ok" {
		t.Fatalf("seed capture failed: %#v", oldCapture)
	}
	for _, key := range []string{"debug.review-a", "debug.review-b"} {
		deferred := runLearningEnvelopeTest(t, []string{"review", "--project-root", root, "--command", "debug", "--decision", "deferred", "--rationale", "Need a fresh exact durable capture", "--recurrence-key", key, "--format", "json"})
		if deferred.Status != "ok" {
			t.Fatalf("defer %s failed: %#v", key, deferred)
		}
	}
	reviewStatePath := filepath.Join(root, ".planning", "learnings", "review-state.json")
	reviewRaw, err := os.ReadFile(reviewStatePath)
	if err != nil {
		t.Fatal(err)
	}
	var reviewState map[string]any
	if err := json.Unmarshal(reviewRaw, &reviewState); err != nil {
		t.Fatal(err)
	}
	for _, rawItem := range reviewState["items"].([]any) {
		item := rawItem.(map[string]any)
		if item["recurrence_key"] == "debug.review-a" {
			item["created_at"] = time.Now().UTC().Add(2 * time.Second).Truncate(time.Second).Format(time.RFC3339)
		}
	}
	reviewRaw, _ = json.Marshal(reviewState)
	mustWriteLearningTest(t, reviewStatePath, string(reviewRaw))
	staleClaim := runLearningEnvelopeTest(t, []string{"review", "--project-root", root, "--command", "debug", "--decision", "captured", "--recurrence-key", "debug.review-a", "--format", "json"})
	if staleClaim.Status != "blocked" {
		t.Fatalf("capture predating defer satisfied review: %#v", staleClaim)
	}
	freshB := runLearningEnvelopeTest(t, []string{"capture", "--project-root", root, "--command", "debug", "--type", "recovery_path", "--summary", "Preserve recovery B", "--evidence", "Recovery B restored its exact runtime boundary", "--action", "Run recovery B before validation", "--recurrence-key", "debug.review-b", "--format", "json"})
	if freshB.Status != "ok" {
		t.Fatalf("fresh B capture failed: %#v", freshB)
	}
	status := runLearningEnvelopeTest(t, []string{"status", "--project-root", root, "--command", "debug", "--format", "json"})
	if intFromAny(status.Data["pending"]) != 1 {
		t.Fatalf("capture B cleared unrelated pending A: %#v", status)
	}
	unspecificClaim := runLearningEnvelopeTest(t, []string{"review", "--project-root", root, "--command", "debug", "--decision", "captured", "--format", "json"})
	if unspecificClaim.Status != "blocked" {
		t.Fatalf("unspecific captured claim bypassed pending A: %#v", unspecificClaim)
	}
}

func TestLearningUnknownSensitiveCommandIsAbstractedAndLabeled(t *testing.T) {
	root := t.TempDir()
	mustMkdirLearningTest(t, filepath.Join(root, ".specify"))
	mustWriteLearningTest(t, filepath.Join(root, ".specify", "config.json"), `{"project_learning":{"detectors":{"sensitive_terms":["zephyr"]}}}`)
	capture := runLearningEnvelopeTest(t, []string{
		"capture", "--project-root", root, "--command", "zephyr", "--type", "workflow_gap",
		"--summary", "Preserve the reusable route boundary", "--evidence", "The route boundary failed during the handoff",
		"--action", "Validate the reusable route before handoff", "--recurrence-key", "workflow.route-boundary", "--format", "json",
	})
	if capture.Status != "ok" {
		t.Fatalf("sensitive unknown command capture failed: %#v", capture)
	}
	entry := mapStringAny(capture.Data["entry"])
	if entry["source_command"] != "sp-other" || entry["assessment_decision"] != "capture-sanitized" || !learningContainsString(anyStringSlice(entry["redaction_labels"]), "organization_sensitive") {
		t.Fatalf("sensitive command was not abstracted and labeled: %#v", entry)
	}
	repeat := runLearningEnvelopeTest(t, []string{
		"capture", "--project-root", root, "--command", "zephyr", "--type", "workflow_gap",
		"--summary", "Preserve the reusable route boundary", "--evidence", "The route boundary failed during the handoff",
		"--action", "Validate the reusable route before handoff", "--recurrence-key", "workflow.route-boundary", "--format", "json",
	})
	if repeat.Status != "ok" {
		t.Fatalf("repeat sensitive command capture failed: %#v", repeat)
	}
	start := runLearningEnvelopeTest(t, []string{"start", "--project-root", root, "--command", "zephyr", "--format", "json"})
	if len(anyMapSlice(start.Data["items"])) == 0 || len(anyMapSlice(start.Data["promotion_ready"])) == 0 {
		t.Fatalf("policy-safe start filter lost the sensitive unknown command candidate: %#v", start)
	}
	assertLearningJSONOmits(t, start, []string{"zephyr", "sp-zephyr"})
	for _, path := range []string{
		filepath.Join(root, ".planning", "learnings", "candidates.md"),
		filepath.Join(root, ".planning", "learnings", "metrics.json"),
		filepath.Join(root, ".specify", "memory", "learnings", "INDEX.md"),
	} {
		raw, err := os.ReadFile(path)
		if err != nil {
			t.Fatal(err)
		}
		if strings.Contains(strings.ToLower(string(raw)), "zephyr") {
			t.Fatalf("sensitive command leaked to %s: %s", path, raw)
		}
	}
}

func TestLearningPolicyAddedAfterStorageScrubsOnReadAndNextWrite(t *testing.T) {
	root := t.TempDir()
	mustMkdirLearningTest(t, filepath.Join(root, ".specify"))
	const rawTerm = "project-zephyr"
	seed := runLearningEnvelopeTest(t, []string{
		"capture", "--project-root", root, "--command", "plan", "--type", "project_constraint",
		"--summary", "Preserve the project route boundary", "--evidence", "The route boundary is reused during planning",
		"--action", "Validate the project route before planning", "--recurrence-key", rawTerm + ".route", "--format", "json",
	})
	if seed.Status != "ok" {
		t.Fatalf("seed capture failed: %#v", seed)
	}
	mustWriteLearningTest(t, filepath.Join(root, ".specify", "config.json"), `{"project_learning":{"detectors":{"sensitive_terms":["Project Zephyr"]}}}`)
	list := runLearningEnvelopeTest(t, []string{"list", "--project-root", root, "--command", "plan", "--all", "--format", "json"})
	assertLearningJSONOmits(t, list, []string{rawTerm, "Project Zephyr"})
	promote := runLearningEnvelopeTest(t, []string{"promote", "--project-root", root, "--recurrence-key", rawTerm + ".route", "--target", "learning", "--format", "json"})
	if promote.Status != "ok" {
		t.Fatalf("policy-scrubbed promotion failed: %#v", promote)
	}
	assertLearningJSONOmits(t, promote, []string{rawTerm, "Project Zephyr"})
	for _, path := range []string{
		filepath.Join(root, ".planning", "learnings", "candidates.md"),
		filepath.Join(root, ".planning", "learnings", "review.md"),
		filepath.Join(root, ".specify", "memory", "learnings", "INDEX.md"),
		filepath.Join(root, ".specify", "memory", "learnings", "confirmed.md"),
	} {
		raw, err := os.ReadFile(path)
		if err != nil {
			t.Fatal(err)
		}
		if strings.Contains(strings.ToLower(string(raw)), rawTerm) {
			t.Fatalf("new policy did not scrub %s on write: %s", path, raw)
		}
	}
}

func TestLearningReviewNoneWithoutPendingNeedsNoRationale(t *testing.T) {
	root := t.TempDir()
	mustMkdirLearningTest(t, filepath.Join(root, ".specify"))
	review := runLearningEnvelopeTest(t, []string{"review", "--project-root", root, "--command", "plan", "--decision", "none", "--format", "json"})
	if review.Status != "ok" || review.Data["status"] != "none" {
		t.Fatalf("none without pending should succeed without rationale: %#v", review)
	}
}

func TestLearningReviewFirstWriteMigratesLegacyWithoutDuplicateOrResurrection(t *testing.T) {
	root := t.TempDir()
	mustMkdirLearningTest(t, filepath.Join(root, ".specify"))
	legacyPath := filepath.Join(root, ".planning", "learnings", "signal-state.json")
	mustWriteLearningTest(t, legacyPath, `{
  "debug": {
    "command": "sp-debug",
    "pain_score": 6,
    "factors": {"retry_attempts": 2},
    "observed_at": "2026-08-01T00:00:00Z",
    "learning_review": {
      "decision": "deferred",
      "rationale": "Preserve the reusable recovery boundary",
      "deferred_at": "2026-08-01T00:00:00Z"
    }
  }
}`)
	before := runLearningEnvelopeTest(t, []string{"status", "--project-root", root, "--command", "debug", "--format", "json"})
	if intFromAny(before.Data["pending"]) != 1 {
		t.Fatalf("legacy pending review was not projected: %#v", before)
	}
	deferred := runLearningEnvelopeTest(t, []string{"review", "--project-root", root, "--command", "debug", "--decision", "deferred", "--rationale", "Preserve the exact reusable recovery boundary", "--recurrence-key", "debug.legacy-migration", "--format", "json"})
	if deferred.Status != "ok" {
		t.Fatalf("canonical migration write failed: %#v", deferred)
	}
	statePath := filepath.Join(root, ".planning", "learnings", "review-state.json")
	stateRaw, err := os.ReadFile(statePath)
	if err != nil {
		t.Fatal(err)
	}
	var state map[string]any
	if err := json.Unmarshal(stateRaw, &state); err != nil {
		t.Fatal(err)
	}
	if items := anyMapSlice(state["items"]); len(items) != 1 || stringFromAny(items[0]["created_at"]) != "2026-08-01T00:00:00Z" {
		t.Fatalf("legacy age was not preserved or review duplicated: %s", stateRaw)
	}
	legacyRaw, err := os.ReadFile(legacyPath)
	if err != nil {
		t.Fatal(err)
	}
	var legacy map[string]any
	if err := json.Unmarshal(legacyRaw, &legacy); err != nil {
		t.Fatal(err)
	}
	legacyDebug := mapStringAny(legacy["debug"])
	if _, exists := legacyDebug["learning_review"]; exists || intFromAny(mapStringAny(legacyDebug["factors"])["retry_attempts"]) != 2 {
		t.Fatalf("legacy review was not removed safely or friction factors were lost: %s", legacyRaw)
	}
	after := runLearningEnvelopeTest(t, []string{"status", "--project-root", root, "--command", "debug", "--format", "json"})
	if intFromAny(after.Data["pending"]) != 1 {
		t.Fatalf("legacy review resurrected after migration: %#v", after)
	}
}

func TestLearningMetricsAreAggregateOnlyAndReadsDoNotMutate(t *testing.T) {
	root := t.TempDir()
	mustMkdirLearningTest(t, filepath.Join(root, ".specify"))
	rawSecret := "ghp_1234567890abcdef"
	capture := runLearningEnvelopeTest(t, []string{"capture", "--project-root", root, "--command", "debug", "--type", "tooling_trap", "--summary", "Do not persist token=" + rawSecret + " during retry", "--evidence", "The retry log exposed the token", "--action", "Redact the credential before retrying", "--recurrence-key", "debug.metrics-redaction", "--format", "json"})
	if capture.Status != "ok" {
		t.Fatalf("capture failed: %#v", capture)
	}
	metricsPath := filepath.Join(root, ".planning", "learnings", "metrics.json")
	before, err := os.ReadFile(metricsPath)
	if err != nil {
		t.Fatal(err)
	}
	if strings.Contains(string(before), rawSecret) || strings.Contains(string(before), "metrics-redaction") {
		t.Fatalf("aggregate metrics leaked raw content or refs: %s", before)
	}
	metrics := runLearningEnvelopeTest(t, []string{"metrics", "--project-root", root, "--command", "debug", "--format", "json"})
	metricTotals := mapStringAny(mapStringAny(metrics.Data["metrics"])["totals"])
	if metrics.Status != "ok" || metrics.Data["read_only"] != true || intFromAny(metricTotals["assessed"]) < 1 {
		t.Fatalf("unexpected metrics response: %#v", metrics)
	}
	_ = runLearningEnvelopeTest(t, []string{"start", "--project-root", root, "--command", "debug", "--format", "json"})
	_ = runLearningEnvelopeTest(t, []string{"list", "--project-root", root, "--command", "debug", "--format", "json"})
	_ = runLearningEnvelopeTest(t, []string{"show", "--project-root", root, "--ref", "debug.metrics-redaction", "--format", "json"})
	after, err := os.ReadFile(metricsPath)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(before, after) {
		t.Fatalf("read-only learning commands mutated metrics\nbefore=%s\nafter=%s", before, after)
	}
}

func TestLearningMetricsUseFixedZeroShapeAndCapturedDenominator(t *testing.T) {
	root := t.TempDir()
	mustMkdirLearningTest(t, filepath.Join(root, ".specify"))
	capture := runLearningEnvelopeTest(t, []string{
		"capture", "--project-root", root, "--command", "plan", "--type", "project_constraint",
		"--summary", "Preserve the runtime boundary", "--evidence", "The boundary is reusable across planning runs",
		"--action", "Validate the runtime boundary before planning", "--recurrence-key", "plan.metrics-shape", "--confirm", "--format", "json",
	})
	if capture.Status != "ok" {
		t.Fatalf("confirmed capture failed: %#v", capture)
	}
	metrics := runLearningEnvelopeTest(t, []string{"metrics", "--project-root", root, "--command", "plan", "--format", "json"})
	bucket := mapStringAny(metrics.Data["metrics"])
	expectedGroups := map[string][]string{
		"totals": learningMetricTotals, "decisions": learningMetricDecisions, "value_tiers": learningMetricValueTiers,
		"risk_tiers": learningMetricRiskTiers, "reason_codes": learningMetricReasonCodes, "redaction_labels": learningMetricLabels,
	}
	for group, expectedKeys := range expectedGroups {
		values := mapStringAny(bucket[group])
		for _, key := range expectedKeys {
			if _, exists := values[key]; !exists {
				t.Fatalf("metrics group %s omitted fixed zero key %s: %#v", group, key, values)
			}
		}
	}
	totals := mapStringAny(bucket["totals"])
	if intFromAny(totals["captured"]) != 1 || intFromAny(totals["confirmed"]) != 1 {
		t.Fatalf("unexpected confirmed capture totals: %#v", totals)
	}
	rate, _ := mapStringAny(metrics.Data["derived"])["confirmation_rate"].(float64)
	if rate != 1 {
		t.Fatalf("confirmation_rate=%v want 1 using confirmed/captured", rate)
	}
}

func TestLearningStartCandidateQuotaDiversifiesAvailableFamilies(t *testing.T) {
	cards := []map[string]any{}
	for i := 0; i < 15; i++ {
		cards = append(cards, map[string]any{"ref": "stable." + strconv.Itoa(i), "type": "workflow_gap", "source_layer": "confirmed-learning", "occurrences": float64(20 - i), "signal": "high"})
	}
	for i := 0; i < 8; i++ {
		cards = append(cards, map[string]any{"ref": "debug.same." + strconv.Itoa(i), "type": "tooling_trap", "source_layer": "candidate", "_source_command": "sp-debug", "_recurrence_family": "debug.same", "occurrences": float64(10 - i), "signal": "high"})
	}
	cards = append(cards,
		map[string]any{"ref": "quick.other.1", "type": "workflow_gap", "source_layer": "candidate", "_source_command": "sp-quick", "_recurrence_family": "quick.other", "occurrences": float64(1), "signal": "medium"},
		map[string]any{"ref": "plan.third.1", "type": "recovery_path", "source_layer": "candidate", "_source_command": "sp-plan", "_recurrence_family": "plan.third", "occurrences": float64(1), "signal": "medium"},
	)
	selected := learningStartQuotaCards(cards, 15, 5)
	if len(selected) != 20 {
		t.Fatalf("selected %d cards, want 20", len(selected))
	}
	families := map[string]bool{}
	for _, card := range selected {
		if !learningCardStable(card) {
			families[stringFromAny(card["_recurrence_family"])] = true
		}
	}
	if len(families) < 3 {
		keys := make([]string, 0, len(families))
		for family := range families {
			keys = append(keys, family)
		}
		sort.Strings(keys)
		t.Fatalf("candidate selection lacked available diversity: %v selected=%#v", keys, selected)
	}
}

func runLearningEnvelopeTest(t *testing.T, args []string) Envelope {
	t.Helper()
	var stdout bytes.Buffer
	code := runLearning(args, &stdout)
	var env Envelope
	if err := json.Unmarshal(stdout.Bytes(), &env); err != nil {
		t.Fatalf("decode learning envelope code=%d err=%v stdout=%s", code, err, stdout.String())
	}
	if code != ExitCodeForStatus(env.Status) {
		t.Fatalf("exit code %d does not match status %s", code, env.Status)
	}
	return env
}

func assertLearningJSONOmits(t *testing.T, value any, forbidden []string) {
	t.Helper()
	raw, err := json.Marshal(value)
	if err != nil {
		t.Fatalf("marshal: %v", err)
	}
	for _, item := range forbidden {
		if item != "" && bytes.Contains(raw, []byte(item)) {
			t.Fatalf("payload leaked %q in %s", item, string(raw))
		}
	}
}

func assertLearningFileOmits(t *testing.T, path string, forbidden []string) {
	t.Helper()
	raw, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read %s: %v", path, err)
	}
	for _, item := range forbidden {
		if item != "" && bytes.Contains(raw, []byte(item)) {
			t.Fatalf("%s leaked %q in %s", path, item, string(raw))
		}
	}
}

func assertStringSetLearningTest(t *testing.T, got, want []string) {
	t.Helper()
	if len(got) != len(want) {
		t.Fatalf("set length got=%v want=%v", got, want)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Fatalf("set got=%v want=%v", got, want)
		}
	}
}

func learningAnySliceContains(value any, expected string) bool {
	for _, item := range value.([]any) {
		if stringFromAny(item) == expected {
			return true
		}
	}
	return false
}

func mustMkdirLearningTest(t *testing.T, path string) {
	t.Helper()
	if err := os.MkdirAll(path, 0o755); err != nil {
		t.Fatalf("mkdir %s: %v", path, err)
	}
}

func mustWriteLearningTest(t *testing.T, path, content string) {
	t.Helper()
	mustMkdirLearningTest(t, filepath.Dir(path))
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatalf("write %s: %v", path, err)
	}
}
