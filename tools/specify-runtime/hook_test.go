package main

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestHookValidateStateAcceptsImplementCommandAliases(t *testing.T) {
	root := t.TempDir()
	feature := filepath.Join(root, ".specify", "features", "001-impl-state")
	if err := os.MkdirAll(feature, 0o755); err != nil {
		t.Fatal(err)
	}
	mustWriteHookText(t, filepath.Join(feature, "workflow-state.md"), `# Workflow State

## Current Command

- active_command: `+"`sp-implement`"+`

## Phase Mode

- phase_mode: `+"`implementation-only`"+`

## Allowed Artifact Writes

- implementation-handoff.json

## Forbidden Actions

- push without authority

## Authoritative Files

- task-index.json

## Next Command

- `+"`/sp-review`"+`
`)
	for _, command := range []string{"implement", "sp-implement", "/sp-implement", "sp.implement"} {
		var stdout, stderr bytes.Buffer
		code := Run([]string{
			"hook", "validate-state",
			"--command", command,
			"--feature-dir", filepath.ToSlash(filepath.Join(".specify", "features", "001-impl-state")),
			"--project-root", root,
			"--format", "json",
		}, &stdout, &stderr, "test")
		if code != 0 {
			t.Fatalf("validate-state --command %q exit=%d stdout=%s", command, code, stdout.String())
		}
		payload := decodeJSONObject(t, stdout.Bytes())
		if payload["status"] != "ok" {
			t.Fatalf("validate-state --command %q = %#v", command, payload)
		}
	}
}

func TestHookValidateStateRejectsUnknownCommandWithoutSpSpAutofix(t *testing.T) {
	root := t.TempDir()
	feature := filepath.Join(root, ".specify", "features", "001-unknown")
	if err := os.MkdirAll(feature, 0o755); err != nil {
		t.Fatal(err)
	}
	mustWriteHookText(t, filepath.Join(feature, "workflow-state.md"), "# Workflow State\n")
	var stdout, stderr bytes.Buffer
	code := Run([]string{
		"hook", "validate-state",
		"--command", "not-a-workflow",
		"--feature-dir", filepath.ToSlash(filepath.Join(".specify", "features", "001-unknown")),
		"--project-root", root,
		"--format", "json",
	}, &stdout, &stderr, "test")
	if code == 0 {
		t.Fatalf("expected unsupported command failure")
	}
	payload := decodeJSONObject(t, stdout.Bytes())
	text, _ := json.Marshal(payload)
	if strings.Contains(string(text), "/sp.sp-") {
		t.Fatalf("autofix must not suggest /sp.sp-*: %s", text)
	}
}

func TestHookExtensionPlanFiltersConfigAndRendersNativeInvocation(t *testing.T) {
	root := t.TempDir()
	specifyDir := filepath.Join(root, ".specify")
	if err := os.MkdirAll(specifyDir, 0o755); err != nil {
		t.Fatal(err)
	}
	mustWriteHookText(t, filepath.Join(specifyDir, "init-options.json"), `{"ai":"codex","ai_skills":true}`+"\n")
	mustWriteHookText(t, filepath.Join(specifyDir, "extensions.yml"), `hooks:
  before_deep_research:
    - extension: required-ext
      command: sp.required.check
      enabled: true
      optional: false
      prompt: Run the required check.
    - extension: optional-ext
      command: sp.optional.check
      description: Optional evidence.
    - extension: disabled-ext
      command: sp.disabled.check
      enabled: false
    - extension: conditional-ext
      command: sp.conditional.check
      condition: config.enabled
`)

	var stdout, stderr bytes.Buffer
	code := Run([]string{
		"hook", "extension-plan",
		"--event", "before_deep_research",
		"--project-root", root,
		"--format", "json",
	}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("extension-plan exit code = %d; stdout=%s stderr=%s", code, stdout.String(), stderr.String())
	}
	payload := decodeJSONObject(t, stdout.Bytes())
	items, ok := payload["items"].([]any)
	if !ok || len(items) != 2 {
		t.Fatalf("extension-plan items = %#v, want two actionable hooks", payload["items"])
	}
	required := items[0].(map[string]any)
	if required["invocation"] != "$sp-required-check" || required["optional"] != false {
		t.Fatalf("required hook = %#v", required)
	}
	optional := items[1].(map[string]any)
	if optional["invocation"] != "$sp-optional-check" || optional["optional"] != true {
		t.Fatalf("optional hook = %#v", optional)
	}
	data := requireObject(t, payload, "data")
	if data["disabled_count"] != float64(1) || data["deferred_condition_count"] != float64(1) {
		t.Fatalf("extension-plan counts = %#v", data)
	}
}

func TestHookExtensionPlanKeepsMissingOrInvalidOptionalConfigOutOfAgentContext(t *testing.T) {
	root := t.TempDir()
	missing := planExtensionHooks([]string{"--event", "after_specify", "--project-root", root})
	if missing.Status != "ok" || missing.Data["config_status"] != "missing" || len(missing.Items) != 0 {
		t.Fatalf("missing extension plan = %#v", missing)
	}
	if err := os.MkdirAll(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	mustWriteHookText(t, filepath.Join(root, ".specify", "extensions.yml"), "hooks: [unterminated\n")
	invalid := planExtensionHooks([]string{"--event", "after_specify", "--project-root", root})
	if invalid.Status != "ok" || invalid.Data["config_status"] != "invalid" || len(invalid.Items) != 0 {
		t.Fatalf("invalid extension plan = %#v", invalid)
	}
}

func TestHookExtensionPlanRequiresCanonicalEventID(t *testing.T) {
	for _, args := range [][]string{{}, {"--event", "Before Specify"}} {
		env := planExtensionHooks(args)
		if env.Status != "usage-error" {
			t.Fatalf("extension plan %#v = %#v, want usage-error", args, env)
		}
	}
}

func TestHookArtifactValidationRequiresCommandArtifacts(t *testing.T) {
	root := t.TempDir()
	feature := filepath.Join(root, ".specify", "features", "001-demo")
	if err := os.MkdirAll(feature, 0o755); err != nil {
		t.Fatal(err)
	}
	for _, name := range []string{"spec.md", "spec-contract.json"} {
		content := "{}\n"
		if name == "spec.md" {
			content = "# Feature Specification\n\n## Requirements\n\n- FR-001: Hook validation.\n"
		}
		if err := os.WriteFile(filepath.Join(feature, name), []byte(content), 0o644); err != nil {
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

func TestHookArtifactValidationUsesSemanticValidatorsForSpecifyTasksReviewAndAccept(t *testing.T) {
	t.Run("specify", func(t *testing.T) {
		root := t.TempDir()
		feature := filepath.Join(root, ".specify", "features", "001-specify")
		if err := os.MkdirAll(feature, 0o755); err != nil {
			t.Fatal(err)
		}
		mustWriteHookText(t, filepath.Join(feature, "spec.md"), "# Feature Specification\n\n## Notes\n\n- Missing requirements.\n")
		mustWriteHookText(t, filepath.Join(feature, "spec-contract.json"), "{\"schema_version\":1,\"status\":\"ready\"}\n")
		mustWriteHookText(t, filepath.Join(feature, "workflow-state.md"), "# Workflow State\n")

		env := validateHookArtifacts([]string{
			"--command", "specify",
			"--feature-dir", ".specify/features/001-specify",
			"--project-root", root,
		})
		if env.Status != "blocked" {
			t.Fatalf("specify semantic validation = %#v, want blocked", env)
		}
	})

	t.Run("tasks", func(t *testing.T) {
		root := t.TempDir()
		feature := filepath.Join(root, ".specify", "features", "002-tasks")
		if err := os.MkdirAll(feature, 0o755); err != nil {
			t.Fatal(err)
		}
		mustWriteHookText(t, filepath.Join(feature, "tasks.md"), "# Tasks\n")
		mustWriteHookText(t, filepath.Join(feature, "workflow-state.md"), "# Workflow State\n")
		mustWriteHookText(t, filepath.Join(feature, "plan-contract.json"), "{\"acceptance_refs\":[\"FR-001\"]}\n")
		mustWriteHookText(t, filepath.Join(feature, "task-index.json"), "{\"acceptance_refs\":[\"FR-999\"],\"official_entrypoints\":[],\"system_review_scenarios\":[],\"review_obligations\":[],\"human_acceptance_obligations\":[],\"human_acceptance_scenarios\":[]}\n")

		env := validateHookArtifacts([]string{
			"--command", "tasks",
			"--feature-dir", ".specify/features/002-tasks",
			"--project-root", root,
		})
		if env.Status != "blocked" {
			t.Fatalf("tasks semantic validation = %#v, want blocked", env)
		}
	})

	t.Run("review", func(t *testing.T) {
		root := t.TempDir()
		feature := filepath.Join(root, ".specify", "features", "003-review")
		if err := os.MkdirAll(filepath.Join(feature, "review-evidence"), 0o755); err != nil {
			t.Fatal(err)
		}
		mustWriteHookText(t, filepath.Join(feature, "review-state.json"), "{\"version\":2,\"status\":\"approved\",\"source\":{\"implementation_handoff_sha256\":\"stale\",\"implementation_fingerprint\":\"stale\",\"workflow_revision\":2},\"final\":{\"verdict\":\"pass\",\"coverage_verdict\":\"pass\",\"repair_verdict\":\"pass\",\"integration_verdict\":\"pass\",\"all_packets_joined\":true},\"findings\":[]}\n")
		mustWriteHookText(t, filepath.Join(feature, "implementation-handoff.json"), "{\"source_revision\":2}\n")
		mustWriteHookText(t, filepath.Join(feature, "implementation-summary.md"), "# Summary\n")
		mustWriteHookText(t, filepath.Join(feature, "human-acceptance.json"), "{\"version\":2,\"status\":\"draft\",\"source\":{\"review_state_sha256\":\"stale\",\"implementation_handoff_sha256\":\"stale\"},\"overall\":{\"verdict\":\"pending\",\"human_decision\":\"review\"}}\n")
		mustWriteHookText(t, filepath.Join(feature, "workflow-state.md"), "# Workflow State\n")

		env := validateHookArtifacts([]string{
			"--command", "review",
			"--feature-dir", ".specify/features/003-review",
			"--project-root", root,
		})
		if env.Status != "blocked" {
			t.Fatalf("review semantic validation = %#v, want blocked", env)
		}
	})

	t.Run("accept", func(t *testing.T) {
		root := t.TempDir()
		feature := filepath.Join(root, ".specify", "features", "004-accept")
		if err := os.MkdirAll(feature, 0o755); err != nil {
			t.Fatal(err)
		}
		mustWriteHookText(t, filepath.Join(feature, "implementation-summary.md"), "# Summary\n")
		mustWriteHookText(t, filepath.Join(feature, "implementation-handoff.json"), "{\"source_revision\":4}\n")
		mustWriteHookText(t, filepath.Join(feature, "review-state.json"), "{\"version\":2,\"status\":\"approved\",\"source\":{\"implementation_handoff_sha256\":\"stale\",\"implementation_fingerprint\":\"stale\",\"workflow_revision\":4},\"final\":{\"verdict\":\"pass\",\"coverage_verdict\":\"pass\",\"repair_verdict\":\"pass\",\"integration_verdict\":\"pass\",\"all_packets_joined\":true},\"findings\":[]}\n")
		mustWriteHookText(t, filepath.Join(feature, "human-acceptance.json"), "{\"version\":2,\"status\":\"accepted\",\"source\":{\"review_state_sha256\":\"stale\",\"implementation_handoff_sha256\":\"stale\"},\"overall\":{\"verdict\":\"fail\",\"human_decision\":\"reject\"}}\n")
		mustWriteHookText(t, filepath.Join(feature, "workflow-state.md"), "# Workflow State\n")

		env := validateHookArtifacts([]string{
			"--command", "accept",
			"--feature-dir", ".specify/features/004-accept",
			"--project-root", root,
		})
		if env.Status != "blocked" {
			t.Fatalf("accept semantic validation = %#v, want blocked", env)
		}
	})
}

func TestHookArtifactValidationUsesPlanSemanticValidator(t *testing.T) {
	t.Run("blocked on invalid acceptance continuity", func(t *testing.T) {
		root := t.TempDir()
		feature := filepath.Join(root, ".specify", "features", "005-plan")
		if err := os.MkdirAll(feature, 0o755); err != nil {
			t.Fatal(err)
		}
		mustWriteHookText(t, filepath.Join(feature, "plan.md"), "# Plan\n")
		mustWriteHookText(t, filepath.Join(feature, "workflow-state.md"), "# Workflow State\n")
		mustWriteHookText(t, filepath.Join(feature, "spec-contract.json"), "{\"acceptance_criteria\":[\"AC-1\",\"AC-2\"]}\n")
		mustWriteHookText(t, filepath.Join(feature, "plan-contract.json"), "{\n  \"version\": 2,\n  \"status\": \"ready\",\n  \"source_contract\": \"spec-contract.json\",\n  \"source_revision\": 1,\n  \"acceptance_refs\": [\"spec-contract.json#/acceptance_criteria/1\"],\n  \"transition\": {\n    \"version\": 1,\n    \"status\": \"ready\",\n    \"source_ref\": \"plan-contract.json\",\n    \"semantic_delta\": [],\n    \"required_refs\": [],\n    \"blockers\": [],\n    \"next_action\": \"/sp.tasks\"\n  }\n}\n")

		env := validateHookArtifacts([]string{
			"--command", "plan",
			"--feature-dir", ".specify/features/005-plan",
			"--project-root", root,
		})
		if env.Status != "blocked" {
			t.Fatalf("plan semantic validation = %#v, want blocked", env)
		}
	})

	t.Run("ok on canonical ready contract", func(t *testing.T) {
		root := t.TempDir()
		feature := filepath.Join(root, ".specify", "features", "006-plan")
		if err := os.MkdirAll(feature, 0o755); err != nil {
			t.Fatal(err)
		}
		mustWriteHookText(t, filepath.Join(feature, "plan.md"), "# Plan\n")
		mustWriteHookText(t, filepath.Join(feature, "workflow-state.md"), "# Workflow State\n")
		mustWriteHookText(t, filepath.Join(feature, "spec-contract.json"), "{\"acceptance_criteria\":[\"AC-1\",\"AC-2\"]}\n")
		mustWriteHookText(t, filepath.Join(feature, "plan-contract.json"), "{\n  \"version\": 2,\n  \"status\": \"ready\",\n  \"source_contract\": \"spec-contract.json\",\n  \"source_revision\": 1,\n  \"acceptance_refs\": [\"spec-contract.json#/acceptance_criteria/0\", \"spec-contract.json#/acceptance_criteria/1\"],\n  \"transition\": {\n    \"version\": 1,\n    \"status\": \"ready\",\n    \"source_ref\": \"plan-contract.json\",\n    \"semantic_delta\": [],\n    \"required_refs\": [],\n    \"blockers\": [],\n    \"next_action\": \"/sp.tasks\"\n  }\n}\n")

		env := validateHookArtifacts([]string{
			"--command", "plan",
			"--feature-dir", ".specify/features/006-plan",
			"--project-root", root,
		})
		if env.Status != "ok" {
			t.Fatalf("plan semantic validation = %#v, want ok", env)
		}
	})
}

func TestHookArtifactValidationUsesAdditionalStageSemanticValidators(t *testing.T) {
	t.Run("clarify", func(t *testing.T) {
		root := t.TempDir()
		feature := filepath.Join(root, ".specify", "features", "007-clarify")
		if err := os.MkdirAll(filepath.Join(feature, "clarification", "handoffs"), 0o755); err != nil {
			t.Fatal(err)
		}
		for _, name := range []string{"spec.md", "alignment.md", "context.md", "references.md", "workflow-state.md"} {
			mustWriteHookText(t, filepath.Join(feature, name), "# Artifact\n")
		}
		mustWriteHookText(t, filepath.Join(feature, "clarification", "checkpoints.ndjson"), "{\"lane_id\":\"L1\"}\n")
		mustWriteHookText(t, filepath.Join(feature, "clarification", "evidence-index.json"), "{\"lanes\":{\"L1\":{\"status\":\"accepted\"}}}\n")

		env := validateHookArtifacts([]string{
			"--command", "clarify",
			"--feature-dir", ".specify/features/007-clarify",
			"--project-root", root,
		})
		if env.Status != "blocked" {
			t.Fatalf("clarify semantic validation = %#v, want blocked", env)
		}
	})

	t.Run("deep-research", func(t *testing.T) {
		root := t.TempDir()
		feature := filepath.Join(root, ".specify", "features", "008-research")
		if err := os.MkdirAll(feature, 0o755); err != nil {
			t.Fatal(err)
		}
		mustWriteHookText(t, filepath.Join(feature, "workflow-state.md"), "# Workflow State\n")
		mustWriteHookText(t, filepath.Join(feature, "deep-research.md"), "# Research\n\n## Planning Handoff\n\n- Missing status.\n")

		env := validateHookArtifacts([]string{
			"--command", "deep-research",
			"--feature-dir", ".specify/features/008-research",
			"--project-root", root,
		})
		if env.Status != "blocked" {
			t.Fatalf("deep-research semantic validation = %#v, want blocked", env)
		}
	})

	t.Run("analyze", func(t *testing.T) {
		root := t.TempDir()
		feature := filepath.Join(root, ".specify", "features", "009-analyze")
		if err := os.MkdirAll(feature, 0o755); err != nil {
			t.Fatal(err)
		}
		mustWriteHookText(t, filepath.Join(feature, "workflow-state.md"), "# Workflow State\n\n## Current Command\n\n- active_command: `sp-analyze`\n\n## Phase Mode\n\n- phase_mode: `analysis-only`\n\n## Analyze Gate\n\n- gate_status: `not-run`\n")

		env := validateHookArtifacts([]string{
			"--command", "analyze",
			"--feature-dir", ".specify/features/009-analyze",
			"--project-root", root,
		})
		if env.Status != "blocked" {
			t.Fatalf("analyze semantic validation = %#v, want blocked", env)
		}
	})

	t.Run("constitution", func(t *testing.T) {
		root := t.TempDir()
		memory := filepath.Join(root, ".specify", "memory")
		if err := os.MkdirAll(memory, 0o755); err != nil {
			t.Fatal(err)
		}
		mustWriteHookText(t, filepath.Join(memory, "constitution.md"), "# Demo Constitution\n\n## Core Principles\n")

		env := validateHookArtifacts([]string{
			"--command", "constitution",
			"--feature-dir", ".specify/memory",
			"--project-root", root,
		})
		if env.Status != "blocked" {
			t.Fatalf("constitution semantic validation = %#v, want blocked", env)
		}
	})

	t.Run("prd-scan", func(t *testing.T) {
		root := t.TempDir()
		runID := "260729-hook-prd"
		runDir := seedPRDRunFixture(t, root, runID, prdFixtureOptions{
			command:        "sp-prd-scan",
			status:         "ready-for-build",
			scanStatus:     "complete",
			buildStatus:    "pending",
			classification: "service",
			nextCommand:    "/sp.prd-build",
			freshness:      "fresh",
			latestRun:      runID,
		})
		rel, err := filepath.Rel(root, runDir)
		if err != nil {
			t.Fatal(err)
		}
		args := []string{
			"--command", "prd-scan",
			"--feature-dir", filepath.ToSlash(rel),
			"--project-root", root,
		}
		if env := validateHookArtifacts(args); env.Status != "ok" {
			t.Fatalf("prd-scan semantic validation = %#v, want ok", env)
		}

		statusPath := filepath.Join(root, ".specify", "prd", "status.json")
		statusRaw, err := os.ReadFile(statusPath)
		if err != nil {
			t.Fatal(err)
		}
		statusRaw = bytes.Replace(statusRaw, []byte(`"freshness": "fresh"`), []byte(`"freshness": "stale"`), 1)
		if err := os.WriteFile(statusPath, statusRaw, 0o644); err != nil {
			t.Fatal(err)
		}
		if env := validateHookArtifacts(args); env.Status != "blocked" {
			t.Fatalf("stale prd-scan semantic validation = %#v, want blocked", env)
		}
	})
}

func TestHookArtifactValidationUsesImplementSemanticValidator(t *testing.T) {
	t.Run("blocked on noncanonical closeout", func(t *testing.T) {
		project, feature, rel := newImplementFeatureProject(t)
		mustWriteHookText(t, filepath.Join(feature, "implementation-handoff.json"), "{\"source_revision\":5}\n")

		env := validateHookArtifacts([]string{
			"--command", "implement",
			"--feature-dir", rel,
			"--project-root", project,
		})
		if env.Status != "blocked" {
			t.Fatalf("implement semantic validation = %#v, want blocked", env)
		}
	})

	t.Run("ok on canonical trusted closeout", func(t *testing.T) {
		project, feature, rel := newImplementFeatureProject(t)
		withImplementCwd(t, project)
		writeImplementJSONFile(t, filepath.Join(feature, "worker-results", "T001.json"), map[string]any{
			"task_id": "T001", "status": "success",
			"validation_results": []any{map[string]any{"command": "go test ./...", "status": "passed"}},
			"summary":            "Implemented task",
		})
		writeImplementJSONFile(t, filepath.Join(feature, "implementation-review", "tasks", "T001.json"), map[string]any{
			"version": 1, "task_id": "T001", "status": "accepted", "blockers": []any{},
		})
		started, err := reserveImplementValidationEpoch(project, feature, "implement", "convergence", implementSnapshotSHA256(project, feature), []string{"go test ./..."}, []string{"T001"})
		if err != nil {
			t.Fatal(err)
		}
		if _, err := completeImplementValidationEpoch(project, feature, implementValidationFinishRequest{
			RunID: started["run_id"].(string), Status: "passed",
			EvidenceRefs: []string{"implementation-review/validation-evidence/V1.txt"},
			Summary:      "Implement convergence passed.",
		}); err != nil {
			t.Fatal(err)
		}
		var stdout bytes.Buffer
		if exit := runImplement([]string{"closeout", "--feature-dir", rel}, &stdout); exit != 0 {
			t.Fatalf("implement closeout exit=%d output=%s", exit, stdout.String())
		}

		env := validateHookArtifacts([]string{
			"--command", "implement",
			"--feature-dir", rel,
			"--project-root", project,
		})
		if env.Status != "ok" {
			t.Fatalf("implement semantic validation = %#v, want ok", env)
		}
	})
}

func TestHookArtifactValidationUsesProjectCognitionValidators(t *testing.T) {
	t.Run("map-scan", func(t *testing.T) {
		root := t.TempDir()
		runtimeDir := filepath.Join(root, ".specify", "project-cognition")
		if err := os.MkdirAll(filepath.Join(runtimeDir, "evidence"), 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.MkdirAll(filepath.Join(runtimeDir, "provisional"), 0o755); err != nil {
			t.Fatal(err)
		}
		mustWriteHookText(t, filepath.Join(runtimeDir, "status.json"), "{\"freshness\":\"fresh\"}\n")
		mustWriteHookText(t, filepath.Join(runtimeDir, "coverage.json"), "{\"rows\":[]}\n")
		mustWriteHookText(t, filepath.Join(runtimeDir, "provisional", "nodes.json"), "{\"rows\":[]}\n")
		mustWriteHookText(t, filepath.Join(runtimeDir, "provisional", "edges.json"), "{\"rows\":[]}\n")
		mustWriteHookText(t, filepath.Join(runtimeDir, "provisional", "observations.json"), "{\"rows\":[]}\n")

		env := validateHookArtifacts([]string{
			"--command", "map-scan",
			"--feature-dir", ".specify/project-cognition",
			"--project-root", root,
		})
		if env.Status != "blocked" {
			t.Fatalf("map-scan semantic validation = %#v, want blocked", env)
		}
	})

	t.Run("map-build", func(t *testing.T) {
		root := t.TempDir()
		runtimeDir := filepath.Join(root, ".specify", "project-cognition")
		if err := os.MkdirAll(runtimeDir, 0o755); err != nil {
			t.Fatal(err)
		}
		mustWriteHookText(t, filepath.Join(runtimeDir, "status.json"), "{\"freshness\":\"fresh\",\"graph_store_path\":\".specify/project-cognition/project-cognition.db\"}\n")
		mustWriteHookText(t, filepath.Join(runtimeDir, "project-cognition.db"), "not-a-real-db")

		env := validateHookArtifacts([]string{
			"--command", "map-build",
			"--feature-dir", ".specify/project-cognition",
			"--project-root", root,
		})
		if env.Status != "blocked" {
			t.Fatalf("map-build semantic validation = %#v, want blocked", env)
		}
	})

	t.Run("map-update", func(t *testing.T) {
		root := t.TempDir()
		runtimeDir := filepath.Join(root, ".specify", "project-cognition")
		if err := os.MkdirAll(runtimeDir, 0o755); err != nil {
			t.Fatal(err)
		}
		mustWriteHookText(t, filepath.Join(runtimeDir, "status.json"), "{\"freshness\":\"fresh\",\"graph_store_path\":\".specify/project-cognition/project-cognition.db\"}\n")
		mustWriteHookText(t, filepath.Join(runtimeDir, "project-cognition.db"), "not-a-real-db")

		env := validateHookArtifacts([]string{
			"--command", "map-update",
			"--feature-dir", ".specify/project-cognition",
			"--project-root", root,
		})
		if env.Status != "blocked" {
			t.Fatalf("map-update semantic validation = %#v, want blocked", env)
		}
	})
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
