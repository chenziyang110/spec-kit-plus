package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strings"
)

const doProtectedSchema = "spec-kit-protected-process.v1"

func doProtectedDefinitionConditions() []any {
	return []any{map[string]any{
		"if": map[string]any{"required": []string{"external_inputs"}, "properties": map[string]any{"external_inputs": map[string]any{"minProperties": 1}}},
		"then": map[string]any{"properties": map[string]any{
			"steps":  map[string]any{"items": map[string]any{"not": map[string]any{"required": []string{"native_action"}}}},
			"checks": map[string]any{"items": map[string]any{"properties": map[string]any{"kind": doSchemaEnum("exit_code", "file")}, "not": map[string]any{"required": []string{"native_action"}}}},
		}},
	}}
}

func doExternalInputSchema() map[string]any {
	return map[string]any{
		"type": "object", "maxProperties": 32, "additionalProperties": false,
		"description": "Protected files outside the project. Store only binding/environment names; inherit actual absolute paths from the local environment. Use a whole {{external:name}} script data argument, never a path parameter or shell expression. Missing bindings block prepare. Paths/content are never returned or copied. Protected sessions support exit_code/file checks only; run through the protected process helper with child output suppressed.",
		"patternProperties": map[string]any{`^[a-z][a-z0-9_]{0,63}$`: doSchemaObject(map[string]any{
			"environment": map[string]any{"type": "string", "pattern": `^[A-Z_][A-Z0-9_]{0,127}$`},
		}, "environment")},
	}
}

// Preserve fingerprints of older sessions when there are no protected inputs.
func doSourceDigest(files map[string]string, revision string, dirty []string, external string) string {
	basis := map[string]any{"files": files, "source_revision": revision, "dirty_paths": dirty}
	if external != "" {
		basis["external_inputs"] = external
	}
	return doDigest(basis)
}

func doProtectedAction(session DoSession, action doAction) bool {
	return len(session.Definition.ExternalInputs) > 0 && len(action.argv) > 0
}

// This packet contains references, never expanded argv. A native tool invokes
// the bundled helper; the runtime continues to own state, not execution.
func doProtectedPacket(root string, session DoSession, action doAction, attemptID, fingerprint string) (map[string]any, error) {
	if !doProtectedAction(session, action) {
		return nil, nil
	}
	snapshot, external, err := doExternalSnapshot(root, session.Definition)
	if err != nil {
		return nil, err
	}
	bindings := map[string]any{}
	for name, binding := range snapshot {
		bindings[name] = map[string]string{"environment": binding.Environment, "sha256": binding.ContentSHA256}
	}
	sources, err := playbookSourceFingerprint(root, session.Definition)
	if err != nil {
		return nil, fmt.Errorf("protected_process_project_source_unavailable")
	}
	if _, current, _, _, err := doCaptureSource(root, session.Definition, session.WriteScope); err != nil || current != fingerprint {
		return nil, fmt.Errorf("protected_process_inputs_changed_while_preparing_packet; refresh do next")
	}
	return map[string]any{
		"schema": doProtectedSchema, "attempt_id": attemptID,
		"definition_digest": session.DefinitionDigest, "source_fingerprint": fingerprint,
		"external_fingerprint": external,
		"cwd":                  action.cwd, "argv": action.argv, "external_inputs": bindings, "source_files": sources,
	}, nil
}

func doProtectedNext(root string, session DoSession, action doAction, attemptID, fingerprint string, entry map[string]any) error {
	packet, err := doProtectedPacket(root, session, action, attemptID, fingerprint)
	if err != nil || packet == nil {
		return err
	}
	entry["protected_execution"] = packet
	entry["execution_argv"] = []string{"python", ".specify/scripts/shared/do_protected_process.py", "--input-json", "-"}
	entry["execution_instructions"] = "After recording started_input refresh do next, then pass protected_execution unchanged on helper stdin from the project root with inherited local bindings. Never expand the symbolic action in tool arguments. Child stdout/stderr are discarded. Map helper outcome to status; blocked/failed never passes even with child exit_code 0, and interruption requires recovery. Record symbolic argv, actual child exit_code and timestamps only; keep summary empty and never attach raw logs."
	return nil
}

var doProtectedToolID = regexp.MustCompile(`^[A-Za-z0-9][A-Za-z0-9_.:-]{0,255}$`)

func doProtectedRecord(session DoSession, event doRecordEvent) error {
	if len(session.Definition.ExternalInputs) == 0 {
		return nil
	}
	if event.Summary != "" || (event.ToolCallID != "" && !doProtectedToolID.MatchString(event.ToolCallID)) {
		return fmt.Errorf("protected_input_observation_requires_empty_summary_and_opaque_tool_call_id; record only symbolic argv, status, exit_code and timestamps")
	}
	for _, ref := range event.ResultRefs {
		if ref.Kind != "file" {
			return fmt.Errorf("protected_input_content_evidence_forbidden; use exit_code or file metadata checks, never logs or report contents")
		}
	}
	return nil
}

// Extra guard for accidentally pasted paths/configuration in free-form metadata
// and recovery evidence. Actual values exist only in memory and never in errors.
// Process output is discarded instead of relying on this guard for redaction.
func doProtectedPrivatePayload(definition PlaybookDefinition, value any) error {
	if len(definition.ExternalInputs) == 0 {
		return nil
	}
	raw, err := json.Marshal(value)
	if err != nil {
		return fmt.Errorf("protected_input_metadata_invalid")
	}
	var decoded any
	if json.Unmarshal(raw, &decoded) != nil {
		return fmt.Errorf("protected_input_metadata_invalid")
	}
	paths, fragments := []string{}, []string{}
	for _, binding := range definition.ExternalInputs {
		file := os.Getenv(binding.Environment)
		if file == "" {
			continue
		}
		paths = append(paths, strings.ToLower(strings.ReplaceAll(file, `\`, "/")))
		if real, err := filepath.EvalSymlinks(file); err == nil {
			paths = append(paths, strings.ToLower(strings.ReplaceAll(real, `\`, "/")))
		}
		info, err := os.Stat(file)
		if err != nil || !info.Mode().IsRegular() || info.Size() > 16*1024*1024 {
			continue
		}
		content, err := os.ReadFile(file)
		if err != nil {
			continue
		}
		for _, line := range bytes.Split(content, []byte{'\n'}) {
			if text := strings.TrimSpace(string(line)); len(text) >= 8 {
				fragments = append(fragments, text)
			}
		}
	}
	var inspect func(any) bool
	inspect = func(value any) bool {
		switch item := value.(type) {
		case string:
			pathText := strings.ToLower(strings.ReplaceAll(item, `\`, "/"))
			for _, path := range paths {
				if path != "" && strings.Contains(pathText, path) {
					return true
				}
			}
			for _, fragment := range fragments {
				if strings.Contains(item, fragment) {
					return true
				}
			}
		case []any:
			for _, child := range item {
				if inspect(child) {
					return true
				}
			}
		case map[string]any:
			for key, child := range item {
				if inspect(key) || inspect(child) {
					return true
				}
			}
		}
		return false
	}
	if inspect(decoded) {
		return fmt.Errorf("protected_input_private_payload_forbidden; retain binding names only and omit local paths, configuration contents and raw logs")
	}
	return nil
}
