package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

const (
	testDesignPublicationFilename = "test-design-publication.json"
	testDesignPublicationSchema   = "spec-kit-test-design-publication-v1"
	testDesignProjectionSchema    = "spec-kit-test-design-projection-v1"
)

func TestTestDesignProjectionCommandsArePublic(t *testing.T) {
	for _, subcommand := range []string{"publish", "projection-build", "projection-verify"} {
		t.Run(subcommand, func(t *testing.T) {
			env, _ := runTestDesignWorkflowCommand(t, []string{
				"test-design", subcommand, "--project-root", t.TempDir(), "--format", "json",
			})
			if strings.Contains(env.Summary, "unknown test-design subcommand") {
				t.Fatalf("%s is absent from the public test-design dispatch: %#v", subcommand, env)
			}
		})
	}
}

func TestTestDesignPublishProducesCanonicalConsumerNeutralPublication(t *testing.T) {
	for _, scope := range []string{"feature", "project"} {
		t.Run(scope, func(t *testing.T) {
			fixture := setupValidatedTestDesignProjectionFixture(t, scope, 1)
			publication := publishTestDesignProjectionFixture(t, fixture)

			if got := strings.TrimSpace(asString(publication["schema_version"])); got != testDesignPublicationSchema {
				t.Fatalf("publication schema_version=%q, want %q", got, testDesignPublicationSchema)
			}
			state, err := testDesignReadState(fixture.artifactRoot)
			if err != nil {
				t.Fatal(err)
			}
			if publication["source_fingerprint"] != state.Source.Fingerprint || intFromAny(publication["state_revision"]) != state.Revision || publication["claim_status"] != state.ClaimStatus {
				t.Fatalf("publication source/state/claim binding=%#v state=%#v", publication, state)
			}
			assertTestDesignProjectionDigestSet(t, publication["artifact_digests"])
			assertStringListEquals(t, publication["obligation_refs"], []string{"test-universe.json#/obligations/TO-001"})
			assertStringListEquals(t, publication["test_case_refs"], []string{"test-catalog.json#/cases/TC-001"})
			assertStringListEquals(t, publication["test_data_refs"], []string{"test-data-manifest.json#/datasets/TD-001"})
			assertStringListEquals(t, publication["coverage_refs"], []string{"coverage-matrix.json#/rows/COV-001"})
			assertStringListEquals(t, publication["gap_refs"], []string{"test-gaps.json#/gaps/GAP-001"})
			if publication["test_execution_status"] != "not_executed_by_test_design" {
				t.Fatalf("test_execution_status=%#v", publication["test_execution_status"])
			}
			forbidden := stringSetFromAny(publication["forbidden_claims"])
			for _, claim := range []string{"tests_executed", "tests_passed", "implementation_complete"} {
				if !forbidden[claim] {
					t.Fatalf("publication forbidden_claims=%#v, missing %q", publication["forbidden_claims"], claim)
				}
			}
		})
	}
}

func TestTestDesignProjectionBuildUsesPointerOnlyConsumerClosure(t *testing.T) {
	fixture := setupValidatedTestDesignProjectionFixture(t, "feature", 2)
	publishTestDesignProjectionFixture(t, fixture)

	planBasis := writeTestDesignProjectionBasis(t, fixture.projectRoot, filepath.ToSlash(filepath.Join(fixture.featureRel, "plan-contract.json")), map[string]any{"version": 2, "status": "ready"})
	quickBasis := writeTestDesignProjectionBasis(t, fixture.projectRoot, ".planning/quick/260811-projection/confirmation.json", map[string]any{"schema": "quick-confirmation-v1", "confirmation_digest": "quick-basis"})
	reviewBasis := writeTestDesignProjectionBasis(t, fixture.projectRoot, filepath.ToSlash(filepath.Join(fixture.featureRel, "implementation-handoff.json")), map[string]any{"version": 1, "status": "ready_for_review"})

	plan, _, _ := buildTestDesignProjection(t, fixture, "plan", planBasis, "")
	assertPointerOnlyTestDesignProjection(t, plan, "plan")

	quick, _, _ := buildTestDesignProjection(t, fixture, "quick", quickBasis, "TO-001")
	assertPointerOnlyTestDesignProjection(t, quick, "quick")
	quickSelection, _ := quick["selection"].(map[string]any)
	assertStringListEquals(t, quickSelection["obligation_refs"], []string{"test-universe.json#/obligations/TO-001"})
	assertStringListEquals(t, quickSelection["test_case_refs"], []string{"test-catalog.json#/cases/TC-001"})
	assertStringListEquals(t, quickSelection["test_data_refs"], []string{"test-data-manifest.json#/datasets/TD-001"})
	assertStringListEquals(t, quickSelection["coverage_refs"], []string{"coverage-matrix.json#/rows/COV-001"})
	assertStringListEquals(t, quickSelection["gap_refs"], []string{"test-gaps.json#/gaps/GAP-001"})
	for _, forbidden := range []string{"TO-002", "TC-002", "TD-002", "COV-002"} {
		if bytes.Contains(mustProjectionJSON(t, quickSelection), []byte(forbidden)) {
			t.Fatalf("quick subset leaked %s outside the selected obligation closure: %#v", forbidden, quickSelection)
		}
	}

	tasks, _, _ := buildTestDesignProjection(t, fixture, "tasks", planBasis, "")
	assertPointerOnlyTestDesignProjection(t, tasks, "tasks")
	tasksSelection, _ := tasks["selection"].(map[string]any)
	assertStringListEquals(t, tasksSelection["obligation_refs"], []string{
		"test-universe.json#/obligations/TO-001",
		"test-universe.json#/obligations/TO-002",
	})

	review, _, _ := buildTestDesignProjection(t, fixture, "review", reviewBasis, "")
	assertPointerOnlyTestDesignProjection(t, review, "review")

	partialTasks, partialTasksExit := runTestDesignWorkflowCommand(t, fixture.command(
		"projection-build", "--consumer", "tasks", "--basis-ref", planBasis, "--obligation-ids", "TO-001", "--format", "json",
	))
	if partialTasksExit == 0 || partialTasks.Status == "ok" || !strings.Contains(testDesignProjectionEnvelopeText(partialTasks), "full frozen obligation denominator") {
		t.Fatalf("Tasks accepted a subset projection: exit=%d env=%#v", partialTasksExit, partialTasks)
	}

	implement, implementExit := runTestDesignWorkflowCommand(t, fixture.command(
		"projection-build", "--consumer", "implement", "--basis-ref", planBasis, "--format", "json",
	))
	if implementExit == 0 || implement.Status == "ok" || !strings.Contains(testDesignProjectionEnvelopeText(implement), "task packet") {
		t.Fatalf("Implement received an independent projection instead of the Tasks-bound JIT packet: exit=%d env=%#v", implementExit, implement)
	}
}

func TestTestDesignProjectionVerifyFailsClosedOnEveryBoundInputTamper(t *testing.T) {
	fixture := setupValidatedTestDesignProjectionFixture(t, "feature", 2)
	publishTestDesignProjectionFixture(t, fixture)
	basisRef := writeTestDesignProjectionBasis(t, fixture.projectRoot, ".planning/quick/260811-verify/confirmation.json", map[string]any{"schema": "quick-confirmation-v1", "confirmation_digest": "verify-basis"})
	_, projectionRef, projectionSHA := buildTestDesignProjection(t, fixture, "quick", basisRef, "TO-001")
	requireTestDesignProjectionVerifyOK(t, fixture, projectionRef, projectionSHA)

	projectionPath := filepath.Join(fixture.projectRoot, filepath.FromSlash(projectionRef))
	tamperCases := []struct {
		name string
		path string
		edit func([]byte) []byte
	}{
		{name: "included source", path: filepath.Join(fixture.projectRoot, "src", "approval.go"), edit: appendProjectionTamper},
		{name: "canonical artifact", path: filepath.Join(fixture.artifactRoot, "test-catalog.json"), edit: appendProjectionTamper},
		{name: "publication", path: filepath.Join(fixture.artifactRoot, testDesignPublicationFilename), edit: appendProjectionTamper},
		{name: "basis", path: filepath.Join(fixture.projectRoot, filepath.FromSlash(basisRef)), edit: appendProjectionTamper},
		{name: "selection", path: projectionPath, edit: tamperTestDesignProjectionSelection},
	}
	for _, tc := range tamperCases {
		t.Run(tc.name, func(t *testing.T) {
			original, err := os.ReadFile(tc.path)
			if err != nil {
				t.Fatal(err)
			}
			if err := os.WriteFile(tc.path, tc.edit(original), 0o644); err != nil {
				t.Fatal(err)
			}
			env, exit := runTestDesignWorkflowCommand(t, fixture.command(
				"projection-verify", "--projection-ref", projectionRef, "--expected-sha256", projectionSHA, "--format", "json",
			))
			if exit == 0 || env.Status == "ok" {
				t.Fatalf("projection verify accepted %s tamper: exit=%d env=%#v", tc.name, exit, env)
			}
			if err := os.WriteFile(tc.path, original, 0o644); err != nil {
				t.Fatal(err)
			}
			requireTestDesignProjectionVerifyOK(t, fixture, projectionRef, projectionSHA)
		})
	}
}

func TestTestDesignLegacyHandoffRemainsTasksCompatibleAfterPublication(t *testing.T) {
	fixture := setupValidatedTestDesignProjectionFixture(t, "feature", 1)
	publishTestDesignProjectionFixture(t, fixture)
	requireTestDesignOK(t, fixture.command("handoff", "--format", "json"))

	handoff := readTestDesignJSONMap(t, filepath.Join(fixture.artifactRoot, "handoff-to-tasks.json"))
	if len(handoff) != 11 || handoff["schema_version"] != testDesignHandoffSchema || handoff["next_command"] != "/sp.tasks" {
		t.Fatalf("legacy Tasks handoff contract changed: %#v", handoff)
	}
	assertStringListEquals(t, handoff["test_case_refs"], []string{"test-catalog.json#/cases/TC-001"})
	assertStringListEquals(t, handoff["test_data_refs"], []string{"test-data-manifest.json#/datasets/TD-001"})
}

func TestTestDesignProjectPublicationAllowsPlanAndQuickButRejectsTasks(t *testing.T) {
	fixture := setupValidatedTestDesignProjectionFixture(t, "project", 1)
	publishTestDesignProjectionFixture(t, fixture)
	planBasis := writeTestDesignProjectionBasis(t, fixture.projectRoot, ".planning/projection-plan-basis.json", map[string]any{"source": "project-baseline"})
	quickBasis := writeTestDesignProjectionBasis(t, fixture.projectRoot, ".planning/quick/260811-project/confirmation.json", map[string]any{"schema": "quick-confirmation-v1"})

	plan, _, _ := buildTestDesignProjection(t, fixture, "plan", planBasis, "")
	assertPointerOnlyTestDesignProjection(t, plan, "plan")
	quick, _, _ := buildTestDesignProjection(t, fixture, "quick", quickBasis, "TO-001")
	assertPointerOnlyTestDesignProjection(t, quick, "quick")

	tasks, exit := runTestDesignWorkflowCommand(t, fixture.command(
		"projection-build", "--consumer", "tasks", "--basis-ref", planBasis, "--format", "json",
	))
	if exit == 0 || tasks.Status == "ok" || !strings.Contains(testDesignProjectionEnvelopeText(tasks), "feature scope") {
		t.Fatalf("project publication authorized Tasks: exit=%d env=%#v", exit, tasks)
	}
}

type testDesignProjectionFixture struct {
	projectRoot  string
	featureRel   string
	artifactRoot string
	scope        string
}

func (fixture testDesignProjectionFixture) command(parts ...string) []string {
	args := []string{"test-design"}
	args = append(args, parts...)
	if fixture.scope == "feature" {
		args = append(args, "--feature-dir", fixture.featureRel)
	}
	return args
}

func setupValidatedTestDesignProjectionFixture(t *testing.T, scope string, obligationCount int) testDesignProjectionFixture {
	t.Helper()
	projectRoot := t.TempDir()
	if err := seedTestDesignScaffoldTemplates(projectRoot); err != nil {
		t.Fatal(err)
	}
	for _, dir := range []string{"src", "tests"} {
		if err := os.MkdirAll(filepath.Join(projectRoot, dir), 0o755); err != nil {
			t.Fatal(err)
		}
	}
	if err := os.WriteFile(filepath.Join(projectRoot, "src", "approval.go"), []byte("package approval\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(projectRoot, "tests", "approval_test.go"), []byte("package approval\n"), 0o644); err != nil {
		t.Fatal(err)
	}

	featureRel := ""
	artifactRoot := filepath.Join(projectRoot, ".specify", "test-design")
	sourceRef := "README.md"
	if scope == "feature" {
		featureRel = filepath.ToSlash(filepath.Join("specs", "001-test-design"))
		featureDir := filepath.Join(projectRoot, filepath.FromSlash(featureRel))
		if err := os.MkdirAll(featureDir, 0o755); err != nil {
			t.Fatal(err)
		}
		sourceRef = featureRel + "/spec.md"
		if err := os.WriteFile(filepath.Join(featureDir, "spec.md"), []byte("REQ-001 approval\nREQ-002 reversal\n"), 0o644); err != nil {
			t.Fatal(err)
		}
		artifactRoot = filepath.Join(featureDir, "test-design")
	} else {
		if err := os.WriteFile(filepath.Join(projectRoot, sourceRef), []byte("# Project\n\nREQ-001 approval.\nREQ-002 reversal.\n"), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	withTestDesignCWD(t, projectRoot)

	initInput := map[string]any{
		"query": "Publish a consumer-neutral test-design bundle", "source_refs": []any{sourceRef},
		"included_paths": []any{"src", "tests"}, "excluded_paths": []any{"vendor"},
		"risk_dimensions": []any{"functional", "state", "security", "recovery"},
	}
	initArgs := []string{"test-design", "init", "--scope", scope, "--mode", map[string]string{"feature": "feature", "project": "project-baseline"}[scope], "--leader-id", "leader-1", "--input-json", mustTestDesignJSON(t, initInput), "--format", "json"}
	if scope == "feature" {
		initArgs = append(initArgs, "--feature-dir", featureRel)
	}
	requireTestDesignOK(t, initArgs)

	evidenceRef := registerTestDesignEvidence(t, projectRoot, "projection contract evidence")
	writeValidTestDesignWorkflowBundle(t, artifactRoot, evidenceRef)
	if obligationCount > 1 {
		addSecondTestDesignProjectionObligation(t, artifactRoot)
	}
	addResolvedTestDesignProjectionGap(t, artifactRoot)
	fixture := testDesignProjectionFixture{projectRoot: projectRoot, featureRel: featureRel, artifactRoot: artifactRoot, scope: scope}
	requireTestDesignOK(t, fixture.command("universe-build", "--format", "json"))

	obligationIDs := make([]any, 0, obligationCount)
	obligationResults := make([]any, 0, obligationCount)
	candidateCases := make([]any, 0, obligationCount)
	dataRequirements := make([]any, 0, obligationCount)
	for index := 1; index <= obligationCount; index++ {
		obligationID := fmt.Sprintf("TO-%03d", index)
		obligationIDs = append(obligationIDs, obligationID)
		obligationResults = append(obligationResults, map[string]any{
			"obligation_id": obligationID, "status": "covered", "evidence_refs": []any{evidenceRef},
			"gap_refs": []any{}, "summary": obligationID + " is covered by verified evidence.",
		})
		candidateCases = append(candidateCases, map[string]any{"test_case_id": fmt.Sprintf("TC-%03d", index)})
		dataRequirements = append(dataRequirements, map[string]any{"test_data_id": fmt.Sprintf("TD-%03d", index)})
	}
	readPaths := []any{"src", "tests", sourceRef}
	lanes := map[string]any{"lanes": []any{map[string]any{
		"lane_id": "LANE-001", "kind": "discovery", "title": "Projection discovery", "obligation_ids": obligationIDs,
		"read_paths": readPaths, "questions": []any{"Prove every frozen obligation and its consumer closure."},
	}}}
	requireTestDesignOK(t, fixture.command("lane-prepare", "--input-json", mustTestDesignJSON(t, lanes), "--format", "json"))
	lease := requireTestDesignOK(t, fixture.command("lane-lease", "--worker-id", "worker-1", "--format", "json"))
	attemptID := lease.Data["attempt_id"].(string)
	result := map[string]any{
		"lane_id": "LANE-001", "attempt_id": attemptID, "status": "success", "inspected_paths": readPaths,
		"evidence_refs": []any{evidenceRef}, "obligation_results": obligationResults, "checks": []any{},
		"candidate_cases": candidateCases, "data_requirements": dataRequirements,
		"contradictions": []any{}, "unknowns": []any{}, "gaps": []any{}, "summary": "Projection discovery complete.",
	}
	requireTestDesignOK(t, fixture.command("lane-checkpoint", "--lane-id", "LANE-001", "--attempt-id", attemptID, "--result-json", mustTestDesignJSON(t, result), "--format", "json"))
	requireTestDesignOK(t, fixture.command("lane-accept", "--lane-id", "LANE-001", "--attempt-id", attemptID, "--format", "json"))
	requireTestDesignOK(t, fixture.command("synthesize", "--leader-id", "leader-1", "--format", "json"))
	requireTestDesignOK(t, fixture.command("audit-prepare", "--format", "json"))
	auditLease := requireTestDesignOK(t, fixture.command("lane-lease", "--worker-id", "independent-auditor", "--format", "json"))
	auditPaths := make([]any, 0, 5)
	rootRef := ".specify/test-design"
	if scope == "feature" {
		rootRef = filepath.ToSlash(filepath.Join(featureRel, "test-design"))
	}
	for _, name := range []string{"test-universe.json", "test-catalog.json", "test-data-manifest.json", "coverage-matrix.json", "test-gaps.json"} {
		auditPaths = append(auditPaths, filepath.ToSlash(filepath.Join(rootRef, name)))
	}
	auditResult := map[string]any{
		"lane_id": auditLease.Data["lane_id"], "attempt_id": auditLease.Data["attempt_id"], "status": "success",
		"inspected_paths": auditPaths, "evidence_refs": []any{evidenceRef}, "obligation_results": obligationResults,
		"checks": projectionAuditChecks(evidenceRef, obligationIDs), "candidate_cases": []any{}, "data_requirements": []any{},
		"contradictions": []any{}, "unknowns": []any{}, "gaps": []any{}, "findings": []any{}, "summary": "Independent projection audit complete.",
	}
	requireTestDesignOK(t, fixture.command("lane-checkpoint", "--lane-id", asString(auditLease.Data["lane_id"]), "--attempt-id", asString(auditLease.Data["attempt_id"]), "--result-json", mustTestDesignJSON(t, auditResult), "--format", "json"))
	requireTestDesignOK(t, fixture.command("lane-accept", "--lane-id", asString(auditLease.Data["lane_id"]), "--attempt-id", asString(auditLease.Data["attempt_id"]), "--format", "json"))
	validated := requireTestDesignOK(t, fixture.command("validate", "--format", "json"))
	if validated.Data["claim_status"] != "complete_against_frozen_scope" {
		t.Fatalf("validated projection fixture claim=%#v", validated.Data["claim_status"])
	}
	return fixture
}

func publishTestDesignProjectionFixture(t *testing.T, fixture testDesignProjectionFixture) map[string]any {
	t.Helper()
	state, err := testDesignReadState(fixture.artifactRoot)
	if err != nil {
		t.Fatal(err)
	}
	requireTestDesignOK(t, fixture.command("publish", "--expected-revision", fmt.Sprint(state.Revision), "--format", "json"))
	return readTestDesignJSONMap(t, filepath.Join(fixture.artifactRoot, testDesignPublicationFilename))
}

func buildTestDesignProjection(t *testing.T, fixture testDesignProjectionFixture, consumer, basisRef, obligationIDs string) (map[string]any, string, string) {
	t.Helper()
	args := []string{"projection-build", "--consumer", consumer, "--basis-ref", basisRef}
	if obligationIDs != "" {
		args = append(args, "--obligation-ids", obligationIDs)
	}
	args = append(args, "--format", "json")
	env := requireTestDesignOK(t, fixture.command(args...))
	projectionRef := strings.TrimSpace(asString(env.Data["projection_ref"]))
	projectionSHA := strings.TrimSpace(asString(env.Data["projection_sha256"]))
	if projectionRef == "" || !testDesignSHA256Pattern.MatchString(projectionSHA) {
		t.Fatalf("projection-build returned an invalid binding: %#v", env.Data)
	}
	if filepath.IsAbs(projectionRef) || strings.Contains(filepath.ToSlash(filepath.Clean(projectionRef)), "../") {
		t.Fatalf("projection_ref must be a safe project-relative path: %q", projectionRef)
	}
	projectionPath := filepath.Join(fixture.projectRoot, filepath.FromSlash(projectionRef))
	projection := readTestDesignJSONMap(t, projectionPath)
	raw, err := os.ReadFile(projectionPath)
	if err != nil {
		t.Fatal(err)
	}
	if got := projectionDigest(raw); got != projectionSHA {
		t.Fatalf("projection sha=%q, want %q", projectionSHA, got)
	}
	return projection, projectionRef, projectionSHA
}

func requireTestDesignProjectionVerifyOK(t *testing.T, fixture testDesignProjectionFixture, projectionRef, projectionSHA string) {
	t.Helper()
	env := requireTestDesignOK(t, fixture.command(
		"projection-verify", "--projection-ref", projectionRef, "--expected-sha256", projectionSHA, "--format", "json",
	))
	if env.Data["valid"] != true || env.Data["fresh"] != true {
		t.Fatalf("projection verify did not report valid+fresh: %#v", env.Data)
	}
}

func addResolvedTestDesignProjectionGap(t *testing.T, artifactRoot string) {
	t.Helper()
	universe := readTestDesignJSONMap(t, filepath.Join(artifactRoot, "test-universe.json"))
	obligations := universe["obligations"].([]any)
	obligation := obligations[0].(map[string]any)
	obligation["gap_refs"] = []any{"GAP-001"}
	if err := writeTestDesignJSONFixture(filepath.Join(artifactRoot, "test-universe.json"), universe); err != nil {
		t.Fatal(err)
	}
	gaps := map[string]any{
		"schema_version": testDesignGapsSchema, "status": "clear", "gaps": []any{map[string]any{
			"gap_id": "GAP-001", "category": "coverage", "severity": "low", "disposition": "resolved",
			"source_refs": []any{"REQ-001"}, "affected_obligation_refs": []any{"TO-001"}, "coverage_refs": []any{},
			"affected_test_case_refs": []any{"TC-001"}, "affected_test_data_refs": []any{"TD-001"},
			"owner": "test-design leader", "residual_risk": "Resolved before publication.",
			"next_action": "Reopen if the frozen source changes.", "unblock_criteria": "The resolved coverage remains demonstrable.",
		}},
	}
	if err := writeTestDesignJSONFixture(filepath.Join(artifactRoot, "test-gaps.json"), gaps); err != nil {
		t.Fatal(err)
	}
}

func addSecondTestDesignProjectionObligation(t *testing.T, artifactRoot string) {
	t.Helper()
	universe := readTestDesignJSONMap(t, filepath.Join(artifactRoot, "test-universe.json"))
	secondObligation := cloneTestDesignProjectionMap(t, universe["obligations"].([]any)[0])
	secondObligation["obligation_id"] = "TO-002"
	secondObligation["title"] = "Reversal is recoverable"
	secondObligation["source_refs"] = []any{"REQ-002"}
	secondObligation["capability_refs"] = []any{"CAP-002"}
	secondObligation["scenario_refs"] = []any{"SCN-002"}
	secondObligation["test_case_ids"] = []any{"TC-002"}
	secondObligation["gap_refs"] = []any{}
	universe["obligations"] = append(universe["obligations"].([]any), secondObligation)
	secondCapability := cloneTestDesignProjectionMap(t, universe["capabilities"].([]any)[0])
	secondCapability["capability_id"] = "CAP-002"
	secondCapability["title"] = "Reversal"
	secondCapability["requirement_refs"] = []any{"REQ-002"}
	secondCapability["obligation_ids"] = []any{"TO-002"}
	secondCapability["test_case_ids"] = []any{"TC-002"}
	secondCapability["scenario_ids"] = []any{"SCN-002"}
	universe["capabilities"] = append(universe["capabilities"].([]any), secondCapability)
	secondScenario := cloneTestDesignProjectionMap(t, universe["scenarios"].([]any)[0])
	secondScenario["scenario_id"] = "SCN-002"
	secondScenario["title"] = "Reverse"
	secondScenario["capability_refs"] = []any{"CAP-002"}
	secondScenario["obligation_refs"] = []any{"TO-002"}
	secondScenario["test_case_ids"] = []any{"TC-002"}
	secondScenario["coverage_ref"] = "COV-002"
	universe["scenarios"] = append(universe["scenarios"].([]any), secondScenario)
	secondUniverseCase := cloneTestDesignProjectionMap(t, universe["test_cases"].([]any)[0])
	secondUniverseCase["test_case_id"] = "TC-002"
	secondUniverseCase["title"] = "Reverse once"
	secondUniverseCase["obligation_refs"] = []any{"TO-002"}
	secondUniverseCase["capability_refs"] = []any{"CAP-002"}
	secondUniverseCase["scenario_refs"] = []any{"SCN-002"}
	secondUniverseCase["data_refs"] = []any{"TD-002"}
	secondUniverseCase["coverage_refs"] = []any{"COV-002"}
	universe["test_cases"] = append(universe["test_cases"].([]any), secondUniverseCase)
	if err := writeTestDesignJSONFixture(filepath.Join(artifactRoot, "test-universe.json"), universe); err != nil {
		t.Fatal(err)
	}

	catalog := readTestDesignJSONMap(t, filepath.Join(artifactRoot, "test-catalog.json"))
	secondCase := cloneTestDesignProjectionMap(t, catalog["cases"].([]any)[0])
	secondCase["test_case_id"] = "TC-002"
	secondCase["title"] = "Reverse once"
	secondCase["objective"] = "Prove reversal is recoverable"
	secondCase["requirement_refs"] = []any{"REQ-002"}
	secondCase["obligation_refs"] = []any{"TO-002"}
	secondCase["capability_refs"] = []any{"CAP-002"}
	secondCase["scenario_refs"] = []any{"SCN-002"}
	secondCase["test_data_refs"] = []any{"TD-002"}
	catalog["cases"] = append(catalog["cases"].([]any), secondCase)
	if err := writeTestDesignJSONFixture(filepath.Join(artifactRoot, "test-catalog.json"), catalog); err != nil {
		t.Fatal(err)
	}

	manifest := readTestDesignJSONMap(t, filepath.Join(artifactRoot, "test-data-manifest.json"))
	secondData := cloneTestDesignProjectionMap(t, manifest["datasets"].([]any)[0])
	secondData["test_data_id"] = "TD-002"
	secondData["name"] = "Synthetic reversal order"
	secondData["applicable_test_case_ids"] = []any{"TC-002"}
	secondData["applicable_scenario_ids"] = []any{"SCN-002"}
	manifest["datasets"] = append(manifest["datasets"].([]any), secondData)
	if err := writeTestDesignJSONFixture(filepath.Join(artifactRoot, "test-data-manifest.json"), manifest); err != nil {
		t.Fatal(err)
	}

	matrix := readTestDesignJSONMap(t, filepath.Join(artifactRoot, "coverage-matrix.json"))
	secondCoverage := cloneTestDesignProjectionMap(t, matrix["rows"].([]any)[0])
	secondCoverage["coverage_id"] = "COV-002"
	secondCoverage["requirement_ref"] = "REQ-002"
	secondCoverage["obligation_ref"] = "TO-002"
	secondCoverage["capability_ref"] = "CAP-002"
	secondCoverage["scenario_ref"] = "SCN-002"
	secondCoverage["test_case_ref"] = "TC-002"
	secondCoverage["test_data_refs"] = []any{"TD-002"}
	secondCoverage["acceptance_refs"] = []any{"HA-002"}
	matrix["rows"] = append(matrix["rows"].([]any), secondCoverage)
	if err := writeTestDesignJSONFixture(filepath.Join(artifactRoot, "coverage-matrix.json"), matrix); err != nil {
		t.Fatal(err)
	}
}

func projectionAuditChecks(evidenceRef string, obligationIDs []any) []any {
	checks := make([]any, 0, len(testDesignAuditCoreCheckIDs))
	for _, checkID := range testDesignAuditCoreCheckIDs {
		checks = append(checks, map[string]any{
			"check_id": checkID, "status": "passed", "evidence_refs": []any{evidenceRef},
			"affected_obligation_refs": append([]any{}, obligationIDs...), "finding_refs": []any{},
			"summary": "Independent verified projection check passed.",
		})
	}
	return checks
}

func cloneTestDesignProjectionMap(t *testing.T, value any) map[string]any {
	t.Helper()
	raw, err := json.Marshal(value)
	if err != nil {
		t.Fatal(err)
	}
	var result map[string]any
	if err := json.Unmarshal(raw, &result); err != nil {
		t.Fatal(err)
	}
	return result
}

func writeTestDesignProjectionBasis(t *testing.T, projectRoot, ref string, payload map[string]any) string {
	t.Helper()
	path := filepath.Join(projectRoot, filepath.FromSlash(ref))
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := writeTestDesignJSONFixture(path, payload); err != nil {
		t.Fatal(err)
	}
	return filepath.ToSlash(ref)
}

func assertTestDesignProjectionDigestSet(t *testing.T, value any) {
	t.Helper()
	digests, ok := value.(map[string]any)
	expected := []string{"state", "universe", "catalog", "data_manifest", "coverage_matrix", "gaps", "audit_result"}
	if !ok || len(digests) != len(expected) {
		t.Fatalf("artifact_digests=%#v, want exactly seven canonical digests", value)
	}
	for _, key := range expected {
		if digest := strings.TrimSpace(asString(digests[key])); !testDesignSHA256Pattern.MatchString(digest) {
			t.Fatalf("artifact_digests[%s]=%q", key, digest)
		}
	}
}

func assertPointerOnlyTestDesignProjection(t *testing.T, projection map[string]any, consumer string) {
	t.Helper()
	if projection["schema_version"] != testDesignProjectionSchema || projection["consumer"] != consumer {
		t.Fatalf("projection identity=%#v", projection)
	}
	for _, key := range []string{"publication_ref", "publication_sha256", "basis_ref", "basis_sha256", "selection_sha256"} {
		if strings.TrimSpace(asString(projection[key])) == "" {
			t.Fatalf("projection missing %s: %#v", key, projection)
		}
	}
	selection, ok := projection["selection"].(map[string]any)
	if !ok {
		t.Fatalf("projection selection=%#v", projection["selection"])
	}
	for _, key := range []string{"obligation_refs", "test_case_refs", "test_data_refs", "coverage_refs", "gap_refs"} {
		values, ok := selection[key].([]any)
		if !ok {
			t.Fatalf("selection %s=%#v", key, selection[key])
		}
		for _, value := range values {
			text, ok := value.(string)
			if !ok || !strings.Contains(text, ".json#/") {
				t.Fatalf("selection %s contains inline/non-pointer value %#v", key, value)
			}
		}
	}
	for _, forbidden := range []string{"obligations", "cases", "datasets", "rows", "test_cases", "test_data"} {
		if _, exists := projection[forbidden]; exists {
			t.Fatalf("projection copied canonical truth in field %s", forbidden)
		}
	}
}

func stringSetFromAny(value any) map[string]bool {
	result := map[string]bool{}
	for _, item := range testDesignStrings(value) {
		result[item] = true
	}
	return result
}

func testDesignProjectionEnvelopeText(env Envelope) string {
	parts := []string{env.Summary}
	for _, blocker := range env.Blockers {
		parts = append(parts, fmt.Sprint(blocker))
	}
	return strings.ToLower(strings.Join(parts, " "))
}

func appendProjectionTamper(raw []byte) []byte {
	return append(append([]byte{}, raw...), []byte(" \n")...)
}

func tamperTestDesignProjectionSelection(raw []byte) []byte {
	var payload map[string]any
	if err := json.Unmarshal(raw, &payload); err != nil {
		return appendProjectionTamper(raw)
	}
	selection, _ := payload["selection"].(map[string]any)
	if selection == nil {
		return appendProjectionTamper(raw)
	}
	selection["test_case_refs"] = append(testDesignAnySlice(selection["test_case_refs"]), "test-catalog.json#/cases/TC-FAKE")
	mutated, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		return appendProjectionTamper(raw)
	}
	return append(mutated, '\n')
}

func testDesignAnySlice(value any) []any {
	items, _ := value.([]any)
	return append([]any{}, items...)
}

func mustProjectionJSON(t *testing.T, value any) []byte {
	t.Helper()
	raw, err := json.Marshal(value)
	if err != nil {
		t.Fatal(err)
	}
	return raw
}

func projectionDigest(raw []byte) string {
	digest := sha256.Sum256(raw)
	return hex.EncodeToString(digest[:])
}
