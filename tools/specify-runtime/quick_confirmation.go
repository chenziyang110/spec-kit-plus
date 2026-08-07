package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
)

const quickConfirmationSchema = "quick-confirmation-v1"
const quickConfirmationFileName = "confirmation.json"

var quickWorkItemIDPattern = regexp.MustCompile(`^Q[1-9][0-9]*$`)

type quickConfirmationDoc struct {
	Schema              string                 `json:"schema"`
	Workspace           string                 `json:"workspace,omitempty"`
	ConfirmationMode    string                 `json:"confirmation_mode"`
	ConfirmationState   string                 `json:"confirmation_state"`
	ConfirmationDigest  string                 `json:"confirmation_digest"`
	Source              quickConfirmationSource `json:"source"`
	Decision            quickConfirmationDecision `json:"decision"`
	Delivery            quickConfirmationDelivery `json:"delivery"`
	Execution           quickConfirmationExecution `json:"execution,omitempty"`
	StagedAt            string                 `json:"staged_at,omitempty"`
	ConfirmedAt         string                 `json:"confirmed_at,omitempty"`
	UpdatedAt           string                 `json:"updated_at,omitempty"`
}

type quickConfirmationSource struct {
	Kind            string `json:"kind"`
	DiscussionSlug  string `json:"discussion_slug,omitempty"`
	ReviewDigest    string `json:"review_digest,omitempty"`
	SemanticDelta   bool   `json:"semantic_delta"`
	DeltaSummary    string `json:"delta_summary,omitempty"`
}

type quickConfirmationDecision struct {
	Goal                   string                   `json:"goal"`
	UserVisibleResult      string                   `json:"user_visible_result"`
	Scope                  quickConfirmationScope   `json:"scope"`
	Items                  []quickConfirmationItem  `json:"items"`
	RecommendedApproach    string                   `json:"recommended_approach,omitempty"`
	AssumptionsAndRisks    []string                 `json:"assumptions_and_risks,omitempty"`
	CompletionEvidence     []string                 `json:"completion_evidence,omitempty"`
	ReconfirmationTrigger  string                   `json:"reconfirmation_trigger"`
	UIConfirmation         map[string]any           `json:"ui_confirmation,omitempty"`
	UserCorrections        []string                 `json:"user_corrections,omitempty"`
}

type quickConfirmationScope struct {
	Include []string `json:"include"`
	Exclude []string `json:"exclude"`
	Defer   []string `json:"defer,omitempty"`
}

type quickConfirmationItem struct {
	ID          string   `json:"id"`
	Deliverable string   `json:"deliverable"`
	DependsOn   []string `json:"depends_on"`
	Acceptance  string   `json:"acceptance"`
	WriteScope  []string `json:"write_scope,omitempty"`
}

type quickConfirmationDelivery struct {
	Waves            []quickConfirmationWave `json:"waves"`
	JoinPoints       []quickConfirmationJoin `json:"join_points,omitempty"`
	IntegrationGate  string                  `json:"integration_gate,omitempty"`
}

type quickConfirmationWave struct {
	ID       string   `json:"id"`
	ItemIDs  []string `json:"item_ids"`
	Parallel bool     `json:"parallel"`
}

type quickConfirmationJoin struct {
	After []string `json:"after"`
	Starts string  `json:"starts"`
	Gate  string   `json:"gate,omitempty"`
}

type quickConfirmationExecution struct {
	WorkItemStatus []quickWorkItemStatus `json:"work_item_status,omitempty"`
	ActiveItemIDs  []string              `json:"active_item_ids,omitempty"`
	JoinPoint      string                `json:"join_point,omitempty"`
	Blockers       []string              `json:"blockers,omitempty"`
	// BlockedDispatch is the machine-readable leader-inline / subagent-blocked record.
	BlockedDispatch *quickBlockedDispatch `json:"blocked_dispatch,omitempty"`
}

type quickBlockedDispatch struct {
	Status         string `json:"status,omitempty"`          // none | recorded-fallback | subagent-blocked
	Reason         string `json:"reason,omitempty"`
	AttemptedShape string `json:"attempted_shape,omitempty"` // one-subagent | parallel-subagents | none
	ChosenShape    string `json:"chosen_shape,omitempty"`    // leader-inline | subagent-blocked | ...
	ItemID         string `json:"item_id,omitempty"`
	ApprovedAt     string `json:"approved_at,omitempty"`
}

type quickWorkItemStatus struct {
	WorkItemID         string   `json:"work_item_id"`
	Status             string   `json:"status"`
	AcceptanceEvidence []string `json:"acceptance_evidence,omitempty"`
	// RequiresWorker is true after item-start until worker result or allow-inline.
	RequiresWorker bool `json:"requires_worker,omitempty"`
	// WorkerResultID / WorkerResultRef bind accept to a result submit record.
	WorkerResultID  string `json:"worker_result_id,omitempty"`
	WorkerResultRef string `json:"worker_result_ref,omitempty"`
	WorkerLaneID    string `json:"worker_lane_id,omitempty"`
	// ExecutionMode is worker | leader-inline after accept.
	ExecutionMode string `json:"execution_mode,omitempty"`
	// InlineReason is set by allow-inline or item-accept --allow-inline.
	InlineReason   string `json:"inline_reason,omitempty"`
	InlineApproved bool   `json:"inline_approved,omitempty"`
}

func (service quickService) runCheckpoint(mode, quickID string, args []string) (Envelope, error) {
	root, err := service.root()
	if err != nil {
		return Envelope{}, err
	}
	tasks, err := service.scan(root)
	if err != nil {
		return Envelope{}, err
	}
	task, err := matchQuickTask(tasks, quickID)
	if err != nil {
		return Envelope{}, err
	}
	workspacePath := stringValue(task["workspace_path"])
	workspace := stringValue(task["workspace"])

	switch strings.ToLower(strings.TrimSpace(mode)) {
	case "checkpoint-stage":
		input, err := readAgentJSONObject(args, service.projectRoot, "quick checkpoint-stage")
		if err != nil {
			return Envelope{}, err
		}
		deliveryOnly := hasFlag(args, "--delivery-only")
		doc, err := service.stageCheckpoint(workspacePath, workspace, input, deliveryOnly)
		if err != nil {
			return Envelope{}, err
		}
		env := NewEnvelope("ok", "quick checkpoint staged")
		env.Data = map[string]any{
			"task":                 task,
			"confirmation":         doc,
			"confirmation_digest":  doc.ConfirmationDigest,
			"confirmation_state":   doc.ConfirmationState,
			"confirmation_mode":    doc.ConfirmationMode,
			"requires_user_confirm": doc.ConfirmationState == "staged",
			"views": map[string]string{
				"decision": renderQuickDecisionView(doc),
				"delivery": renderQuickDeliveryView(doc),
				"pulse":    renderQuickPulseView(doc),
			},
			"confirmation_path": filepath.ToSlash(filepath.Join(".planning", "quick", workspace, quickConfirmationFileName)),
		}
		return env, nil
	case "checkpoint-confirm":
		digest := firstNonEmpty(optionValue(args, "--digest", ""), positionalArg(args, 2, ""))
		if strings.TrimSpace(digest) == "" {
			return Envelope{}, fmt.Errorf("checkpoint-confirm requires --digest")
		}
		doc, err := service.confirmCheckpoint(workspacePath, workspace, digest)
		if err != nil {
			return Envelope{}, err
		}
		env := NewEnvelope("ok", "quick checkpoint confirmed")
		env.Data = map[string]any{
			"task":                task,
			"confirmation":        doc,
			"confirmation_digest": doc.ConfirmationDigest,
			"confirmation_state":  doc.ConfirmationState,
			"views": map[string]string{
				"decision": renderQuickDecisionView(doc),
				"delivery": renderQuickDeliveryView(doc),
				"pulse":    renderQuickPulseView(doc),
			},
		}
		return env, nil
	case "checkpoint-show":
		view := strings.ToLower(strings.TrimSpace(firstNonEmpty(optionValue(args, "--view", ""), "decision")))
		doc, err := service.loadConfirmation(workspacePath)
		if err != nil {
			return Envelope{}, err
		}
		text, err := renderQuickConfirmationView(doc, view)
		if err != nil {
			return Envelope{}, err
		}
		env := NewEnvelope("ok", "quick checkpoint view")
		env.Data = map[string]any{
			"task":                task,
			"view":                view,
			"text":                text,
			"confirmation":        doc,
			"confirmation_digest": doc.ConfirmationDigest,
			"confirmation_state":  doc.ConfirmationState,
		}
		return env, nil
	default:
		return Envelope{}, fmt.Errorf("unknown checkpoint mode: %s", mode)
	}
}

func (service quickService) stageCheckpoint(workspacePath, workspace string, input map[string]any, deliveryOnly bool) (*quickConfirmationDoc, error) {
	existing, _ := service.loadConfirmation(workspacePath)
	doc, err := normalizeQuickConfirmationInput(input, workspace, existing, deliveryOnly)
	if err != nil {
		return nil, err
	}
	if err := validateQuickConfirmation(doc); err != nil {
		return nil, err
	}
	digest, err := computeQuickConfirmationDigest(doc.Decision)
	if err != nil {
		return nil, err
	}
	doc.ConfirmationDigest = digest
	ts := nowUTCString()
	doc.StagedAt = ts
	doc.UpdatedAt = ts

	if deliveryOnly {
		if existing == nil || existing.ConfirmationState != "confirmed" && existing.ConfirmationState != "inherited" {
			return nil, fmt.Errorf("--delivery-only requires an already confirmed checkpoint")
		}
		if existing.ConfirmationDigest != digest {
			return nil, fmt.Errorf("--delivery-only cannot change decision fields; decision digest changed")
		}
		doc.ConfirmationState = existing.ConfirmationState
		doc.ConfirmationMode = existing.ConfirmationMode
		doc.ConfirmedAt = existing.ConfirmedAt
		doc.Source = existing.Source
	} else {
		mode, state, err := deriveQuickConfirmationMode(doc)
		if err != nil {
			return nil, err
		}
		doc.ConfirmationMode = mode
		doc.ConfirmationState = state
		if state == "inherited" || state == "confirmed" {
			doc.ConfirmedAt = ts
		} else {
			doc.ConfirmedAt = ""
		}
	}

	if err := service.persistConfirmation(workspacePath, doc); err != nil {
		return nil, err
	}
	if err := service.projectConfirmationIntoStatus(workspacePath, doc); err != nil {
		return nil, err
	}
	return doc, nil
}

func (service quickService) confirmCheckpoint(workspacePath, workspace, digest string) (*quickConfirmationDoc, error) {
	doc, err := service.loadConfirmation(workspacePath)
	if err != nil {
		return nil, err
	}
	expected := strings.TrimSpace(digest)
	if expected == "" {
		return nil, fmt.Errorf("confirmation digest is required")
	}
	if doc.ConfirmationDigest != expected {
		return nil, fmt.Errorf("confirmation digest mismatch: expected %s", doc.ConfirmationDigest)
	}
	if doc.ConfirmationState == "confirmed" || doc.ConfirmationState == "inherited" {
		return doc, nil
	}
	if doc.ConfirmationState != "staged" {
		return nil, fmt.Errorf("checkpoint is not staged for confirmation")
	}
	ts := nowUTCString()
	doc.ConfirmationState = "confirmed"
	doc.ConfirmedAt = ts
	doc.UpdatedAt = ts
	doc.Workspace = workspace
	if err := service.persistConfirmation(workspacePath, doc); err != nil {
		return nil, err
	}
	if err := service.projectConfirmationIntoStatus(workspacePath, doc); err != nil {
		return nil, err
	}
	return doc, nil
}

func (service quickService) loadConfirmation(workspacePath string) (*quickConfirmationDoc, error) {
	path := filepath.Join(workspacePath, quickConfirmationFileName)
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("quick confirmation not found; run checkpoint-stage first")
	}
	var doc quickConfirmationDoc
	if err := json.Unmarshal(raw, &doc); err != nil {
		return nil, fmt.Errorf("quick confirmation is invalid JSON: %w", err)
	}
	if doc.Schema != quickConfirmationSchema {
		return nil, fmt.Errorf("unsupported confirmation schema %q", doc.Schema)
	}
	return &doc, nil
}

func (service quickService) persistConfirmation(workspacePath string, doc *quickConfirmationDoc) error {
	path := filepath.Join(workspacePath, quickConfirmationFileName)
	return writeScriptJSONFile(path, doc)
}

func normalizeQuickConfirmationInput(input map[string]any, workspace string, existing *quickConfirmationDoc, deliveryOnly bool) (*quickConfirmationDoc, error) {
	doc := &quickConfirmationDoc{
		Schema:    quickConfirmationSchema,
		Workspace: workspace,
	}

	if deliveryOnly {
		if existing == nil {
			return nil, fmt.Errorf("no existing confirmation to update")
		}
		*doc = *existing
		if deliveryRaw, ok := input["delivery"].(map[string]any); ok {
			delivery, err := parseQuickDelivery(deliveryRaw)
			if err != nil {
				return nil, err
			}
			doc.Delivery = delivery
		} else if len(input) > 0 {
			// allow top-level wave payload
			if _, hasWaves := input["waves"]; hasWaves {
				delivery, err := parseQuickDelivery(input)
				if err != nil {
					return nil, err
				}
				doc.Delivery = delivery
			}
		}
		if executionRaw, ok := input["execution"].(map[string]any); ok {
			doc.Execution = parseQuickExecution(executionRaw)
		}
		if len(doc.Delivery.Waves) == 0 {
			doc.Delivery = deriveQuickDeliveryWaves(doc.Decision.Items)
		}
		return doc, nil
	}

	sourceRaw := mapValue(input["source"])
	doc.Source = quickConfirmationSource{
		Kind:           firstNonEmpty(stringValue(sourceRaw["kind"]), "prompt"),
		DiscussionSlug: stringValue(sourceRaw["discussion_slug"]),
		ReviewDigest:   stringValue(sourceRaw["review_digest"]),
		SemanticDelta:  quickBool(sourceRaw["semantic_delta"]),
		DeltaSummary:   stringValue(sourceRaw["delta_summary"]),
	}

	decisionRaw := mapValue(input["decision"])
	if decisionRaw == nil {
		// allow flat decision fields at top level for compact agent input
		decisionRaw = input
	}
	decision, err := parseQuickDecision(decisionRaw)
	if err != nil {
		return nil, err
	}
	doc.Decision = decision

	if deliveryRaw, ok := input["delivery"].(map[string]any); ok {
		delivery, err := parseQuickDelivery(deliveryRaw)
		if err != nil {
			return nil, err
		}
		doc.Delivery = delivery
	}
	if len(doc.Delivery.Waves) == 0 {
		doc.Delivery = deriveQuickDeliveryWaves(doc.Decision.Items)
	}
	if executionRaw, ok := input["execution"].(map[string]any); ok {
		doc.Execution = parseQuickExecution(executionRaw)
	} else {
		doc.Execution = defaultQuickExecution(doc.Decision.Items)
	}
	return doc, nil
}

func parseQuickDecision(raw map[string]any) (quickConfirmationDecision, error) {
	scopeRaw := mapValue(raw["scope"])
	itemsRaw, ok := raw["items"].([]any)
	if !ok || len(itemsRaw) == 0 {
		// compatibility: ordered_work_items + work_item_acceptance
		if ordered, hasOrdered := raw["ordered_work_items"].([]any); hasOrdered {
			itemsRaw = ordered
			ok = true
		}
	}
	if !ok || len(itemsRaw) == 0 {
		return quickConfirmationDecision{}, fmt.Errorf("decision.items must be a non-empty array")
	}
	acceptanceByID := map[string]string{}
	if acceptanceRows, ok := raw["work_item_acceptance"].([]any); ok {
		for _, row := range acceptanceRows {
			entry := mapValue(row)
			id := firstNonEmpty(stringValue(entry["work_item_id"]), stringValue(entry["id"]))
			acceptanceByID[id] = firstNonEmpty(stringValue(entry["observable_result"]), stringValue(entry["acceptance"]), strings.Join(quickStringSlice(entry["evidence"]), "; "))
		}
	}
	items := make([]quickConfirmationItem, 0, len(itemsRaw))
	for _, row := range itemsRaw {
		entry := mapValue(row)
		id := strings.TrimSpace(stringValue(entry["id"]))
		item := quickConfirmationItem{
			ID:          id,
			Deliverable: firstNonEmpty(stringValue(entry["deliverable"]), stringValue(entry["title"])),
			DependsOn:   quickStringSlice(entry["depends_on"]),
			Acceptance:  firstNonEmpty(stringValue(entry["acceptance"]), acceptanceByID[id]),
			WriteScope:  quickStringSlice(entry["write_scope"]),
		}
		items = append(items, item)
	}
	ui := mapValue(raw["ui_confirmation"])
	if ui != nil && quickBool(ui["applicable"]) == false && len(ui) <= 2 {
		ui = nil
	}
	return quickConfirmationDecision{
		Goal:                  firstNonEmpty(stringValue(raw["goal"]), stringValue(raw["request_and_outcome"])),
		UserVisibleResult:     stringValue(raw["user_visible_result"]),
		Scope: quickConfirmationScope{
			Include: quickStringSlice(scopeRaw["include"]),
			Exclude: quickStringSlice(scopeRaw["exclude"]),
			Defer:   quickStringSlice(scopeRaw["defer"]),
		},
		Items:                 items,
		RecommendedApproach:   stringValue(raw["recommended_approach"]),
		AssumptionsAndRisks:   quickStringSlice(raw["assumptions_and_risks"]),
		CompletionEvidence:    quickStringSlice(raw["completion_evidence"]),
		ReconfirmationTrigger: stringValue(raw["reconfirmation_trigger"]),
		UIConfirmation:        ui,
		UserCorrections:       quickStringSlice(raw["user_corrections"]),
	}, nil
}

func parseQuickDelivery(raw map[string]any) (quickConfirmationDelivery, error) {
	wavesRaw, _ := raw["waves"].([]any)
	waves := make([]quickConfirmationWave, 0, len(wavesRaw))
	for i, row := range wavesRaw {
		entry := mapValue(row)
		id := firstNonEmpty(stringValue(entry["id"]), fmt.Sprintf("W%d", i+1))
		itemIDs := quickStringSlice(entry["item_ids"])
		if len(itemIDs) == 0 {
			itemIDs = quickStringSlice(entry["items"])
		}
		waves = append(waves, quickConfirmationWave{
			ID:       id,
			ItemIDs:  itemIDs,
			Parallel: quickBool(entry["parallel"]) || len(itemIDs) > 1,
		})
	}
	joinsRaw, _ := raw["join_points"].([]any)
	joins := make([]quickConfirmationJoin, 0, len(joinsRaw))
	for _, row := range joinsRaw {
		entry := mapValue(row)
		joins = append(joins, quickConfirmationJoin{
			After:  quickStringSlice(entry["after"]),
			Starts: stringValue(entry["starts"]),
			Gate:   stringValue(entry["gate"]),
		})
	}
	return quickConfirmationDelivery{
		Waves:           waves,
		JoinPoints:      joins,
		IntegrationGate: stringValue(raw["integration_gate"]),
	}, nil
}

func parseQuickExecution(raw map[string]any) quickConfirmationExecution {
	rows, _ := raw["work_item_status"].([]any)
	statuses := make([]quickWorkItemStatus, 0, len(rows))
	for _, row := range rows {
		entry := mapValue(row)
		statuses = append(statuses, quickWorkItemStatus{
			WorkItemID:         firstNonEmpty(stringValue(entry["work_item_id"]), stringValue(entry["id"])),
			Status:             firstNonEmpty(stringValue(entry["status"]), "pending"),
			AcceptanceEvidence: quickStringSlice(entry["acceptance_evidence"]),
		})
	}
	return quickConfirmationExecution{
		WorkItemStatus: statuses,
		ActiveItemIDs:  quickStringSlice(raw["active_item_ids"]),
		JoinPoint:      stringValue(raw["join_point"]),
		Blockers:       quickStringSlice(raw["blockers"]),
	}
}

func defaultQuickExecution(items []quickConfirmationItem) quickConfirmationExecution {
	statuses := make([]quickWorkItemStatus, 0, len(items))
	for _, item := range items {
		statuses = append(statuses, quickWorkItemStatus{WorkItemID: item.ID, Status: "pending"})
	}
	return quickConfirmationExecution{WorkItemStatus: statuses}
}

func deriveQuickDeliveryWaves(items []quickConfirmationItem) quickConfirmationDelivery {
	remaining := map[string]quickConfirmationItem{}
	deps := map[string][]string{}
	for _, item := range items {
		remaining[item.ID] = item
		deps[item.ID] = append([]string{}, item.DependsOn...)
	}
	accepted := map[string]bool{}
	waves := []quickConfirmationWave{}
	waveNum := 1
	for len(remaining) > 0 {
		ready := []string{}
		for id, item := range remaining {
			ok := true
			for _, dep := range item.DependsOn {
				if !accepted[dep] {
					ok = false
					break
				}
			}
			if ok {
				ready = append(ready, id)
			}
		}
		if len(ready) == 0 {
			// cycle or missing deps already validated elsewhere; dump rest
			for id := range remaining {
				ready = append(ready, id)
			}
		}
		sort.Strings(ready)
		wave := quickConfirmationWave{
			ID:       fmt.Sprintf("W%d", waveNum),
			ItemIDs:  ready,
			Parallel: len(ready) > 1,
		}
		waves = append(waves, wave)
		for _, id := range ready {
			accepted[id] = true
			delete(remaining, id)
		}
		waveNum++
	}
	joins := []quickConfirmationJoin{}
	for i := 0; i+1 < len(waves); i++ {
		joins = append(joins, quickConfirmationJoin{
			After:  append([]string{}, waves[i].ItemIDs...),
			Starts: waves[i+1].ID,
			Gate:   fmt.Sprintf("%s acceptance evidence", strings.Join(waves[i].ItemIDs, ", ")),
		})
	}
	return quickConfirmationDelivery{
		Waves:           waves,
		JoinPoints:      joins,
		IntegrationGate: "all work-item acceptance evidence plus overall completion evidence",
	}
}

func deriveQuickConfirmationMode(doc *quickConfirmationDoc) (mode, state string, err error) {
	source := strings.ToLower(strings.TrimSpace(doc.Source.Kind))
	switch source {
	case "discussion":
		if strings.TrimSpace(doc.Source.ReviewDigest) == "" {
			return "", "", fmt.Errorf("discussion source requires review_digest")
		}
		if !doc.Source.SemanticDelta {
			return "inherited", "inherited", nil
		}
		return "delta", "staged", nil
	case "delta":
		return "delta", "staged", nil
	case "prompt", "":
		return "full", "staged", nil
	default:
		return "", "", fmt.Errorf("unsupported source.kind %q", doc.Source.Kind)
	}
}

func validateQuickConfirmation(doc *quickConfirmationDoc) error {
	if strings.TrimSpace(doc.Decision.Goal) == "" {
		return fmt.Errorf("decision.goal is required")
	}
	if strings.TrimSpace(doc.Decision.UserVisibleResult) == "" {
		return fmt.Errorf("decision.user_visible_result is required")
	}
	if len(doc.Decision.Scope.Include) == 0 {
		return fmt.Errorf("decision.scope.include must not be empty")
	}
	if strings.TrimSpace(doc.Decision.ReconfirmationTrigger) == "" {
		return fmt.Errorf("decision.reconfirmation_trigger is required")
	}
	if len(doc.Decision.Items) == 0 {
		return fmt.Errorf("decision.items must not be empty")
	}

	seen := map[string]bool{}
	itemByID := map[string]quickConfirmationItem{}
	for _, item := range doc.Decision.Items {
		id := strings.TrimSpace(item.ID)
		if !quickWorkItemIDPattern.MatchString(id) {
			return fmt.Errorf("work item id %q must match Q1, Q2, ...", item.ID)
		}
		if seen[id] {
			return fmt.Errorf("duplicate work item id %s", id)
		}
		seen[id] = true
		if strings.TrimSpace(item.Deliverable) == "" {
			return fmt.Errorf("%s deliverable is required", id)
		}
		if strings.TrimSpace(item.Acceptance) == "" {
			return fmt.Errorf("%s acceptance is required", id)
		}
		itemByID[id] = item
	}
	for _, item := range doc.Decision.Items {
		for _, dep := range item.DependsOn {
			if !seen[dep] {
				return fmt.Errorf("%s depends on missing item %s", item.ID, dep)
			}
			if dep == item.ID {
				return fmt.Errorf("%s cannot depend on itself", item.ID)
			}
		}
	}
	if err := validateQuickDependencyDAG(doc.Decision.Items); err != nil {
		return err
	}

	if len(doc.Delivery.Waves) == 0 {
		return fmt.Errorf("delivery.waves must not be empty")
	}
	covered := map[string]string{}
	for _, wave := range doc.Delivery.Waves {
		if strings.TrimSpace(wave.ID) == "" {
			return fmt.Errorf("delivery wave id is required")
		}
		if len(wave.ItemIDs) == 0 {
			return fmt.Errorf("delivery wave %s has no items", wave.ID)
		}
		for _, id := range wave.ItemIDs {
			if !seen[id] {
				return fmt.Errorf("delivery wave %s references unknown item %s", wave.ID, id)
			}
			if prev, ok := covered[id]; ok {
				return fmt.Errorf("item %s appears in multiple waves (%s and %s)", id, prev, wave.ID)
			}
			covered[id] = wave.ID
		}
		if wave.Parallel || len(wave.ItemIDs) > 1 {
			if err := validateQuickParallelWriteScopes(wave, itemByID); err != nil {
				return err
			}
		}
	}
	for id := range seen {
		if _, ok := covered[id]; !ok {
			return fmt.Errorf("item %s is not assigned to any delivery wave", id)
		}
	}

	if ui := doc.Decision.UIConfirmation; ui != nil {
		if applicable, exists := ui["applicable"]; exists && !quickBool(applicable) {
			// explicitly not applicable
		} else {
			for _, field := range []string{"confirmation_purpose", "user_and_primary_job", "target_experience", "acceptance_evidence"} {
				if field == "acceptance_evidence" {
					if len(quickStringSlice(ui[field])) == 0 && strings.TrimSpace(stringValue(ui[field])) == "" {
						return fmt.Errorf("ui_confirmation.%s is required when UI confirmation is present", field)
					}
					continue
				}
				if strings.TrimSpace(stringValue(ui[field])) == "" {
					return fmt.Errorf("ui_confirmation.%s is required when UI confirmation is present", field)
				}
			}
		}
	}
	return nil
}

func validateQuickDependencyDAG(items []quickConfirmationItem) error {
	deps := map[string][]string{}
	for _, item := range items {
		deps[item.ID] = append([]string{}, item.DependsOn...)
	}
	state := map[string]int{} // 0=unseen 1=visiting 2=done
	var visit func(string) error
	visit = func(id string) error {
		switch state[id] {
		case 1:
			return fmt.Errorf("dependency cycle detected at %s", id)
		case 2:
			return nil
		}
		state[id] = 1
		for _, dep := range deps[id] {
			if err := visit(dep); err != nil {
				return err
			}
		}
		state[id] = 2
		return nil
	}
	ids := make([]string, 0, len(items))
	for _, item := range items {
		ids = append(ids, item.ID)
	}
	sort.Strings(ids)
	for _, id := range ids {
		if err := visit(id); err != nil {
			return err
		}
	}
	return nil
}

func validateQuickParallelWriteScopes(wave quickConfirmationWave, items map[string]quickConfirmationItem) error {
	seenPaths := map[string]string{}
	for _, id := range wave.ItemIDs {
		item := items[id]
		for _, path := range item.WriteScope {
			key := filepath.ToSlash(strings.TrimSpace(path))
			if key == "" {
				continue
			}
			if owner, ok := seenPaths[key]; ok && owner != id {
				return fmt.Errorf("parallel wave %s has write-scope conflict on %s between %s and %s", wave.ID, key, owner, id)
			}
			seenPaths[key] = id
		}
	}
	return nil
}

func computeQuickConfirmationDigest(decision quickConfirmationDecision) (string, error) {
	// Digest only user-owned decision fields. Delivery/execution never enter the digest.
	protected := map[string]any{
		"schema":              quickConfirmationSchema,
		"goal":                decision.Goal,
		"user_visible_result": decision.UserVisibleResult,
		"scope": map[string]any{
			"include": append([]string{}, decision.Scope.Include...),
			"exclude": append([]string{}, decision.Scope.Exclude...),
			"defer":   append([]string{}, decision.Scope.Defer...),
		},
		"items":                  normalizeQuickItemsForDigest(decision.Items),
		"recommended_approach":   decision.RecommendedApproach,
		"assumptions_and_risks":  append([]string{}, decision.AssumptionsAndRisks...),
		"completion_evidence":    append([]string{}, decision.CompletionEvidence...),
		"reconfirmation_trigger": decision.ReconfirmationTrigger,
		"ui_confirmation":        decision.UIConfirmation,
	}
	raw, err := stableMarshalJSON(protected)
	if err != nil {
		return "", err
	}
	sum := sha256.Sum256(raw)
	return hex.EncodeToString(sum[:]), nil
}

func normalizeQuickItemsForDigest(items []quickConfirmationItem) []any {
	out := make([]any, 0, len(items))
	sorted := append([]quickConfirmationItem{}, items...)
	sort.Slice(sorted, func(i, j int) bool { return sorted[i].ID < sorted[j].ID })
	for _, item := range sorted {
		deps := append([]string{}, item.DependsOn...)
		sort.Strings(deps)
		out = append(out, map[string]any{
			"id":          item.ID,
			"deliverable": item.Deliverable,
			"depends_on":  deps,
			"acceptance":  item.Acceptance,
			// write_scope is execution-facing and excluded from digest
		})
	}
	return out
}

func stableMarshalJSON(value any) ([]byte, error) {
	switch typed := value.(type) {
	case map[string]any:
		keys := make([]string, 0, len(typed))
		for key := range typed {
			keys = append(keys, key)
		}
		sort.Strings(keys)
		var b strings.Builder
		b.WriteByte('{')
		for i, key := range keys {
			if i > 0 {
				b.WriteByte(',')
			}
			keyRaw, err := json.Marshal(key)
			if err != nil {
				return nil, err
			}
			valRaw, err := stableMarshalJSON(typed[key])
			if err != nil {
				return nil, err
			}
			b.Write(keyRaw)
			b.WriteByte(':')
			b.Write(valRaw)
		}
		b.WriteByte('}')
		return []byte(b.String()), nil
	case []any:
		var b strings.Builder
		b.WriteByte('[')
		for i, item := range typed {
			if i > 0 {
				b.WriteByte(',')
			}
			itemRaw, err := stableMarshalJSON(item)
			if err != nil {
				return nil, err
			}
			b.Write(itemRaw)
		}
		b.WriteByte(']')
		return []byte(b.String()), nil
	case []string:
		out := make([]any, 0, len(typed))
		for _, item := range typed {
			out = append(out, item)
		}
		return stableMarshalJSON(out)
	case nil:
		return []byte("null"), nil
	default:
		return json.Marshal(typed)
	}
}

func renderQuickConfirmationView(doc *quickConfirmationDoc, view string) (string, error) {
	switch strings.ToLower(strings.TrimSpace(view)) {
	case "decision":
		return renderQuickDecisionView(doc), nil
	case "delivery":
		return renderQuickDeliveryView(doc), nil
	case "pulse":
		return renderQuickPulseView(doc), nil
	default:
		return "", fmt.Errorf("unsupported view %q (use decision|delivery|pulse)", view)
	}
}

func renderQuickDecisionView(doc *quickConfirmationDoc) string {
	var b strings.Builder
	b.WriteString("## Quick Delivery Checkpoint\n\n")
	sourceLabel := doc.Source.Kind
	if doc.Source.Kind == "discussion" && doc.Source.DiscussionSlug != "" {
		sourceLabel = "discussion/" + doc.Source.DiscussionSlug
	}
	bindState := "待确认"
	semantic := "有变更"
	handling := "需要用户确认后执行"
	switch doc.ConfirmationState {
	case "inherited":
		bindState = "已继承确认"
		semantic = "无"
		handling = "无需重复确认，直接进入执行"
	case "confirmed":
		bindState = "已确认"
		if doc.ConfirmationMode == "delta" {
			semantic = firstNonEmpty(doc.Source.DeltaSummary, "局部变更已确认")
		} else {
			semantic = "无"
		}
		handling = "已确认，可执行"
	case "staged":
		if doc.ConfirmationMode == "delta" {
			bindState = "待确认变更"
			semantic = firstNonEmpty(doc.Source.DeltaSummary, "存在语义变更")
			handling = "只确认变更项"
		} else {
			bindState = "待确认"
			semantic = "新请求"
			handling = "展示完整 Decision Checkpoint，确认一次"
		}
	}
	b.WriteString(fmt.Sprintf("来源：%s\n", sourceLabel))
	b.WriteString(fmt.Sprintf("绑定状态：%s\n", bindState))
	b.WriteString(fmt.Sprintf("语义变化：%s\n", semantic))
	b.WriteString(fmt.Sprintf("处理方式：%s\n\n", handling))
	if doc.ConfirmationDigest != "" {
		b.WriteString(fmt.Sprintf("confirmation_digest: %s\n\n", doc.ConfirmationDigest))
	}
	b.WriteString(fmt.Sprintf("目标：%s\n\n", doc.Decision.Goal))
	b.WriteString(fmt.Sprintf("可见结果：%s\n\n", doc.Decision.UserVisibleResult))
	b.WriteString(fmt.Sprintf("范围：包含 %s；排除 %s", joinOrDash(doc.Decision.Scope.Include), joinOrDash(doc.Decision.Scope.Exclude)))
	if len(doc.Decision.Scope.Defer) > 0 {
		b.WriteString(fmt.Sprintf("；延期 %s", joinOrDash(doc.Decision.Scope.Defer)))
	}
	b.WriteString("\n\n")
	b.WriteString(" ID     交付结果                          依赖              独立验收门槛\n")
	b.WriteString("━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
	for i, item := range doc.Decision.Items {
		deps := "—"
		if len(item.DependsOn) > 0 {
			deps = strings.Join(item.DependsOn, "、")
		}
		b.WriteString(fmt.Sprintf(" %-5s  %-33s  %-16s  %s\n", item.ID, truncateRunes(item.Deliverable, 33), truncateRunes(deps, 16), item.Acceptance))
		if i+1 < len(doc.Decision.Items) {
			b.WriteString("─────  ─────────────────────────────────  ────────────────  ───────────────────────────────\n")
		}
	}
	if doc.Decision.RecommendedApproach != "" {
		b.WriteString(fmt.Sprintf("\n推荐路径：%s\n", doc.Decision.RecommendedApproach))
	}
	if len(doc.Decision.AssumptionsAndRisks) > 0 {
		b.WriteString(fmt.Sprintf("假设与风险：%s\n", strings.Join(doc.Decision.AssumptionsAndRisks, "；")))
	}
	if len(doc.Decision.CompletionEvidence) > 0 {
		b.WriteString(fmt.Sprintf("完成证据：%s\n", strings.Join(doc.Decision.CompletionEvidence, "；")))
	}
	b.WriteString(fmt.Sprintf("重新确认触发：%s\n", doc.Decision.ReconfirmationTrigger))
	if doc.ConfirmationState == "staged" {
		b.WriteString("\n回复：确认全部 / 修改 Qn 验收 / 调整依赖 / 调整范围\n")
	}
	return b.String()
}

func renderQuickDeliveryView(doc *quickConfirmationDoc) string {
	var b strings.Builder
	b.WriteString("## Delivery Map\n\n")
	itemLabel := map[string]string{}
	for _, item := range doc.Decision.Items {
		itemLabel[item.ID] = item.Deliverable
	}
	for _, wave := range doc.Delivery.Waves {
		b.WriteString(fmt.Sprintf("%s\n", wave.ID))
		if len(wave.ItemIDs) == 1 {
			id := wave.ItemIDs[0]
			b.WriteString(fmt.Sprintf("└─ %s %s\n\n", id, itemLabel[id]))
			continue
		}
		for i, id := range wave.ItemIDs {
			branch := "├─"
			suffix := ""
			if i+1 == len(wave.ItemIDs) {
				branch = "└─"
				if wave.Parallel {
					suffix = "  ┘ 并行"
				}
			} else if wave.Parallel && i == 0 {
				suffix = "  ┐"
			} else if wave.Parallel {
				suffix = "  │"
			}
			b.WriteString(fmt.Sprintf("%s %s %s%s\n", branch, id, itemLabel[id], suffix))
		}
		b.WriteString("\n")
	}
	if len(doc.Delivery.JoinPoints) > 0 {
		b.WriteString("Join points:\n")
		for _, join := range doc.Delivery.JoinPoints {
			gate := join.Gate
			if gate == "" {
				gate = "prerequisite acceptance"
			}
			b.WriteString(fmt.Sprintf("- after %s → start %s (%s)\n", strings.Join(join.After, ", "), join.Starts, gate))
		}
		b.WriteString("\n")
	}
	if doc.Delivery.IntegrationGate != "" {
		b.WriteString(fmt.Sprintf("最终集成门槛：%s\n", doc.Delivery.IntegrationGate))
	}
	b.WriteString("\n（Delivery Map 为 Agent 执行投影，不要求用户确认；仅调整 wave/batch/subagent 不触发重新确认。）\n")
	return b.String()
}

func renderQuickPulseView(doc *quickConfirmationDoc) string {
	var b strings.Builder
	b.WriteString("## Delivery Pulse\n\n")
	switch doc.ConfirmationState {
	case "inherited":
		b.WriteString("✓ Checkpoint 已继承\n")
	case "confirmed":
		b.WriteString("✓ Checkpoint 已确认\n")
	default:
		b.WriteString("• Checkpoint 待确认\n")
	}

	statusByID := map[string]quickWorkItemStatus{}
	for _, row := range doc.Execution.WorkItemStatus {
		statusByID[row.WorkItemID] = row
	}
	for _, item := range doc.Decision.Items {
		row, ok := statusByID[item.ID]
		if !ok {
			row = quickWorkItemStatus{WorkItemID: item.ID, Status: "pending"}
		}
		label := item.Deliverable
		switch strings.ToLower(row.Status) {
		case "in_progress", "active":
			b.WriteString(fmt.Sprintf("→ %s %s 正在执行\n", item.ID, label))
		case "accepted", "done", "completed":
			b.WriteString(fmt.Sprintf("✓ %s %s 已验收\n", item.ID, label))
		case "blocked":
			b.WriteString(fmt.Sprintf("✕ %s %s 阻塞\n", item.ID, label))
		default:
			waiting := unmetQuickDeps(item.DependsOn, statusByID)
			if len(waiting) > 0 {
				b.WriteString(fmt.Sprintf("⏸ %s %s 等待 %s\n", item.ID, label, strings.Join(waiting, "、")))
			} else if quickContains(doc.Execution.ActiveItemIDs, item.ID) {
				b.WriteString(fmt.Sprintf("→ %s %s 正在执行\n", item.ID, label))
			} else {
				b.WriteString(fmt.Sprintf("· %s %s 就绪\n", item.ID, label))
			}
		}
	}
	if doc.Execution.JoinPoint != "" {
		b.WriteString(fmt.Sprintf("\nJoin point：%s\n", doc.Execution.JoinPoint))
	} else if len(doc.Delivery.JoinPoints) > 0 {
		// derive next join from first incomplete wave
		for _, join := range doc.Delivery.JoinPoints {
			ready := true
			for _, id := range join.After {
				if strings.ToLower(statusByID[id].Status) != "accepted" {
					ready = false
					break
				}
			}
			if !ready {
				b.WriteString(fmt.Sprintf("\nJoin point：%s 验收通过后启动 %s\n", strings.Join(join.After, "、"), join.Starts))
				break
			}
		}
	}
	if len(doc.Execution.Blockers) > 0 {
		b.WriteString(fmt.Sprintf("\nBlockers：%s\n", strings.Join(doc.Execution.Blockers, "；")))
	}
	return b.String()
}

func unmetQuickDeps(deps []string, statusByID map[string]quickWorkItemStatus) []string {
	out := []string{}
	for _, dep := range deps {
		if strings.ToLower(statusByID[dep].Status) != "accepted" {
			out = append(out, dep)
		}
	}
	return out
}

func (service quickService) projectConfirmationIntoStatus(workspacePath string, doc *quickConfirmationDoc) error {
	statusPath := filepath.Join(workspacePath, "STATUS.md")
	raw, err := os.ReadFile(statusPath)
	if err != nil {
		return err
	}
	frontmatter, body := parseFrontmatter(string(raw))
	ts := nowUTCString()
	frontmatter["updated"] = ts
	confirmed := doc.ConfirmationState == "confirmed" || doc.ConfirmationState == "inherited"
	if confirmed {
		frontmatter["understanding_confirmed"] = "true"
		if frontmatter["status"] == "gathering" || frontmatter["status"] == "" {
			frontmatter["status"] = "ready"
		}
	} else {
		frontmatter["understanding_confirmed"] = "false"
		if frontmatter["status"] == "" || frontmatter["status"] == "ready" {
			frontmatter["status"] = "gathering"
		}
	}

	checkpointSection := buildQuickStatusCheckpointSection(doc)
	executionSection := buildQuickStatusExecutionSection(doc)
	// Sections already include the heading; replaceMarkdownSection keeps the existing heading line.
	checkpointBody := stripLeadingMarkdownHeading(checkpointSection, "Understanding Checkpoint")
	executionBody := stripLeadingMarkdownHeading(executionSection, "Execution")
	updated, err := replaceMarkdownSection([]byte(body), "Understanding Checkpoint", checkpointBody)
	if err != nil {
		return err
	}
	updated, err = replaceMarkdownSection(updated, "Execution", executionBody)
	if err != nil {
		return err
	}
	return writeScriptTextFile(statusPath, emitFrontmatter(frontmatter, string(updated)))
}

func stripLeadingMarkdownHeading(section, heading string) string {
	lines := strings.Split(strings.ReplaceAll(section, "\r\n", "\n"), "\n")
	if len(lines) == 0 {
		return section
	}
	first := strings.TrimSpace(lines[0])
	want := strings.ToLower("## " + heading)
	if strings.ToLower(first) == want || strings.HasPrefix(strings.ToLower(first), want) {
		return strings.TrimSpace(strings.Join(lines[1:], "\n"))
	}
	return strings.TrimSpace(section)
}

func buildQuickStatusCheckpointSection(doc *quickConfirmationDoc) string {
	var b strings.Builder
	b.WriteString("## Understanding Checkpoint\n")
	b.WriteString("<!-- agent-fill:understanding_checkpoint -->\n")
	b.WriteString("<!-- runtime-managed:quick-confirmation-v1 -->\n\n")
	b.WriteString(fmt.Sprintf("confirmation_schema: %s\n", quickConfirmationSchema))
	b.WriteString(fmt.Sprintf("confirmation_mode: %s\n", doc.ConfirmationMode))
	b.WriteString(fmt.Sprintf("confirmation_state: %s\n", doc.ConfirmationState))
	b.WriteString(fmt.Sprintf("confirmation_digest: %s\n", doc.ConfirmationDigest))
	b.WriteString(fmt.Sprintf("source_kind: %s\n", doc.Source.Kind))
	if doc.Source.DiscussionSlug != "" {
		b.WriteString(fmt.Sprintf("source_discussion_slug: %s\n", doc.Source.DiscussionSlug))
	}
	if doc.Source.ReviewDigest != "" {
		b.WriteString(fmt.Sprintf("source_review_digest: %s\n", doc.Source.ReviewDigest))
	}
	b.WriteString(fmt.Sprintf("semantic_delta: %t\n\n", doc.Source.SemanticDelta))
	b.WriteString("checkpoint:\n")
	b.WriteString(fmt.Sprintf("  request_and_outcome: %q\n", doc.Decision.Goal))
	b.WriteString(fmt.Sprintf("  user_visible_result: %q\n", doc.Decision.UserVisibleResult))
	b.WriteString("  scope:\n")
	b.WriteString(fmt.Sprintf("    include: %s\n", formatYAMLStringList(doc.Decision.Scope.Include)))
	b.WriteString(fmt.Sprintf("    exclude: %s\n", formatYAMLStringList(doc.Decision.Scope.Exclude)))
	if len(doc.Decision.Scope.Defer) > 0 {
		b.WriteString(fmt.Sprintf("    defer: %s\n", formatYAMLStringList(doc.Decision.Scope.Defer)))
	}
	b.WriteString("  ordered_work_items:\n")
	for _, item := range doc.Decision.Items {
		b.WriteString(fmt.Sprintf("    - id: %s\n", item.ID))
		b.WriteString(fmt.Sprintf("      deliverable: %q\n", item.Deliverable))
		b.WriteString(fmt.Sprintf("      depends_on: %s\n", formatYAMLStringList(item.DependsOn)))
	}
	b.WriteString("  work_item_acceptance:\n")
	for _, item := range doc.Decision.Items {
		b.WriteString(fmt.Sprintf("    - work_item_id: %s\n", item.ID))
		b.WriteString(fmt.Sprintf("      observable_result: %q\n", item.Acceptance))
		b.WriteString("      evidence: []\n")
	}
	if doc.Decision.RecommendedApproach != "" {
		b.WriteString(fmt.Sprintf("  recommended_approach: %q\n", doc.Decision.RecommendedApproach))
	}
	b.WriteString(fmt.Sprintf("  assumptions_and_risks: %s\n", formatYAMLStringList(doc.Decision.AssumptionsAndRisks)))
	b.WriteString(fmt.Sprintf("  completion_evidence: %s\n", formatYAMLStringList(doc.Decision.CompletionEvidence)))
	b.WriteString(fmt.Sprintf("  reconfirmation_trigger: %q\n", doc.Decision.ReconfirmationTrigger))
	b.WriteString(fmt.Sprintf("  confirmation_digest: %q\n", doc.ConfirmationDigest))
	b.WriteString("\n")
	b.WriteString("agent_execution_plan:\n")
	b.WriteString("  note: \"Agent-owned delivery projection; not part of confirmation digest.\"\n")
	b.WriteString("  delivery_map:\n")
	for _, wave := range doc.Delivery.Waves {
		b.WriteString(fmt.Sprintf("    - id: %s\n", wave.ID))
		b.WriteString(fmt.Sprintf("      item_ids: %s\n", formatYAMLStringList(wave.ItemIDs)))
		b.WriteString(fmt.Sprintf("      parallel: %t\n", wave.Parallel))
	}
	return b.String()
}

func buildQuickStatusExecutionSection(doc *quickConfirmationDoc) string {
	var b strings.Builder
	b.WriteString("## Execution\n")
	b.WriteString("<!-- agent-fill:execution -->\n")
	b.WriteString("<!-- runtime-managed:quick-confirmation-v1 -->\n\n")
	active := ""
	if len(doc.Execution.ActiveItemIDs) > 0 {
		active = strings.Join(doc.Execution.ActiveItemIDs, ", ")
	}
	b.WriteString(fmt.Sprintf("active_lane: %q\n", active))
	b.WriteString(fmt.Sprintf("join_point: %q\n", doc.Execution.JoinPoint))
	b.WriteString(fmt.Sprintf("blockers: %s\n", formatYAMLStringList(doc.Execution.Blockers)))
	b.WriteString("blocked_dispatch:\n")
	if doc.Execution.BlockedDispatch != nil && strings.TrimSpace(doc.Execution.BlockedDispatch.Status) != "" {
		bd := doc.Execution.BlockedDispatch
		b.WriteString(fmt.Sprintf("  status: %s\n", firstNonEmpty(bd.Status, "none")))
		b.WriteString(fmt.Sprintf("  reason: %q\n", bd.Reason))
		b.WriteString(fmt.Sprintf("  attempted_shape: %q\n", bd.AttemptedShape))
		b.WriteString(fmt.Sprintf("  chosen_shape: %q\n", bd.ChosenShape))
		if bd.ItemID != "" {
			b.WriteString(fmt.Sprintf("  item_id: %s\n", bd.ItemID))
		}
	} else {
		b.WriteString("  status: none\n")
		b.WriteString("  reason: \"\"\n")
		b.WriteString("  # Illegal: docs-only, few files, serial order, save time.\n")
		b.WriteString("  # Legal: spawn_failed / tool_missing after real attempts; use quick allow-inline.\n")
		b.WriteString("  attempted_shape: \"\"\n")
		b.WriteString("  chosen_shape: \"\"\n")
	}
	b.WriteString("work_item_status:\n")
	statusByID := map[string]quickWorkItemStatus{}
	for _, row := range doc.Execution.WorkItemStatus {
		statusByID[row.WorkItemID] = row
	}
	for _, item := range doc.Decision.Items {
		row := statusByID[item.ID]
		status := firstNonEmpty(row.Status, "pending")
		b.WriteString(fmt.Sprintf("  - work_item_id: %s\n", item.ID))
		b.WriteString(fmt.Sprintf("    status: %s\n", status))
		b.WriteString(fmt.Sprintf("    requires_worker: %t\n", row.RequiresWorker))
		b.WriteString(fmt.Sprintf("    execution_mode: %q\n", row.ExecutionMode))
		b.WriteString(fmt.Sprintf("    worker_result_id: %q\n", row.WorkerResultID))
		b.WriteString(fmt.Sprintf("    inline_approved: %t\n", row.InlineApproved))
		b.WriteString(fmt.Sprintf("    acceptance_evidence: %s\n", formatYAMLStringList(row.AcceptanceEvidence)))
	}
	b.WriteString("batches:\n")
	for _, wave := range doc.Delivery.Waves {
		b.WriteString(fmt.Sprintf("  - wave_id: %s\n", wave.ID))
		b.WriteString(fmt.Sprintf("    item_ids: %s\n", formatYAMLStringList(wave.ItemIDs)))
		b.WriteString(fmt.Sprintf("    parallel: %t\n", wave.Parallel))
	}
	b.WriteString("lanes: []\n")
	b.WriteString("retry_attempts: 0\n")
	b.WriteString("recovery_action: none\n")
	b.WriteString("blocker_reason: \"\"\n")
	return b.String()
}

func formatYAMLStringList(values []string) string {
	if len(values) == 0 {
		return "[]"
	}
	parts := make([]string, 0, len(values))
	for _, value := range values {
		parts = append(parts, fmt.Sprintf("%q", value))
	}
	return "[" + strings.Join(parts, ", ") + "]"
}

func joinOrDash(values []string) string {
	if len(values) == 0 {
		return "—"
	}
	return strings.Join(values, "、")
}

func truncateRunes(value string, max int) string {
	runes := []rune(value)
	if len(runes) <= max {
		return value
	}
	if max <= 1 {
		return string(runes[:max])
	}
	return string(runes[:max-1]) + "…"
}

func quickStringSlice(value any) []string {
	switch typed := value.(type) {
	case []string:
		out := make([]string, 0, len(typed))
		for _, item := range typed {
			item = strings.TrimSpace(item)
			if item != "" {
				out = append(out, item)
			}
		}
		return out
	case []any:
		out := make([]string, 0, len(typed))
		for _, item := range typed {
			text := strings.TrimSpace(stringValue(item))
			if text != "" {
				out = append(out, text)
			}
		}
		return out
	case string:
		text := strings.TrimSpace(typed)
		if text == "" {
			return nil
		}
		return []string{text}
	default:
		return nil
	}
}

func quickBool(value any) bool {
	switch typed := value.(type) {
	case bool:
		return typed
	case string:
		switch strings.ToLower(strings.TrimSpace(typed)) {
		case "1", "true", "yes", "y", "on":
			return true
		default:
			return false
		}
	case float64:
		return typed != 0
	case int:
		return typed != 0
	default:
		return false
	}
}

func quickContains(values []string, target string) bool {
	for _, value := range values {
		if value == target {
			return true
		}
	}
	return false
}
