package main

import (
	"encoding/json"
	"fmt"
	"strings"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/delta"
	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/update"
)

type preparedCloseoutInput struct {
	Missing      []string
	ChangedPaths []string
	DeltaDigest  string
}

func prepareCloseoutInput(paths rt.Paths, workflow, payloadJSON, deltaSession string, override []update.VerificationEvidence, commitRange ...string) (preparedCloseoutInput, error) {
	prepared := preparedCloseoutInput{Missing: []string{}, ChangedPaths: []string{}}
	if strings.TrimSpace(payloadJSON) != "" {
		payload, err := update.ParseUpdatePayload([]byte(payloadJSON), override)
		if err != nil {
			return prepared, err
		}
		if strings.TrimSpace(payload.Workflow) != "" {
			payloadWorkflow, err := normalizeMutationWorkflowID(payload.Workflow)
			if err != nil {
				return prepared, err
			}
			if payloadWorkflow != workflow {
				return prepared, fmt.Errorf("closeout apply workflow %s does not match payload workflow %s", workflow, payloadWorkflow)
			}
		}
		owned := normalizedCloseoutPaths(payload.Boundary.WorkflowOwnedPaths)
		if strings.TrimSpace(payload.Boundary.ScopeMode) != "explicit" {
			prepared.Missing = append(prepared.Missing, "boundary.scope_mode=explicit")
		}
		if len(owned) == 0 {
			prepared.Missing = append(prepared.Missing, "boundary.workflow_owned_paths")
		}
		changed := append([]string{}, payload.ChangedPaths...)
		changed = append(changed, payload.ScopePaths...)
		for _, change := range payload.PathChanges {
			changed = append(changed, change.Path, change.OldPath)
		}
		prepared.ChangedPaths = normalizedCloseoutPaths(changed)
		if len(prepared.ChangedPaths) == 0 {
			prepared.Missing = append(prepared.Missing, "changed_paths")
		}
		if len(owned) > 0 {
			ownedSet := closeoutPathSet(owned)
			for _, path := range prepared.ChangedPaths {
				if !ownedSet[path] {
					return prepared, fmt.Errorf("payload path %s is outside boundary.workflow_owned_paths", path)
				}
			}
		}
		if !closeoutHasPassingVerification(payload.Verification) {
			prepared.Missing = append(prepared.Missing, "verification[result=passed]")
		}
		prepared.Missing = sortedUniqueCloseoutStrings(prepared.Missing)
		return prepared, nil
	}
	if len(commitRange) > 0 {
		if err := update.ValidateCommitRange(paths, commitRange[0]); err != nil {
			return prepared, err
		}
	}
	bundle, err := delta.Load(paths.RuntimeDir, strings.TrimSpace(deltaSession))
	if err != nil {
		return prepared, err
	}
	if err := update.ValidateDeltaInput(bundle, override); err != nil {
		return prepared, err
	}
	prepared.DeltaDigest, err = delta.Digest(bundle)
	if err != nil {
		return prepared, err
	}
	if strings.TrimSpace(bundle.Session.OriginCommand) != "" {
		sessionWorkflow, err := normalizeMutationWorkflowID(bundle.Session.OriginCommand)
		if err != nil {
			return prepared, fmt.Errorf("invalid delta session origin_command: %w", err)
		}
		if sessionWorkflow != workflow {
			return prepared, fmt.Errorf("closeout apply workflow %s does not match delta workflow %s", workflow, sessionWorkflow)
		}
	}
	endpoints := []string{}
	verification := update.VerificationEvidenceList{}
	for _, event := range bundle.Events {
		prepared.ChangedPaths = append(prepared.ChangedPaths, event.ChangedPaths...)
		for _, change := range event.PathChanges {
			endpoints = append(endpoints, change.Path, change.OldPath)
		}
		for _, raw := range event.Verification {
			var evidence update.VerificationEvidence
			if json.Unmarshal([]byte(strings.TrimSpace(raw)), &evidence) == nil {
				verification = append(verification, evidence)
			}
		}
	}
	prepared.ChangedPaths = normalizedCloseoutPaths(prepared.ChangedPaths)
	if len(prepared.ChangedPaths) == 0 {
		prepared.Missing = append(prepared.Missing, "delta.workflow_owned_changed_paths")
	} else {
		declared := closeoutPathSet(prepared.ChangedPaths)
		for _, path := range normalizedCloseoutPaths(endpoints) {
			if !declared[path] {
				return prepared, fmt.Errorf("delta path change endpoint %s is outside declared workflow-owned changed paths", path)
			}
		}
	}
	if override != nil {
		verification = override
	}
	if !closeoutHasPassingVerification(verification) {
		prepared.Missing = append(prepared.Missing, "delta.verification[result=passed]")
	}
	prepared.Missing = sortedUniqueCloseoutStrings(prepared.Missing)
	return prepared, nil
}
