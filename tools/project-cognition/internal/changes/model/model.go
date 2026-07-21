package model

import (
	"fmt"
	"strings"
)

type Operation string

const (
	OperationAdd    Operation = "add"
	OperationModify Operation = "modify"
	OperationDelete Operation = "delete"
	OperationRename Operation = "rename"
)

type Disposition string

const (
	DispositionAdoptable            Disposition = "adoptable"
	DispositionReviewOnly           Disposition = "review_only"
	DispositionIgnored              Disposition = "ignored"
	DispositionBlockingKnownUnknown Disposition = "blocking_known_unknown"
)

type PathChange struct {
	Path         string       `json:"path"`
	OldPath      string       `json:"old_path,omitempty"`
	Operation    Operation    `json:"operation"`
	NodeID       string       `json:"node_id,omitempty"`
	Disposition  *Disposition `json:"disposition,omitempty"`
	EvidenceRefs []string     `json:"evidence_refs,omitempty"`
}

type PathDispositionDecision struct {
	Path             string       `json:"path"`
	AgentDisposition *Disposition `json:"agent_disposition"`
}

// ResolvePathDispositions binds planner-visible agent decisions to the typed
// path changes that the mutation runtime validates and persists. Decisions are
// never silently ignored: unknown paths, duplicates, missing values, and
// conflicts with an already typed disposition fail closed.
func ResolvePathDispositions(values []PathChange, decisions []PathDispositionDecision) ([]PathChange, error) {
	resolved := append([]PathChange{}, values...)
	byPath := make(map[string]Disposition, len(decisions))
	for _, decision := range decisions {
		path := strings.TrimSpace(decision.Path)
		if path == "" {
			return nil, fmt.Errorf("path disposition decision requires path")
		}
		if decision.AgentDisposition == nil {
			return nil, fmt.Errorf("path disposition decision %s requires agent_disposition", path)
		}
		if !decision.AgentDisposition.Valid() {
			return nil, fmt.Errorf("path disposition decision %s has unsupported agent_disposition %q", path, *decision.AgentDisposition)
		}
		if _, exists := byPath[path]; exists {
			return nil, fmt.Errorf("path disposition decision %s is duplicated", path)
		}
		byPath[path] = *decision.AgentDisposition
	}
	matched := make(map[string]bool, len(byPath))
	for index := range resolved {
		path := strings.TrimSpace(resolved[index].Path)
		disposition, exists := byPath[path]
		if !exists {
			continue
		}
		matched[path] = true
		if resolved[index].Disposition != nil && *resolved[index].Disposition != disposition {
			return nil, fmt.Errorf("path change %s disposition %q conflicts with agent_disposition %q", path, *resolved[index].Disposition, disposition)
		}
		resolved[index].Disposition = &disposition
	}
	for path := range byPath {
		if !matched[path] {
			return nil, fmt.Errorf("path disposition decision %s has no matching path change", path)
		}
	}
	return resolved, nil
}

func (operation Operation) Valid() bool {
	switch operation {
	case OperationAdd, OperationModify, OperationDelete, OperationRename:
		return true
	default:
		return false
	}
}

func (disposition Disposition) Valid() bool {
	switch disposition {
	case DispositionAdoptable, DispositionReviewOnly, DispositionIgnored, DispositionBlockingKnownUnknown:
		return true
	default:
		return false
	}
}

func (change PathChange) Validate() error {
	if strings.TrimSpace(change.Path) == "" {
		return fmt.Errorf("path change path is required")
	}
	if !change.Operation.Valid() {
		return fmt.Errorf("path change %s has unsupported operation %q", change.Path, change.Operation)
	}
	if change.Operation == OperationRename && strings.TrimSpace(change.OldPath) == "" {
		return fmt.Errorf("path change %s rename requires old_path", change.Path)
	}
	if change.Disposition == nil {
		return fmt.Errorf("path change %s requires disposition", change.Path)
	}
	if !change.Disposition.Valid() {
		return fmt.Errorf("path change %s has unsupported disposition %q", change.Path, *change.Disposition)
	}
	return nil
}

func (change PathChange) MutatesGraph() bool {
	return change.Disposition != nil && *change.Disposition == DispositionAdoptable
}
