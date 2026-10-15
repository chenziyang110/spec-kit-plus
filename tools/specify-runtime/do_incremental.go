package main

import (
	"fmt"
	"reflect"
)

// A retained result refers to its original observation. It never impersonates
// execution in the new epoch. The immutable epoch binds the whole attempt.
type DoRetainedAttempt struct {
	TargetID          string `json:"target_id"`
	AttemptID         string `json:"attempt_id"`
	AttemptDigest     string `json:"attempt_digest"`
	SourceFingerprint string `json:"source_fingerprint"`
	FromEpoch         int    `json:"from_epoch"`
}

func doActionDefinition(definition PlaybookDefinition, id string) any {
	definition = playbookNormalizeDefinition(definition)
	for _, step := range definition.Steps {
		if step.ID == id {
			return step
		}
	}
	for _, check := range definition.Checks {
		if check.ID == id {
			return check
		}
	}
	return nil
}

func doRetainedAttempt(session DoSession, attempt DoAttempt) bool {
	if len(session.DefinitionHistory) == 0 {
		return false
	}
	current := session.DefinitionHistory[len(session.DefinitionHistory)-1]
	for _, retained := range current.RetainedAttempts {
		if retained.TargetID == attempt.TargetID && retained.AttemptID == attempt.ID && retained.AttemptDigest == doDigest(attempt) && retained.SourceFingerprint == attempt.SourceFingerprint && retained.FromEpoch == attempt.DefinitionEpoch && retained.FromEpoch == current.Epoch-1 {
			previous := session.DefinitionHistory[retained.FromEpoch-1]
			return attempt.DefinitionDigest == previous.DefinitionDigest && reflect.DeepEqual(doActionDefinition(previous.Definition, attempt.TargetID), doActionDefinition(current.Definition, attempt.TargetID))
		}
	}
	return false
}

func doValidateRetainedBindings(session DoSession) error {
	for i, epoch := range session.DefinitionHistory {
		seen := map[string]bool{}
		for _, retained := range epoch.RetainedAttempts {
			if i == 0 || retained.FromEpoch != i || seen[retained.TargetID] || retained.SourceFingerprint != epoch.SourceFingerprint {
				return fmt.Errorf("invalid retained evidence epoch binding")
			}
			seen[retained.TargetID] = true
			found := false
			for _, attempt := range session.Attempts {
				if attempt.ID != retained.AttemptID {
					continue
				}
				found = attempt.TargetID == retained.TargetID && attempt.Status == "passed" && attempt.DefinitionEpoch == retained.FromEpoch && attempt.DefinitionDigest == session.DefinitionHistory[i-1].DefinitionDigest && doDigest(attempt) == retained.AttemptDigest && attempt.SourceFingerprint == retained.SourceFingerprint && reflect.DeepEqual(doActionDefinition(session.DefinitionHistory[i-1].Definition, attempt.TargetID), doActionDefinition(epoch.Definition, attempt.TargetID))
			}
			if !found {
				return fmt.Errorf("retained original observation is missing or changed")
			}
		}
	}
	return nil
}

func doIncrementalContract(previous, next PlaybookDefinition) error {
	required := map[string]bool{}
	var visit func(string)
	visit = func(id string) {
		if required[id] {
			return
		}
		required[id] = true
		switch action := doActionDefinition(previous, id).(type) {
		case PlaybookStep:
			for _, dependency := range action.DependsOn {
				visit(dependency)
			}
		case PlaybookCheck:
			for _, dependency := range action.DependsOn {
				visit(dependency)
			}
		}
	}
	for _, step := range previous.Steps {
		if step.Required {
			visit(step.ID)
		}
	}
	for _, check := range previous.Checks {
		if check.Required {
			visit(check.ID)
		}
	}
	for _, step := range previous.Steps {
		if !required[step.ID] {
			continue
		}
		value, ok := doActionDefinition(next, step.ID).(PlaybookStep)
		if !ok || (step.Required && !value.Required) {
			return fmt.Errorf("incremental replan cannot delete or weaken required steps")
		}
		for _, dependency := range step.DependsOn {
			if !doContainsDependency(value.DependsOn, dependency) {
				return fmt.Errorf("incremental replan cannot remove required prerequisite edges")
			}
		}
	}
	for _, check := range previous.Checks {
		if !required[check.ID] {
			continue
		}
		value, ok := doActionDefinition(next, check.ID).(PlaybookCheck)
		if !ok || (check.Required && !value.Required) || value.Kind != check.Kind || value.ResultPath != check.ResultPath || value.JSONPointer != check.JSONPointer || !reflect.DeepEqual(value.ExpectedJSON, check.ExpectedJSON) || value.MinCases != check.MinCases || value.Cwd != check.Cwd || doDigest(value.Argv) != doDigest(check.Argv) || value.ScriptRef != check.ScriptRef || !doNativeActionsEqual(value.NativeAction, check.NativeAction) {
			return fmt.Errorf("incremental replan must preserve every required outcome assertion")
		}
		for _, dependency := range check.DependsOn {
			if !doContainsDependency(value.DependsOn, dependency) {
				return fmt.Errorf("incremental replan cannot remove required check dependencies")
			}
		}
	}
	return nil
}

func doPlanRetained(root string, previous DoSession, definition PlaybookDefinition, fingerprint string) []DoRetainedAttempt {
	result := []DoRetainedAttempt{}
	latest := doLatestAttempts(previous)
	accepted := map[string]bool{}
	// Topological fixed point; unchanged dependencies must keep exact attempt IDs.
	for pass := 0; pass < len(latest)+1; pass++ {
		progress := false
		for id, attempt := range latest {
			if accepted[id] || !doAttemptInCurrentDefinition(previous, attempt) || attempt.Status != "passed" || attempt.NativeAction != nil || len(attempt.Results) == 0 || attempt.SourceFingerprint != fingerprint || !reflect.DeepEqual(doActionDefinition(previous.Definition, id), doActionDefinition(definition, id)) {
				continue
			}
			action, err := doFindAction(previous, attempt.Kind, id)
			if err != nil || len(action.sourceWrites) != 0 {
				continue
			}
			if step, ok := doActionDefinition(previous.Definition, id).(PlaybookStep); ok && step.SideEffect != "read" && step.SideEffect != "local_write" {
				continue
			}
			ready := true
			for _, dependency := range action.dependencies {
				if !accepted[dependency] {
					ready = false
				}
			}
			if !ready {
				continue
			}
			validation := DoValidation{}
			observations := []DoAttempt{}
			doValidateAttempt(root, previous, latest, id, attempt.Kind, fingerprint, &validation, &observations)
			if len(validation.Blockers) > 0 {
				continue
			}
			accepted[id] = true
			result = append(result, DoRetainedAttempt{TargetID: id, AttemptID: attempt.ID, AttemptDigest: doDigest(attempt), SourceFingerprint: fingerprint, FromEpoch: doCurrentDefinitionEpoch(previous)})
			progress = true
		}
		if !progress {
			break
		}
	}
	// Stable epoch serialization regardless of map order.
	for i := 0; i < len(result); i++ {
		for j := i + 1; j < len(result); j++ {
			if result[j].TargetID < result[i].TargetID {
				result[i], result[j] = result[j], result[i]
			}
		}
	}
	return result
}

func doContainsDependency(values []string, wanted string) bool {
	for _, value := range values {
		if value == wanted {
			return true
		}
	}
	return false
}

// A producer handoff is accepted only while its complete evidence closure is
// usable. Check before the dependent tool can run, not just during closeout.
func doDependencyReady(root string, session DoSession, latest map[string]DoAttempt, id, fingerprint string) error {
	kind := "step"
	if _, err := doFindAction(session, kind, id); err != nil {
		kind = "check"
	}
	validation := DoValidation{}
	accepted := []DoAttempt{}
	doValidateRequiredClosure(root, session, latest, id, kind, fingerprint, &validation, &accepted, map[string]bool{})
	if len(validation.Blockers) != 0 {
		return fmt.Errorf("dependency %s evidence must be refreshed: %v", id, validation.Blockers)
	}
	return nil
}
