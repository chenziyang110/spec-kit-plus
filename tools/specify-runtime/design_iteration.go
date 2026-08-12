package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"reflect"
	"regexp"
	"sort"
	"strings"
)

const designDiffSchema = "spec-kit-ui-design-diff-v1"

func runDesignIterate(args []string, stdout io.Writer) int {
	if len(args) < 2 || strings.HasPrefix(args[0], "-") || strings.HasPrefix(args[1], "-") {
		return writeDesignError(stdout, "usage-error", "design iterate requires source and successor UD-* IDs")
	}
	title := strings.TrimSpace(optionValue(args, "--title", ""))
	if title == "" {
		return writeDesignError(stdout, "usage-error", "design iterate requires --title")
	}
	path, err := scaffoldDesignIteration(
		args[0],
		args[1],
		title,
		strings.ToLower(strings.TrimSpace(optionValue(args, "--type", "preserve"))),
		optionValues(args, "--scope"),
		optionValue(args, "--profiles", ""),
	)
	if err != nil {
		return writeDesignError(stdout, "blocked", err.Error())
	}
	workspace := filepath.Dir(path)
	env := NewEnvelope("ok", "UI design iteration workspace created")
	env.Data["path"] = filepath.ToSlash(path)
	env.Data["index_path"] = ".specify/design/index.json"
	env.Data["source_change_id"] = strings.ToUpper(strings.TrimSpace(args[0]))
	env.Data["brief_path"] = filepath.ToSlash(filepath.Join(workspace, "brief.md"))
	env.NextArgv = []string{
		"specify-runtime", "design", "preview-manifest",
		"--out", filepath.ToSlash(filepath.Join(workspace, "previews", "round-01.manifest.json")),
	}
	return writeEnvelope(stdout, env)
}

func runDesignResolve(args []string, stdout io.Writer) int {
	scope := strings.TrimSpace(optionValue(args, "--scope", ""))
	if scope == "" {
		return writeDesignError(stdout, "usage-error", "design resolve requires --scope")
	}
	root, err := os.Getwd()
	if err != nil {
		return writeDesignError(stdout, "error", "resolve project root: "+err.Error())
	}
	items, err := resolveDesignChanges(root, scope)
	if err != nil {
		return writeDesignError(stdout, "blocked", err.Error())
	}
	env := NewEnvelope("ok", "active UI design changes resolved for explicit adoption")
	for _, item := range items {
		env.Items = append(env.Items, item)
	}
	env.Data["scope"] = scope
	env.Data["candidate_count"] = len(items)
	env.Data["composite"] = len(items) > 1
	env.Data["requires_explicit_adoption"] = true
	return writeEnvelope(stdout, env)
}

func runDesignDiff(args []string, stdout io.Writer) int {
	if len(args) < 2 || strings.HasPrefix(args[0], "-") || strings.HasPrefix(args[1], "-") {
		return writeDesignError(stdout, "usage-error", "design diff requires source and target UD-* IDs")
	}
	root, err := os.Getwd()
	if err != nil {
		return writeDesignError(stdout, "error", "resolve project root: "+err.Error())
	}
	diff, err := diffDesignChanges(root, args[0], args[1])
	if err != nil {
		return writeDesignError(stdout, "blocked", err.Error())
	}
	env := NewEnvelope("ok", "UI design changes compared semantically")
	env.Data["diff"] = diff
	return writeEnvelope(stdout, env)
}

func runDesignAdopt(args []string, stdout io.Writer) int {
	if len(args) == 0 || strings.HasPrefix(args[0], "-") {
		return writeDesignError(stdout, "usage-error", "design adopt requires a consumer reference")
	}
	request := designAdoptionRequest{
		ConsumerRef:    args[0],
		ChangeID:       optionValue(args, "--change", ""),
		Scope:          optionValue(args, "--scope", ""),
		Mode:           optionValue(args, "--mode", ""),
		BindingRef:     optionValue(args, "--binding-ref", ""),
		BindingSHA256:  optionValue(args, "--binding-sha256", ""),
		ExpectedChange: optionValue(args, "--expected-change", ""),
	}
	root, err := os.Getwd()
	if err != nil {
		return writeDesignError(stdout, "error", "resolve project root: "+err.Error())
	}
	receipt, err := adoptDesignChange(root, request)
	if err != nil {
		return writeDesignError(stdout, "blocked", err.Error())
	}
	env := NewEnvelope("ok", "UI design change adopted explicitly")
	env.Data["adoption"] = receipt
	return writeEnvelope(stdout, env)
}

func scaffoldDesignIteration(sourceID, changeID, title, changeType string, scopes []string, profilesCSV string) (string, error) {
	root, err := os.Getwd()
	if err != nil {
		return "", err
	}
	index, _, records, err := loadDesignChangeIndex(root)
	if err != nil {
		return "", err
	}
	_ = index
	sourceID = strings.ToUpper(strings.TrimSpace(sourceID))
	source := records[sourceID]
	if source == nil || !designRecordIsRegistered(source) {
		return "", fmt.Errorf("design iteration source %s must be registered", sourceID)
	}
	sourcePath, sourceDigest, _, err := loadRegisteredDesignChange(root, sourceID)
	if err != nil {
		return "", err
	}
	if len(scopes) == 0 {
		if len(designSupersededScopeRows(source)) > 0 {
			return "", fmt.Errorf("design iteration source %s is partially superseded; pass explicit --scope values", sourceID)
		}
		scopes = stringList(source["scope"])
	}
	for _, scope := range scopes {
		within := false
		for _, sourceScope := range stringList(source["scope"]) {
			if designScopeWithin(scope, sourceScope) {
				within = true
				break
			}
		}
		if !within {
			return "", fmt.Errorf("iteration scope %s must stay within source change %s", scope, sourceID)
		}
		for _, row := range designSupersededScopeRows(source) {
			if _, overlaps := designScopeIntersection(scope, row["scope"].(string)); overlaps {
				return "", fmt.Errorf(
					"iteration scope %s is no longer active on source %s; it was superseded by %s for %s",
					scope,
					sourceID,
					row["by"],
					row["scope"],
				)
			}
		}
	}
	profileIDs := []string{}
	if strings.TrimSpace(profilesCSV) != "" {
		profileIDs, err = parseDesignCapabilityProfileIDs(profilesCSV)
		if err != nil {
			return "", err
		}
	} else {
		raw, readErr := os.ReadFile(sourcePath)
		if readErr != nil {
			return "", readErr
		}
		doc, parseErr := parseDesignMarkdown(string(raw), sourcePath)
		if parseErr != nil {
			return "", parseErr
		}
		profileIDs = stringList(doc.DesignSystem["capability_profiles"])
		if len(profileIDs) == 0 {
			profileIDs = []string{"web"}
		}
	}
	baseline := filepath.ToSlash(source["design_ref"].(string)) + "#sha256=" + sourceDigest
	return scaffoldDesignChange(
		changeID,
		title,
		changeType,
		scopes,
		profileIDs,
		[]string{baseline},
		[]string{sourceID},
		sourceID,
		sourceDigest,
	)
}

func loadDesignChangeIndex(root string) (map[string]any, string, map[string]map[string]any, error) {
	indexPath := filepath.Join(root, ".specify", "design", "index.json")
	raw, err := os.ReadFile(indexPath)
	if err != nil {
		return nil, indexPath, nil, fmt.Errorf("cannot read design change index: %v", err)
	}
	index := map[string]any{}
	if err := json.Unmarshal(raw, &index); err != nil {
		return nil, indexPath, nil, fmt.Errorf("cannot read design change index: %v", err)
	}
	if index["schema"] != designChangeIndexSchema {
		return nil, indexPath, nil, fmt.Errorf("design change index has an invalid schema")
	}
	changes, ok := index["changes"].([]any)
	if !ok {
		return nil, indexPath, nil, fmt.Errorf("design change index changes must be a list")
	}
	records := map[string]map[string]any{}
	for _, rawRecord := range changes {
		record, ok := rawRecord.(map[string]any)
		if !ok {
			continue
		}
		records[strings.TrimSpace(fmt.Sprint(record["id"]))] = record
	}
	return index, indexPath, records, nil
}

func designRecordIsRegistered(record map[string]any) bool {
	status := strings.TrimSpace(fmt.Sprint(record["status"]))
	digest := strings.TrimSpace(fmt.Sprint(record["approval_sha256"]))
	return (status == "approved" || status == "superseded") && hexDigestRE.MatchString(digest)
}

func loadRegisteredDesignChange(root, changeID string) (string, string, designDocument, error) {
	_, _, records, err := loadDesignChangeIndex(root)
	if err != nil {
		return "", "", designDocument{}, err
	}
	changeID = strings.ToUpper(strings.TrimSpace(changeID))
	record := records[changeID]
	if record == nil || !designRecordIsRegistered(record) {
		return "", "", designDocument{}, fmt.Errorf("design change %s is not registered", changeID)
	}
	ref := strings.TrimSpace(fmt.Sprint(record["design_ref"]))
	path, err := resolveProjectContainedPath(root, ref)
	if err != nil {
		return "", "", designDocument{}, err
	}
	raw, err := os.ReadFile(path)
	if err != nil {
		return "", "", designDocument{}, err
	}
	digestBytes := sha256.Sum256(raw)
	digest := hex.EncodeToString(digestBytes[:])
	if digest != strings.TrimSpace(fmt.Sprint(record["approval_sha256"])) {
		return "", "", designDocument{}, fmt.Errorf("registered design change %s digest does not match its contract", changeID)
	}
	doc, err := parseDesignMarkdown(string(raw), path)
	if err != nil {
		return "", "", designDocument{}, err
	}
	return path, digest, doc, nil
}

func designScopeWithin(scope, root string) bool {
	scope = strings.TrimSpace(scope)
	root = strings.TrimSpace(root)
	return scope == root || strings.HasPrefix(scope, root+"/")
}

func designScopeIntersection(left, right string) (string, bool) {
	if designScopeWithin(left, right) {
		return left, true
	}
	if designScopeWithin(right, left) {
		return right, true
	}
	return "", false
}

func designSupersededScopeRows(record map[string]any) []map[string]any {
	rows := []map[string]any{}
	for _, raw := range designAnyList(record["superseded_scopes"]) {
		row, ok := raw.(map[string]any)
		if !ok {
			continue
		}
		scope := strings.TrimSpace(fmt.Sprint(row["scope"]))
		by := strings.TrimSpace(fmt.Sprint(row["by"]))
		if scope != "" && by != "" {
			rows = append(rows, map[string]any{"scope": scope, "by": by})
		}
	}
	return rows
}

func designScopeExcluded(record map[string]any, scope string) bool {
	for _, row := range designSupersededScopeRows(record) {
		if designScopeWithin(scope, row["scope"].(string)) {
			return true
		}
	}
	return false
}

func designRecordActiveIntersections(record map[string]any, scopes []string) []string {
	if strings.TrimSpace(fmt.Sprint(record["status"])) != "approved" {
		return nil
	}
	seen := map[string]bool{}
	intersections := []string{}
	for _, ownScope := range stringList(record["scope"]) {
		for _, scope := range scopes {
			intersection, ok := designScopeIntersection(ownScope, scope)
			if !ok || designScopeExcluded(record, intersection) || seen[intersection] {
				continue
			}
			seen[intersection] = true
			intersections = append(intersections, intersection)
		}
	}
	sort.Strings(intersections)
	return intersections
}

func addDesignSupersededScopes(record map[string]any, scopes []string, by string) {
	rows := designSupersededScopeRows(record)
	for _, scope := range scopes {
		covered := false
		for _, row := range rows {
			if designScopeWithin(scope, row["scope"].(string)) {
				covered = true
				break
			}
		}
		if covered {
			continue
		}
		filtered := rows[:0]
		for _, row := range rows {
			if !designScopeWithin(row["scope"].(string), scope) {
				filtered = append(filtered, row)
			}
		}
		rows = append(filtered, map[string]any{"scope": scope, "by": by})
	}
	sort.Slice(rows, func(i, j int) bool {
		return rows[i]["scope"].(string) < rows[j]["scope"].(string)
	})
	raw := make([]any, 0, len(rows))
	for _, row := range rows {
		raw = append(raw, row)
	}
	record["superseded_scopes"] = raw
	fullyCovered := true
	for _, ownScope := range stringList(record["scope"]) {
		if !designScopeExcluded(record, ownScope) {
			fullyCovered = false
			break
		}
	}
	if fullyCovered {
		record["status"] = "superseded"
		record["superseded_by"] = by
	}
}

func resolveDesignChanges(root, scope string) ([]map[string]any, error) {
	if !designChangeScopeRE.MatchString(strings.TrimSpace(scope)) {
		return nil, fmt.Errorf("design resolve scope must be a stable path-like identifier")
	}
	_, _, records, err := loadDesignChangeIndex(root)
	if err != nil {
		return nil, err
	}
	type candidate struct {
		item        map[string]any
		specificity int
	}
	candidates := []candidate{}
	for _, record := range records {
		intersections := designRecordActiveIntersections(record, []string{scope})
		if len(intersections) == 0 {
			continue
		}
		matched := intersections[0]
		for _, value := range intersections[1:] {
			if designScopeSpecificity(value) > designScopeSpecificity(matched) {
				matched = value
			}
		}
		candidates = append(candidates, candidate{
			item: map[string]any{
				"id":              record["id"],
				"design_ref":      record["design_ref"],
				"approval_sha256": record["approval_sha256"],
				"matched_scope":   matched,
				"scope":           record["scope"],
			},
			specificity: designScopeSpecificity(matched),
		})
	}
	sort.Slice(candidates, func(i, j int) bool {
		if candidates[i].specificity != candidates[j].specificity {
			return candidates[i].specificity > candidates[j].specificity
		}
		return fmt.Sprint(candidates[i].item["id"]) < fmt.Sprint(candidates[j].item["id"])
	})
	items := make([]map[string]any, 0, len(candidates))
	for _, candidate := range candidates {
		items = append(items, candidate.item)
	}
	return items, nil
}

func designScopeSpecificity(scope string) int {
	return strings.Count(scope, "/")*10000 + len(scope)
}

func diffDesignChanges(root, fromID, toID string) (map[string]any, error) {
	fromPath, fromDigest, fromDoc, err := loadRegisteredDesignChange(root, fromID)
	if err != nil {
		return nil, err
	}
	toPath, toDigest, toDoc, err := loadRegisteredDesignChange(root, toID)
	if err != nil {
		return nil, err
	}
	fromID = strings.ToUpper(strings.TrimSpace(fromID))
	toID = strings.ToUpper(strings.TrimSpace(toID))
	toRelationships, _ := toDoc.DesignSystem["relationships"].(map[string]any)
	sections := []string{
		"product_context", "direction_contract", "scope", "constraints", "platforms",
		"capability_profiles", "specimens", "tokens", "color_modes", "components",
		"responsive", "content", "decisions", "verification", "accessibility",
	}
	changedSections := []string{}
	for _, section := range sections {
		if !reflect.DeepEqual(fromDoc.DesignSystem[section], toDoc.DesignSystem[section]) {
			changedSections = append(changedSections, section)
		}
	}
	sort.Strings(changedSections)
	fromApproval, _ := fromDoc.DesignSystem["approval"].(map[string]any)
	toApproval, _ := toDoc.DesignSystem["approval"].(map[string]any)
	return map[string]any{
		"schema": designDiffSchema,
		"from": map[string]any{
			"id": fromID, "design_ref": projectRelativeSlash(root, fromPath), "sha256": fromDigest,
		},
		"to": map[string]any{
			"id": toID, "design_ref": projectRelativeSlash(root, toPath), "sha256": toDigest,
		},
		"lineage": map[string]any{
			"direct_iteration":  strings.TrimSpace(fmt.Sprint(toRelationships["iteration_of"])) == fromID,
			"supersedes_source": designStringContains(stringList(toRelationships["supersedes"]), fromID),
		},
		"scope":             diffStringSets(stringList(fromDoc.DesignSystem["scope"].(map[string]any)["surfaces"]), stringList(toDoc.DesignSystem["scope"].(map[string]any)["surfaces"])),
		"decisions":         diffDesignRowsByID(designAnyList(fromDoc.DesignSystem["decisions"]), designAnyList(toDoc.DesignSystem["decisions"])),
		"handoff_contracts": diffStringSets(stringList(fromApproval["handoff_contract_ids"]), stringList(toApproval["handoff_contract_ids"])),
		"changed_sections":  changedSections,
	}, nil
}

func diffDesignRowsByID(fromRows, toRows []any) map[string]any {
	from := designRowsByID(fromRows)
	to := designRowsByID(toRows)
	added, removed, changed, retained := []string{}, []string{}, []string{}, []string{}
	for id, row := range from {
		toRow, ok := to[id]
		if !ok {
			removed = append(removed, id)
		} else if reflect.DeepEqual(row, toRow) {
			retained = append(retained, id)
		} else {
			changed = append(changed, id)
		}
	}
	for id := range to {
		if _, ok := from[id]; !ok {
			added = append(added, id)
		}
	}
	for _, values := range [][]string{added, removed, changed, retained} {
		sort.Strings(values)
	}
	return map[string]any{"added": added, "removed": removed, "changed": changed, "retained": retained}
}

func designRowsByID(rows []any) map[string]map[string]any {
	result := map[string]map[string]any{}
	for _, raw := range rows {
		row, ok := raw.(map[string]any)
		if !ok {
			continue
		}
		id := strings.TrimSpace(fmt.Sprint(row["id"]))
		if id != "" {
			result[id] = row
		}
	}
	return result
}

func diffStringSets(from, to []string) map[string]any {
	fromSet := map[string]bool{}
	toSet := map[string]bool{}
	for _, value := range from {
		fromSet[value] = true
	}
	for _, value := range to {
		toSet[value] = true
	}
	added, removed, retained := []string{}, []string{}, []string{}
	for value := range fromSet {
		if toSet[value] {
			retained = append(retained, value)
		} else {
			removed = append(removed, value)
		}
	}
	for value := range toSet {
		if !fromSet[value] {
			added = append(added, value)
		}
	}
	sort.Strings(added)
	sort.Strings(removed)
	sort.Strings(retained)
	return map[string]any{"added": added, "removed": removed, "retained": retained}
}

type designAdoptionRequest struct {
	ConsumerRef    string
	ChangeID       string
	Scope          string
	Mode           string
	BindingRef     string
	BindingSHA256  string
	ExpectedChange string
}

func adoptDesignChange(root string, request designAdoptionRequest) (map[string]any, error) {
	release, err := acquireDesignIndexLock(root)
	if err != nil {
		return nil, err
	}
	defer release()
	request.ConsumerRef = strings.TrimSpace(request.ConsumerRef)
	request.ChangeID = strings.ToUpper(strings.TrimSpace(request.ChangeID))
	request.Scope = strings.TrimSpace(request.Scope)
	request.Mode = strings.ToLower(strings.TrimSpace(request.Mode))
	request.BindingRef = filepath.ToSlash(strings.TrimSpace(request.BindingRef))
	request.BindingSHA256 = strings.ToLower(strings.TrimSpace(request.BindingSHA256))
	request.ExpectedChange = strings.ToUpper(strings.TrimSpace(request.ExpectedChange))
	if !designChangeScopeRE.MatchString(request.ConsumerRef) {
		return nil, fmt.Errorf("design adoption consumer reference must be a stable identifier")
	}
	if !designChangeIDRE.MatchString(request.ChangeID) {
		return nil, fmt.Errorf("design adoption requires --change UD-*")
	}
	if !designChangeScopeRE.MatchString(request.Scope) {
		return nil, fmt.Errorf("design adoption scope must be a stable path-like identifier")
	}
	if request.Mode != "formal" && request.Mode != "quick" {
		return nil, fmt.Errorf("design adoption mode must be formal or quick")
	}
	if request.BindingRef == "" || !hexDigestRE.MatchString(request.BindingSHA256) {
		return nil, fmt.Errorf("design adoption requires --binding-ref and a SHA-256 --binding-sha256")
	}
	if request.ExpectedChange == "" {
		return nil, fmt.Errorf("design adoption requires --expected-change <UD-ID|none>")
	}
	if request.ExpectedChange != "NONE" && !designChangeIDRE.MatchString(request.ExpectedChange) {
		return nil, fmt.Errorf("expected current change must be a UD-* ID or none")
	}
	index, indexPath, records, err := loadDesignChangeIndex(root)
	if err != nil {
		return nil, err
	}
	record := records[request.ChangeID]
	if record == nil || !designRecordIsRegistered(record) || len(designRecordActiveIntersections(record, []string{request.Scope})) == 0 {
		return nil, fmt.Errorf("design change %s is not active for scope %s", request.ChangeID, request.Scope)
	}
	coveredByRoot := false
	for _, rootScope := range stringList(record["scope"]) {
		if designScopeWithin(request.Scope, rootScope) {
			coveredByRoot = true
			break
		}
	}
	if !coveredByRoot || designScopeExcluded(record, request.Scope) {
		return nil, fmt.Errorf("design change %s cannot be the singular binding for scope %s", request.ChangeID, request.Scope)
	}
	designRef := strings.TrimSpace(fmt.Sprint(record["design_ref"]))
	designPath, designDigest, _, err := loadRegisteredDesignChange(root, request.ChangeID)
	if err != nil {
		return nil, err
	}
	designContractRef := filepath.ToSlash(filepath.Join(filepath.Dir(designRef), "design-contract.json"))
	contractPath, err := resolveProjectContainedPath(root, designContractRef)
	if err != nil {
		return nil, err
	}
	contractRaw, err := os.ReadFile(contractPath)
	if err != nil {
		return nil, fmt.Errorf("cannot read design contract export %s: %v", designContractRef, err)
	}
	var contract map[string]any
	if err := json.Unmarshal(contractRaw, &contract); err != nil || strings.TrimSpace(fmt.Sprint(contract["id"])) != request.ChangeID {
		return nil, fmt.Errorf("design contract export does not match %s", request.ChangeID)
	}
	expectedRaw, err := exportDesignSystem(designPath, "json", true)
	if err != nil {
		return nil, fmt.Errorf("cannot verify design contract export for %s: %v", request.ChangeID, err)
	}
	var expectedContract map[string]any
	if err := json.Unmarshal([]byte(expectedRaw), &expectedContract); err != nil {
		return nil, fmt.Errorf("cannot verify design contract export for %s: %v", request.ChangeID, err)
	}
	if !reflect.DeepEqual(contract, expectedContract) {
		return nil, fmt.Errorf("design contract export does not match the registered design %s", request.ChangeID)
	}
	bindingPath, err := resolveProjectContainedPath(root, request.BindingRef)
	if err != nil {
		return nil, err
	}
	bindingRaw, err := os.ReadFile(bindingPath)
	if err != nil {
		return nil, fmt.Errorf("cannot read design adoption binding: %v", err)
	}
	if err := validateDesignAdoptionSurface(root, request, bindingPath, bindingRaw); err != nil {
		return nil, err
	}
	bindingDigestBytes := sha256.Sum256(bindingRaw)
	bindingDigest := hex.EncodeToString(bindingDigestBytes[:])
	if bindingDigest != request.BindingSHA256 {
		return nil, fmt.Errorf("design adoption binding SHA-256 does not match %s", request.BindingRef)
	}
	wantBinding := map[string]string{
		"design_change_id":     request.ChangeID,
		"design_change_ref":    designRef,
		"design_change_sha256": designDigest,
		"design_contract_ref":  designContractRef,
	}
	if !designBindingContains(bindingRaw, wantBinding) {
		return nil, fmt.Errorf("design adoption binding does not contain the exact registered change fields")
	}

	adoptions := designAnyList(index["adoptions"])
	var current map[string]any
	maxRevision := 0
	for _, raw := range adoptions {
		row, ok := raw.(map[string]any)
		if !ok || row["consumer_ref"] != request.ConsumerRef || row["scope"] != request.Scope {
			continue
		}
		revision := intFromAny(row["revision"])
		if revision > maxRevision {
			maxRevision = revision
		}
		if row["status"] == "current" {
			current = row
		}
	}
	currentID := "NONE"
	if current != nil {
		currentID = strings.ToUpper(strings.TrimSpace(fmt.Sprint(current["change_id"])))
	}
	if currentID != request.ExpectedChange {
		return nil, fmt.Errorf("expected current change %s but found %s", request.ExpectedChange, currentID)
	}
	if current != nil && currentID == request.ChangeID && current["binding_sha256"] == bindingDigest {
		return current, nil
	}
	revision := maxRevision + 1
	if current != nil {
		current["status"] = "superseded"
		current["superseded_by_revision"] = revision
	}
	previous := any(nil)
	if current != nil {
		previous = currentID
	}
	receipt := map[string]any{
		"consumer_ref":         request.ConsumerRef,
		"scope":                request.Scope,
		"mode":                 request.Mode,
		"revision":             revision,
		"status":               "current",
		"change_id":            request.ChangeID,
		"design_change_id":     request.ChangeID,
		"design_ref":           designRef,
		"design_sha256":        designDigest,
		"design_change_ref":    designRef,
		"design_change_sha256": designDigest,
		"design_contract_ref":  designContractRef,
		"binding_ref":          request.BindingRef,
		"binding_sha256":       bindingDigest,
		"previous_change_id":   previous,
	}
	adoptions = append(adoptions, receipt)
	index["adoptions"] = adoptions
	updateDesignRecordConsumers(records, request, revision)
	if err := writeJSONAtomic(indexPath, index); err != nil {
		return nil, err
	}
	return receipt, nil
}

func updateDesignRecordConsumers(records map[string]map[string]any, request designAdoptionRequest, revision int) {
	for _, record := range records {
		filtered := []any{}
		for _, raw := range designAnyList(record["consumers"]) {
			consumer, ok := raw.(map[string]any)
			if ok && consumer["consumer_ref"] == request.ConsumerRef && consumer["scope"] == request.Scope {
				continue
			}
			filtered = append(filtered, raw)
		}
		record["consumers"] = filtered
	}
	target := records[request.ChangeID]
	target["consumers"] = append(designAnyList(target["consumers"]), map[string]any{
		"consumer_ref": request.ConsumerRef,
		"scope":        request.Scope,
		"mode":         request.Mode,
		"revision":     revision,
	})
}

func designBindingContains(raw []byte, fields map[string]string) bool {
	var payload any
	if json.Unmarshal(raw, &payload) == nil {
		for key, value := range fields {
			if !designJSONContainsField(payload, key, value) {
				return false
			}
		}
		return true
	}
	content := strings.ReplaceAll(strings.ReplaceAll(string(raw), "\r\n", "\n"), "\r", "\n")
	for key, value := range fields {
		pattern := `(?m)^[\t ]*(?:[-*][\t ]+)?` + regexp.QuoteMeta(key) +
			`[\t ]*:[\t ]*(?:` + regexp.QuoteMeta(value) + `|"` + regexp.QuoteMeta(value) +
			`"|'` + regexp.QuoteMeta(value) + `')[\t ]*$`
		if !regexp.MustCompile(pattern).MatchString(content) {
			return false
		}
	}
	return true
}

func validateDesignAdoptionSurface(root string, request designAdoptionRequest, bindingPath string, bindingRaw []byte) error {
	if request.Mode == "formal" {
		if !strings.HasPrefix(request.ConsumerRef, "feature:") {
			return fmt.Errorf("formal design adoption consumer must use feature:<id>")
		}
		validRoot := strings.HasPrefix(request.BindingRef, "specs/") || strings.HasPrefix(request.BindingRef, ".specify/features/")
		if !validRoot || !strings.HasSuffix(request.BindingRef, "/spec-contract.json") {
			return fmt.Errorf("formal design adoption binding must be a feature spec-contract.json")
		}
		return nil
	}
	if !strings.HasPrefix(request.ConsumerRef, "quick:") {
		return fmt.Errorf("quick design adoption consumer must use quick:<id>")
	}
	if !strings.HasPrefix(request.BindingRef, ".planning/quick/") || !strings.HasSuffix(request.BindingRef, "/STATUS.md") {
		return fmt.Errorf("quick design adoption binding must be .planning/quick/<id>/STATUS.md")
	}
	frontmatter, _ := parseFrontmatter(string(bindingRaw))
	if !strings.EqualFold(strings.TrimSpace(frontmatter["understanding_confirmed"]), "true") {
		return fmt.Errorf("quick design adoption checkpoint must be confirmed in STATUS.md")
	}
	doc, err := (quickService{projectRoot: root}).loadConfirmation(filepath.Dir(bindingPath))
	if err != nil {
		return fmt.Errorf("quick design adoption checkpoint must be confirmed through confirmation.json: %v", err)
	}
	if doc.ConfirmationState != "confirmed" && doc.ConfirmationState != "inherited" {
		return fmt.Errorf("quick design adoption checkpoint must be confirmed or inherited")
	}
	return nil
}

func designJSONContainsField(value any, key, want string) bool {
	switch typed := value.(type) {
	case map[string]any:
		if got, ok := typed[key]; ok && strings.TrimSpace(fmt.Sprint(got)) == want {
			return true
		}
		for _, child := range typed {
			if designJSONContainsField(child, key, want) {
				return true
			}
		}
	case []any:
		for _, child := range typed {
			if designJSONContainsField(child, key, want) {
				return true
			}
		}
	}
	return false
}

func designStringContains(values []string, want string) bool {
	for _, value := range values {
		if value == want {
			return true
		}
	}
	return false
}

func designAnyList(value any) []any {
	if value == nil {
		return []any{}
	}
	values, ok := value.([]any)
	if !ok {
		return []any{}
	}
	return values
}

func projectRelativeSlash(root, path string) string {
	relative, err := filepath.Rel(root, path)
	if err != nil {
		return filepath.ToSlash(path)
	}
	return filepath.ToSlash(relative)
}
