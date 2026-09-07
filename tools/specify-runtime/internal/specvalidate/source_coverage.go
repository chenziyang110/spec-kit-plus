package specvalidate

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"reflect"
	"regexp"
	"strings"
)

var sourceRequirementID = regexp.MustCompile(`^REQ-[0-9]{3,}$`)

// ValidateSourceRequirementCoverage binds a feature's compiled requirements to
// the reviewed Discussion inventory and its complete source snapshots.
func ValidateSourceRequirementCoverage(featureDir string) error {
	spec, err := readCoverageObject(filepath.Join(featureDir, "spec-contract.json"))
	if err != nil {
		return err
	}
	source, sourceIsString := spec["source_contract"].(string)
	if spec["source_contract"] != nil && !sourceIsString {
		return fmt.Errorf("spec source_contract must be a canonical ref or null")
	}
	boundSource, boundDigest, err := discussionConsumerBinding(featureDir)
	if err != nil {
		return err
	}
	if boundSource != "" && (source != boundSource || coverageText(spec["source_revision"]) != boundDigest) {
		return fmt.Errorf("spec source binding cannot detach from its bound Discussion consumer pointer")
	}
	if strings.TrimSpace(source) == "" {
		rows, err := coverageRows(spec)
		if err != nil {
			return err
		}
		if len(rows) > 0 {
			return fmt.Errorf("source_requirement_coverage requires the canonical Discussion source_contract")
		}
		return nil
	}
	parts := strings.Split(source, "/")
	if len(parts) != 4 || parts[0] != ".specify" || parts[1] != "discussions" || parts[2] == "" || parts[2] == "." || parts[2] == ".." || parts[3] != "handoff-to-specify.json" || strings.Contains(source, `\`) {
		return fmt.Errorf("source_contract must identify one canonical Discussion handoff")
	}
	root, err := coverageProjectRoot(featureDir)
	if err != nil {
		return err
	}
	handoffPath, archived, err := coverageDiscussionHandoff(root, source, parts[2])
	if err != nil {
		return err
	}
	handoff, err := readCoverageObject(handoffPath)
	if err != nil {
		return fmt.Errorf("Discussion source_contract is unavailable: %w", err)
	}
	if handoff["source_contract"] != source {
		return fmt.Errorf("Discussion source_contract identity does not match the specification")
	}
	state, err := readCoverageObject(filepath.Join(filepath.Dir(handoffPath), "discussion-state.json"))
	if err != nil {
		return fmt.Errorf("Discussion current state is unavailable: %w", err)
	}
	if err := validateCurrentDiscussionSnapshot(handoff, state); err != nil {
		return err
	}
	if err := ValidateSourceRequirementCoverageAgainstHandoff(spec, handoff); err != nil {
		return err
	}
	materials, _ := handoff["source_materials"].([]any)
	for _, raw := range materials {
		material := raw.(map[string]any)
		reading := material["reading"].(map[string]any)
		snapshotRef := coverageText(reading["snapshot_ref"])
		if archived {
			prefix := ".specify/discussions/" + parts[2] + "/"
			if !strings.HasPrefix(snapshotRef, prefix) {
				return fmt.Errorf("archived material %s snapshot must belong to its exact Discussion workspace", material["id"])
			}
			snapshotRef = ".specify/discussions/archive/" + parts[2] + "/" + strings.TrimPrefix(snapshotRef, prefix)
		}
		snapshot, err := coverageProjectFile(root, snapshotRef)
		if err != nil {
			return fmt.Errorf("material %s snapshot: %w", material["id"], err)
		}
		content, err := os.ReadFile(snapshot)
		if err != nil || coverageDigest(content) != coverageText(reading["content_sha256"]) {
			return fmt.Errorf("material %s snapshot is missing or its digest changed", material["id"])
		}
		runes := []rune(string(content))
		position := 0
		for _, rawUnit := range reading["units"].([]any) {
			unit := rawUnit.(map[string]any)
			start, startOK := coverageInteger(unit["start_rune"])
			end, endOK := coverageInteger(unit["end_rune"])
			if !startOK || !endOK || start != position || end <= start || end > len(runes) || coverageDigest([]byte(string(runes[start:end]))) != coverageText(unit["sha256"]) {
				return fmt.Errorf("material %s reading units do not exactly cover the unchanged snapshot", material["id"])
			}
			position = end
		}
		if position != len(runes) {
			return fmt.Errorf("material %s reading omitted snapshot content", material["id"])
		}
		// Confirmed input is the immutable snapshot. Product implementation may
		// legitimately change source_path; explicit re-import changes the current
		// Discussion snapshot and is caught by the semantic binding above.
	}
	return nil
}

func coverageDiscussionHandoff(root, source, slug string) (string, bool, error) {
	active := filepath.Join(root, ".specify", "discussions", slug)
	archive := filepath.Join(root, ".specify", "discussions", "archive", slug)
	activeInfo, activeErr := os.Stat(active)
	archiveInfo, archiveErr := os.Stat(archive)
	if activeErr != nil && !os.IsNotExist(activeErr) {
		return "", false, activeErr
	}
	if archiveErr != nil && !os.IsNotExist(archiveErr) {
		return "", false, archiveErr
	}
	if activeErr == nil && archiveErr == nil {
		return "", false, fmt.Errorf("Discussion source has conflicting active and archived workspaces for %s", slug)
	}
	if activeErr == nil {
		if !activeInfo.IsDir() {
			return "", false, fmt.Errorf("Discussion source workspace is not a directory")
		}
		path, err := coverageProjectFile(root, source)
		return path, false, err
	}
	if archiveErr == nil && archiveInfo.IsDir() {
		path, err := coverageProjectFile(root, ".specify/discussions/archive/"+slug+"/handoff-to-specify.json")
		return path, true, err
	}
	return "", false, fmt.Errorf("Discussion source %s is missing from both its exact active and archive locations", slug)
}

// ValidateSourceRequirementCoverageAgainstHandoff is also used by the
// Discussion owner before binding/consuming a compiled specification. The
// owner verifies its current source snapshots before calling this pure check.
func ValidateSourceRequirementCoverageAgainstHandoff(spec, handoff map[string]any) error {
	if err := ValidateAcceptanceCoverage(spec); err != nil {
		return err
	}
	version, versionOK := coverageInteger(handoff["version"])
	eligibility, _ := handoff["consumer_eligibility"].(map[string]any)
	formal, _ := eligibility["sp-specify"].(map[string]any)
	hardUnknowns, unknownsOK := coverageInteger(handoff["hard_unknown_count"])
	conflicts, conflictsOK := coverageInteger(handoff["open_conflict_count"])
	if !versionOK || version != 5 || handoff["handoff_kind"] != "discussion_requirement_contract" || handoff["entry_source"] != "sp-discussion" || handoff["status"] != "handoff-ready" || handoff["coverage_status"] != "complete" || handoff["planning_gate_status"] != "ready" || handoff["recommended_consumer"] != "sp-specify" || formal["status"] != "ready" || !unknownsOK || hardUnknowns != 0 || !conflictsOK || conflicts != 0 {
		return fmt.Errorf("Discussion source is not a complete, ready, conflict-free sp-specify handoff")
	}
	digest := coverageText(handoff["review_digest"])
	computedDigest, digestErr := DiscussionReviewDigest(handoff)
	quality, _ := handoff["quality_gate"].(map[string]any)
	sourceRef := coverageText(handoff["source_contract"])
	if digestErr != nil || digest != computedDigest || sourceRef == "" || coverageText(spec["source_contract"]) != sourceRef || spec["source_revision"] != digest || quality["confirmed_digest"] != digest || quality["status"] != "user_confirmed" {
		return fmt.Errorf("spec source_revision must match the user-confirmed Discussion review_digest")
	}
	contract, _ := handoff["agent_requirement_contract"].(map[string]any)
	requirements, ok := contract["source_requirements"].([]any)
	if !ok {
		materials, hasMaterials := handoff["source_materials"].([]any)
		_, fieldPresent := contract["source_requirements"]
		if !fieldPresent && hasMaterials && len(materials) == 0 {
			requirements = []any{}
		} else {
			return fmt.Errorf("Discussion source_requirements inventory is missing; reopen Discussion before compiling")
		}
	}
	materialUnits, err := validateCoverageMaterialReadings(handoff)
	if err != nil {
		return err
	}
	byID := map[string]map[string]any{}
	for _, raw := range requirements {
		requirement, ok := raw.(map[string]any)
		if !ok {
			return fmt.Errorf("source_requirements entries must be objects")
		}
		id := coverageText(requirement["id"])
		if !sourceRequirementID.MatchString(id) || byID[id] != nil || strings.TrimSpace(coverageText(requirement["statement"])) == "" {
			return fmt.Errorf("source_requirements must have unique stable REQ IDs and non-empty statements")
		}
		refs, ok := requirement["source_refs"].([]any)
		if !ok || len(refs) == 0 {
			return fmt.Errorf("%s is missing its original material/unit source_refs", id)
		}
		for _, ref := range refs {
			object, ok := ref.(map[string]any)
			if !ok || !materialUnits[coverageText(object["material_id"])][coverageText(object["unit_id"])] || strings.TrimSpace(coverageText(object["locator"])) == "" {
				return fmt.Errorf("%s source_refs must identify fully read declared material units", id)
			}
		}
		byID[id] = requirement
	}
	if err := validateSourceUnitRequirementLinks(handoff, byID); err != nil {
		return err
	}
	rows, err := coverageRows(spec)
	if err != nil {
		return err
	}
	if len(rows) != len(byID) {
		return fmt.Errorf("source_requirement_coverage must preserve every Discussion REQ exactly once")
	}
	acceptanceToRequirement := map[string]string{}
	for _, raw := range spec["acceptance_coverage"].([]any) {
		row := raw.(map[string]any)
		acceptanceToRequirement[coverageText(row["acceptance_ref"])] = coverageText(row["requirement_ref"])
	}
	seen, owners := map[string]bool{}, map[string]string{}
	for _, raw := range rows {
		row, ok := raw.(map[string]any)
		if !ok {
			return fmt.Errorf("source_requirement_coverage entries must be objects")
		}
		id := coverageText(row["requirement_id"])
		upstream := byID[id]
		if upstream == nil || seen[id] {
			return fmt.Errorf("source_requirement_coverage contains unknown or duplicate REQ %q", id)
		}
		seen[id] = true
		disposition := coverageText(upstream["disposition"])
		if row["disposition"] != disposition {
			return fmt.Errorf("%s disposition changed from the confirmed Discussion", id)
		}
		requirementRefs, err := coverageStringSet(row["requirement_refs"], id+" requirement_refs")
		if err != nil {
			return err
		}
		acceptanceRefs, err := coverageStringSet(row["acceptance_refs"], id+" acceptance_refs")
		if err != nil {
			return err
		}
		if disposition != "in_scope" && (len(requirementRefs) != 0 || len(acceptanceRefs) != 0) {
			return fmt.Errorf("%s non-scope disposition cannot claim independent requirement/acceptance coverage", id)
		}
		switch disposition {
		case "in_scope":
			if len(requirementRefs) == 0 || len(acceptanceRefs) == 0 {
				return fmt.Errorf("%s requires concrete specification requirements and dedicated acceptance criteria", id)
			}
			mappedRequirements := map[string]bool{}
			for acceptanceRef := range acceptanceRefs {
				requirementRef := acceptanceToRequirement[acceptanceRef]
				if !requirementRefs[requirementRef] {
					return fmt.Errorf("%s acceptance_ref %s has no matching actual acceptance_coverage pair", id, acceptanceRef)
				}
				if owner := owners[acceptanceRef]; owner != "" {
					return fmt.Errorf("independent source requirements %s and %s cannot share one acceptance criterion", owner, id)
				}
				owners[acceptanceRef], mappedRequirements[requirementRef] = id, true
			}
			if len(missingCoverageRefs(requirementRefs, mappedRequirements)) > 0 {
				return fmt.Errorf("%s requirement_refs lack a dedicated mapped acceptance criterion", id)
			}
		case "duplicate":
			target := coverageText(upstream["duplicate_of"])
			if target == "" || target == id || byID[target] == nil || row["duplicate_of"] != target {
				return fmt.Errorf("%s duplicate_of must preserve its existing upstream target", id)
			}
			visited := map[string]bool{id: true}
			for current := upstream; coverageText(current["disposition"]) == "duplicate"; {
				next := coverageText(current["duplicate_of"])
				if visited[next] || byID[next] == nil {
					return fmt.Errorf("%s duplicate_of chain is cyclic or missing", id)
				}
				visited[next], current = true, byID[next]
			}
		case "deferred", "out_of_scope":
			if strings.TrimSpace(coverageText(upstream["decision_source"])) == "" || strings.TrimSpace(coverageText(upstream["reason"])) == "" || strings.TrimSpace(coverageText(upstream["reopen_condition"])) == "" {
				return fmt.Errorf("%s deferral/exclusion requires the upstream user decision, reason, and reopen condition", id)
			}
		case "context":
			if strings.TrimSpace(coverageText(upstream["reason"])) == "" {
				return fmt.Errorf("%s context disposition requires an explicit upstream reason", id)
			}
		default:
			return fmt.Errorf("%s has unresolved or unsupported source disposition %q", id, disposition)
		}
	}
	return nil
}

// DiscussionReviewDigest is shared with the Discussion producer so consumers
// verify the same protected bytes instead of trusting a stored digest label.
func DiscussionReviewDigest(handoff map[string]any) (string, error) {
	protected := make(map[string]any, len(handoff))
	for key, value := range handoff {
		switch key {
		case "review_digest", "status", "handoff_integrity", "updated_at", "quality_gate":
			continue
		}
		protected[key] = value
	}
	var content bytes.Buffer
	encoder := json.NewEncoder(&content)
	encoder.SetEscapeHTML(false)
	if err := encoder.Encode(protected); err != nil {
		return "", err
	}
	return coverageDigest(bytes.TrimSpace(content.Bytes())), nil
}

func validateCoverageMaterialReadings(handoff map[string]any) (map[string]map[string]bool, error) {
	materials, ok := handoff["source_materials"].([]any)
	if !ok {
		return nil, fmt.Errorf("Discussion source_materials inventory is missing")
	}
	result := map[string]map[string]bool{}
	for _, raw := range materials {
		material, ok := raw.(map[string]any)
		if !ok {
			return nil, fmt.Errorf("source_materials entries must be objects")
		}
		id := coverageText(material["id"])
		reading, ok := material["reading"].(map[string]any)
		version, validVersion := coverageInteger(reading["version"])
		if id == "" || result[id] != nil || !ok || !validVersion || version != 1 || len(coverageText(reading["content_sha256"])) != 64 || coverageText(reading["snapshot_ref"]) == "" || material["inspection_status"] != "inspected" {
			return nil, fmt.Errorf("material %s is missing a complete runtime-owned reading contract", id)
		}
		units, ok := reading["units"].([]any)
		if !ok || len(units) == 0 {
			return nil, fmt.Errorf("material %s declared reading units are missing", id)
		}
		declared := map[string]bool{}
		for _, rawUnit := range units {
			unit, ok := rawUnit.(map[string]any)
			unitID := coverageText(unit["id"])
			if !ok || unitID == "" || declared[unitID] {
				return nil, fmt.Errorf("material %s reading units must have unique IDs", id)
			}
			declared[unitID] = true
		}
		delivered, err := coverageStringSet(reading["delivered_unit_ids"], "delivered_unit_ids")
		if err != nil || !reflect.DeepEqual(declared, delivered) {
			return nil, fmt.Errorf("material %s has unread or unknown units", id)
		}
		dispositions, ok := material["unit_dispositions"].([]any)
		if !ok || len(dispositions) != len(declared) {
			return nil, fmt.Errorf("material %s is missing explicit source unit dispositions", id)
		}
		seen := map[string]bool{}
		for _, value := range dispositions {
			row, ok := value.(map[string]any)
			unitID := coverageText(row["unit_id"])
			if !ok || !declared[unitID] || seen[unitID] {
				return nil, fmt.Errorf("material %s has invalid source unit disposition coverage", id)
			}
			seen[unitID] = true
			requirementIDs, err := coverageStringSet(row["requirement_ids"], "unit_dispositions requirement_ids")
			if err != nil {
				return nil, err
			}
			switch row["disposition"] {
			case "requirements":
				if len(requirementIDs) == 0 {
					return nil, fmt.Errorf("material %s unit %s has unmapped requirements", id, unitID)
				}
			case "context":
				if len(requirementIDs) != 0 || strings.TrimSpace(coverageText(row["reason"])) == "" {
					return nil, fmt.Errorf("material %s context unit requires an explicit reason and no claimed requirements", id)
				}
			default:
				return nil, fmt.Errorf("material %s unit %s has an unresolved disposition", id, unitID)
			}
		}
		result[id] = declared
	}
	return result, nil
}

func validateSourceUnitRequirementLinks(handoff map[string]any, requirements map[string]map[string]any) error {
	linked := map[string]map[string]bool{}
	for _, raw := range handoff["source_materials"].([]any) {
		material := raw.(map[string]any)
		materialID := coverageText(material["id"])
		for _, rawRow := range material["unit_dispositions"].([]any) {
			row := rawRow.(map[string]any)
			unitID := coverageText(row["unit_id"])
			key := materialID + "/" + unitID
			linked[key] = map[string]bool{}
			for _, rawID := range row["requirement_ids"].([]any) {
				id := coverageText(rawID)
				if requirements[id] == nil {
					return fmt.Errorf("source unit %s maps unknown requirement %s", key, id)
				}
				linked[key][id] = true
			}
		}
	}
	for id, requirement := range requirements {
		consumedUnits := map[string]bool{}
		for _, rawRef := range requirement["source_refs"].([]any) {
			ref := rawRef.(map[string]any)
			key := coverageText(ref["material_id"]) + "/" + coverageText(ref["unit_id"])
			if !linked[key][id] {
				return fmt.Errorf("requirement %s is missing its source unit disposition mapping", id)
			}
			consumedUnits[key] = true
		}
		for key := range consumedUnits {
			delete(linked[key], id)
		}
	}
	for key, remaining := range linked {
		if len(remaining) != 0 {
			return fmt.Errorf("source unit %s requirement links lack matching requirement source_refs", key)
		}
	}
	return nil
}

// HasBoundDiscussionSource distinguishes a real binding from the pending/null
// create-feature scaffold, including before the first bind-consumer call.
func HasBoundDiscussionSource(feature string) (bool, error) {
	source, _, err := discussionConsumerBinding(feature)
	return source != "", err
}

func discussionConsumerBinding(feature string) (string, string, error) {
	path := filepath.Join(feature, "brainstorming", "handoff-to-specify.json")
	if _, err := os.Stat(path); os.IsNotExist(err) {
		return "", "", nil
	}
	pointer, err := readCoverageObject(path)
	if err != nil {
		return "", "", fmt.Errorf("Discussion consumer pointer is invalid: %w", err)
	}
	source := coverageText(pointer["source_contract"])
	digest := coverageText(pointer["review_digest"])
	if source == "" && digest == "" && coverageText(pointer["discussion_slug"]) == "" {
		return "", "", nil
	}
	if source == "" || digest == "" {
		return "", "", fmt.Errorf("Discussion consumer pointer has an incomplete source binding")
	}
	return source, digest, nil
}

func coverageRows(payload map[string]any) ([]any, error) {
	value, exists := payload["source_requirement_coverage"]
	if !exists {
		return []any{}, nil
	}
	rows, ok := value.([]any)
	if !ok {
		return nil, fmt.Errorf("source_requirement_coverage must be an array")
	}
	return rows, nil
}

func coverageStringSet(value any, label string) (map[string]bool, error) {
	values, ok := value.([]any)
	if !ok {
		return nil, fmt.Errorf("%s must be an array", label)
	}
	result := map[string]bool{}
	for _, value := range values {
		text, ok := value.(string)
		if !ok || strings.TrimSpace(text) == "" || result[text] {
			return nil, fmt.Errorf("%s must contain unique non-empty refs", label)
		}
		result[text] = true
	}
	return result, nil
}

func coverageText(value any) string {
	text, _ := value.(string)
	return text
}

func coverageInteger(value any) (int, bool) {
	number, ok := numericValue(value)
	return int(number), ok && number == float64(int(number))
}

func coverageDigest(content []byte) string {
	digest := sha256.Sum256(content)
	return hex.EncodeToString(digest[:])
}

func readCoverageObject(path string) (map[string]any, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var object map[string]any
	if err := json.Unmarshal(raw, &object); err != nil || object == nil {
		return nil, fmt.Errorf("%s must contain a JSON object", filepath.Base(path))
	}
	return object, nil
}

func coverageProjectRoot(feature string) (string, error) {
	current, err := filepath.Abs(feature)
	if err != nil {
		return "", err
	}
	for {
		if filepath.Base(current) == ".specify" {
			return filepath.Dir(current), nil
		}
		if info, err := os.Stat(filepath.Join(current, ".specify")); err == nil && info.IsDir() {
			return current, nil
		}
		parent := filepath.Dir(current)
		if parent == current {
			return "", fmt.Errorf("cannot locate the project owning Discussion source_contract")
		}
		current = parent
	}
}

func coverageProjectFile(root, relative string) (string, error) {
	if relative == "" || filepath.IsAbs(relative) || filepath.VolumeName(relative) != "" {
		return "", fmt.Errorf("source evidence path must be project-relative")
	}
	resolved, err := filepath.EvalSymlinks(filepath.Join(root, filepath.FromSlash(relative)))
	if err != nil {
		return "", err
	}
	rel, err := filepath.Rel(root, resolved)
	if err != nil || rel == ".." || strings.HasPrefix(rel, ".."+string(filepath.Separator)) {
		return "", fmt.Errorf("source evidence path escapes the project")
	}
	return resolved, nil
}

func checkSourceRequirementCoverage(a artifactSet) checkResult {
	if strings.TrimSpace(a.specContract) == "" {
		return checkResult{status: statusPass}
	}
	if err := ValidateSourceRequirementCoverage(a.dir); err != nil {
		return checkResult{status: statusFail, message: err.Error()}
	}
	return checkResult{status: statusPass}
}
