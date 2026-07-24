package main

import (
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strconv"
	"strings"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/filelock"
)

const (
	reviewStateFilename               = "review-state.json"
	implementationHandoffFilename     = "implementation-handoff.json"
	humanAcceptanceFilename           = "human-acceptance.json"
	humanAcceptanceSummaryFilename    = "implementation-summary.md"
	humanAcceptanceRepairJournalName  = ".human-acceptance-repair.json"
	humanAcceptanceRepairBackupName   = ".human-acceptance-repair-backup.json"
	reviewSchemaRef                   = ".specify/templates/review-state-schema.json"
	humanAcceptanceSchemaRef          = ".specify/templates/human-acceptance-state-schema.json"
	reviewStateVersion                = 2
	humanAcceptanceStateVersion       = 2
	implementationFingerprintAlgorith = "git-working-tree-v1"
)

type reviewAcceptFeature struct {
	id  string
	abs string
	rel string
}

func runReview(args []string, stdout io.Writer) int {
	if len(args) == 0 {
		return writeEnvelope(stdout, NewEnvelope("usage-error", "missing review subcommand"))
	}
	service := reviewAcceptService{projectRoot: optionValue(args, "--project-root", ".")}
	var env Envelope
	switch args[0] {
	case "prepare":
		expected, ok := intOption(args, "--expected-revision")
		if !ok {
			return writeEnvelope(stdout, usageEnvelope("review prepare requires --expected-revision"))
		}
		env = service.prepareReview(optionValue(args, "--feature-dir", ""), expected)
	case "resume-audit":
		env = service.resumeReviewAudit(optionValue(args, "--feature-dir", ""))
	case "validate":
		env = service.validateReviewEnvelope(optionValue(args, "--feature-dir", ""))
	case "closeout":
		expected, ok := intOption(args, "--expected-revision")
		if !ok {
			return writeEnvelope(stdout, usageEnvelope("review closeout requires --expected-revision"))
		}
		env = service.closeoutReview(optionValue(args, "--feature-dir", ""), expected)
	default:
		env = NewEnvelope("usage-error", fmt.Sprintf("unknown review subcommand %q", args[0]))
	}
	return writeEnvelope(stdout, env)
}

func runAccept(args []string, stdout io.Writer) int {
	if len(args) == 0 {
		return writeEnvelope(stdout, NewEnvelope("usage-error", "missing accept subcommand"))
	}
	service := reviewAcceptService{projectRoot: optionValue(args, "--project-root", ".")}
	var env Envelope
	switch args[0] {
	case "prepare":
		env = service.prepareHumanAcceptance(optionValue(args, "--feature-dir", ""))
	case "validate":
		env = service.validateHumanAcceptanceEnvelope(optionValue(args, "--feature-dir", ""))
	case "route-repair":
		expected, ok := intOption(args, "--expected-revision")
		if !ok {
			return writeEnvelope(stdout, usageEnvelope("accept route-repair requires --expected-revision"))
		}
		env = service.routeHumanAcceptanceRepair(routeHumanAcceptanceRepairRequest{
			featureDir:        optionValue(args, "--feature-dir", ""),
			findingID:         optionValue(args, "--finding-id", ""),
			route:             optionValue(args, "--route", ""),
			expectedRevision:  expected,
			evidence:          optionValues(args, "--evidence"),
			humanActionReason: optionValue(args, "--human-action-reason", ""),
		})
	case "closeout":
		expected, ok := intOption(args, "--expected-revision")
		if !ok {
			root, feature, featureEnv, featureOK := service.resolveFeature(optionValue(args, "--feature-dir", ""))
			if !featureOK {
				return writeEnvelope(stdout, featureEnv)
			}
			workflow := NewWorkflowService(root).Show(WorkflowShowRequest{FeatureDir: feature.rel})
			revision, revisionOK := jsonInteger(workflow.Data["revision"])
			if workflow.Status != "ok" || !revisionOK {
				return writeEnvelope(stdout, workflow)
			}
			expected = revision
		}
		env = service.closeoutHumanAcceptance(optionValue(args, "--feature-dir", ""), expected)
	default:
		env = NewEnvelope("usage-error", fmt.Sprintf("unknown accept subcommand %q", args[0]))
	}
	return writeEnvelope(stdout, env)
}

type reviewAcceptService struct {
	projectRoot string
}

type routeHumanAcceptanceRepairRequest struct {
	featureDir        string
	findingID         string
	route             string
	expectedRevision  int
	evidence          []string
	humanActionReason string
}

func (service reviewAcceptService) prepareReview(featureDir string, expectedRevision int) Envelope {
	root, feature, env, ok := service.resolveFeature(featureDir)
	if !ok {
		return env
	}
	workflow := NewWorkflowService(root).Show(WorkflowShowRequest{FeatureDir: feature.rel})
	if workflow.Status != "ok" {
		return workflow
	}
	if stage, _ := workflow.Data["stage"].(string); stage != "review" {
		return blockedEnvelope("review prepare requires active review workflow stage", "workflow stage must be review")
	}
	if revision, ok := jsonInteger(workflow.Data["revision"]); !ok || revision != expectedRevision {
		return blockedEnvelope("review prepare revision mismatch", "expected revision does not match workflow revision")
	}
	handoffPath := filepath.Join(feature.abs, implementationHandoffFilename)
	handoff, err := readJSONObject(handoffPath)
	if err != nil {
		return blockedEnvelope("implementation handoff is unavailable", err.Error())
	}
	sourceRevision, ok := jsonInteger(handoff["source_revision"])
	if !ok || sourceRevision != expectedRevision {
		return blockedEnvelope("implementation handoff revision mismatch", "implementation-handoff.json source_revision must match expected revision")
	}
	handoffSHA, err := fileSHA256(handoffPath)
	if err != nil {
		return blockedEnvelope("implementation handoff is unavailable", err.Error())
	}
	fingerprint := stringField(handoff, "implementation_fingerprint")
	if fingerprint == "" {
		fingerprint = stringField(handoff, "implementation_snapshot_sha256")
	}
	if fingerprint == "" {
		fingerprint = stringField(handoff, "fingerprint")
	}
	if fingerprint == "" {
		fingerprint = sourceTreeFingerprint(root, feature.abs)
	}
	statePath := filepath.Join(feature.abs, reviewStateFilename)
	release, lockEnv, locked := acquireReviewAcceptLock(filepath.Join(feature.abs, ".review-state.lock"))
	if !locked {
		return lockEnv
	}
	defer release()
	if existing, err := readJSONObject(statePath); err == nil {
		if source, ok := existing["source"].(map[string]any); ok &&
			stringField(source, "implementation_handoff_sha256") == handoffSHA &&
			intField(source, "workflow_revision") == expectedRevision {
			env := NewEnvelope("ok", "system review state is already prepared")
			env.Data = existing
			env.ShowArgv = reviewShowArgv(feature.rel)
			env.NextArgv = []string{"specify-runtime", "review", "validate", "--feature-dir", feature.rel, "--format", "json"}
			return env
		}
		return blockedEnvelope("existing review state is stale", "preserve existing review-state.json or restart through the Python runtime with --restart-stale")
	}
	state := map[string]any{
		"version":    reviewStateVersion,
		"schema_ref": reviewSchemaRef,
		"status":     "gathering",
		"source": map[string]any{
			"workflow_revision":                expectedRevision,
			"implementation_handoff":           implementationHandoffFilename,
			"implementation_handoff_sha256":    handoffSHA,
			"implementation_fingerprint":       fingerprint,
			"fingerprint_algorithm":            valueOr(handoff["fingerprint_algorithm"], implementationFingerprintAlgorith),
			"implementation_summary_sha256":    optionalFileSHA256(filepath.Join(feature.abs, humanAcceptanceSummaryFilename)),
			"review_cycle":                     1,
			"human_acceptance_contract_sha256": nestedString(handoff, "human_acceptance_contract", "sha256"),
		},
		"entrypoints":                  cloneAny(handoff["entrypoints"]),
		"scenarios":                    cloneAny(handoff["review_scenarios"]),
		"obligations":                  cloneAny(handoff["review_obligations"]),
		"human_acceptance_scenarios":   cloneAny(handoff["human_acceptance_scenarios"]),
		"human_acceptance_obligations": cloneAny(handoff["human_acceptance_obligations"]),
		"user_confirmed_deferrals":     cloneAny(handoff["user_confirmed_deferrals"]),
		"findings":                     []any{},
		"reviewed_runtime_targets":     cloneAny(handoff["runtime_targets"]),
		"evidence":                     []any{},
		"rounds":                       []any{},
		"blocker":                      nil,
		"final": map[string]any{
			"verdict":                       "pending",
			"coverage_verdict":              "pending",
			"repair_verdict":                "pending",
			"integration_verdict":           "pending",
			"all_packets_joined":            false,
			"reviewed_snapshot_sha256":      "",
			"implementation_summary_sha256": optionalFileSHA256(filepath.Join(feature.abs, humanAcceptanceSummaryFilename)),
			"runtime_targets_sha256":        "",
		},
	}
	if err := writeReviewAcceptJSONAtomic(statePath, state); err != nil {
		return errorEnvelope("failed to write review state", err)
	}
	env = NewEnvelope("ok", "system review state prepared")
	env.Data = state
	env.ShowArgv = reviewShowArgv(feature.rel)
	env.NextArgv = []string{"specify-runtime", "review", "validate", "--feature-dir", feature.rel, "--format", "json"}
	return env
}

func (service reviewAcceptService) resumeReviewAudit(featureDir string) Envelope {
	root, feature, env, ok := service.resolveFeature(featureDir)
	if !ok {
		return env
	}
	validation := service.validateReview(feature)
	env = NewEnvelope("ok", "review resume audit completed")
	env.Data["valid"] = validation.valid
	env.Data["fresh"] = validation.fresh
	env.Data["errors"] = validation.errors
	env.Data["state_path"] = filepath.Join(feature.rel, reviewStateFilename)
	env.Data["current_fingerprint"] = sourceTreeFingerprint(root, feature.abs)
	env.Data["findings"] = []any{}
	if validation.state != nil {
		env.Data["status"] = validation.state["status"]
		env.Data["state"] = validation.state
		if findings, ok := validation.state["findings"].([]any); ok {
			env.Data["findings"] = findings
		}
		env.NextArgv = []string{"specify-runtime", "review", "validate", "--feature-dir", feature.rel, "--format", "json"}
	} else {
		env.NextArgv = []string{"specify-runtime", "review", "prepare", "--feature-dir", feature.rel, "--expected-revision", "<revision>", "--format", "json"}
	}
	env.ShowArgv = reviewShowArgv(feature.rel)
	return env
}

func (service reviewAcceptService) validateReviewEnvelope(featureDir string) Envelope {
	_, feature, env, ok := service.resolveFeature(featureDir)
	if !ok {
		return env
	}
	validation := service.validateReview(feature)
	env = NewEnvelope("ok", "review validation completed")
	env.Data["valid"] = validation.valid
	env.Data["fresh"] = validation.fresh
	env.Data["errors"] = validation.errors
	env.Data["state"] = validation.state
	env.Data["state_path"] = filepath.Join(feature.rel, reviewStateFilename)
	env.Data["current_fingerprint"] = validation.currentFingerprint
	env.ShowArgv = reviewShowArgv(feature.rel)
	return env
}

func (service reviewAcceptService) closeoutReview(featureDir string, expectedRevision int) Envelope {
	root, feature, env, ok := service.resolveFeature(featureDir)
	if !ok {
		return env
	}
	workflow := NewWorkflowService(root).Show(WorkflowShowRequest{FeatureDir: feature.rel})
	if workflow.Status != "ok" {
		return workflow
	}
	if stage, _ := workflow.Data["stage"].(string); stage != "review" {
		return blockedEnvelope("review closeout requires review workflow stage", "workflow stage must be review")
	}
	if revision, ok := jsonInteger(workflow.Data["revision"]); !ok || revision != expectedRevision {
		return blockedEnvelope("review closeout revision mismatch", "expected revision does not match workflow revision")
	}
	validation := service.validateReview(feature)
	if !validation.valid {
		env := NewEnvelope("blocked", "review closeout blocked")
		env.Blockers = append(env.Blockers, strings.Join(validation.errors, "; "))
		env.Data["valid"] = false
		env.Data["fresh"] = validation.fresh
		env.Data["state_path"] = filepath.Join(feature.rel, reviewStateFilename)
		env.ShowArgv = reviewShowArgv(feature.rel)
		env.NextArgv = []string{"specify-runtime", "review", "resume-audit", "--feature-dir", feature.rel, "--format", "json"}
		return env
	}
	env = NewEnvelope("ok", "system review is approved and ready for workflow stage completion")
	env.Data["status"] = "approved"
	env.Data["fresh"] = true
	env.Data["state_path"] = filepath.Join(feature.rel, reviewStateFilename)
	env.ShowArgv = reviewShowArgv(feature.rel)
	env.NextArgv = workflowCompleteArgv(reviewAcceptWorkflowFeature(feature), expectedRevision)
	return env
}

func (service reviewAcceptService) prepareHumanAcceptance(featureDir string) Envelope {
	_, feature, env, ok := service.resolveFeature(featureDir)
	if !ok {
		return env
	}
	reviewValidation := service.validateReview(feature)
	if !reviewValidation.valid || reviewValidation.state == nil || reviewValidation.state["status"] != "approved" {
		env := NewEnvelope("blocked", "human acceptance requires fresh approved review")
		env.Blockers = append(env.Blockers, strings.Join(reviewValidation.errors, "; "))
		env.NextArgv = []string{"specify-runtime", "review", "resume-audit", "--feature-dir", feature.rel, "--format", "json"}
		return env
	}
	handoffPath := filepath.Join(feature.abs, implementationHandoffFilename)
	handoff, err := readJSONObject(handoffPath)
	if err != nil {
		return blockedEnvelope("implementation handoff is unavailable", err.Error())
	}
	reviewSHA := optionalFileSHA256(filepath.Join(feature.abs, reviewStateFilename))
	handoffSHA := optionalFileSHA256(handoffPath)
	statePath := filepath.Join(feature.abs, humanAcceptanceFilename)
	release, lockEnv, locked := acquireReviewAcceptLock(filepath.Join(feature.abs, ".human-acceptance.lock"))
	if !locked {
		return lockEnv
	}
	defer release()
	if existing, err := readJSONObject(statePath); err == nil {
		if source, ok := existing["source"].(map[string]any); ok &&
			stringField(source, "review_state_sha256") == reviewSHA &&
			stringField(source, "implementation_handoff_sha256") == handoffSHA {
			env := NewEnvelope("ok", "human acceptance state is already prepared")
			env.Data = existing
			env.ShowArgv = acceptShowArgv(feature.rel)
			env.NextArgv = []string{"specify-runtime", "accept", "validate", "--feature-dir", feature.rel, "--format", "json"}
			return env
		}
		return blockedEnvelope("existing human acceptance state is stale", "preserve existing human-acceptance.json before restarting acceptance")
	}
	state := newHumanAcceptanceState(feature, handoff, reviewValidation.state, handoffSHA, reviewSHA)
	if err := writeReviewAcceptJSONAtomic(statePath, state); err != nil {
		return errorEnvelope("failed to write human acceptance state", err)
	}
	env = NewEnvelope("ok", "human acceptance state prepared")
	env.Data = state
	env.ShowArgv = acceptShowArgv(feature.rel)
	env.NextArgv = []string{"specify-runtime", "accept", "validate", "--feature-dir", feature.rel, "--format", "json"}
	return env
}

func (service reviewAcceptService) validateHumanAcceptanceEnvelope(featureDir string) Envelope {
	_, feature, env, ok := service.resolveFeature(featureDir)
	if !ok {
		return env
	}
	result := service.validateHumanAcceptance(feature)
	env = NewEnvelope("ok", "human acceptance validation completed")
	env.Data["valid"] = result.valid
	env.Data["accepted"] = result.accepted
	env.Data["stale"] = result.stale
	env.Data["errors"] = result.errors
	env.Data["finding_routes"] = result.findingRoutes
	env.Data["next_command"] = result.nextCommand
	env.Data["state_path"] = filepath.Join(feature.rel, humanAcceptanceFilename)
	env.Data["state"] = result.state
	env.ShowArgv = acceptShowArgv(feature.rel)
	return env
}

func (service reviewAcceptService) routeHumanAcceptanceRepair(request routeHumanAcceptanceRepairRequest) Envelope {
	root, feature, env, ok := service.resolveFeature(request.featureDir)
	if !ok {
		return env
	}
	route := strings.TrimSpace(request.route)
	findingID := strings.TrimSpace(request.findingID)
	if findingID == "" {
		return usageEnvelope("accept route-repair requires --finding-id")
	}
	if route != "sp-review" && route != "spx-review" && route != "human-action" {
		return usageEnvelope("accept route-repair --route must be sp-review, spx-review, or human-action")
	}
	if len(nonEmptyStrings(request.evidence)) == 0 {
		return usageEnvelope("accept route-repair requires at least one --evidence")
	}
	statePath := filepath.Join(feature.abs, humanAcceptanceFilename)
	release, lockEnv, locked := acquireReviewAcceptLock(filepath.Join(feature.abs, ".human-acceptance.lock"))
	if !locked {
		return lockEnv
	}
	defer release()
	state, err := readJSONObject(statePath)
	if err != nil {
		return blockedEnvelope("human acceptance state is unavailable", err.Error())
	}
	if state["status"] != "rejected" && state["status"] != "blocked" {
		return blockedEnvelope("acceptance repair requires rejected or blocked status", "human-acceptance.json status must be rejected or blocked")
	}
	if !hasOpenFindingRoute(state, findingID, route) {
		return blockedEnvelope("acceptance finding route is unavailable", "named finding must be open and routed to the requested command")
	}
	if route == "human-action" {
		env := NewEnvelope("blocked", "acceptance finding requires human action")
		env.Blockers = append(env.Blockers, valueOr(request.humanActionReason, "complete the named human action before accepting"))
		env.Data["finding_id"] = findingID
		env.Data["route"] = route
		env.ShowArgv = acceptShowArgv(feature.rel)
		return env
	}
	backupPath := filepath.Join(feature.abs, humanAcceptanceRepairBackupName)
	journalPath := filepath.Join(feature.abs, humanAcceptanceRepairJournalName)
	originalRaw, err := os.ReadFile(statePath)
	if err != nil {
		return blockedEnvelope("human acceptance state is unavailable", err.Error())
	}
	if err := atomicWriteFile(backupPath, originalRaw, 0o644); err != nil {
		return errorEnvelope("failed to write acceptance repair backup", err)
	}
	state["status"] = "draft"
	state["repair_resume"] = map[string]any{
		"finding_id":        findingID,
		"route":             route,
		"target_stage":      "review",
		"expected_revision": request.expectedRevision,
		"evidence":          nonEmptyStrings(request.evidence),
	}
	state["repair_history"] = appendAny(state["repair_history"], map[string]any{
		"finding_id": findingID,
		"route":      route,
		"target":     "review",
	})
	state["overall"] = map[string]any{
		"verdict":      "pending",
		"next_command": route,
	}
	mutatedRaw, err := json.MarshalIndent(state, "", "  ")
	if err != nil {
		return errorEnvelope("failed to encode invalidated acceptance", err)
	}
	mutatedRaw = append(mutatedRaw, '\n')
	if err := atomicWriteFile(statePath, mutatedRaw, 0o644); err != nil {
		return errorEnvelope("failed to invalidate acceptance state", err)
	}
	invalidatedSHA := fmt.Sprintf("%x", sha256.Sum256(mutatedRaw))
	journal := map[string]any{
		"version":                       1,
		"phase":                         "acceptance-invalidated",
		"finding_id":                    findingID,
		"route":                         route,
		"target_stage":                  "review",
		"expected_revision":             request.expectedRevision,
		"invalidated_acceptance_sha256": invalidatedSHA,
		"acceptance_file":               humanAcceptanceFilename,
		"backup_file":                   humanAcceptanceRepairBackupName,
	}
	if err := writeReviewAcceptJSONAtomic(journalPath, journal); err != nil {
		return errorEnvelope("failed to write acceptance repair journal", err)
	}
	workflow := NewWorkflowService(root).Reopen(WorkflowReopenRequest{
		FeatureDir:       feature.rel,
		To:               "review",
		ExpectedRevision: request.expectedRevision,
		RepairRoute:      route,
		FindingID:        findingID,
		Evidence:         nonEmptyStrings(request.evidence),
	})
	workflow.Data["acceptance_state_path"] = filepath.Join(feature.rel, humanAcceptanceFilename)
	workflow.Data["acceptance_status"] = "draft"
	workflow.Data["repair_handoff_command"] = route
	workflow.Data["owning_stage_command"] = "review"
	workflow.Data["acceptance_return_argv"] = []string{"specify-runtime", "accept", "prepare", "--feature-dir", feature.rel, "--format", "json"}
	return workflow
}

func (service reviewAcceptService) closeoutHumanAcceptance(featureDir string, expectedRevision int) Envelope {
	root, feature, env, ok := service.resolveFeature(featureDir)
	if !ok {
		return env
	}
	workflow := NewWorkflowService(root).Show(WorkflowShowRequest{FeatureDir: feature.rel})
	if workflow.Status != "ok" {
		return workflow
	}
	if stage, _ := workflow.Data["stage"].(string); stage != "accept" {
		return blockedEnvelope("accept closeout requires accept workflow stage", "workflow stage must be accept")
	}
	if revision, ok := jsonInteger(workflow.Data["revision"]); !ok || revision != expectedRevision {
		return blockedEnvelope("accept closeout revision mismatch", "expected revision does not match workflow revision")
	}
	result := service.validateHumanAcceptance(feature)
	if !result.valid {
		env := NewEnvelope("blocked", "human acceptance closeout blocked")
		env.Blockers = append(env.Blockers, strings.Join(result.errors, "; "))
		env.Data["valid"] = false
		env.Data["accepted"] = result.accepted
		env.Data["stale"] = result.stale
		env.Data["finding_routes"] = result.findingRoutes
		env.Data["next_command"] = result.nextCommand
		env.ShowArgv = acceptShowArgv(feature.rel)
		env.NextArgv = []string{"specify-runtime", "accept", "validate", "--feature-dir", feature.rel, "--format", "json"}
		return env
	}
	env = NewEnvelope("ok", "human acceptance is accepted and ready for workflow closeout")
	env.Data["status"] = "accepted"
	env.Data["accepted"] = true
	env.Data["state_path"] = filepath.Join(feature.rel, humanAcceptanceFilename)
	env.ShowArgv = acceptShowArgv(feature.rel)
	env.NextArgv = workflowCloseoutArgv(reviewAcceptWorkflowFeature(feature), expectedRevision)
	return env
}

type reviewValidationResult struct {
	valid              bool
	fresh              bool
	errors             []string
	state              map[string]any
	currentFingerprint string
}

func (service reviewAcceptService) validateReview(feature reviewAcceptFeature) reviewValidationResult {
	statePath := filepath.Join(feature.abs, reviewStateFilename)
	handoffPath := filepath.Join(feature.abs, implementationHandoffFilename)
	state, err := readJSONObject(statePath)
	if err != nil {
		return reviewValidationResult{errors: []string{err.Error()}}
	}
	handoff, err := readJSONObject(handoffPath)
	if err != nil {
		return reviewValidationResult{state: state, errors: []string{err.Error()}}
	}
	handoffSHA := optionalFileSHA256(handoffPath)
	currentFingerprint := sourceTreeFingerprint(service.projectRoot, feature.abs)
	errors := []string{}
	if intField(state, "version") != reviewStateVersion {
		errors = append(errors, "review-state.json version must be 2")
	}
	source, _ := state["source"].(map[string]any)
	if source == nil {
		errors = append(errors, "review-state.json source is required")
	} else {
		if stringField(source, "implementation_handoff_sha256") != handoffSHA {
			errors = append(errors, "review source implementation_handoff_sha256 is stale")
		}
		expectedFingerprint := stringField(source, "implementation_fingerprint")
		if expectedFingerprint != "" && expectedFingerprint != currentFingerprint {
			errors = append(errors, "review source implementation_fingerprint is stale")
		}
		if handoffRevision, ok := jsonInteger(handoff["source_revision"]); ok && intField(source, "workflow_revision") != handoffRevision {
			errors = append(errors, "review source workflow_revision does not match implementation handoff")
		}
	}
	if state["status"] == "approved" {
		final, _ := state["final"].(map[string]any)
		if final == nil {
			errors = append(errors, "approved Review requires final verdict metadata")
		} else {
			for _, key := range []string{"verdict", "coverage_verdict", "repair_verdict", "integration_verdict"} {
				if stringField(final, key) != "pass" {
					errors = append(errors, "approved Review requires final."+key+"=pass")
				}
			}
			if joined, _ := final["all_packets_joined"].(bool); !joined {
				errors = append(errors, "approved Review requires all_packets_joined=true")
			}
		}
		if open := openFindings(state); len(open) > 0 {
			errors = append(errors, "approved Review cannot contain open findings")
		}
	}
	return reviewValidationResult{
		valid:              len(errors) == 0,
		fresh:              len(errors) == 0 || state["status"] != "approved",
		errors:             errors,
		state:              state,
		currentFingerprint: currentFingerprint,
	}
}

type acceptanceValidationResult struct {
	valid         bool
	accepted      bool
	stale         bool
	errors        []string
	findingRoutes []any
	nextCommand   string
	state         map[string]any
}

func (service reviewAcceptService) validateHumanAcceptance(feature reviewAcceptFeature) acceptanceValidationResult {
	statePath := filepath.Join(feature.abs, humanAcceptanceFilename)
	state, err := readJSONObject(statePath)
	if err != nil {
		return acceptanceValidationResult{errors: []string{err.Error()}, nextCommand: "accept prepare"}
	}
	errors := []string{}
	stale := false
	if intField(state, "version") != humanAcceptanceStateVersion {
		errors = append(errors, "human-acceptance.json version must be 2")
	}
	source, _ := state["source"].(map[string]any)
	if source == nil {
		errors = append(errors, "human-acceptance.json source is required")
	} else {
		if got, want := stringField(source, "review_state_sha256"), optionalFileSHA256(filepath.Join(feature.abs, reviewStateFilename)); got != "" && got != want {
			errors = append(errors, "human acceptance source review_state_sha256 is stale")
			stale = true
		}
		if got, want := stringField(source, "implementation_handoff_sha256"), optionalFileSHA256(filepath.Join(feature.abs, implementationHandoffFilename)); got != "" && got != want {
			errors = append(errors, "human acceptance source implementation_handoff_sha256 is stale")
			stale = true
		}
	}
	status, _ := state["status"].(string)
	if status != "accepted" {
		errors = append(errors, "human acceptance closeout requires status=accepted")
	}
	overall, _ := state["overall"].(map[string]any)
	if overall == nil || stringField(overall, "verdict") != "pass" || stringField(overall, "human_decision") != "accept" {
		errors = append(errors, "accepted human acceptance requires overall.verdict=pass and human_decision=accept")
	}
	if open := acceptanceOpenFindingRoutes(state); len(open) > 0 {
		errors = append(errors, "accepted human acceptance cannot contain open findings")
	}
	return acceptanceValidationResult{
		valid:         len(errors) == 0,
		accepted:      status == "accepted",
		stale:         stale,
		errors:        errors,
		findingRoutes: acceptanceOpenFindingRoutes(state),
		nextCommand:   acceptanceNextCommand(state),
		state:         state,
	}
}

func newHumanAcceptanceState(feature reviewAcceptFeature, handoff, reviewState map[string]any, handoffSHA, reviewSHA string) map[string]any {
	return map[string]any{
		"version":    humanAcceptanceStateVersion,
		"schema_ref": humanAcceptanceSchemaRef,
		"status":     "draft",
		"source": map[string]any{
			"implementation_handoff":        implementationHandoffFilename,
			"implementation_handoff_sha256": handoffSHA,
			"review_state":                  reviewStateFilename,
			"review_state_sha256":           reviewSHA,
			"feature_dir":                   feature.rel,
			"workflow_revision":             nestedAny(reviewState, "source", "workflow_revision"),
		},
		"orientation": map[string]any{
			"summary_path":    humanAcceptanceSummaryFilename,
			"summary_sha256":  optionalFileSHA256(filepath.Join(feature.abs, humanAcceptanceSummaryFilename)),
			"review_status":   reviewState["status"],
			"review_final":    cloneAny(reviewState["final"]),
			"runtime_targets": cloneAny(reviewState["reviewed_runtime_targets"]),
		},
		"acceptance_universe": map[string]any{
			"obligations": cloneAny(handoff["human_acceptance_obligations"]),
			"scenarios":   cloneAny(handoff["human_acceptance_scenarios"]),
		},
		"runtime_targets": cloneAny(reviewState["reviewed_runtime_targets"]),
		"scenarios":       cloneAny(handoff["human_acceptance_scenarios"]),
		"findings":        []any{},
		"repair_resume":   nil,
		"repair_history":  []any{},
		"overall": map[string]any{
			"verdict":        "pending",
			"human_decision": "pending",
			"next_command":   "accept validate",
		},
	}
}

func (service reviewAcceptService) resolveFeature(featureDir string) (string, reviewAcceptFeature, Envelope, bool) {
	var feature reviewAcceptFeature
	root, err := filepath.Abs(service.projectRoot)
	if err != nil {
		return "", feature, errorEnvelope("project root is invalid", err), false
	}
	root, err = filepath.EvalSymlinks(root)
	if err != nil {
		return "", feature, errorEnvelope("project root is invalid", err), false
	}
	requested := strings.TrimSpace(featureDir)
	if requested == "" {
		return "", feature, usageEnvelope("--feature-dir is required"), false
	}
	if filepath.IsAbs(requested) || filepath.VolumeName(requested) != "" {
		requested, err = filepath.Abs(requested)
		if err != nil {
			return "", feature, errorEnvelope("feature directory is invalid", err), false
		}
	} else {
		requested = filepath.Join(root, filepath.FromSlash(requested))
	}
	requested = filepath.Clean(requested)
	rel, err := filepath.Rel(root, requested)
	if err != nil || rel == "." || rel == ".." || strings.HasPrefix(rel, ".."+string(filepath.Separator)) {
		return "", feature, blockedEnvelope("feature directory is outside project root", "feature-dir must resolve inside project root"), false
	}
	secure, err := secureProjectPath(root, filepath.ToSlash(rel))
	if err != nil {
		return "", feature, blockedEnvelope("feature directory failed path safety check", err.Error()), false
	}
	if !sameFilesystemPath(secure, requested) {
		return "", feature, blockedEnvelope("feature directory is not canonical", "feature-dir must resolve to the canonical project path"), false
	}
	info, err := os.Stat(secure)
	if err != nil {
		return "", feature, blockedEnvelope("feature directory is unavailable", err.Error()), false
	}
	if !info.IsDir() {
		return "", feature, blockedEnvelope("feature path is not a directory", "feature-dir must be a directory"), false
	}
	feature.id = filepath.Base(secure)
	feature.abs = secure
	feature.rel = filepath.ToSlash(rel)
	return root, feature, Envelope{}, true
}

func reviewAcceptWorkflowFeature(feature reviewAcceptFeature) workflowFeature {
	return workflowFeature{ID: feature.id, Abs: feature.abs, Rel: feature.rel}
}

func reviewShowArgv(featureRel string) []string {
	return []string{"specify-runtime", "review", "resume-audit", "--feature-dir", featureRel, "--format", "json"}
}

func acceptShowArgv(featureRel string) []string {
	return []string{"specify-runtime", "accept", "validate", "--feature-dir", featureRel, "--format", "json"}
}

func intOption(args []string, name string) (int, bool) {
	raw := optionValue(args, name, "")
	if raw == "" {
		return 0, false
	}
	value, err := strconv.Atoi(raw)
	return value, err == nil
}

func usageEnvelope(message string) Envelope {
	return NewEnvelope("usage-error", message)
}

func blockedEnvelope(summary, blocker string) Envelope {
	env := NewEnvelope("blocked", summary)
	if strings.TrimSpace(blocker) != "" {
		env.Blockers = append(env.Blockers, blocker)
	}
	return env
}

func errorEnvelope(summary string, err error) Envelope {
	env := NewEnvelope("error", summary)
	if err != nil {
		env.Blockers = append(env.Blockers, err.Error())
	}
	return env
}

func acquireReviewAcceptLock(path string) (func(), Envelope, bool) {
	release, err := filelock.Acquire(path)
	if err != nil {
		return nil, errorEnvelope("failed to acquire state lock", err), false
	}
	return release, Envelope{}, true
}

func readJSONObject(path string) (map[string]any, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var payload map[string]any
	if err := json.Unmarshal(raw, &payload); err != nil {
		return nil, err
	}
	if payload == nil {
		return nil, fmt.Errorf("%s must contain a JSON object", filepath.Base(path))
	}
	return payload, nil
}

func writeReviewAcceptJSONAtomic(path string, payload any) error {
	raw, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		return err
	}
	raw = append(raw, '\n')
	return atomicWriteFile(path, raw, 0o644)
}

func fileSHA256(path string) (string, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return "", err
	}
	return fmt.Sprintf("%x", sha256.Sum256(raw)), nil
}

func optionalFileSHA256(path string) string {
	digest, err := fileSHA256(path)
	if err != nil {
		return ""
	}
	return digest
}

func sourceTreeFingerprint(projectRoot, featureAbs string) string {
	reviewOwned := map[string]bool{
		reviewStateFilename:              true,
		humanAcceptanceFilename:          true,
		humanAcceptanceRepairJournalName: true,
		humanAcceptanceRepairBackupName:  true,
		".review-state.lock":             true,
		".human-acceptance.lock":         true,
	}
	h := sha256.New()
	_ = filepath.WalkDir(featureAbs, func(path string, d os.DirEntry, err error) error {
		if err != nil || d.IsDir() {
			return nil
		}
		if reviewOwned[filepath.Base(path)] {
			return nil
		}
		rel, err := filepath.Rel(projectRoot, path)
		if err != nil {
			return nil
		}
		raw, err := os.ReadFile(path)
		if err != nil {
			return nil
		}
		_, _ = h.Write([]byte(filepath.ToSlash(rel)))
		_, _ = h.Write([]byte{0})
		_, _ = h.Write(raw)
		_, _ = h.Write([]byte{0})
		return nil
	})
	return fmt.Sprintf("%x", h.Sum(nil))
}

func cloneAny(value any) any {
	if value == nil {
		return []any{}
	}
	raw, err := json.Marshal(value)
	if err != nil {
		return value
	}
	var out any
	if err := json.Unmarshal(raw, &out); err != nil {
		return value
	}
	return out
}

func valueOr(value any, fallback string) any {
	if text, ok := value.(string); ok && strings.TrimSpace(text) != "" {
		return text
	}
	return fallback
}

func stringField(payload map[string]any, key string) string {
	if payload == nil {
		return ""
	}
	text, _ := payload[key].(string)
	return strings.TrimSpace(text)
}

func intField(payload map[string]any, key string) int {
	value, ok := jsonInteger(payload[key])
	if !ok {
		return 0
	}
	return value
}

func nestedAny(payload map[string]any, keys ...string) any {
	var cur any = payload
	for _, key := range keys {
		obj, ok := cur.(map[string]any)
		if !ok {
			return nil
		}
		cur = obj[key]
	}
	return cur
}

func nestedString(payload map[string]any, keys ...string) string {
	value, _ := nestedAny(payload, keys...).(string)
	return strings.TrimSpace(value)
}

func appendAny(existing any, item any) []any {
	if list, ok := existing.([]any); ok {
		return append(list, item)
	}
	return []any{item}
}

func nonEmptyStrings(values []string) []string {
	out := []string{}
	for _, value := range values {
		if trimmed := strings.TrimSpace(value); trimmed != "" {
			out = append(out, trimmed)
		}
	}
	return out
}

func openFindings(state map[string]any) []any {
	findings, _ := state["findings"].([]any)
	open := []any{}
	for _, item := range findings {
		finding, _ := item.(map[string]any)
		if stringField(finding, "status") == "open" {
			open = append(open, item)
		}
	}
	return open
}

func acceptanceOpenFindingRoutes(state map[string]any) []any {
	findings, _ := state["findings"].([]any)
	routes := []any{}
	for _, item := range findings {
		finding, _ := item.(map[string]any)
		if stringField(finding, "status") == "open" {
			routes = append(routes, map[string]any{
				"id":     stringField(finding, "id"),
				"route":  stringField(finding, "route"),
				"status": "open",
			})
		}
	}
	return routes
}

func hasOpenFindingRoute(state map[string]any, findingID, route string) bool {
	findings, _ := state["findings"].([]any)
	for _, item := range findings {
		finding, _ := item.(map[string]any)
		if stringField(finding, "id") == findingID && stringField(finding, "route") == route && stringField(finding, "status") == "open" {
			return true
		}
	}
	return false
}

func acceptanceNextCommand(state map[string]any) string {
	if routes := acceptanceOpenFindingRoutes(state); len(routes) > 0 {
		if first, ok := routes[0].(map[string]any); ok {
			if route := stringField(first, "route"); route != "" {
				return "accept route-repair --route " + route
			}
		}
	}
	if overall, ok := state["overall"].(map[string]any); ok {
		return stringField(overall, "next_command")
	}
	return "accept prepare"
}
