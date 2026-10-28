package main

import (
	"encoding/json"
	"fmt"
	"path/filepath"
	"strings"
)

// Learning registers its exact planned files with the existing Do Work before
// creating a lock, a seed, an index, or a detail. No directory-wide exemption is
// given to arbitrary session callers, and the regular Learning lock still owns
// recurrence merges and candidate assessment.
func (service learningService) registerDoLearningFiles(paths []string) error {
	if service.doSessionID == "" {
		return nil
	}
	root, err := filepath.Abs(service.projectRoot)
	if err != nil {
		return err
	}
	refs := make([]string, 0, len(paths))
	for _, path := range paths {
		absolute, err := filepath.Abs(path)
		if err != nil {
			return err
		}
		rel, err := filepath.Rel(root, absolute)
		if err != nil || rel == ".." || strings.HasPrefix(rel, ".."+string(filepath.Separator)) {
			return fmt.Errorf("learning metadata path escapes the Do project")
		}
		refs = append(refs, filepath.ToSlash(rel))
	}
	if service.doWriteLockHeld {
		return doRegisterOwnerMetadataWritesLocked(service.projectRoot, service.doSessionID, "learning", refs)
	}
	return doRegisterLearningWrites(service.projectRoot, service.doSessionID, refs)
}

// Do's typed session is the evidence source. A normal successful operation
// belongs in its playbook usage history, not in a new generic lesson. Only an
// observed failed/interrupted attempt followed by currently valid recovery can
// produce an automatic recovery suggestion. More specific lessons use capture.
func (service learningService) suggestDoAutoCapture(id string) (string, []learningSuggestion, error) {
	session, _, err := loadDoSession(service.projectRoot, id)
	if err != nil {
		return "", nil, err
	}
	source := filepath.Join(service.projectRoot, filepath.FromSlash(doSessionRef(id)))
	validation := doValidate(service.projectRoot, session, true)
	return source, doLearningSuggestions(session, validation), nil
}

func doLearningSuggestions(session DoSession, validation DoValidation) []learningSuggestion {
	suggestions := []learningSuggestion{}
	if validation.Status != "passed" {
		return suggestions
	}
	hints := map[string]map[string]any{}
	for _, hint := range doVerifiedRecoveryHints(session, validation) {
		hints[fmt.Sprint(hint["failed_attempt"])+":"+fmt.Sprint(hint["verified_attempt"])] = hint
	}
	failed := map[string]DoAttempt{}
	latest := map[string]DoAttempt{}
	order := []string{}
	for _, attempt := range session.Attempts {
		key := attempt.Kind + ":" + attempt.TargetID
		if _, exists := latest[key]; !exists {
			order = append(order, key)
		}
		latest[key] = attempt
		if attempt.Status == "failed" || attempt.Status == "interrupted" || attempt.Status == "unknown" || attempt.TimedOut || attempt.Cancelled || attempt.Recovery != nil {
			failed[key] = attempt
		}
	}
	for _, key := range order {
		before, exists := failed[key]
		after := latest[key]
		if !exists || after.Status != "passed" || before.ID == after.ID || after.EvidenceOrigin != "agent_tool_observation" || after.ToolCallID == "" || !doAttemptInCurrentDefinition(session, after) {
			continue
		}
		definition := session.Definition
		identity := strings.Join([]string{definition.Operation, definition.Target, definition.Owner, definition.Variant, key}, "|")
		hint := hints[before.ID+":"+after.ID]
		if hint != nil {
			identity += "|" + fmt.Sprint(hint["failure_signature"])
		}
		pairs := [][2]string{
			{"session", doSessionRef(session.ID)}, {"operation", definition.Operation}, {"target", definition.Target},
			{"failed_attempt", before.ID}, {"verified_attempt", after.ID},
			{"verified_definition_epoch", fmt.Sprint(doCurrentDefinitionEpoch(session))},
			{"failed_summary", before.Summary}, {"recovery_summary", after.Summary},
			{"validation", validation.EvidenceDigest}, {"evidence_origin", "agent_tool_observation"},
		}
		if session.MethodBinding != nil {
			pairs = append(pairs, [2]string{"method", session.MethodBinding.ID})
		}
		if before.Recovery != nil {
			pairs = append(pairs, [2]string{"recovery_evidence", before.Recovery.EvidenceRef})
		}
		if hint != nil {
			for _, field := range []string{"failure_signature", "failure_discriminator", "observed_delta", "preflight_candidates", "prevention_status"} {
				value, _ := json.Marshal(hint[field])
				pairs = append(pairs, [2]string{field, string(value)})
			}
		}
		suggestions = append(suggestions, learningSuggestion{
			learningType: "recovery_path", signalStrength: "medium",
			summary:           "Verify recovery for " + definition.Operation + " on " + definition.Target + " before reusing the method",
			evidence:          formatLearningEvidence("Observed failed and recovered native operation attempts", pairs),
			recurrenceKey:     "do.recovered-operation." + safeSemanticLearningDigest(identity),
			appliesTo:         []string{"sp-do", "sp-quick", "sp-implement", "sp-debug", "sp-e2e"},
			problem:           "This operation needed recovery after an observed failed or interrupted attempt; its first result was insufficient.",
			recommendedAction: "Match the observed failure discriminator and current environment before reusing the recovery difference. Inspect the bound failed/verified actions and candidate preflights; their observed success does not prove prevention or a root cause. Freeze and execute any selected preflight in the current Do definition, rerun required checks, and publish it only through verified playbook update.",
			triggerSignals:    []string{"same observed failure discriminator", "native attempt interrupted", definition.Operation, definition.Target},
			successCriteria:   []string{"all frozen required steps and checks validate against the current sources", "recovery evidence remains linked to the same operation"},
			avoid:             []string{"reusing the earlier failed result", "retrying an unknown process without inspecting its effects", "promoting an untested recovery into the current playbook"},
			facets:            map[string][]string{"operation_owners": {definition.Owner}, "components": {definition.Target}, "entrypoints": {definition.Operation}, "outcomes": {"verified-recovery"}},
		})
		if len(suggestions) == 6 {
			break
		}
	}
	return suggestions
}
