package main

import (
	"bytes"
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"regexp"
	"runtime"
	"sort"
	"strconv"
	"strings"
	"time"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/filelock"
)

const (
	learningMachineBegin = "<!-- SPECKIT_LEARNING_DATA_BEGIN -->"
	learningMachineEnd   = "<!-- SPECKIT_LEARNING_DATA_END -->"
)

var learningTypes = map[string]bool{
	"pitfall": true, "recovery_path": true, "user_preference": true, "workflow_gap": true,
	"project_constraint": true, "routing_mistake": true, "verification_gap": true,
	"state_surface_gap": true, "map_coverage_gap": true, "tooling_trap": true,
	"false_lead_pattern": true, "near_miss": true, "decision_debt": true,
}

var learningStatuses = map[string]bool{"candidate": true, "confirmed": true, "promoted-rule": true}
var learningSignals = map[string]bool{"low": true, "medium": true, "high": true}
var learningContextKeyMap = map[string]string{
	"component": "components", "operation_owner": "operation_owners", "consumer_owner": "consumer_owners",
	"outcome": "outcomes", "state": "states", "entrypoint": "entrypoints", "validation_surface": "validation_surfaces",
}
var learningFacetKeys = []string{"components", "operation_owners", "consumer_owners", "outcomes", "states", "entrypoints", "validation_surfaces"}
var mapWorkflowCommands = []string{"sp-map-scan", "sp-map-build", "sp-map-update", "sp-map-rebuild"}
var knownLearningCommands = []string{
	"sp-accept", "sp-analyze", "sp-ask", "sp-auto", "sp-checklist", "sp-clarify", "sp-constitution",
	"sp-debug", "sp-deep-research", "sp-design", "sp-discussion", "sp-explain", "sp-fast", "sp-implement",
	"sp-implement-teams", "sp-integrate", "sp-map-scan", "sp-map-build", "sp-map-update", "sp-map-rebuild",
	"sp-plan", "sp-prd", "sp-prd-build", "sp-prd-scan", "sp-quick", "sp-specify", "sp-tasks", "sp-taskstoissues", "sp-team",
}

var workflowStateAutoCaptureCommands = map[string]bool{
	"sp-constitution": true, "sp-specify": true, "sp-clarify": true, "sp-deep-research": true,
	"sp-plan": true, "sp-checklist": true, "sp-tasks": true, "sp-analyze": true, "sp-accept": true,
	"sp-prd-scan": true, "sp-prd-build": true, "sp-map-scan": true, "sp-map-build": true,
	"sp-map-update": true, "sp-map-rebuild": true,
}

type learningService struct {
	projectRoot string
}

type learningPaths struct {
	constitution           string
	projectRules           string
	confirmedLearnings     string
	learningIndex          string
	learningDetailTemplate string
	candidates             string
	review                 string
	reviewState            string
	metrics                string
}

type learningSuggestion struct {
	learningType      string
	summary           string
	evidence          string
	recurrenceKey     string
	signalStrength    string
	appliesTo         []string
	problem           string
	recommendedAction string
	triggerSignals    []string
	successCriteria   []string
	avoid             []string
	exceptions        []string
}

func runLearning(args []string, stdout io.Writer) int {
	if len(args) == 0 {
		return writeEnvelope(stdout, NewEnvelope("usage-error", "missing learning subcommand"))
	}
	service := learningService{projectRoot: optionValue(args, "--project-root", ".")}
	env, err := service.run(args)
	if err != nil {
		blocked := NewEnvelope("blocked", "learning command failed")
		policy, _, _ := service.loadLearningPolicy(false)
		blocked.Blockers = append(blocked.Blockers, redactLearningTextWithPolicy(err.Error(), policy).text)
		blocked.Data["error_code"] = "learning-runtime-error"
		return writeEnvelope(stdout, blocked)
	}
	return writeEnvelope(stdout, env)
}

func (service learningService) run(args []string) (Envelope, error) {
	command := args[0]
	switch command {
	case "start":
		data, err := service.start(optionValue(args, "--command", ""), parseLearningContexts(optionValues(args, "--context")))
		return learningDataEnvelope("learning start completed", data), err
	case "list":
		cursor, _ := strconv.Atoi(optionValue(args, "--cursor", "0"))
		limit, _ := strconv.Atoi(optionValue(args, "--limit", "50"))
		data, err := service.list(learningListRequest{
			commandName:  optionValue(args, "--command", ""),
			learningType: optionValue(args, "--type", ""),
			status:       optionValue(args, "--status", ""),
			query:        optionValue(args, "--query", ""),
			context:      parseLearningContexts(optionValues(args, "--context")),
			cursor:       cursor,
			limit:        limit,
			includeAll:   hasFlag(args, "--all"),
		})
		return learningDataEnvelope("learning list completed", data), err
	case "show":
		data, err := service.show(optionValue(args, "--ref", ""))
		return learningDataEnvelope("learning show completed", data), err
	case "capture":
		data, err := service.capture(learningCaptureRequest{
			source:            "manual",
			commandName:       optionValue(args, "--command", ""),
			learningType:      optionValue(args, "--type", ""),
			summary:           optionValue(args, "--summary", ""),
			evidence:          optionValue(args, "--evidence", ""),
			recurrenceKey:     optionValue(args, "--recurrence-key", ""),
			signalStrength:    optionValue(args, "--signal", "medium"),
			appliesTo:         optionValues(args, "--applies-to"),
			defaultScope:      optionValue(args, "--scope", ""),
			confirm:           hasFlag(args, "--confirm"),
			painScore:         optionValue(args, "--pain-score", ""),
			falseStarts:       optionValues(args, "--false-start"),
			rejectedPaths:     optionValues(args, "--rejected-path"),
			decisiveSignal:    optionValue(args, "--decisive-signal", ""),
			rootCauseFamily:   optionValue(args, "--root-cause-family", ""),
			injectionTargets:  optionValues(args, "--injection-target"),
			promotionHint:     optionValue(args, "--promotion-hint", ""),
			problem:           optionValue(args, "--problem", ""),
			recommendedAction: optionValue(args, "--action", ""),
			avoid:             optionValues(args, "--avoid"),
			triggerSignals:    optionValues(args, "--trigger"),
			successCriteria:   optionValues(args, "--success"),
			exceptions:        optionValues(args, "--exception"),
			facets:            parseLearningContexts(optionValues(args, "--context")),
		})
		return learningDataEnvelope("learning capture completed", data), err
	case "capture-auto":
		data, err := service.captureAuto(optionValue(args, "--command", ""), optionValue(args, "--feature-dir", ""), optionValue(args, "--workspace", ""), optionValue(args, "--session-file", ""), hasFlag(args, "--dry-run"))
		return learningDataEnvelope("learning capture-auto completed", data), err
	case "promote":
		data, err := service.promote(optionValue(args, "--recurrence-key", ""), optionValue(args, "--target", ""))
		return learningDataEnvelope("learning promote completed", data), err
	case "review":
		data, err := service.review(optionValue(args, "--command", ""), optionValue(args, "--decision", ""), optionValue(args, "--rationale", ""), optionValue(args, "--recurrence-key", ""))
		return learningDataEnvelope("learning review completed", data), err
	case "status":
		data, err := service.learningStatus(optionValue(args, "--command", ""))
		return learningDataEnvelope("learning status completed", data), err
	case "metrics":
		data, err := service.learningMetrics(optionValue(args, "--command", ""))
		return learningDataEnvelope("learning metrics completed", data), err
	default:
		return Envelope{}, fmt.Errorf("unknown learning subcommand %q", command)
	}
}

func learningDataEnvelope(summary string, data map[string]any) Envelope {
	env := NewEnvelope("ok", summary)
	env.Data = data
	return env
}

type learningListRequest struct {
	commandName, learningType, status, query string
	context                                  map[string][]string
	cursor, limit                            int
	includeAll                               bool
	startMode                                bool
}

type learningCaptureRequest struct {
	source                                                                                    string
	commandName, learningType, summary, evidence, recurrenceKey, signalStrength, defaultScope string
	confirm                                                                                   bool
	painScore, decisiveSignal, rootCauseFamily, promotionHint, problem, recommendedAction     string
	appliesTo, falseStarts, rejectedPaths, injectionTargets, avoid, triggerSignals            []string
	successCriteria, exceptions                                                               []string
	facets                                                                                    map[string][]string
}

func (service learningService) paths() (learningPaths, error) {
	memoryDir, err := secureProjectPath(service.projectRoot, ".specify/memory")
	if err != nil {
		return learningPaths{}, err
	}
	learningMemoryDir, err := secureProjectPath(service.projectRoot, ".specify/memory/learnings")
	if err != nil {
		return learningPaths{}, err
	}
	learningDir, err := secureProjectPath(service.projectRoot, ".planning/learnings")
	if err != nil {
		return learningPaths{}, err
	}
	template, err := secureProjectPath(service.projectRoot, ".specify/templates/project-learning-detail-template.md")
	if err != nil {
		return learningPaths{}, err
	}
	return learningPaths{
		constitution: filepath.Join(memoryDir, "constitution.md"), projectRules: filepath.Join(memoryDir, "project-rules.md"),
		confirmedLearnings: filepath.Join(learningMemoryDir, "confirmed.md"), learningIndex: filepath.Join(learningMemoryDir, "INDEX.md"),
		learningDetailTemplate: template, candidates: filepath.Join(learningDir, "candidates.md"), review: filepath.Join(learningDir, "review.md"),
		reviewState: filepath.Join(learningDir, "review-state.json"), metrics: filepath.Join(learningDir, "metrics.json"),
	}, nil
}

func (paths learningPaths) toMap() map[string]any {
	return map[string]any{
		"constitution": paths.constitution, "project_rules": paths.projectRules, "confirmed_learnings": paths.confirmedLearnings,
		"learning_index": paths.learningIndex, "learning_detail_template": paths.learningDetailTemplate,
		"candidates": paths.candidates, "review": paths.review, "review_state": paths.reviewState, "metrics": paths.metrics,
	}
}

func (service learningService) withLock(fn func(learningPaths) (map[string]any, error)) (map[string]any, error) {
	paths, err := service.paths()
	if err != nil {
		return nil, err
	}
	lockPath := filepath.Join(filepath.Dir(paths.review), ".learning.lock")
	if err := os.MkdirAll(filepath.Dir(lockPath), 0o755); err != nil {
		return nil, err
	}
	release, err := filelock.Acquire(lockPath)
	if err != nil {
		return nil, err
	}
	defer release()
	if err := service.ensureFiles(paths, true); err != nil {
		return nil, err
	}
	return fn(paths)
}

func (service learningService) ensureFiles(paths learningPaths, includeRuntime bool) error {
	seeds := []struct{ path, text string }{
		{paths.projectRules, learningRulesTemplateText()},
		{paths.confirmedLearnings, learningConfirmedTemplateText()},
		{paths.learningIndex, learningIndexTemplateText()},
	}
	if includeRuntime {
		seeds = append(seeds, struct{ path, text string }{paths.candidates, learningCandidatesTemplateText()}, struct{ path, text string }{paths.review, learningReviewTemplateText()})
	}
	for _, seed := range seeds {
		if _, err := os.Stat(seed.path); err == nil {
			continue
		} else if !os.IsNotExist(err) {
			return err
		}
		if err := os.MkdirAll(filepath.Dir(seed.path), 0o755); err != nil {
			return err
		}
		if err := writeCreateOnly(seed.path, []byte(seed.text)); err != nil && !os.IsExist(err) {
			return err
		}
	}
	return nil
}

func (service learningService) start(commandName string, context map[string][]string) (map[string]any, error) {
	paths, err := service.paths()
	if err != nil {
		return nil, err
	}
	normalized, err := normalizeLearningCommand(commandName)
	if err != nil {
		return nil, err
	}
	policy, _, _ := service.loadLearningPolicy(false)
	normalized = safeLearningCommandProjection(normalized, policy)
	context = sanitizeLearningContextsWithPolicy(context, policy)
	list, err := service.list(learningListRequest{commandName: normalized, context: context, limit: 20, startMode: true})
	if err != nil {
		return nil, err
	}
	candidates := readLearningEntriesIfPresent(paths.candidates)
	promotionReady := []any{}
	needsConfirmation := []any{}
	for _, entry := range candidates {
		entry = applyLearningAssessment(sanitizeLearningEntryWithPolicy(entry, policy), "")
		if !learningEntryRelevantToCommand(entry, normalized) {
			continue
		}
		if intFromAny(entry["occurrence_count"]) >= 2 {
			promotionReady = append(promotionReady, map[string]any{"ref": entry["recurrence_key"], "summary": entry["summary"], "occurrences": entry["occurrence_count"]})
		}
		if learningHighestSignal(entry) {
			needsConfirmation = append(needsConfirmation, map[string]any{"ref": entry["recurrence_key"], "summary": entry["summary"], "signal": entry["signal_strength"]})
		}
	}
	payload := map[string]any{
		"schema_version":     float64(1),
		"record_schema":      ".specify/templates/project-learning-record-schema.json#/$defs/startSummary",
		"command":            safeLearningCommandProjection(normalized, policy),
		"policy":             learningWorkflowPolicy(normalized),
		"read_only":          true,
		"items":              list["items"],
		"pagination":         list["pagination"],
		"promotion_ready":    promotionReady,
		"needs_confirmation": needsConfirmation,
		"warnings":           list["warnings"],
	}
	if len(context) > 0 {
		payload["task_context"] = context
	}
	return sanitizeLearningProjection(payload), nil
}

func (service learningService) list(request learningListRequest) (map[string]any, error) {
	policy, policyWarnings, _ := service.loadLearningPolicy(false)
	request.context = sanitizeLearningContextsWithPolicy(request.context, policy)
	normalizedCommand := ""
	var err error
	if strings.TrimSpace(request.commandName) != "" {
		normalizedCommand, err = normalizeLearningCommand(request.commandName)
		if err != nil {
			return nil, err
		}
		normalizedCommand = safeLearningCommandProjection(normalizedCommand, policy)
	}
	normalizedType := ""
	if strings.TrimSpace(request.learningType) != "" {
		normalizedType, err = normalizeLearningType(request.learningType)
		if err != nil {
			return nil, err
		}
	}
	normalizedStatus := strings.ToLower(strings.TrimSpace(request.status))
	if normalizedStatus != "" && !learningStatuses[normalizedStatus] && normalizedStatus != "indexed" {
		return nil, fmt.Errorf("unsupported learning status %q", request.status)
	}
	if request.cursor < 0 {
		request.cursor = 0
	}
	if request.includeAll {
		request.limit = 0
	} else if request.limit < 1 {
		return nil, fmt.Errorf("limit must be at least 1 unless --all is used")
	} else if request.limit > 200 {
		request.limit = 200
	}
	catalog, warnings, err := service.catalogWithPolicy(policy)
	if err != nil {
		return nil, err
	}
	warnings = append(policyWarnings, warnings...)
	safeQuery := redactLearningTextWithPolicy(request.query, policy).text
	query := strings.ToLower(strings.TrimSpace(safeQuery))
	cards := []map[string]any{}
	for _, item := range catalog {
		indexEntry := item.indexEntry
		entry := item.entry
		commandMatch := normalizedCommand != "" && learningContainsString(anyStringSlice(indexEntry["applies_to"]), normalizedCommand)
		contextMatch := learningContextMatch(indexEntry, request.context)
		crossCommand := false
		if normalizedCommand != "" && !commandMatch {
			if len(request.context) == 0 || !learningContextAllowsCrossCommand(contextMatch) {
				continue
			}
			crossCommand = true
		} else if normalizedCommand == "" && len(request.context) > 0 && intFromAny(contextMatch["matched_dimensions"]) == 0 {
			continue
		}
		if normalizedType != "" && indexEntry["learning_type"] != normalizedType {
			continue
		}
		status := "indexed"
		if entry != nil {
			status = stringFromAny(entry["status"])
		}
		if normalizedStatus != "" && status != normalizedStatus {
			continue
		}
		if query != "" && !strings.Contains(strings.ToLower(learningSearchText(indexEntry)), query) {
			continue
		}
		cards = append(cards, learningSummaryCard(indexEntry, entry, item.sourceLayer, normalizedCommand, contextMatch, crossCommand, len(request.context) > 0))
	}
	sortLearningCards(cards)
	total := len(cards)
	if request.startMode && !request.includeAll && request.limit == 20 && request.cursor == 0 {
		cards = learningStartQuotaCards(cards, 15, 5)
	}
	end := total
	if !request.includeAll {
		end = request.cursor + request.limit
		if end > total {
			end = total
		}
		if end > len(cards) {
			end = len(cards)
		}
	}
	page := []map[string]any{}
	if request.cursor < len(cards) {
		page = cards[request.cursor:end]
	}
	for _, card := range page {
		delete(card, "_source_command")
		delete(card, "_recurrence_family")
		delete(card, "_learning_value_tier")
	}
	var nextCursor any
	var nextArgv any
	if !request.includeAll && end < total {
		nextCursor = float64(end)
		next := []any{"specify-runtime", "learning", "list"}
		if normalizedCommand != "" {
			next = append(next, "--command", safeLearningCommandProjection(normalizedCommand, policy))
		}
		if normalizedType != "" {
			next = append(next, "--type", normalizedType)
		}
		if normalizedStatus != "" {
			next = append(next, "--status", normalizedStatus)
		}
		if safeQuery != "" {
			next = append(next, "--query", safeQuery)
		}
		next = append(next, learningContextArgv(request.context)...)
		cursorArg := end
		if request.startMode {
			cursorArg = 0
			nextCursor = float64(0)
		}
		next = append(next, "--cursor", strconv.Itoa(cursorArg), "--limit", strconv.Itoa(request.limit), "--format", "json")
		nextArgv = next
	}
	payload := map[string]any{
		"schema_version": float64(1),
		"record_schema":  ".specify/templates/project-learning-record-schema.json#/$defs/summaryList",
		"command":        nil,
		"policy":         nil,
		"filters":        map[string]any{"type": nil, "status": nil, "query": nil},
		"pagination":     map[string]any{"cursor": float64(request.cursor), "limit": float64(request.limit), "returned": float64(len(page)), "total": float64(total), "next_cursor": nextCursor, "next_argv": nextArgv},
		"items":          mapsToAnyLearning(page),
		"warnings":       stringsToAny(warnings),
	}
	if normalizedCommand != "" {
		payload["command"] = safeLearningCommandProjection(normalizedCommand, policy)
		payload["policy"] = learningWorkflowPolicy(normalizedCommand)
	}
	if normalizedType != "" {
		payload["filters"].(map[string]any)["type"] = normalizedType
	}
	if normalizedStatus != "" {
		payload["filters"].(map[string]any)["status"] = normalizedStatus
	}
	if safeQuery != "" {
		payload["filters"].(map[string]any)["query"] = safeQuery
	}
	if len(request.context) > 0 {
		payload["task_context"] = request.context
	}
	return sanitizeLearningProjection(payload), nil
}

func (service learningService) show(ref string) (map[string]any, error) {
	requested := strings.TrimSpace(ref)
	if requested == "" {
		return nil, fmt.Errorf("learning ref is required")
	}
	paths, err := service.paths()
	if err != nil {
		return nil, err
	}
	policy, policyWarnings, _ := service.loadLearningPolicy(false)
	requestedSafe := sanitizeLearningRecurrenceKeyWithPolicy(requested, policy).text
	catalog, warnings, err := service.catalogWithPolicy(policy)
	if err != nil {
		return nil, err
	}
	warnings = append(policyWarnings, warnings...)
	for _, item := range catalog {
		indexEntry := item.indexEntry
		if requested != stringFromAny(indexEntry["id"]) && requested != stringFromAny(indexEntry["recurrence_key"]) && requestedSafe != stringFromAny(indexEntry["recurrence_key"]) {
			continue
		}
		entry := item.entry
		detailPath := any(nil)
		if validLearningDetailRef(stringFromAny(indexEntry["detail"])) {
			candidate := filepath.Join(filepath.Dir(paths.learningIndex), strings.TrimPrefix(stringFromAny(indexEntry["detail"]), "./"))
			if insideDir(filepath.Dir(paths.learningIndex), candidate) {
				if info, err := os.Stat(candidate); err == nil && !info.IsDir() {
					detailPath = redactLearningTextWithPolicy(service.learningSourceRef(candidate), policy).text
					if detailEntries := readLearningEntriesIfPresent(candidate); len(detailEntries) > 0 {
						for _, detailEntry := range detailEntries {
							if detailEntry["recurrence_key"] == indexEntry["recurrence_key"] {
								entry = applyLearningAssessment(sanitizeLearningEntryWithPolicy(detailEntry, policy), "")
							}
						}
					}
				}
			}
		}
		problem := stringFromAny(indexEntry["problem"])
		action := stringFromAny(indexEntry["lesson"])
		if entry != nil {
			if value := stringFromAny(entry["problem"]); value != "" {
				problem = value
			}
			if value := stringFromAny(entry["recommended_action"]); value != "" {
				action = value
			}
		}
		applicability := map[string]any{"commands": indexEntry["applies_to"], "trigger_signals": indexEntry["trigger_signals"], "scope": ""}
		if entry != nil {
			applicability["scope"] = entry["default_scope"]
			if facets := mapStringAny(entry["facets"]); len(facets) > 0 {
				applicability["facets"] = facets
			}
		} else if facets := mapStringAny(indexEntry["facets"]); len(facets) > 0 {
			applicability["facets"] = facets
		}
		status := "indexed"
		summary := stringFromAny(indexEntry["problem"])
		if entry != nil {
			status = stringFromAny(entry["status"])
			summary = stringFromAny(entry["summary"])
		}
		contentSafetyLabels := map[string]bool{}
		for _, label := range anyStringSlice(indexEntry["redaction_labels"]) {
			if validLearningRedactionLabel(label) {
				contentSafetyLabels[label] = true
			}
		}
		contentSafetySensitivity := stringFromAny(indexEntry["sensitivity"])
		if entry != nil {
			for _, label := range anyStringSlice(entry["redaction_labels"]) {
				if validLearningRedactionLabel(label) {
					contentSafetyLabels[label] = true
				}
			}
			contentSafetySensitivity = firstString(stringFromAny(entry["sensitivity"]), contentSafetySensitivity)
		}
		payload := map[string]any{
			"schema_version": float64(1), "record_schema": ".specify/templates/project-learning-record-schema.json#/$defs/detailRecord",
			"ref": indexEntry["recurrence_key"], "id": indexEntry["id"], "summary": summary, "type": indexEntry["learning_type"], "status": status,
			"guidance":      map[string]any{"problem": problem, "action": action, "avoid": entryFieldList(entry, "avoid"), "success_criteria": entryFieldList(entry, "success_criteria"), "exceptions": entryFieldList(entry, "exceptions")},
			"applicability": applicability,
			"evidence":      map[string]any{"observation": firstString(entryString(entry, "evidence"), stringFromAny(indexEntry["lesson"])), "decisive_signal": entryString(entry, "decisive_signal"), "false_starts": entryFieldList(entry, "false_starts"), "rejected_paths": entryFieldList(entry, "rejected_paths"), "root_cause_family": entryString(entry, "root_cause_family")},
			"provenance":    map[string]any{"source_command": indexEntry["source_command"], "first_seen": indexEntry["first_seen"], "last_seen": indexEntry["last_seen"], "occurrences": indexEntry["occurrence_count"], "source_layer": item.sourceLayer},
			"lifecycle":     map[string]any{"signal": indexEntry["signal_strength"], "pain_score": entryNumber(entry, "pain_score"), "injection_targets": entryFieldList(entry, "injection_targets"), "promotion_hint": entryString(entry, "promotion_hint")},
			"detail_path":   detailPath, "warnings": stringsToAny(warnings),
		}
		if assessment := learningAssessmentProjection(firstNonNilLearningEntry(entry, indexEntry)); assessment != nil {
			payload["assessment"] = assessment
		}
		payload = sanitizeLearningPayload(payload)
		for _, label := range anyStringSlice(payload["redaction_labels"]) {
			if validLearningRedactionLabel(label) {
				contentSafetyLabels[label] = true
			}
		}
		labels := sortedLearningLabels(contentSafetyLabels)
		if len(labels) > 0 {
			contentSafetySensitivity = "sanitized"
		}
		payload["content_safety"] = map[string]any{
			"sensitivity":      firstString(contentSafetySensitivity, "safe"),
			"risk_tier":        learningRiskTier(labels),
			"redaction_labels": stringsToAny(labels),
		}
		delete(payload, "sensitivity")
		delete(payload, "redaction_labels")
		return payload, nil
	}
	return nil, fmt.Errorf("learning %q not found", requestedSafe)
}

func (service learningService) capture(request learningCaptureRequest) (map[string]any, error) {
	policy, _, err := service.loadLearningPolicy(true)
	if err != nil {
		return nil, err
	}
	entry, err := buildLearningEntry(request, policy)
	if err != nil {
		return nil, err
	}
	return service.withLock(func(paths learningPaths) (map[string]any, error) {
		decision := stringFromAny(entry["assessment_decision"])
		if decision == "ignore" {
			if err := service.recordLearningAssessment(paths, entry, false, false); err != nil {
				return nil, err
			}
			return map[string]any{"status": "ignored", "assessment": learningAssessmentProjection(entry)}, nil
		}
		if decision == "defer" {
			if err := service.upsertDeferredLearningReview(paths, entry, "deferred", stringFromAny(entry["assessment_reason"]), policy); err != nil {
				return nil, err
			}
			if err := service.recordLearningAssessment(paths, entry, false, false); err != nil {
				return nil, err
			}
			return map[string]any{"status": "deferred", "assessment": learningAssessmentProjection(entry)}, nil
		}
		stored, err := service.storeLearningEntry(paths, entry, request.confirm, policy)
		if err != nil {
			return nil, err
		}
		storedEntry := mapStringAny(stored["entry"])
		if err := service.recordLearningAssessment(paths, storedEntry, true, request.confirm); err != nil {
			return nil, err
		}
		if err := service.clearMatchingLearningReviews(paths, stringFromAny(storedEntry["source_command"]), stringFromAny(storedEntry["recurrence_key"]), policy); err != nil {
			return nil, err
		}
		stored["assessment"] = learningAssessmentProjection(storedEntry)
		return stored, nil
	})
}

func (service learningService) captureAuto(commandName, featureDir, workspace, sessionFile string, dryRun bool) (map[string]any, error) {
	policy, _, err := service.loadLearningPolicy(true)
	if err != nil {
		return nil, err
	}
	normalized, err := normalizeLearningCommand(commandName)
	if err != nil {
		return nil, err
	}
	var sourcePath string
	var suggestions []learningSuggestion
	switch {
	case normalized == "sp-implement":
		if strings.TrimSpace(featureDir) == "" {
			return nil, fmt.Errorf("feature_dir is required for implement auto-capture")
		}
		sourcePath, suggestions, err = service.suggestImplementAutoCapture(featureDir)
	case normalized == "sp-quick":
		if strings.TrimSpace(workspace) == "" {
			return nil, fmt.Errorf("workspace is required for quick auto-capture")
		}
		sourcePath, suggestions, err = service.suggestQuickAutoCapture(workspace)
	case workflowStateAutoCaptureCommands[normalized]:
		if strings.TrimSpace(featureDir) == "" {
			return nil, fmt.Errorf("feature_dir is required for workflow-state auto-capture")
		}
		sourcePath, suggestions, err = service.suggestWorkflowStateAutoCapture(featureDir, normalized)
	case normalized == "sp-debug":
		if strings.TrimSpace(sessionFile) == "" {
			return nil, fmt.Errorf("session_file is required for debug auto-capture")
		}
		sourcePath, suggestions, err = service.suggestDebugAutoCapture(sessionFile)
	default:
		err = fmt.Errorf("auto-capture is unsupported for %q", commandName)
	}
	if err != nil {
		return nil, err
	}
	sourceRef := redactLearningReferenceTextWithPolicy(service.learningSourceRef(sourcePath), policy).text
	if len(suggestions) == 0 {
		if dryRun {
			return map[string]any{"status": "dry-run", "dry_run": true, "command": normalized, "source_path": sourceRef, "assessed": []any{}, "captured": []any{}}, nil
		}
		return map[string]any{"status": "no-op", "command": normalized, "source_path": sourceRef, "captured": []any{}, "reason": "no high-signal auto-capture patterns matched the current state"}, nil
	}
	fingerprint, err := learningSnapshotFingerprint(normalized, sourceRef, suggestions, policy)
	if err != nil {
		return nil, err
	}
	buildAssessedEntries := func() ([]map[string]any, error) {
		existingOccurrences, countErr := service.existingLearningOccurrenceCounts(policy)
		if countErr != nil {
			return nil, countErr
		}
		assessedEntries := []map[string]any{}
		for _, suggestion := range suggestions {
			entry, buildErr := buildLearningEntry(learningCaptureRequest{
				source: "auto", commandName: normalized, learningType: suggestion.learningType, summary: suggestion.summary, evidence: suggestion.evidence,
				recurrenceKey: suggestion.recurrenceKey, signalStrength: firstString(suggestion.signalStrength, "medium"),
				appliesTo: suggestion.appliesTo, problem: suggestion.problem, recommendedAction: suggestion.recommendedAction,
				triggerSignals: suggestion.triggerSignals, successCriteria: suggestion.successCriteria, avoid: suggestion.avoid, exceptions: suggestion.exceptions,
			}, policy)
			if buildErr != nil {
				return nil, buildErr
			}
			key := stringFromAny(entry["recurrence_key"])
			if existingOccurrences[key] > 0 {
				entry["occurrence_count"] = float64(existingOccurrences[key] + 1)
				entry = applyLearningAssessment(entry, "auto")
			}
			assessedEntries = append(assessedEntries, entry)
		}
		return assessedEntries, nil
	}
	if dryRun {
		assessedEntries, buildErr := buildAssessedEntries()
		if buildErr != nil {
			return nil, buildErr
		}
		assessed := []any{}
		for _, entry := range assessedEntries {
			assessed = append(assessed, learningAssessedCard(entry))
		}
		return sanitizeLearningProjection(map[string]any{"status": "dry-run", "dry_run": true, "command": normalized, "source_path": sourceRef, "assessed": assessed, "captured": []any{}}), nil
	}
	return service.withLock(func(paths learningPaths) (map[string]any, error) {
		registry, err := service.loadAutoCaptureRegistry(paths)
		if err != nil {
			return nil, err
		}
		normalizedRegistry, registryChanged := service.normalizeAutoCaptureRegistry(registry)
		registry = normalizedRegistry
		if registryChanged {
			if err := service.writeAutoCaptureRegistry(paths, registry); err != nil {
				return nil, err
			}
		}
		if _, exists := registry[fingerprint]; exists {
			return map[string]any{"status": "duplicate-snapshot", "command": normalized, "source_path": sourceRef, "captured": []any{}, "reason": "this workflow state snapshot was already auto-captured", "fingerprint": fingerprint}, nil
		}
		// Occurrence counts and the resulting value assessment are state-derived.
		// Recompute them only after the duplicate check and while holding the same
		// lock used for persistence so concurrent captures cannot undercount.
		assessedEntries, buildErr := buildAssessedEntries()
		if buildErr != nil {
			return nil, buildErr
		}
		captured := []any{}
		assessed := []any{}
		keys := []any{}
		hadDeferred := false
		for _, entry := range assessedEntries {
			assessed = append(assessed, learningAssessedCard(entry))
			decision := stringFromAny(entry["assessment_decision"])
			if decision == "ignore" {
				if err := service.recordLearningAssessment(paths, entry, false, false); err != nil {
					return nil, err
				}
				continue
			}
			if decision == "defer" {
				hadDeferred = true
				if err := service.upsertDeferredLearningReview(paths, entry, "deferred", stringFromAny(entry["assessment_reason"]), policy); err != nil {
					return nil, err
				}
				if err := service.recordLearningAssessment(paths, entry, false, false); err != nil {
					return nil, err
				}
				continue
			}
			stored, err := service.storeLearningEntry(paths, entry, false, policy)
			if err != nil {
				return nil, err
			}
			storedEntry := mapStringAny(stored["entry"])
			if err := service.recordLearningAssessment(paths, storedEntry, true, false); err != nil {
				return nil, err
			}
			if err := service.clearMatchingLearningReviews(paths, normalized, stringFromAny(storedEntry["recurrence_key"]), policy); err != nil {
				return nil, err
			}
			captured = append(captured, sanitizeLearningPayload(stored))
			keys = append(keys, storedEntry["recurrence_key"])
		}
		registry[fingerprint] = map[string]any{"command": normalized, "source_ref": sourceRef, "recurrence_keys": keys, "captured_at": learningNow()}
		if err := service.writeAutoCaptureRegistry(paths, registry); err != nil {
			return nil, err
		}
		if err := appendLearningReview(paths.review, redactLearningFormat("auto-captured %d learning candidate(s) from `%s` using `%s`", len(captured), normalized, sourceRef), policy); err != nil {
			return nil, err
		}
		status := "captured"
		if len(captured) == 0 {
			status = "no-op"
			if hadDeferred {
				status = "deferred"
			}
		}
		return map[string]any{"status": status, "command": normalized, "source_path": sourceRef, "assessed": assessed, "captured": captured, "fingerprint": fingerprint}, nil
	})
}

func (service learningService) promote(recurrenceKey, target string) (map[string]any, error) {
	policy, _, err := service.loadLearningPolicy(true)
	if err != nil {
		return nil, err
	}
	normalizedTarget := strings.ToLower(strings.TrimSpace(target))
	if normalizedTarget != "learning" && normalizedTarget != "rule" {
		return nil, fmt.Errorf("unsupported promotion target %q", target)
	}
	rawKey := strings.ToLower(strings.TrimSpace(recurrenceKey))
	if rawKey == "" {
		return nil, fmt.Errorf("learning recurrence_key is required")
	}
	key := sanitizeLearningRecurrenceKeyWithPolicy(rawKey, policy).text
	return service.withLock(func(paths learningPaths) (map[string]any, error) {
		candidatePreamble, candidateEntries, err := readLearningEntries(paths.candidates)
		if err != nil {
			return nil, err
		}
		learningPreamble, learningEntries, err := readLearningEntries(paths.confirmedLearnings)
		if err != nil {
			return nil, err
		}
		rulePreamble, ruleEntries, err := readLearningEntries(paths.projectRules)
		if err != nil {
			return nil, err
		}
		candidateEntries = sanitizeLearningEntriesWithPolicy(candidateEntries, policy)
		learningEntries = sanitizeLearningEntriesWithPolicy(learningEntries, policy)
		ruleEntries = sanitizeLearningEntriesWithPolicy(ruleEntries, policy)
		key = sanitizeLearningRecurrenceKeyWithPolicy(key, policy).text
		source, layer := findLearningEntry(candidateEntries, key), "candidates"
		if source == nil {
			source, layer = findLearningEntry(learningEntries, key), "confirmed_learnings"
		}
		if source == nil {
			source, layer = findLearningEntry(ruleEntries, key), "project_rules"
		}
		if source == nil {
			return nil, fmt.Errorf("learning %q not found", key)
		}
		if normalizedTarget == "rule" && layer == "candidates" {
			return nil, fmt.Errorf("candidate learning %q must be promoted to learning before rule", key)
		}
		if normalizedTarget == "learning" {
			source["status"] = "confirmed"
			source["last_seen"] = learningNow()
			learningEntries, source = upsertLearningEntry(learningEntries, source, "confirmed")
			candidateEntries = removeLearningByRecurrence(candidateEntries, key)
			if err := writeLearningEntries(paths.confirmedLearnings, firstString(learningPreamble, strings.TrimSpace(learningConfirmedTemplateText())), learningEntries); err != nil {
				return nil, err
			}
			if err := writeLearningEntries(paths.candidates, firstString(candidatePreamble, strings.TrimSpace(learningCandidatesTemplateText())), candidateEntries); err != nil {
				return nil, err
			}
			if err := appendLearningReview(paths.review, fmt.Sprintf("promoted `%s` to project learnings from `%s`", key, layer), policy); err != nil {
				return nil, err
			}
			index, detail, err := service.syncLearningIndexDetail(paths, source, policy)
			if err != nil {
				return nil, err
			}
			if err := service.recordLearningPromotion(paths, source, "confirmed"); err != nil {
				return nil, err
			}
			if err := service.clearMatchingLearningReviews(paths, stringFromAny(source["source_command"]), key, policy); err != nil {
				return nil, err
			}
			return sanitizeLearningPayload(map[string]any{"status": "confirmed", "entry": source, "index_entry": index, "detail_path": service.learningSourceRef(detail), "assessment": learningAssessmentProjection(source)}), nil
		}
		source["status"] = "promoted-rule"
		source["last_seen"] = learningNow()
		ruleEntries, source = upsertLearningEntry(ruleEntries, source, "promoted-rule")
		candidateEntries = removeLearningByRecurrence(candidateEntries, key)
		learningEntries = removeLearningByRecurrence(learningEntries, key)
		if err := writeLearningEntries(paths.projectRules, firstString(rulePreamble, strings.TrimSpace(learningRulesTemplateText())), ruleEntries); err != nil {
			return nil, err
		}
		if err := writeLearningEntries(paths.confirmedLearnings, firstString(learningPreamble, strings.TrimSpace(learningConfirmedTemplateText())), learningEntries); err != nil {
			return nil, err
		}
		if err := writeLearningEntries(paths.candidates, firstString(candidatePreamble, strings.TrimSpace(learningCandidatesTemplateText())), candidateEntries); err != nil {
			return nil, err
		}
		if err := appendLearningReview(paths.review, fmt.Sprintf("promoted `%s` to project rules from `%s`", key, layer), policy); err != nil {
			return nil, err
		}
		index, detail, err := service.syncLearningIndexDetail(paths, source, policy)
		if err != nil {
			return nil, err
		}
		if err := service.recordLearningPromotion(paths, source, "promoted"); err != nil {
			return nil, err
		}
		if err := service.clearMatchingLearningReviews(paths, stringFromAny(source["source_command"]), key, policy); err != nil {
			return nil, err
		}
		return sanitizeLearningPayload(map[string]any{"status": "promoted-rule", "entry": source, "index_entry": index, "detail_path": service.learningSourceRef(detail), "assessment": learningAssessmentProjection(source)}), nil
	})
}

func (service learningService) storeLearningEntry(paths learningPaths, entry map[string]any, confirm bool, policy learningPolicy) (map[string]any, error) {
	entry = applyLearningAssessment(sanitizeLearningEntryWithPolicy(entry, policy), "")
	if confirm {
		preamble, entries, err := readLearningEntries(paths.confirmedLearnings)
		if err != nil {
			return nil, err
		}
		entries = sanitizeLearningEntriesWithPolicy(entries, policy)
		entries, stored := upsertLearningEntry(entries, entry, "confirmed")
		if err := writeLearningEntries(paths.confirmedLearnings, firstString(preamble, strings.TrimSpace(learningConfirmedTemplateText())), entries); err != nil {
			return nil, err
		}
		candidatePreamble, candidates, err := readLearningEntries(paths.candidates)
		if err != nil {
			return nil, err
		}
		candidates = sanitizeLearningEntriesWithPolicy(candidates, policy)
		candidates = removeLearningByRecurrence(candidates, stringFromAny(stored["recurrence_key"]))
		if err := writeLearningEntries(paths.candidates, firstString(candidatePreamble, strings.TrimSpace(learningCandidatesTemplateText())), candidates); err != nil {
			return nil, err
		}
		if err := appendLearningReview(paths.review, fmt.Sprintf("confirmed `%s` from `%s`", stored["recurrence_key"], stored["source_command"]), policy); err != nil {
			return nil, err
		}
		index, detail, err := service.syncLearningIndexDetail(paths, stored, policy)
		if err != nil {
			return nil, err
		}
		return sanitizeLearningPayload(map[string]any{"status": "confirmed", "entry": stored, "index_entry": index, "detail_path": service.learningSourceRef(detail), "needs_confirmation": false}), nil
	}
	preamble, entries, err := readLearningEntries(paths.candidates)
	if err != nil {
		return nil, err
	}
	entries = sanitizeLearningEntriesWithPolicy(entries, policy)
	entries, stored := upsertLearningEntry(entries, entry, "candidate")
	if err := writeLearningEntries(paths.candidates, firstString(preamble, strings.TrimSpace(learningCandidatesTemplateText())), entries); err != nil {
		return nil, err
	}
	if err := appendLearningReview(paths.review, fmt.Sprintf("captured candidate `%s` from `%s`", stored["recurrence_key"], stored["source_command"]), policy); err != nil {
		return nil, err
	}
	index, detail, err := service.syncLearningIndexDetail(paths, stored, policy)
	if err != nil {
		return nil, err
	}
	return sanitizeLearningPayload(map[string]any{"status": "candidate", "entry": stored, "index_entry": index, "detail_path": service.learningSourceRef(detail), "needs_confirmation": learningHighestSignal(stored)}), nil
}

type learningCatalogItem struct {
	indexEntry  map[string]any
	entry       map[string]any
	sourceLayer string
}

func (service learningService) catalog() ([]learningCatalogItem, []string, error) {
	policy, policyWarnings, _ := service.loadLearningPolicy(false)
	catalog, warnings, err := service.catalogWithPolicy(policy)
	return catalog, append(policyWarnings, warnings...), err
}

func (service learningService) catalogWithPolicy(policy learningPolicy) ([]learningCatalogItem, []string, error) {
	paths, err := service.paths()
	if err != nil {
		return nil, nil, err
	}
	sourceByKey := map[string]learningCatalogItem{}
	for _, source := range []struct {
		layer string
		path  string
	}{{"candidate", paths.candidates}, {"confirmed-learning", paths.confirmedLearnings}, {"project-rule", paths.projectRules}} {
		for _, entry := range readLearningEntriesIfPresent(source.path) {
			entry = applyLearningAssessment(sanitizeLearningEntryWithPolicy(entry, policy), "")
			sourceByKey[stringFromAny(entry["recurrence_key"])] = learningCatalogItem{entry: entry, sourceLayer: source.layer}
		}
	}
	indexEntries, warnings := readLearningIndexEntriesWithDiagnostics(paths.learningIndex)
	catalog := []learningCatalogItem{}
	seen := map[string]bool{}
	for _, indexEntry := range indexEntries {
		indexEntry = applyLearningAssessment(sanitizeLearningEntryWithPolicy(indexEntry, policy), "")
		key := stringFromAny(indexEntry["recurrence_key"])
		item := sourceByKey[key]
		item.indexEntry = indexEntry
		if item.sourceLayer == "" {
			item.sourceLayer = "index-only"
		}
		catalog = append(catalog, item)
		seen[key] = true
	}
	for key, item := range sourceByKey {
		if seen[key] {
			continue
		}
		item.indexEntry = indexEntryFromLearning(item.entry)
		catalog = append(catalog, item)
	}
	sort.Slice(catalog, func(i, j int) bool {
		left, right := catalog[i].indexEntry, catalog[j].indexEntry
		if intFromAny(left["occurrence_count"]) != intFromAny(right["occurrence_count"]) {
			return intFromAny(left["occurrence_count"]) > intFromAny(right["occurrence_count"])
		}
		if signalRank(stringFromAny(left["signal_strength"])) != signalRank(stringFromAny(right["signal_strength"])) {
			return signalRank(stringFromAny(left["signal_strength"])) < signalRank(stringFromAny(right["signal_strength"]))
		}
		return stringFromAny(left["recurrence_key"]) < stringFromAny(right["recurrence_key"])
	})
	return catalog, warnings, nil
}

func (service learningService) existingLearningOccurrenceCounts(policy learningPolicy) (map[string]int, error) {
	paths, err := service.paths()
	if err != nil {
		return nil, err
	}
	counts := map[string]int{}
	for _, path := range []string{paths.candidates, paths.confirmedLearnings, paths.projectRules, paths.learningIndex} {
		for _, entry := range readLearningEntriesIfPresent(path) {
			entry = sanitizeLearningEntryWithPolicy(entry, policy)
			key := stringFromAny(entry["recurrence_key"])
			if count := intFromAny(entry["occurrence_count"]); key != "" && count > counts[key] {
				counts[key] = count
			}
		}
	}
	return counts, nil
}

func buildLearningEntry(request learningCaptureRequest, policy learningPolicy) (map[string]any, error) {
	summary := strings.TrimSpace(request.summary)
	evidence := strings.TrimSpace(request.evidence)
	if summary == "" {
		return nil, fmt.Errorf("learning summary is required")
	}
	if evidence == "" {
		return nil, fmt.Errorf("learning evidence is required")
	}
	command, err := normalizeLearningCommand(request.commandName)
	if err != nil {
		return nil, err
	}
	learningType, err := normalizeLearningType(request.learningType)
	if err != nil {
		return nil, err
	}
	signal := strings.ToLower(strings.TrimSpace(firstString(request.signalStrength, "medium")))
	if !learningSignals[signal] {
		return nil, fmt.Errorf("unsupported signal strength %q", request.signalStrength)
	}
	applies := normalizeLearningCommands(request.appliesTo)
	if len(applies) == 0 {
		applies = defaultAppliesToForLearningType(learningType, command)
	}
	applies = uniqueSortedTrimmed(append(applies, command))
	key := strings.ToLower(strings.TrimSpace(request.recurrenceKey))
	if key == "" {
		key = learningType + "." + slugifyLearning(summary)
	}
	painScore, _ := strconv.Atoi(strings.TrimSpace(request.painScore))
	if painScore < 0 {
		painScore = 0
	}
	now := learningNow()
	entry := sanitizeLearningEntryWithPolicy(map[string]any{
		"id": buildLearningID(), "summary": summary, "learning_type": learningType, "source_command": command, "evidence": evidence,
		"recurrence_key": key, "default_scope": strings.ToLower(strings.TrimSpace(firstString(request.defaultScope, defaultScopeForLearningType(learningType)))),
		"applies_to": stringsToAny(applies), "signal_strength": signal, "status": "candidate", "first_seen": now, "last_seen": now,
		"occurrence_count": float64(1), "pain_score": float64(painScore), "false_starts": stringsToAny(uniqueSortedTrimmed(request.falseStarts)),
		"rejected_paths": stringsToAny(uniqueSortedTrimmed(request.rejectedPaths)), "decisive_signal": strings.TrimSpace(request.decisiveSignal),
		"root_cause_family": strings.TrimSpace(request.rootCauseFamily), "injection_targets": stringsToAny(uniqueSortedTrimmed(request.injectionTargets)),
		"promotion_hint": strings.TrimSpace(request.promotionHint), "problem": strings.TrimSpace(firstString(request.problem, summary)),
		"recommended_action": strings.TrimSpace(firstString(request.recommendedAction, summary)), "avoid": stringsToAny(uniqueSortedTrimmed(request.avoid)),
		"trigger_signals": stringsToAny(uniqueSortedTrimmed(request.triggerSignals)), "success_criteria": stringsToAny(uniqueSortedTrimmed(request.successCriteria)),
		"exceptions": stringsToAny(uniqueSortedTrimmed(request.exceptions)), "facets": facetsToAny(normalizeLearningFacets(request.facets)),
	}, policy)
	return applyLearningAssessment(entry, firstString(request.source, "manual")), nil
}

func upsertLearningEntry(entries []map[string]any, entry map[string]any, status string) ([]map[string]any, map[string]any) {
	key := stringFromAny(entry["recurrence_key"])
	for index, existing := range entries {
		if existing["recurrence_key"] != key {
			continue
		}
		merged := mergeLearningEntry(existing, entry, status)
		entries[index] = merged
		return entries, merged
	}
	stored := cloneLearningMap(entry)
	if status != "" {
		stored["status"] = status
	}
	return append(entries, stored), stored
}

func mergeLearningEntry(existing, incoming map[string]any, status string) map[string]any {
	merged := cloneLearningMap(existing)
	for _, key := range []string{"summary", "source_command", "evidence", "default_scope", "decisive_signal", "root_cause_family", "promotion_hint", "problem", "recommended_action"} {
		if value := stringFromAny(incoming[key]); value != "" {
			merged[key] = value
		}
	}
	if status != "" {
		merged["status"] = status
	}
	merged["last_seen"] = incoming["last_seen"]
	merged["occurrence_count"] = float64(intFromAny(existing["occurrence_count"]) + 1)
	merged["pain_score"] = float64(maxInt(intFromAny(existing["pain_score"]), intFromAny(incoming["pain_score"])))
	merged["signal_strength"] = strongestLearningSignal(stringFromAny(existing["signal_strength"]), stringFromAny(incoming["signal_strength"]))
	for _, key := range []string{"applies_to", "false_starts", "rejected_paths", "injection_targets", "avoid", "trigger_signals", "success_criteria", "exceptions"} {
		merged[key] = stringsToAny(uniqueSortedTrimmed(append(anyStringSlice(existing[key]), anyStringSlice(incoming[key])...)))
	}
	merged["facets"] = facetsToAny(mergeLearningFacets(anyFacets(existing["facets"]), anyFacets(incoming["facets"])))
	sensitivity, labels := mergeLearningContentSafety(existing, incoming, merged)
	merged["sensitivity"] = sensitivity
	merged["redaction_labels"] = stringsToAny(labels)
	return applyLearningAssessment(merged, "")
}

func sanitizeLearningEntriesWithPolicy(entries []map[string]any, policy learningPolicy) []map[string]any {
	result := make([]map[string]any, 0, len(entries))
	for _, entry := range entries {
		result = append(result, applyLearningAssessment(sanitizeLearningEntryWithPolicy(entry, policy), ""))
	}
	return result
}

func (service learningService) syncLearningIndexDetail(paths learningPaths, entry map[string]any, policy learningPolicy) (map[string]any, string, error) {
	preamble, indexEntries, err := readLearningIndexEntries(paths.learningIndex)
	if err != nil {
		return nil, "", err
	}
	cleanIndexEntries := make([]map[string]any, 0, len(indexEntries))
	for _, indexEntry := range indexEntries {
		cleanIndexEntries, _ = upsertLearningIndexEntry(cleanIndexEntries, sanitizeLearningEntryWithPolicy(indexEntry, policy))
	}
	indexEntries, storedIndex := upsertLearningIndexEntry(cleanIndexEntries, indexEntryFromLearning(entry))
	learningDir := filepath.Dir(paths.learningIndex)
	oldDetail := stringFromAny(storedIndex["detail"])
	policySensitiveDetail := redactLearningReferenceTextWithPolicy(oldDetail, policy).text != oldDetail
	if !validLearningDetailRef(oldDetail) || policySensitiveDetail || usedDetailByOther(indexEntries, oldDetail, stringFromAny(storedIndex["recurrence_key"])) {
		id, detail := unusedLearningDetailRef(indexEntries, stringFromAny(storedIndex["recurrence_key"]), stringFromAny(storedIndex["first_seen"]))
		storedIndex["id"], storedIndex["detail"] = id, detail
	}
	if !validLearningDetailRef(stringFromAny(storedIndex["detail"])) {
		return nil, "", fmt.Errorf("learning detail path escapes learning memory directory")
	}
	detailPath := filepath.Join(learningDir, strings.TrimPrefix(stringFromAny(storedIndex["detail"]), "./"))
	if !insideDir(learningDir, detailPath) {
		return nil, "", fmt.Errorf("learning detail path escapes learning memory directory")
	}
	if err := writeLearningDetail(detailPath, entry, storedIndex); err != nil {
		return nil, "", err
	}
	if err := writeLearningIndexEntries(paths.learningIndex, firstString(preamble, strings.TrimSpace(learningIndexTemplateText())), indexEntries); err != nil {
		return nil, "", err
	}
	if oldDetail != "" && oldDetail != stringFromAny(storedIndex["detail"]) && validLearningDetailRef(oldDetail) && !usedDetailByOther(indexEntries, oldDetail, stringFromAny(storedIndex["recurrence_key"])) {
		oldDetailPath := filepath.Join(learningDir, strings.TrimPrefix(oldDetail, "./"))
		if insideDir(learningDir, oldDetailPath) {
			if err := os.Remove(oldDetailPath); err != nil && !os.IsNotExist(err) {
				return nil, "", err
			}
		}
	}
	return storedIndex, detailPath, nil
}

func upsertLearningIndexEntry(entries []map[string]any, entry map[string]any) ([]map[string]any, map[string]any) {
	key := stringFromAny(entry["recurrence_key"])
	for index, existing := range entries {
		if existing["recurrence_key"] != key {
			continue
		}
		merged := cloneLearningMap(existing)
		for _, field := range []string{"problem", "lesson", "source_command", "last_seen", "occurrence_count", "learning_value_tier", "sensitivity_risk_tier", "assessment_decision", "assessment_reason"} {
			if value := entry[field]; value != nil && stringFromAny(value) != "" {
				merged[field] = value
			}
		}
		for _, field := range []string{"applies_to", "trigger_signals"} {
			merged[field] = stringsToAny(uniqueSortedTrimmed(append(anyStringSlice(existing[field]), anyStringSlice(entry[field])...)))
		}
		merged["learning_value_reason_codes"] = stringsToAny(canonicalLearningReasonCodes(append(anyStringSlice(existing["learning_value_reason_codes"]), anyStringSlice(entry["learning_value_reason_codes"])...)))
		merged["signal_strength"] = strongestLearningSignal(stringFromAny(existing["signal_strength"]), stringFromAny(entry["signal_strength"]))
		merged["facets"] = facetsToAny(mergeLearningFacets(anyFacets(existing["facets"]), anyFacets(entry["facets"])))
		sensitivity, labels := mergeLearningContentSafety(existing, entry, merged)
		merged["sensitivity"] = sensitivity
		merged["redaction_labels"] = stringsToAny(labels)
		entries[index] = merged
		return entries, merged
	}
	return append(entries, entry), entry
}

func indexEntryFromLearning(entry map[string]any) map[string]any {
	id := learningIndexID(stringFromAny(entry["recurrence_key"]), stringFromAny(entry["first_seen"]))
	lesson := firstString(stringFromAny(entry["recommended_action"]), firstLine(stringFromAny(entry["evidence"])), stringFromAny(entry["summary"]))
	return map[string]any{
		"id": id, "problem": firstString(stringFromAny(entry["problem"]), stringFromAny(entry["summary"])), "lesson": lesson,
		"learning_type": entry["learning_type"], "source_command": entry["source_command"], "recurrence_key": entry["recurrence_key"],
		"applies_to": entry["applies_to"], "trigger_signals": stringsToAny(triggerSignalsFromLearning(entry)), "detail": "./" + id + ".md",
		"first_seen": entry["first_seen"], "last_seen": entry["last_seen"], "occurrence_count": entry["occurrence_count"],
		"signal_strength": entry["signal_strength"], "facets": entry["facets"], "sensitivity": entry["sensitivity"], "redaction_labels": entry["redaction_labels"],
		"learning_value_tier": entry["learning_value_tier"], "learning_value_reason_codes": entry["learning_value_reason_codes"],
		"sensitivity_risk_tier": entry["sensitivity_risk_tier"], "assessment_decision": entry["assessment_decision"], "assessment_reason": entry["assessment_reason"],
	}
}

func readLearningEntries(path string) (string, []map[string]any, error) {
	raw, err := os.ReadFile(path)
	if os.IsNotExist(err) {
		return "", []map[string]any{}, nil
	}
	if err != nil {
		return "", nil, err
	}
	preamble, payloads, err := extractLearningPayloadBlock(string(raw))
	if err != nil {
		return "", nil, err
	}
	for i, payload := range payloads {
		payloads[i] = sanitizeLearningEntry(payload)
	}
	return preamble, payloads, nil
}

func readLearningEntriesIfPresent(path string) []map[string]any {
	_, entries, err := readLearningEntries(path)
	if err != nil {
		return []map[string]any{}
	}
	return entries
}

func readLearningIndexEntries(path string) (string, []map[string]any, error) {
	return readLearningEntries(path)
}

func readLearningIndexEntriesWithDiagnostics(path string) ([]map[string]any, []string) {
	if _, err := os.Stat(path); os.IsNotExist(err) {
		return []map[string]any{}, []string{"Learning index is missing; restore the project Learning bootstrap assets before capture."}
	}
	preamble, payloads, err := readLearningIndexEntries(path)
	_ = preamble
	if err != nil {
		return []map[string]any{}, []string{"learning_index_parse_error:" + typeName(err)}
	}
	valid := []map[string]any{}
	warnings := []string{}
	for i, payload := range payloads {
		if err := validateLearningIndexEntry(payload); err != nil {
			warnings = append(warnings, fmt.Sprintf("learning_index_entry_%d_skipped:%s", i, typeName(err)))
			continue
		}
		valid = append(valid, payload)
	}
	return valid, warnings
}

func extractLearningPayloadBlock(content string) (string, []map[string]any, error) {
	if !strings.Contains(content, learningMachineBegin) || !strings.Contains(content, learningMachineEnd) {
		return strings.TrimRight(content, "\r\n"), []map[string]any{}, nil
	}
	parts := strings.SplitN(content, learningMachineBegin, 2)
	rest := strings.SplitN(parts[1], learningMachineEnd, 2)
	if len(rest) != 2 {
		return "", nil, fmt.Errorf("learning payload block is incomplete")
	}
	text := strings.TrimSpace(rest[0])
	if text == "" {
		return strings.TrimRight(parts[0], "\r\n"), []map[string]any{}, nil
	}
	var payload []map[string]any
	if err := json.Unmarshal([]byte(text), &payload); err != nil {
		return "", nil, err
	}
	return strings.TrimRight(parts[0], "\r\n"), payload, nil
}

func writeLearningEntries(path, preamble string, entries []map[string]any) error {
	return writeLearningText(path, renderLearningFile(preamble, entries))
}

func writeLearningIndexEntries(path, preamble string, entries []map[string]any) error {
	return writeLearningText(path, renderLearningIndexFile(preamble, entries))
}

func writeLearningText(path, content string) error {
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	return atomicWriteFile(path, []byte(content), 0o644)
}

func renderLearningFile(preamble string, entries []map[string]any) string {
	var buf bytes.Buffer
	payload, _ := json.MarshalIndent(entries, "", "  ")
	buf.WriteString(strings.TrimRight(preamble, "\r\n"))
	buf.WriteString("\n\n")
	buf.WriteString(learningMachineBegin + "\n")
	buf.Write(payload)
	buf.WriteString("\n" + learningMachineEnd + "\n\n## Managed Entries\n\n")
	if len(entries) == 0 {
		buf.WriteString("_No entries recorded yet._\n")
		return buf.String()
	}
	for i, entry := range entries {
		if i > 0 {
			buf.WriteString("\n---\n\n")
		}
		buf.WriteString(renderLearningEntrySummary(entry))
	}
	buf.WriteString("\n")
	return buf.String()
}

func renderLearningIndexFile(preamble string, entries []map[string]any) string {
	var buf bytes.Buffer
	payload, _ := json.MarshalIndent(entries, "", "  ")
	buf.WriteString(strings.TrimRight(preamble, "\r\n"))
	buf.WriteString("\n\n")
	buf.WriteString(learningMachineBegin + "\n")
	buf.Write(payload)
	buf.WriteString("\n" + learningMachineEnd + "\n\n## Managed Entries\n\n")
	if len(entries) == 0 {
		buf.WriteString("_No learning index entries recorded yet._\n")
		return buf.String()
	}
	for i, entry := range entries {
		if i > 0 {
			buf.WriteString("\n---\n\n")
		}
		buf.WriteString(renderLearningIndexSummary(entry))
	}
	buf.WriteString("\n")
	return buf.String()
}

func renderLearningEntrySummary(entry map[string]any) string {
	return fmt.Sprintf("### %s - %s\n\n- Status: `%s`\n- Type: `%s`\n- Source Command: `%s`\n- Recurrence Key: `%s`\n- Scope: `%s`\n- Applies To: %s\n- Signal: `%s`\n- Occurrence Count: %d\n- First Seen: `%s`\n- Last Seen: `%s`\n\n#### Evidence\n\n%s\n",
		entry["id"], entry["summary"], entry["status"], entry["learning_type"], entry["source_command"], entry["recurrence_key"], entry["default_scope"], strings.Join(anyStringSlice(entry["applies_to"]), ", "), entry["signal_strength"], intFromAny(entry["occurrence_count"]), entry["first_seen"], entry["last_seen"], entry["evidence"])
}

func renderLearningIndexSummary(entry map[string]any) string {
	return fmt.Sprintf("### %s - %s\n\n- Type: `%s`\n- Source Command: `%s`\n- Recurrence Key: `%s`\n- Applies To: %s\n- Trigger Signals: %s\n- Signal: `%s`\n- Occurrence Count: %d\n- First Seen: `%s`\n- Last Seen: `%s`\n- Detail: `%s`\n\n#### Lesson\n\n%s\n",
		entry["id"], entry["problem"], entry["learning_type"], entry["source_command"], entry["recurrence_key"], strings.Join(anyStringSlice(entry["applies_to"]), ", "), strings.Join(anyStringSlice(entry["trigger_signals"]), ", "), entry["signal_strength"], intFromAny(entry["occurrence_count"]), entry["first_seen"], entry["last_seen"], entry["detail"], entry["lesson"])
}

func writeLearningDetail(path string, entry, indexEntry map[string]any) error {
	payload := []map[string]any{entry}
	raw, _ := json.MarshalIndent(payload, "", "  ")
	content := strings.Join([]string{
		"# " + stringFromAny(indexEntry["problem"]), "", learningMachineBegin, string(raw), learningMachineEnd, "",
		"## Problem", "", stringFromAny(indexEntry["problem"]), "",
		"## Lesson", "", stringFromAny(indexEntry["lesson"]), "",
		"## Recommended Action", "", firstString(stringFromAny(entry["recommended_action"]), stringFromAny(indexEntry["lesson"])), "",
		"## When To Apply", "", strings.Join(anyStringSlice(indexEntry["applies_to"]), ", "), "",
		"## Trigger Signals", "", bulletsOrEmpty(anyStringSlice(indexEntry["trigger_signals"]), "_No trigger signals recorded._"), "",
		"## Evidence", "", stringFromAny(entry["evidence"]), "",
	}, "\n")
	return writeLearningText(path, content)
}

func appendLearningReview(path, note string, policy learningPolicy) error {
	if _, err := os.Stat(path); os.IsNotExist(err) {
		if err := writeLearningText(path, learningReviewTemplateText()); err != nil {
			return err
		}
	}
	raw, err := os.ReadFile(path)
	if err != nil {
		return err
	}
	content := redactLearningReferenceTextWithPolicy(strings.TrimRight(string(raw), "\r\n"), policy).text + fmt.Sprintf("\n- `%s` %s\n", learningNow(), redactLearningReferenceTextWithPolicy(note, policy).text)
	return writeLearningText(path, content)
}

func (service learningService) suggestQuickAutoCapture(workspace string) (string, []learningSuggestion, error) {
	path, err := safeLearningPath(service.projectRoot, workspace)
	if err != nil {
		return "", nil, err
	}
	workspaceRef := service.learningSourceRef(path)
	statusPath := filepath.Join(path, "STATUS.md")
	frontmatter, sections := loadLearningSectionedMarkdown(statusPath)
	status := strings.ToLower(stringFromAny(frontmatter["status"]))
	exec := sections["Execution"]
	focus := sections["Current Focus"]
	validation := sections["Validation"]
	retry := intFromAny(exec["retry_attempts"])
	blockerReason := stringFromAny(exec["blocker_reason"])
	recoveryAction := stringFromAny(exec["recovery_action"])
	fallback := stringFromAny(exec["execution_fallback"])
	completedChecks := anyStringSlice(validation["completed_checks"])
	suggestions := []learningSuggestion{}
	if status == "resolved" && retry >= 1 && (len(completedChecks) > 0 || blockerReason != "" || recoveryAction != "") {
		suggestions = append(suggestions, learningSuggestion{
			learningType: "recovery_path", summary: "Retry the smallest recorded recovery step and rerun scoped checks before resolving a quick task",
			recurrenceKey: "quick.retry-recovery-step-before-resolve", evidence: formatLearningEvidence("Observed auto-capture evidence from quick STATUS.md", [][2]string{{"workspace", workspaceRef}, {"status", status}, {"retry_attempts", strconv.Itoa(retry)}, {"goal", stringFromAny(focus["goal"])}, {"next_action", stringFromAny(focus["next_action"])}, {"blocker_reason", blockerReason}, {"recovery_action", recoveryAction}, {"completed_checks", strings.Join(completedChecks, ", ")}}),
			problem: "A quick task can be marked resolved before the recovery step and scoped checks prove the fix.", recommendedAction: "Run the smallest recorded recovery action, then rerun the scoped checks before resolving.", triggerSignals: []string{"quick task recovered after retry", "quick blocker cleared"}, successCriteria: []string{"the recorded recovery action is followed by green scoped checks"}, avoid: []string{"resolving immediately after the retry without validation"},
		})
	}
	if fallback != "" && !strings.EqualFold(fallback, "none") {
		suggestions = append(suggestions, learningSuggestion{
			learningType: "project_constraint", summary: "Leader-inline quick-task fallback should preserve the runtime unavailability reason as a reusable execution constraint",
			recurrenceKey: "quick.leader-inline-fallback-preserves-runtime-unavailability-reason", evidence: formatLearningEvidence("Observed auto-capture evidence from quick STATUS.md", [][2]string{{"workspace", workspaceRef}, {"status", status}, {"goal", stringFromAny(focus["goal"])}, {"execution_fallback", fallback}, {"blocker_reason", blockerReason}, {"recovery_action", recoveryAction}}),
			problem: "An inline fallback can hide a reusable runtime limitation and cause future dispatch attempts to repeat the same failure.", recommendedAction: "Check the recorded runtime limitation before dispatch and reuse the approved fallback only while it still applies.", triggerSignals: []string{"leader-inline fallback used", "agent runtime unavailable"}, successCriteria: []string{"future routing checks runtime readiness before selecting the fallback"}, avoid: []string{"retrying unavailable execution infrastructure without a state change"},
		})
	}
	return statusPath, suggestions, nil
}

func (service learningService) suggestWorkflowStateAutoCapture(featureDir, command string) (string, []learningSuggestion, error) {
	dir, err := safeLearningPath(service.projectRoot, featureDir)
	if err != nil {
		return "", nil, err
	}
	dirRef := service.learningSourceRef(dir)
	statePath := filepath.Join(dir, "workflow-state.md")
	_, sections := loadLearningSectionedMarkdown(statePath)
	flat := flattenLearningSections(sections)
	nextCommand := cleanLearningPlaceholder(stringFromAny(flat["next_command"]))
	nextAction := stringFromAny(flat["next_action"])
	routeReason := cleanLearningPlaceholder(stringFromAny(flat["route_reason"]))
	blockedReason := cleanLearningPlaceholder(stringFromAny(flat["blocked_reason"]))
	falseStarts := anyStringSlice(flat["false_starts"])
	hidden := anyStringSlice(flat["hidden_dependencies"])
	constraints := anyStringSlice(flat["reusable_constraints"])
	triggers := anyStringSlice(flat["trigger_signals"])
	status := stringFromAny(flat["status"])
	phaseMode := stringFromAny(flat["phase_mode"])
	suggestions := []learningSuggestion{}
	if nextCommand != "" && routeReason != "" {
		suggestions = append(suggestions, learningSuggestion{learningType: "workflow_gap", summary: "Workflow-state handoff should preserve the exact re-entry reason so later stages do not rediscover why routing changed", recurrenceKey: command + ".workflow-state-preserves-reentry-reason", evidence: formatLearningEvidence("Observed auto-capture evidence from workflow-state.md", [][2]string{{"feature_dir", dirRef}, {"command", command}, {"status", status}, {"phase_mode", phaseMode}, {"next_command", nextCommand}, {"next_action", nextAction}, {"route_reason", routeReason}, {"blocked_reason", blockedReason}}), problem: "A changed workflow route can lose its exact re-entry reason between stages or after resume.", recommendedAction: "Preserve the next command, next action, and exact route reason before handoff.", triggerSignals: []string{"next command changed", "route reason recorded", "workflow re-entry"}, successCriteria: []string{"the resumed workflow can explain and follow the route without chat history"}, avoid: []string{"routing from chat memory alone"}})
	}
	if blockedReason != "" && !(nextCommand != "" && routeReason != "") {
		suggestions = append(suggestions, learningSuggestion{learningType: "state_surface_gap", summary: "Workflow-state should preserve blocked reasons before terminal or handoff stops", recurrenceKey: command + ".workflow-state-preserves-blocked-reason", evidence: formatLearningEvidence("Observed auto-capture evidence from workflow-state.md", [][2]string{{"feature_dir", dirRef}, {"command", command}, {"status", status}, {"phase_mode", phaseMode}, {"blocked_reason", blockedReason}, {"next_action", nextAction}}), problem: "A blocked or terminal state can lose the blocker detail needed for safe recovery.", recommendedAction: "Preserve the blocker, owner, next action, and unblock condition before stopping.", triggerSignals: []string{"workflow blocked", "blocked_reason present"}, successCriteria: []string{"resume can continue from the recorded unblock condition"}, avoid: []string{"reporting blocked without a durable reason"}})
	}
	if len(falseStarts) > 0 {
		suggestions = append(suggestions, learningSuggestion{learningType: "false_lead_pattern", summary: "Workflow-state should preserve false starts so later runs do not repeat the same route or diagnosis loop", recurrenceKey: command + ".workflow-state-preserves-false-starts", evidence: formatLearningEvidence("Observed auto-capture evidence from workflow-state.md", [][2]string{{"feature_dir", dirRef}, {"command", command}, {"status", status}, {"phase_mode", phaseMode}, {"false_starts", strings.Join(falseStarts, ", ")}, {"next_command", nextCommand}, {"next_action", nextAction}}), problem: "A later run can repeat a route or diagnosis already disproved by evidence.", recommendedAction: "Check recorded false starts before repeating a route or hypothesis.", triggerSignals: []string{"false start recorded", "hypothesis changed", "route rejected"}, successCriteria: []string{"the rejected path is not retried without new contradictory evidence"}, avoid: []string{"replaying a false start without new evidence"}})
	}
	if len(hidden) > 0 || len(constraints) > 0 {
		suggestions = append(suggestions, learningSuggestion{learningType: "project_constraint", summary: "Dependencies and reusable constraints discovered in workflow-state should be promoted into shared memory before later work resumes", recurrenceKey: command + ".workflow-state-promotes-discovered-constraints", evidence: formatLearningEvidence("Observed auto-capture evidence from workflow-state.md", [][2]string{{"feature_dir", dirRef}, {"command", command}, {"status", status}, {"phase_mode", phaseMode}, {"hidden_dependencies", strings.Join(hidden, ", ")}, {"reusable_constraints", strings.Join(constraints, ", ")}, {"next_command", nextCommand}}), problem: "A hidden dependency or reusable constraint can disappear when it remains only in workflow-local state.", recommendedAction: "Apply the recorded dependency or constraint before planning or changing the affected surface.", triggerSignals: []string{"hidden dependency", "reusable constraint", "cross-workflow dependency"}, successCriteria: []string{"downstream work names and honors the dependency or constraint"}, avoid: []string{"rediscovering the constraint after implementation starts"}})
	}
	for _, signal := range triggers {
		suggestions = append(suggestions, semanticLearningSuggestion(command, dirRef, signal))
	}
	return statePath, suggestions, nil
}

func (service learningService) suggestImplementAutoCapture(featureDir string) (string, []learningSuggestion, error) {
	dir, err := safeLearningPath(service.projectRoot, featureDir)
	if err != nil {
		return "", nil, err
	}
	dirRef := service.learningSourceRef(dir)
	tracker := filepath.Join(dir, "implement-tracker.md")
	front, sections := loadLearningSectionedMarkdown(tracker)
	_ = front
	flat := flattenLearningSections(sections)
	retry := intFromAny(flat["retry_attempts"])
	failed := anyStringSlice(flat["failed_tasks"])
	completed := anyStringSlice(flat["completed_checks"])
	status := strings.ToLower(stringFromAny(flat["status"]))
	suggestions := []learningSuggestion{}
	if status == "resolved" && retry >= 1 && len(completed) > 0 {
		suggestions = append(suggestions, learningSuggestion{learningType: "recovery_path", summary: "Rerun planned validation after implementation recovery before resolving the feature", recurrenceKey: "implement.rerun-validation-after-recovery-before-resolve", evidence: formatLearningEvidence("Observed auto-capture evidence from implement-tracker.md", [][2]string{{"feature_dir", dirRef}, {"tracker_status", status}, {"retry_attempts", strconv.Itoa(retry)}, {"failed_tasks", strings.Join(failed, ", ")}, {"completed_checks", strings.Join(completed, ", ")}}), problem: "Implementation recovery can be marked resolved before the planned validation is rerun.", recommendedAction: "Rerun the planned validation after recovery and record green evidence before resolving the feature.", triggerSignals: []string{"implementation retry completed", "recovery before terminal resolution"}, successCriteria: []string{"all planned post-recovery checks are recorded green"}, avoid: []string{"resolving from the code change alone"}})
	}
	if retry >= 1 && len(failed) > 0 && len(completed) > 0 {
		suggestions = append(suggestions, learningSuggestion{learningType: "pitfall", summary: "Failed implementation tasks should keep execution in recovery until validation turns green", recurrenceKey: "implement.failed-tasks-keep-recovery-active-until-validation", evidence: formatLearningEvidence("Observed auto-capture evidence from implement-tracker.md", [][2]string{{"feature_dir", dirRef}, {"tracker_status", status}, {"retry_attempts", strconv.Itoa(retry)}, {"failed_tasks", strings.Join(failed, ", ")}, {"completed_checks", strings.Join(completed, ", ")}}), problem: "A failed task can be treated as finished while its recovery validation is still incomplete.", recommendedAction: "Keep execution in recovery, clear the failed task, and rerun its planned checks before continuing.", triggerSignals: []string{"failed task after retry", "validation incomplete after task failure"}, successCriteria: []string{"failed tasks are cleared and their planned checks are green"}, avoid: []string{"continuing later batches while failed-task validation is unresolved"}})
	}
	return tracker, suggestions, nil
}

func (service learningService) suggestDebugAutoCapture(sessionFile string) (string, []learningSuggestion, error) {
	path, err := safeLearningPath(service.projectRoot, sessionFile)
	if err != nil {
		return "", nil, err
	}
	if _, err := os.Stat(path); err != nil {
		return path, nil, nil
	}
	return path, nil, nil
}

func semanticLearningSuggestion(command, featureDir, signal string) learningSuggestion {
	rawKind, detail, found := strings.Cut(signal, ":")
	kind := strings.ReplaceAll(strings.ReplaceAll(strings.ToLower(strings.TrimSpace(rawKind)), "-", "_"), " ", "_")
	if !found {
		detail = signal
	}
	detail = strings.Join(strings.Fields(strings.TrimSpace(detail)), " ")
	safeDetail := redactLearningText(detail).text
	type actionSet struct{ typ, action, success, avoid string }
	table := map[string]actionSet{
		"user_correction": {"user_preference", "Apply the corrected assumption, preference, or boundary before repeating the affected work.", "The next affected workflow reflects the correction without requiring the user to repeat it.", "Continuing from the superseded assumption."},
		"cognition_gap":   {"map_coverage_gap", "Use live evidence for the missing surface and refresh cognition coverage through the owning map workflow.", "The truth-owning surface is queryable and the active workflow no longer depends on a stale omission.", "Treating missing cognition coverage as evidence that the surface does not exist."},
		"tooling_trap":    {"tooling_trap", "Verify the environment and tool boundary before diagnosing the same symptom as a product defect.", "The environment/tool cause is ruled in or out before production code changes.", "Changing product code before checking the recorded tooling condition."},
	}
	selected, ok := table[kind]
	if !ok {
		selected = actionSet{"pitfall", "Apply the recorded signal before repeating the affected work.", "The next affected workflow uses the signal and records confirming evidence.", "Ignoring an explicit reusable-learning signal."}
	}
	label := strings.ReplaceAll(kind, "_", " ")
	return learningSuggestion{learningType: selected.typ, summary: label + ": " + safeDetail, recurrenceKey: command + ".trigger." + kind + ".digest-" + safeSemanticLearningDigest(safeDetail), evidence: formatLearningEvidence("Observed explicit Learning trigger from workflow-state.md", [][2]string{{"feature_dir", featureDir}, {"command", command}, {"trigger_kind", kind}, {"trigger_detail", safeDetail}}), problem: "The recorded " + label + " signal could be lost after handoff or compaction: " + safeDetail, recommendedAction: selected.action, triggerSignals: []string{kind}, successCriteria: []string{selected.success}, avoid: []string{selected.avoid}}
}

func loadLearningSectionedMarkdown(path string) (map[string]any, map[string]map[string]any) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return map[string]any{}, map[string]map[string]any{}
	}
	front, body := parseLearningFrontmatter(string(raw))
	sections := map[string]map[string]any{}
	var current string
	lines := []string{}
	flush := func() {
		if current != "" {
			sections[current] = parseLearningYAMLLite(lines)
		}
	}
	for _, line := range strings.Split(body, "\n") {
		if match := regexp.MustCompile(`^##\s+(.+?)\s*$`).FindStringSubmatch(line); len(match) == 2 {
			flush()
			current = strings.TrimSpace(match[1])
			lines = []string{}
			continue
		}
		if current != "" {
			lines = append(lines, line)
		}
	}
	flush()
	return front, sections
}

func parseLearningFrontmatter(text string) (map[string]any, string) {
	if !strings.HasPrefix(text, "---\n") && !strings.HasPrefix(text, "---\r\n") {
		return map[string]any{}, text
	}
	lines := strings.Split(text, "\n")
	end := -1
	for i := 1; i < len(lines); i++ {
		if strings.TrimSpace(strings.TrimSuffix(lines[i], "\r")) == "---" {
			end = i
			break
		}
	}
	if end < 0 {
		return map[string]any{}, text
	}
	fields := parseLearningYAMLLite(lines[1:end])
	return fields, strings.Join(lines[end+1:], "\n")
}

func parseLearningYAMLLite(lines []string) map[string]any {
	result := map[string]any{}
	var currentKey string
	for _, raw := range lines {
		line := strings.TrimRight(raw, "\r")
		trimmed := strings.TrimSpace(line)
		if trimmed == "" || strings.HasPrefix(trimmed, "#") {
			continue
		}
		if strings.HasPrefix(trimmed, "- ") && currentKey != "" {
			result[currentKey] = append(anyStringSlice(result[currentKey]), strings.TrimSpace(strings.TrimPrefix(trimmed, "- ")))
			continue
		}
		if !strings.Contains(trimmed, ":") {
			continue
		}
		parts := strings.SplitN(trimmed, ":", 2)
		key := strings.TrimSpace(parts[0])
		value := strings.TrimSpace(parts[1])
		currentKey = key
		if value == "" {
			result[key] = []any{}
			continue
		}
		value = strings.Trim(value, `"'`)
		if number, err := strconv.Atoi(value); err == nil {
			result[key] = float64(number)
		} else if strings.EqualFold(value, "[]") {
			result[key] = []any{}
		} else {
			result[key] = value
		}
	}
	return result
}

func flattenLearningSections(sections map[string]map[string]any) map[string]any {
	flat := map[string]any{}
	for _, section := range sections {
		for key, value := range section {
			flat[key] = value
		}
	}
	return flat
}

func safeLearningPath(projectRoot, raw string) (string, error) {
	root, err := filepath.Abs(projectRoot)
	if err != nil {
		return "", err
	}
	root, err = filepath.EvalSymlinks(root)
	if err != nil {
		return "", err
	}
	candidate := filepath.FromSlash(raw)
	if !filepath.IsAbs(candidate) && filepath.VolumeName(candidate) == "" {
		candidate = filepath.Join(root, candidate)
	}
	candidate, err = filepath.Abs(candidate)
	if err != nil {
		return "", err
	}
	rel, err := filepath.Rel(root, candidate)
	if err != nil || rel == ".." || strings.HasPrefix(rel, ".."+string(filepath.Separator)) {
		return "", fmt.Errorf("path must stay inside the project root")
	}
	return secureProjectPath(root, filepath.ToSlash(rel))
}

func learningSnapshotFingerprint(command, sourcePath string, suggestions []learningSuggestion, policies ...learningPolicy) (string, error) {
	policy := builtinLearningPolicy()
	if len(policies) > 0 {
		policy = policies[0]
	}
	canonicalSuggestions := []any{}
	for _, suggestion := range suggestions {
		canonicalSuggestions = append(canonicalSuggestions, map[string]any{
			"learning_type": suggestion.learningType, "recurrence_key": sanitizeLearningRecurrenceKeyWithPolicy(suggestion.recurrenceKey, policy).text,
			"signal_strength": suggestion.signalStrength, "summary_digest": safeSemanticLearningDigest(redactLearningTextWithPolicy(suggestion.summary, policy).text),
			"evidence_digest": safeSemanticLearningDigest(redactLearningTextWithPolicy(suggestion.evidence, policy).text),
		})
	}
	payload := map[string]any{
		"command": command, "source_ref": sourcePath, "suggestions": canonicalSuggestions,
		"assessment_version": learningAssessmentVersion, "policy_digest": policy.digest(),
	}
	raw, err := json.Marshal(payload)
	if err != nil {
		return "", err
	}
	sum := sha256.Sum256(raw)
	return hex.EncodeToString(sum[:]), nil
}

func (service learningService) loadAutoCaptureRegistry(paths learningPaths) (map[string]any, error) {
	path := filepath.Join(filepath.Dir(paths.review), "auto-capture.json")
	raw, err := os.ReadFile(path)
	if os.IsNotExist(err) {
		return map[string]any{}, nil
	}
	if err != nil {
		return nil, err
	}
	var payload map[string]any
	if err := json.Unmarshal(raw, &payload); err != nil {
		return map[string]any{}, nil
	}
	return payload, nil
}

func (service learningService) normalizeAutoCaptureRegistry(payload map[string]any) (map[string]any, bool) {
	normalized := map[string]any{}
	changed := false
	for rawKey, rawValue := range payload {
		entry := mapStringAny(rawValue)
		if len(entry) == 0 {
			changed = true
			continue
		}
		key := normalizeAutoCaptureRegistryKey(rawKey)
		if key != rawKey {
			changed = true
		}
		command, err := normalizeLearningCommand(stringFromAny(entry["command"]))
		if err != nil || !learningAutoCaptureCommandSupported(command) {
			changed = true
			continue
		}
		source := firstString(stringFromAny(entry["source_ref"]), stringFromAny(entry["source_path"]))
		sourceRef := service.learningSourceRef(source)
		keys := []any{}
		for _, recurrenceKey := range anyStringSlice(entry["recurrence_keys"]) {
			if sanitized := sanitizeLearningRecurrenceKey(recurrenceKey).text; sanitized != "" {
				keys = append(keys, sanitized)
				if sanitized != recurrenceKey {
					changed = true
				}
			}
		}
		capturedAt := stringFromAny(entry["captured_at"])
		if capturedAt != "" {
			if _, err := time.Parse(time.RFC3339, capturedAt); err != nil {
				capturedAt = ""
				changed = true
			}
		}
		clean := map[string]any{
			"command":         command,
			"source_ref":      sourceRef,
			"recurrence_keys": keys,
			"captured_at":     capturedAt,
		}
		if !autoCaptureRegistryEntryEqual(entry, clean) {
			changed = true
		}
		normalized[key] = clean
	}
	return normalized, changed
}

func learningAutoCaptureCommandSupported(command string) bool {
	return command == "sp-implement" || command == "sp-quick" || command == "sp-debug" || workflowStateAutoCaptureCommands[command]
}

func normalizeAutoCaptureRegistryKey(key string) string {
	if regexp.MustCompile(`^[a-f0-9]{64}$`).MatchString(key) {
		return key
	}
	sum := sha256.Sum256([]byte(redactLearningText(key).text))
	return hex.EncodeToString(sum[:])
}

func autoCaptureRegistryEntryEqual(left, right map[string]any) bool {
	if len(left) != len(right) {
		return false
	}
	for key, rightValue := range right {
		switch key {
		case "recurrence_keys":
			leftKeys := anyStringSlice(left[key])
			rightKeys := anyStringSlice(rightValue)
			if len(leftKeys) != len(rightKeys) {
				return false
			}
			for i := range leftKeys {
				if leftKeys[i] != rightKeys[i] {
					return false
				}
			}
		default:
			if stringFromAny(left[key]) != stringFromAny(rightValue) {
				return false
			}
		}
	}
	return true
}

func (service learningService) learningSourceRef(path string) string {
	if strings.TrimSpace(path) == "" {
		return "unknown-source"
	}
	root, err := filepath.Abs(service.projectRoot)
	if err != nil {
		return safeLearningBasenameRef(path)
	}
	candidate := filepath.FromSlash(path)
	if foreignLearningAbsolutePath(path) {
		return safeLearningBasenameRef(path)
	}
	if !filepath.IsAbs(candidate) && filepath.VolumeName(candidate) == "" {
		candidate = filepath.Join(root, candidate)
	}
	absolute, err := filepath.Abs(candidate)
	if err != nil {
		return safeLearningBasenameRef(path)
	}
	if rel, err := filepath.Rel(root, absolute); err == nil && rel != ".." && !strings.HasPrefix(rel, ".."+string(filepath.Separator)) {
		return filepath.ToSlash(rel)
	}
	return safeLearningBasenameRef(path)
}

func foreignLearningAbsolutePath(path string) bool {
	trimmed := strings.TrimSpace(path)
	if trimmed == "" {
		return false
	}
	normalized := strings.ReplaceAll(trimmed, "\\", "/")
	if runtime.GOOS != "windows" && (regexp.MustCompile(`^[A-Za-z]:/`).MatchString(normalized) || strings.HasPrefix(normalized, "//")) {
		return true
	}
	if runtime.GOOS == "windows" && strings.HasPrefix(normalized, "/") {
		return true
	}
	return false
}

func safeLearningBasenameRef(path string) string {
	normalized := strings.TrimRight(strings.ReplaceAll(strings.TrimSpace(path), "\\", "/"), "/")
	base := normalized
	if separator := strings.LastIndex(normalized, "/"); separator >= 0 {
		base = normalized[separator+1:]
	}
	if base == "." || base == ".." || base == "" {
		return "external-source"
	}
	redacted := redactLearningText(base).text
	if strings.TrimSpace(redacted) == "" {
		return "external-source"
	}
	return redacted
}

func (service learningService) writeAutoCaptureRegistry(paths learningPaths, payload map[string]any) error {
	raw, _ := json.MarshalIndent(payload, "", "  ")
	return writeLearningText(filepath.Join(filepath.Dir(paths.review), "auto-capture.json"), string(raw)+"\n")
}

func normalizeLearningCommand(commandName string) (string, error) {
	raw := strings.ToLower(strings.TrimSpace(commandName))
	for strings.HasPrefix(raw, "/") {
		raw = strings.TrimPrefix(raw, "/")
	}
	if raw == "" {
		return "", fmt.Errorf("command name is required")
	}
	if strings.HasPrefix(raw, "spx-") || strings.HasPrefix(raw, "spx.") {
		raw = "sp-" + raw[4:]
	} else if strings.HasPrefix(raw, "sp.") {
		raw = "sp-" + raw[3:]
	} else if !strings.HasPrefix(raw, "sp-") {
		raw = "sp-" + raw
	}
	if raw == "sp-research" {
		raw = "sp-deep-research"
	}
	if !regexp.MustCompile(`^sp-[a-z0-9][a-z0-9-]*$`).MatchString(raw) {
		return "", fmt.Errorf("invalid command name %q", commandName)
	}
	return raw, nil
}

func parseLearningContexts(values []string) map[string][]string {
	facets := map[string][]string{}
	seen := map[string]bool{}
	for _, raw := range values {
		key, value, ok := strings.Cut(strings.TrimSpace(raw), "=")
		if !ok {
			continue
		}
		normalizedKey := strings.ReplaceAll(strings.ToLower(strings.TrimSpace(key)), "-", "_")
		facet := learningContextKeyMap[normalizedKey]
		value = strings.Join(strings.Fields(strings.ReplaceAll(strings.TrimSpace(value), "\\", "/")), " ")
		if facet == "" || value == "" {
			continue
		}
		token := facet + "\x00" + strings.ToLower(value)
		if seen[token] {
			continue
		}
		seen[token] = true
		facets[facet] = append(facets[facet], value)
	}
	return normalizeLearningFacets(facets)
}

func learningContextArgv(context map[string][]string) []any {
	args := []any{}
	argumentKey := map[string]string{}
	for raw, facet := range learningContextKeyMap {
		argumentKey[facet] = raw
	}
	for _, facet := range learningFacetKeys {
		for _, value := range context[facet] {
			args = append(args, "--context", argumentKey[facet]+"="+value)
		}
	}
	return args
}

func normalizeLearningFacets(value map[string][]string) map[string][]string {
	result := map[string][]string{}
	for _, key := range learningFacetKeys {
		values := uniqueSortedTrimmed(value[key])
		if len(values) > 0 {
			result[key] = values
		}
	}
	return result
}

func normalizeLearningType(value string) (string, error) {
	normalized := strings.ToLower(strings.TrimSpace(value))
	if !learningTypes[normalized] {
		return "", fmt.Errorf("unsupported learning type %q", value)
	}
	return normalized, nil
}

func normalizeLearningCommands(values []string) []string {
	result := []string{}
	for _, value := range values {
		if normalized, err := normalizeLearningCommand(value); err == nil {
			result = append(result, normalized)
		}
	}
	return uniqueSortedTrimmed(result)
}

func normalizeLearningCommandsWithPolicy(values []string, policy learningPolicy) []string {
	result := []string{}
	for _, value := range values {
		if normalized, err := normalizeLearningCommand(value); err == nil {
			result = append(result, safeLearningCommandProjection(normalized, policy))
		}
	}
	return uniqueSortedTrimmed(result)
}

func learningWorkflowPolicy(command string) string {
	policies := map[string]string{"sp-accept": "consume-only", "sp-analyze": "consume-only", "sp-ask": "consume-only", "sp-auto": "consume-only", "sp-constitution": "consume-only", "sp-explain": "consume-only", "sp-fast": "skip", "sp-implement-teams": "consume-only", "sp-taskstoissues": "consume-only", "sp-team": "consume-only"}
	if policy := policies[command]; policy != "" {
		return policy
	}
	return "consume-capture"
}

func defaultScopeForLearningType(typ string) string {
	if typ == "user_preference" || typ == "project_constraint" {
		return "global"
	}
	if typ == "workflow_gap" || typ == "routing_mistake" || typ == "state_surface_gap" || typ == "decision_debt" {
		return "planning-heavy"
	}
	if typ == "recovery_path" || typ == "verification_gap" || typ == "false_lead_pattern" {
		return "execution-heavy"
	}
	if typ == "map_coverage_gap" || typ == "tooling_trap" || typ == "near_miss" {
		return "cross-workflow"
	}
	return "implementation-heavy"
}

func defaultAppliesToForLearningType(typ, source string) []string {
	switch typ {
	case "user_preference", "project_constraint":
		return append([]string{}, knownLearningCommands...)
	case "workflow_gap":
		return []string{"sp-specify", "sp-deep-research", "sp-plan", "sp-tasks", "sp-quick"}
	case "routing_mistake":
		return []string{"sp-fast", "sp-quick", "sp-specify", "sp-plan", "sp-tasks", "sp-implement", "sp-debug"}
	case "verification_gap":
		return []string{"sp-implement", "sp-accept", "sp-debug", "sp-quick", "sp-fast"}
	case "state_surface_gap":
		return append([]string{"sp-specify", "sp-deep-research", "sp-plan", "sp-tasks", "sp-implement", "sp-accept", "sp-debug", "sp-quick"}, mapWorkflowCommands...)
	case "map_coverage_gap":
		return append(append([]string{}, mapWorkflowCommands...), "sp-specify", "sp-deep-research", "sp-plan", "sp-tasks", "sp-implement", "sp-debug")
	case "tooling_trap":
		return append([]string{"sp-implement", "sp-debug", "sp-quick"}, mapWorkflowCommands...)
	case "false_lead_pattern":
		return []string{"sp-debug", "sp-implement", "sp-quick"}
	case "near_miss", "pitfall":
		return uniqueSortedTrimmed([]string{source, "sp-implement", "sp-debug", "sp-quick"})
	case "decision_debt":
		return append([]string{"sp-specify", "sp-deep-research", "sp-plan", "sp-tasks"}, mapWorkflowCommands...)
	case "recovery_path":
		return []string{"sp-implement", "sp-debug", "sp-quick"}
	default:
		return []string{source}
	}
}

func learningSummaryCard(indexEntry, entry map[string]any, sourceLayer, command string, contextMatch map[string]any, crossCommand, includeContext bool) map[string]any {
	status := "indexed"
	summary := stringFromAny(indexEntry["problem"])
	action := stringFromAny(indexEntry["lesson"])
	sensitivity := stringFromAny(indexEntry["sensitivity"])
	redactionLabels := anyStringSlice(indexEntry["redaction_labels"])
	if entry != nil {
		status = stringFromAny(entry["status"])
		summary = stringFromAny(entry["summary"])
		sensitivity = stringFromAny(entry["sensitivity"])
		redactionLabels = anyStringSlice(entry["redaction_labels"])
		if value := stringFromAny(entry["recommended_action"]); value != "" {
			action = value
		}
	}
	if sensitivity == "" {
		sensitivity = "safe"
	}
	assessmentEntry := indexEntry
	if entry != nil {
		assessmentEntry = entry
	}
	ref := stringFromAny(indexEntry["recurrence_key"])
	card := map[string]any{"ref": indexEntry["recurrence_key"], "summary": summary, "action": action, "type": indexEntry["learning_type"], "status": status, "signal": indexEntry["signal_strength"], "occurrences": indexEntry["occurrence_count"], "applies_to": indexEntry["applies_to"], "trigger_signals": indexEntry["trigger_signals"], "source_layer": sourceLayer, "sensitivity": sensitivity, "redaction_labels": stringsToAny(redactionLabels), "show_argv": []any{"specify-runtime", "learning", "show", "--ref", indexEntry["recurrence_key"], "--format", "json"}, "_source_command": indexEntry["source_command"], "_recurrence_family": learningRecurrenceFamily(stringFromAny(indexEntry["learning_type"]), ref), "_learning_value_tier": assessmentEntry["learning_value_tier"]}
	if assessment := learningAssessmentProjection(assessmentEntry); assessment != nil {
		card["assessment"] = assessment
	}
	if includeContext && intFromAny(contextMatch["matched_dimensions"]) > 0 {
		card["context_match"] = map[string]any{"matched_facets": contextMatch["matched_facets"], "matched_dimensions": contextMatch["matched_dimensions"], "matched_values": contextMatch["matched_values"], "exact_operation_owner": contextMatch["exact_operation_owner"], "cross_command": crossCommand}
		card["why_relevant"] = "task context matched"
	} else if command != "" {
		card["why_relevant"] = "applies to " + command
	}
	return card
}

func learningRecurrenceFamily(learningType, ref string) string {
	trimmed := strings.Trim(strings.TrimSpace(ref), ".")
	suffix := trimmed
	if parts := strings.SplitN(trimmed, ".", 2); len(parts) == 2 {
		suffix = parts[1]
	}
	if parts := strings.SplitN(suffix, "-", 2); len(parts) > 0 {
		suffix = parts[0]
	}
	return strings.TrimSpace(learningType) + ":" + suffix
}

func learningContextMatch(indexEntry map[string]any, context map[string][]string) map[string]any {
	matched := map[string]any{}
	facets := anyFacets(indexEntry["facets"])
	dimensions, values := 0, 0
	for key, queries := range context {
		stored := facets[key]
		hits := []string{}
		for _, query := range queries {
			for _, value := range stored {
				if strings.EqualFold(query, value) {
					hits = append(hits, value)
				}
			}
		}
		if len(hits) > 0 {
			matched[key] = stringsToAny(uniqueSortedTrimmed(hits))
			dimensions++
			values += len(uniqueSortedTrimmed(hits))
		}
	}
	return map[string]any{"matched_facets": matched, "matched_dimensions": float64(dimensions), "matched_values": float64(values), "exact_operation_owner": len(anyStringSlice(matched["operation_owners"])) > 0}
}

func learningContextAllowsCrossCommand(match map[string]any) bool {
	return match["exact_operation_owner"] == true || intFromAny(match["matched_dimensions"]) >= 2
}

func learningSearchText(indexEntry map[string]any) string {
	parts := []string{stringFromAny(indexEntry["recurrence_key"]), stringFromAny(indexEntry["problem"]), stringFromAny(indexEntry["lesson"]), stringFromAny(indexEntry["learning_type"])}
	parts = append(parts, anyStringSlice(indexEntry["trigger_signals"])...)
	parts = append(parts, anyStringSlice(indexEntry["applies_to"])...)
	for _, values := range anyFacets(indexEntry["facets"]) {
		parts = append(parts, values...)
	}
	return strings.Join(parts, " ")
}

func validateLearningIndexEntry(entry map[string]any) error {
	for _, key := range []string{"id", "problem", "lesson", "learning_type", "source_command", "recurrence_key", "applies_to", "trigger_signals", "detail", "first_seen", "last_seen", "occurrence_count", "signal_strength"} {
		if _, ok := entry[key]; !ok {
			return fmt.Errorf("missing %s", key)
		}
	}
	if !strings.HasPrefix(stringFromAny(entry["id"]), "learn-") || !validLearningDetailRef(stringFromAny(entry["detail"])) {
		return fmt.Errorf("invalid id or detail")
	}
	if _, err := normalizeLearningType(stringFromAny(entry["learning_type"])); err != nil {
		return err
	}
	return nil
}

func validLearningDetailRef(ref string) bool {
	return regexp.MustCompile(`^\./learn-[A-Za-z0-9][A-Za-z0-9._-]*\.md$`).MatchString(ref)
}

func learningIndexID(recurrenceKey, firstSeen string) string {
	date := "unknown-date"
	if regexp.MustCompile(`^\d{4}-\d{2}-\d{2}`).MatchString(firstSeen) {
		date = firstSeen[:10]
	}
	sum := sha256.Sum256([]byte(recurrenceKey))
	return fmt.Sprintf("learn-%s-%s-%s", date, truncateString(slugifyLearning(recurrenceKey), 56), hex.EncodeToString(sum[:])[:10])
}

func usedDetailByOther(entries []map[string]any, detail, key string) bool {
	for _, entry := range entries {
		if entry["recurrence_key"] != key && entry["detail"] == detail {
			return true
		}
	}
	return false
}

func unusedLearningDetailRef(entries []map[string]any, key, firstSeen string) (string, string) {
	base := learningIndexID(key, firstSeen)
	id := base
	for suffix := 2; usedDetailByOther(entries, "./"+id+".md", key); suffix++ {
		id = fmt.Sprintf("%s-%d", base, suffix)
	}
	return id, "./" + id + ".md"
}

func triggerSignalsFromLearning(entry map[string]any) []string {
	signals := []string{stringFromAny(entry["learning_type"]), stringFromAny(entry["signal_strength"])}
	for _, key := range []string{"trigger_signals", "false_starts", "rejected_paths"} {
		signals = append(signals, anyStringSlice(entry[key])...)
	}
	for _, key := range []string{"decisive_signal", "root_cause_family"} {
		if value := stringFromAny(entry[key]); value != "" {
			signals = append(signals, value)
		}
	}
	return uniqueSortedTrimmed(signals)
}

func findLearningEntry(entries []map[string]any, key string) map[string]any {
	for _, entry := range entries {
		if entry["recurrence_key"] == key {
			return cloneLearningMap(entry)
		}
	}
	return nil
}

func removeLearningByRecurrence(entries []map[string]any, key string) []map[string]any {
	filtered := []map[string]any{}
	for _, entry := range entries {
		if entry["recurrence_key"] != key {
			filtered = append(filtered, entry)
		}
	}
	return filtered
}

func learningEntryRelevantToCommand(entry map[string]any, command string) bool {
	return learningContainsString(anyStringSlice(entry["applies_to"]), command)
}

func learningHighestSignal(entry map[string]any) bool {
	return stringFromAny(entry["signal_strength"]) == "high" || intFromAny(entry["occurrence_count"]) >= 2
}

func learningNow() string {
	return time.Now().UTC().Truncate(time.Second).Format(time.RFC3339)
}

func buildLearningID() string {
	var b [4]byte
	_, _ = rand.Read(b[:])
	return time.Now().UTC().Format("LRN-20060102-150405-") + hex.EncodeToString(b[:])
}

func slugifyLearning(value string) string {
	re := regexp.MustCompile(`[^a-z0-9]+`)
	slug := strings.Trim(re.ReplaceAllString(strings.ToLower(value), "-"), "-")
	if slug == "" {
		return "learning"
	}
	return slug
}

func cleanLearningPlaceholder(value string) string {
	lower := strings.ToLower(strings.TrimSpace(value))
	if lower == "none" || lower == "n/a" || lower == "not-applicable" || strings.HasPrefix(lower, "[") {
		return ""
	}
	return strings.TrimSpace(value)
}

func formatLearningEvidence(title string, items [][2]string) string {
	lines := []string{title}
	for _, item := range items {
		if strings.TrimSpace(item[1]) != "" {
			lines = append(lines, "- "+item[0]+": "+item[1])
		}
	}
	return strings.Join(lines, "\n")
}

func learningSnapshotValue(value any) any {
	return value
}

func learningRulesTemplateText() string {
	return "# Project Rules\n\nShared defaults that later `sp-xxx` workflows should follow across specification,\nplanning, implementation, debugging, and quick-task execution.\n\nPromote only stable project rules through `specify-runtime learning promote --target rule`.\nKeep one-off observations as runtime-managed candidates until recurrence or explicit\nconfirmation proves they belong in this shared rule layer.\n\n---\n"
}

func learningConfirmedTemplateText() string {
	return "# Confirmed Project Learning\n\nRuntime-maintained confirmed Learning behind `specify-runtime learning start`, `list`,\nand `show`. Agents should use those runtime surfaces instead of parsing this file.\n\n---\n"
}

func learningIndexTemplateText() string {
	return "# Project Learning Index\n\nRuntime-maintained compact index behind `specify-runtime learning start` and\n`specify-runtime learning list`. Agents should use those runtime surfaces and expand one\nselected record with `specify-runtime learning show`; do not parse this file directly\nduring normal workflow execution.\n\n---\n\n" + learningMachineBegin + "\n[]\n" + learningMachineEnd + "\n\n## Managed Entries\n\n_No learning index entries recorded yet._\n"
}

func learningCandidatesTemplateText() string {
	return "# Candidate Learnings\n\nPassive candidate learnings captured from `sp-xxx` workflows.\n\n---\n"
}

func learningReviewTemplateText() string {
	return "# Learning Review\n\nPending recurrence, confirmation, and promotion notes for passive project learning.\n\n---\n"
}

func stringsToAny(values []string) []any {
	result := make([]any, len(values))
	for i, value := range values {
		result[i] = value
	}
	return result
}

func mapsToAnyLearning(values []map[string]any) []any {
	result := make([]any, len(values))
	for i, value := range values {
		result[i] = value
	}
	return result
}

func facetsToAny(facets map[string][]string) map[string]any {
	result := map[string]any{}
	for key, values := range facets {
		result[key] = stringsToAny(values)
	}
	return result
}

func anyFacets(value any) map[string][]string {
	result := map[string][]string{}
	for key, values := range mapStringAny(value) {
		result[key] = anyStringSlice(values)
	}
	return result
}

func mergeLearningFacets(left, right map[string][]string) map[string][]string {
	merged := map[string][]string{}
	for _, key := range learningFacetKeys {
		merged[key] = uniqueSortedTrimmed(append(left[key], right[key]...))
		if len(merged[key]) == 0 {
			delete(merged, key)
		}
	}
	return merged
}

func anyStringSlice(value any) []string {
	switch typed := value.(type) {
	case []any:
		result := []string{}
		for _, item := range typed {
			if text := strings.TrimSpace(stringFromAny(item)); text != "" {
				result = append(result, text)
			}
		}
		return result
	case []string:
		return uniqueSortedTrimmed(typed)
	case string:
		if strings.TrimSpace(typed) == "" {
			return nil
		}
		return []string{strings.TrimSpace(typed)}
	default:
		return nil
	}
}

func mapStringAny(value any) map[string]any {
	if typed, ok := value.(map[string]any); ok {
		return typed
	}
	return map[string]any{}
}

func entryFieldList(entry map[string]any, key string) []any {
	if entry == nil {
		return []any{}
	}
	return stringsToAny(anyStringSlice(entry[key]))
}

func entryString(entry map[string]any, key string) string {
	if entry == nil {
		return ""
	}
	return stringFromAny(entry[key])
}

func entryNumber(entry map[string]any, key string) float64 {
	if entry == nil {
		return 0
	}
	return float64(intFromAny(entry[key]))
}

func stringFromAny(value any) string {
	switch typed := value.(type) {
	case string:
		return typed
	case nil:
		return ""
	default:
		return fmt.Sprint(typed)
	}
}

func intFromAny(value any) int {
	switch typed := value.(type) {
	case int:
		return typed
	case float64:
		return int(typed)
	case json.Number:
		i, _ := strconv.Atoi(typed.String())
		return i
	case string:
		i, _ := strconv.Atoi(strings.TrimSpace(typed))
		return i
	default:
		return 0
	}
}

func firstString(values ...string) string {
	for _, value := range values {
		if strings.TrimSpace(value) != "" {
			return strings.TrimSpace(value)
		}
	}
	return ""
}

func firstLine(value string) string {
	lines := strings.Split(strings.TrimSpace(value), "\n")
	if len(lines) == 0 {
		return ""
	}
	return strings.TrimSpace(lines[0])
}

func uniqueSortedTrimmed(values []string) []string {
	seen := map[string]string{}
	for _, value := range values {
		trimmed := strings.Join(strings.Fields(strings.TrimSpace(value)), " ")
		if trimmed != "" {
			seen[strings.ToLower(trimmed)] = trimmed
		}
	}
	keys := []string{}
	for key := range seen {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	result := []string{}
	for _, key := range keys {
		result = append(result, seen[key])
	}
	return result
}

func learningContainsString(values []string, value string) bool {
	for _, item := range values {
		if item == value {
			return true
		}
	}
	return false
}

func signalRank(signal string) int {
	switch signal {
	case "high":
		return 0
	case "medium":
		return 1
	default:
		return 2
	}
}

func strongestLearningSignal(left, right string) string {
	if signalRank(left) < signalRank(right) {
		return left
	}
	return right
}

func cloneLearningMap(value map[string]any) map[string]any {
	raw, _ := json.Marshal(value)
	var result map[string]any
	_ = json.Unmarshal(raw, &result)
	return result
}

func typeName(err error) string {
	return fmt.Sprintf("%T", err)
}

func maxInt(left, right int) int {
	if left > right {
		return left
	}
	return right
}

func minInt(left, right int) int {
	if left < right {
		return left
	}
	return right
}

func truncateString(value string, max int) string {
	if len(value) <= max {
		return value
	}
	return strings.TrimRight(value[:max], "-")
}

func insideDir(root, path string) bool {
	rootAbs, err := filepath.Abs(root)
	if err != nil {
		return false
	}
	pathAbs, err := filepath.Abs(path)
	if err != nil {
		return false
	}
	rel, err := filepath.Rel(rootAbs, pathAbs)
	return err == nil && rel != ".." && !strings.HasPrefix(rel, ".."+string(filepath.Separator))
}

func bulletsOrEmpty(values []string, empty string) string {
	if len(values) == 0 {
		return empty
	}
	lines := []string{}
	for _, value := range values {
		lines = append(lines, "- "+value)
	}
	return strings.Join(lines, "\n")
}
