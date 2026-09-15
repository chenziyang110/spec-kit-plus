package main

import "strings"

// compactQuickExecutionData is an opt-in presentation projection. It never
// mutates canonical state or removes dispatch authority, blockers, worker proof,
// the current packet, or the complete ready/blocked/active item sets.
//
// The full confirmation and pulse are duplicate context on a hot execution
// path. Keep their source pointer and exact decision binding instead. Consumers
// needing full context must use the existing read-only item-status response.
func compactQuickExecutionData(data map[string]any, confirmationRef, state, digest string) map[string]any {
	if data["confirmation"] == nil || strings.TrimSpace(confirmationRef) == "" ||
		strings.TrimSpace(state) == "" || strings.TrimSpace(digest) == "" {
		// Do not discard context when a trustworthy replacement is unavailable.
		return data
	}
	bindings := map[string]string{
		"response_schema":     "quick-execution-compact-v1",
		"confirmation_ref":    confirmationRef,
		"confirmation_state":  state,
		"confirmation_digest": digest,
	}
	for key, expected := range bindings {
		if value, exists := data[key]; exists {
			if current, ok := value.(string); !ok || current != expected {
				// Presentation must not silently overwrite a future contract field.
				return data
			}
		}
	}
	out := make(map[string]any, len(data)+2)
	for key, value := range data {
		if key != "confirmation" && key != "pulse" {
			out[key] = value
		}
	}
	for key, value := range bindings {
		out[key] = value
	}
	return out
}
