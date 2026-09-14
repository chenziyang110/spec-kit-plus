package main

// compactQuickExecutionData is an opt-in presentation projection. It never
// mutates canonical state or removes dispatch authority, blockers, worker proof,
// the current packet, or the complete ready/blocked/active item sets.
//
// The full confirmation and pulse are duplicate context on a hot execution
// path. Keep their source pointer and exact decision binding instead. Consumers
// needing full context must use the existing read-only item-status response.
func compactQuickExecutionData(data map[string]any, confirmationRef, state, digest string) map[string]any {
	if _, ok := data["confirmation"]; !ok || confirmationRef == "" || state == "" || digest == "" {
		// Do not discard context when a trustworthy replacement is unavailable.
		return data
	}
	out := make(map[string]any, len(data)+2)
	for key, value := range data {
		if key != "confirmation" && key != "pulse" {
			out[key] = value
		}
	}
	out["response_schema"] = "quick-execution-compact-v1"
	out["confirmation_ref"] = confirmationRef
	out["confirmation_state"] = state
	out["confirmation_digest"] = digest
	return out
}
