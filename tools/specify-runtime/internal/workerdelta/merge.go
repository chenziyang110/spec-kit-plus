package workerdelta

import (
	"fmt"
	"sort"
)

type Event struct {
	SourceRef       string         `json:"source_ref"`
	SourceSHA256    string         `json:"source_sha256"`
	Sequence        int            `json:"sequence"`
	TaskID          string         `json:"task_id"`
	AttemptID       string         `json:"attempt_id"`
	ResultSHA256    string         `json:"result_sha256"`
	Status          string         `json:"status"`
	Accepted        bool           `json:"accepted"`
	Delta           map[string]any `json:"cognition_delta"`
	CandidateInput  map[string]any `json:"candidate_input,omitempty"`
	RetainedPaths   []string       `json:"retained_paths"`
	RejectionReason string         `json:"rejection_reason,omitempty"`
	Unaccounted     bool           `json:"unaccounted_changes,omitempty"`
}

type Conflict struct {
	Kind    string   `json:"kind"`
	Key     string   `json:"key"`
	Sources []string `json:"sources"`
}

type Merge struct {
	Events          []Event          `json:"events"`
	ChangedPaths    []string         `json:"changed_paths"`
	AcceptedDeltas  []map[string]any `json:"accepted_deltas"`
	CandidateDeltas []map[string]any `json:"candidate_deltas"`
	Conflicts       []Conflict       `json:"conflicts"`
	KnownUnknowns   []string         `json:"known_unknowns"`
}

func MergeEvents(events []Event) Merge {
	result := Merge{Events: events, ChangedPaths: []string{}, AcceptedDeltas: []map[string]any{}, CandidateDeltas: []map[string]any{}, Conflicts: []Conflict{}, KnownUnknowns: []string{}}
	paths := map[string]bool{}
	pathSources, claimSources := map[string][]string{}, map[string][]string{}
	for _, event := range events {
		id := fmt.Sprintf("%s#submission-%d:%s", event.SourceRef, event.Sequence, event.AttemptID)
		for _, p := range event.RetainedPaths {
			paths[p] = true
			pathSources[p] = append(pathSources[p], id)
		}
		for _, p := range Accounting(map[string]any{"cognition_delta": event.Delta}) {
			paths[p] = true
		}
		if event.Accepted {
			result.AcceptedDeltas = append(result.AcceptedDeltas, Clone(event.Delta))
		} else {
			result.CandidateDeltas = append(result.CandidateDeltas, Clone(event.Delta))
		}
		for _, field := range []string{"invalidated_claim_refs", "evidence_refs"} {
			rows, _ := event.Delta[field].([]any)
			for _, row := range rows {
				key := ""
				if text, ok := row.(string); ok {
					if field == "invalidated_claim_refs" {
						key = text
					}
				} else if object, ok := row.(map[string]any); ok {
					if ref, ok := object["claim_ref"].(string); ok {
						key = ref
					}
					if ref, ok := object["claim_id"].(string); ok {
						key = ref
					}
				}
				if key != "" {
					claimSources[key] = append(claimSources[key], id)
				}
			}
		}
		if event.Unaccounted {
			result.KnownUnknowns = append(result.KnownUnknowns, id+": rejected input has unaccounted retained changes")
		}
	}
	for p := range paths {
		result.ChangedPaths = append(result.ChangedPaths, p)
	}
	sort.Strings(result.ChangedPaths)
	for _, entry := range []struct {
		kind   string
		values map[string][]string
	}{{"overlapping_path_versions", pathSources}, {"shared_claim_versions", claimSources}} {
		keys := []string{}
		for key := range entry.values {
			keys = append(keys, key)
		}
		sort.Strings(keys)
		for _, key := range keys {
			sources := entry.values[key]
			if len(sources) > 1 {
				result.Conflicts = append(result.Conflicts, Conflict{Kind: entry.kind, Key: key, Sources: sources})
			}
		}
	}
	return result
}
