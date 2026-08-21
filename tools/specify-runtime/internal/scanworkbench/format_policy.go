package scanworkbench

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"path/filepath"
	"sort"
	"strings"

	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/scanset"
)

const (
	formatInventoryProtocolV1      = "project_cognition_format_inventory.v1"
	formatPolicyProposalProtocolV1 = "project_cognition_scan_policy_proposal.v1"
	formatPolicyProtocolV1         = "project_cognition_scan_policy.v1"
	formatDetectorVersion          = "format_detector.v1"
	formatInventoryFileName        = "format-inventory.json"
	formatPolicyProposalFileName   = "scan-policy.proposal.json"
	formatPolicyConfirmedFileName  = "scan-policy.confirmed.json"
	formatCohortRepresentativeCap  = 3
	formatPolicyReasonMaxBytes     = 240
)

var formatPolicyDecisions = []string{"semantic_scan", "sample", "inventory_only", "exclude", "split_required"}

type FormatInventoryInput struct {
	ScanSetPath string
}

type FormatCohort struct {
	CohortID            string   `json:"cohort_id"`
	FormatKey           string   `json:"format_key"`
	FileFormat          string   `json:"file_format"`
	FormatFamily        string   `json:"format_family"`
	FormatDetection     string   `json:"format_detection"`
	PathKind            string   `json:"path_kind"`
	DirectoryFamily     string   `json:"directory_family"`
	GitState            string   `json:"git_state"`
	PathCount           int      `json:"path_count"`
	TotalBytes          int64    `json:"total_bytes"`
	RepresentativePaths []string `json:"representative_paths"`
}

type FormatInventoryPayload struct {
	Status           string         `json:"status"`
	Protocol         string         `json:"protocol"`
	DetectorVersion  string         `json:"detector_version"`
	ScanSetPath      string         `json:"scan_set_path"`
	ScanSetDigest    string         `json:"scan_set_digest"`
	InventoryDigest  string         `json:"inventory_digest"`
	PathCount        int            `json:"path_count"`
	CohortCount      int            `json:"cohort_count"`
	Cohorts          []FormatCohort `json:"cohorts"`
	ProposalProtocol string         `json:"proposal_protocol"`
	AllowedDecisions []string       `json:"allowed_decisions"`
	InventoryPath    string         `json:"inventory_path"`
	ReviewRequired   bool           `json:"review_required"`
	NextAction       string         `json:"next_action"`
}

type FormatPolicyDecisionGroup struct {
	CohortIDs []string `json:"cohort_ids"`
	Decision  string   `json:"decision"`
	Reason    string   `json:"reason"`
}

type StageFormatPolicyInput struct {
	Protocol        string                      `json:"protocol"`
	InventoryDigest string                      `json:"inventory_digest"`
	DecisionGroups  []FormatPolicyDecisionGroup `json:"decision_groups"`
}

type FormatPolicyDecisionSummary struct {
	CohortCount int   `json:"cohort_count"`
	PathCount   int   `json:"path_count"`
	TotalBytes  int64 `json:"total_bytes"`
}

type StageFormatPolicyPayload struct {
	Status              string                                 `json:"status"`
	ProposalDigest      string                                 `json:"proposal_digest"`
	InventoryDigest     string                                 `json:"inventory_digest"`
	ProposalPath        string                                 `json:"proposal_path"`
	DecisionSummary     map[string]FormatPolicyDecisionSummary `json:"decision_summary"`
	ReviewRequired      bool                                   `json:"review_required"`
	ConfirmationAllowed bool                                   `json:"confirmation_allowed"`
	NextAction          string                                 `json:"next_action"`
}

type ConfirmFormatPolicyInput struct {
	ProposalDigest string
}

type ConfirmFormatPolicyPayload struct {
	Status          string `json:"status"`
	ProposalDigest  string `json:"proposal_digest"`
	InventoryDigest string `json:"inventory_digest"`
	PolicyDigest    string `json:"policy_digest"`
	PolicyPath      string `json:"policy_path"`
	NextAction      string `json:"next_action"`
}

type stagedFormatPolicy struct {
	Protocol        string                      `json:"protocol"`
	InventoryDigest string                      `json:"inventory_digest"`
	DecisionGroups  []FormatPolicyDecisionGroup `json:"decision_groups"`
	ProposalDigest  string                      `json:"proposal_digest"`
}

type confirmedFormatPolicy struct {
	Protocol        string            `json:"protocol"`
	InventoryDigest string            `json:"inventory_digest"`
	ProposalDigest  string            `json:"proposal_digest"`
	Decisions       map[string]string `json:"decisions"`
	Reasons         map[string]string `json:"reasons"`
	PolicyDigest    string            `json:"policy_digest"`
}

func InventoryFormats(paths rt.Paths, input FormatInventoryInput) (FormatInventoryPayload, error) {
	if err := validateRuntimeControlDir(paths); err != nil {
		return FormatInventoryPayload{}, err
	}
	release, err := acquireWorkbenchLock(paths)
	if err != nil {
		return FormatInventoryPayload{}, err
	}
	defer release()

	inventory, _, err := computeFormatInventory(paths, input.ScanSetPath)
	if err != nil {
		return FormatInventoryPayload{}, err
	}
	if err := writeJSONAtomic(formatInventoryPath(paths), inventory); err != nil {
		return FormatInventoryPayload{}, fmt.Errorf("write format inventory: %w", err)
	}
	return inventory, nil
}

func StageFormatPolicy(paths rt.Paths, input StageFormatPolicyInput) (StageFormatPolicyPayload, error) {
	if err := validateRuntimeControlDir(paths); err != nil {
		return StageFormatPolicyPayload{}, err
	}
	release, err := acquireWorkbenchLock(paths)
	if err != nil {
		return StageFormatPolicyPayload{}, err
	}
	defer release()

	inventory, err := loadCurrentFormatInventory(paths)
	if err != nil {
		return StageFormatPolicyPayload{}, err
	}
	if strings.TrimSpace(input.Protocol) != formatPolicyProposalProtocolV1 {
		return StageFormatPolicyPayload{}, fmt.Errorf("scan policy proposal protocol must be %s", formatPolicyProposalProtocolV1)
	}
	if input.InventoryDigest != inventory.InventoryDigest {
		return StageFormatPolicyPayload{}, fmt.Errorf("scan policy inventory digest does not match current format inventory")
	}

	normalized, decisions, err := normalizeFormatPolicyDecisionGroups(inventory, input.DecisionGroups)
	if err != nil {
		return StageFormatPolicyPayload{}, err
	}
	proposal := stagedFormatPolicy{
		Protocol:        formatPolicyProposalProtocolV1,
		InventoryDigest: inventory.InventoryDigest,
		DecisionGroups:  normalized,
	}
	proposal.ProposalDigest, err = stagedFormatPolicyDigest(proposal)
	if err != nil {
		return StageFormatPolicyPayload{}, err
	}
	if err := writeJSONAtomic(formatPolicyProposalPath(paths), proposal); err != nil {
		return StageFormatPolicyPayload{}, fmt.Errorf("write staged scan policy: %w", err)
	}

	confirmationAllowed := true
	for _, decision := range decisions {
		if decision == "split_required" {
			confirmationAllowed = false
			break
		}
	}
	status := "staged"
	nextAction := "obtain_user_confirmation"
	if !confirmationAllowed {
		status = "needs_refinement"
		nextAction = "refine_format_cohorts_or_policy"
	}
	return StageFormatPolicyPayload{
		Status:              status,
		ProposalDigest:      proposal.ProposalDigest,
		InventoryDigest:     inventory.InventoryDigest,
		ProposalPath:        policyRuntimePath(formatPolicyProposalFileName),
		DecisionSummary:     summarizeFormatPolicyDecisions(inventory, decisions),
		ReviewRequired:      confirmationAllowed,
		ConfirmationAllowed: confirmationAllowed,
		NextAction:          nextAction,
	}, nil
}

func ConfirmFormatPolicy(paths rt.Paths, input ConfirmFormatPolicyInput) (ConfirmFormatPolicyPayload, error) {
	if err := validateRuntimeControlDir(paths); err != nil {
		return ConfirmFormatPolicyPayload{}, err
	}
	release, err := acquireWorkbenchLock(paths)
	if err != nil {
		return ConfirmFormatPolicyPayload{}, err
	}
	defer release()

	var proposal stagedFormatPolicy
	if err := readJSON(formatPolicyProposalPath(paths), &proposal); err != nil {
		return ConfirmFormatPolicyPayload{}, fmt.Errorf("read staged scan policy: %w", err)
	}
	if proposal.Protocol != formatPolicyProposalProtocolV1 {
		return ConfirmFormatPolicyPayload{}, fmt.Errorf("staged scan policy protocol must be %s", formatPolicyProposalProtocolV1)
	}
	proposalDigest, err := stagedFormatPolicyDigest(proposal)
	if err != nil {
		return ConfirmFormatPolicyPayload{}, err
	}
	if proposalDigest != proposal.ProposalDigest {
		return ConfirmFormatPolicyPayload{}, fmt.Errorf("staged scan policy digest does not match its contents")
	}
	if strings.TrimSpace(input.ProposalDigest) == "" || input.ProposalDigest != proposal.ProposalDigest {
		return ConfirmFormatPolicyPayload{}, fmt.Errorf("proposal digest does not match the staged scan policy")
	}
	inventory, err := loadCurrentFormatInventory(paths)
	if err != nil {
		return ConfirmFormatPolicyPayload{}, err
	}
	if proposal.InventoryDigest != inventory.InventoryDigest {
		return ConfirmFormatPolicyPayload{}, fmt.Errorf("format inventory changed after the scan policy proposal was staged")
	}
	normalized, decisions, err := normalizeFormatPolicyDecisionGroups(inventory, proposal.DecisionGroups)
	if err != nil {
		return ConfirmFormatPolicyPayload{}, err
	}
	for _, decision := range decisions {
		if decision == "split_required" {
			return ConfirmFormatPolicyPayload{}, fmt.Errorf("scan policy cannot be confirmed while a cohort decision is split_required")
		}
	}
	reasons := map[string]string{}
	for _, group := range normalized {
		for _, cohortID := range group.CohortIDs {
			reasons[cohortID] = group.Reason
		}
	}
	confirmed := confirmedFormatPolicy{
		Protocol:        formatPolicyProtocolV1,
		InventoryDigest: inventory.InventoryDigest,
		ProposalDigest:  proposal.ProposalDigest,
		Decisions:       decisions,
		Reasons:         reasons,
	}
	confirmed.PolicyDigest, err = confirmedFormatPolicyDigest(confirmed)
	if err != nil {
		return ConfirmFormatPolicyPayload{}, err
	}
	if err := writeJSONAtomic(formatPolicyConfirmedPath(paths), confirmed); err != nil {
		return ConfirmFormatPolicyPayload{}, fmt.Errorf("write confirmed scan policy: %w", err)
	}
	return ConfirmFormatPolicyPayload{
		Status:          "confirmed",
		ProposalDigest:  proposal.ProposalDigest,
		InventoryDigest: inventory.InventoryDigest,
		PolicyDigest:    confirmed.PolicyDigest,
		PolicyPath:      policyRuntimePath(formatPolicyConfirmedFileName),
		NextAction:      "run_scan_prepare",
	}, nil
}

func computeFormatInventory(paths rt.Paths, scanSetPath string) (FormatInventoryPayload, []pathClassification, error) {
	scanSetPath = strings.TrimSpace(scanSetPath)
	if scanSetPath == "" {
		scanSetPath = scanset.DefaultOutputPath
	}
	absScanSet, relScanSet, err := resolveRepositoryFile(paths.Root, scanSetPath)
	if err != nil {
		return FormatInventoryPayload{}, nil, fmt.Errorf("resolve scan set: %w", err)
	}
	var scanSet scanSetFile
	if err := readJSON(absScanSet, &scanSet); err != nil {
		return FormatInventoryPayload{}, nil, fmt.Errorf("read canonical scan set: %w", err)
	}
	files, err := validateScanSetPaths(paths.Root, scanSet.Files)
	if err != nil {
		return FormatInventoryPayload{}, nil, err
	}
	if len(files) == 0 {
		return FormatInventoryPayload{}, nil, fmt.Errorf("canonical scan set contains no files")
	}
	classifications, err := classifyRepositoryPaths(paths.Root, files, false)
	if err != nil {
		return FormatInventoryPayload{}, nil, err
	}
	inventory, err := buildFormatInventory(filepath.ToSlash(relScanSet), files, classifications)
	if err != nil {
		return FormatInventoryPayload{}, nil, err
	}
	return inventory, classifications, nil
}

func buildFormatInventory(scanSetPath string, files []string, classifications []pathClassification) (FormatInventoryPayload, error) {
	type cohortAccumulator struct {
		cohort FormatCohort
	}
	groups := map[string]*cohortAccumulator{}
	for index := range classifications {
		classification := &classifications[index]
		if classification.CohortID == "" {
			classification.CohortID = formatCohortID(*classification)
		}
		key := formatCohortKey(*classification)
		group := groups[key]
		if group == nil {
			group = &cohortAccumulator{cohort: FormatCohort{
				CohortID:        classification.CohortID,
				FormatKey:       classification.FormatKey,
				FileFormat:      classification.FileFormat,
				FormatFamily:    classification.FormatFamily,
				FormatDetection: classification.FormatDetection,
				PathKind:        classification.PathKind,
				DirectoryFamily: classification.DirectoryFamily,
				GitState:        formatGitState(*classification),
			}}
			groups[key] = group
		}
		group.cohort.PathCount++
		group.cohort.TotalBytes += classification.SizeBytes
		if len(group.cohort.RepresentativePaths) < formatCohortRepresentativeCap {
			group.cohort.RepresentativePaths = append(group.cohort.RepresentativePaths, classification.Path)
		}
	}
	keys := make([]string, 0, len(groups))
	for key := range groups {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	cohorts := make([]FormatCohort, 0, len(keys))
	for _, key := range keys {
		cohort := groups[key].cohort
		sort.Strings(cohort.RepresentativePaths)
		cohorts = append(cohorts, cohort)
	}
	scanSetDigest, err := digestJSON(struct {
		Files []string `json:"files"`
	}{Files: files})
	if err != nil {
		return FormatInventoryPayload{}, err
	}
	inventory := FormatInventoryPayload{
		Status:           "ready_for_agent_policy",
		Protocol:         formatInventoryProtocolV1,
		DetectorVersion:  formatDetectorVersion,
		ScanSetPath:      scanSetPath,
		ScanSetDigest:    scanSetDigest,
		PathCount:        len(files),
		CohortCount:      len(cohorts),
		Cohorts:          cohorts,
		ProposalProtocol: formatPolicyProposalProtocolV1,
		AllowedDecisions: append([]string{}, formatPolicyDecisions...),
		InventoryPath:    policyRuntimePath(formatInventoryFileName),
		ReviewRequired:   true,
		NextAction:       "agent_stage_scan_policy",
	}
	inventory.InventoryDigest, err = digestJSON(struct {
		Protocol        string         `json:"protocol"`
		DetectorVersion string         `json:"detector_version"`
		ScanSetPath     string         `json:"scan_set_path"`
		ScanSetDigest   string         `json:"scan_set_digest"`
		PathCount       int            `json:"path_count"`
		Cohorts         []FormatCohort `json:"cohorts"`
	}{inventory.Protocol, inventory.DetectorVersion, inventory.ScanSetPath, inventory.ScanSetDigest, inventory.PathCount, inventory.Cohorts})
	if err != nil {
		return FormatInventoryPayload{}, err
	}
	return inventory, nil
}

func loadCurrentFormatInventory(paths rt.Paths) (FormatInventoryPayload, error) {
	var stored FormatInventoryPayload
	if err := readJSON(formatInventoryPath(paths), &stored); err != nil {
		return FormatInventoryPayload{}, fmt.Errorf("read format inventory: %w", err)
	}
	current, _, err := computeFormatInventory(paths, stored.ScanSetPath)
	if err != nil {
		return FormatInventoryPayload{}, err
	}
	if current.InventoryDigest != stored.InventoryDigest {
		return FormatInventoryPayload{}, fmt.Errorf("format inventory changed; rerun scan-formats before staging or confirming a policy")
	}
	return current, nil
}

func normalizeFormatPolicyDecisionGroups(inventory FormatInventoryPayload, groups []FormatPolicyDecisionGroup) ([]FormatPolicyDecisionGroup, map[string]string, error) {
	known := map[string]bool{}
	for _, cohort := range inventory.Cohorts {
		known[cohort.CohortID] = true
	}
	decisions := map[string]string{}
	normalized := make([]FormatPolicyDecisionGroup, 0, len(groups))
	for _, raw := range groups {
		decision := strings.TrimSpace(raw.Decision)
		if !containsFormatPolicyDecision(decision) {
			return nil, nil, fmt.Errorf("unsupported scan policy decision %q", raw.Decision)
		}
		reason := strings.TrimSpace(raw.Reason)
		if reason == "" {
			return nil, nil, fmt.Errorf("every scan policy decision group requires a reason")
		}
		if len(reason) > formatPolicyReasonMaxBytes || strings.ContainsAny(reason, "\r\n") {
			return nil, nil, fmt.Errorf("scan policy reason must be one line and at most %d bytes", formatPolicyReasonMaxBytes)
		}
		ids := append([]string{}, raw.CohortIDs...)
		if len(ids) == 0 {
			return nil, nil, fmt.Errorf("scan policy decision group requires at least one cohort_id")
		}
		sort.Strings(ids)
		for _, cohortID := range ids {
			if !known[cohortID] {
				return nil, nil, fmt.Errorf("unknown cohort %q in scan policy proposal", cohortID)
			}
			if _, exists := decisions[cohortID]; exists {
				return nil, nil, fmt.Errorf("duplicate cohort %q in scan policy proposal", cohortID)
			}
			decisions[cohortID] = decision
		}
		normalized = append(normalized, FormatPolicyDecisionGroup{CohortIDs: ids, Decision: decision, Reason: reason})
	}
	missing := []string{}
	for cohortID := range known {
		if _, ok := decisions[cohortID]; !ok {
			missing = append(missing, cohortID)
		}
	}
	if len(missing) > 0 {
		sort.Strings(missing)
		return nil, nil, fmt.Errorf("scan policy proposal is missing cohort decisions: %s", strings.Join(missing, ", "))
	}
	sort.Slice(normalized, func(i, j int) bool {
		left := normalized[i].Decision + "\x00" + normalized[i].Reason + "\x00" + strings.Join(normalized[i].CohortIDs, ",")
		right := normalized[j].Decision + "\x00" + normalized[j].Reason + "\x00" + strings.Join(normalized[j].CohortIDs, ",")
		return left < right
	})
	return normalized, decisions, nil
}

func summarizeFormatPolicyDecisions(inventory FormatInventoryPayload, decisions map[string]string) map[string]FormatPolicyDecisionSummary {
	result := map[string]FormatPolicyDecisionSummary{}
	for _, cohort := range inventory.Cohorts {
		decision := decisions[cohort.CohortID]
		summary := result[decision]
		summary.CohortCount++
		summary.PathCount += cohort.PathCount
		summary.TotalBytes += cohort.TotalBytes
		result[decision] = summary
	}
	return result
}

func loadConfirmedFormatPolicy(paths rt.Paths, inventory FormatInventoryPayload) (confirmedFormatPolicy, error) {
	var policy confirmedFormatPolicy
	if err := readJSON(formatPolicyConfirmedPath(paths), &policy); err != nil {
		return confirmedFormatPolicy{}, fmt.Errorf("confirmed scan policy is required before scan-prepare: %w", err)
	}
	if policy.Protocol != formatPolicyProtocolV1 {
		return confirmedFormatPolicy{}, fmt.Errorf("confirmed scan policy protocol must be %s", formatPolicyProtocolV1)
	}
	digest, err := confirmedFormatPolicyDigest(policy)
	if err != nil {
		return confirmedFormatPolicy{}, err
	}
	if digest != policy.PolicyDigest {
		return confirmedFormatPolicy{}, fmt.Errorf("confirmed scan policy digest does not match its contents")
	}
	missing := []string{}
	for _, cohort := range inventory.Cohorts {
		decision, ok := policy.Decisions[cohort.CohortID]
		if !ok || decision == "split_required" || !containsFormatPolicyDecision(decision) {
			missing = append(missing, cohort.CohortID)
		}
	}
	if len(missing) > 0 {
		sort.Strings(missing)
		return confirmedFormatPolicy{}, fmt.Errorf("new format cohorts require Agent review and user confirmation: %s", strings.Join(missing, ", "))
	}
	return policy, nil
}

func applyConfirmedFormatPolicy(classifications []pathClassification, policy confirmedFormatPolicy) error {
	for index := range classifications {
		classification := &classifications[index]
		decision, ok := policy.Decisions[classification.CohortID]
		if !ok {
			return fmt.Errorf("confirmed scan policy is missing cohort %s", classification.CohortID)
		}
		classification.PolicyDecision = decision
		classification.DecisionSource = "confirmed_scan_policy:" + policy.PolicyDigest
		classification.ClassificationReason = "confirmed_format_policy_" + decision
		switch decision {
		case "semantic_scan":
			if classification.ValueTier != "P0" {
				classification.ValueTier = "P1"
			}
			classification.Disposition = "deep_read"
			classification.ScanDecision = "scan"
			if classification.ValueTier == "P0" {
				classification.Criticality = "critical"
			} else {
				classification.Criticality = "important"
			}
			classification.AgentAssist = "semantic_scan"
		case "sample":
			classification.ValueTier = "P2"
			classification.Disposition = "sampled"
			classification.ScanDecision = "sample"
			classification.Criticality = "low_risk"
			if classification.FormatFamily == "doc" {
				classification.AgentAssist = "context_scan"
			} else {
				classification.AgentAssist = "semantic_scan"
			}
		case "inventory_only":
			classification.ValueTier = "P3"
			classification.Disposition = "inventory_only"
			classification.ScanDecision = "inventory_only"
			classification.Criticality = "low_risk"
			classification.AgentAssist = "none"
		case "exclude":
			classification.ValueTier = "P3"
			classification.Disposition = "excluded"
			classification.ScanDecision = "exclude"
			classification.Criticality = "low_risk"
			classification.AgentAssist = "none"
		default:
			return fmt.Errorf("confirmed scan policy decision %q is not executable", decision)
		}
	}
	return nil
}

func confirmedFormatPolicyDigest(policy confirmedFormatPolicy) (string, error) {
	return digestJSON(struct {
		Protocol        string            `json:"protocol"`
		InventoryDigest string            `json:"inventory_digest"`
		ProposalDigest  string            `json:"proposal_digest"`
		Decisions       map[string]string `json:"decisions"`
		Reasons         map[string]string `json:"reasons"`
	}{policy.Protocol, policy.InventoryDigest, policy.ProposalDigest, policy.Decisions, policy.Reasons})
}

func stagedFormatPolicyDigest(policy stagedFormatPolicy) (string, error) {
	return digestJSON(struct {
		Protocol        string                      `json:"protocol"`
		InventoryDigest string                      `json:"inventory_digest"`
		DecisionGroups  []FormatPolicyDecisionGroup `json:"decision_groups"`
	}{policy.Protocol, policy.InventoryDigest, policy.DecisionGroups})
}

func formatCohortKey(classification pathClassification) string {
	return strings.Join([]string{
		classification.FormatKey,
		"family=" + classification.FormatFamily,
		"kind=" + classification.PathKind,
		"directory=" + classification.DirectoryFamily,
		"git=" + formatGitState(classification),
	}, "|")
}

func formatCohortID(classification pathClassification) string {
	sum := sha256.Sum256([]byte(formatCohortKey(classification)))
	return "fmt-" + hex.EncodeToString(sum[:8])
}

func formatGitState(classification pathClassification) string {
	if classification.GitTracked {
		return "tracked"
	}
	if classification.GitIgnored {
		return "ignored_untracked"
	}
	return "untracked"
}

func containsFormatPolicyDecision(value string) bool {
	for _, allowed := range formatPolicyDecisions {
		if value == allowed {
			return true
		}
	}
	return false
}

func digestJSON(value any) (string, error) {
	data, err := json.Marshal(value)
	if err != nil {
		return "", fmt.Errorf("encode digest input: %w", err)
	}
	sum := sha256.Sum256(data)
	return hex.EncodeToString(sum[:]), nil
}

func formatInventoryPath(paths rt.Paths) string {
	return filepath.Join(paths.RuntimeDir, "tmp", formatInventoryFileName)
}

func formatPolicyProposalPath(paths rt.Paths) string {
	return filepath.Join(paths.RuntimeDir, "tmp", formatPolicyProposalFileName)
}

func formatPolicyConfirmedPath(paths rt.Paths) string {
	return filepath.Join(paths.RuntimeDir, "tmp", formatPolicyConfirmedFileName)
}

func policyRuntimePath(name string) string {
	return filepath.ToSlash(filepath.Join(rt.SpecifyDir, rt.CognitionDir, "tmp", name))
}
