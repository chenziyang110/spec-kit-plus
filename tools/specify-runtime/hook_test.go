package main

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

func TestHookArtifactValidationRequiresCommandArtifacts(t *testing.T) {
	root := t.TempDir()
	feature := filepath.Join(root, ".specify", "features", "001-demo")
	if err := os.MkdirAll(feature, 0o755); err != nil {
		t.Fatal(err)
	}
	for _, name := range []string{"spec.md", "spec-contract.json"} {
		if err := os.WriteFile(filepath.Join(feature, name), []byte("{}\n"), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	mustWriteHookText(t, filepath.Join(feature, "workflow-state.md"), "# Workflow State\n")
	env := validateHookArtifacts([]string{
		"--command", "specify",
		"--feature-dir", ".specify/features/001-demo",
		"--project-root", root,
	})
	if env.Status != "ok" {
		t.Fatalf("hook status = %q, blockers=%#v", env.Status, env.Blockers)
	}
}

func TestHookStateValidationAutofixRepairsMissingSections(t *testing.T) {
	root := t.TempDir()
	feature := filepath.Join(root, ".specify", "features", "002-state")
	if err := os.MkdirAll(feature, 0o755); err != nil {
		t.Fatal(err)
	}
	statePath := filepath.Join(feature, "workflow-state.md")
	if err := os.WriteFile(statePath, []byte("# Workflow State\n\n## Current Command\n\n- active_command: `sp-specify`\n- status: `active`\n\n## Phase Mode\n\n- phase_mode: `planning-only`\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	env := validateHookState([]string{
		"--command", "specify",
		"--feature-dir", filepath.Join(root, ".specify", "features", "002-state"),
		"--project-root", root,
		"--autofix",
	})
	if env.Status != "repaired" {
		t.Fatalf("state status = %q blockers=%#v", env.Status, env.Blockers)
	}
	repaired, err := os.ReadFile(statePath)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Contains(repaired, []byte("## Allowed Artifact Writes")) || !bytes.Contains(repaired, []byte("## Next Command")) {
		t.Fatalf("autofix did not append required sections:\n%s", string(repaired))
	}
}

func TestHookStateValidationBlocksWrongCommand(t *testing.T) {
	root := t.TempDir()
	feature := filepath.Join(root, ".specify", "features", "003-state")
	if err := os.MkdirAll(feature, 0o755); err != nil {
		t.Fatal(err)
	}
	mustWriteHookText(t, filepath.Join(feature, "workflow-state.md"), "# Workflow State\n\n## Current Command\n\n- active_command: `sp-plan`\n\n## Phase Mode\n\n- phase_mode: `design-only`\n\n## Allowed Artifact Writes\n\n- plan.md\n\n## Forbidden Actions\n\n- edit source code\n\n## Authoritative Files\n\n- plan.md\n\n## Next Command\n\n- `/sp.tasks`\n")
	env := validateHookState([]string{
		"--command", "specify",
		"--feature-dir", ".specify/features/003-state",
		"--project-root", root,
	})
	if env.Status != "blocked" {
		t.Fatalf("state status = %q, want blocked", env.Status)
	}
}

func TestHookArtifactValidationBlocksProjectEscape(t *testing.T) {
	env := validateHookArtifacts([]string{
		"--command", "specify",
		"--feature-dir", "../outside",
		"--project-root", t.TempDir(),
	})
	if env.Status != "blocked" {
		t.Fatalf("hook status = %q, want blocked", env.Status)
	}
}

func TestHookArtifactValidationBlocksInvalidTypesAndJSON(t *testing.T) {
	root := t.TempDir()
	feature := filepath.Join(root, ".specify", "features", "004-artifacts")
	if err := os.MkdirAll(filepath.Join(feature, "clarification", "evidence-index.json"), 0o755); err != nil {
		t.Fatal(err)
	}
	for _, name := range []string{"spec.md", "alignment.md", "context.md", "references.md", "workflow-state.md", "clarification/checkpoints.ndjson"} {
		mustWriteHookText(t, filepath.Join(feature, filepath.FromSlash(name)), "content\n")
	}
	if err := os.MkdirAll(filepath.Join(feature, "clarification", "handoffs"), 0o755); err != nil {
		t.Fatal(err)
	}
	env := validateHookArtifacts([]string{
		"--command", "clarify",
		"--feature-dir", ".specify/features/004-artifacts",
		"--project-root", root,
	})
	if env.Status != "blocked" {
		t.Fatalf("artifact status = %q, want blocked", env.Status)
	}
}

func TestHookCommitValidationGatesFinalizeAndExternalCheckpoint(t *testing.T) {
	root := t.TempDir()
	feature := filepath.Join(root, ".specify", "features", "005-commit")
	if err := os.MkdirAll(filepath.Join(feature, "implementation-review", "tasks"), 0o755); err != nil {
		t.Fatal(err)
	}
	mustWriteHookText(t, filepath.Join(feature, "implement-tracker.md"), "---\nstatus: executing\nnext_action: Continue implementation.\n---\n")
	finalize := validateHookCommit([]string{
		"--commit-message", "fix: checkpoint work",
		"--feature-dir", ".specify/features/005-commit",
		"--project-root", root,
	})
	if finalize.Status != "blocked" {
		t.Fatalf("finalize status = %q, want blocked", finalize.Status)
	}
	invalidMessage := validateHookCommit([]string{"--commit-message", "not conventional"})
	if invalidMessage.Status != "blocked" {
		t.Fatalf("invalid commit status = %q, want blocked", invalidMessage.Status)
	}

	mustWriteHookJSON(t, filepath.Join(feature, "implementation-review", "tasks", "T001.json"), map[string]any{
		"task_id": "T001",
		"status":  "blocked",
		"blockers": []any{map[string]any{
			"classification":              "external",
			"owner":                       "external-system",
			"evidence":                    []any{"CI is pending on protected branch"},
			"exact_next_action":           "Wait for CI result.",
			"approval_question":           nil,
			"unblock_criteria":            "CI passes.",
			"implementation_can_continue": false,
			"completion_impact":           "mandatory_for_completion",
		}},
	})
	checkpoint := validateHookCommit([]string{
		"--commit-message", "chore: record external evidence checkpoint",
		"--commit-intent", "external-evidence-checkpoint",
		"--feature-dir", ".specify/features/005-commit",
		"--project-root", root,
	})
	if checkpoint.Status != "ok" {
		t.Fatalf("checkpoint status = %q blockers=%#v", checkpoint.Status, checkpoint.Blockers)
	}
	if got := checkpoint.Data["workflow_finalized"]; got != false {
		t.Fatalf("workflow_finalized = %#v, want false", got)
	}
}

func TestRunHookExitCodesFollowEnvelopeStatus(t *testing.T) {
	var out bytes.Buffer
	code := runHook([]string{"validate-commit", "--commit-message", "not conventional"}, &out)
	if code != 10 {
		t.Fatalf("exit code = %d output=%s", code, out.String())
	}
	var env Envelope
	if err := json.Unmarshal(out.Bytes(), &env); err != nil {
		t.Fatalf("invalid envelope: %v", err)
	}
	if env.Status != "blocked" {
		t.Fatalf("status = %q, want blocked", env.Status)
	}
}

func mustWriteHookText(t *testing.T, path, content string) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
}

func mustWriteHookJSON(t *testing.T, path string, payload any) {
	t.Helper()
	raw, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	mustWriteHookText(t, path, string(raw)+"\n")
}
