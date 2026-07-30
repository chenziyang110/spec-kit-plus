package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"reflect"
	"regexp"
	"slices"
	"sort"
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

var (
	reviewExceptionIDRE                = regexp.MustCompile(`^REX-[0-9a-f]{12}$`)
	reviewSHA256RE                     = regexp.MustCompile(`^[0-9a-f]{64}$`)
	reviewExceptionConfirmationSources = map[string]bool{
		"human-reply": true, "interactive-input": true, "attached-evidence": true,
	}
	reviewExceptionInputFields = []string{
		"kind", "scenario_ids", "obligation_ids", "required_resource",
		"unavailable_evidence_refs", "attempted_alternatives", "claims_withheld",
		"residual_risk", "risk_severity",
	}
	reviewExceptionProposalFields = []string{
		"kind", "scenario_ids", "obligation_ids", "required_resource",
		"unavailable_evidence_refs", "unavailable_evidence_sha256",
		"attempted_alternatives", "claims_withheld", "residual_risk", "risk_severity",
		"review_cycle_id", "implementation_fingerprint",
	}
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
		env = service.prepareReview(optionValue(args, "--feature-dir", ""), expected, hasFlag(args, "--restart-stale"))
	case "resume-audit":
		env = service.resumeReviewAudit(optionValue(args, "--feature-dir", ""))
	case "validate":
		env = service.validateReviewEnvelope(optionValue(args, "--feature-dir", ""))
	case "exception-propose":
		proposal, err := readAgentJSONObject(args, service.projectRoot, "review exception-propose")
		if err != nil {
			return writeEnvelope(stdout, usageEnvelope(err.Error()))
		}
		env = service.proposeReviewException(optionValue(args, "--feature-dir", ""), proposal)
	case "exception-confirm":
		env = service.confirmReviewException(
			optionValue(args, "--feature-dir", ""),
			optionValue(args, "--exception-id", ""),
			optionValue(args, "--proposal-sha256", ""),
			optionValue(args, "--confirmation-source", ""),
			optionValue(args, "--statement", ""),
		)
	case "target-bind":
		target, err := readAgentJSONObject(args, service.projectRoot, "review target-bind")
		if err != nil {
			return writeEnvelope(stdout, usageEnvelope(err.Error()))
		}
		env = service.bindReviewRuntimeTarget(optionValue(args, "--feature-dir", ""), target)
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

func (service reviewAcceptService) prepareReview(featureDir string, expectedRevision int, restartStale bool) Envelope {
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
	lastReopen, _ := workflow.Data["last_reopen"].(map[string]any)
	isAcceptanceRepair := lastReopen != nil &&
		stringField(lastReopen, "source_stage") == "accept" &&
		stringField(lastReopen, "target_stage") == "review"
	handoffPath := filepath.Join(feature.abs, implementationHandoffFilename)
	handoff, err := readJSONObject(handoffPath)
	if err != nil {
		return blockedEnvelope("implementation handoff is unavailable", err.Error())
	}
	sourceRevision, ok := jsonInteger(handoff["source_revision"])
	if !ok || (!isAcceptanceRepair && sourceRevision != expectedRevision) {
		return blockedEnvelope("implementation handoff revision mismatch", "implementation-handoff.json source_revision must match expected revision")
	}
	handoffSHA, err := fileSHA256(handoffPath)
	if err != nil {
		return blockedEnvelope("implementation handoff is unavailable", err.Error())
	}
	if err := validateCanonicalImplementationHandoff(root, feature.abs, handoff); err != nil {
		return blockedEnvelope("implementation handoff contract is invalid", err.Error())
	}
	fingerprint := stringField(handoff, "implementation_fingerprint")
	if fingerprint != sourceTreeFingerprint(root, feature.abs) {
		return blockedEnvelope("implementation handoff fingerprint is stale", "implementation-handoff.json does not describe the current Git working tree")
	}
	statePath := filepath.Join(feature.abs, reviewStateFilename)
	release, lockEnv, locked := acquireReviewAcceptLock(filepath.Join(feature.abs, ".review-state.lock"))
	if !locked {
		return lockEnv
	}
	defer release()
	previousRaw, readErr := os.ReadFile(statePath)
	if readErr == nil {
		var existing map[string]any
		decodeErr := json.Unmarshal(previousRaw, &existing)
		if decodeErr != nil || existing == nil {
			if isAcceptanceRepair || !restartStale {
				return blockedEnvelope("existing review state is malformed", "preserve review-state.json and rerun review prepare with --restart-stale: "+decodeErrorText(decodeErr))
			}
			return service.restartReviewState(feature, handoff, expectedRevision, handoffSHA, fingerprint, previousRaw, nil, decodeErrorText(decodeErr))
		}
		source, _ := existing["source"].(map[string]any)
		if isAcceptanceRepair {
			findingID := stringField(lastReopen, "finding_id")
			if source != nil &&
				stringField(source, "implementation_handoff_sha256") == handoffSHA &&
				intField(source, "workflow_revision") == expectedRevision &&
				stringField(source, "acceptance_finding_id") == findingID {
				return preparedReviewEnvelope(feature.rel, existing, "acceptance repair Review cycle is already prepared")
			}
			if existing["status"] != "approved" {
				return blockedEnvelope("acceptance repair requires the previous Review to be approved", "preserve the previous approved review-state.json")
			}
			if source == nil || stringField(source, "implementation_handoff_sha256") != handoffSHA {
				return blockedEnvelope("acceptance repair implementation handoff is stale", "restore the handoff reviewed by the previous approved Review")
			}
			previousDigest := fmt.Sprintf("%x", sha256.Sum256(previousRaw))
			context, contextErr := service.acceptanceRepairContext(feature, lastReopen, existing, previousDigest)
			if contextErr != nil {
				return blockedEnvelope("acceptance repair context is invalid", contextErr.Error())
			}
			previousCycle := intField(source, "review_cycle")
			if previousCycle < 1 {
				previousCycle = 1
			}
			rounds := clonedReviewRounds(existing)
			rounds = append(rounds, map[string]any{
				"review_cycle":             previousCycle,
				"review_state_sha256":      previousDigest,
				"reviewed_snapshot_sha256": nestedString(existing, "final", "reviewed_snapshot_sha256"),
				"status":                   "superseded-by-acceptance-repair",
				"acceptance_finding_id":    context["finding_id"],
			})
			state := newReviewState(feature, handoff, expectedRevision, handoffSHA, fingerprint, previousCycle+1, previousDigest, "", rounds, context)
			if err := writeReviewAcceptJSONAtomic(statePath, state); err != nil {
				return errorEnvelope("failed to write acceptance repair review state", err)
			}
			return preparedReviewEnvelope(feature.rel, state, "acceptance repair Review cycle prepared")
		}
		if source != nil &&
			stringField(source, "implementation_handoff_sha256") == handoffSHA &&
			intField(source, "workflow_revision") == expectedRevision && !restartStale {
			if upgradeReviewExceptionContract(existing) {
				if err := writeReviewAcceptJSONAtomic(statePath, existing); err != nil {
					return errorEnvelope("failed to upgrade review state", err)
				}
			}
			return preparedReviewEnvelope(feature.rel, existing, "system review state is already prepared")
		}
		if !restartStale {
			return blockedEnvelope("existing review state is stale", "preserve review-state.json and rerun review prepare with --restart-stale")
		}
		return service.restartReviewState(feature, handoff, expectedRevision, handoffSHA, fingerprint, previousRaw, existing, "")
	}
	if !os.IsNotExist(readErr) {
		return blockedEnvelope("review state cannot be inspected", readErr.Error())
	}
	if isAcceptanceRepair {
		return blockedEnvelope("acceptance repair is missing the previous Review", "restore the previous approved review-state.json")
	}
	state := newReviewState(feature, handoff, expectedRevision, handoffSHA, fingerprint, 1, "", "", nil, nil)
	if err := writeReviewAcceptJSONAtomic(statePath, state); err != nil {
		return errorEnvelope("failed to write review state", err)
	}
	return preparedReviewEnvelope(feature.rel, state, "system review state prepared")
}

func decodeErrorText(err error) string {
	if err == nil {
		return "review-state.json must contain a JSON object"
	}
	return err.Error()
}

func preparedReviewEnvelope(featureRel string, state map[string]any, summary string) Envelope {
	env := NewEnvelope("ok", summary)
	env.Data = state
	env.ShowArgv = reviewShowArgv(featureRel)
	env.NextArgv = []string{"specify-runtime", "review", "validate", "--feature-dir", featureRel, "--format", "json"}
	return env
}

var reviewRuntimeTargetIDRE = regexp.MustCompile(`^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$`)

var reviewRuntimeTargetInputFields = map[string]bool{
	"id": true, "mode": true, "entrypoint_id": true,
	"environment_ref": true, "instance_ref": true, "configuration_ref": true,
	"artifact_ref": true, "artifact_sha256": true, "deployment_id": true,
	"observed_version": true, "test_data_refs": true,
	"ready_evidence_refs": true, "review_scenario_ids": true,
}

var reviewRuntimeTargetContractFields = map[string]bool{
	"id": true, "mode": true, "status": true, "entrypoint_id": true,
	"environment_ref": true, "instance_ref": true, "configuration_ref": true,
	"reviewed_snapshot_sha256": true, "artifact_ref": true, "artifact_sha256": true,
	"deployment_id": true, "observed_version": true, "test_data_refs": true,
	"ready_evidence_refs": true, "review_scenario_ids": true,
	"identity_evidence_ref": true, "identity_evidence_sha256": true,
}

var reviewRuntimeTargetBaseFields = []string{
	"id", "mode", "status", "entrypoint_id", "environment_ref", "instance_ref",
	"configuration_ref", "reviewed_snapshot_sha256", "artifact_ref", "artifact_sha256",
	"deployment_id", "observed_version", "test_data_refs", "ready_evidence_refs",
	"review_scenario_ids",
}

func (service reviewAcceptService) bindReviewRuntimeTarget(featureDir string, raw map[string]any) Envelope {
	root, feature, env, ok := service.resolveFeature(featureDir)
	if !ok {
		return env
	}
	workflow := NewWorkflowService(root).Show(WorkflowShowRequest{FeatureDir: feature.rel})
	if workflow.Status != "ok" || stringField(workflow.Data, "stage") != "review" || stringField(workflow.Data, "status") != "active" {
		return blockedEnvelope("review target binding requires active Review", "workflow stage must be active review")
	}
	release, lockEnv, locked := acquireReviewAcceptLock(filepath.Join(feature.abs, ".review-state.lock"))
	if !locked {
		return lockEnv
	}
	defer release()

	statePath := filepath.Join(feature.abs, reviewStateFilename)
	state, err := readJSONObject(statePath)
	if err != nil {
		return blockedEnvelope("review state is unavailable", err.Error())
	}
	if stringField(state, "status") == "approved" {
		return blockedEnvelope("approved Review targets are immutable", "reopen or restart Review before changing runtime targets")
	}
	fingerprint := sourceTreeFingerprint(root, feature.abs)
	source, _ := state["source"].(map[string]any)
	if source == nil || stringField(source, "implementation_fingerprint") != fingerprint {
		return blockedEnvelope("review runtime target binding is stale", "restart Review against the current implementation snapshot before binding targets")
	}
	target, err := normalizeReviewRuntimeTarget(feature, state, raw, fingerprint)
	if err != nil {
		return blockedEnvelope("review runtime target is invalid", err.Error())
	}
	cycle := intField(source, "review_cycle")
	if cycle < 1 {
		return blockedEnvelope("review runtime target is invalid", "review source review_cycle must be a positive integer")
	}
	identityRef := reviewRuntimeTargetIdentityRef(stringField(target, "id"), cycle)
	identity := reviewRuntimeIdentityClaim(target)
	identityRaw, err := marshalReviewAcceptJSON(identity)
	if err != nil {
		return errorEnvelope("review runtime target identity cannot be rendered", err)
	}
	target["identity_evidence_ref"] = identityRef
	target["identity_evidence_sha256"] = fileContentSHA256(identityRaw)

	targets, _ := state["reviewed_runtime_targets"].([]any)
	updated := make([]any, 0, len(targets)+1)
	replaced := false
	for _, value := range targets {
		existing, ok := value.(map[string]any)
		if ok && stringField(existing, "id") == stringField(target, "id") {
			updated = append(updated, target)
			replaced = true
			continue
		}
		updated = append(updated, cloneAny(value))
	}
	if !replaced {
		updated = append(updated, target)
	}
	state["reviewed_runtime_targets"] = updated
	final, _ := state["final"].(map[string]any)
	if final == nil {
		final = map[string]any{}
		state["final"] = final
	}
	final["reviewed_snapshot_sha256"] = fingerprint
	final["runtime_targets_sha256"] = reviewRuntimeTargetsSHA256(updated)
	stateRaw, err := marshalReviewAcceptJSON(state)
	if err != nil {
		return errorEnvelope("review state cannot be rendered", err)
	}
	identityPath, err := secureProjectPath(root, filepath.ToSlash(filepath.Join(feature.rel, filepath.FromSlash(identityRef))))
	if err != nil {
		return blockedEnvelope("review runtime identity path is unsafe", err.Error())
	}
	receipt, err := applyFileTransaction(root, "review-target-bind", []fileTransactionUpdate{
		{Path: identityPath, Content: identityRaw, Perm: 0o644},
		{Path: statePath, Content: stateRaw, Perm: 0o644},
	})
	if err != nil {
		return errorEnvelope("review runtime target cannot be bound atomically", err)
	}
	env = NewEnvelope("ok", "review runtime target bound")
	env.Data["identity_evidence_ref"] = identityRef
	env.Data["identity_evidence_sha256"] = target["identity_evidence_sha256"]
	env.Data["runtime_targets_sha256"] = final["runtime_targets_sha256"]
	env.Data["target"] = target
	env.Data["transaction_receipt_ref"] = receipt.ReceiptRef
	env.ShowArgv = reviewShowArgv(feature.rel)
	env.NextArgv = []string{"specify-runtime", "review", "validate", "--feature-dir", feature.rel, "--format", "json"}
	return env
}

func normalizeReviewRuntimeTarget(feature reviewAcceptFeature, state, raw map[string]any, fingerprint string) (map[string]any, error) {
	for field := range raw {
		if !reviewRuntimeTargetInputFields[field] {
			return nil, fmt.Errorf("unsupported runtime target field %q", field)
		}
	}
	targetID := stringField(raw, "id")
	if !reviewRuntimeTargetIDRE.MatchString(targetID) {
		return nil, errors.New("id must use 1-128 safe alphanumeric, dot, underscore, or dash characters")
	}
	mode := stringField(raw, "mode")
	if !slices.Contains([]string{"source", "build", "deployment", "device"}, mode) {
		return nil, errors.New("mode must be source, build, deployment, or device")
	}
	entrypointID := stringField(raw, "entrypoint_id")
	if findObjectByID(state["entrypoints"], entrypointID) == nil {
		return nil, errors.New("entrypoint_id must name an official Review entrypoint")
	}
	for _, field := range []string{"environment_ref", "instance_ref", "configuration_ref"} {
		if stringField(raw, field) == "" {
			return nil, fmt.Errorf("%s is required", field)
		}
	}
	testDataRefs, err := optionalReviewStringList(raw, "test_data_refs", false)
	if err != nil {
		return nil, err
	}
	readyEvidenceRefs, err := optionalReviewStringList(raw, "ready_evidence_refs", true)
	if err != nil {
		return nil, err
	}
	reviewScenarioIDs, err := optionalReviewStringList(raw, "review_scenario_ids", true)
	if err != nil {
		return nil, err
	}
	cycle := 0
	if source, ok := state["source"].(map[string]any); ok {
		cycle = intField(source, "review_cycle")
	}
	linkedEvidence := map[string]bool{}
	for _, scenarioID := range reviewScenarioIDs {
		scenario := findObjectByID(state["scenarios"], scenarioID)
		if scenario == nil {
			return nil, fmt.Errorf("review_scenario_ids references unknown scenario %s", scenarioID)
		}
		if stringField(scenario, "entrypoint_id") != entrypointID {
			return nil, fmt.Errorf("review scenario %s belongs to a different entrypoint", scenarioID)
		}
		for _, value := range listValue(scenario["evidence"]) {
			if item, ok := value.(map[string]any); ok {
				linkedEvidence[stringField(item, "path")] = true
			}
		}
	}
	for _, ref := range readyEvidenceRefs {
		if !linkedEvidence[ref] {
			return nil, fmt.Errorf("ready_evidence_refs must come from linked Review scenarios: %s", ref)
		}
		if _, err := reviewCycleEvidencePath(feature, ref, cycle); err != nil {
			return nil, err
		}
	}
	artifactRef := nullableReviewString(raw["artifact_ref"])
	artifactSHA := nullableReviewString(raw["artifact_sha256"])
	if mode == "build" || mode == "deployment" {
		if artifactRef == nil {
			return nil, fmt.Errorf("artifact_ref is required for %s targets", mode)
		}
		if artifactSHA == nil || !reviewSHA256RE.MatchString(*artifactSHA) {
			return nil, fmt.Errorf("artifact_sha256 must be a sha256 digest for %s targets", mode)
		}
		artifactPath, err := reviewImplementationArtifactPath(feature, *artifactRef)
		if err != nil {
			return nil, fmt.Errorf("artifact_ref is unsafe: %w", err)
		}
		if digest, err := fileSHA256(artifactPath); err != nil || digest != *artifactSHA {
			return nil, errors.New("artifact_sha256 must bind current artifact bytes")
		}
	}
	deploymentID := nullableReviewString(raw["deployment_id"])
	observedVersion := nullableReviewString(raw["observed_version"])
	if mode == "deployment" && (deploymentID == nil || observedVersion == nil) {
		return nil, errors.New("deployment targets require deployment_id and observed_version")
	}
	target := map[string]any{
		"id": targetID, "mode": mode, "status": "ready", "entrypoint_id": entrypointID,
		"environment_ref": stringField(raw, "environment_ref"), "instance_ref": stringField(raw, "instance_ref"),
		"configuration_ref": stringField(raw, "configuration_ref"), "reviewed_snapshot_sha256": fingerprint,
		"artifact_ref": nullableReviewStringValue(artifactRef), "artifact_sha256": nullableReviewStringValue(artifactSHA),
		"deployment_id": nullableReviewStringValue(deploymentID), "observed_version": nullableReviewStringValue(observedVersion),
		"test_data_refs":      stringSliceToAny(testDataRefs),
		"ready_evidence_refs": stringSliceToAny(readyEvidenceRefs), "review_scenario_ids": stringSliceToAny(reviewScenarioIDs),
	}
	return target, nil
}

func optionalReviewStringList(raw map[string]any, field string, required bool) ([]string, error) {
	value, exists := raw[field]
	if !exists {
		if required {
			return nil, fmt.Errorf("%s is required", field)
		}
		return []string{}, nil
	}
	return anyStringList(value, field, required)
}

func nullableReviewString(value any) *string {
	text, ok := value.(string)
	text = strings.TrimSpace(text)
	if !ok || text == "" {
		return nil
	}
	return &text
}

func nullableReviewStringValue(value *string) any {
	if value == nil {
		return nil
	}
	return *value
}

func reviewRuntimeTargetIdentityRef(targetID string, cycle int) string {
	root := "review-evidence"
	if cycle > 1 {
		root = filepath.ToSlash(filepath.Join(root, fmt.Sprintf("cycle-%d", cycle)))
	}
	return filepath.ToSlash(filepath.Join(root, "runtime-target-"+targetID+".identity.json"))
}

func reviewRuntimeIdentityClaim(target map[string]any) map[string]any {
	claim := map[string]any{}
	for _, field := range []string{
		"id", "mode", "entrypoint_id", "environment_ref", "instance_ref", "configuration_ref",
		"reviewed_snapshot_sha256", "artifact_ref", "artifact_sha256", "deployment_id",
		"observed_version", "review_scenario_ids", "ready_evidence_refs",
	} {
		if target[field] == nil {
			claim[field] = nil
		} else {
			claim[field] = cloneAny(target[field])
		}
	}
	return map[string]any{"version": 1, "status": "ready", "target": claim}
}

func reviewRuntimeTargetsSHA256(targets []any) string {
	return canonicalJSONSHA256(map[string]any{"reviewed_runtime_targets": targets})
}

func reviewFeatureRelativePath(feature reviewAcceptFeature, ref string) (string, error) {
	if err := validateSafeRelativeSlashPath(ref); err != nil {
		return "", err
	}
	path, err := secureProjectPath(feature.abs, ref)
	if err != nil {
		return "", err
	}
	info, err := os.Stat(path)
	if err != nil || info.IsDir() {
		if err == nil {
			err = errors.New("path is a directory")
		}
		return "", err
	}
	return path, nil
}

func reviewImplementationArtifactPath(feature reviewAcceptFeature, ref string) (string, error) {
	path, err := reviewFeatureRelativePath(feature, ref)
	if err != nil {
		return "", err
	}
	normalized := filepath.ToSlash(strings.TrimSpace(ref))
	excludedNames := map[string]bool{
		implementationHandoffFilename: true, reviewStateFilename: true,
		"implementation-summary.md": true, humanAcceptanceFilename: true,
		".human-acceptance.lock": true, humanAcceptanceRepairJournalName: true,
		humanAcceptanceRepairBackupName: true, ".human-acceptance-terminal.json": true,
		"workflow.json": true, "workflow-state.md": true,
		"implementation-review/validation-runs.json": true,
	}
	excludedPrefixes := []string{
		"review-evidence/", "review-results/", "review-history/",
		"implementation-review/deferrals/", "implementation-review/validation-evidence/",
	}
	if excludedNames[normalized] || strings.HasSuffix(normalized, ".lock") {
		return "", errors.New("artifact is excluded from the implementation snapshot")
	}
	for _, prefix := range excludedPrefixes {
		if strings.HasPrefix(normalized, prefix) {
			return "", errors.New("artifact is excluded from the implementation snapshot")
		}
	}
	return path, nil
}

func reviewCycleEvidencePath(feature reviewAcceptFeature, ref string, cycle int) (string, error) {
	path, err := reviewFeatureRelativePath(feature, ref)
	if err != nil {
		return "", fmt.Errorf("Review evidence file is missing or unsafe: %s", ref)
	}
	prefix := "review-evidence/"
	if cycle > 1 {
		prefix = fmt.Sprintf("review-evidence/cycle-%d/", cycle)
	}
	if !strings.HasPrefix(ref, prefix) {
		return "", errors.New("Review evidence must belong to the current Review cycle")
	}
	if cycle == 1 {
		remainder := strings.TrimPrefix(ref, prefix)
		first := strings.SplitN(remainder, "/", 2)[0]
		if regexp.MustCompile(`^cycle-[0-9]+$`).MatchString(first) {
			return "", errors.New("Review evidence must belong to the current Review cycle")
		}
	}
	return path, nil
}

func validateReviewRuntimeTargets(feature reviewAcceptFeature, state map[string]any, expectedSnapshot string) ([]string, bool) {
	errorsOut := []string{}
	fresh := true
	rawTargets, ok := state["reviewed_runtime_targets"].([]any)
	if !ok {
		return []string{"reviewed_runtime_targets must be an array"}, fresh
	}
	status := stringField(state, "status")
	if status == "approved" && len(rawTargets) == 0 {
		errorsOut = append(errorsOut, "approved Review requires at least one reviewed runtime target")
	}
	source, _ := state["source"].(map[string]any)
	cycle := intField(source, "review_cycle")
	seen := map[string]bool{}
	targets := make([]map[string]any, 0, len(rawTargets))
	canonicalTargets := make([]any, 0, len(rawTargets))
	for index, value := range rawTargets {
		prefix := fmt.Sprintf("reviewed_runtime_targets[%d]", index)
		target, ok := value.(map[string]any)
		if !ok {
			errorsOut = append(errorsOut, prefix+" must be an object")
			continue
		}
		for field := range target {
			if !reviewRuntimeTargetContractFields[field] {
				errorsOut = append(errorsOut, fmt.Sprintf("%s contains unsupported field %q", prefix, field))
			}
		}
		targetID := stringField(target, "id")
		if targetID == "" || !reviewRuntimeTargetIDRE.MatchString(targetID) {
			errorsOut = append(errorsOut, prefix+".id is invalid")
		} else if seen[targetID] {
			errorsOut = append(errorsOut, "duplicate reviewed runtime target id: "+targetID)
		}
		seen[targetID] = true

		semantic := map[string]any{}
		for field := range reviewRuntimeTargetInputFields {
			if fieldValue, exists := target[field]; exists {
				semantic[field] = fieldValue
			}
		}
		expected, err := normalizeReviewRuntimeTarget(feature, state, semantic, expectedSnapshot)
		if err != nil {
			errorsOut = append(errorsOut, prefix+": "+err.Error())
		} else {
			for _, field := range reviewRuntimeTargetBaseFields {
				if !reflect.DeepEqual(target[field], expected[field]) {
					if field == "reviewed_snapshot_sha256" {
						fresh = false
					}
					errorsOut = append(errorsOut, fmt.Sprintf("%s.%s does not match the runtime-derived target contract", prefix, field))
				}
			}
		}

		expectedIdentityRef := reviewRuntimeTargetIdentityRef(targetID, cycle)
		identityRef := stringField(target, "identity_evidence_ref")
		if identityRef != expectedIdentityRef {
			errorsOut = append(errorsOut, prefix+".identity_evidence_ref must use the runtime-derived current-cycle path")
		} else {
			identityPath, pathErr := reviewCycleEvidencePath(feature, identityRef, cycle)
			if pathErr != nil {
				errorsOut = append(errorsOut, prefix+".identity_evidence_ref is invalid: "+pathErr.Error())
			} else {
				identitySHA := stringField(target, "identity_evidence_sha256")
				actualSHA, shaErr := fileSHA256(identityPath)
				if shaErr != nil || !reviewSHA256RE.MatchString(identitySHA) || identitySHA != actualSHA {
					errorsOut = append(errorsOut, prefix+".identity_evidence_sha256 must bind current identity evidence bytes")
				}
				identity, readErr := readJSONObject(identityPath)
				if readErr != nil {
					errorsOut = append(errorsOut, prefix+" identity evidence is invalid: "+readErr.Error())
				} else if !reflect.DeepEqual(identity, cloneAny(reviewRuntimeIdentityClaim(target))) {
					errorsOut = append(errorsOut, prefix+".identity_evidence_ref must exactly identify the reviewed runtime target")
				}
			}
		}
		targets = append(targets, target)
		canonicalTargets = append(canonicalTargets, reviewRuntimeTargetContract(target))
	}

	if status == "approved" {
		for _, value := range listValue(state["human_acceptance_scenarios"]) {
			scenario, ok := value.(map[string]any)
			if !ok || scenario["required"] != true {
				continue
			}
			linkedIDs, err := anyStringList(scenario["review_scenario_ids"], "review_scenario_ids", true)
			if err != nil {
				errorsOut = append(errorsOut, "required human acceptance scenario has invalid review_scenario_ids: "+stringField(scenario, "id"))
				continue
			}
			matching := 0
			for _, target := range targets {
				if stringField(target, "status") != "ready" || stringField(target, "entrypoint_id") != stringField(scenario, "entrypoint_id") {
					continue
				}
				targetIDs, err := anyStringList(target["review_scenario_ids"], "review_scenario_ids", true)
				targetIDSet := map[string]bool{}
				for _, targetID := range targetIDs {
					targetIDSet[targetID] = true
				}
				if err == nil && stringSetContainsAll(targetIDSet, linkedIDs) {
					matching++
				}
			}
			if matching != 1 {
				errorsOut = append(errorsOut, fmt.Sprintf("required human acceptance scenario %s requires exactly one reviewed runtime target", stringField(scenario, "id")))
			}
		}
	}
	if len(canonicalTargets) > 0 || status == "approved" {
		final, _ := state["final"].(map[string]any)
		if final == nil || stringField(final, "runtime_targets_sha256") != reviewRuntimeTargetsSHA256(canonicalTargets) {
			errorsOut = append(errorsOut, "final.runtime_targets_sha256 must match reviewed_runtime_targets")
		}
		if final == nil || stringField(final, "reviewed_snapshot_sha256") != expectedSnapshot {
			fresh = false
			errorsOut = append(errorsOut, "final.reviewed_snapshot_sha256 must match the current implementation snapshot")
		}
	}
	return errorsOut, fresh
}

func reviewRuntimeTargetContract(target map[string]any) map[string]any {
	contract := map[string]any{}
	for field := range reviewRuntimeTargetContractFields {
		if target[field] == nil {
			contract[field] = nil
		} else {
			contract[field] = cloneAny(target[field])
		}
	}
	return contract
}

func (service reviewAcceptService) restartReviewState(feature reviewAcceptFeature, handoff map[string]any, expectedRevision int, handoffSHA, fingerprint string, previousRaw []byte, existing map[string]any, restartError string) Envelope {
	previousDigest := fmt.Sprintf("%x", sha256.Sum256(previousRaw))
	historyRef := filepath.ToSlash(filepath.Join("review-history", "review-state-"+previousDigest+".json"))
	historyPath := filepath.Join(feature.abs, filepath.FromSlash(historyRef))
	if err := os.MkdirAll(filepath.Dir(historyPath), 0o755); err != nil {
		return errorEnvelope("failed to create review history", err)
	}
	if archived, err := os.ReadFile(historyPath); err == nil {
		if !bytes.Equal(archived, previousRaw) {
			return blockedEnvelope("review history digest collision", "preserve review-state.json and inspect review-history")
		}
	} else if !os.IsNotExist(err) {
		return errorEnvelope("failed to inspect review history", err)
	} else if err := atomicWriteFile(historyPath, previousRaw, 0o644); err != nil {
		return errorEnvelope("failed to archive stale review state", err)
	}
	previousCycle := 1
	if source, ok := existing["source"].(map[string]any); ok && intField(source, "review_cycle") >= 1 {
		previousCycle = intField(source, "review_cycle")
	}
	rounds := clonedReviewRounds(existing)
	archivedRound := map[string]any{
		"review_cycle":             previousCycle,
		"review_state_sha256":      previousDigest,
		"reviewed_snapshot_sha256": nestedString(existing, "final", "reviewed_snapshot_sha256"),
		"status":                   "restarted-stale",
		"history_ref":              historyRef,
	}
	if strings.TrimSpace(restartError) != "" {
		archivedRound["restart_error"] = restartError
	}
	rounds = append(rounds, archivedRound)
	state := newReviewState(feature, handoff, expectedRevision, handoffSHA, fingerprint, previousCycle+1, previousDigest, "stale-review-restart", rounds, nil)
	if err := writeReviewAcceptJSONAtomic(filepath.Join(feature.abs, reviewStateFilename), state); err != nil {
		return errorEnvelope("failed to write restarted review state", err)
	}
	env := preparedReviewEnvelope(feature.rel, state, "stale system review state was archived and restarted")
	env.Data["archived_review_state_ref"] = historyRef
	return env
}

func clonedReviewRounds(state map[string]any) []any {
	if state == nil {
		return []any{}
	}
	raw, ok := state["rounds"].([]any)
	if !ok {
		return []any{}
	}
	cloned, ok := cloneAny(raw).([]any)
	if !ok {
		return []any{}
	}
	return cloned
}

func validateCanonicalImplementationHandoff(projectRoot, featureAbs string, handoff map[string]any) error {
	if version, ok := jsonInteger(handoff["version"]); !ok || version != 1 {
		return errors.New("implementation-handoff.json version must be 1")
	}
	if handoff["status"] != "ready_for_review" || handoff["source_stage"] != "implement" {
		return errors.New("implementation-handoff.json must record status ready_for_review and source_stage implement")
	}
	if revision, ok := jsonInteger(handoff["source_revision"]); !ok || revision < 1 {
		return errors.New("implementation-handoff.json source_revision must be a positive integer")
	}
	for _, legacy := range []string{"entrypoints", "review_scenarios", "source_fingerprint", "implementation_snapshot_sha256", "fingerprint"} {
		if _, present := handoff[legacy]; present {
			return fmt.Errorf("implementation-handoff.json legacy field %s is not accepted", legacy)
		}
	}
	fingerprint := stringField(handoff, "implementation_fingerprint")
	if !reviewSHA256RE.MatchString(fingerprint) || handoff["fingerprint_algorithm"] != implementationFingerprintAlgorith {
		return errors.New("implementation-handoff.json requires a sha256 implementation_fingerprint using git-working-tree-v1")
	}
	officialEntrypoints, err := canonicalHandoffArray(handoff, "official_entrypoints", true)
	if err != nil {
		return err
	}
	_ = officialEntrypoints
	if _, err := canonicalHandoffArray(handoff, "system_review_scenarios", true); err != nil {
		return err
	}
	if _, err := canonicalHandoffArray(handoff, "review_obligations", false); err != nil {
		return err
	}
	humanObligations, err := canonicalHandoffArray(handoff, "human_acceptance_obligations", false)
	if err != nil {
		return err
	}
	humanScenarios, err := canonicalHandoffArray(handoff, "human_acceptance_scenarios", false)
	if err != nil {
		return err
	}
	if _, err := canonicalHandoffStringList(handoff, "acceptance_refs", true); err != nil {
		return err
	}
	if _, err := canonicalHandoffStringList(handoff, "task_ids", true); err != nil {
		return err
	}
	if _, err := canonicalHandoffStringList(handoff, "user_confirmed_deferral_refs", false); err != nil {
		return err
	}
	confirmedDeferrals, err := canonicalHandoffArray(handoff, "user_confirmed_deferrals", false)
	if err != nil {
		return err
	}
	expectedAcceptanceDigest := canonicalJSONSHA256(map[string]any{
		"human_acceptance_obligations": humanObligations,
		"human_acceptance_scenarios":   humanScenarios,
	})
	if handoff["human_acceptance_contract_origin"] != "task-index-v2" || stringField(handoff, "human_acceptance_contract_sha256") != expectedAcceptanceDigest {
		return errors.New("implementation-handoff.json human acceptance contract digest is invalid")
	}
	expectedDeferralDigest := canonicalJSONSHA256(map[string]any{"user_confirmed_deferrals": confirmedDeferrals})
	if stringField(handoff, "user_confirmed_deferrals_sha256") != expectedDeferralDigest {
		return errors.New("implementation-handoff.json user_confirmed_deferrals_sha256 is invalid")
	}
	policy, ok := handoff["validation_policy"].(map[string]any)
	if !ok || policy["mode"] != "feature_epochs" || policy["budget_scope"] != "implement-review" || policy["heavy_gate_owner"] != "leader" {
		return errors.New("implementation-handoff.json validation_policy is invalid")
	}
	maxEpochs, maxOK := jsonInteger(policy["max_epochs"])
	policyRef := strings.TrimSpace(fmt.Sprint(policy["budget_ref"]))
	if !maxOK || maxEpochs != implementMaxValidationEpochs || policyRef != implementDefaultBudgetRef {
		return errors.New("implementation-handoff.json validation_policy must reserve the canonical implement-review budget")
	}
	budget, ok := handoff["validation_budget"].(map[string]any)
	if !ok || budget["mode"] != "feature_epochs" || strings.TrimSpace(fmt.Sprint(budget["ledger_ref"])) != policyRef {
		return errors.New("implementation-handoff.json validation_budget is invalid")
	}
	budgetMax, budgetMaxOK := jsonInteger(budget["max_epochs"])
	used, usedOK := jsonInteger(budget["used_epochs"])
	remaining, remainingOK := jsonInteger(budget["remaining_epochs"])
	consumedDigest := stringField(budget, "consumed_runs_sha256")
	if !budgetMaxOK || budgetMax != maxEpochs || !usedOK || used < 0 || used > maxEpochs || !remainingOK || remaining != maxEpochs-used || !reviewSHA256RE.MatchString(consumedDigest) {
		return errors.New("implementation-handoff.json validation_budget counters or digest are invalid")
	}
	status, err := implementValidationBudgetStatus(projectRoot, featureAbs)
	if err != nil {
		return fmt.Errorf("implementation-handoff.json validation ledger is invalid: %w", err)
	}
	runs, ok := status["runs"].([]any)
	if !ok || len(runs) < used {
		return errors.New("implementation-handoff.json validation budget references unavailable consumed runs")
	}
	if canonicalJSONSHA256(runs[:used]) != consumedDigest {
		return errors.New("implementation-handoff.json consumed_runs_sha256 no longer matches the frozen validation ledger prefix")
	}
	return nil
}

func canonicalHandoffArray(handoff map[string]any, field string, required bool) ([]any, error) {
	values, ok := handoff[field].([]any)
	if !ok || (required && len(values) == 0) {
		return nil, fmt.Errorf("implementation-handoff.json %s must be %sarray", field, map[bool]string{true: "a non-empty ", false: "an "}[required])
	}
	for index, value := range values {
		if _, ok := value.(map[string]any); !ok {
			return nil, fmt.Errorf("implementation-handoff.json %s[%d] must be an object", field, index)
		}
	}
	return values, nil
}

func canonicalHandoffStringList(handoff map[string]any, field string, required bool) ([]string, error) {
	values, ok := handoff[field].([]any)
	if !ok || (required && len(values) == 0) {
		return nil, fmt.Errorf("implementation-handoff.json %s must be a string array", field)
	}
	out := make([]string, 0, len(values))
	seen := map[string]bool{}
	for index, value := range values {
		text, ok := value.(string)
		text = strings.TrimSpace(text)
		if !ok || text == "" || seen[text] {
			return nil, fmt.Errorf("implementation-handoff.json %s[%d] must be a unique non-empty string", field, index)
		}
		seen[text] = true
		out = append(out, text)
	}
	return out, nil
}

func newReviewState(feature reviewAcceptFeature, handoff map[string]any, expectedRevision int, handoffSHA, fingerprint string, cycle int, previousReviewSHA, restartReason string, rounds []any, acceptanceRepair map[string]any) map[string]any {
	findingID := stringField(acceptanceRepair, "finding_id")
	findingSHA := stringField(acceptanceRepair, "finding_sha256")
	cycleID := reviewCycleID(expectedRevision, handoffSHA, cycle, previousReviewSHA, findingID, findingSHA)
	source := map[string]any{
		"workflow_revision":             expectedRevision,
		"implementation_handoff_sha256": handoffSHA,
		"implementation_fingerprint":    fingerprint,
		"review_cycle":                  cycle,
		"review_cycle_id":               cycleID,
		"previous_review_state_sha256":  previousReviewSHA,
		"acceptance_finding_id":         findingID,
		"acceptance_finding_sha256":     findingSHA,
	}
	if restartReason != "" {
		source["restart_reason"] = restartReason
	}
	findings := []any{}
	repairCycles := []any{}
	if acceptanceRepair != nil {
		findings = append(findings, acceptanceOriginReviewFinding(acceptanceRepair))
		repairCycle := cloneAny(acceptanceRepair).(map[string]any)
		repairCycle["review_cycle"] = cycle
		repairCycle["review_cycle_id"] = cycleID
		repairCycle["status"] = "reviewing"
		repairCycles = append(repairCycles, repairCycle)
	}
	obligations := cloneAny(handoff["review_obligations"])
	scenarios := cloneAny(handoff["system_review_scenarios"])
	state := map[string]any{
		"version":                      reviewStateVersion,
		"schema_ref":                   reviewSchemaRef,
		"status":                       "gathering",
		"source":                       source,
		"entrypoints":                  cloneAny(handoff["official_entrypoints"]),
		"scenarios":                    scenarios,
		"obligations":                  obligations,
		"human_acceptance_scenarios":   cloneAny(handoff["human_acceptance_scenarios"]),
		"human_acceptance_obligations": cloneAny(handoff["human_acceptance_obligations"]),
		"implementation_deferrals":     newReviewDeferralStates(handoff["user_confirmed_deferrals"]),
		"review_exceptions":            []any{},
		"reviewed_runtime_targets":     []any{},
		"review_assignments":           []any{},
		"fix_assignments":              []any{},
		"revalidations":                []any{},
		"coverage": map[string]any{
			"discovery_complete":       false,
			"blind_audit_complete":     false,
			"uncovered_obligation_ids": requiredReviewObligationIDs(obligations),
			"uncovered_surface_ids":    []any{},
			"final_gap_scan":           "pending",
		},
		"leader": map[string]any{
			"strategy":                    "pending",
			"review_plan_complete":        false,
			"all_review_results_joined":   false,
			"fix_plan_complete":           false,
			"all_fix_results_joined":      false,
			"final_revalidation_complete": false,
			"verdict":                     "pending",
		},
		"rounds":        append([]any{}, rounds...),
		"findings":      findings,
		"repair_cycles": repairCycles,
		"validation": map[string]any{
			"startup":                  "pending",
			"real_entrypoint_journeys": "pending",
			"regression":               "pending",
			"ui_verification":          "pending",
		},
		"cursor": map[string]any{
			"scenario_id": firstReviewScenarioID(scenarios, acceptanceRepair),
			"next_action": "Run the current scenario from its official entrypoint.",
		},
		"blocker": nil,
		"final": map[string]any{
			"verdict":                       "pending",
			"coverage_verdict":              "pending",
			"repair_verdict":                "pending",
			"integration_verdict":           "pending",
			"all_packets_joined":            false,
			"reviewed_snapshot_sha256":      "",
			"implementation_summary_sha256": "",
			"runtime_targets_sha256":        "",
			"review_exceptions_sha256":      reviewExceptionsSHA256([]any{}),
		},
	}
	return state
}

func newReviewDeferralStates(value any) []any {
	fields := []string{
		"deferral_id", "deferral_ref", "proposal_sha256", "confirmation_id",
		"implementation_fingerprint", "blocker_refs", "affected_task_ids",
		"affected_acceptance_refs", "deferred_validation_purposes",
		"exact_excluded_behavior", "residual_risk", "risk_severity",
		"claims_withheld", "reopen_or_stop_condition", "downstream_artifact",
		"downstream_owner", "defer_until",
	}
	result := []any{}
	items, _ := value.([]any)
	for _, raw := range items {
		deferral, ok := raw.(map[string]any)
		if !ok {
			continue
		}
		state := map[string]any{}
		for _, field := range fields {
			state[field] = cloneAny(deferral[field])
		}
		state["status"] = "pending"
		state["resolution"] = nil
		result = append(result, state)
	}
	return result
}

func requiredReviewObligationIDs(value any) []any {
	result := []any{}
	items, _ := value.([]any)
	for _, raw := range items {
		item, ok := raw.(map[string]any)
		if !ok {
			continue
		}
		required, exists := item["required"].(bool)
		if exists && !required {
			continue
		}
		if id := stringField(item, "id"); id != "" {
			result = append(result, id)
		}
	}
	return result
}

func firstReviewScenarioID(value any, acceptanceRepair map[string]any) any {
	if id := stringField(acceptanceRepair, "review_scenario_id"); id != "" {
		return id
	}
	items, _ := value.([]any)
	for _, raw := range items {
		if item, ok := raw.(map[string]any); ok {
			if id := stringField(item, "id"); id != "" {
				return id
			}
		}
	}
	return nil
}

func acceptanceFindingSHA256(finding map[string]any) string {
	return canonicalJSONSHA256(finding)
}

func (service reviewAcceptService) acceptanceRepairContext(feature reviewAcceptFeature, lastReopen, previousReview map[string]any, previousReviewSHA string) (map[string]any, error) {
	findingID := stringField(lastReopen, "finding_id")
	if findingID == "" {
		return nil, errors.New("acceptance repair finding_id is missing")
	}
	acceptancePath := filepath.Join(feature.abs, humanAcceptanceFilename)
	acceptance, err := readJSONObject(acceptancePath)
	if err != nil {
		return nil, err
	}
	repairResume, _ := acceptance["repair_resume"].(map[string]any)
	if repairResume == nil || stringField(repairResume, "finding_id") != findingID {
		return nil, errors.New("human-acceptance.json repair_resume does not match the routed finding")
	}
	if stringField(repairResume, "previous_review_state_sha256") != previousReviewSHA {
		return nil, errors.New("previous approved Review changed after acceptance repair routing")
	}
	finding := findAcceptanceFinding(acceptance, findingID)
	if finding == nil || stringField(finding, "status") != "open" {
		return nil, errors.New("routed acceptance finding is missing or no longer open")
	}
	findingSHA := acceptanceFindingSHA256(finding)
	if stringField(repairResume, "finding_contract_sha256") != findingSHA {
		return nil, errors.New("routed acceptance finding changed after repair routing")
	}
	humanScenarioID := stringField(finding, "scenario_id")
	humanScenario := findObjectByID(previousReview["human_acceptance_scenarios"], humanScenarioID)
	if humanScenario == nil {
		return nil, errors.New("routed acceptance scenario is absent from the frozen Human Acceptance Universe")
	}
	reviewScenarioIDs, err := anyStringList(humanScenario["review_scenario_ids"], "review_scenario_ids", true)
	if err != nil || len(reviewScenarioIDs) == 0 {
		return nil, errors.New("routed acceptance scenario has no linked Review scenario")
	}
	reviewScenarioID := reviewScenarioIDs[0]
	reviewScenario := findObjectByID(previousReview["scenarios"], reviewScenarioID)
	if reviewScenario == nil {
		return nil, errors.New("routed acceptance finding references an unknown Review scenario")
	}
	obligationIDs, _ := anyStringList(reviewScenario["obligation_ids"], "obligation_ids", false)
	return map[string]any{
		"acceptance_state_sha256": optionalFileSHA256(acceptancePath),
		"finding_id":              findingID,
		"finding_sha256":          findingSHA,
		"route":                   stringField(finding, "route"),
		"human_scenario_id":       humanScenarioID,
		"human_step_id":           stringField(finding, "step_id"),
		"review_scenario_id":      reviewScenarioID,
		"review_obligation_ids":   stringSliceToAny(obligationIDs),
		"expected":                stringField(finding, "expected"),
		"observed":                stringField(finding, "observed"),
		"evidence":                cloneAny(finding["evidence"]),
	}, nil
}

func findAcceptanceFinding(acceptance map[string]any, findingID string) map[string]any {
	return findObjectByID(acceptance["findings"], findingID)
}

func findObjectByID(value any, id string) map[string]any {
	items, _ := value.([]any)
	for _, raw := range items {
		if item, ok := raw.(map[string]any); ok && stringField(item, "id") == id {
			return item
		}
	}
	return nil
}

func acceptanceOriginReviewFinding(context map[string]any) map[string]any {
	findingID := stringField(context, "finding_id")
	fragment := sha256String(findingID)
	if len(fragment) > 12 {
		fragment = fragment[:12]
	}
	return map[string]any{
		"id":                                 "SRF-ACCEPT-" + fragment,
		"scenario_id":                        stringField(context, "review_scenario_id"),
		"obligation_ids":                     cloneAny(context["review_obligation_ids"]),
		"classification":                     "interaction",
		"gap_classification":                 "implementation_gap",
		"severity":                           "high",
		"blocking":                           true,
		"summary":                            "Human acceptance observed a mismatch; Review must diagnose, fix, and independently revalidate it.",
		"expected":                           stringField(context, "expected"),
		"observed":                           stringField(context, "observed"),
		"evidence":                           cloneAny(context["evidence"]),
		"origin_acceptance_finding_id":       findingID,
		"discovered_by_review_assignment_id": "",
		"status":                             "open",
		"fix_assignment_id":                  "",
		"revalidation_ids":                   []any{},
	}
}

func reviewExceptionsSHA256(value any) string {
	raw, ok := value.([]any)
	if !ok {
		raw = []any{}
	}
	items := make([]map[string]any, 0, len(raw))
	for _, entry := range raw {
		if item, ok := entry.(map[string]any); ok {
			items = append(items, cloneAny(item).(map[string]any))
		}
	}
	sort.Slice(items, func(i, j int) bool {
		return fmt.Sprint(items[i]["exception_id"]) < fmt.Sprint(items[j]["exception_id"])
	})
	normalized := make([]any, len(items))
	for index, item := range items {
		normalized[index] = item
	}
	return canonicalJSONSHA256(map[string]any{"review_exceptions": normalized})
}

func reviewCycleID(workflowRevision int, handoffSHA string, cycle int, previousReviewSHA, findingID, findingSHA string) string {
	return canonicalJSONSHA256(map[string]any{
		"acceptance_finding_id":        findingID,
		"acceptance_finding_sha256":    findingSHA,
		"handoff_sha256":               handoffSHA,
		"previous_review_state_sha256": previousReviewSHA,
		"review_cycle":                 cycle,
		"workflow_revision":            workflowRevision,
	})
}

func upgradeReviewExceptionContract(state map[string]any) bool {
	changed := false
	if _, exists := state["review_exceptions"]; !exists {
		state["review_exceptions"] = []any{}
		changed = true
	}
	if final, ok := state["final"].(map[string]any); ok {
		if _, exists := final["review_exceptions_sha256"]; !exists {
			final["review_exceptions_sha256"] = reviewExceptionsSHA256(state["review_exceptions"])
			changed = true
		}
	}
	if source, ok := state["source"].(map[string]any); ok && stringField(source, "review_cycle_id") == "" {
		workflowRevision, revisionOK := numberAsInt(source["workflow_revision"])
		cycle, cycleOK := numberAsInt(source["review_cycle"])
		handoffSHA := strings.TrimSpace(fmt.Sprint(source["implementation_handoff_sha256"]))
		if revisionOK && cycleOK && cycle >= 1 && handoffSHA != "" {
			source["review_cycle_id"] = reviewCycleID(workflowRevision, handoffSHA, cycle, "", "", "")
			changed = true
		}
	}
	return changed
}

func reviewExceptionConfirmationID(value string) string {
	digest := sha256.Sum256([]byte(value))
	return fmt.Sprintf("%x", digest[:])[:24]
}

func reviewExceptionProposalPayload(record map[string]any) map[string]any {
	payload := map[string]any{}
	for _, field := range reviewExceptionProposalFields {
		payload[field] = cloneAny(record[field])
	}
	return payload
}

func reviewExceptionInputPayload(record map[string]any) map[string]any {
	payload := map[string]any{}
	for _, field := range reviewExceptionInputFields {
		payload[field] = cloneAny(record[field])
	}
	return payload
}

func reviewExceptionEvidencePath(feature reviewAcceptFeature, ref string, cycle int) (string, error) {
	if err := validateSafeRelativeSlashPath(ref); err != nil {
		return "", errors.New("hardware unavailability evidence must be a safe feature-relative path")
	}
	expectedPrefix := "review-evidence/"
	if cycle > 1 {
		expectedPrefix = fmt.Sprintf("review-evidence/cycle-%d/", cycle)
	}
	if !strings.HasPrefix(ref, expectedPrefix) {
		return "", errors.New("hardware unavailability evidence must belong to the current Review cycle")
	}
	path := filepath.Join(feature.abs, filepath.FromSlash(ref))
	rel, err := filepath.Rel(feature.abs, path)
	if err != nil || rel == ".." || strings.HasPrefix(rel, ".."+string(filepath.Separator)) {
		return "", errors.New("hardware unavailability evidence escapes the feature directory")
	}
	if info, err := os.Stat(path); err != nil || info.IsDir() {
		return "", fmt.Errorf("hardware unavailability evidence file does not exist: %s", ref)
	}
	return path, nil
}

func normalizeReviewExceptionProposal(feature reviewAcceptFeature, state, raw map[string]any, fingerprint string) (map[string]any, error) {
	allowed := map[string]bool{}
	for _, field := range reviewExceptionInputFields {
		allowed[field] = true
	}
	for field := range raw {
		if !allowed[field] {
			return nil, fmt.Errorf("review exception proposal contains unsupported field: %s", field)
		}
	}
	if strings.TrimSpace(fmt.Sprint(raw["kind"])) != "hardware_unavailable" {
		return nil, errors.New("review exception kind must be hardware_unavailable")
	}
	scenarioIDs, err := anyStringList(raw["scenario_ids"], "scenario_ids", true)
	if err != nil {
		return nil, err
	}
	obligationIDs, err := anyStringList(raw["obligation_ids"], "obligation_ids", true)
	if err != nil {
		return nil, err
	}
	scenarios, _ := state["scenarios"].([]any)
	knownScenarios := map[string]map[string]any{}
	for _, value := range scenarios {
		if scenario, ok := value.(map[string]any); ok {
			knownScenarios[strings.TrimSpace(fmt.Sprint(scenario["id"]))] = scenario
		}
	}
	for _, scenarioID := range scenarioIDs {
		scenario := knownScenarios[scenarioID]
		if scenario == nil || scenario["required"] == false {
			return nil, fmt.Errorf("review exception may reference only required Review scenarios: %s", scenarioID)
		}
	}
	selectedScenarios := map[string]bool{}
	for _, scenarioID := range scenarioIDs {
		selectedScenarios[scenarioID] = true
	}
	impacted := []string{}
	obligations, _ := state["obligations"].([]any)
	for _, value := range obligations {
		obligation, ok := value.(map[string]any)
		if !ok || obligation["required"] == false {
			continue
		}
		linked, _ := anyStringList(obligation["scenario_ids"], "scenario_ids", false)
		for _, scenarioID := range linked {
			if selectedScenarios[scenarioID] {
				impacted = append(impacted, strings.TrimSpace(fmt.Sprint(obligation["id"])))
				break
			}
		}
	}
	sort.Strings(impacted)
	sortedObligationIDs := append([]string{}, obligationIDs...)
	sort.Strings(sortedObligationIDs)
	if !reflect.DeepEqual(impacted, sortedObligationIDs) {
		return nil, errors.New("obligation_ids must exactly name every required obligation affected by the waived scenarios")
	}
	evidenceRefs, err := anyStringList(raw["unavailable_evidence_refs"], "unavailable_evidence_refs", true)
	if err != nil {
		return nil, err
	}
	attemptedAlternatives, err := anyStringList(raw["attempted_alternatives"], "attempted_alternatives", true)
	if err != nil {
		return nil, err
	}
	claimsWithheld, err := anyStringList(raw["claims_withheld"], "claims_withheld", true)
	if err != nil {
		return nil, err
	}
	requiredResource := strings.TrimSpace(fmt.Sprint(raw["required_resource"]))
	residualRisk := strings.TrimSpace(fmt.Sprint(raw["residual_risk"]))
	severity := strings.TrimSpace(fmt.Sprint(raw["risk_severity"]))
	if requiredResource == "" || residualRisk == "" {
		return nil, errors.New("required_resource and residual_risk must be non-empty strings")
	}
	if severity != "low" && severity != "medium" && severity != "high" {
		return nil, errors.New("risk_severity must be low, medium, or high")
	}
	source, _ := state["source"].(map[string]any)
	cycle, ok := numberAsInt(source["review_cycle"])
	if !ok || cycle < 1 {
		return nil, errors.New("review source review_cycle is invalid")
	}
	cycleID := strings.TrimSpace(fmt.Sprint(source["review_cycle_id"]))
	if cycleID == "" {
		return nil, errors.New("review source review_cycle_id is required")
	}
	evidenceDigests := map[string]any{}
	for _, ref := range evidenceRefs {
		path, err := reviewExceptionEvidencePath(feature, ref, cycle)
		if err != nil {
			return nil, err
		}
		digest, err := fileSHA256(path)
		if err != nil {
			return nil, err
		}
		evidenceDigests[ref] = digest
	}
	return map[string]any{
		"kind": "hardware_unavailable", "scenario_ids": stringSliceToAny(scenarioIDs),
		"obligation_ids": stringSliceToAny(obligationIDs), "required_resource": requiredResource,
		"unavailable_evidence_refs": stringSliceToAny(evidenceRefs), "unavailable_evidence_sha256": evidenceDigests,
		"attempted_alternatives": stringSliceToAny(attemptedAlternatives), "claims_withheld": stringSliceToAny(claimsWithheld),
		"residual_risk": residualRisk, "risk_severity": severity,
		"review_cycle_id": cycleID, "implementation_fingerprint": fingerprint,
	}, nil
}

func (service reviewAcceptService) proposeReviewException(featureDir string, raw map[string]any) Envelope {
	root, feature, env, ok := service.resolveFeature(featureDir)
	if !ok {
		return env
	}
	workflow := NewWorkflowService(root).Show(WorkflowShowRequest{FeatureDir: feature.rel})
	if workflow.Status != "ok" || workflow.Data["stage"] != "review" || workflow.Data["status"] != "active" {
		return blockedEnvelope("review exception requires active Review", "workflow stage must be active review")
	}
	release, lockEnv, locked := acquireReviewAcceptLock(filepath.Join(feature.abs, ".review-state.lock"))
	if !locked {
		return lockEnv
	}
	defer release()
	statePath := filepath.Join(feature.abs, reviewStateFilename)
	state, err := readJSONObject(statePath)
	if err != nil {
		return blockedEnvelope("review state is unavailable", err.Error())
	}
	status := strings.TrimSpace(fmt.Sprint(state["status"]))
	if status != "gathering" && status != "reviewing" && status != "repairing" && status != "validating" {
		return blockedEnvelope("review exception proposal is not allowed", "exceptions may be proposed only during active Review work")
	}
	source, _ := state["source"].(map[string]any)
	currentFingerprint := sourceTreeFingerprint(root, feature.abs)
	if source == nil || strings.TrimSpace(fmt.Sprint(source["implementation_fingerprint"])) != currentFingerprint {
		return blockedEnvelope("review exception proposal is stale", "current implementation fingerprint differs from Review source")
	}
	normalized, err := normalizeReviewExceptionProposal(feature, state, raw, currentFingerprint)
	if err != nil {
		return blockedEnvelope("review exception proposal is invalid", err.Error())
	}
	proposalSHA := canonicalJSONSHA256(normalized)
	exceptionID := "REX-" + proposalSHA[:12]
	exceptions, ok := state["review_exceptions"].([]any)
	if !ok {
		return blockedEnvelope("review exception state is invalid", "review_exceptions must be an array")
	}
	for _, value := range exceptions {
		existing, ok := value.(map[string]any)
		if !ok {
			continue
		}
		if existing["proposal_sha256"] == proposalSHA {
			env := NewEnvelope("ok", "review exception proposal already exists")
			env.Data = map[string]any{
				"status": existing["status"], "reused": true, "exception_id": existing["exception_id"],
				"proposal_sha256": proposalSHA, "confirmation_required": existing["status"] != "confirmed",
			}
			return env
		}
		if existing["exception_id"] == exceptionID {
			return blockedEnvelope("review exception id collision", exceptionID)
		}
	}
	record := map[string]any{"exception_id": exceptionID}
	for key, value := range normalized {
		record[key] = value
	}
	record["proposal_sha256"] = proposalSHA
	record["status"] = "proposed"
	record["confirmation"] = nil
	exceptions = append(exceptions, record)
	state["review_exceptions"] = exceptions
	if final, ok := state["final"].(map[string]any); ok {
		final["review_exceptions_sha256"] = reviewExceptionsSHA256(exceptions)
	}
	if err := writeReviewAcceptJSONAtomic(statePath, state); err != nil {
		return errorEnvelope("failed to write Review exception proposal", err)
	}
	env = NewEnvelope("ok", "review exception proposal prepared")
	env.Data = map[string]any{
		"status": "proposed", "reused": false, "exception_id": exceptionID,
		"proposal_sha256": proposalSHA, "confirmation_required": true,
	}
	return env
}

func (service reviewAcceptService) confirmReviewException(featureDir, exceptionID, proposalSHA, confirmationSource, statement string) Envelope {
	root, feature, env, ok := service.resolveFeature(featureDir)
	if !ok {
		return env
	}
	exceptionID = strings.TrimSpace(exceptionID)
	proposalSHA = strings.TrimSpace(proposalSHA)
	confirmationSource = strings.TrimSpace(confirmationSource)
	statement = strings.TrimSpace(statement)
	if !reviewExceptionIDRE.MatchString(exceptionID) || proposalSHA == "" || !reviewExceptionConfirmationSources[confirmationSource] || statement == "" {
		return usageEnvelope("exception-confirm requires a valid exception id, proposal digest, human confirmation source, and statement")
	}
	workflow := NewWorkflowService(root).Show(WorkflowShowRequest{FeatureDir: feature.rel})
	if workflow.Status != "ok" || workflow.Data["stage"] != "review" || workflow.Data["status"] != "active" {
		return blockedEnvelope("review exception requires active Review", "workflow stage must be active review")
	}
	release, lockEnv, locked := acquireReviewAcceptLock(filepath.Join(feature.abs, ".review-state.lock"))
	if !locked {
		return lockEnv
	}
	defer release()
	statePath := filepath.Join(feature.abs, reviewStateFilename)
	state, err := readJSONObject(statePath)
	if err != nil {
		return blockedEnvelope("review state is unavailable", err.Error())
	}
	status := strings.TrimSpace(fmt.Sprint(state["status"]))
	if status != "gathering" && status != "reviewing" && status != "repairing" && status != "validating" {
		return blockedEnvelope("review exception confirmation is not allowed", "exceptions may be confirmed only during active Review work")
	}
	source, _ := state["source"].(map[string]any)
	currentFingerprint := sourceTreeFingerprint(root, feature.abs)
	exceptions, _ := state["review_exceptions"].([]any)
	var record map[string]any
	for _, value := range exceptions {
		candidate, ok := value.(map[string]any)
		if ok && candidate["exception_id"] == exceptionID {
			record = candidate
			break
		}
	}
	if record == nil {
		return blockedEnvelope("review exception is unknown", exceptionID)
	}
	actualSHA := canonicalJSONSHA256(reviewExceptionProposalPayload(record))
	if record["proposal_sha256"] != actualSHA || proposalSHA != actualSHA {
		return blockedEnvelope("review exception proposal digest mismatch", "proposal sha256 does not match the immutable exception proposal")
	}
	if source == nil || record["review_cycle_id"] != source["review_cycle_id"] || record["implementation_fingerprint"] != currentFingerprint {
		return blockedEnvelope("review exception proposal is stale", "create a new proposal for the current Review cycle and implementation")
	}
	normalized, err := normalizeReviewExceptionProposal(feature, state, reviewExceptionInputPayload(record), currentFingerprint)
	if err != nil || canonicalJSONSHA256(normalized) != actualSHA {
		detail := "review exception evidence or affected scope changed after proposal"
		if err != nil {
			detail = err.Error()
		}
		return blockedEnvelope("review exception proposal is stale", detail)
	}
	if record["status"] == "confirmed" {
		confirmation, _ := record["confirmation"].(map[string]any)
		if confirmation != nil && confirmation["source"] == confirmationSource && confirmation["statement"] == statement {
			env := NewEnvelope("ok", "review exception confirmation already exists")
			env.Data = map[string]any{
				"status": "confirmed", "reused": true, "exception_id": exceptionID,
				"proposal_sha256": actualSHA, "confirmation_id": confirmation["confirmation_id"],
			}
			return env
		}
		return blockedEnvelope("confirmed Review exception is immutable", "create a new proposal for a different human decision")
	}
	if record["status"] != "proposed" || record["confirmation"] != nil {
		return blockedEnvelope("review exception cannot be confirmed", fmt.Sprintf("current status is %v", record["status"]))
	}
	cycleID := fmt.Sprint(source["review_cycle_id"])
	confirmationID := "HC-" + reviewExceptionConfirmationID(actualSHA+"\x00"+confirmationSource+"\x00"+statement+"\x00"+cycleID+"\x00"+currentFingerprint)
	record["status"] = "confirmed"
	record["confirmation"] = map[string]any{
		"actor": "human", "source": confirmationSource, "statement": statement,
		"confirmation_id": confirmationID, "confirmed_payload_sha256": actualSHA,
		"review_cycle_id": cycleID, "implementation_fingerprint": currentFingerprint,
	}
	selectedScenarios := map[string]bool{}
	for _, scenarioID := range record["scenario_ids"].([]any) {
		selectedScenarios[scenarioID.(string)] = true
	}
	for _, value := range state["scenarios"].([]any) {
		if scenario, ok := value.(map[string]any); ok && selectedScenarios[fmt.Sprint(scenario["id"])] {
			scenario["result"] = "waived"
			scenario["evidence"] = []any{}
		}
	}
	selectedObligations := map[string]bool{}
	for _, obligationID := range record["obligation_ids"].([]any) {
		selectedObligations[obligationID.(string)] = true
	}
	for _, value := range state["obligations"].([]any) {
		if obligation, ok := value.(map[string]any); ok && selectedObligations[fmt.Sprint(obligation["id"])] {
			obligation["status"] = "waived"
		}
	}
	if final, ok := state["final"].(map[string]any); ok {
		final["review_exceptions_sha256"] = reviewExceptionsSHA256(exceptions)
	}
	if err := writeReviewAcceptJSONAtomic(statePath, state); err != nil {
		return errorEnvelope("failed to write Review exception confirmation", err)
	}
	env = NewEnvelope("ok", "review hardware exception confirmed")
	env.Data = map[string]any{
		"status": "confirmed", "reused": false, "exception_id": exceptionID,
		"proposal_sha256": actualSHA, "confirmation_id": confirmationID,
		"disposition": "explicit_review_waiver",
	}
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
	finding := findAcceptanceFinding(state, findingID)
	if finding == nil {
		return blockedEnvelope("acceptance finding route is unavailable", "routed finding is missing")
	}
	reviewRaw, err := os.ReadFile(filepath.Join(feature.abs, reviewStateFilename))
	if err != nil {
		return blockedEnvelope("approved Review state is unavailable", err.Error())
	}
	previousReviewSHA := fmt.Sprintf("%x", sha256.Sum256(reviewRaw))
	if source, ok := state["source"].(map[string]any); ok {
		if bound := stringField(source, "review_state_sha256"); bound != "" && bound != previousReviewSHA {
			return blockedEnvelope("human acceptance is stale", "review-state.json changed after acceptance preparation")
		}
		if bound := stringField(source, "implementation_handoff_sha256"); bound != "" && bound != optionalFileSHA256(filepath.Join(feature.abs, implementationHandoffFilename)) {
			return blockedEnvelope("human acceptance is stale", "implementation-handoff.json changed after acceptance preparation")
		}
	}
	findingSHA := acceptanceFindingSHA256(finding)
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
		"finding_id":                   findingID,
		"finding_contract_sha256":      findingSHA,
		"previous_review_state_sha256": previousReviewSHA,
		"route":                        route,
		"target_stage":                 "review",
		"expected_revision":            request.expectedRevision,
		"evidence":                     nonEmptyStrings(request.evidence),
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
		"finding_contract_sha256":       findingSHA,
		"previous_review_state_sha256":  previousReviewSHA,
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

func validateReviewExceptions(feature reviewAcceptFeature, state map[string]any, currentFingerprint string) ([]string, int) {
	errorsOut := []string{}
	rawExceptions, ok := state["review_exceptions"].([]any)
	if !ok {
		return []string{"review_exceptions must be an array"}, 0
	}
	source, _ := state["source"].(map[string]any)
	cycleID := strings.TrimSpace(fmt.Sprint(source["review_cycle_id"]))
	confirmedScenarios := map[string]bool{}
	confirmedObligations := map[string]bool{}
	seenIDs := map[string]bool{}
	confirmedCount := 0
	for index, value := range rawExceptions {
		record, ok := value.(map[string]any)
		if !ok {
			errorsOut = append(errorsOut, fmt.Sprintf("review exception %d must be an object", index+1))
			continue
		}
		exceptionID := strings.TrimSpace(fmt.Sprint(record["exception_id"]))
		proposalSHA := canonicalJSONSHA256(reviewExceptionProposalPayload(record))
		if !reviewExceptionIDRE.MatchString(exceptionID) || exceptionID != "REX-"+proposalSHA[:12] {
			errorsOut = append(errorsOut, fmt.Sprintf("review exception %d id does not bind its proposal", index+1))
		}
		if seenIDs[exceptionID] {
			errorsOut = append(errorsOut, "duplicate review exception id: "+exceptionID)
		}
		seenIDs[exceptionID] = true
		if record["proposal_sha256"] != proposalSHA {
			errorsOut = append(errorsOut, exceptionID+" proposal_sha256 does not bind its proposal")
		}
		if record["review_cycle_id"] != cycleID || record["implementation_fingerprint"] != currentFingerprint {
			errorsOut = append(errorsOut, exceptionID+" is stale for the current Review cycle or implementation")
		}
		normalized, err := normalizeReviewExceptionProposal(feature, state, reviewExceptionInputPayload(record), currentFingerprint)
		if err != nil || canonicalJSONSHA256(normalized) != proposalSHA {
			detail := "proposal evidence or affected scope changed"
			if err != nil {
				detail = err.Error()
			}
			errorsOut = append(errorsOut, exceptionID+" "+detail)
		}
		status := strings.TrimSpace(fmt.Sprint(record["status"]))
		if status == "proposed" {
			if record["confirmation"] != nil {
				errorsOut = append(errorsOut, exceptionID+" proposed exception cannot contain confirmation")
			}
			if state["status"] == "approved" {
				errorsOut = append(errorsOut, exceptionID+" requires explicit human confirmation before approval")
			}
			continue
		}
		if status != "confirmed" {
			errorsOut = append(errorsOut, exceptionID+" status must be proposed or confirmed")
			continue
		}
		confirmation, ok := record["confirmation"].(map[string]any)
		if !ok {
			errorsOut = append(errorsOut, exceptionID+" requires explicit human confirmation")
			continue
		}
		confirmationSource := strings.TrimSpace(fmt.Sprint(confirmation["source"]))
		statement := strings.TrimSpace(fmt.Sprint(confirmation["statement"]))
		expectedConfirmationID := "HC-" + reviewExceptionConfirmationID(proposalSHA+"\x00"+confirmationSource+"\x00"+statement+"\x00"+cycleID+"\x00"+currentFingerprint)
		if confirmation["actor"] != "human" || !reviewExceptionConfirmationSources[confirmationSource] || statement == "" || confirmation["confirmed_payload_sha256"] != proposalSHA || confirmation["review_cycle_id"] != cycleID || confirmation["implementation_fingerprint"] != currentFingerprint || confirmation["confirmation_id"] != expectedConfirmationID {
			errorsOut = append(errorsOut, exceptionID+" human confirmation is invalid or stale")
			continue
		}
		confirmedCount++
		scenarioIDs, _ := anyStringList(record["scenario_ids"], "scenario_ids", true)
		for _, scenarioID := range scenarioIDs {
			if confirmedScenarios[scenarioID] {
				errorsOut = append(errorsOut, "Review scenario belongs to multiple confirmed exceptions: "+scenarioID)
			}
			confirmedScenarios[scenarioID] = true
		}
		obligationIDs, _ := anyStringList(record["obligation_ids"], "obligation_ids", true)
		for _, obligationID := range obligationIDs {
			if confirmedObligations[obligationID] {
				errorsOut = append(errorsOut, "Review obligation belongs to multiple confirmed exceptions: "+obligationID)
			}
			confirmedObligations[obligationID] = true
		}
	}
	if scenarios, ok := state["scenarios"].([]any); ok {
		for _, value := range scenarios {
			if scenario, ok := value.(map[string]any); ok {
				id := fmt.Sprint(scenario["id"])
				if scenario["result"] == "waived" && !confirmedScenarios[id] {
					errorsOut = append(errorsOut, "waived scenario requires explicit human confirmation: "+id)
				}
				if confirmedScenarios[id] && scenario["result"] != "waived" {
					errorsOut = append(errorsOut, "confirmed exception scenario must record result waived: "+id)
				}
			}
		}
	}
	if obligations, ok := state["obligations"].([]any); ok {
		for _, value := range obligations {
			if obligation, ok := value.(map[string]any); ok {
				id := fmt.Sprint(obligation["id"])
				if obligation["status"] == "waived" && !confirmedObligations[id] {
					errorsOut = append(errorsOut, "waived obligation requires explicit human confirmation: "+id)
				}
				if confirmedObligations[id] && obligation["status"] != "waived" {
					errorsOut = append(errorsOut, "confirmed exception obligation must record status waived: "+id)
				}
			}
		}
	}
	final, _ := state["final"].(map[string]any)
	if final == nil || final["review_exceptions_sha256"] != reviewExceptionsSHA256(rawExceptions) {
		errorsOut = append(errorsOut, "final review_exceptions_sha256 must bind the complete exception ledger")
	}
	return errorsOut, confirmedCount
}

func (service reviewAcceptService) validateReview(feature reviewAcceptFeature) reviewValidationResult {
	statePath := filepath.Join(feature.abs, reviewStateFilename)
	handoffPath := filepath.Join(feature.abs, implementationHandoffFilename)
	state, err := readJSONObject(statePath)
	if err != nil {
		return reviewValidationResult{errors: []string{err.Error()}}
	}
	upgradeReviewExceptionContract(state)
	handoff, err := readJSONObject(handoffPath)
	if err != nil {
		return reviewValidationResult{state: state, errors: []string{err.Error()}}
	}
	handoffSHA := optionalFileSHA256(handoffPath)
	currentFingerprint := sourceTreeFingerprint(service.projectRoot, feature.abs)
	errors := []string{}
	fresh := true
	if err := validateCanonicalImplementationHandoff(service.projectRoot, feature.abs, handoff); err != nil {
		errors = append(errors, err.Error())
	}
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
			fresh = false
		}
		if handoffRevision, ok := jsonInteger(handoff["source_revision"]); ok &&
			intField(source, "workflow_revision") != handoffRevision &&
			stringField(source, "acceptance_finding_id") == "" {
			errors = append(errors, "review source workflow_revision does not match implementation handoff")
		}
	}
	targetErrors, targetsFresh := validateReviewRuntimeTargets(feature, state, currentFingerprint)
	errors = append(errors, targetErrors...)
	fresh = fresh && targetsFresh
	if state["status"] == "approved" {
		final, _ := state["final"].(map[string]any)
		exceptionErrors, confirmedExceptionCount := validateReviewExceptions(feature, state, currentFingerprint)
		errors = append(errors, exceptionErrors...)
		if final == nil {
			errors = append(errors, "approved Review requires final verdict metadata")
		} else {
			expectedOverall := "pass"
			if confirmedExceptionCount > 0 {
				expectedOverall = "pass_with_waivers"
			}
			for _, key := range []string{"verdict", "coverage_verdict"} {
				if stringField(final, key) != expectedOverall {
					errors = append(errors, "approved Review requires final."+key+"="+expectedOverall)
				}
			}
			for _, key := range []string{"repair_verdict", "integration_verdict"} {
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
	} else {
		exceptionErrors, _ := validateReviewExceptions(feature, state, currentFingerprint)
		errors = append(errors, exceptionErrors...)
	}
	return reviewValidationResult{
		valid:              len(errors) == 0,
		fresh:              fresh && (len(errors) == 0 || state["status"] != "approved"),
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
		"review_exceptions": cloneAny(reviewState["review_exceptions"]),
		"runtime_targets":   cloneAny(reviewState["reviewed_runtime_targets"]),
		"scenarios":         cloneAny(handoff["human_acceptance_scenarios"]),
		"findings":          []any{},
		"repair_resume":     nil,
		"repair_history":    []any{},
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
	raw, err := marshalReviewAcceptJSON(payload)
	if err != nil {
		return err
	}
	return atomicWriteFile(path, raw, 0o644)
}

func marshalReviewAcceptJSON(payload any) ([]byte, error) {
	raw, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		return nil, err
	}
	return append(raw, '\n'), nil
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
	return implementSnapshotSHA256(projectRoot, featureAbs)
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
