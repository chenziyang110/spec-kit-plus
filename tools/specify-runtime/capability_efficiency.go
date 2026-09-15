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

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/buildinfo"
)

const (
	maxAPICapabilitySelection = 32
	maxAPIPackOutputBytes     = 128 * 1024
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
		return writeEnvelope(stdout, env)
	}
	requested, env, ok := apiRequestedCapabilities(args, optionValue(args, "--project-root", "."), "api ensure")
	if !ok {
		return writeEnvelope(stdout, env)
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
	return writeEnvelope(stdout, env)
}

func runAPIPack(args []string, stdout io.Writer, cliVersion string) int {
	if env, ok := validateAPIEfficiencyOptions(args, "api pack", map[string]bool{"--include-schema": true}, "--capabilities", "--requires-json", "--project-root", "--format"); !ok {
		return writeEnvelope(stdout, env)
	}
	requested, env, ok := apiRequestedCapabilities(args, optionValue(args, "--project-root", "."), "api pack")
	if !ok {
		return writeEnvelope(stdout, env)
	}
	includeSchema := hasFlag(args, "--include-schema")
	items := make([]any, 0, len(requested))
	for _, capabilityID := range requested {
		descriptor, ok := apiCapabilityDescriptor(capabilityID)
		if !ok {
			env := NewEnvelope("usage-error", fmt.Sprintf("unknown capability %q", capabilityID))
			env.Blockers = append(env.Blockers, "request only capabilities published by api list")
			return writeEnvelope(stdout, env)
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
		if schemaID, ok := descriptor.capability["input_schema"].(string); ok && strings.TrimSpace(schemaID) != "" {
			item["schema_ref"] = schemaID
			if includeSchema {
				schema, found := apiSchemaPayload(schemaID)
				if !found {
					env := NewEnvelope("error", fmt.Sprintf("schema %q could not be resolved", schemaID))
					env.Blockers = append(env.Blockers, "published capability input_schema is missing its runtime descriptor")
					return writeEnvelope(stdout, env)
				}
				item["schema"] = schema
			}
		}
		items = append(items, item)
	}
	encoded, err := json.Marshal(items)
	if err != nil {
		env := NewEnvelope("error", "capability pack could not be encoded")
		env.Blockers = append(env.Blockers, err.Error())
		return writeEnvelope(stdout, env)
	}
	if len(encoded) > maxAPIPackOutputBytes {
		env := NewEnvelope("usage-error", "requested capability pack exceeds the bounded output limit")
		env.Blockers = append(env.Blockers, fmt.Sprintf("capability pack exceeds %d bytes; request fewer capabilities or omit --include-schema", maxAPIPackOutputBytes))
		return writeEnvelope(stdout, env)
	}
	env = NewEnvelope("ok", "capability pack assembled")
	env.Data["requested"] = presentOrRequested(requested)
	env.Data["include_schema"] = includeSchema
	env.Data["capability_set_sha256"] = capabilitySetSHA256()
	env.Data["runtime"] = apiRuntimeIdentity(cliVersion)
	env.Items = items
	return writeEnvelope(stdout, env)
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
	raw, err := resolveJSONInputBytesFrom(optionValue(args, "--requires-json", ""), projectRoot, label, "--requires-json", os.Stdin)
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
	request := map[string]any{}
	if err := json.Unmarshal(raw, &request); err != nil {
		return nil, fmt.Errorf("%s --requires-json must be a JSON object: %w", label, err)
	}
	values, ok := request["capabilities"].([]any)
	if !ok {
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
	if code := runAPIShow([]string{capabilityID}, &stdout); code != 0 {
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
