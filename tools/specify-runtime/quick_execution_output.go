package main

import (
	"fmt"
	"strings"
)

// quickCompactOutputContract is additive discovery metadata. It does not change
// a capability's existing usage, input contract, or side-effect classification.
// Each call returns fresh collections, never shared mutable discovery state.
func quickCompactOutputContract(capabilityID string) map[string]any {
	if !strings.HasPrefix(capabilityID, "quick.") {
		return nil
	}
	mode := strings.TrimPrefix(capabilityID, "quick.")
	if !quickCompactCommand(mode) {
		return nil
	}
	return map[string]any{
		"scope":                   "response_presentation_only",
		"flag":                    "--compact",
		"flag_type":               "standalone_boolean",
		"default":                 "full",
		"response_schema":         quickExecutionCompactSchema,
		"fallback":                "full",
		"omitted_fields":          []string{"confirmation", "pulse"},
		"binding_kind":            "decision_digest_not_file_hash",
		"requires_full_intake":    true,
		"mutates_canonical_state": false,
		"compact_usage":           quickCompactUsage(mode),
		"full_context_usage":      "specify-runtime quick item-status <quick-id> [--project-root <path>] --format json",
		"context_refresh_policy":  "query item-status without --compact; never replay a mutation to expand output",
	}
}

func quickCompactCommand(mode string) bool {
	switch mode {
	case "item-start", "allow-inline", "item-accept", "item-status":
		return true
	default:
		return false
	}
}

func quickCompactUsage(mode string) string {
	base := "specify-runtime quick " + mode + " <quick-id>"
	switch mode {
	case "item-start":
		base += " --item Qn [--current-work-id <work-id>] [--current-work-fence <fence>]"
	case "allow-inline":
		base += " --item Qn --reason <spawn_failed:detail|tool_missing:detail|subagent-blocked:detail>"
	case "item-accept":
		base += " --item Qn --evidence <text> [--allow-inline --reason <spawn_failed:detail|tool_missing:detail|subagent-blocked:detail>]"
	}
	return base + " [--project-root <path>] [--compact] --format json"
}

// Preserve an owning descriptor's output contract, including explicit null.
// Quick's fallback fills only absent metadata; it never replaces upstream data.
func addQuickPackOutputContract(capabilityID string, descriptor, item map[string]any) {
	addQuickItemDispatchContract(capabilityID, descriptor, item)
	if item == nil {
		return
	}
	if _, exists := item["output_contract"]; exists {
		return
	}
	if contract, exists := descriptor["output_contract"]; exists {
		item["output_contract"] = contract
		return
	}
	if contract := quickCompactOutputContract(capabilityID); contract != nil {
		item["output_contract"] = contract
	}
}

// Parse presentation once, before runExecution accesses the project. Values of
// existing Quick options are data, even when their literal text is --compact.
// Required input validation remains with each existing command. This does not
// add a general CLI parser or change other Quick command families.
func parseQuickExecutionCompactOption(mode string, args []string) (bool, error) {
	requested := false
	for index := 0; index < len(args); index++ {
		arg := args[index]
		if quickExecutionOptionTakesValue(arg) {
			if index+1 < len(args) {
				index++
			}
			continue
		}
		if strings.HasPrefix(arg, "--compact=") {
			return false, fmt.Errorf("--compact is a standalone boolean flag; omit it for full output")
		}
		if arg == "--compact" {
			if requested {
				return false, fmt.Errorf("--compact must not be repeated")
			}
			requested = true
		}
	}
	mode = strings.ToLower(strings.TrimSpace(mode))
	if mode == "packet-compile" {
		// Historical compatibility: the flag is accepted but packets stay full.
		return false, nil
	}
	if requested && !quickCompactCommand(mode) {
		return false, fmt.Errorf("--compact is supported by item-start, allow-inline, item-accept and item-status only")
	}
	return requested, nil
}

// Help uses the same per-capability producer as api show and api pack.
// Derive membership from the command list the owning help already publishes.
func addQuickHelpOutputContracts(data map[string]any) {
	if data == nil {
		return
	}
	if _, exists := data["output_contracts"]; exists {
		return
	}
	commands, ok := data["commands"].([]string)
	if !ok {
		return
	}
	addQuickHelpDispatchContract(data)
	contracts := map[string]any{}
	for _, mode := range commands {
		id := "quick." + mode
		if contract := quickCompactOutputContract(id); contract != nil {
			contracts[id] = contract
		}
	}
	if len(contracts) > 0 {
		data["output_contracts"] = contracts
	}
}

// Shared option-value classification keeps literal flag-shaped evidence as data.
func quickExecutionOptionTakesValue(arg string) bool {
	switch arg {
	case "--project-root", "--format", "--item", "--current-work-id",
		"--current-work-fence", "--reason", "--evidence", "--input-json",
		"--digest", "--view", "--status", "--result-state", "--evidence-json",
		"--update-id", "--slug", "--intent", "--summary", "--phase",
		"--decision", "--recommendation", "--mode", "--input", "--review-digest",
		"--expected-state-sha256", "--feature-dir", "--surface", "--record-id",
		"--expected-sha256", "--limit":
		return true
	}
	return false
}
