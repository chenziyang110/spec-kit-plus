package main

import (
	"fmt"
	"sort"
	"strings"
)

type WorkflowRecoveryAttempt struct {
	Action string `json:"action"`
	Result string `json:"result"`
}

type WorkflowBlockRequest struct {
	FeatureDir          string                    `json:"feature_dir"`
	FeatureID           string                    `json:"-"`
	ExpectedRevision    int                       `json:"expected_revision"`
	Category            string                    `json:"category"`
	Owner               string                    `json:"owner"`
	Cause               string                    `json:"cause"`
	Evidence            []string                  `json:"evidence"`
	AttemptedRecovery   []WorkflowRecoveryAttempt `json:"attempted_recovery"`
	AffectedScope       []string                  `json:"affected_scope"`
	ExactNextAction     string                    `json:"exact_next_action"`
	UnblockCriteria     string                    `json:"unblock_criteria"`
	HumanAction         map[string]any            `json:"human_action,omitempty"`
	HumanActionRequired *bool                     `json:"human_action_required,omitempty"`
}

var workflowBlockerCategories = map[string]bool{
	"workflow-validation":          true,
	"artifact-or-state":            true,
	"technical-failure":            true,
	"dependency-or-service":        true,
	"delegation":                   true,
	"project-cognition":            true,
	"credentials-or-permission":    true,
	"external-system":              true,
	"external-write-authorization": true,
	"human-decision":               true,
	"human-review":                 true,
	"timeout":                      true,
	"conflict-or-drift":            true,
}

var workflowBlockerOwners = map[string]bool{
	"agent":           true,
	"user":            true,
	"maintainer":      true,
	"external-system": true,
}

func (service *WorkflowService) Block(request WorkflowBlockRequest) Envelope {
	feature, err := service.resolveFeature(request.FeatureDir, request.FeatureID)
	if err != nil {
		return workflowInvalid("workflow feature directory is invalid", "invalid-feature-dir", err)
	}
	category := strings.ToLower(strings.TrimSpace(request.Category))
	if !workflowBlockerCategories[category] {
		return workflowInvalid("workflow blocker category is invalid", "invalid-blocker-category", fmt.Errorf("unsupported blocker category %q", request.Category))
	}
	owner := strings.ToLower(strings.TrimSpace(request.Owner))
	if !workflowBlockerOwners[owner] {
		return workflowInvalid("workflow blocker owner is invalid", "invalid-blocker-owner", fmt.Errorf("unsupported blocker owner %q", request.Owner))
	}
	cause := strings.TrimSpace(request.Cause)
	if cause == "" {
		return workflowInvalid("workflow blocker cause is invalid", "invalid-blocker-cause", fmt.Errorf("cause is required"))
	}
	evidence, err := requiredWorkflowStrings(request.Evidence, "evidence")
	if err != nil {
		return workflowInvalid("workflow blocker evidence is invalid", "invalid-blocker-evidence", err)
	}
	scope, err := requiredWorkflowStrings(request.AffectedScope, "affected-scope")
	if err != nil {
		return workflowInvalid("workflow blocker scope is invalid", "invalid-blocker-scope", err)
	}
	nextAction := strings.TrimSpace(request.ExactNextAction)
	if nextAction == "" {
		return workflowInvalid("workflow blocker next action is invalid", "invalid-blocker-next-action", fmt.Errorf("exact_next_action is required"))
	}
	unblockCriteria := strings.TrimSpace(request.UnblockCriteria)
	if unblockCriteria == "" {
		return workflowInvalid("workflow blocker criteria are invalid", "invalid-blocker-criteria", fmt.Errorf("unblock_criteria is required"))
	}
	attempts := make([]any, 0, len(request.AttemptedRecovery))
	for index, attempt := range request.AttemptedRecovery {
		action := strings.TrimSpace(attempt.Action)
		result := strings.TrimSpace(attempt.Result)
		if action == "" || result == "" {
			return workflowInvalid("workflow recovery attempt is invalid", "invalid-blocker-recovery", fmt.Errorf("attempted_recovery[%d] requires action and result", index))
		}
		attempts = append(attempts, map[string]any{"action": action, "result": result})
	}
	humanRequired := owner == "user" || owner == "maintainer"
	if request.HumanAction != nil {
		humanRequired = true
	}
	if request.HumanActionRequired != nil {
		if (owner == "user" || owner == "maintainer" || request.HumanAction != nil) && !*request.HumanActionRequired {
			return workflowInvalid("workflow human action flag is invalid", "invalid-human-action", fmt.Errorf("user or maintainer owner requires human_action_required=true"))
		}
		humanRequired = *request.HumanActionRequired
	}

	release, env, ok := service.acquireWorkflowLock(feature)
	if !ok {
		return env
	}
	defer release()
	state, err := service.readState(feature)
	if err != nil {
		return service.stateReadFailure(feature, err)
	}
	if request.ExpectedRevision != state.Revision {
		return workflowRevisionConflictWithState(feature, request.ExpectedRevision, state)
	}
	if isTerminalWorkflowState(state) {
		return workflowStateBlocked(feature, state, "completed workflow cannot be blocked", "workflow-already-completed")
	}
	if state.Status == "blocked" {
		return workflowStateBlocked(feature, state, "an unresolved workflow blocker cannot be replaced", "blocker-already-recorded")
	}

	resumeArgv := workflowShowArgv(feature)
	humanGuide := request.HumanAction
	if humanRequired && humanGuide == nil {
		humanGuide = noviceWorkflowHumanAction(owner, evidence, nextAction, unblockCriteria, resumeArgv)
	}
	if humanGuide != nil {
		if err := validateWorkflowHumanAction(humanGuide); err != nil {
			return workflowInvalid("workflow human action guide is invalid", "invalid-human-action", err)
		}
	}
	var persistedHumanGuide any
	if humanGuide != nil {
		persistedHumanGuide = humanGuide
	}
	blockedRevision := state.Revision + 1
	blocker := map[string]any{
		"version":               1,
		"blocker_id":            fmt.Sprintf("workflow-%s-%s-r%d", workflowSlug(state.Stage), workflowSlug(category), blockedRevision),
		"workflow":              state.Stage,
		"stage":                 state.Stage,
		"category":              category,
		"owner":                 owner,
		"summary":               cause,
		"details":               cause,
		"evidence":              stringValuesAsAny(evidence),
		"attempted_recovery":    attempts,
		"exact_next_action":     nextAction,
		"unblock_criteria":      unblockCriteria,
		"affected_scope":        stringValuesAsAny(scope),
		"can_continue":          false,
		"human_action_required": humanRequired,
		"human_action_guide":    persistedHumanGuide,
		"resume": map[string]any{
			"instruction": "Execute the structured resume.argv array exactly; do not reconstruct a shell command.",
			"command":     "use resume.argv",
			"argv":        stringValuesAsAny(resumeArgv),
		},
	}
	state.Revision = blockedRevision
	state.Status = "blocked"
	state.Summary = cause
	state.Blocker = blocker
	if err := service.writeState(feature, state); err != nil {
		return workflowError("failed to write workflow blocker", err)
	}
	env = NewEnvelope("blocked", cause)
	addWorkflowStateData(&env, state)
	env.Data["resolution_action"] = workflowResolutionAction(feature, state.Revision)
	env.Blockers = append(env.Blockers, cloneMap(blocker))
	env.ShowArgv = workflowShowArgv(feature)
	return env
}

func noviceWorkflowHumanAction(owner string, evidence []string, nextAction, unblockCriteria string, resumeArgv []string) map[string]any {
	return map[string]any{
		"goal":      nextAction,
		"why_human": fmt.Sprintf("This boundary is owned by %s; the agent cannot safely exercise that authority.", owner),
		"prerequisites": stringValuesAsAny(append([]string{
			"Access to the exact repository, environment, artifact, or decision named in the evidence.",
			"The authority required for the requested action.",
		}, evidence...)),
		"safety_notes": stringValuesAsAny([]string{
			"Do not share tokens, passwords, cookies, private keys, or unredacted private logs.",
			"Do not broaden the action to another repository, branch, environment, job, or setting.",
			"Stop and return the ambiguity when the target cannot be matched exactly.",
		}),
		"steps": []any{
			map[string]any{
				"order": 1, "title": "Confirm the exact target",
				"action":  "Match the named repository, environment, artifact, setting, or decision to the blocker evidence before changing anything.",
				"command": nil, "expected_result": "Exactly one target matches the sanitized evidence.",
				"if_failed": "Make no change; return the conflicting target names or missing identifier.",
			},
			map[string]any{
				"order": 2, "title": "Perform only the requested action", "action": nextAction,
				"command": nil, "expected_result": unblockCriteria,
				"if_failed": "Do not expand scope; record the terminal status and smallest sanitized error evidence.",
			},
			map[string]any{
				"order": 3, "title": "Verify independently",
				"action":  "Refresh or rerun a read-only check against the same exact target.",
				"command": nil, "expected_result": unblockCriteria,
				"if_failed": "Return the observed mismatch instead of claiming resolution.",
			},
		},
		"verification": stringValuesAsAny([]string{unblockCriteria}),
		"evidence_to_return": stringValuesAsAny([]string{
			"The exact target identifier and terminal result.",
			"Sanitized evidence that independently proves the result.",
		}),
		"resume_instruction": "Return the evidence, then execute this blocker's structured resume.argv array exactly.",
	}
}

func validateWorkflowHumanAction(guide map[string]any) error {
	required := []string{"goal", "why_human", "prerequisites", "safety_notes", "steps", "verification", "evidence_to_return", "resume_instruction"}
	allowed := map[string]bool{}
	for _, key := range required {
		allowed[key] = true
	}
	for key := range guide {
		if !allowed[key] {
			return fmt.Errorf("human_action contains unknown field %q", key)
		}
	}
	for _, key := range []string{"goal", "why_human", "resume_instruction"} {
		value, ok := guide[key].(string)
		if !ok || strings.TrimSpace(value) == "" {
			return fmt.Errorf("human_action.%s is required", key)
		}
	}
	for _, key := range []string{"prerequisites", "safety_notes", "verification", "evidence_to_return"} {
		values, ok := guide[key].([]any)
		if !ok || len(values) == 0 || !nonEmptyStringValues(values) {
			return fmt.Errorf("human_action.%s must be a non-empty array", key)
		}
	}
	steps, ok := guide["steps"].([]any)
	if !ok || len(steps) == 0 {
		return fmt.Errorf("human_action.steps must be a non-empty array")
	}
	for index, rawStep := range steps {
		step, ok := rawStep.(map[string]any)
		if !ok {
			return fmt.Errorf("human_action.steps[%d] must be an object", index)
		}
		allowedStep := map[string]bool{"order": true, "title": true, "action": true, "command": true, "expected_result": true, "if_failed": true}
		for key := range step {
			if !allowedStep[key] {
				return fmt.Errorf("human_action.steps[%d] contains unknown field %q", index, key)
			}
		}
		order, ok := jsonInteger(step["order"])
		if !ok || order < 1 {
			return fmt.Errorf("human_action.steps[%d].order must be a positive integer", index)
		}
		for _, key := range []string{"title", "action", "expected_result", "if_failed"} {
			value, ok := step[key].(string)
			if !ok || strings.TrimSpace(value) == "" {
				return fmt.Errorf("human_action.steps[%d].%s is required", index, key)
			}
		}
		if command, exists := step["command"]; exists && command != nil {
			if _, ok := command.(string); !ok {
				return fmt.Errorf("human_action.steps[%d].command must be a string or null", index)
			}
		}
	}
	return nil
}

func workflowSlug(value string) string {
	var result strings.Builder
	lastDash := false
	for _, char := range strings.ToLower(value) {
		if (char >= 'a' && char <= 'z') || (char >= '0' && char <= '9') {
			result.WriteRune(char)
			lastDash = false
		} else if !lastDash && result.Len() > 0 {
			result.WriteByte('-')
			lastDash = true
		}
	}
	return strings.Trim(result.String(), "-")
}

func stringValuesAsAny(values []string) []any {
	result := make([]any, 0, len(values))
	for _, value := range values {
		result = append(result, value)
	}
	return result
}

func sortedWorkflowBlockerCategories() []string {
	values := make([]string, 0, len(workflowBlockerCategories))
	for value := range workflowBlockerCategories {
		values = append(values, value)
	}
	sort.Strings(values)
	return values
}
