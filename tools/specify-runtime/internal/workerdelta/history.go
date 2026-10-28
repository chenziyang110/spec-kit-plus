package workerdelta

import (
	"encoding/json"
	"fmt"
	"sort"
)

const BindingSchema = "spec-kit-cognition-result-binding-v1"

// CandidateFromStored is a read-only canonical path, never an input bypass.
// Every stored row retains its exact JSON bytes and runtime-owned digest.
func CandidateFromStored(stored map[string]any) (map[string]any, error) {
	if err := ValidateStored(stored); err != nil {
		return nil, err
	}
	result := Clone(stored)
	delete(result, "submission_history")
	delete(result, "cognition_result_binding")
	return result, nil
}

func Sequence(value any) (int, error) {
	switch v := value.(type) {
	case int:
		return v, nil
	case float64:
		if v == float64(int(v)) {
			return int(v), nil
		}
	case json.Number:
		n, err := v.Int64()
		if err == nil && n == int64(int(n)) {
			return int(n), nil
		}
	}
	return 0, fmt.Errorf("history sequence must be an integer")
}

func ValidateStored(stored map[string]any) error {
	value, present := stored["submission_history"]
	if !present {
		if _, exists := stored["cognition_result_binding"]; exists {
			return fmt.Errorf("result binding requires history")
		}
		return nil
	}
	rows, ok := value.([]any)
	if !ok {
		return fmt.Errorf("submission_history must be an array")
	}
	for index, raw := range rows {
		row, ok := raw.(map[string]any)
		if !ok {
			return fmt.Errorf("submission_history entries must be objects")
		}
		sequence, err := Sequence(row["sequence"])
		if err != nil || sequence != index+1 || row["schema"] != HistorySchema || !VersionOne(row["version"]) {
			return fmt.Errorf("invalid submission history sequence/schema")
		}
		text, ok := row["result_json"].(string)
		if !ok || row["result_sha256"] != Digest([]byte(text)) {
			return fmt.Errorf("submission history result digest mismatch")
		}
		attempt, ok := row["attempt_id"].(string)
		if !ok || attempt == "" {
			return fmt.Errorf("submission history lacks attempt")
		}
		status, ok := row["status"].(string)
		if !ok || !contains([]string{"success", "blocked", "failed", "rejected", "legacy", "pending"}, status) {
			return fmt.Errorf("submission history has invalid status")
		}
		if _, ok := row["rejection_reason"].(string); !ok {
			return fmt.Errorf("submission history lacks rejection reason")
		}
		if status != "rejected" {
			payload, err := Decode([]byte(text))
			if err != nil {
				return err
			}
			if _, exists := payload["submission_history"]; exists {
				return fmt.Errorf("recursive submission history")
			}
			if _, exists := payload["cognition_result_binding"]; exists {
				return fmt.Errorf("recursive result binding")
			}
		}
	}
	if raw, exists := stored["cognition_result_binding"]; exists {
		binding, ok := raw.(map[string]any)
		if !ok || binding["schema"] != BindingSchema || !VersionOne(binding["version"]) {
			return fmt.Errorf("unsupported result binding")
		}
		sequence, err := Sequence(binding["sequence"])
		if err != nil || sequence < 1 || sequence > len(rows) {
			return fmt.Errorf("result binding sequence is unavailable")
		}
		row := rows[sequence-1].(map[string]any)
		if row["status"] == "rejected" || binding["result_sha256"] != row["result_sha256"] || binding["attempt_id"] != row["attempt_id"] {
			return fmt.Errorf("result binding differs from submission history")
		}
		payload, err := Decode([]byte(row["result_json"].(string)))
		if err != nil {
			return err
		}
		projection := Clone(stored)
		delete(projection, "submission_history")
		delete(projection, "cognition_result_binding")
		if !Same(payload, projection) {
			return fmt.Errorf("current projection differs from its bound submission")
		}
		if !contains([]string{"submitted", "accepted"}, fmt.Sprint(binding["acceptance_state"])) {
			return fmt.Errorf("invalid result acceptance binding")
		}
	}
	return nil
}

// Append keeps previous immutable rows inside the existing canonical result;
// its caller commits this projection and owner state using the existing CAS.
func Append(previous, result map[string]any, raw []byte, status, rejection, resultRef, attempt string, revision int) (map[string]any, error) {
	if previous == nil {
		previous = map[string]any{}
	}
	if err := ValidateStored(previous); err != nil {
		return nil, err
	}
	rows := []any{}
	if existing, ok := Clone(previous)["submission_history"].([]any); ok {
		rows = existing
	}
	if len(rows) == 0 && len(previous) > 0 {
		legacy := Clone(previous)
		delete(legacy, "submission_history")
		delete(legacy, "cognition_result_binding")
		text, err := json.Marshal(legacy)
		if err != nil {
			return nil, err
		}
		rows = append(rows, historyRow(1, "legacy:1", "legacy", string(text), "", Accounting(legacy)))
	}
	sequence := len(rows) + 1
	if attempt == "" {
		attempt = fmt.Sprintf("submission:%d", sequence)
	}
	var text []byte
	var accounting []string
	projection := Clone(previous)
	delete(projection, "submission_history")
	if rejection != "" {
		status, text = "rejected", raw
		if candidate, err := Decode(raw); err == nil {
			accounting = Accounting(candidate)
		}
		if len(projection) == 0 {
			projection = map[string]any{"status": "pending", "summary": "Rejected worker submission; no accepted result"}
		}
	} else {
		projection = Clone(result)
		delete(projection, "submission_history")
		delete(projection, "cognition_result_binding")
		var err error
		text, err = json.Marshal(projection)
		if err != nil {
			return nil, err
		}
		accounting = Accounting(projection)
		projection["cognition_result_binding"] = map[string]any{"schema": BindingSchema, "version": 1, "sequence": sequence, "result_ref": resultRef, "result_sha256": Digest(text), "attempt_id": attempt, "lifecycle_revision": revision, "acceptance_state": "submitted", "acceptance_ref": "", "acceptance_revision": 0}
	}
	rows = append(rows, historyRow(sequence, attempt, status, string(text), rejection, accounting))
	projection["submission_history"] = rows
	if err := ValidateStored(projection); err != nil {
		return nil, err
	}
	return projection, nil
}

func historyRow(sequence int, attempt, status, text, rejection string, paths []string) map[string]any {
	return map[string]any{"schema": HistorySchema, "version": 1, "sequence": sequence, "attempt_id": attempt, "status": status, "result_json": text, "result_sha256": Digest([]byte(text)), "rejection_reason": rejection, "retained_paths": paths}
}

func Accept(stored map[string]any, acceptanceRef string, revision int) error {
	if err := ValidateStored(stored); err != nil {
		return err
	}
	binding, ok := stored["cognition_result_binding"].(map[string]any)
	if !ok {
		return nil
	} // Existing legacy acceptance remains audit-only.
	if stored["status"] != "success" {
		return fmt.Errorf("only successful submitted results may be accepted")
	}
	binding["acceptance_state"], binding["acceptance_ref"], binding["acceptance_revision"] = "accepted", acceptanceRef, revision
	return nil
}

func HistoryPaths(stored map[string]any) []string {
	set := map[string]bool{}
	for _, p := range Accounting(stored) {
		set[p] = true
	}
	rows, _ := stored["submission_history"].([]any)
	for _, raw := range rows {
		row, _ := raw.(map[string]any)
		if text, ok := row["result_json"].(string); ok {
			if input, err := Decode([]byte(text)); err == nil {
				for _, p := range Accounting(input) {
					set[p] = true
				}
			}
		}
		if paths, err := Paths(row["retained_paths"]); err == nil {
			for _, p := range paths {
				set[p] = true
			}
		}
	}
	result := []string{}
	for p := range set {
		result = append(result, p)
	}
	sort.Strings(result)
	return result
}

// PendingSequences keeps unparseable retained-change claims visible to the
// source reconciliation owner without pretending that they changed no files.
func PendingSequences(stored map[string]any) []any {
	result := []any{}
	rows, _ := stored["submission_history"].([]any)
	for index, raw := range rows {
		row, _ := raw.(map[string]any)
		text, _ := row["result_json"].(string)
		if _, err := Decode([]byte(text)); err != nil {
			result = append(result, index+1)
		}
	}
	return result
}
