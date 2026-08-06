package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"regexp"
	"sort"
	"strings"
	"time"

	ignorepkg "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/ignore"
)

const (
	implementValidationLedgerVersion = 2
	implementMaxValidationEpochs     = 3
	implementDefaultBudgetRef        = "implementation-review/validation-runs.json"
	implementDeferralSchemaRef       = ".specify/templates/implementation-deferral-schema.json"
	implementDeferralDirRef          = "implementation-review/deferrals"
)

var (
	implementValidStages       = map[string]bool{"implement": true, "review": true}
	implementValidPurposes     = map[string]bool{"baseline": true, "convergence": true, "delivery": true}
	implementValidStatuses     = map[string]bool{"running": true, "passed": true, "failed": true, "interrupted": true}
	implementValidFailureKinds = map[string]bool{
		"assertion": true, "verification": true, "harness": true, "environment": true,
		"runner_timeout": true, "runner_terminated": true, "cancelled": true, "unknown": true,
	}
	implementTaskBlockerRefRE      = regexp.MustCompile(`^(T\d+)-B(\d{2})$`)
	implementValidationBlockerRE   = regexp.MustCompile(`^VALIDATION-(BASELINE|CONVERGENCE)$`)
	implementDeferralIDRE          = regexp.MustCompile(`^DEF-[0-9a-f]{12}$`)
	implementTaskIDRE              = regexp.MustCompile(`^T\d+$`)
	implementSHA256RE              = regexp.MustCompile(`^[0-9a-f]{64}$`)
	implementTaskLineRE            = regexp.MustCompile(`(?m)^\s*-\s\[(?P<checked>[ xX])\]\s+(?P<task_id>T\d+)\b(?P<body>.*)$`)
	implementAllowedProposalFields = map[string]bool{
		"blocker_refs": true, "affected_task_ids": true, "affected_acceptance_refs": true,
		"deferred_validation_purposes": true, "exact_excluded_behavior": true,
		"residual_risk": true, "risk_severity": true, "claims_withheld": true,
		"reopen_or_stop_condition": true, "downstream_artifact": true,
		"downstream_owner": true, "defer_until": true,
	}
)

func runImplement(args []string, stdout io.Writer) int {
	if len(args) == 0 {
		return writeImplementError(stdout, "usage-error", "missing implement subcommand")
	}
	switch args[0] {
	case "task-next":
		payload, err := runImplementTaskNext(args[1:])
		return writeImplementTaskNextPayload(stdout, payload, err)
	case "packet-compile":
		payload, err := runImplementPacketCompile(args[1:])
		return writeImplementPayload(stdout, payload, err, "worker task packet compiled")
	case "task-start":
		payload, err := runImplementTaskStart(args[1:])
		return writeImplementPayload(stdout, payload, err, "task lifecycle started")
	case "result-merge":
		payload, err := runImplementResultMerge(args[1:])
		return writeImplementPayload(stdout, payload, err, "worker task result merged")
	case "task-accept":
		payload, err := runImplementTaskAccept(args[1:])
		return writeImplementPayload(stdout, payload, err, "validated task accepted")
	case "task-reopen":
		payload, err := runImplementTaskReopen(args[1:])
		return writeImplementPayload(stdout, payload, err, "task reopened with immutable recovery history")
	case "validation-start":
		return runImplementValidationStart(args[1:], stdout)
	case "validation-finish":
		return runImplementValidationFinish(args[1:], stdout)
	case "validation-status":
		return runImplementValidationStatus(args[1:], stdout)
	case "resume-audit":
		return runImplementResumeAudit(args[1:], stdout)
	case "deferral-propose":
		return runImplementDeferralPropose(args[1:], stdout)
	case "deferral-confirm":
		return runImplementDeferralConfirm(args[1:], stdout)
	case "closeout":
		return runImplementCloseout(args[1:], stdout)
	default:
		return writeImplementError(stdout, "usage-error", fmt.Sprintf("unknown implement subcommand %q", args[0]))
	}
}

func runImplementValidationStart(args []string, stdout io.Writer) int {
	root, feature, env, ok := implementFeatureFromArgs(args)
	if !ok {
		return writeEnvelope(stdout, env)
	}
	stage := strings.ToLower(strings.TrimSpace(optionValue(args, "--stage", "")))
	purpose := strings.ToLower(strings.TrimSpace(optionValue(args, "--purpose", "")))
	fingerprint := strings.TrimSpace(optionValue(args, "--fingerprint", ""))
	if fingerprint == "" {
		fingerprint = implementSnapshotSHA256(root, feature)
	}
	payload, err := reserveImplementValidationEpoch(root, feature, stage, purpose, fingerprint, optionValues(args, "--command"), optionValues(args, "--task-id"))
	return writeImplementPayload(stdout, payload, err, "validation epoch reserved")
}

func runImplementValidationFinish(args []string, stdout io.Writer) int {
	root, feature, env, ok := implementFeatureFromArgs(args)
	if !ok {
		return writeEnvelope(stdout, env)
	}
	payload, err := completeImplementValidationEpoch(root, feature, implementValidationFinishRequest{
		RunID:        optionValue(args, "--run-id", ""),
		Status:       optionValue(args, "--status", ""),
		FailureKind:  optionValue(args, "--failure-kind", ""),
		EvidenceRefs: optionValues(args, "--evidence-ref"),
		Summary:      optionValue(args, "--summary", ""),
	})
	return writeImplementPayload(stdout, payload, err, "validation epoch finished")
}

func runImplementValidationStatus(args []string, stdout io.Writer) int {
	root, feature, env, ok := implementFeatureFromArgs(args)
	if !ok {
		return writeEnvelope(stdout, env)
	}
	payload, err := implementValidationBudgetStatus(root, feature)
	return writeImplementPayload(stdout, payload, err, "validation budget status")
}

func runImplementResumeAudit(args []string, stdout io.Writer) int {
	root, feature, env, ok := implementFeatureFromArgs(args)
	if !ok {
		return writeEnvelope(stdout, env)
	}
	payload := auditImplementResume(root, feature)
	if payload["status"] == "fail" || payload["status"] == "conflict" {
		if payload["reason_code"] == "workflow-blocked" && payload["workflow_blocker"] != nil {
			payload["blockers"] = []any{cloneJSONValue(payload["workflow_blocker"])}
		} else {
			payload["blockers"] = implementationCloseoutBlockers(feature, payload, nil)
		}
		env := NewEnvelope("blocked", "implementation resume audit failed")
		env.Data = payload
		switch blockers := payload["blockers"].(type) {
		case []map[string]any:
			for _, blocker := range blockers {
				env.Blockers = append(env.Blockers, blocker)
			}
		case []any:
			env.Blockers = append(env.Blockers, blockers...)
		}
		return writeEnvelope(stdout, env)
	}
	env = NewEnvelope("ok", "implementation resume audit completed")
	env.Data = payload
	return writeEnvelope(stdout, env)
}

func runImplementDeferralPropose(args []string, stdout io.Writer) int {
	root, feature, env, ok := implementFeatureFromArgs(args)
	if !ok {
		return writeEnvelope(stdout, env)
	}
	proposal, err := readAgentJSONObject(args, root, "deferral-propose")
	if err != nil {
		return writeImplementError(stdout, "usage-error", err.Error())
	}
	payload, err := proposeImplementationDeferral(root, feature, proposal)
	return writeImplementPayload(stdout, payload, err, "implementation deferral proposed")
}

func runImplementDeferralConfirm(args []string, stdout io.Writer) int {
	root, feature, env, ok := implementFeatureFromArgs(args)
	if !ok {
		return writeEnvelope(stdout, env)
	}
	payload, err := confirmImplementationDeferral(root, feature, implementDeferralConfirmRequest{
		DeferralID:         optionValue(args, "--deferral-id", ""),
		ProposalSHA256:     optionValue(args, "--proposal-sha256", ""),
		ConfirmationSource: optionValue(args, "--confirmation-source", ""),
		Statement:          optionValue(args, "--statement", ""),
	})
	return writeImplementPayload(stdout, payload, err, "implementation deferral confirmed")
}

func runImplementCloseout(args []string, stdout io.Writer) int {
	root, feature, env, ok := implementFeatureFromArgs(args)
	if !ok {
		return writeEnvelope(stdout, env)
	}
	audit := auditImplementResume(root, feature)
	if audit["status"] == "fail" || audit["status"] == "conflict" || audit["trusted_terminal_state"] != true {
		blockers := implementationCloseoutBlockers(feature, audit, nil)
		payload := map[string]any{
			"status":       "blocked",
			"feature_dir":  feature,
			"resume_audit": audit,
			"blockers":     blockers,
		}
		env := NewEnvelope("blocked", "implement closeout blocked by resume audit")
		env.Data = payload
		for _, blocker := range blockers {
			env.Blockers = append(env.Blockers, blocker)
		}
		return writeEnvelope(stdout, env)
	}
	workflow, _ := readImplementJSONMap(filepath.Join(feature, "workflow.json"))
	revision := 1
	if raw, ok := workflow["revision"].(float64); ok {
		revision = int(raw)
	}
	reviewRevision := revision + 1
	if workflow["stage"] == "implement" && workflow["status"] == "active" {
		reviewRevision = revision + 2
	}
	summaryPayload, handoffPayload, transactionReceipt, err := buildImplementCloseoutArtifacts(root, feature, audit, reviewRevision)
	if err != nil {
		return writeImplementError(stdout, "blocked", err.Error())
	}
	view := strings.ToLower(strings.TrimSpace(optionValue(args, "--view", "compact")))
	if view != "compact" && view != "full" {
		return writeImplementError(stdout, "usage-error", "--view must be compact or full")
	}
	payload := map[string]any{
		"status":                 "ok",
		"feature_dir":            feature,
		"implementation_summary": summaryPayload,
		"implementation_handoff": handoffPayload,
		"transaction":            transactionReceipt,
		"next_command":           "sp-review (Classic) or spx-review (Advanced)",
	}
	if view == "full" {
		payload["artifact_validation"] = map[string]any{
			"status":    "ok",
			"validator": "go-native canonical implementation handoff",
		}
		payload["resume_audit"] = audit
	} else {
		payload["trusted_terminal_state"] = audit["trusted_terminal_state"]
	}
	env = NewEnvelope("ok", "implement closeout completed")
	env.Data = payload
	return writeEnvelope(stdout, env)
}

type implementPolicy struct {
	MaxEpochs int
	BudgetRef string
}

func reserveImplementValidationEpoch(root, feature, stage, purpose, fingerprint string, commands, taskIDs []string) (map[string]any, error) {
	policy, err := implementValidationPolicy(feature)
	if err != nil {
		return nil, err
	}
	if !implementValidStages[stage] {
		return nil, errors.New("validation stage must be implement or review")
	}
	if !implementValidPurposes[purpose] {
		return nil, errors.New("validation purpose must be baseline, convergence, or delivery")
	}
	if (stage == "review") != (purpose == "delivery") {
		return nil, errors.New("implement epochs use baseline/convergence; review epochs use delivery")
	}
	if err := validateImplementActiveStageOwner(feature, stage); err != nil {
		return nil, err
	}
	fingerprint = strings.TrimSpace(fingerprint)
	if fingerprint == "" {
		return nil, errors.New("validation fingerprint is required")
	}
	commands, err = uniqueStrings(commands, "commands", true)
	if err != nil {
		return nil, err
	}
	taskIDs, err = uniqueStrings(taskIDs, "covered_task_ids", false)
	if err != nil {
		return nil, err
	}
	path, err := implementLedgerPath(feature, policy)
	if err != nil {
		return nil, err
	}
	ledger, err := loadImplementValidationLedger(path, feature, policy)
	if err != nil {
		return nil, err
	}
	runs := ledger["runs"].([]any)
	usedAttempts := implementUsedAttempts(runs)
	var gate map[string]any
	var active map[string]any
	for _, raw := range runs {
		run := raw.(map[string]any)
		if run["stage"] == stage && run["purpose"] == purpose {
			gate = run
		}
		if run["status"] == "running" {
			active = run
		}
	}
	if gate != nil {
		sameScope := gate["fingerprint"] == fingerprint && reflect.DeepEqual(gate["commands"], stringSliceToAny(commands)) && reflect.DeepEqual(gate["covered_task_ids"], stringSliceToAny(taskIDs))
		if gate["status"] == "running" {
			if !sameScope {
				return nil, fmt.Errorf("validation attempt %s is already running", gate["attempt_id"])
			}
			return implementRunResponse(gate, runs, true, policy, len(runs), usedAttempts), nil
		}
		if active != nil && active["run_id"] != gate["run_id"] {
			return nil, fmt.Errorf("validation attempt %s is already running", active["attempt_id"])
		}
		if gate["status"] == "passed" && sameScope {
			return implementRunResponse(gate, runs, true, policy, len(runs), usedAttempts), nil
		}
		if gate["status"] == "passed" && purpose == "baseline" {
			return nil, errors.New("passed baseline is immutable; open the convergence gate instead")
		}
		if gate["status"] == "passed" && purpose == "convergence" && implementHandoffFrozen(feature) {
			return nil, errors.New("passed convergence is immutable after implementation-handoff.json is frozen; continue in Review delivery")
		}
		if gate["status"] == "failed" && gate["fingerprint"] == fingerprint {
			return nil, errors.New("failed validation cannot be retried with an unchanged fingerprint")
		}
		attempts := gate["attempts"].([]any)
		attempt := implementAttemptPayload(fmt.Sprintf("%s-A%d", gate["run_id"], len(attempts)+1), fingerprint, commands, taskIDs, "running", nil, nil, "", utcNow())
		gate["attempts"] = append(attempts, attempt)
		syncImplementRunFromAttempt(gate, attempt)
		if err := writeJSONAtomic(path, ledger); err != nil {
			return nil, err
		}
		return implementRunResponse(gate, runs, false, policy, len(runs), usedAttempts+1), nil
	}
	if active != nil {
		return nil, fmt.Errorf("validation attempt %s is already running", active["attempt_id"])
	}
	if len(runs) >= policy.MaxEpochs {
		return nil, fmt.Errorf("validation logical-gate budget exhausted: maximum of %d epochs", policy.MaxEpochs)
	}
	purposes := map[string]bool{}
	for _, raw := range runs {
		purposes[raw.(map[string]any)["purpose"].(string)] = true
	}
	if purpose == "baseline" && len(runs) > 0 {
		return nil, errors.New("baseline is an early optional gate and cannot start after another logical gate")
	}
	if purpose == "convergence" && purposes["delivery"] {
		return nil, errors.New("convergence cannot start after Review delivery")
	}
	for _, raw := range runs {
		run := raw.(map[string]any)
		if run["status"] == "failed" && run["fingerprint"] == fingerprint {
			return nil, errors.New("failed validation cannot be retried with an unchanged fingerprint")
		}
	}
	runID := fmt.Sprintf("V%d", len(runs)+1)
	attempt := implementAttemptPayload(runID+"-A1", fingerprint, commands, taskIDs, "running", nil, nil, "", utcNow())
	run := map[string]any{"run_id": runID, "stage": stage, "purpose": purpose, "attempts": []any{attempt}}
	syncImplementRunFromAttempt(run, attempt)
	ledger["runs"] = append(runs, run)
	if err := writeJSONAtomic(path, ledger); err != nil {
		return nil, err
	}
	return implementRunResponse(run, ledger["runs"].([]any), false, policy, len(runs)+1, usedAttempts+1), nil
}

func implementHandoffFrozen(feature string) bool {
	path := filepath.Join(feature, implementationHandoffFilename)
	if _, err := os.Stat(path); err != nil {
		return false
	}
	payload, err := readImplementJSONMap(path)
	if err != nil {
		return false
	}
	workflow, err := readImplementJSONMap(filepath.Join(feature, "workflow.json"))
	if err != nil {
		return false
	}
	revision, ok := numberAsInt(workflow["revision"])
	if !ok || workflow["stage"] != "implement" || workflow["status"] != "active" {
		return false
	}
	sourceRevision, ok := numberAsInt(payload["source_revision"])
	if !ok || sourceRevision != revision+2 {
		return false
	}
	_, hasCanonicalEntrypoints := payload["official_entrypoints"].([]any)
	_, hasCanonicalScenarios := payload["system_review_scenarios"].([]any)
	return hasCanonicalEntrypoints && hasCanonicalScenarios
}

type implementValidationFinishRequest struct {
	RunID        string
	Status       string
	FailureKind  string
	EvidenceRefs []string
	Summary      string
}

func completeImplementValidationEpoch(root, feature string, request implementValidationFinishRequest) (map[string]any, error) {
	policy, err := implementValidationPolicy(feature)
	if err != nil {
		return nil, err
	}
	status := strings.ToLower(strings.TrimSpace(request.Status))
	if status != "passed" && status != "failed" && status != "interrupted" {
		return nil, errors.New("validation status must be passed, failed, or interrupted")
	}
	failureKind := strings.TrimSpace(request.FailureKind)
	var failure any
	if failureKind != "" {
		failure = failureKind
	}
	if status == "passed" && failureKind != "" {
		return nil, errors.New("passed validation must not declare failure_kind")
	}
	if status == "failed" && failureKind == "" {
		failureKind = "assertion"
		failure = failureKind
	}
	if status == "interrupted" && failureKind == "" {
		failureKind = "runner_terminated"
		failure = failureKind
	}
	if failureKind != "" && !implementValidFailureKinds[failureKind] {
		return nil, errors.New("validation failure_kind must be assertion, verification, harness, environment, runner_timeout, runner_terminated, cancelled, or unknown")
	}
	if status == "failed" && failureKind != "assertion" && failureKind != "verification" {
		return nil, errors.New("failed validation requires assertion or verification failure_kind; runner, harness, and environment loss is interrupted")
	}
	if status == "interrupted" && (failureKind == "assertion" || failureKind == "verification") {
		return nil, errors.New("assertion or verification verdict must be failed, not interrupted")
	}
	evidenceRefs, err := uniqueStrings(request.EvidenceRefs, "evidence_refs", true)
	if err != nil {
		return nil, err
	}
	summary := strings.TrimSpace(request.Summary)
	if summary == "" {
		return nil, errors.New("validation summary is required")
	}
	path, err := implementLedgerPath(feature, policy)
	if err != nil {
		return nil, err
	}
	ledger, err := loadImplementValidationLedger(path, feature, policy)
	if err != nil {
		return nil, err
	}
	runID := strings.TrimSpace(request.RunID)
	var run map[string]any
	for _, raw := range ledger["runs"].([]any) {
		candidate := raw.(map[string]any)
		if candidate["run_id"] == runID {
			run = candidate
			break
		}
	}
	if run == nil {
		return nil, fmt.Errorf("unknown validation run_id: %s", runID)
	}
	if run["status"] != "running" {
		if run["status"] == status && run["failure_kind"] == failure && reflect.DeepEqual(run["evidence_refs"], stringSliceToAny(evidenceRefs)) && run["summary"] == summary {
			runs := ledger["runs"].([]any)
			return implementRunResponse(run, runs, true, policy, len(runs), implementUsedAttempts(runs)), nil
		}
		return nil, fmt.Errorf("validation run %s is already closed", runID)
	}
	if err := validateImplementActiveStageOwner(feature, fmt.Sprint(run["stage"])); err != nil {
		return nil, err
	}
	attempts := run["attempts"].([]any)
	attempt := attempts[len(attempts)-1].(map[string]any)
	attempt["status"] = status
	attempt["failure_kind"] = failure
	attempt["evidence_refs"] = stringSliceToAny(evidenceRefs)
	attempt["summary"] = summary
	attempt["completed_at"] = utcNow()
	syncImplementRunFromAttempt(run, attempt)
	if err := writeJSONAtomic(path, ledger); err != nil {
		return nil, err
	}
	runs := ledger["runs"].([]any)
	return implementRunResponse(run, runs, false, policy, len(runs), implementUsedAttempts(runs)), nil
}

func implementValidationBudgetStatus(root, feature string) (map[string]any, error) {
	policy, err := implementValidationPolicy(feature)
	if err != nil {
		return nil, err
	}
	path, err := implementLedgerPath(feature, policy)
	if err != nil {
		return nil, err
	}
	ledger, err := loadImplementValidationLedger(path, feature, policy)
	if err != nil {
		return nil, err
	}
	runs := ledger["runs"].([]any)
	payload := cloneImplementMap(ledger)
	payload["used_epochs"] = len(runs)
	payload["remaining_epochs"] = policy.MaxEpochs - len(runs)
	payload["remaining_gate_slots"] = policy.MaxEpochs - len(runs)
	payload["new_gate_budget_exhausted"] = len(runs) >= policy.MaxEpochs
	payload["used_attempts"] = implementUsedAttempts(runs)
	payload["ledger_ref"] = policy.BudgetRef
	payload["runs_sha256"] = canonicalJSONSHA256(runs)
	var last map[string]any
	if len(runs) > 0 {
		last = runs[len(runs)-1].(map[string]any)
	}
	payload["next_action"] = implementValidationNextAction(last)
	payload["current_fingerprint"] = implementSnapshotSHA256(root, feature)
	activeStage := ""
	if workflow, err := readJSONObject(filepath.Join(feature, "workflow.json")); err == nil && workflow["status"] == "active" {
		activeStage = strings.TrimSpace(fmt.Sprint(workflow["stage"]))
	}
	payload["attempt_decision"] = implementValidationAttemptDecision(runs, policy.MaxEpochs, payload["current_fingerprint"].(string), activeStage)
	payload["runs"] = runs
	return payload, nil
}

func implementValidationPolicy(feature string) (implementPolicy, error) {
	var raw map[string]any
	for _, name := range []string{"task-index.json", "implementation-handoff.json"} {
		payload, err := readImplementJSONMap(filepath.Join(feature, name))
		if err == nil {
			if policy, ok := payload["validation_policy"].(map[string]any); ok && policy["mode"] == "feature_epochs" {
				raw = policy
				break
			}
			if floor, ok := payload["validation_budget"].(map[string]any); ok && floor["mode"] == "feature_epochs" {
				raw = floor
				break
			}
		}
	}
	if raw == nil {
		return implementPolicy{}, errors.New("task-index.json does not enable feature_epochs validation")
	}
	maxEpochs, ok := numberAsInt(raw["max_epochs"])
	if !ok || maxEpochs != implementMaxValidationEpochs {
		return implementPolicy{}, errors.New("validation max_epochs must equal 3 so Review always retains its delivery gate")
	}
	if raw["budget_scope"] != "implement-review" {
		return implementPolicy{}, errors.New("validation budget_scope must be implement-review")
	}
	ref := strings.TrimSpace(fmt.Sprint(raw["budget_ref"]))
	if ref == "" {
		ref = implementDefaultBudgetRef
	}
	if err := validateSafeRelativeSlashPath(ref); err != nil {
		return implementPolicy{}, fmt.Errorf("validation budget_ref must be a safe relative path")
	}
	if owner, ok := raw["heavy_gate_owner"]; ok && owner != "leader" {
		return implementPolicy{}, errors.New("validation heavy_gate_owner must be leader")
	}
	return implementPolicy{MaxEpochs: maxEpochs, BudgetRef: filepath.ToSlash(ref)}, nil
}

func implementLedgerPath(feature string, policy implementPolicy) (string, error) {
	target := filepath.Join(feature, filepath.FromSlash(policy.BudgetRef))
	rel, err := filepath.Rel(feature, target)
	if err != nil || rel == ".." || strings.HasPrefix(rel, ".."+string(filepath.Separator)) {
		return "", errors.New("validation budget_ref escapes feature_dir")
	}
	return target, nil
}

func implementLedgerHasDuplicateGates(ledger map[string]any) bool {
	runs, ok := ledger["runs"].([]any)
	if !ok {
		return false
	}
	seen := map[string]bool{}
	for _, raw := range runs {
		run, ok := raw.(map[string]any)
		if !ok {
			return false
		}
		key := fmt.Sprint(run["stage"]) + "\x00" + fmt.Sprint(run["purpose"])
		if seen[key] {
			return true
		}
		seen[key] = true
	}
	return false
}

func migrateTransitionalImplementLedger(ledger map[string]any, policy implementPolicy) (map[string]any, error) {
	rawRuns, ok := ledger["runs"].([]any)
	if !ok {
		return nil, errors.New("validation ledger runs must be a list of objects")
	}
	gates := []any{}
	byGate := map[string]map[string]any{}
	normalizationCodes := []any{}
	purposeOrder := map[string]int{"baseline": 0, "convergence": 1, "delivery": 2}
	lastOrder := -1
	for rawIndex, value := range rawRuns {
		raw, ok := value.(map[string]any)
		if !ok {
			return nil, errors.New("validation ledger runs must be a list of objects")
		}
		legacyRunID := strings.TrimSpace(fmt.Sprint(raw["run_id"]))
		if legacyRunID == "" {
			legacyRunID = fmt.Sprintf("V%d", rawIndex+1)
		}
		stage, purpose := fmt.Sprint(raw["stage"]), fmt.Sprint(raw["purpose"])
		if !implementValidStages[stage] || !implementValidPurposes[purpose] || ((stage == "review") != (purpose == "delivery")) {
			return nil, fmt.Errorf("transitional validation %s has incompatible stage/purpose", legacyRunID)
		}
		if purposeOrder[purpose] < lastOrder {
			return nil, errors.New("validation logical gates must remain ordered as baseline, convergence, then delivery")
		}
		lastOrder = purposeOrder[purpose]
		rawAttempts, ok := raw["attempts"].([]any)
		if !ok || len(rawAttempts) == 0 {
			return nil, fmt.Errorf("transitional validation %s attempts must be a non-empty list of objects", legacyRunID)
		}
		for attemptIndex, rawAttempt := range rawAttempts {
			attempt, ok := rawAttempt.(map[string]any)
			if !ok {
				return nil, fmt.Errorf("transitional validation %s attempts must be a non-empty list of objects", legacyRunID)
			}
			if err := validateImplementAttempt(attempt, legacyRunID, attemptIndex+1); err != nil {
				return nil, err
			}
		}
		latest := rawAttempts[len(rawAttempts)-1].(map[string]any)
		for _, field := range []string{"attempt_id", "fingerprint", "commands", "covered_task_ids", "status", "failure_kind", "evidence_refs", "summary", "started_at", "completed_at"} {
			if !reflect.DeepEqual(raw[field], latest[field]) {
				return nil, fmt.Errorf("transitional validation %s %s must match its latest attempt", legacyRunID, field)
			}
		}
		gateKey := stage + "\x00" + purpose
		gate := byGate[gateKey]
		if gate == nil {
			gate = map[string]any{
				"run_id": fmt.Sprintf("V%d", len(gates)+1),
				"stage":  stage, "purpose": purpose, "attempts": []any{},
			}
			gates = append(gates, gate)
			byGate[gateKey] = gate
		} else {
			normalizationCodes = append(normalizationCodes, fmt.Sprintf("%s:duplicate-logical-gate->%s", legacyRunID, gate["run_id"]))
		}
		attempts := gate["attempts"].([]any)
		for _, rawAttempt := range rawAttempts {
			attempt := cloneImplementMap(rawAttempt.(map[string]any))
			attempt["attempt_id"] = fmt.Sprintf("%s-A%d", gate["run_id"], len(attempts)+1)
			attempts = append(attempts, attempt)
			gate["attempts"] = attempts
			syncImplementRunFromAttempt(gate, attempt)
		}
	}
	return map[string]any{
		"version": float64(implementValidationLedgerVersion),
		"mode":    "feature_epochs", "budget_scope": "implement-review",
		"max_epochs": float64(policy.MaxEpochs), "runs": gates,
		"migration": map[string]any{
			"from_version": float64(2), "legacy_run_count": float64(len(rawRuns)),
			"legacy_runs_sha256": canonicalJSONSHA256(rawRuns),
			"legacy_runs":        cloneAny(rawRuns), "normalization_codes": normalizationCodes,
		},
	}, nil
}

func loadImplementValidationLedger(path, feature string, policy implementPolicy) (map[string]any, error) {
	if _, err := os.Stat(path); os.IsNotExist(err) {
		return map[string]any{
			"version":      float64(implementValidationLedgerVersion),
			"mode":         "feature_epochs",
			"budget_scope": "implement-review",
			"max_epochs":   float64(policy.MaxEpochs),
			"runs":         []any{},
		}, nil
	}
	ledger, err := readImplementJSONMap(path)
	if err != nil {
		return nil, fmt.Errorf("invalid validation state at %s: %v", path, err)
	}
	version, _ := numberAsInt(ledger["version"])
	if version == implementValidationLedgerVersion && implementLedgerHasDuplicateGates(ledger) {
		ledger, err = migrateTransitionalImplementLedger(ledger, policy)
		if err != nil {
			return nil, err
		}
	}
	if err := validateImplementLedger(ledger, policy); err != nil {
		return nil, err
	}
	return ledger, nil
}

func validateImplementLedger(ledger map[string]any, policy implementPolicy) error {
	version, _ := numberAsInt(ledger["version"])
	if version != implementValidationLedgerVersion {
		return fmt.Errorf("validation ledger version must be %d", implementValidationLedgerVersion)
	}
	if ledger["mode"] != "feature_epochs" || ledger["budget_scope"] != "implement-review" {
		return errors.New("validation ledger mode and budget_scope must be feature_epochs/implement-review")
	}
	maxEpochs, _ := numberAsInt(ledger["max_epochs"])
	if maxEpochs != policy.MaxEpochs {
		return errors.New("validation ledger max_epochs conflicts with task-index")
	}
	runs, ok := ledger["runs"].([]any)
	if !ok {
		return errors.New("validation ledger runs must be a list of objects")
	}
	if len(runs) > policy.MaxEpochs {
		return errors.New("validation ledger already exceeds its logical-gate budget")
	}
	running := 0
	seenGates := map[string]bool{}
	purposeOrder := map[string]int{"baseline": 0, "convergence": 1, "delivery": 2}
	lastPurposeOrder := -1
	for index, raw := range runs {
		run, ok := raw.(map[string]any)
		if !ok {
			return errors.New("validation ledger runs must be a list of objects")
		}
		runID := fmt.Sprintf("V%d", index+1)
		if run["run_id"] != runID {
			return fmt.Errorf("validation logical gate %d run_id must be %s", index+1, runID)
		}
		stage, purpose := fmt.Sprint(run["stage"]), fmt.Sprint(run["purpose"])
		if !implementValidStages[stage] || !implementValidPurposes[purpose] || ((stage == "review") != (purpose == "delivery")) {
			return fmt.Errorf("validation %s has incompatible stage/purpose", runID)
		}
		if purposeOrder[purpose] <= lastPurposeOrder {
			return errors.New("validation logical gates must remain ordered as baseline, convergence, then delivery")
		}
		lastPurposeOrder = purposeOrder[purpose]
		gateKey := stage + "\x00" + purpose
		if seenGates[gateKey] {
			return fmt.Errorf("validation ledger has duplicate logical gate: %s/%s", stage, purpose)
		}
		seenGates[gateKey] = true
		attempts, ok := run["attempts"].([]any)
		if !ok || len(attempts) == 0 {
			return fmt.Errorf("validation %s attempts must be a non-empty list of objects", runID)
		}
		for attemptIndex, rawAttempt := range attempts {
			attempt, ok := rawAttempt.(map[string]any)
			if !ok {
				return fmt.Errorf("validation %s attempts must be a non-empty list of objects", runID)
			}
			if err := validateImplementAttempt(attempt, runID, attemptIndex+1); err != nil {
				return err
			}
			if attempt["status"] == "running" {
				running++
			}
		}
		latest := attempts[len(attempts)-1].(map[string]any)
		for _, field := range []string{"attempt_id", "fingerprint", "commands", "covered_task_ids", "status", "failure_kind", "evidence_refs", "summary", "started_at", "completed_at"} {
			if !reflect.DeepEqual(run[field], latest[field]) {
				return fmt.Errorf("validation %s %s must match its latest attempt", runID, field)
			}
		}
	}
	if running > 1 {
		return errors.New("validation ledger may contain only one running attempt")
	}
	return nil
}

func validateImplementAttempt(attempt map[string]any, runID string, index int) error {
	expected := fmt.Sprintf("%s-A%d", runID, index)
	if attempt["attempt_id"] != expected {
		return fmt.Errorf("validation %s attempt %d attempt_id must be %s", runID, index, expected)
	}
	if strings.TrimSpace(fmt.Sprint(attempt["fingerprint"])) == "" {
		return fmt.Errorf("validation %s attempt %d fingerprint is required", runID, index)
	}
	if _, err := anyStringList(attempt["commands"], "commands", true); err != nil {
		return err
	}
	status := fmt.Sprint(attempt["status"])
	if !implementValidStatuses[status] {
		return fmt.Errorf("validation %s attempt %d has unsupported status: %s", runID, index, status)
	}
	failureKind := ""
	if attempt["failure_kind"] != nil {
		failureKind = fmt.Sprint(attempt["failure_kind"])
		if !implementValidFailureKinds[failureKind] {
			return fmt.Errorf("validation %s attempt %d has unsupported failure_kind: %s", runID, index, failureKind)
		}
	}
	if (status == "failed" || status == "interrupted") && failureKind == "" {
		return fmt.Errorf("validation %s attempt %d %s requires failure_kind", runID, index, status)
	}
	if (status == "running" || status == "passed") && failureKind != "" {
		return fmt.Errorf("validation %s attempt %d %s must not declare failure_kind", runID, index, status)
	}
	evidence, err := anyStringList(attempt["evidence_refs"], "evidence_refs", false)
	if err != nil {
		return err
	}
	if status != "running" && (len(evidence) == 0 || strings.TrimSpace(fmt.Sprint(attempt["summary"])) == "") {
		return fmt.Errorf("validation %s attempt %d terminal state requires evidence_refs and summary", runID, index)
	}
	return nil
}

func validateImplementActiveStageOwner(feature, stage string) error {
	workflow, err := readImplementJSONMap(filepath.Join(feature, "workflow.json"))
	if err != nil {
		return nil
	}
	if workflow["stage"] != stage || workflow["status"] != "active" {
		return fmt.Errorf("validation %s gate requires active %s workflow ownership", stage, stage)
	}
	return nil
}

func implementAttemptPayload(attemptID, fingerprint string, commands, taskIDs []string, status string, failureKind any, evidenceRefs []string, summary, startedAt string) map[string]any {
	completed := ""
	if status != "running" {
		completed = utcNow()
	}
	return map[string]any{
		"attempt_id":       attemptID,
		"fingerprint":      fingerprint,
		"commands":         stringSliceToAny(commands),
		"covered_task_ids": stringSliceToAny(taskIDs),
		"status":           status,
		"failure_kind":     failureKind,
		"evidence_refs":    stringSliceToAny(evidenceRefs),
		"summary":          summary,
		"started_at":       startedAt,
		"completed_at":     completed,
	}
}

func syncImplementRunFromAttempt(run, attempt map[string]any) {
	for _, field := range []string{"attempt_id", "fingerprint", "commands", "covered_task_ids", "status", "failure_kind", "evidence_refs", "summary", "started_at", "completed_at"} {
		run[field] = attempt[field]
	}
}

func implementRunResponse(run map[string]any, runs []any, reused bool, policy implementPolicy, usedEpochs, usedAttempts int) map[string]any {
	payload := cloneImplementMap(run)
	payload["reused"] = reused
	payload["ledger_ref"] = policy.BudgetRef
	payload["max_epochs"] = policy.MaxEpochs
	payload["used_epochs"] = usedEpochs
	payload["remaining_epochs"] = policy.MaxEpochs - usedEpochs
	payload["remaining_gate_slots"] = policy.MaxEpochs - usedEpochs
	payload["new_gate_budget_exhausted"] = usedEpochs >= policy.MaxEpochs
	payload["used_attempts"] = usedAttempts
	payload["next_action"] = implementValidationNextAction(run)
	payload["attempt_decision"] = implementValidationAttemptDecision(runs, policy.MaxEpochs, fmt.Sprint(run["fingerprint"]), fmt.Sprint(run["stage"]))
	return payload
}

func implementValidationAttemptDecision(runs []any, maxEpochs int, currentFingerprint, activeStage string) map[string]any {
	if len(runs) == 0 {
		return map[string]any{
			"action": "open_logical_gate", "can_start_attempt": true,
			"gate_id": "", "next_attempt_id": "V1-A1",
			"requires_new_fingerprint": false, "reason_code": "no-validation-history",
		}
	}
	run := runs[len(runs)-1].(map[string]any)
	runID := fmt.Sprint(run["run_id"])
	attemptCount := 1
	if attempts, ok := run["attempts"].([]any); ok {
		attemptCount = len(attempts)
	}
	nextAttemptID := fmt.Sprintf("%s-A%d", runID, attemptCount+1)
	status := fmt.Sprint(run["status"])
	recordedFingerprint := fmt.Sprint(run["fingerprint"])
	fingerprintChanged := strings.TrimSpace(currentFingerprint) != "" && currentFingerprint != recordedFingerprint
	decision := map[string]any{
		"gate_id": runID, "next_attempt_id": nextAttemptID,
		"requires_new_fingerprint": false,
	}
	switch {
	case status == "running":
		decision["action"] = "resume_running_attempt"
		decision["can_start_attempt"] = false
		decision["next_attempt_id"] = fmt.Sprint(run["attempt_id"])
		decision["reason_code"] = "attempt-already-running"
	case status == "interrupted":
		decision["action"] = "retry_same_gate"
		decision["can_start_attempt"] = true
		decision["reason_code"] = "attempt-interrupted"
	case status == "failed" && fingerprintChanged:
		decision["action"] = "retry_same_gate"
		decision["can_start_attempt"] = true
		decision["reason_code"] = "failed-attempt-repaired"
	case status == "failed":
		decision["action"] = "repair_before_retry"
		decision["can_start_attempt"] = false
		decision["requires_new_fingerprint"] = true
		decision["reason_code"] = "failed-attempt-unchanged-fingerprint"
	case status == "passed" && fingerprintChanged && activeStage == "review" && run["purpose"] == "convergence" && len(runs) < maxEpochs:
		decision["action"] = "open_logical_gate"
		decision["can_start_attempt"] = true
		decision["gate_id"] = ""
		decision["next_attempt_id"] = fmt.Sprintf("V%d-A1", len(runs)+1)
		decision["reason_code"] = "review-owned-repair-needs-delivery-proof"
	case status == "passed" && fingerprintChanged && run["purpose"] != "baseline":
		decision["action"] = "retry_same_gate"
		decision["can_start_attempt"] = true
		decision["reason_code"] = "snapshot-changed-after-pass"
	case len(runs) < maxEpochs && run["purpose"] != "delivery":
		decision["action"] = "open_logical_gate"
		decision["can_start_attempt"] = true
		decision["gate_id"] = ""
		decision["next_attempt_id"] = fmt.Sprintf("V%d-A1", len(runs)+1)
		decision["reason_code"] = "next-logical-gate-available"
	default:
		decision["action"] = "validation_complete"
		decision["can_start_attempt"] = false
		decision["next_attempt_id"] = ""
		decision["reason_code"] = "latest-gate-passed"
	}
	return decision
}

func implementValidationNextAction(run map[string]any) string {
	if run == nil {
		return "Open the next applicable logical validation gate."
	}
	switch run["status"] {
	case "running":
		return "Run or resume this exact attempt. If its runner no longer exists, finish it as interrupted before starting the retry."
	case "interrupted":
		if run["failure_kind"] == "runner_timeout" {
			return "Do not rerun the whole gate blindly. Determine whether the suite legitimately exceeds the runner ceiling; isolate the last active test with open-handle/process-exit diagnostics, or split the recorded command into deterministic bounded shards, then retry this same logical gate."
		}
		return "Repair or re-establish the runner/harness, then retry this same logical gate; no additional gate is consumed."
	case "failed":
		return "Diagnose and repair the assertion or verification failure, produce a new source fingerprint, then retry this same logical gate."
	default:
		return "Continue to the next applicable logical gate; do not rerun the same scope on an unchanged fingerprint."
	}
}

func implementUsedAttempts(runs []any) int {
	total := 0
	for _, raw := range runs {
		if attempts, ok := raw.(map[string]any)["attempts"].([]any); ok {
			total += len(attempts)
		}
	}
	return total
}

func proposeImplementationDeferral(root, feature string, raw map[string]any) (map[string]any, error) {
	normalized, err := normalizeImplementDeferralProposal(feature, raw)
	if err != nil {
		return nil, err
	}
	if err := validateImplementBlockerRefs(feature, normalized); err != nil {
		return nil, err
	}
	proposalSHA := canonicalJSONSHA256(normalized)
	sourceFingerprint := implementSnapshotSHA256(root, feature)
	identity := canonicalJSONSHA256(map[string]any{"proposal_sha256": proposalSHA, "source_fingerprint": sourceFingerprint})
	deferralID := "DEF-" + identity[:12]
	path := filepath.Join(feature, filepath.FromSlash(implementDeferralDirRef), deferralID+".json")
	if existing, err := readImplementJSONMap(path); err == nil {
		return map[string]any{
			"status":                existing["status"],
			"reused":                true,
			"deferral_id":           deferralID,
			"proposal_sha256":       proposalSHA,
			"path":                  path,
			"confirmation_required": existing["status"] != "confirmed",
		}, nil
	}
	record := map[string]any{
		"version":            1,
		"schema_ref":         implementDeferralSchemaRef,
		"deferral_id":        deferralID,
		"status":             "proposed",
		"source_stage":       "implement",
		"source_fingerprint": sourceFingerprint,
		"proposal":           normalized,
		"proposal_sha256":    proposalSHA,
		"confirmation":       nil,
	}
	if err := writeJSONAtomic(path, record); err != nil {
		return nil, err
	}
	return map[string]any{
		"status":                "proposed",
		"reused":                false,
		"deferral_id":           deferralID,
		"proposal_sha256":       proposalSHA,
		"path":                  path,
		"confirmation_required": true,
	}, nil
}

type implementDeferralConfirmRequest struct {
	DeferralID         string
	ProposalSHA256     string
	ConfirmationSource string
	Statement          string
}

func confirmImplementationDeferral(root, feature string, request implementDeferralConfirmRequest) (map[string]any, error) {
	deferralID := strings.TrimSpace(request.DeferralID)
	if !implementDeferralIDRE.MatchString(deferralID) {
		return nil, fmt.Errorf("invalid deferral_id: %s", deferralID)
	}
	proposalSHA := strings.TrimSpace(request.ProposalSHA256)
	if proposalSHA == "" {
		return nil, errors.New("proposal_sha256 must be a non-empty string")
	}
	source := strings.TrimSpace(request.ConfirmationSource)
	statement := strings.TrimSpace(request.Statement)
	if source == "" || statement == "" {
		return nil, errors.New("confirmation_source and statement must be non-empty")
	}
	path := filepath.Join(feature, filepath.FromSlash(implementDeferralDirRef), deferralID+".json")
	record, err := readImplementJSONMap(path)
	if err != nil {
		return nil, fmt.Errorf("unknown deferral_id: %s", deferralID)
	}
	proposal, ok := record["proposal"].(map[string]any)
	if !ok {
		return nil, errors.New("deferral proposal is malformed")
	}
	actualSHA := canonicalJSONSHA256(proposal)
	if actualSHA != record["proposal_sha256"] || actualSHA != proposalSHA {
		return nil, errors.New("proposal sha256 does not match the immutable deferral proposal")
	}
	if record["status"] == "confirmed" {
		confirmation, _ := record["confirmation"].(map[string]any)
		if confirmation["source"] == source && confirmation["statement"] == statement {
			return map[string]any{
				"status": "confirmed", "reused": true, "deferral_id": deferralID,
				"proposal_sha256": actualSHA, "confirmation_id": confirmation["confirmation_id"],
				"path": path, "disposition": "transferred_to_review",
			}, nil
		}
		return nil, errors.New("confirmed deferrals are immutable; create a new proposal")
	}
	if record["status"] != "proposed" {
		return nil, fmt.Errorf("deferral cannot be confirmed from status %v", record["status"])
	}
	if record["source_fingerprint"] != implementSnapshotSHA256(root, feature) {
		return nil, errors.New("deferral proposal is stale for the current implementation; propose the same exact scope again to obtain a new DEF id")
	}
	if err := validateImplementBlockerRefs(feature, proposal); err != nil {
		return nil, err
	}
	relativeRef := filepath.ToSlash(filepath.Join(implementDeferralDirRef, deferralID+".json"))
	if err := bindImplementTaskBlockers(feature, proposal, relativeRef); err != nil {
		return nil, err
	}
	fingerprint := implementSnapshotSHA256(root, feature)
	confirmationID := "HC-" + sha256String(actualSHA + "\x00" + source + "\x00" + statement + "\x00" + fingerprint)[:24]
	record["status"] = "confirmed"
	record["confirmation"] = map[string]any{
		"actor":                      "human",
		"source":                     source,
		"statement":                  statement,
		"confirmation_id":            confirmationID,
		"confirmed_payload_sha256":   actualSHA,
		"implementation_fingerprint": fingerprint,
	}
	if err := writeJSONAtomic(path, record); err != nil {
		return nil, err
	}
	return map[string]any{
		"status": "confirmed", "reused": false, "deferral_id": deferralID,
		"proposal_sha256": actualSHA, "confirmation_id": confirmationID,
		"path": path, "disposition": "transferred_to_review",
	}, nil
}

func normalizeImplementDeferralProposal(feature string, raw map[string]any) (map[string]any, error) {
	for key := range raw {
		if !implementAllowedProposalFields[key] {
			return nil, fmt.Errorf("deferral proposal contains unsupported fields: %s", key)
		}
	}
	blockerRefs, err := anyStringList(raw["blocker_refs"], "blocker_refs", true)
	if err != nil {
		return nil, err
	}
	for _, blocker := range blockerRefs {
		if !implementTaskBlockerRefRE.MatchString(blocker) && !implementValidationBlockerRE.MatchString(blocker) {
			return nil, fmt.Errorf("unsupported blocker_ref: %s", blocker)
		}
	}
	taskIDs, err := anyStringList(raw["affected_task_ids"], "affected_task_ids", true)
	if err != nil {
		return nil, err
	}
	for index, taskID := range taskIDs {
		taskIDs[index] = strings.ToUpper(taskID)
		if !implementTaskIDRE.MatchString(taskIDs[index]) {
			return nil, errors.New("affected_task_ids must contain canonical Txx identifiers")
		}
	}
	acceptanceRefs, err := anyStringList(rawOrDefault(raw, "affected_acceptance_refs", []any{}), "affected_acceptance_refs", false)
	if err != nil {
		return nil, err
	}
	knownAcceptance := taskIndexAcceptanceRefs(feature)
	if len(knownAcceptance) > 0 && len(acceptanceRefs) == 0 {
		return nil, errors.New("affected_acceptance_refs must identify the frozen acceptance scope")
	}
	for _, ref := range acceptanceRefs {
		if len(knownAcceptance) > 0 && !knownAcceptance[ref] {
			return nil, fmt.Errorf("deferral references unknown acceptance refs: %s", ref)
		}
	}
	purposes, err := anyStringList(rawOrDefault(raw, "deferred_validation_purposes", []any{}), "deferred_validation_purposes", false)
	if err != nil {
		return nil, err
	}
	for index, purpose := range purposes {
		purpose = strings.ToLower(purpose)
		purposes[index] = purpose
		if purpose != "baseline" && purpose != "convergence" {
			return nil, errors.New("Implement may defer only baseline or convergence validation")
		}
		if !stringInSlice("VALIDATION-"+strings.ToUpper(purpose), blockerRefs) {
			return nil, fmt.Errorf("deferred validation purpose %s requires blocker_ref VALIDATION-%s", purpose, strings.ToUpper(purpose))
		}
	}
	risk := strings.ToLower(requiredText(raw["risk_severity"], "risk_severity"))
	if risk != "low" && risk != "medium" {
		return nil, errors.New("only low or medium delivery risk may be deferred; high/critical risk remains a hard blocker")
	}
	owner := strings.ToLower(requiredText(raw["downstream_owner"], "downstream_owner"))
	if owner != "review" {
		return nil, errors.New("Implement deferrals must transfer ownership to Review")
	}
	deferUntil := strings.ToLower(requiredText(raw["defer_until"], "defer_until"))
	if deferUntil != "review" {
		return nil, errors.New("Implement deferrals expire at Review and cannot waive final delivery")
	}
	artifact := requiredText(raw["downstream_artifact"], "downstream_artifact")
	if artifact != "implementation-handoff.json" {
		return nil, errors.New("Implement deferrals must be carried by implementation-handoff.json")
	}
	claims, err := anyStringList(raw["claims_withheld"], "claims_withheld", true)
	if err != nil {
		return nil, err
	}
	return map[string]any{
		"blocker_refs":                 stringSliceToAny(blockerRefs),
		"affected_task_ids":            stringSliceToAny(taskIDs),
		"affected_acceptance_refs":     stringSliceToAny(acceptanceRefs),
		"deferred_validation_purposes": stringSliceToAny(purposes),
		"exact_excluded_behavior":      requiredText(raw["exact_excluded_behavior"], "exact_excluded_behavior"),
		"residual_risk":                requiredText(raw["residual_risk"], "residual_risk"),
		"risk_severity":                risk,
		"claims_withheld":              stringSliceToAny(claims),
		"reopen_or_stop_condition":     requiredText(raw["reopen_or_stop_condition"], "reopen_or_stop_condition"),
		"downstream_artifact":          artifact,
		"downstream_owner":             owner,
		"defer_until":                  deferUntil,
	}, nil
}

func validateImplementBlockerRefs(feature string, proposal map[string]any) error {
	taskIDs := listToStringSet(proposal["affected_task_ids"])
	for _, blocker := range listStrings(proposal["blocker_refs"]) {
		match := implementTaskBlockerRefRE.FindStringSubmatch(blocker)
		if match == nil {
			continue
		}
		taskID := match[1]
		if !taskIDs[taskID] {
			return fmt.Errorf("%s task must appear in affected_task_ids", blocker)
		}
		lifecyclePath := filepath.Join(feature, "implementation-review", "tasks", taskID+".json")
		lifecycle, err := readImplementJSONMap(lifecyclePath)
		if err != nil {
			return fmt.Errorf("%s references missing task lifecycle %s", blocker, filepath.Base(lifecyclePath))
		}
		blockers, ok := lifecycle["blockers"].([]any)
		index := mustAtoi(match[2]) - 1
		if !ok || index < 0 || index >= len(blockers) {
			return fmt.Errorf("%s references a missing task blocker", blocker)
		}
		blockerPayload, ok := blockers[index].(map[string]any)
		if !ok {
			return fmt.Errorf("%s references a malformed task blocker", blocker)
		}
		classification := strings.TrimSpace(fmt.Sprint(blockerPayload["classification"]))
		owner := strings.TrimSpace(fmt.Sprint(blockerPayload["owner"]))
		if owner == "agent" || classification == "technical" || classification == "project_cognition_readiness" {
			return fmt.Errorf("%s is agent-owned and must be repaired or routed, not human-deferred", blocker)
		}
		if !map[string]bool{"external": true, "human-action": true, "verification_policy": true, "baseline_timeout": true}[classification] {
			return fmt.Errorf("%s classification %s is not eligible for Implement-to-Review deferral", blocker, classification)
		}
	}
	return nil
}

func bindImplementTaskBlockers(feature string, proposal map[string]any, relativeRef string) error {
	for _, blocker := range listStrings(proposal["blocker_refs"]) {
		match := implementTaskBlockerRefRE.FindStringSubmatch(blocker)
		if match == nil {
			continue
		}
		taskID := match[1]
		index := mustAtoi(match[2]) - 1
		path := filepath.Join(feature, "implementation-review", "tasks", taskID+".json")
		lifecycle, err := readImplementJSONMap(path)
		if err != nil {
			return err
		}
		blockers := lifecycle["blockers"].([]any)
		blockerPayload := blockers[index].(map[string]any)
		blockerPayload["disposition"] = "user_confirmed_deferral"
		blockerPayload["disposition_ref"] = relativeRef
		lifecycle["status"] = "deferred"
		if err := writeJSONAtomic(path, lifecycle); err != nil {
			return err
		}
	}
	return nil
}

func auditImplementResume(root, feature string) map[string]any {
	workflow, workflowErr := loadImplementWorkflowSnapshot(root, feature)
	if workflowErr != nil {
		payload := implementAuditPayload("fail", feature, "workflow-state-invalid", false, "blocked", "Repair workflow.json before resuming implementation.", nil, []string{workflowErr.Error()})
		payload["reason_code"] = "workflow-state-invalid"
		return payload
	}
	if workflow.Status == "blocked" {
		payload := implementAuditPayload("fail", feature, "workflow-blocked", false, "blocked", anyString(valueOrDefault(workflow.Summary, "Resolve the persisted workflow blocker before resuming implementation.")), nil, []string{"workflow.json contains an unresolved blocker"})
		payload["reason_code"] = "workflow-blocked"
		payload["workflow_revision"] = workflow.Revision
		payload["workflow_stage"] = workflow.Stage
		payload["workflow_blocker"] = cloneJSONValue(workflow.Blocker)
		payload["resolution_action"] = cloneJSONValue(workflow.ResolutionAction)
		return payload
	}
	tasks := parseImplementTasks(filepath.Join(feature, "tasks.md"))
	tracker := parseImplementTracker(filepath.Join(feature, "implement-tracker.md"))
	trackerStatus := strings.ToLower(strings.TrimSpace(tracker["status"]))
	if len(tasks) == 0 {
		payload := implementAuditPayload("fail", feature, "task-graph-invalid", false, "blocked", "Recover tasks.md and task-index.json before resuming implementation.", nil, []string{"tasks.md has no task checklist evidence"})
		payload["reason_code"] = "task-graph-invalid"
		return payload
	}
	if index, err := loadReadyImplementTaskIndex(root, feature); err == nil {
		decision := resolveImplementTaskNext(root, feature, index, workflow)
		reasonCode := anyString(decision["reason_code"])
		if reasonCode == "task-state-invalid" {
			gap := fmt.Sprintf("%s: %s", anyString(decision["blocked_task_id"]), anyString(decision["state_error"]))
			payload := implementAuditPayload("fail", feature, "state-conflict", false, "blocked", anyString(decision["recommended_next_action"]), nil, []string{gap})
			payload["reason_code"] = reasonCode
			payload["blocked_task_id"] = decision["blocked_task_id"]
			payload["workflow_revision"] = decision["workflow_revision"]
			payload["lifecycle_ref"] = decision["lifecycle_ref"]
			payload["state_error"] = decision["state_error"]
			return payload
		}
		if reasonCode == "task-reopen-required" {
			gap := fmt.Sprintf("%s: %s", anyString(decision["blocked_task_id"]), anyString(decision["acceptance_error"]))
			payload := implementAuditPayload("fail", feature, "task-recovery-required", false, "blocked", anyString(decision["recommended_next_action"]), nil, []string{gap})
			payload["reason_code"] = "task-reopen-required"
			payload["blocked_task_id"] = decision["blocked_task_id"]
			payload["task_revision"] = decision["task_revision"]
			payload["workflow_revision"] = decision["workflow_revision"]
			payload["acceptance_error"] = decision["acceptance_error"]
			payload["recovery_action"] = cloneJSONValue(decision["recovery_action"])
			return payload
		}
	}
	allChecked := len(tasks) > 0
	for _, task := range tasks {
		if !task.Checked {
			allChecked = false
		}
	}
	terminal := trackerStatus == "resolved" || allChecked
	classification := "clean-active"
	if terminal {
		classification = "terminal-audit-required"
	}
	var gaps []string
	var findings []any
	for _, task := range tasks {
		if !task.Checked {
			continue
		}
		missing := []string{}
		resultPath := filepath.Join(feature, "worker-results", task.ID+".json")
		result, err := readImplementJSONMap(resultPath)
		if err != nil {
			missing = append(missing, "missing worker result")
		} else {
			status := strings.ToLower(strings.TrimSpace(fmt.Sprint(result["status"])))
			if status != "success" && status != "done" && status != "done_with_concerns" {
				missing = append(missing, "worker result is not successful")
			}
			if !resultHasPassedValidation(result) && !featureEpochValidationEnabled(feature) {
				missing = append(missing, "missing passed validation evidence")
			}
		}
		lifecyclePath := filepath.Join(feature, "implementation-review", "tasks", task.ID+".json")
		if lifecycle, err := readImplementJSONMap(lifecyclePath); err == nil {
			if lifecycle["status"] == "blocked" {
				missing = append(missing, "task lifecycle has unresolved blockers")
			}
		}
		if len(missing) > 0 {
			gaps = append(gaps, task.ID+": "+strings.Join(missing, ", "))
		}
		findings = append(findings, map[string]any{"task_id": task.ID, "checked": task.Checked, "result_path": resultPath, "missing_evidence": strings.Join(missing, "; ")})
	}
	if terminal && featureEpochValidationEnabled(feature) {
		status, err := implementValidationBudgetStatus(root, feature)
		if err != nil {
			gaps = append(gaps, err.Error())
		} else if !hasPassedImplementConvergence(status, strings.TrimSpace(fmt.Sprint(status["current_fingerprint"]))) {
			gaps = append(gaps, "shared implement validation has no passed convergence gate for the current implementation fingerprint")
		}
	}
	if terminal && len(gaps) == 0 {
		return implementAuditPayload("pass", feature, classification, true, "resolved", "Terminal implement state has closeout-quality evidence.", findings, []string{})
	}
	if terminal {
		return implementAuditPayload("fail", feature, classification, false, "validating", "Resume sp-implement in validation/recovery mode and close the evidence gaps before reporting completion.", findings, gaps)
	}
	return implementAuditPayload("pass", feature, classification, false, trackerStatus, valueOrDefault(tracker["next_action"], "Resume the recorded implementation batch."), findings, gaps)
}

type implementTask struct {
	ID      string
	Checked bool
	Body    string
}

func parseImplementTasks(path string) []implementTask {
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil
	}
	var tasks []implementTask
	for _, match := range implementTaskLineRE.FindAllStringSubmatch(string(raw), -1) {
		tasks = append(tasks, implementTask{ID: strings.ToUpper(match[2]), Checked: strings.EqualFold(match[1], "x"), Body: strings.TrimSpace(match[3])})
	}
	return tasks
}

func parseImplementTracker(path string) map[string]string {
	raw, err := os.ReadFile(path)
	if err != nil {
		return map[string]string{}
	}
	result := map[string]string{}
	for _, line := range strings.Split(string(raw), "\n") {
		line = strings.TrimSpace(line)
		if strings.Contains(line, ":") {
			parts := strings.SplitN(line, ":", 2)
			result[strings.TrimSpace(parts[0])] = strings.TrimSpace(parts[1])
		}
	}
	return result
}

func implementAuditPayload(status, feature, classification string, trusted bool, recommendedStatus, nextAction string, findings []any, gaps []string) map[string]any {
	return map[string]any{
		"status":                     status,
		"feature_dir":                feature,
		"resume_classification":      classification,
		"trusted_terminal_state":     trusted,
		"task_findings":              findings,
		"join_point_findings":        []any{},
		"open_gaps":                  stringSliceToAny(gaps),
		"recommended_tracker_status": recommendedStatus,
		"recommended_next_action":    nextAction,
	}
}

func implementationCloseoutBlockers(feature string, resumeAudit map[string]any, hookErrors []string) []map[string]any {
	evidence := []any{"resume audit does not trust a terminal implementation state"}
	if gaps, ok := resumeAudit["open_gaps"].([]any); ok && len(gaps) > 0 {
		evidence = gaps
	}
	return []map[string]any{{
		"version": 1, "blocker_id": "IMPLEMENT-RESUME-AUDIT", "code": "implementation-closeout-blocked",
		"workflow": "sp-implement|spx-implement", "stage": "implementation closeout",
		"category": "workflow-validation", "owner": "agent",
		"summary":            "Implementation closeout evidence is incomplete or non-terminal.",
		"details":            "The deterministic closeout gate cannot claim implementation completion from the current recorded evidence.",
		"evidence":           evidence,
		"attempted_recovery": []any{map[string]any{"action": "Run the implementation session-state and resume-audit checks.", "result": "The closeout prerequisites remain unsatisfied."}},
		"exact_next_action":  valueOrDefault(resumeAudit["recommended_next_action"], "Resume implementation and close every recorded evidence gap."),
		"unblock_criteria":   "The resume audit returns status=pass with trusted_terminal_state=true and no open gaps.",
		"affected_scope":     []any{"implementation closeout", "human acceptance handoff"},
		"can_continue":       true, "human_action_required": false, "human_action_guide": nil,
		"resume": map[string]any{"argv": []any{"specify-runtime", "implement", "resume-audit", "--feature-dir", feature, "--format", "json"}},
	}}
}

func buildImplementCloseoutArtifacts(root, feature string, audit map[string]any, sourceRevision int) (map[string]any, map[string]any, fileTransactionReceipt, error) {
	var empty fileTransactionReceipt
	summaryPath := filepath.Join(feature, "implementation-summary.md")
	summaryContent := []byte("# Implementation Summary\n\n" +
		"- Status: " + fmt.Sprint(audit["status"]) + "\n" +
		"- Trusted terminal state: " + fmt.Sprint(audit["trusted_terminal_state"]) + "\n")
	taskIndex, err := readImplementJSONMap(filepath.Join(feature, "task-index.json"))
	if err != nil {
		return nil, nil, empty, errors.New("task-index.json is required before implementation closeout can freeze human acceptance")
	}
	version, _ := numberAsInt(taskIndex["version"])
	if version != 2 || taskIndex["status"] != "ready" {
		return nil, nil, empty, errors.New("task-index.json must use version 2 with status ready before implementation closeout")
	}
	policy, _ := taskIndex["validation_policy"].(map[string]any)
	status, _ := implementValidationBudgetStatus(root, feature)
	fingerprint := implementSnapshotSHA256(root, feature)
	// Normalize string arrays left by older tasks packages into objects so
	// closeout does not fail with "must be an object" after tasks allowed strings.
	if err := normalizeTaskControlRootObjectLists(taskIndex); err != nil {
		return nil, nil, empty, err
	}
	officialEntrypoints, ok := taskIndex["official_entrypoints"].([]any)
	if !ok || len(officialEntrypoints) == 0 {
		return nil, nil, empty, errors.New("task-index.json official_entrypoints are required before implementation closeout (array of objects with id/path or id/command)")
	}
	systemReviewScenarios, ok := taskIndex["system_review_scenarios"].([]any)
	if !ok || len(systemReviewScenarios) == 0 {
		return nil, nil, empty, errors.New("task-index.json system_review_scenarios are required before implementation closeout (array of objects)")
	}
	reviewObligations, ok := taskIndex["review_obligations"].([]any)
	if !ok {
		return nil, nil, empty, errors.New("task-index.json review_obligations must be an array of objects")
	}
	humanAcceptanceObligations, ok := taskIndex["human_acceptance_obligations"].([]any)
	if !ok {
		return nil, nil, empty, errors.New("task-index.json human_acceptance_obligations must be an array of objects")
	}
	humanAcceptanceScenarios, ok := taskIndex["human_acceptance_scenarios"].([]any)
	if !ok {
		return nil, nil, empty, errors.New("task-index.json human_acceptance_scenarios must be an array of objects")
	}
	acceptanceRefs, err := anyStringList(taskIndex["acceptance_refs"], "acceptance_refs", false)
	if err != nil {
		return nil, nil, empty, err
	}
	taskIDs := taskIndexTaskIDs(taskIndex["tasks"])
	userConfirmedDeferrals := []any{}
	payload := map[string]any{
		"version":                          1,
		"status":                           "ready_for_review",
		"source_revision":                  sourceRevision,
		"source_stage":                     "implement",
		"feature_dir":                      feature,
		"implementation_fingerprint":       fingerprint,
		"fingerprint_algorithm":            implementationFingerprintAlgorith,
		"official_entrypoints":             officialEntrypoints,
		"system_review_scenarios":          systemReviewScenarios,
		"review_obligations":               reviewObligations,
		"task_ids":                         taskIDs,
		"acceptance_refs":                  stringSliceToAny(acceptanceRefs),
		"human_acceptance_obligations":     humanAcceptanceObligations,
		"human_acceptance_scenarios":       humanAcceptanceScenarios,
		"human_acceptance_contract_sha256": canonicalJSONSHA256(map[string]any{"human_acceptance_obligations": humanAcceptanceObligations, "human_acceptance_scenarios": humanAcceptanceScenarios}),
		"human_acceptance_contract_origin": "task-index-v2",
		"user_confirmed_deferral_refs":     []any{},
		"user_confirmed_deferrals":         userConfirmedDeferrals,
		"user_confirmed_deferrals_sha256":  canonicalJSONSHA256(map[string]any{"user_confirmed_deferrals": userConfirmedDeferrals}),
		"validation_policy":                policy,
		"validation_budget": map[string]any{
			"mode":                 "feature_epochs",
			"ledger_ref":           implementDefaultBudgetRef,
			"max_epochs":           implementMaxValidationEpochs,
			"used_epochs":          status["used_epochs"],
			"remaining_epochs":     status["remaining_epochs"],
			"consumed_runs_sha256": status["runs_sha256"],
		},
	}
	if previous, err := readImplementJSONMap(filepath.Join(feature, implementationHandoffFilename)); err == nil &&
		previous["source_revision"] == float64(sourceRevision) &&
		previous["human_acceptance_contract_origin"] == "task-index-v2" {
		frozenFields := []string{
			"official_entrypoints",
			"system_review_scenarios",
			"review_obligations",
			"task_ids",
			"acceptance_refs",
			"human_acceptance_obligations",
			"human_acceptance_scenarios",
			"human_acceptance_contract_sha256",
			"human_acceptance_contract_origin",
			"user_confirmed_deferral_refs",
			"user_confirmed_deferrals",
			"user_confirmed_deferrals_sha256",
			"validation_policy",
			"validation_budget",
		}
		previousScope := map[string]any{}
		nextScope := map[string]any{}
		for _, field := range frozenFields {
			previousScope[field] = previous[field]
			nextScope[field] = payload[field]
		}
		if canonicalJSONSHA256(previousScope) != canonicalJSONSHA256(nextScope) {
			return nil, nil, empty, errors.New("implementation-handoff.json scope is already frozen for this workflow revision; reopen the owning Tasks/Implement stages instead of resigning a changed acceptance or Review universe")
		}
	}
	if err := validateCanonicalImplementationHandoff(root, feature, payload); err != nil {
		return nil, nil, empty, fmt.Errorf("generated implementation handoff failed Go-native validation: %w", err)
	}
	handoffContent, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		return nil, nil, empty, err
	}
	handoffContent = append(handoffContent, '\n')
	handoffPath := filepath.Join(feature, "implementation-handoff.json")
	receipt, err := applyFileTransaction(root, "implement.closeout", []fileTransactionUpdate{
		{Path: summaryPath, Content: summaryContent, Perm: 0o644},
		{Path: handoffPath, Content: handoffContent, Perm: 0o644},
	})
	if err != nil {
		return nil, nil, empty, fmt.Errorf("cannot commit implementation closeout: %w", err)
	}
	summaryDigest := sha256.Sum256(summaryContent)
	handoffDigest := sha256.Sum256(handoffContent)
	summaryResult := map[string]any{"status": "ok", "report_path": summaryPath, "sha256": hex.EncodeToString(summaryDigest[:])}
	handoffResult := map[string]any{"status": "ok", "path": handoffPath, "sha256": hex.EncodeToString(handoffDigest[:]), "source_revision": sourceRevision}
	return summaryResult, handoffResult, receipt, nil
}

func implementSnapshotSHA256(root, feature string) string {
	rootAbs, err := filepath.Abs(root)
	if err != nil {
		rootAbs = root
	}
	featureAbs, _ := filepath.Abs(feature)
	if fingerprint, ok := implementGitSnapshotSHA256(rootAbs, featureAbs); ok {
		return fingerprint
	}
	return implementFallbackSnapshotSHA256(rootAbs, featureAbs)
}

func implementGitSnapshotSHA256(rootAbs, featureAbs string) (string, bool) {
	if _, err := exec.LookPath("git"); err != nil {
		return "", false
	}
	head, err := gitCommandOutput(rootAbs, "rev-parse", "HEAD")
	if err != nil {
		return "", false
	}
	pathSet := map[string]bool{}
	for _, args := range [][]string{
		{"diff", "-z", "--name-only", "--relative", "HEAD", "--", "."},
		{"diff", "-z", "--name-only", "--relative", "--cached", "HEAD", "--", "."},
		{"ls-files", "-z", "--others", "--exclude-standard", "--", "."},
	} {
		lines, err := gitCommandNULPaths(rootAbs, args...)
		if err != nil {
			return "", false
		}
		for _, rel := range lines {
			rel = filepath.ToSlash(strings.TrimSpace(rel))
			if rel == "" || !implementFingerprintIncludesPath(rootAbs, featureAbs, rel) {
				continue
			}
			pathSet[rel] = true
		}
	}
	paths := make([]string, 0, len(pathSet))
	for rel := range pathSet {
		paths = append(paths, rel)
	}
	sort.Strings(paths)
	digest := sha256.New()
	digest.Write([]byte("HEAD\n"))
	digest.Write([]byte(strings.TrimSpace(head)))
	for _, rel := range paths {
		digest.Write([]byte("\nPATH\n"))
		digest.Write([]byte(rel))
		raw, err := os.ReadFile(filepath.Join(rootAbs, filepath.FromSlash(rel)))
		if err != nil {
			digest.Write([]byte("\nMISSING"))
			continue
		}
		digest.Write([]byte("\nCONTENT\n"))
		digest.Write(raw)
	}
	return hex.EncodeToString(digest.Sum(nil)), true
}

func implementFallbackSnapshotSHA256(rootAbs, featureAbs string) string {
	ignoreMatcher := ignorepkg.Load(rootAbs)
	var files []string
	_ = filepath.WalkDir(rootAbs, func(path string, d os.DirEntry, err error) error {
		if err != nil {
			return nil
		}
		name := d.Name()
		if d.IsDir() && (name == ".git" || name == "node_modules" || name == ".pytest_cache" || name == "__pycache__") {
			return filepath.SkipDir
		}
		if d.IsDir() {
			if rel, relErr := filepath.Rel(rootAbs, path); relErr == nil {
				rel = filepath.ToSlash(rel)
				if rel != "." && ignoreMatcher.Ignored(rel) && !ignoreMatcher.MayReincludeDescendant(rel) {
					return filepath.SkipDir
				}
			}
			return nil
		}
		rel, err := filepath.Rel(rootAbs, path)
		if err != nil {
			return nil
		}
		rel = filepath.ToSlash(rel)
		if ignoreMatcher.Ignored(rel) {
			return nil
		}
		if !implementFingerprintIncludesPath(rootAbs, featureAbs, rel) {
			return nil
		}
		files = append(files, rel)
		return nil
	})
	sort.Strings(files)
	digest := sha256.New()
	for _, rel := range files {
		digest.Write([]byte(rel))
		raw, err := os.ReadFile(filepath.Join(rootAbs, filepath.FromSlash(rel)))
		if err == nil {
			digest.Write(raw)
		}
	}
	return hex.EncodeToString(digest.Sum(nil))
}

func implementFingerprintIncludesPath(rootAbs, featureAbs, rel string) bool {
	normalized := strings.Trim(filepath.ToSlash(rel), "/")
	if normalized == ".specify/runtime" || strings.HasPrefix(normalized, ".specify/runtime/") {
		return false
	}
	for _, segment := range strings.Split(normalized, "/") {
		if segment == "test-results" || segment == "playwright-report" {
			return false
		}
	}
	excludedNames := map[string]bool{
		"implementation-handoff.json": true, "review-state.json": true, "implementation-summary.md": true,
		"human-acceptance.json": true, "workflow.json": true, "workflow-state.md": true,
		"implementation-review/validation-runs.json": true,
	}
	excludedPrefixes := []string{"review-evidence/", "review-results/", "review-history/", "implementation-review/deferrals/", "implementation-review/validation-evidence/"}
	path := rel
	if !filepath.IsAbs(path) {
		path = filepath.Join(rootAbs, filepath.FromSlash(rel))
	}
	featureRel, err := filepath.Rel(featureAbs, path)
	if err != nil {
		return true
	}
	if featureRel == ".." || strings.HasPrefix(featureRel, ".."+string(filepath.Separator)) {
		return true
	}
	suffix := filepath.ToSlash(featureRel)
	if excludedNames[suffix] || strings.HasSuffix(suffix, ".lock") {
		return false
	}
	for _, prefix := range excludedPrefixes {
		if strings.HasPrefix(suffix, prefix) {
			return false
		}
	}
	return true
}

func gitCommandOutput(dir string, args ...string) (string, error) {
	cmd := exec.Command("git", args...)
	cmd.Dir = dir
	raw, err := cmd.CombinedOutput()
	if err != nil {
		return "", err
	}
	return strings.TrimSpace(string(raw)), nil
}

func gitCommandNULPaths(dir string, args ...string) ([]string, error) {
	cmd := exec.Command("git", args...)
	cmd.Dir = dir
	raw, err := cmd.CombinedOutput()
	if err != nil {
		return nil, err
	}
	if len(raw) == 0 {
		return []string{}, nil
	}
	parts := bytes.Split(raw, []byte{0})
	lines := make([]string, 0, len(parts))
	for _, part := range parts {
		if len(part) != 0 {
			lines = append(lines, string(part))
		}
	}
	return lines, nil
}

func taskIndexTaskIDs(value any) []any {
	items, ok := value.([]any)
	if !ok {
		return []any{}
	}
	out := []any{}
	seen := map[string]bool{}
	for _, raw := range items {
		item, ok := raw.(map[string]any)
		if !ok {
			continue
		}
		taskID := strings.TrimSpace(strings.ToUpper(fmt.Sprint(valueOrDefault(item["task_id"], fmt.Sprint(item["id"])))))
		if taskID == "" || seen[taskID] {
			continue
		}
		seen[taskID] = true
		out = append(out, taskID)
	}
	return out
}

func implementFeatureFromArgs(args []string) (string, string, Envelope, bool) {
	root, err := filepath.Abs(optionValue(args, "--project-root", "."))
	if err != nil {
		return "", "", NewEnvelope("error", "resolve project root: "+err.Error()), false
	}
	if _, err := os.Stat(filepath.Join(root, ".specify")); err != nil {
		env := NewEnvelope("usage-error", "not a Spec Kit Plus project")
		env.Blockers = append(env.Blockers, ".specify directory is required")
		return "", "", env, false
	}
	featureArg := strings.TrimSpace(optionValue(args, "--feature-dir", ""))
	if featureArg == "" {
		env := NewEnvelope("usage-error", "--feature-dir is required")
		env.Blockers = append(env.Blockers, "--feature-dir is required")
		return "", "", env, false
	}
	feature, err := resolveProjectContainedPath(root, featureArg)
	if err != nil {
		env := NewEnvelope("usage-error", "feature_dir must stay inside project_root")
		env.Blockers = append(env.Blockers, err.Error())
		return "", "", env, false
	}
	return root, feature, Envelope{}, true
}

func writeImplementPayload(stdout io.Writer, payload map[string]any, err error, summary string) int {
	if err != nil {
		env := NewEnvelope("blocked", err.Error())
		env.Data = map[string]any{"status": "blocked", "errors": []any{err.Error()}}
		env.Blockers = append(env.Blockers, err.Error())
		return writeEnvelope(stdout, env)
	}
	env := NewEnvelope("ok", summary)
	env.Data = payload
	return writeEnvelope(stdout, env)
}

func writeImplementTaskNextPayload(stdout io.Writer, payload map[string]any, err error) int {
	if err != nil {
		return writeImplementPayload(stdout, payload, err, "next dependency-ready task resolved")
	}
	if payload["status"] != "blocked" {
		return writeImplementPayload(stdout, payload, nil, "next implementation action resolved")
	}
	summary := strings.TrimSpace(anyString(payload["recommended_next_action"]))
	if summary == "" {
		summary = "implementation cannot select a dependency-ready task"
	}
	env := NewEnvelope("blocked", summary)
	env.Data = payload
	if blocker := payload["workflow_blocker"]; blocker != nil {
		env.Blockers = append(env.Blockers, cloneJSONValue(blocker))
	} else if acceptanceError := strings.TrimSpace(anyString(payload["acceptance_error"])); acceptanceError != "" {
		env.Blockers = append(env.Blockers, acceptanceError)
	} else {
		env.Blockers = append(env.Blockers, summary)
	}
	if raw, ok := payload["next_argv"].([]any); ok {
		for _, value := range raw {
			env.NextArgv = append(env.NextArgv, anyString(value))
		}
	}
	return writeEnvelope(stdout, env)
}

func writeImplementError(stdout io.Writer, status, message string) int {
	env := NewEnvelope(status, message)
	env.Blockers = append(env.Blockers, message)
	return writeEnvelope(stdout, env)
}

func readImplementJSONMap(path string) (map[string]any, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var payload map[string]any
	if err := json.Unmarshal(raw, &payload); err != nil {
		return nil, err
	}
	return payload, nil
}

func uniqueStrings(values []string, label string, required bool) ([]string, error) {
	result := []string{}
	seen := map[string]bool{}
	for _, value := range values {
		normalized := strings.TrimSpace(value)
		if normalized == "" {
			return nil, fmt.Errorf("%s must contain nonblank strings", label)
		}
		if !seen[normalized] {
			result = append(result, normalized)
			seen[normalized] = true
		}
	}
	if required && len(result) == 0 {
		return nil, fmt.Errorf("%s must not be empty", label)
	}
	return result, nil
}

func anyStringList(value any, label string, required bool) ([]string, error) {
	list, ok := value.([]any)
	if !ok {
		return nil, fmt.Errorf("%s must be a list", label)
	}
	values := make([]string, 0, len(list))
	for _, raw := range list {
		text, ok := raw.(string)
		if !ok {
			return nil, fmt.Errorf("%s must contain nonblank strings", label)
		}
		values = append(values, text)
	}
	return uniqueStrings(values, label, required)
}

func validateSafeRelativeSlashPath(path string) error {
	if filepath.IsAbs(path) || strings.Contains(path, "\\") {
		return errors.New("unsafe path")
	}
	for _, part := range strings.Split(path, "/") {
		if part == "" || part == "." || part == ".." {
			return errors.New("unsafe path")
		}
	}
	return nil
}

func stringSliceToAny(values []string) []any {
	result := make([]any, len(values))
	for i, value := range values {
		result[i] = value
	}
	return result
}

func cloneImplementMap(input map[string]any) map[string]any {
	output := map[string]any{}
	for key, value := range input {
		output[key] = value
	}
	return output
}

func utcNow() string {
	return time.Now().UTC().Format(time.RFC3339Nano)
}

func numberAsInt(value any) (int, bool) {
	switch typed := value.(type) {
	case int:
		return typed, true
	case float64:
		if typed == float64(int(typed)) {
			return int(typed), true
		}
	}
	return 0, false
}

func rawOrDefault(raw map[string]any, key string, fallback any) any {
	if value, ok := raw[key]; ok {
		return value
	}
	return fallback
}

func requiredText(value any, label string) string {
	text, ok := value.(string)
	if !ok || strings.TrimSpace(text) == "" {
		panic(label + " must be a non-empty string")
	}
	return strings.TrimSpace(text)
}

func taskIndexAcceptanceRefs(feature string) map[string]bool {
	payload, err := readImplementJSONMap(filepath.Join(feature, "task-index.json"))
	if err != nil {
		return map[string]bool{}
	}
	return listToStringSet(payload["acceptance_refs"])
}

func listStrings(value any) []string {
	list, _ := anyStringList(value, "list", false)
	return list
}

func mustAtoi(value string) int {
	var result int
	_, _ = fmt.Sscanf(value, "%d", &result)
	return result
}

func featureEpochValidationEnabled(feature string) bool {
	_, err := implementValidationPolicy(feature)
	return err == nil
}

func resultHasPassedValidation(result map[string]any) bool {
	for _, raw := range result["validation_results"].([]any) {
		item, ok := raw.(map[string]any)
		if ok && item["status"] == "passed" {
			return true
		}
	}
	return false
}

func hasPassedImplementConvergence(status map[string]any, currentFingerprint string) bool {
	runs, _ := status["runs"].([]any)
	for _, raw := range runs {
		run := raw.(map[string]any)
		if run["stage"] == "implement" && run["purpose"] == "convergence" && run["status"] == "passed" && strings.TrimSpace(fmt.Sprint(run["fingerprint"])) == currentFingerprint {
			return true
		}
	}
	return false
}

func valueOrDefault(value any, fallback string) string {
	text := strings.TrimSpace(fmt.Sprint(value))
	if text == "" || text == "<nil>" {
		return fallback
	}
	return text
}
