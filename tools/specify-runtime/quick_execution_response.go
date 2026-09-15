package main

import "strings"

const quickExecutionCompactSchema = "quick-execution-compact-v1"

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
		"response_schema":     quickExecutionCompactSchema,
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

// quickExecutionResponseData materializes the human pulse only if the caller
// will receive it. Canonical confirmation is still loaded by the owning action;
// this optimization never skips validation, packet compilation, or Work claims.
func quickExecutionResponseData(data map[string]any, ref, state, digest string, compact bool, buildPulse func() any) map[string]any {
	out := data
	if compact {
		out = compactQuickExecutionData(data, ref, state, digest)
	}
	if _, hasConfirmation := out["confirmation"]; !hasConfirmation {
		// Includes both a successful compact projection and packet-only output.
		return out
	}
	if _, hasPulse := out["pulse"]; hasPulse {
		return out
	}
	// Do not mutate the input map when the projection falls back to full output.
	full := make(map[string]any, len(out)+1)
	for key, value := range out {
		full[key] = value
	}
	full["pulse"] = buildPulse()
	return full
}
