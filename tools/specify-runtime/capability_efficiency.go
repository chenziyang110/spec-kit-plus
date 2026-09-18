package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"strings"
	"unicode/utf8"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/buildinfo"
)

const (
	maxAPICapabilitySelection  = 32
	maxAPICapabilityInputBytes = 128 * 1024
	maxAPIPackOutputBytes      = 128 * 1024
)

type apiCapabilityDescriptorRecord struct {
	capability map[string]any
	showArgv   []string
	nextArgv   []string
}

func capabilitySetSHA256() string {
	sum := sha256.Sum256([]byte(strings.Join(defaultCapabilities(), "\n")))
	return hex.EncodeToString(sum[:])
}

func apiRuntimeIdentity(cliVersion string) map[string]any {
	info := buildinfo.Current(cliVersion)
	return map[string]any{
		"cli_version":       info.Version,
		"protocol_version":  protocolVersion,
		"source_revision":   info.SourceRevision,
		"dirty":             info.Dirty,
		"capability_set_id": capabilitySetSHA256(),
	}
}

func runAPIEnsure(args []string, stdout io.Writer, cliVersion string) int {
	if env, ok := validateAPIEfficiencyOptions(args, "api ensure", nil, "--capabilities", "--requires-json", "--project-root", "--format"); !ok {
		return writeAPICapabilityEnvelope(stdout, env)
	}
	requested, env, ok := apiRequestedCapabilities(args, optionValue(args, "--project-root", "."), "api ensure")
	if !ok {
		return writeAPICapabilityEnvelope(stdout, env)
	}
	present := make([]string, 0, len(requested))
	missing := make([]string, 0)
	available := defaultCapabilities()
	for _, capabilityID := range requested {
		if containsCapability(available, capabilityID) {
			present = append(present, capabilityID)
			continue
		}
		missing = append(missing, capabilityID)
	}
	status := "ok"
	summary := "requested capabilities are available"
	if len(missing) > 0 {
		status = "blocked"
		summary = "requested capabilities are missing"
	}
	env = NewEnvelope(status, summary)
	env.Data["requested"] = presentOrRequested(requested)
	env.Data["present"] = present
	env.Data["missing"] = missing
	env.Data["capability_set_sha256"] = capabilitySetSHA256()
	env.Data["runtime"] = apiRuntimeIdentity(cliVersion)
	env.ShowArgv = []string{"specify-runtime", "api", "list", "--format", "json"}
	return writeAPICapabilityEnvelope(stdout, env)
}

func runAPIPack(args []string, stdout io.Writer, cliVersion string) int {
	if env, ok := validateAPIEfficiencyOptions(args, "api pack", map[string]bool{"--include-schema": true}, "--capabilities", "--requires-json", "--project-root", "--format"); !ok {
		return writeAPICapabilityEnvelope(stdout, env)
	}
	requested, env, ok := apiRequestedCapabilities(args, optionValue(args, "--project-root", "."), "api pack")
	if !ok {
		return writeAPICapabilityEnvelope(stdout, env)
	}
	includeSchema := hasFlag(args, "--include-schema")
	items := make([]any, 0, len(requested))
	for _, capabilityID := range requested {
		descriptor, ok := apiCapabilityDescriptor(capabilityID)
		if !ok {
			env := NewEnvelope("usage-error", fmt.Sprintf("unknown capability %q", capabilityID))
			env.Blockers = append(env.Blockers, "request only capabilities published by api list")
			return writeAPICapabilityEnvelope(stdout, env)
		}
		item := map[string]any{
			"id":             descriptor.capability["id"],
			"summary":        descriptor.capability["summary"],
			"command":        descriptor.capability["command"],
			"usage":          descriptor.capability["usage"],
			"side_effect":    descriptor.capability["side_effect"],
			"input_contract": descriptor.capability["input_contract"],
		}
		addQuickPackOutputContract(capabilityID, descriptor.capability, item)
		addQuickShadowPackContract(capabilityID, item)
		if schemaID, ok := descriptor.capability["input_schema"].(string); ok && strings.TrimSpace(schemaID) != "" {
			item["schema_ref"] = schemaID
			if includeSchema {
				schema, found := apiSchemaPayload(schemaID)
				if !found {
					env := NewEnvelope("error", fmt.Sprintf("schema %q could not be resolved", schemaID))
					env.Blockers = append(env.Blockers, "published capability input_schema is missing its runtime descriptor")
					return writeAPICapabilityEnvelope(stdout, env)
				}
				item["schema"] = schema
			}
		}
		items = append(items, item)
	}
	env = NewEnvelope("ok", "capability pack assembled")
	env.Data["requested"] = presentOrRequested(requested)
	env.Data["include_schema"] = includeSchema
	env.Data["capability_set_sha256"] = capabilitySetSHA256()
	env.Data["runtime"] = apiRuntimeIdentity(cliVersion)
	env.Items = items
	return writeAPICapabilityEnvelope(stdout, env)
}

func validateAPIEfficiencyOptions(args []string, label string, booleanOptions map[string]bool, valueOptions ...string) (Envelope, bool) {
	allowedValues := make(map[string]bool, len(valueOptions))
	for _, option := range valueOptions {
		allowedValues[option] = true
	}
	seen := map[string]bool{}
	for index := 0; index < len(args); index++ {
		option := args[index]
		if !strings.HasPrefix(option, "--") || (!allowedValues[option] && !booleanOptions[option]) {
			env := NewEnvelope("usage-error", label+" options are invalid")
			env.Blockers = append(env.Blockers, fmt.Sprintf("unknown option %q", option))
			return env, false
		}
		if seen[option] {
			env := NewEnvelope("usage-error", label+" options are invalid")
			env.Blockers = append(env.Blockers, fmt.Sprintf("option %q was repeated", option))
			return env, false
		}
		seen[option] = true
		if booleanOptions[option] {
			continue
		}
		if index+1 >= len(args) || strings.HasPrefix(args[index+1], "--") {
			env := NewEnvelope("usage-error", label+" options are invalid")
			env.Blockers = append(env.Blockers, fmt.Sprintf("option %q requires a value", option))
			return env, false
		}
		index++
	}
	return Envelope{}, true
}

func apiRequestedCapabilities(args []string, projectRoot, label string) ([]string, Envelope, bool) {
	hasCSV := hasFlag(args, "--capabilities")
	hasJSON := hasFlag(args, "--requires-json")
	if hasCSV == hasJSON {
		env := NewEnvelope("usage-error", label+" requires exactly one of --capabilities or --requires-json")
		env.Blockers = append(env.Blockers, "use --capabilities <csv> for a short list or --requires-json <object|@path|-> for structured input")
		return nil, env, false
	}
	if hasCSV {
		return parseCapabilityCSV(optionValue(args, "--capabilities", ""), label)
	}
	raw, err := resolveFileBackedInputBytesFrom(optionValue(args, "--requires-json", ""), projectRoot, label, "--requires-json", os.Stdin, maxAPICapabilityInputBytes)
	if err != nil {
		env := NewEnvelope("usage-error", label+" input is invalid")
		env.Blockers = append(env.Blockers, err.Error())
		return nil, env, false
	}
	requested, err := parseCapabilityRequirementsJSON(raw, label)
	if err != nil {
		env := NewEnvelope("usage-error", label+" input is invalid")
		env.Blockers = append(env.Blockers, err.Error())
		return nil, env, false
	}
	return requested, Envelope{}, true
}

func parseCapabilityCSV(raw, label string) ([]string, Envelope, bool) {
	if len(raw) > maxAPICapabilityInputBytes || !utf8.ValidString(raw) {
		env := NewEnvelope("usage-error", label+" capabilities are invalid")
		env.Blockers = append(env.Blockers, "capability selection must be valid UTF-8 and at most 128 KiB")
		return nil, env, false
	}
	parts := strings.Split(raw, ",")
	ids := make([]string, 0, len(parts))
	seen := map[string]bool{}
	for _, part := range parts {
		id := strings.TrimSpace(part)
		if id == "" {
			env := NewEnvelope("usage-error", label+" capabilities are invalid")
			env.Blockers = append(env.Blockers, "capability ids must be non-empty comma-separated values")
			return nil, env, false
		}
		if seen[id] {
			env := NewEnvelope("usage-error", label+" capabilities are invalid")
			env.Blockers = append(env.Blockers, fmt.Sprintf("duplicate capability %q", id))
			return nil, env, false
		}
		seen[id] = true
		ids = append(ids, id)
	}
	if len(ids) == 0 {
		env := NewEnvelope("usage-error", label+" requires at least one capability")
		return nil, env, false
	}
	if len(ids) > maxAPICapabilitySelection {
		env := NewEnvelope("usage-error", label+" exceeds the bounded capability selection limit")
		env.Blockers = append(env.Blockers, fmt.Sprintf("request at most %d capabilities per call", maxAPICapabilitySelection))
		return nil, env, false
	}
	return ids, Envelope{}, true
}

func parseCapabilityRequirementsJSON(raw []byte, label string) ([]string, error) {
	if len(raw) > maxAPICapabilityInputBytes || !utf8.Valid(raw) {
		return nil, fmt.Errorf("%s --requires-json must be valid UTF-8 and at most 128 KiB", label)
	}
	decoder := json.NewDecoder(bytes.NewReader(raw))
	opening, err := decoder.Token()
	if err != nil || opening != json.Delim('{') {
		return nil, fmt.Errorf("%s --requires-json must be a JSON object", label)
	}
	seenFields := map[string]bool{}
	var selected json.RawMessage
	for decoder.More() {
		token, err := decoder.Token()
		key, ok := token.(string)
		if err != nil || !ok {
			return nil, fmt.Errorf("%s --requires-json has an invalid object key", label)
		}
		// Token decodes escapes first, so capabilities and capabiliti\u0065s
		// cannot silently become two competing selectors.
		if seenFields[key] {
			return nil, fmt.Errorf("%s --requires-json has a duplicate object key", label)
		}
		seenFields[key] = true
		if key != "capabilities" && strings.EqualFold(key, "capabilities") {
			return nil, fmt.Errorf("%s --requires-json requires the exact capabilities field name", label)
		}
		var value json.RawMessage
		if err := decoder.Decode(&value); err != nil {
			return nil, fmt.Errorf("%s --requires-json contains invalid JSON: %w", label, err)
		}
		if key == "capabilities" {
			selected = value
		}
		// Preserve compatibility with unrelated top-level metadata: validate
		// its JSON syntax but do not decode numbers, retain or interpret it.
	}
	if closing, err := decoder.Token(); err != nil || closing != json.Delim('}') {
		return nil, fmt.Errorf("%s --requires-json has an incomplete object", label)
	}
	if err := decoder.Decode(new(json.RawMessage)); err != io.EOF {
		return nil, fmt.Errorf("%s --requires-json must contain exactly one JSON object", label)
	}
	var values []any
	if len(selected) == 0 || json.Unmarshal(selected, &values) != nil || values == nil {
		return nil, fmt.Errorf("%s --requires-json must include capabilities[]", label)
	}
	if len(values) == 0 {
		return nil, fmt.Errorf("%s --requires-json capabilities[] must not be empty", label)
	}
	if len(values) > maxAPICapabilitySelection {
		return nil, fmt.Errorf("%s --requires-json exceeds %d capabilities", label, maxAPICapabilitySelection)
	}
	ids := make([]string, 0, len(values))
	seen := map[string]bool{}
	for _, rawValue := range values {
		id, ok := rawValue.(string)
		id = strings.TrimSpace(id)
		if !ok || id == "" {
			return nil, fmt.Errorf("%s --requires-json capabilities[] must contain only non-empty strings", label)
		}
		if seen[id] {
			return nil, fmt.Errorf("%s --requires-json contains duplicate capability %q", label, id)
		}
		seen[id] = true
		ids = append(ids, id)
	}
	return ids, nil
}

func presentOrRequested(ids []string) []string {
	return append([]string(nil), ids...)
}

func apiCapabilityDescriptor(capabilityID string) (apiCapabilityDescriptorRecord, bool) {
	var stdout bytes.Buffer
	if code := runAPIShowWithQuickShadow([]string{capabilityID}, &stdout); code != 0 {
		return apiCapabilityDescriptorRecord{}, false
	}
	payload := map[string]any{}
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		return apiCapabilityDescriptorRecord{}, false
	}
	data, ok := payload["data"].(map[string]any)
	if !ok {
		return apiCapabilityDescriptorRecord{}, false
	}
	capability, ok := data["capability"].(map[string]any)
	if !ok {
		return apiCapabilityDescriptorRecord{}, false
	}
	return apiCapabilityDescriptorRecord{
		capability: capability,
		showArgv:   stringSliceFromAny(payload["show_argv"]),
		nextArgv:   stringSliceFromAny(payload["next_argv"]),
	}, true
}

func apiSchemaPayload(schemaID string) (map[string]any, bool) {
	var stdout bytes.Buffer
	if code := runAPISchema([]string{schemaID}, &stdout); code != 0 {
		return nil, false
	}
	payload := map[string]any{}
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		return nil, false
	}
	data, ok := payload["data"].(map[string]any)
	if !ok {
		return nil, false
	}
	schema, ok := data["schema"].(map[string]any)
	return schema, ok
}

func stringSliceFromAny(value any) []string {
	items, ok := value.([]any)
	if !ok {
		if strings, ok := value.([]string); ok {
			return append([]string(nil), strings...)
		}
		return nil
	}
	result := make([]string, 0, len(items))
	for _, item := range items {
		text, ok := item.(string)
		if !ok {
			return nil
		}
		result = append(result, text)
	}
	return result
}

// The bound applies to the complete encoded response, not only Items. The
// ordinary writer binds the runtime argv and metadata before this size check.
// Nothing is emitted until serialization succeeds. A failed/short destination
// write returns 1 without retrying, appending another response or rerunning work.
func writeAPICapabilityEnvelope(stdout io.Writer, env Envelope) int {
	if stdout == nil {
		return 1
	}
	var buffer bytes.Buffer
	code := writeEnvelope(&buffer, env)
	if code != ExitCodeForStatus(env.Status) || !json.Valid(buffer.Bytes()) {
		return 1
	}
	if buffer.Len() > maxAPIPackOutputBytes {
		buffer.Reset()
		env = NewEnvelope("usage-error", "requested capability response exceeds the bounded output limit")
		env.Data["error_code"] = "api-capability-output-limit"
		env.Data["max_output_bytes"] = maxAPIPackOutputBytes
		env.Blockers = append(env.Blockers, "Request fewer capabilities or omit --include-schema; no partial capability contract was returned.")
		code = writeEnvelope(&buffer, env)
		if code != 2 || buffer.Len() > maxAPIPackOutputBytes || !json.Valid(buffer.Bytes()) {
			return 1
		}
	}
	n, err := stdout.Write(buffer.Bytes())
	if err != nil || n != buffer.Len() {
		return 1
	}
	return code
}
