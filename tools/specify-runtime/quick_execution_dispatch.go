package main

import (
	"fmt"
	"strings"
)

const quickLeaderDirectMode = "leader-direct"
const quickDispatchSchema = "quick-item-dispatch-v1"

// Selection is explicit and capability-negotiated. The runtime enforces state,
// scope and result gates; it cannot infer semantic risk from the number of files.
func parseQuickLeaderDirectOption(mode string, args []string) (bool, error) {
	requested := false
	for i := 0; i < len(args); i++ {
		arg := args[i]
		if quickExecutionOptionTakesValue(arg) {
			if i+1 < len(args) {
				i++
			}
			continue
		}
		if strings.HasPrefix(arg, "--leader-direct=") {
			return false, fmt.Errorf("--leader-direct is a standalone boolean flag")
		}
		if arg == "--leader-direct" {
			if requested {
				return false, fmt.Errorf("--leader-direct must not be repeated")
			}
			requested = true
		}
	}
	if requested && strings.ToLower(strings.TrimSpace(mode)) != "item-start" {
		return false, fmt.Errorf("--leader-direct selects an executor at item-start only")
	}
	return requested, nil
}

// A missing flag on resume preserves a recorded selection. An active legacy
// worker may not be relabelled as direct: that could steal its write scope.
func resolveQuickItemExecutionMode(status, recorded string, inlineApproved, directRequested bool) (string, error) {
	status = strings.ToLower(strings.TrimSpace(status))
	recorded = strings.ToLower(strings.TrimSpace(recorded))
	if recorded == quickLeaderDirectMode {
		if inlineApproved {
			return "", fmt.Errorf("leader-direct cannot carry inline fallback approval")
		}
		return quickLeaderDirectMode, nil
	}
	if recorded != "" && recorded != "worker" && recorded != "leader-inline" {
		return "", fmt.Errorf("unsupported recorded Quick execution mode")
	}
	if directRequested {
		if recorded != "" || inlineApproved || (status != "pending" && status != "ready") {
			return "", fmt.Errorf("leader-direct must be selected before first start; do not relabel an active or fallback executor")
		}
		return quickLeaderDirectMode, nil
	}
	return "worker", nil
}

// The normal result path still checks status, scope, lane identity, reuse and
// source continuity. Direct execution additionally requires explicit green
// checks and no blockers rather than accepting a prose-only success assertion.
// Input is the canonical map returned by normalizeWorkerTaskResult.
func validateQuickLeaderDirectResult(result map[string]any) error {
	checks, ok := result["validation_results"].([]map[string]string)
	if !ok || len(checks) == 0 {
		return fmt.Errorf("leader-direct result requires non-empty normalized validation_results")
	}
	for _, check := range checks {
		if strings.TrimSpace(check["command"]) == "" || check["status"] != "passed" {
			return fmt.Errorf("leader-direct result requires every validation command to pass")
		}
	}
	blockers, ok := result["blockers"].([]string)
	if !ok || len(blockers) != 0 {
		return fmt.Errorf("leader-direct result requires an empty normalized blockers list")
	}
	return nil
}

func quickItemDispatchContract(capabilityID string) map[string]any {
	if capabilityID != "quick.item-start" {
		return nil
	}
	return map[string]any{
		"schema": quickDispatchSchema,
		"flag":   "--leader-direct", "flag_type": "standalone_boolean",
		"default": "worker", "selected_mode": quickLeaderDirectMode,
		"select_before_first_start": true, "resume_preserves_mode": true,
		"result_submit_required": true, "independent_review_not_waived": true,
		"semantic_risk_owner": "leader; select only a bounded low-risk change with sufficient context and no required independent implementation",
		"usage":               "specify-runtime quick item-start <quick-id> --item Qn --leader-direct [--current-work-id <work-id>] [--current-work-fence <fence>] [--project-root <path>] --format json",
		"result_policy":       "submit the same stage-owned result; all direct validation_results must pass and blockers must be empty; allow-inline cannot bypass direct proof",
		"write_policy":        "wait for the existing execution guard and matching work_claim; requires_worker=false is not write permission",
	}
}

func addQuickItemDispatchContract(capabilityID string, descriptor, item map[string]any) {
	if item == nil {
		return
	}
	if _, exists := item["execution_contract"]; exists {
		return
	}
	if contract, exists := descriptor["execution_contract"]; exists {
		item["execution_contract"] = contract
	} else if contract := quickItemDispatchContract(capabilityID); contract != nil {
		item["execution_contract"] = contract
	}
}

func addQuickHelpDispatchContract(data map[string]any) {
	if data == nil {
		return
	}
	if _, exists := data["execution_contracts"]; exists {
		return
	}
	commands, ok := data["commands"].([]string)
	if !ok {
		return
	}
	for _, command := range commands {
		if command == "item-start" {
			data["execution_contracts"] = map[string]any{"quick.item-start": quickItemDispatchContract("quick.item-start")}
			return
		}
	}
}
