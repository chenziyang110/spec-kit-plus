package main

import (
	"fmt"
	"io"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"unicode/utf8"
)

const discussionMaterialUnitRunes = 2000
const discussionMaterialMaxBytes = 64 << 20

var discussionRequirementID = regexp.MustCompile(`^REQ-[0-9]{3,}$`)
var discussionMaterialID = regexp.MustCompile(`^MAT-[0-9]{3,}$`)

func discussionMaterialText(value any) bool {
	text, ok := value.(string)
	return ok && strings.TrimSpace(text) != ""
}

// Source text is untrusted data. These routes only import and return bytes;
// they never execute instructions, fetch URLs, or launch source processors.
func runDiscussionMaterial(args []string, stdout io.Writer, mode, slug, projectRoot string) int {
	service := discussionService{projectRoot: projectRoot, expectedStateSHA256: strings.TrimSpace(optionValue(args, "--expected-state-sha256", ""))}
	var input map[string]any
	var err error
	if mode == "import-material" {
		input, err = readAgentJSONObject(args, projectRoot, "discussion import-material")
	}
	if mode == "read-material" && hasFlag(args, "--expected-state-sha256") && service.expectedStateSHA256 == "" {
		err = fmt.Errorf("an explicitly supplied --expected-state-sha256 cannot be empty")
	}
	var data map[string]any
	if err == nil {
		err = service.withMutationLock(mode, slug, func() error {
			var runErr error
			if mode == "import-material" {
				data, runErr = service.importMaterial(slug, input)
			} else {
				data, runErr = service.readMaterial(slug, optionValue(args, "--material-id", ""), optionValue(args, "--unit-id", ""))
			}
			return runErr
		})
	}
	if err != nil {
		env := scriptDomainError("discussion", err)
		env.NextArgv = []string{"specify-runtime", "discussion", "resolve", "--intent", "continue", "--slug", slug, "--format", "json"}
		if workspace, _, findErr := service.findWorkspace(slug, true); findErr == nil {
			if state, _, loadErr := service.loadState(workspace); loadErr == nil {
				if binding, bindErr := service.focusBinding(workspace, state); bindErr == nil {
					env.Data["binding"] = binding
				}
			}
		}
		return writeEnvelope(stdout, env)
	}
	env := NewEnvelope("ok", "discussion material "+mode+" completed")
	env.Data = data
	return writeEnvelope(stdout, env)
}

func (service discussionService) materialMutationState(slug string) (string, map[string]any, error) {
	workspace, archived, err := service.findWorkspace(slug, false)
	if err != nil {
		return "", nil, err
	}
	if archived {
		return "", nil, fmt.Errorf("archived discussion materials cannot change")
	}
	state, _, err := service.loadState(workspace)
	if err != nil {
		return "", nil, err
	}
	if service.expectedStateSHA256 == "" {
		return "", nil, fmt.Errorf("material commands require --expected-state-sha256 from discussion resolve")
	}
	if err := service.requireExpectedStateSHA(workspace); err != nil {
		return "", nil, err
	}
	if discussionMaterialsFrozen(state) {
		return "", nil, fmt.Errorf("confirmed discussion materials are frozen; explicitly reopen through a semantic checkpoint before importing or delivering unread units")
	}
	return workspace, state, nil
}

func discussionMaterialsFrozen(state map[string]any) bool {
	phase := stringValue(state["lifecycle_phase"])
	return phase == "ready" || phase == "consumed" || phase == "closed" ||
		(phase == "review" && mapValue(state["handoff"])["quality_gate_status"] == "user_confirmed")
}

func (service discussionService) materialReadWorkspace(slug string) (string, bool, error) {
	if slug == "" || slug == "." || slug == ".." || strings.ContainsAny(slug, `/\`) {
		return "", false, fmt.Errorf("material reading requires one exact discussion slug")
	}
	active, err := secureProjectPath(service.projectRoot, filepath.ToSlash(filepath.Join(".specify", "discussions", slug)))
	if err != nil {
		return "", false, err
	}
	archive, err := secureProjectPath(service.projectRoot, filepath.ToSlash(filepath.Join(".specify", "discussions", "archive", slug)))
	if err != nil {
		return "", false, err
	}
	activeInfo, activeErr := os.Stat(active)
	archiveInfo, archiveErr := os.Stat(archive)
	if activeErr != nil && !os.IsNotExist(activeErr) {
		return "", false, activeErr
	}
	if archiveErr != nil && !os.IsNotExist(archiveErr) {
		return "", false, archiveErr
	}
	if activeErr == nil && archiveErr == nil {
		return "", false, fmt.Errorf("material source has conflicting active and archived workspaces for %s", slug)
	}
	if activeErr == nil {
		if !activeInfo.IsDir() {
			return "", false, fmt.Errorf("active material workspace is not a directory")
		}
		return active, false, nil
	}
	if archiveErr == nil && archiveInfo.IsDir() {
		return archive, true, nil
	}
	return "", false, fmt.Errorf("material workspace is missing from both exact active and archive locations")
}

func readDiscussionMaterialFile(path string) ([]byte, error) {
	file, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer file.Close()
	info, err := file.Stat()
	if err != nil || !info.Mode().IsRegular() {
		return nil, fmt.Errorf("material must be a readable regular UTF-8 text file")
	}
	content, err := io.ReadAll(io.LimitReader(file, discussionMaterialMaxBytes+1))
	if err != nil {
		return nil, err
	}
	if len(content) > discussionMaterialMaxBytes {
		return nil, fmt.Errorf("material exceeds 64 MiB; explicitly split the complete source into registered materials, never truncate it")
	}
	if !utf8.Valid(content) {
		return nil, fmt.Errorf("material is not valid UTF-8; import a complete UTF-8 extraction with its original locator")
	}
	if strings.TrimSpace(strings.TrimPrefix(string(content), "\ufeff")) == "" {
		return nil, fmt.Errorf("material text is empty")
	}
	return content, nil
}

func discussionMaterialUnits(content []byte) []any {
	runes := []rune(string(content))
	units := []any{}
	for start := 0; start < len(runes); start += discussionMaterialUnitRunes {
		end := start + discussionMaterialUnitRunes
		if end > len(runes) {
			end = len(runes)
		}
		digest := fileContentSHA256([]byte(string(runes[start:end])))
		units = append(units, map[string]any{"id": fmt.Sprintf("U%04d-%s", len(units)+1, digest[:12]), "start_rune": start, "end_rune": end, "sha256": digest})
	}
	return units
}

func (service discussionService) importMaterial(slug string, input map[string]any) (map[string]any, error) {
	allowed := map[string]bool{"id": true, "path": true, "locator": true, "material_type": true, "summary": true, "sensitivity": true, "version_ref": true}
	for key := range input {
		if !allowed[key] {
			return nil, fmt.Errorf("import-material unknown fields: %s", key)
		}
	}
	for _, key := range []string{"id", "path", "locator", "material_type", "summary", "sensitivity"} {
		if !discussionMaterialText(input[key]) {
			return nil, fmt.Errorf("import-material %s must be a non-empty string", key)
		}
	}
	for field, limit := range map[string]int{"locator": 2048, "material_type": 128, "summary": 1000, "version_ref": 512} {
		if value, present := input[field]; present && (!discussionMaterialText(value) || utf8.RuneCountInString(stringValue(value)) > limit) {
			return nil, fmt.Errorf("import-material %s must contain 1..%d characters", field, limit)
		}
	}
	id := stringValue(input["id"])
	if !discussionMaterialID.MatchString(id) || !discussionSourceMaterialSensitivities[stringValue(input["sensitivity"])] {
		return nil, fmt.Errorf("invalid material id or sensitivity")
	}
	workspace, state, err := service.materialMutationState(slug)
	if err != nil {
		return nil, err
	}
	sourcePath := stringValue(input["path"])
	if !filepath.IsAbs(sourcePath) {
		sourcePath = filepath.Join(service.projectRoot, sourcePath)
	}
	sourcePath, err = filepath.Abs(sourcePath)
	if err != nil {
		return nil, err
	}
	sourcePath, err = filepath.EvalSymlinks(sourcePath)
	if err != nil {
		return nil, err
	}
	content, err := readDiscussionMaterialFile(sourcePath)
	if err != nil {
		return nil, err
	}
	digest := fileContentSHA256(content)
	ref := filepath.ToSlash(filepath.Join(".specify", "discussions", slug, "materials", id, digest+".txt"))
	snapshot, err := secureProjectPath(service.projectRoot, ref)
	if err != nil {
		return nil, err
	}
	packet := mapValue(state["turn_packet"])
	if requirements := mapValue(packet["requirements_snapshot"]); requirements != nil {
		if _, present := requirements["source_requirements"]; !present {
			requirements["source_requirements"] = []any{}
		}
	}
	materials := listValue(packet["source_materials"])
	oldIndex := -1
	var previous map[string]any
	for index, item := range materials {
		if mapValue(item)["id"] == id {
			oldIndex, previous = index, mapValue(item)
			break
		}
	}
	reading := map[string]any{"version": 1, "content_sha256": digest, "snapshot_ref": ref, "source_path": sourcePath, "units": discussionMaterialUnits(content), "delivered_unit_ids": []any{}}
	material := map[string]any{"id": id, "material_type": input["material_type"], "locator": input["locator"], "summary": input["summary"], "sensitivity": input["sensitivity"], "inspection_status": "pending", "claims": []any{}, "coverage_gaps": []any{}, "content_sha256": digest, "reading": reading, "unit_dispositions": []any{}}
	if version, present := input["version_ref"]; present {
		if _, ok := version.(string); !ok {
			return nil, fmt.Errorf("version_ref must be a string")
		}
		material["version_ref"] = version
	}
	if previous != nil {
		oldReading := mapValue(previous["reading"])
		if oldReading["content_sha256"] == digest && oldReading["source_path"] == sourcePath && previous["locator"] == material["locator"] && previous["version_ref"] == material["version_ref"] && previous["summary"] == material["summary"] && previous["material_type"] == material["material_type"] && previous["sensitivity"] == material["sensitivity"] {
			if _, err := service.verifiedMaterialContent(slug, previous, true); err == nil {
				return service.materialResult(workspace, state, previous)
			}
		}
		history := append([]any{}, listValue(previous["version_history"])...)
		prior := cloneAnyMap(previous)
		delete(prior, "version_history")
		history = append(history, prior)
		material["version_history"] = history
	}
	if oldIndex >= 0 {
		materials[oldIndex] = material
	} else {
		materials = append(materials, material)
	}
	packet["source_materials"] = materials
	updates := []fileTransactionUpdate{}
	if existing, readErr := os.ReadFile(snapshot); readErr == nil {
		if fileContentSHA256(existing) != digest {
			return nil, fmt.Errorf("material snapshot is corrupt; refusing to overwrite immutable source evidence")
		}
	} else if os.IsNotExist(readErr) {
		updates = append(updates, fileTransactionUpdate{Path: snapshot, Content: content})
	} else {
		return nil, readErr
	}
	if err := service.persistMaterialMutation(workspace, state, updates); err != nil {
		return nil, err
	}
	return service.materialResult(workspace, state, material)
}

func (service discussionService) verifiedMaterialContent(slug string, material map[string]any, checkLiveSource bool) ([]byte, error) {
	reading := mapValue(material["reading"])
	if intValue(reading["version"]) != 1 {
		return nil, fmt.Errorf("%s has no runtime reading receipt; import-material and read-material are required", material["id"])
	}
	digest := stringValue(reading["content_sha256"])
	expectedRef := filepath.ToSlash(filepath.Join(".specify", "discussions", slug, "materials", stringValue(material["id"]), digest+".txt"))
	if !regexp.MustCompile(`^[a-f0-9]{64}$`).MatchString(digest) || reading["snapshot_ref"] != expectedRef || material["content_sha256"] != digest {
		return nil, fmt.Errorf("material reading snapshot binding is invalid")
	}
	_, archived, err := service.materialReadWorkspace(slug)
	if err != nil {
		return nil, err
	}
	physicalRef := expectedRef
	if archived {
		physicalRef = filepath.ToSlash(filepath.Join(".specify", "discussions", "archive", slug, "materials", stringValue(material["id"]), digest+".txt"))
	}
	snapshot, err := secureProjectPath(service.projectRoot, physicalRef)
	if err != nil {
		return nil, err
	}
	content, err := readDiscussionMaterialFile(snapshot)
	if err != nil || fileContentSHA256(content) != digest {
		return nil, fmt.Errorf("material snapshot is missing or changed: %s", material["id"])
	}
	units := discussionMaterialUnits(content)
	if !discussionValuesEqual(units, reading["units"]) {
		return nil, fmt.Errorf("material reading unit inventory differs from its complete snapshot")
	}
	if !checkLiveSource {
		return content, nil
	}
	sourcePath := stringValue(reading["source_path"])
	if !filepath.IsAbs(sourcePath) {
		return nil, fmt.Errorf("material source_path must be absolute")
	}
	source, err := readDiscussionMaterialFile(sourcePath)
	if os.IsNotExist(err) {
		// Extracted input can be temporary. The immutable snapshot remains the
		// authority; a missing source does not claim remote freshness.
		return content, nil
	}
	if err != nil || fileContentSHA256(source) != digest {
		return nil, fmt.Errorf("material local source is unavailable or stale; re-import and re-read %s", material["id"])
	}
	return content, nil
}

func (service discussionService) readMaterial(slug, materialID, unitID string) (map[string]any, error) {
	workspace, archived, err := service.materialReadWorkspace(slug)
	if err != nil {
		return nil, err
	}
	state, _, err := service.loadState(workspace)
	if err != nil {
		return nil, err
	}
	if state["slug"] != slug {
		return nil, fmt.Errorf("material state identity does not match its exact discussion slug")
	}
	if service.expectedStateSHA256 != "" {
		if err := service.requireExpectedStateSHA(workspace); err != nil {
			return nil, err
		}
	}
	var material map[string]any
	for _, item := range listValue(mapValue(state["turn_packet"])["source_materials"]) {
		if mapValue(item)["id"] == materialID {
			material = mapValue(item)
			break
		}
	}
	if material == nil {
		return nil, fmt.Errorf("unknown material id: %s", materialID)
	}
	reading := mapValue(material["reading"])
	var selected map[string]any
	for _, item := range listValue(reading["units"]) {
		if mapValue(item)["id"] == unitID {
			selected = mapValue(item)
			break
		}
	}
	if selected == nil {
		return nil, fmt.Errorf("unknown material unit id: %s", unitID)
	}
	delivered := anyStrings(listValue(reading["delivered_unit_ids"]))
	alreadyDelivered := false
	for _, id := range delivered {
		if id == unitID {
			alreadyDelivered = true
		}
	}
	content, err := service.verifiedMaterialContent(slug, material, !alreadyDelivered)
	if err != nil {
		return nil, err
	}
	if !alreadyDelivered {
		if archived || discussionMaterialsFrozen(state) {
			return nil, fmt.Errorf("frozen or archived material permits replay only of units already delivered")
		}
		if service.expectedStateSHA256 == "" {
			return nil, fmt.Errorf("first material delivery requires --expected-state-sha256 from discussion resolve")
		}
		delivered = append(delivered, unitID)
		sort.Strings(delivered)
		values := make([]any, len(delivered))
		for index, id := range delivered {
			values[index] = id
		}
		reading["delivered_unit_ids"] = values
		material["inspection_status"] = "partial"
		if len(delivered) == len(listValue(reading["units"])) {
			material["inspection_status"] = "inspected"
		}
		if err := service.persistMaterialMutation(workspace, state, nil); err != nil {
			return nil, err
		}
	}
	result, err := service.materialResult(workspace, state, material)
	if err != nil {
		return nil, err
	}
	runes := []rune(string(content))
	result["unit"] = selected
	result["replayed"] = alreadyDelivered
	result["text"] = string(runes[intValue(selected["start_rune"]):intValue(selected["end_rune"])])
	result["receipt"] = map[string]any{"material_id": materialID, "unit_id": unitID, "content_sha256": reading["content_sha256"], "unit_sha256": selected["sha256"]}
	return result, nil
}

func (service discussionService) persistMaterialMutation(workspace string, state map[string]any, updates []fileTransactionUpdate) error {
	state["updated_at"] = nowUTCString()
	normalizeDiscussionState(state)
	if err := validateDiscussionState(state); err != nil {
		return err
	}
	raw, err := canonicalJSON(state)
	if err != nil {
		return err
	}
	statePath := filepath.Join(workspace, "discussion-state.json")
	updates = append(updates, fileTransactionUpdate{Path: statePath, Content: raw}, fileTransactionUpdate{Path: filepath.Join(workspace, "discussion-state.md"), Content: []byte(renderDiscussionMarkdown(state))})
	_, err = applyFileTransactionWithPreconditions(service.projectRoot, "discussion.material", updates, []fileTransactionPrecondition{{Path: statePath, ExpectedSHA256: service.expectedStateSHA256}})
	return err
}

func (service discussionService) materialResult(workspace string, state, material map[string]any) (map[string]any, error) {
	binding, err := service.focusBinding(workspace, state)
	if err != nil {
		return nil, err
	}
	summary := map[string]any{}
	for _, field := range []string{"id", "material_type", "locator", "summary", "sensitivity", "version_ref", "inspection_status", "content_sha256"} {
		if value, present := material[field]; present {
			summary[field] = value
		}
	}
	reading := mapValue(material["reading"])
	delivered := map[string]bool{}
	for _, item := range listValue(reading["delivered_unit_ids"]) {
		delivered[stringValue(item)] = true
	}
	next := ""
	for _, item := range listValue(reading["units"]) {
		id := stringValue(mapValue(item)["id"])
		if !delivered[id] {
			next = id
			break
		}
	}
	progress := map[string]any{"total_units": len(listValue(reading["units"])), "delivered_units": len(delivered), "next_unit_id": next}
	return map[string]any{"material": summary, "reading_progress": progress, "binding": binding}, nil
}

func discussionValuesEqual(left, right any) bool {
	leftSHA, leftErr := discussionCanonicalDigest(left)
	rightSHA, rightErr := discussionCanonicalDigest(right)
	return leftErr == nil && rightErr == nil && leftSHA == rightSHA
}

func validateDiscussionMaterialCheckpoint(packet, changes map[string]any) error {
	if supplied, exists := changes["source_materials"]; exists {
		old := map[string]map[string]any{}
		for _, item := range listValue(packet["source_materials"]) {
			material := mapValue(item)
			old[stringValue(material["id"])] = material
		}
		seen := map[string]bool{}
		for _, item := range listValue(supplied) {
			material := mapValue(item)
			id := stringValue(material["id"])
			seen[id] = true
			previous := old[id]
			if mapValue(previous["reading"]) != nil {
				for _, field := range []string{"reading", "content_sha256", "version_history", "locator", "version_ref", "material_type", "summary", "sensitivity", "inspection_status"} {
					if value, present := material[field]; present && !discussionValuesEqual(value, previous[field]) {
						return fmt.Errorf("runtime-owned material %s.%s cannot be changed through checkpoint", id, field)
					}
					if value, present := previous[field]; present {
						material[field] = cloneAny(value)
					}
				}
			} else {
				if _, present := material["reading"]; present {
					return fmt.Errorf("reading evidence can only be created by import-material/read-material")
				}
				if material["inspection_status"] != "pending" && material["inspection_status"] != "unavailable" {
					return fmt.Errorf("material %s requires import-material/read-material before it can be inspected", id)
				}
			}
		}
		for id := range old {
			if !seen[id] {
				return fmt.Errorf("source material %s cannot disappear from a checkpoint", id)
			}
		}
	}
	if incoming, exists := changes["requirements_snapshot"]; exists {
		old := listValue(mapValue(packet["requirements_snapshot"])["source_requirements"])
		newIDs := map[string]bool{}
		for _, item := range listValue(mapValue(incoming)["source_requirements"]) {
			newIDs[stringValue(mapValue(item)["id"])] = true
		}
		for _, item := range old {
			if id := stringValue(mapValue(item)["id"]); !newIDs[id] {
				return fmt.Errorf("source requirement %s cannot disappear; preserve it with an explicit disposition", id)
			}
		}
	}
	return nil
}

func validateDiscussionSourceRequirementShapes(requirements map[string]any) error {
	value, present := requirements["source_requirements"]
	if !present {
		return nil
	}
	items, ok := value.([]any)
	if !ok {
		return fmt.Errorf("source_requirements must be an array")
	}
	byID := map[string]map[string]any{}
	for _, item := range items {
		req := mapValue(item)
		id := stringValue(req["id"])
		if !discussionRequirementID.MatchString(id) || byID[id] != nil || !discussionMaterialText(req["statement"]) {
			return fmt.Errorf("source requirement needs a unique REQ-### id and non-empty statement")
		}
		byID[id] = req
		refs, ok := req["source_refs"].([]any)
		if !ok || len(refs) == 0 {
			return fmt.Errorf("%s requires source_refs", id)
		}
		for _, item := range refs {
			ref := mapValue(item)
			for _, field := range []string{"material_id", "unit_id", "locator"} {
				if !discussionMaterialText(ref[field]) {
					return fmt.Errorf("%s source_refs.%s must be non-empty", id, field)
				}
			}
		}
		disposition := stringValue(req["disposition"])
		fields := []string{}
		switch disposition {
		case "in_scope":
			fields = []string{"acceptance_hint"}
		case "context", "unresolved":
			fields = []string{"reason"}
		case "duplicate":
			fields = []string{"reason", "duplicate_of"}
		case "deferred", "out_of_scope":
			fields = []string{"reason", "decision_source", "reopen_condition"}
		default:
			return fmt.Errorf("%s has an invalid source requirement disposition", id)
		}
		for _, field := range fields {
			if !discussionMaterialText(req[field]) {
				return fmt.Errorf("%s disposition %s requires %s", id, disposition, field)
			}
		}
	}
	for id, req := range byID {
		seen := map[string]bool{id: true}
		for req["disposition"] == "duplicate" {
			target := stringValue(req["duplicate_of"])
			if seen[target] || byID[target] == nil {
				return fmt.Errorf("%s has an unknown or cyclic duplicate_of", id)
			}
			seen[target] = true
			req = byID[target]
		}
	}
	return nil
}

func (service discussionService) validateSourceReadCoverage(slug string, packet map[string]any, complete bool) error {
	requirements := mapValue(packet["requirements_snapshot"])
	if requirements == nil {
		requirements = mapValue(packet["agent_requirement_contract"])
	}
	if err := validateDiscussionSourceRequirementShapes(requirements); err != nil {
		return err
	}
	materials := map[string]map[string]any{}
	if len(listValue(packet["source_materials"])) > 0 {
		if _, present := requirements["source_requirements"]; !present && complete {
			return fmt.Errorf("materials require an explicit source_requirements ledger, which may be empty only for context-only sources")
		}
	}
	units := map[string]bool{}
	delivered := map[string]bool{}
	for _, item := range listValue(packet["source_materials"]) {
		material := mapValue(item)
		id := stringValue(material["id"])
		materials[id] = material
		reading := mapValue(material["reading"])
		if complete {
			checkLiveSource := mapValue(packet["quality_gate"])["status"] != "user_confirmed"
			if _, err := service.verifiedMaterialContent(slug, material, checkLiveSource); err != nil {
				return err
			}
		}
		for _, unit := range listValue(reading["units"]) {
			units[id+"/"+stringValue(mapValue(unit)["id"])] = true
		}
		for _, rawID := range listValue(reading["delivered_unit_ids"]) {
			key := id + "/" + stringValue(rawID)
			if !units[key] || delivered[key] {
				return fmt.Errorf("unknown or duplicate delivered material unit: %s", key)
			}
			delivered[key] = true
		}
	}
	if complete && len(delivered) != len(units) {
		return fmt.Errorf("source reading incomplete: delivered %d of %d units", len(delivered), len(units))
	}
	reqRefs := map[string]map[string]bool{}
	for _, item := range listValue(requirements["source_requirements"]) {
		req := mapValue(item)
		id := stringValue(req["id"])
		if complete && req["disposition"] == "unresolved" {
			return fmt.Errorf("source requirement %s is unresolved", id)
		}
		reqRefs[id] = map[string]bool{}
		for _, item := range listValue(req["source_refs"]) {
			ref := mapValue(item)
			key := stringValue(ref["material_id"]) + "/" + stringValue(ref["unit_id"])
			if !delivered[key] || reqRefs[id][key] {
				return fmt.Errorf("%s references an unread, unknown, stale or duplicate source unit %s", id, key)
			}
			reqRefs[id][key] = true
		}
	}
	disposed := map[string]bool{}
	mapped := map[string]map[string]bool{}
	for materialID, material := range materials {
		if value, present := material["unit_dispositions"]; present {
			if _, ok := value.([]any); !ok {
				return fmt.Errorf("unit_dispositions must be an array")
			}
		}
		for _, item := range listValue(material["unit_dispositions"]) {
			row := mapValue(item)
			key := materialID + "/" + stringValue(row["unit_id"])
			if !delivered[key] || disposed[key] {
				return fmt.Errorf("unit disposition references an unread, unknown or duplicate unit: %s", key)
			}
			disposed[key] = true
			ids, ok := row["requirement_ids"].([]any)
			if !ok {
				return fmt.Errorf("unit disposition requirement_ids must be an array")
			}
			switch row["disposition"] {
			case "context":
				if len(ids) != 0 || !discussionMaterialText(row["reason"]) {
					return fmt.Errorf("context unit needs a reason and no requirement_ids: %s", key)
				}
			case "requirements":
				if len(ids) == 0 {
					return fmt.Errorf("requirements unit needs requirement_ids: %s", key)
				}
			default:
				return fmt.Errorf("invalid unit disposition: %s", key)
			}
			mapped[key] = map[string]bool{}
			for _, value := range ids {
				id := stringValue(value)
				if !reqRefs[id][key] || mapped[key][id] {
					return fmt.Errorf("unit %s has unknown, duplicate or unbound requirement %s", key, id)
				}
				mapped[key][id] = true
			}
		}
	}
	if complete && len(disposed) != len(units) {
		return fmt.Errorf("source extraction incomplete: disposed %d of %d units", len(disposed), len(units))
	}
	if complete {
		for id, refs := range reqRefs {
			for key := range refs {
				if !mapped[key][id] {
					return fmt.Errorf("source requirement %s is missing from unit disposition %s", id, key)
				}
			}
		}
	}
	return nil
}
