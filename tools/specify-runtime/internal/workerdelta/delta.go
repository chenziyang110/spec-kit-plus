// Package workerdelta owns the shared, advisory worker cognition handoff.
// Candidate semantics never grant execution, acceptance, or graph authority.
package workerdelta

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"math"
	"reflect"
	"sort"
	"strconv"
	"strings"
)

const Schema = "spec-kit-cognition-delta-v1"
const HistorySchema = "spec-kit-worker-submission-v1"

func VersionOne(value any) bool {
	switch v := value.(type) {
	case int:
		return v == 1
	case int64:
		return v == 1
	case json.Number:
		return v.String() == "1"
	}
	return false
}

var Fields = []string{"changed_paths", "path_changes", "behavior_surfaces", "owner_surfaces", "consumer_surfaces", "interfaces", "generated_surfaces", "generated_surface_notes", "state_contracts", "evidence_refs", "verification_evidence", "invalidated_claim_refs", "known_unknowns", "confidence_notes"}
var PathAliases = []string{"changed_files", "changedFiles", "files_changed", "changed_paths", "changedPaths"}

func Contract(taskID string) map[string]any {
	return map[string]any{"schema": Schema, "version": 1, "task_id": taskID, "authority": "worker_candidate", "retained_failure_edits": true, "rename_endpoints": true, "acceptance_owner": "runtime", "source_binding_owner": "runtime"}
}

func Clone(value map[string]any) map[string]any {
	raw, _ := json.Marshal(value)
	result, _ := Decode(raw)
	if result == nil {
		result = map[string]any{}
	}
	return result
}

func Digest(raw []byte) string { sum := sha256.Sum256(raw); return hex.EncodeToString(sum[:]) }

// Decode rejects duplicate keys and keeps JSON integers exactly, including
// evidence counters larger than the IEEE-754 exact integer range.
func Decode(raw []byte) (map[string]any, error) {
	d := json.NewDecoder(bytes.NewReader(raw))
	d.UseNumber()
	var read func() (any, error)
	read = func() (any, error) {
		t, err := d.Token()
		if err != nil {
			return nil, err
		}
		if delim, ok := t.(json.Delim); ok {
			switch delim {
			case '{':
				m := map[string]any{}
				for d.More() {
					key, err := d.Token()
					if err != nil {
						return nil, err
					}
					s, ok := key.(string)
					if !ok {
						return nil, fmt.Errorf("invalid JSON key")
					}
					if _, duplicate := m[s]; duplicate {
						return nil, fmt.Errorf("duplicate JSON field: %s", s)
					}
					value, err := read()
					if err != nil {
						return nil, err
					}
					m[s] = value
				}
				if _, err := d.Token(); err != nil {
					return nil, err
				}
				return m, nil
			case '[':
				a := []any{}
				for d.More() {
					value, err := read()
					if err != nil {
						return nil, err
					}
					a = append(a, value)
				}
				if _, err := d.Token(); err != nil {
					return nil, err
				}
				return a, nil
			default:
				return nil, fmt.Errorf("invalid JSON delimiter")
			}
		}
		return t, nil
	}
	value, err := read()
	if err != nil {
		return nil, err
	}
	if _, err := d.Token(); err != io.EOF {
		return nil, fmt.Errorf("input must contain exactly one JSON object")
	}
	result, ok := value.(map[string]any)
	if !ok {
		return nil, fmt.Errorf("worker result must be a JSON object")
	}
	if err := checkJSON(result); err != nil {
		return nil, err
	}
	return result, nil
}

func checkJSON(value any) error {
	switch v := value.(type) {
	case json.Number:
		// JSON integer evidence remains arbitrary precision. Fractional and
		// exponential values must also be finite in the Python JSON consumer.
		if strings.ContainsAny(v.String(), ".eE") {
			number, err := strconv.ParseFloat(v.String(), 64)
			if err != nil || math.IsInf(number, 0) || math.IsNaN(number) {
				return fmt.Errorf("non-finite JSON number")
			}
		}
	case float64:
		if math.IsNaN(v) || math.IsInf(v, 0) {
			return fmt.Errorf("non-finite JSON number")
		}
	case float32:
		if math.IsNaN(float64(v)) || math.IsInf(float64(v), 0) {
			return fmt.Errorf("non-finite JSON number")
		}
	case map[string]any:
		for _, child := range v {
			if err := checkJSON(child); err != nil {
				return err
			}
		}
	case []any:
		for _, child := range v {
			if err := checkJSON(child); err != nil {
				return err
			}
		}
	}
	_, err := json.Marshal(value)
	return err
}

func SafePath(value string) (string, error) {
	value = strings.ReplaceAll(strings.TrimSpace(value), "\\", "/")
	if value == "" || strings.HasPrefix(value, "/") || strings.ContainsAny(value, ":\x00\r\n") {
		return "", fmt.Errorf("path must be a project-relative path")
	}
	for _, part := range strings.Split(value, "/") {
		if part == ".." {
			return "", fmt.Errorf("path must stay within the project")
		}
	}
	for strings.HasPrefix(value, "./") {
		value = strings.TrimPrefix(value, "./")
	}
	if value == "." || value == "" {
		return "", fmt.Errorf("path must name a project file")
	}
	return value, nil
}

func Paths(value any) ([]string, error) {
	if value == nil {
		return []string{}, nil
	}
	var rows []any
	switch v := value.(type) {
	case []any:
		rows = v
	case []string:
		for _, item := range v {
			rows = append(rows, item)
		}
	case string:
		if strings.TrimSpace(v) == "" {
			return []string{}, nil
		}
		rows = []any{v} // Existing result path-list compatibility.
	default:
		return nil, fmt.Errorf("changed paths must be strings or an array of strings")
	}
	seen := map[string]bool{}
	result := []string{}
	for _, row := range rows {
		text, ok := row.(string)
		if !ok {
			return nil, fmt.Errorf("changed paths entries must be strings")
		}
		text, err := SafePath(text)
		if err != nil {
			return nil, err
		}
		if !seen[text] {
			seen[text] = true
			result = append(result, text)
		}
	}
	return result, nil
}

func array(value any, field string) ([]any, error) {
	if value == nil {
		return []any{}, nil
	}
	if v, ok := value.([]any); ok {
		return v, nil
	}
	if v, ok := value.([]string); ok {
		rows := []any{}
		for _, s := range v {
			rows = append(rows, s)
		}
		return rows, nil
	}
	return nil, fmt.Errorf("cognition_delta.%s must be an array", field)
}

func Same(left, right any) bool {
	a, ea := json.Marshal(left)
	b, eb := json.Marshal(right)
	return ea == nil && eb == nil && string(a) == string(b)
}

// Normalize accepts only a worker candidate. Canonical readers must first use
// CandidateFromStored, which independently checks runtime-owned history.
func Normalize(input map[string]any) (map[string]any, []string, error) {
	if err := checkJSON(input); err != nil {
		return nil, nil, err
	}
	for _, field := range []string{"submission_history", "cognition_result_binding"} {
		if _, supplied := input[field]; supplied {
			return nil, nil, fmt.Errorf("%s is runtime-owned", field)
		}
	}
	delta := map[string]any{}
	if raw, supplied := input["cognition_delta"]; supplied && raw != nil {
		object, ok := raw.(map[string]any)
		if !ok {
			return nil, nil, fmt.Errorf("cognition_delta must be an object")
		}
		if len(object) > 0 && !VersionOne(object["version"]) {
			return nil, nil, fmt.Errorf("unsupported cognition_delta schema/version")
		}
		delta = Clone(object)
	}
	explicit := len(delta) > 0
	allowed := map[string]bool{"schema": true, "version": true, "identity": true, "recovery": true}
	for _, field := range Fields {
		allowed[field] = true
	}
	if explicit {
		for field := range delta {
			if !allowed[field] {
				return nil, nil, fmt.Errorf("unsupported cognition_delta field: %s", field)
			}
		}
		if delta["schema"] != Schema || !VersionOne(delta["version"]) {
			return nil, nil, fmt.Errorf("unsupported cognition_delta schema/version")
		}
		if _, bad := delta["version"].(bool); bad {
			return nil, nil, fmt.Errorf("unsupported cognition_delta schema/version")
		}
		if raw, exists := delta["identity"]; exists {
			identity, ok := raw.(map[string]any)
			if !ok {
				return nil, nil, fmt.Errorf("cognition_delta.identity must be an object")
			}
			for field, rawValue := range identity {
				if !contains([]string{"task_ref", "task_id", "packet_id", "attempt_id"}, field) {
					return nil, nil, fmt.Errorf("unsupported cognition_delta.identity field: %s", field)
				}
				value, ok := rawValue.(string)
				if !ok || strings.TrimSpace(value) == "" {
					return nil, nil, fmt.Errorf("cognition_delta.identity.%s must be a nonblank string", field)
				}
				identity[field] = strings.TrimSpace(value)
			}
		}
	}
	identity, _ := delta["identity"].(map[string]any)
	for _, pair := range [][2]string{{"task_id", "taskId"}, {"packet_id", "packetId"}} {
		var value string
		seen := false
		for _, alias := range pair {
			if raw, exists := input[alias]; exists {
				text, ok := raw.(string)
				if !ok {
					return nil, nil, fmt.Errorf("%s must be a string", alias)
				}
				text = strings.TrimSpace(text)
				if seen && value != text {
					return nil, nil, fmt.Errorf("%s identity aliases conflict", pair[0])
				}
				value, seen = text, true
			}
		}
		if bound, exists := identity[pair[0]]; exists && value != "" && bound != value {
			return nil, nil, fmt.Errorf("cognition_delta.identity.%s conflicts with result", pair[0])
		}
	}
	var paths []string
	seen := false
	for _, field := range PathAliases {
		if raw, supplied := input[field]; supplied {
			if raw == nil {
				return nil, nil, fmt.Errorf("%s must be an array of paths", field)
			}
			incoming, err := Paths(raw)
			if err != nil {
				return nil, nil, err
			}
			if seen && !samePaths(paths, incoming) {
				return nil, nil, fmt.Errorf("changed path aliases conflict: %s", field)
			}
			if !seen {
				paths = incoming
			}
			seen = true
		}
	}
	if raw, supplied := delta["changed_paths"]; supplied {
		if _, ok := raw.([]any); !ok {
			if _, ok := raw.([]string); !ok {
				return nil, nil, fmt.Errorf("cognition_delta.changed_paths must be an array")
			}
		}
		incoming, err := Paths(raw)
		if err != nil {
			return nil, nil, err
		}
		if seen && !samePaths(paths, incoming) {
			return nil, nil, fmt.Errorf("cognition_delta conflicts with changed path aliases")
		}
		paths = incoming
	}
	if paths == nil {
		paths = []string{}
	}
	for _, field := range Fields {
		if field == "changed_paths" {
			continue
		}
		if raw, exists := delta[field]; exists {
			if raw == nil {
				return nil, nil, fmt.Errorf("cognition_delta.%s must be an array", field)
			}
			rows, err := array(raw, field)
			if err != nil {
				return nil, nil, err
			}
			delta[field] = rows
		}

		aliases := []string{field}
		if field == "verification_evidence" {
			aliases = append(aliases, "verification")
		}
		for _, alias := range aliases {
			if raw, exists := input[alias]; exists {
				if raw == nil {
					return nil, nil, fmt.Errorf("%s must be an array", alias)
				}
				rows, err := array(raw, field)
				if err != nil {
					return nil, nil, err
				}
				if previous, exists := delta[field]; exists && !Same(previous, rows) {
					return nil, nil, fmt.Errorf("cognition_delta.%s conflicts with %s", field, alias)
				}
				delta[field] = rows
			}
		}
	}
	pathSet := map[string]bool{}
	for _, p := range paths {
		pathSet[p] = true
	}
	rows, _ := delta["path_changes"].([]any)
	for index, value := range rows {
		row, ok := value.(map[string]any)
		if !ok {
			return nil, nil, fmt.Errorf("path_changes[%d] must be an object", index)
		}
		kind, _ := row["kind"].(string)
		if !contains([]string{"added", "modified", "deleted", "renamed", "retained", "unknown"}, kind) {
			return nil, nil, fmt.Errorf("path_changes[%d] has unsupported kind", index)
		}
		fields := []string{"path"}
		expected := 2
		if kind == "renamed" {
			fields = []string{"old_path", "new_path"}
			expected = 3
		}
		if len(row) != expected {
			return nil, nil, fmt.Errorf("path_changes[%d] has invalid shape", index)
		}
		for _, field := range fields {
			text, ok := row[field].(string)
			if !ok {
				return nil, nil, fmt.Errorf("path_changes[%d].%s must be a string", index, field)
			}
			p, err := SafePath(text)
			if err != nil {
				return nil, nil, err
			}
			if !pathSet[p] {
				return nil, nil, fmt.Errorf("path_changes endpoint %s is absent from changed_paths", p)
			}
			row[field] = p
		}
		if kind == "renamed" && row["old_path"] == row["new_path"] {
			return nil, nil, fmt.Errorf("rename endpoints must be distinct")
		}
	}
	if raw, exists := delta["recovery"]; exists {
		recovery, ok := raw.(map[string]any)
		if !ok {
			return nil, nil, fmt.Errorf("cognition_delta.recovery must be an object")
		}
		for field := range recovery {
			if field != "state" && field != "actions" {
				return nil, nil, fmt.Errorf("unsupported cognition_delta.recovery field")
			}
		}
		if raw, exists := recovery["state"]; exists {
			if _, ok := raw.(string); !ok {
				return nil, nil, fmt.Errorf("recovery.state must be a string")
			}
		}
		if raw, exists := recovery["actions"]; exists {
			if raw == nil {
				return nil, nil, fmt.Errorf("recovery.actions must be an array")
			}
			actions, err := array(raw, "recovery.actions")
			if err != nil {
				return nil, nil, err
			}
			recovery["actions"] = actions
		}
	}
	if len(delta) > 0 || len(paths) > 0 {
		delta["schema"] = Schema
		delta["version"] = 1
		delta["changed_paths"] = paths
		if _, exists := delta["identity"]; !exists {
			delta["identity"] = map[string]any{}
		}
		if _, exists := delta["path_changes"]; !exists {
			changes := []any{}
			for _, p := range paths {
				changes = append(changes, map[string]any{"kind": "unknown", "path": p})
			}
			delta["path_changes"] = changes
		}
	}
	return delta, paths, nil
}

func samePaths(left, right []string) bool {
	a := append([]string{}, left...)
	b := append([]string{}, right...)
	sort.Strings(a)
	sort.Strings(b)
	return reflect.DeepEqual(a, b)
}
func contains(values []string, value string) bool {
	for _, item := range values {
		if item == value {
			return true
		}
	}
	return false
}

// Accounting is deliberately conservative for rejected candidates. It keeps
// every safe reported endpoint, including disagreeing aliases, without making
// any statement that the worker owned or actually changed those bytes.
func Accounting(input map[string]any) []string {
	set := map[string]bool{}
	add := func(value any) {
		rows, _ := value.([]any)
		if s, ok := value.(string); ok {
			rows = []any{s}
		}
		if ss, ok := value.([]string); ok {
			for _, s := range ss {
				rows = append(rows, s)
			}
		}
		for _, row := range rows {
			if s, ok := row.(string); ok {
				if p, err := SafePath(s); err == nil {
					set[p] = true
				}
			}
		}
	}
	for _, field := range PathAliases {
		add(input[field])
	}
	delta, _ := input["cognition_delta"].(map[string]any)
	add(delta["changed_paths"])
	for _, value := range []any{input["path_changes"], delta["path_changes"]} {
		rows, _ := value.([]any)
		for _, raw := range rows {
			row, _ := raw.(map[string]any)
			for _, field := range []string{"path", "old_path", "new_path"} {
				add(row[field])
			}
		}
	}
	result := []string{}
	for p := range set {
		result = append(result, p)
	}
	if nested, ok := input["worker_result"].(map[string]any); ok {
		for _, p := range Accounting(nested) {
			if !set[p] {
				result = append(result, p)
				set[p] = true
			}
		}
	}
	sort.Strings(result)
	return result
}
