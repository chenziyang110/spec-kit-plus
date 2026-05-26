package scanartifacts

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"math"
	"os"
	"path/filepath"
	"sort"
	"strings"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
)

type ValidateOptions struct {
	RequireStatusJSON bool
}

type Result struct {
	Status       string         `json:"status"`
	Gate         string         `json:"gate"`
	Readiness    string         `json:"readiness"`
	Errors       []string       `json:"errors"`
	Warnings     []string       `json:"warnings"`
	CheckedPaths []string       `json:"checked_paths"`
	Details      map[string]any `json:"details"`
}

type Package struct {
	Evidence      []EvidenceRow
	Nodes         []NodeRow
	Edges         []EdgeRow
	Observations  []ObservationRow
	CoveragePaths []string
	AcceptedGaps  map[string]bool
	Identities    IdentitySet
}

type Boundary struct {
	SchemaVersion         int
	LegacyRows            bool
	CandidatePaths        map[string]string
	IncludedPaths         map[string]bool
	ExcludedPaths         map[string]bool
	AmbiguousPaths        map[string]bool
	Dispositions          map[string]string
	Criticality           map[string]string
	ClassificationReasons map[string]string
	DecisionSource        map[string]string
}

type PacketValidationSummary struct {
	ResultCount int
	Outcomes    map[string]int
}

type queueRow struct {
	PacketID          string
	State             string
	AssignedPaths     []string
	ParentPacketID    string
	ResultHandoffPath string
}

type queueState struct {
	rowsByPacket        map[string]queueRow
	childrenByParent    map[string]bool
	returnedPackets     map[string]bool
	returnPathsByPacket map[string]string
	acceptedPaths       map[string]bool
	openGaps            []openGapClosure
}

type openGapClosure struct {
	PacketID       string
	ParentPacketID string
	SourcePacketID string
	Paths          []string
}

type IdentitySet struct {
	Evidence      map[string]bool `json:"evidence"`
	Nodes         map[string]bool `json:"nodes"`
	Edges         map[string]bool `json:"edges"`
	Observations  map[string]bool `json:"observations"`
	CoveragePaths map[string]bool `json:"coverage_paths"`
}

type EvidenceRow struct {
	ID          string
	SourceKind  string
	SourcePath  string
	CommitSHA   string
	Span        string
	Extractor   string
	ContentHash string
	Attrs       map[string]any
}

type EvidenceIndex map[string][]EvidenceRow

type NodeRow struct {
	ID          string
	Type        string
	Title       string
	Confidence  string
	Paths       []string
	EvidenceIDs []string
	Attrs       map[string]any
}

type EdgeRow struct {
	ID          string
	Type        string
	SourceID    string
	TargetID    string
	Confidence  string
	EvidenceIDs []string
	Attrs       map[string]any
}

type ObservationRow struct {
	ID              string
	ObservationType string
	Summary         string
	EvidenceIDs     []string
	Attrs           map[string]any
}

func Validate(paths rt.Paths, opts ValidateOptions) Result {
	_, result := Load(paths, opts)
	return result
}

func Load(paths rt.Paths, opts ValidateOptions) (Package, Result) {
	result := newResult(requiredArtifactPaths(opts))
	pkg := Package{Identities: newIdentitySet()}
	for _, rel := range result.CheckedPaths {
		full := filepath.Join(paths.Root, filepath.FromSlash(rel))
		info, err := os.Stat(full)
		if err != nil {
			result.Errors = append(result.Errors, "missing "+rel)
			continue
		}
		if requiredArtifactMustBeDirectory(rel) && !info.IsDir() {
			result.Errors = append(result.Errors, "required artifact must be a directory: "+rel)
			continue
		}
		if !info.IsDir() && filepath.Ext(full) == ".json" {
			if rel == ".specify/project-cognition/status.json" {
				if err := validateJSONObjectFile(full, filepath.Base(rel)); err != nil {
					result.Errors = append(result.Errors, err.Error())
				}
				continue
			}
			if _, err := readJSONFile(full, filepath.Base(rel)); err != nil {
				result.Errors = append(result.Errors, err.Error())
			}
		}
	}
	loadOptionalWorkbenchJSON(paths, &result, "capability-ledger.json")
	loadOptionalWorkbenchJSON(paths, &result, "control-ledger.json")
	loadEvidence(paths, &pkg, &result)
	loadNodes(paths, &pkg, &result)
	loadEdges(paths, &pkg, &result)
	normalizeEdgeEndpoints(&pkg)
	loadObservations(paths, &pkg, &result)
	loadCoverage(paths, &pkg, &result)
	pkg.AcceptedGaps = acceptedGapPaths(paths)
	boundary := loadBoundary(paths, &result)
	validateBoundaryCoverage(boundary, pkg, &result)
	queue := loadQueueState(paths, &result)
	validateScanPacketQueueFiles(paths, boundary, pkg, queue, &result)
	packetSummary := validateWorkerResults(paths, boundary, pkg, queue, &result)
	result.Errors = append(result.Errors, validateCoverageLedger(paths, "scan")...)
	buildIdentities(&pkg)
	if len(result.Errors) > 0 {
		result.Status = "blocked"
		result.Readiness = "blocked"
	}
	result.Details["required_artifacts"] = result.CheckedPaths
	result.Details["boundary"] = map[string]any{
		"candidate_count": len(boundary.CandidatePaths),
		"included_count":  len(boundary.IncludedPaths),
		"excluded_count":  len(boundary.ExcludedPaths),
		"ambiguous_count": len(boundary.AmbiguousPaths),
	}
	result.Details["scan_packet_results"] = map[string]any{
		"result_count": packetSummary.ResultCount,
		"outcomes":     packetSummary.Outcomes,
	}
	return pkg, result
}

func validateCoverageLedger(paths rt.Paths, owner string) []string {
	ledgerPath := filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json")
	payload, err := readJSONFile(ledgerPath, "coverage-ledger.json")
	if err != nil {
		return []string{err.Error()}
	}
	obj, ok := payload.(map[string]any)
	if !ok {
		return []string{"coverage-ledger.json must contain a top-level JSON object"}
	}
	if _, ok := obj["rows"].([]any); !ok {
		return []string{"coverage-ledger.json must define a top-level rows array"}
	}
	errors := []string{}
	if gaps, ok := obj["open_gaps"].([]any); ok {
		for _, gap := range gaps {
			gapObj, ok := gap.(map[string]any)
			if !ok {
				continue
			}
			reason := normalizedString(gapObj["reason"])
			status := normalizedString(gapObj["status"])
			if reason == "subagent_blocked" || status == "blocked" {
				errors = append(errors, "subagent_blocked coverage gap must be resolved before project cognition acceptance")
			}
		}
	}
	return errors
}

func validateJSONObjectFile(path string, label string) error {
	payload, err := readJSONFile(path, label)
	if err != nil {
		return err
	}
	if _, ok := payload.(map[string]any); !ok {
		return fmt.Errorf("%s must contain a top-level JSON object", label)
	}
	return nil
}

func newResult(checked []string) Result {
	return Result{
		Status:       "ok",
		Gate:         "scan_acceptance",
		Readiness:    "scan_ready",
		Errors:       []string{},
		Warnings:     []string{},
		CheckedPaths: checked,
		Details:      map[string]any{},
	}
}

func requiredArtifactPaths(opts ValidateOptions) []string {
	required := []string{
		".specify/project-cognition/evidence",
		".specify/project-cognition/provisional/nodes.json",
		".specify/project-cognition/provisional/edges.json",
		".specify/project-cognition/provisional/observations.json",
		".specify/project-cognition/coverage.json",
		".specify/project-cognition/workbench/map-scan.md",
		".specify/project-cognition/workbench/coverage-ledger.md",
		".specify/project-cognition/workbench/coverage-ledger.json",
		".specify/project-cognition/workbench/scan-packets",
		".specify/project-cognition/workbench/worker-results",
		".specify/project-cognition/workbench/map-state.md",
		".specify/project-cognition/workbench/repository-universe.json",
		".specify/project-cognition/workbench/scan-queue.json",
		".specify/project-cognition/workbench/handoff-ledger.json",
	}
	if opts.RequireStatusJSON {
		required = append(required, ".specify/project-cognition/status.json")
	}
	return required
}

func requiredArtifactMustBeDirectory(rel string) bool {
	switch rel {
	case ".specify/project-cognition/evidence",
		".specify/project-cognition/workbench/scan-packets",
		".specify/project-cognition/workbench/worker-results":
		return true
	default:
		return false
	}
}

func newIdentitySet() IdentitySet {
	return IdentitySet{
		Evidence:      map[string]bool{},
		Nodes:         map[string]bool{},
		Edges:         map[string]bool{},
		Observations:  map[string]bool{},
		CoveragePaths: map[string]bool{},
	}
}

func loadOptionalWorkbenchJSON(paths rt.Paths, result *Result, name string) {
	path := filepath.Join(paths.RuntimeDir, "workbench", name)
	if _, err := os.Stat(path); err != nil {
		return
	}
	if _, err := readJSONFile(path, name); err != nil {
		result.Errors = append(result.Errors, err.Error())
	}
}

func loadQueueState(paths rt.Paths, result *Result) queueState {
	state := queueState{
		rowsByPacket:        map[string]queueRow{},
		childrenByParent:    map[string]bool{},
		returnedPackets:     map[string]bool{},
		returnPathsByPacket: map[string]string{},
		acceptedPaths:       map[string]bool{},
		openGaps:            []openGapClosure{},
	}
	for path := range loadCoverageLedgerState(paths, result) {
		state.acceptedPaths[path] = true
	}
	state.openGaps = loadOpenGapClosures(paths, result)
	raw, err := readJSONFile(filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"), "scan-queue.json")
	if err != nil {
		result.Errors = append(result.Errors, err.Error())
	} else {
		rows, err := arrayRowsForKeys(raw, "packets", "rows", "queue")
		if err != nil {
			result.Errors = append(result.Errors, "scan-queue.json: "+err.Error())
		} else {
			for i, row := range rows {
				packetID := normalizedString(row["packet_id"])
				if packetID == "" {
					result.Errors = append(result.Errors, fmt.Sprintf("scan-queue.json rows[%d] is missing packet_id", i))
					continue
				}
				if state.rowsByPacket[packetID].PacketID != "" {
					result.Errors = append(result.Errors, fmt.Sprintf("scan-queue.json packet_id %s appears more than once", packetID))
					continue
				}
				parentPacketID := normalizedString(row["parent_packet_id"])
				if parentPacketID != "" {
					state.childrenByParent[parentPacketID] = true
				}
				state.rowsByPacket[packetID] = queueRow{
					PacketID:          packetID,
					State:             normalizedString(row["state"]),
					AssignedPaths:     normalizedStringSlice(row["assigned_paths"]),
					ParentPacketID:    parentPacketID,
					ResultHandoffPath: normalizedString(row["result_handoff_path"]),
				}
			}
		}
	}
	rawEvents, err := readJSONFile(filepath.Join(paths.RuntimeDir, "workbench", "handoff-ledger.json"), "handoff-ledger.json")
	if err != nil {
		result.Errors = append(result.Errors, err.Error())
		return state
	}
	events, err := arrayRowsForKeys(rawEvents, "events", "rows", "handoffs")
	if err != nil {
		result.Errors = append(result.Errors, "handoff-ledger.json: "+err.Error())
		return state
	}
	for i, event := range events {
		packetID := normalizedString(event["packet_id"])
		if packetID == "" {
			result.Errors = append(result.Errors, fmt.Sprintf("handoff-ledger.json events[%d] is missing packet_id", i))
			continue
		}
		eventType := normalizedString(event["event_type"])
		if eventType == "returned" || eventType == "return" {
			state.returnedPackets[packetID] = true
			if path := firstNormalizedString(event, "worker_result_path", "result_handoff_path"); path != "" {
				state.returnPathsByPacket[packetID] = path
			}
		}
	}
	return state
}

func loadCoverageLedgerState(paths rt.Paths, result *Result) map[string]bool {
	accepted := map[string]bool{}
	raw, err := readJSONFile(filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json"), "coverage-ledger.json")
	if err != nil {
		result.Errors = append(result.Errors, err.Error())
		return accepted
	}
	obj, ok := raw.(map[string]any)
	if !ok {
		result.Errors = append(result.Errors, "coverage-ledger.json must contain a top-level JSON object")
		return accepted
	}
	rows, ok := obj["rows"].([]any)
	if !ok {
		result.Errors = append(result.Errors, "coverage-ledger.json must define a top-level rows array")
		return accepted
	}
	for i, row := range rows {
		obj, ok := row.(map[string]any)
		if !ok {
			continue
		}
		path := normalizedString(obj["path"])
		if path == "" {
			result.Errors = append(result.Errors, fmt.Sprintf("coverage-ledger.json rows[%d] is missing path", i))
			continue
		}
		if coverageLedgerRowIsAccepted(obj) {
			accepted[path] = true
		}
	}
	return accepted
}

func loadOpenGapClosures(paths rt.Paths, result *Result) []openGapClosure {
	closures := []openGapClosure{}
	raw, err := readJSONFile(filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json"), "coverage-ledger.json")
	if err != nil {
		return closures
	}
	obj, ok := raw.(map[string]any)
	if !ok {
		return closures
	}
	gaps, ok := obj["open_gaps"].([]any)
	if !ok {
		return closures
	}
	for i, gap := range gaps {
		obj, ok := gap.(map[string]any)
		if !ok {
			continue
		}
		if !openGapRowHasRequiredMetadata(obj) {
			if result != nil {
				result.Errors = append(result.Errors, fmt.Sprintf("coverage-ledger open_gaps[%d] is missing required metadata", i))
			}
			continue
		}
		paths := uniqueStrings(append(normalizedStringSlice(obj["paths"]), normalizedString(obj["path"])))
		packetID := normalizedString(obj["packet_id"])
		parentPacketID := normalizedString(obj["parent_packet_id"])
		sourcePacketID := normalizedString(obj["source_packet_id"])
		if len(paths) == 0 && packetID == "" && parentPacketID == "" && sourcePacketID == "" {
			if result != nil {
				result.Errors = append(result.Errors, fmt.Sprintf("coverage-ledger open_gaps[%d] is missing affected paths or packet linkage", i))
			}
			continue
		}
		status := normalizedString(obj["status"])
		coverageState := normalizedString(obj["coverage_state"])
		if status != "low_risk_open_gap" && coverageState != "low_risk_open_gap" {
			continue
		}
		closures = append(closures, openGapClosure{
			PacketID:       packetID,
			ParentPacketID: parentPacketID,
			SourcePacketID: sourcePacketID,
			Paths:          paths,
		})
	}
	return closures
}

func coverageLedgerRowIsAccepted(obj map[string]any) bool {
	if status := normalizedString(obj["status"]); status != "" {
		switch status {
		case "read", "deep_read", "sampled", "inventory_only", "covered", "accepted":
			return true
		default:
			return false
		}
	}
	if rowState := normalizedString(obj["state"]); rowState != "" {
		switch rowState {
		case "read", "deep_read", "sampled", "inventory_only", "covered", "accepted":
			return true
		default:
			return false
		}
	}
	if coverageState := normalizedString(obj["coverage_state"]); coverageState != "" {
		switch coverageState {
		case "read", "deep_read", "sampled", "inventory_only", "covered", "accepted":
			return true
		default:
			return false
		}
	}
	if outcome := normalizedString(obj["outcome"]); outcome != "" {
		switch outcome {
		case "read", "deep_read", "sampled", "inventory_only":
			return true
		default:
			return false
		}
	}
	if accepted := normalizedString(obj["accepted"]); accepted != "" {
		return accepted == "true"
	}
	return false
}

func openGapRowHasRequiredMetadata(obj map[string]any) bool {
	return normalizedString(obj["owner"]) != "" &&
		normalizedString(obj["reason"]) != "" &&
		normalizedString(obj["evidence_expectation"]) != "" &&
		normalizedString(obj["revisit_condition"]) != ""
}

func loadEvidence(paths rt.Paths, pkg *Package, result *Result) {
	evidenceDir := filepath.Join(paths.RuntimeDir, "evidence")
	entries, err := os.ReadDir(evidenceDir)
	if err != nil {
		return
	}
	sort.Slice(entries, func(i, j int) bool { return entries[i].Name() < entries[j].Name() })
	for _, entry := range entries {
		if entry.IsDir() || filepath.Ext(entry.Name()) != ".json" {
			continue
		}
		path := filepath.Join(evidenceDir, entry.Name())
		raw, err := readJSONFile(path, filepath.ToSlash(path))
		if err != nil {
			result.Errors = append(result.Errors, err.Error())
			continue
		}
		rows, err := evidenceRows(raw)
		if err != nil {
			result.Errors = append(result.Errors, filepath.ToSlash(path)+": "+err.Error())
			continue
		}
		stem := strings.TrimSuffix(entry.Name(), filepath.Ext(entry.Name()))
		for i, row := range rows {
			item := evidenceFromObject(row, stem, i)
			if strings.HasPrefix(item.SourcePath, ".specify/") {
				result.Errors = append(result.Errors, ".specify/** must not enter project cognition graph evidence")
			}
			pkg.Evidence = append(pkg.Evidence, item)
		}
	}
}

func loadNodes(paths rt.Paths, pkg *Package, result *Result) {
	raw, err := readJSONFile(filepath.Join(paths.RuntimeDir, "provisional", "nodes.json"), "nodes.json")
	if err != nil {
		result.Errors = append(result.Errors, err.Error())
		return
	}
	rows, err := arrayRows(raw, "nodes")
	if err != nil {
		result.Errors = append(result.Errors, "nodes.json: "+err.Error())
		return
	}
	for i, row := range rows {
		attrs := objectMapFromAliases(row, "attrs", "attrs_json")
		item := NodeRow{
			ID:          normalizedIdentityString(firstValue(row, "id", "node_id")),
			Type:        firstNormalizedString(row, "type", "kind"),
			Title:       firstNormalizedString(row, "title", "label", "name"),
			Confidence:  normalizedString(row["confidence"]),
			Paths:       nodePaths(row, attrs),
			EvidenceIDs: evidenceRefs(row),
			Attrs:       attrs,
		}
		if item.ID == "" {
			item.ID = generatedRowID("N", row, i, item.Type, item.Title, strings.Join(item.Paths, "|"))
		}
		pkg.Nodes = append(pkg.Nodes, item)
	}
}

func loadEdges(paths rt.Paths, pkg *Package, result *Result) {
	raw, err := readJSONFile(filepath.Join(paths.RuntimeDir, "provisional", "edges.json"), "edges.json")
	if err != nil {
		result.Errors = append(result.Errors, err.Error())
		return
	}
	rows, err := arrayRows(raw, "edges")
	if err != nil {
		result.Errors = append(result.Errors, "edges.json: "+err.Error())
		return
	}
	for i, row := range rows {
		item := EdgeRow{
			ID:          normalizedIdentityString(row["id"]),
			Type:        firstNormalizedString(row, "type", "kind", "relation"),
			SourceID:    firstNormalizedString(row, "source_id", "source", "source_node_id"),
			TargetID:    firstNormalizedString(row, "target_id", "target", "target_node_id"),
			Confidence:  normalizedString(row["confidence"]),
			EvidenceIDs: evidenceRefs(row),
			Attrs:       objectMapFromAliases(row, "attrs", "attrs_json"),
		}
		if item.ID == "" {
			item.ID = generatedRowID("EDGE", row, i, item.Type, item.SourceID, item.TargetID)
		}
		pkg.Edges = append(pkg.Edges, item)
	}
}

func loadObservations(paths rt.Paths, pkg *Package, result *Result) {
	raw, err := readJSONFile(filepath.Join(paths.RuntimeDir, "provisional", "observations.json"), "observations.json")
	if err != nil {
		result.Errors = append(result.Errors, err.Error())
		return
	}
	rows, err := looseObjectRows(raw, "observations", normalizeObservationRow)
	if err != nil {
		result.Errors = append(result.Errors, "observations.json: "+err.Error())
		return
	}
	for i, row := range rows {
		item := ObservationRow{
			ID:              normalizedIdentityString(firstValue(row, "id", "observation_id")),
			ObservationType: firstNormalizedString(row, "observation_type", "type", "kind"),
			Summary:         firstNormalizedString(row, "summary", "content", "text"),
			EvidenceIDs:     evidenceRefs(row),
			Attrs:           objectMapFromAliases(row, "attrs", "attrs_json"),
		}
		if item.ID == "" {
			item.ID = generatedRowID("OBS", row, i, item.ObservationType, item.Summary)
		}
		if item.ObservationType == "" {
			item.ObservationType = "note"
		}
		pkg.Observations = append(pkg.Observations, item)
	}
}

func normalizeEdgeEndpoints(pkg *Package) {
	nodeIDs := nodeIDSet(pkg.Nodes)
	pathOwners := nodeIDsByPath(pkg.Nodes)
	for i := range pkg.Edges {
		pkg.Edges[i].SourceID = resolveEdgeEndpoint(pkg.Edges[i].SourceID, nodeIDs, pathOwners)
		pkg.Edges[i].TargetID = resolveEdgeEndpoint(pkg.Edges[i].TargetID, nodeIDs, pathOwners)
	}
}

func nodeIDSet(nodes []NodeRow) map[string]bool {
	out := map[string]bool{}
	for _, node := range nodes {
		out[node.ID] = true
	}
	return out
}

func nodeIDsByPath(nodes []NodeRow) map[string][]string {
	out := map[string][]string{}
	for _, node := range nodes {
		for _, path := range node.Paths {
			out[path] = append(out[path], node.ID)
		}
	}
	return out
}

func resolveEdgeEndpoint(endpoint string, nodeIDs map[string]bool, pathOwners map[string][]string) string {
	if nodeIDs[endpoint] {
		return endpoint
	}
	owners := pathOwners[endpoint]
	if len(owners) == 1 {
		return owners[0]
	}
	return endpoint
}

func loadCoverage(paths rt.Paths, pkg *Package, result *Result) {
	raw, err := readJSONFile(filepath.Join(paths.RuntimeDir, "coverage.json"), "coverage.json")
	if err != nil {
		result.Errors = append(result.Errors, err.Error())
		return
	}
	rows, err := mergedArrayRowsForKeys(raw, "rows", "coverage")
	if err != nil {
		result.Errors = append(result.Errors, "coverage.json must define a top-level rows or coverage array")
		return
	}
	for i, row := range rows {
		path := normalizedString(row["path"])
		if path == "" {
			result.Errors = append(result.Errors, fmt.Sprintf("coverage.json rows[%d] is missing path", i))
			continue
		}
		if strings.HasPrefix(path, ".specify/") {
			result.Errors = append(result.Errors, ".specify/** must not enter project cognition graph evidence")
			continue
		}
		pkg.CoveragePaths = append(pkg.CoveragePaths, path)
	}
}

func loadBoundary(paths rt.Paths, result *Result) Boundary {
	boundary := Boundary{
		CandidatePaths:        map[string]string{},
		IncludedPaths:         map[string]bool{},
		ExcludedPaths:         map[string]bool{},
		AmbiguousPaths:        map[string]bool{},
		Dispositions:          map[string]string{},
		ClassificationReasons: map[string]string{},
		DecisionSource:        map[string]string{},
		Criticality:           map[string]string{},
	}
	raw, err := readJSONFile(filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), "repository-universe.json")
	if err != nil {
		result.Errors = append(result.Errors, err.Error())
		return boundary
	}
	obj, ok := raw.(map[string]any)
	if !ok {
		result.Errors = append(result.Errors, "repository-universe.json must contain a top-level JSON object")
		return boundary
	}
	if !isVersionedBoundaryObject(obj) {
		boundary.LegacyRows = true
		boundary.CandidatePaths = boundaryCandidatePaths(obj["rows"])
		for path := range boundary.CandidatePaths {
			boundary.IncludedPaths[path] = true
			boundary.CandidatePaths[path] = "inventory_only"
			boundary.Dispositions[path] = "inventory_only"
		}
		return boundary
	}
	validateVersionedBoundaryShapes(obj, result)
	boundary.SchemaVersion = intFromValue(obj["schema_version"])
	boundary.CandidatePaths = boundaryCandidatePaths(obj["candidate_universe"])
	boundary.IncludedPaths = boundaryPathsFromValue(obj["included_paths"])
	boundary.ExcludedPaths = boundaryPathsFromValue(obj["excluded_paths"])
	boundary.AmbiguousPaths = boundaryPathsFromValue(obj["ambiguous_paths"])
	boundary.Dispositions = boundaryDispositionMap(obj["dispositions"])
	boundary.Criticality = boundaryDispositionMap(obj["criticality"])
	boundary.ClassificationReasons = boundaryDispositionMap(obj["classification_reasons"])
	boundary.DecisionSource = boundaryDispositionMap(obj["decision_source"])
	return boundary
}

func isVersionedBoundaryObject(obj map[string]any) bool {
	for _, key := range []string{
		"schema_version",
		"candidate_universe",
		"included_paths",
		"excluded_paths",
		"ambiguous_paths",
		"dispositions",
		"classification_reasons",
		"decision_source",
	} {
		if _, ok := obj[key]; ok {
			return true
		}
	}
	return false
}

func validateVersionedBoundaryShapes(obj map[string]any, result *Result) {
	schemaVersion, ok := obj["schema_version"]
	if !ok {
		result.Errors = append(result.Errors, "repository-universe schema_version is required")
	} else if !isNumericSchemaVersion(schemaVersion) {
		result.Errors = append(result.Errors, "repository-universe schema_version must be a number")
	}
	for _, key := range []string{"candidate_universe", "included_paths", "excluded_paths", "ambiguous_paths"} {
		if _, ok := obj[key].([]any); !ok {
			result.Errors = append(result.Errors, fmt.Sprintf("repository-universe %s must be an array", key))
		}
	}
	for _, key := range []string{"dispositions", "criticality", "classification_reasons", "decision_source"} {
		if _, ok := obj[key].(map[string]any); !ok {
			result.Errors = append(result.Errors, fmt.Sprintf("repository-universe %s must be an object", key))
		}
	}
}

func isNumericSchemaVersion(value any) bool {
	switch typed := value.(type) {
	case float64:
		return typed == math.Trunc(typed)
	case int:
		return true
	default:
		return false
	}
}

func boundaryPathsFromValue(value any) map[string]bool {
	paths := map[string]bool{}
	rows, ok := value.([]any)
	if !ok {
		return paths
	}
	for _, row := range rows {
		path := ""
		switch typed := row.(type) {
		case string:
			path = normalizedString(typed)
		case map[string]any:
			path = normalizedString(typed["path"])
		}
		if path != "" {
			paths[path] = true
		}
	}
	return paths
}

func boundaryDispositionMap(value any) map[string]string {
	values := map[string]string{}
	obj, ok := value.(map[string]any)
	if !ok {
		return values
	}
	for rawPath, rawValue := range obj {
		path := normalizedString(rawPath)
		item := normalizedString(rawValue)
		if path != "" && item != "" {
			values[path] = item
		}
	}
	return values
}

func boundaryCandidatePaths(value any) map[string]string {
	paths := map[string]string{}
	rows, ok := value.([]any)
	if !ok {
		return paths
	}
	for _, row := range rows {
		path := ""
		disposition := ""
		switch typed := row.(type) {
		case string:
			path = normalizedString(typed)
		case map[string]any:
			path = normalizedString(typed["path"])
			disposition = normalizedString(typed["disposition"])
		}
		if path != "" {
			paths[path] = disposition
		}
	}
	return paths
}

func validateBoundaryCoverage(boundary Boundary, pkg Package, result *Result) {
	if boundary.LegacyRows {
		return
	}
	coveragePaths := map[string]bool{}
	for _, path := range pkg.CoveragePaths {
		coveragePaths[path] = true
	}
	acceptedGaps := pkg.AcceptedGaps
	if acceptedGaps == nil {
		acceptedGaps = map[string]bool{}
	}
	validateBoundaryListCandidates("included", boundary.IncludedPaths, boundary.CandidatePaths, result)
	validateBoundaryListCandidates("excluded", boundary.ExcludedPaths, boundary.CandidatePaths, result)
	validateBoundaryListCandidates("ambiguous", boundary.AmbiguousPaths, boundary.CandidatePaths, result)
	validateCoveragePathsInBoundary(coveragePaths, boundary, result)
	for path, candidateDisposition := range boundary.CandidatePaths {
		disposition := boundary.Dispositions[path]
		if disposition != "" && candidateDisposition != "" && disposition != candidateDisposition {
			result.Errors = append(result.Errors, fmt.Sprintf("repository-universe candidate path %s disposition %s conflicts with dispositions map %s", path, candidateDisposition, disposition))
			continue
		}
		if disposition == "" {
			disposition = candidateDisposition
		}
		if disposition == "" {
			result.Errors = append(result.Errors, fmt.Sprintf("repository-universe candidate path %s has no disposition", path))
			continue
		}
		if !validBoundaryDisposition(disposition) {
			result.Errors = append(result.Errors, fmt.Sprintf("repository-universe candidate path %s has invalid disposition %s", path, disposition))
			continue
		}
		criticality := boundary.Criticality[path]
		if criticality == "" {
			result.Errors = append(result.Errors, fmt.Sprintf("repository-universe candidate path %s has no criticality", path))
		} else if !validBoundaryCriticality(criticality) {
			result.Errors = append(result.Errors, fmt.Sprintf("repository-universe candidate path %s has invalid criticality %s", path, criticality))
		}
		if boundaryListMembershipCount(path, boundary) != 1 {
			result.Errors = append(result.Errors, fmt.Sprintf("repository-universe candidate path %s must appear in exactly one boundary list", path))
		}
		switch {
		case includedDispositionRequiresCoverage(disposition):
			if !boundary.IncludedPaths[path] {
				result.Errors = append(result.Errors, fmt.Sprintf("repository-universe candidate path %s with disposition %s must be listed in included_paths", path, disposition))
			}
			if !coveragePaths[path] && !acceptedGaps[path] {
				result.Errors = append(result.Errors, fmt.Sprintf("repository-universe included path %s has no coverage row or accepted gap", path))
			}
		case disposition == "excluded":
			if !boundary.ExcludedPaths[path] {
				result.Errors = append(result.Errors, fmt.Sprintf("repository-universe candidate path %s with excluded disposition must be listed in excluded_paths", path))
			}
			if coveragePaths[path] {
				result.Errors = append(result.Errors, fmt.Sprintf("excluded path %s must not appear in coverage.json", path))
			}
		case disposition == "blocked":
			if !boundary.AmbiguousPaths[path] {
				result.Errors = append(result.Errors, fmt.Sprintf("repository-universe candidate path %s with blocked disposition must be listed in ambiguous_paths", path))
			}
		}
	}
	for path := range boundary.IncludedPaths {
		if boundary.ExcludedPaths[path] {
			result.Errors = append(result.Errors, fmt.Sprintf("repository-universe path %s must not appear in both included_paths and excluded_paths", path))
		}
		if boundary.AmbiguousPaths[path] {
			result.Errors = append(result.Errors, fmt.Sprintf("repository-universe path %s must not appear in both included_paths and ambiguous_paths", path))
		}
	}
	for path := range boundary.ExcludedPaths {
		if boundary.AmbiguousPaths[path] {
			result.Errors = append(result.Errors, fmt.Sprintf("repository-universe path %s must not appear in both excluded_paths and ambiguous_paths", path))
		}
	}
	for path := range boundary.IncludedPaths {
		disposition := boundary.Dispositions[path]
		if disposition == "" {
			disposition = boundary.CandidatePaths[path]
		}
		if disposition == "" {
			result.Errors = append(result.Errors, fmt.Sprintf("repository-universe included path %s has no disposition", path))
			continue
		}
		if !validBoundaryDisposition(disposition) {
			result.Errors = append(result.Errors, fmt.Sprintf("repository-universe included path %s has invalid disposition %s", path, disposition))
			continue
		}
		if includedDispositionRequiresCoverage(disposition) && !coveragePaths[path] && !acceptedGaps[path] {
			result.Errors = append(result.Errors, fmt.Sprintf("repository-universe included path %s has no coverage row or accepted gap", path))
		}
	}
	for path := range boundary.ExcludedPaths {
		disposition := boundary.Dispositions[path]
		if disposition == "" {
			disposition = boundary.CandidatePaths[path]
		}
		if disposition == "" {
			result.Errors = append(result.Errors, fmt.Sprintf("repository-universe excluded path %s has no disposition", path))
			continue
		}
		if !validBoundaryDisposition(disposition) {
			result.Errors = append(result.Errors, fmt.Sprintf("repository-universe excluded path %s has invalid disposition %s", path, disposition))
			continue
		}
		if disposition != "excluded" {
			result.Errors = append(result.Errors, fmt.Sprintf("repository-universe excluded path %s must have excluded disposition", path))
			continue
		}
		if coveragePaths[path] {
			result.Errors = append(result.Errors, fmt.Sprintf("excluded path %s must not appear in coverage.json", path))
		}
		validateExcludedPathNotInGraphArtifacts(path, pkg, result)
	}
}

func validateCoveragePathsInBoundary(coveragePaths map[string]bool, boundary Boundary, result *Result) {
	for path := range coveragePaths {
		disposition := boundary.Dispositions[path]
		if disposition == "" {
			disposition = boundary.CandidatePaths[path]
		}
		if _, ok := boundary.CandidatePaths[path]; !ok ||
			!boundary.IncludedPaths[path] ||
			!includedDispositionRequiresCoverage(disposition) {
			result.Errors = append(result.Errors, fmt.Sprintf("coverage path %s must be listed in repository-universe candidate_universe and included_paths with coverage-eligible disposition", path))
		}
	}
}

func validateWorkerResults(paths rt.Paths, boundary Boundary, pkg Package, queue queueState, result *Result) PacketValidationSummary {
	summary := PacketValidationSummary{Outcomes: map[string]int{}}
	packetIDs := validateScanPacketFiles(paths, result)
	resultsDir := filepath.Join(paths.RuntimeDir, "workbench", "worker-results")
	entries, err := os.ReadDir(resultsDir)
	if err != nil {
		result.Errors = append(result.Errors, fmt.Sprintf("read workbench/worker-results: %v", err))
		return summary
	}
	familyFailures := map[string]map[string]int{}
	jsonResultCount := 0
	resultIDs := map[string]bool{}
	for _, entry := range entries {
		if entry.IsDir() || filepath.Ext(entry.Name()) != ".json" {
			continue
		}
		fileStem := strings.TrimSuffix(entry.Name(), filepath.Ext(entry.Name()))
		jsonResultCount++
		packetPath := filepath.Join(resultsDir, entry.Name())
		raw, err := readJSONFile(packetPath, entry.Name())
		if err != nil {
			result.Errors = append(result.Errors, err.Error())
			continue
		}
		packet, ok := raw.(map[string]any)
		if !ok {
			result.Errors = append(result.Errors, entry.Name()+" must contain a top-level JSON object")
			continue
		}
		summary.ResultCount++
		packetID := normalizedString(packet["packet_id"])
		if packetID == "" {
			packetID = fileStem
		} else if packetID != fileStem {
			result.Errors = append(result.Errors, fmt.Sprintf("worker result %s packet_id %s must match file stem %s", entry.Name(), packetID, fileStem))
		}
		if resultIDs[packetID] {
			result.Errors = append(result.Errors, fmt.Sprintf("worker result packet_id %s appears more than once", packetID))
		}
		resultIDs[packetID] = true
		row := queue.rowsByPacket[packetID]
		if len(packetIDs) > 0 && !packetIDs[packetID] {
			result.Errors = append(result.Errors, fmt.Sprintf("worker result %s has no matching scan packet", entry.Name()))
		}
		if row.PacketID == "" {
			result.Errors = append(result.Errors, fmt.Sprintf("worker result %s has no matching scan-queue row", packetID))
		} else {
			validateQueueWorkerAssignedPaths(packetID, row, normalizedStringSlice(packet["assigned_paths"]), result)
			validateQueueResultHandoffPath(packetID, row, entry.Name(), result)
		}
		if !queue.returnedPackets[packetID] {
			result.Errors = append(result.Errors, fmt.Sprintf("worker result %s has no matching return event in handoff-ledger.json", packetID))
		} else {
			validateHandoffWorkerResultPath(packetID, queue.returnPathsByPacket[packetID], entry.Name(), result)
		}
		outcome := normalizedString(packet["acceptance"])
		if outcome == "" {
			outcome = normalizedString(packet["outcome"])
		}
		if outcome == "" {
			outcome = "pass"
		}
		summary.Outcomes[outcome]++
		validateScanPacket(packetID, packet, boundary, pkg, row, queue, result)
		familyID := normalizedString(packet["family_id"])
		if familyID == "" {
			familyID = normalizedString(packet["lane"])
		}
		if familyID == "" {
			familyID = packetID
		}
		if strings.HasPrefix(outcome, "fail_") {
			if familyFailures[familyID] == nil {
				familyFailures[familyID] = map[string]int{}
			}
			familyFailures[familyID][outcome]++
		}
	}
	if jsonResultCount == 0 {
		result.Errors = append(result.Errors, "workbench/worker-results must contain at least one packet result JSON file")
	}
	for packetID := range packetIDs {
		if !resultIDs[packetID] {
			result.Errors = append(result.Errors, fmt.Sprintf("scan packet %s has no matching worker result", packetID))
		}
	}
	for familyID, counts := range familyFailures {
		for outcome, count := range counts {
			if outcome != "fail_systemic" && count > 1 {
				result.Errors = append(result.Errors, fmt.Sprintf("packet family %s has repeated %s outcomes; escalate to fail_systemic", familyID, outcome))
			}
		}
	}
	return summary
}

func validateScanPacketFiles(paths rt.Paths, result *Result) map[string]bool {
	packetDir := filepath.Join(paths.RuntimeDir, "workbench", "scan-packets")
	entries, err := os.ReadDir(packetDir)
	if err != nil {
		result.Errors = append(result.Errors, fmt.Sprintf("read workbench/scan-packets: %v", err))
		return map[string]bool{}
	}
	packetIDs := map[string]bool{}
	for _, entry := range entries {
		if entry.IsDir() || filepath.Ext(entry.Name()) != ".md" {
			continue
		}
		packetID := strings.TrimSuffix(entry.Name(), filepath.Ext(entry.Name()))
		packetIDs[packetID] = true
	}
	if len(packetIDs) == 0 {
		result.Errors = append(result.Errors, "workbench/scan-packets must contain at least one scan packet Markdown file")
	}
	return packetIDs
}

func validateScanPacketQueueFiles(paths rt.Paths, _ Boundary, _ Package, queue queueState, result *Result) {
	packetIDs := validateScanPacketFiles(paths, result)
	for packetID := range packetIDs {
		row := queue.rowsByPacket[packetID]
		if row.PacketID == "" {
			result.Errors = append(result.Errors, fmt.Sprintf("scan packet %s has no matching scan-queue row", packetID))
		}
	}
	for packetID, row := range queue.rowsByPacket {
		if len(packetIDs) > 0 && !packetIDs[packetID] {
			result.Errors = append(result.Errors, fmt.Sprintf("scan-queue packet %s has no matching scan packet", packetID))
		}
		validateQueueRowAcceptedAssignedPaths(packetID, row, result)
		validateQueueRowCoverage(packetID, row, queue.acceptedPaths, result)
		validateQueueRowClosure(packetID, row, queue, result)
	}
}

func validateScanPacket(packetID string, packet map[string]any, boundary Boundary, pkg Package, row queueRow, queue queueState, result *Result) {
	assigned := normalizedStringSlice(packet["assigned_paths"])
	if len(assigned) == 0 {
		result.Errors = append(result.Errors, fmt.Sprintf("packet %s must define assigned_paths", packetID))
	}
	assignedSet := stringSet(assigned)
	ledger, ok := packet["ledger"].(map[string]any)
	if !ok {
		result.Errors = append(result.Errors, fmt.Sprintf("packet %s must define packet-local ledger", packetID))
	} else {
		validatePacketLedger(packetID, assignedSet, ledger, result)
	}
	coverageRows := packetCoverageRows(packet["coverage"])
	coverageByPath := map[string]map[string]any{}
	evidence := evidenceIndex(pkg)
	for i, row := range coverageRows {
		path := normalizedString(row["path"])
		if path == "" {
			result.Errors = append(result.Errors, fmt.Sprintf("packet %s coverage rows[%d] is missing path", packetID, i))
			continue
		}
		if !assignedSet[path] {
			result.Errors = append(result.Errors, fmt.Sprintf("packet %s coverage path %s is not in assigned_paths", packetID, path))
		}
		coverageByPath[path] = row
		validatePacketCoverageOutcome(packetID, path, row, boundary, pkg, result)
		validatePacketCoverageEvidence(packetID, path, row, evidence, result)
	}
	for _, path := range assigned {
		if _, ok := coverageByPath[path]; !ok && !ledgerAccountsForFinalPath(ledger, path) {
			result.Errors = append(result.Errors, fmt.Sprintf("packet %s assigned path %s has no declared final outcome", packetID, path))
		}
	}
	validatePacketPathsRead(packetID, packet, assignedSet, coverageByPath, result)
	validatePacketAcceptance(packetID, packet, assignedSet, ledger, coverageByPath, result)
	validateQueueRowCoverage(packetID, row, queue.acceptedPaths, result)
	validateQueueRowClosure(packetID, row, queue, result)
}

func validateQueueWorkerAssignedPaths(packetID string, row queueRow, workerAssigned []string, result *Result) {
	if row.PacketID == "" {
		return
	}
	queueAssigned := uniqueStrings(row.AssignedPaths)
	workerAssigned = uniqueStrings(workerAssigned)
	validateQueueRowAcceptedAssignedPaths(packetID, row, result)
	if !sameStringSet(queueAssigned, workerAssigned) {
		result.Errors = append(result.Errors, fmt.Sprintf("scan-queue packet %s assigned_paths must match worker result assigned_paths", packetID))
	}
}

func validateQueueResultHandoffPath(packetID string, row queueRow, resultFileName string, result *Result) {
	if row.ResultHandoffPath == "" || !workerResultPathMatches(row.ResultHandoffPath, resultFileName) {
		result.Errors = append(result.Errors, fmt.Sprintf("scan-queue packet %s result_handoff_path must match %s", packetID, canonicalWorkerResultPath(resultFileName)))
	}
}

func validateHandoffWorkerResultPath(packetID string, path string, resultFileName string, result *Result) {
	if path == "" {
		result.Errors = append(result.Errors, fmt.Sprintf("handoff-ledger return for packet %s worker_result_path must match %s", packetID, canonicalWorkerResultPath(resultFileName)))
		return
	}
	if !workerResultPathMatches(path, resultFileName) {
		result.Errors = append(result.Errors, fmt.Sprintf("handoff-ledger return for packet %s worker_result_path must match %s", packetID, canonicalWorkerResultPath(resultFileName)))
	}
}

func workerResultPathMatches(path string, resultFileName string) bool {
	normalized := normalizedString(path)
	for _, expected := range workerResultPathEquivalents(resultFileName) {
		if normalized == expected {
			return true
		}
	}
	return false
}

func workerResultPathEquivalents(resultFileName string) []string {
	canonical := canonicalWorkerResultPath(resultFileName)
	return []string{
		canonical,
		"workbench/worker-results/" + resultFileName,
	}
}

func canonicalWorkerResultPath(resultFileName string) string {
	return ".specify/project-cognition/workbench/worker-results/" + resultFileName
}

func sameStringSet(left []string, right []string) bool {
	leftSet := stringSet(left)
	rightSet := stringSet(right)
	if len(leftSet) != len(rightSet) {
		return false
	}
	for value := range leftSet {
		if !rightSet[value] {
			return false
		}
	}
	return true
}

func validateQueueRowAcceptedAssignedPaths(packetID string, row queueRow, result *Result) {
	if row.PacketID == "" || row.State != "accepted" {
		return
	}
	if len(uniqueStrings(row.AssignedPaths)) == 0 {
		result.Errors = append(result.Errors, fmt.Sprintf("scan-queue packet %s accepted state requires assigned_paths", packetID))
	}
}

func validateQueueRowCoverage(packetID string, row queueRow, accepted map[string]bool, result *Result) {
	if row.PacketID == "" || row.State != "accepted" {
		return
	}
	if accepted == nil {
		accepted = map[string]bool{}
	}
	for _, path := range row.AssignedPaths {
		if !accepted[path] {
			result.Errors = append(result.Errors, fmt.Sprintf("scan-queue packet %s accepted state requires accepted coverage for assigned path %s", packetID, path))
		}
	}
}

func validateQueueRowClosure(packetID string, row queueRow, queue queueState, result *Result) {
	if row.PacketID == "" {
		return
	}
	switch row.State {
	case "overflow", "blocked", "repack_required":
		if !queueRowHasOpenGap(row, queue) && !queue.childrenByParent[packetID] {
			result.Errors = append(result.Errors, fmt.Sprintf("scan-queue packet %s state %s requires an open coverage gap or child packet", packetID, row.State))
		}
	}
}

func queueRowHasOpenGap(row queueRow, queue queueState) bool {
	for _, closure := range queue.openGaps {
		if closure.PacketID != "" && closure.PacketID == row.PacketID {
			return true
		}
		if closure.ParentPacketID != "" && (closure.ParentPacketID == row.PacketID || closure.ParentPacketID == row.ParentPacketID) {
			return true
		}
		if closure.SourcePacketID != "" && closure.SourcePacketID == row.PacketID {
			return true
		}
	}
	return false
}

func validatePacketLedger(packetID string, assigned map[string]bool, ledger map[string]any, result *Result) {
	accounted := map[string]string{}
	for _, state := range []string{"todo", "doing", "done", "blocked", "overflow"} {
		if _, ok := ledger[state].([]any); !ok {
			result.Errors = append(result.Errors, fmt.Sprintf("packet %s ledger.%s must be an array", packetID, state))
			continue
		}
		for _, path := range normalizedStringSlice(ledger[state]) {
			if !assigned[path] {
				result.Errors = append(result.Errors, fmt.Sprintf("packet %s ledger path %s is not in assigned_paths", packetID, path))
			}
			if previous := accounted[path]; previous != "" {
				result.Errors = append(result.Errors, fmt.Sprintf("packet %s ledger path %s appears in both %s and %s", packetID, path, previous, state))
			}
			accounted[path] = state
		}
	}
	for path := range assigned {
		if accounted[path] == "" {
			result.Errors = append(result.Errors, fmt.Sprintf("packet %s assigned path %s is missing from packet-local ledger", packetID, path))
		}
	}
}

func validatePacketCoverageOutcome(packetID string, path string, row map[string]any, boundary Boundary, pkg Package, result *Result) {
	outcome := normalizedString(row["outcome"])
	if outcome == "" {
		result.Errors = append(result.Errors, fmt.Sprintf("packet %s path %s coverage outcome is required", packetID, path))
		return
	}
	if !validPacketOutcome(outcome) {
		result.Errors = append(result.Errors, fmt.Sprintf("packet %s path %s has invalid coverage outcome %s", packetID, path, outcome))
		return
	}
	disposition := boundaryDisposition(path, boundary)
	if outcome == "sampled" || outcome == "inventory_only" {
		if disposition != outcome {
			result.Errors = append(result.Errors, fmt.Sprintf("packet %s path %s outcome %s conflicts with repository-universe disposition %s", packetID, path, outcome, disposition))
		}
		if criticalityBlocksShallowOutcome(boundary.Criticality[path]) && !pkg.AcceptedGaps[path] {
			result.Errors = append(result.Errors, fmt.Sprintf("packet %s path %s outcome %s is not allowed for criticality %s without accepted gap", packetID, path, outcome, boundary.Criticality[path]))
		}
	}
	if outcome == "read" || outcome == "deep_read" {
		if len(evidenceRefs(row)) == 0 {
			result.Errors = append(result.Errors, fmt.Sprintf("packet %s path %s read outcome must include evidence_ids", packetID, path))
		}
	}
}

func validatePacketCoverageEvidence(packetID string, path string, row map[string]any, evidence EvidenceIndex, result *Result) {
	outcome := normalizedString(row["outcome"])
	if outcome != "read" && outcome != "deep_read" {
		return
	}
	evidenceIDs := evidenceRefs(row)
	if len(evidenceIDs) == 0 {
		return
	}
	matchesPath := false
	for _, evidenceID := range evidenceIDs {
		rows := evidence[evidenceID]
		if len(rows) == 0 {
			result.Errors = append(result.Errors, fmt.Sprintf("packet %s path %s references missing evidence_id %s", packetID, path, evidenceID))
			continue
		}
		for _, evidenceRow := range rows {
			if evidenceRow.SourcePath == path {
				matchesPath = true
			}
		}
	}
	if !matchesPath {
		result.Errors = append(result.Errors, fmt.Sprintf("packet %s path %s read outcome must reference evidence with matching source_path", packetID, path))
	}
}

func evidenceIndex(pkg Package) EvidenceIndex {
	index := EvidenceIndex{}
	for _, row := range pkg.Evidence {
		if row.ID == "" {
			continue
		}
		index[row.ID] = append(index[row.ID], row)
	}
	return index
}

func validatePacketAcceptance(packetID string, packet map[string]any, assigned map[string]bool, ledger map[string]any, coverageByPath map[string]map[string]any, result *Result) {
	acceptance := normalizedString(packet["acceptance"])
	if acceptance == "" {
		acceptance = normalizedString(packet["outcome"])
	}
	if acceptance == "" {
		acceptance = "pass"
	}
	if !validPacketAcceptance(acceptance) {
		result.Errors = append(result.Errors, fmt.Sprintf("packet %s has invalid acceptance %s", packetID, acceptance))
		return
	}
	switch acceptance {
	case "pass":
		if len(assigned) == 0 {
			return
		}
		if !packetHasConfidence(packet) {
			result.Errors = append(result.Errors, fmt.Sprintf("packet %s pass acceptance must include confidence", packetID))
		}
		for path := range assigned {
			row := coverageByPath[path]
			outcome := normalizedString(row["outcome"])
			if row == nil || outcome == "blocked" || outcome == "overflow" || outcome == "excluded" || outcome == "" {
				result.Errors = append(result.Errors, fmt.Sprintf("packet %s cannot pass with unresolved path %s", packetID, path))
			}
		}
	case "fail_gap":
		if !hasGapLedgerState(ledger) {
			result.Errors = append(result.Errors, fmt.Sprintf("packet %s fail_gap must be limited to blocked or overflow ledger paths", packetID))
		}
		result.Errors = append(result.Errors, fmt.Sprintf("packet %s failed coverage gate and must be repacked for missing, blocked, or overflow paths", packetID))
	case "fail_quality":
		if !hasRepackSubset(packet["repack_subset"]) {
			result.Errors = append(result.Errors, fmt.Sprintf("packet %s fail_quality must include repack subset paths, claim_ids, coverage_row_ids, or evidence_ids", packetID))
		} else {
			result.Errors = append(result.Errors, fmt.Sprintf("packet %s failed quality gate for repack subset", packetID))
		}
	case "fail_contract", "fail_systemic":
		if requestsLocalPatch(packet) {
			result.Errors = append(result.Errors, fmt.Sprintf("packet %s acceptance %s must not request local patch redispatch", packetID, acceptance))
		}
		result.Errors = append(result.Errors, fmt.Sprintf("packet %s acceptance %s requires scan packet schema repair or packet-family repack", packetID, acceptance))
	}
}

func validatePacketPathsRead(packetID string, packet map[string]any, assigned map[string]bool, coverageByPath map[string]map[string]any, result *Result) {
	rawPathsRead, ok := packet["paths_read"]
	if !ok {
		result.Errors = append(result.Errors, fmt.Sprintf("packet %s must define paths_read as an array of concrete paths", packetID))
		return
	}
	if _, ok := rawPathsRead.([]any); !ok {
		result.Errors = append(result.Errors, fmt.Sprintf("packet %s paths_read must be an array of concrete paths", packetID))
		return
	}
	validateConcretePathArray(packetID, "paths_read", rawPathsRead, result)
	pathsRead := normalizedStringSlice(rawPathsRead)
	if len(pathsRead) == 0 && packetRequiresPathsRead(packet, coverageByPath) {
		result.Errors = append(result.Errors, fmt.Sprintf("packet %s paths_read must include at least one concrete path", packetID))
		return
	}
	pathsReadSet := stringSet(pathsRead)
	for _, path := range pathsRead {
		if !assigned[path] {
			result.Errors = append(result.Errors, fmt.Sprintf("packet %s paths_read path %s is not in assigned_paths", packetID, path))
		}
	}
	for path, row := range coverageByPath {
		outcome := normalizedString(row["outcome"])
		if (outcome == "read" || outcome == "deep_read") && !pathsReadSet[path] {
			result.Errors = append(result.Errors, fmt.Sprintf("packet %s path %s has read outcome but is missing from paths_read", packetID, path))
		}
	}
}

func validateConcretePathArray(packetID string, field string, value any, result *Result) {
	raw, ok := value.([]any)
	if !ok {
		return
	}
	for i, item := range raw {
		text, ok := item.(string)
		if !ok || normalizedString(text) == "" {
			result.Errors = append(result.Errors, fmt.Sprintf("packet %s %s[%d] must be a concrete path string", packetID, field, i))
		}
	}
}

func packetRequiresPathsRead(packet map[string]any, coverageByPath map[string]map[string]any) bool {
	acceptance := normalizedString(packet["acceptance"])
	if acceptance == "" {
		acceptance = normalizedString(packet["outcome"])
	}
	if acceptance == "" || acceptance == "pass" {
		return true
	}
	for _, row := range coverageByPath {
		outcome := normalizedString(row["outcome"])
		if outcome == "read" || outcome == "deep_read" {
			return true
		}
	}
	return false
}

func packetHasConfidence(packet map[string]any) bool {
	for _, key := range []string{"confidence", "confidence_level"} {
		if normalizedString(packet[key]) != "" {
			return true
		}
	}
	return false
}

func packetCoverageRows(value any) []map[string]any {
	rows, ok := value.([]any)
	if !ok {
		return []map[string]any{}
	}
	objects, err := objectRows(rows)
	if err != nil {
		return []map[string]any{}
	}
	return objects
}

func ledgerAccountsForFinalPath(ledger map[string]any, path string) bool {
	for _, state := range []string{"done", "blocked", "overflow"} {
		for _, item := range normalizedStringSlice(ledger[state]) {
			if item == path {
				return true
			}
		}
	}
	return false
}

func hasGapLedgerState(ledger map[string]any) bool {
	return len(normalizedStringSlice(ledger["blocked"])) > 0 || len(normalizedStringSlice(ledger["overflow"])) > 0
}

func hasRepackSubset(value any) bool {
	obj, ok := value.(map[string]any)
	if !ok {
		return false
	}
	for _, key := range []string{"paths", "claim_ids", "coverage_row_ids", "evidence_ids"} {
		if len(normalizedStringSlice(obj[key])) > 0 {
			return true
		}
	}
	return false
}

func requestsLocalPatch(packet map[string]any) bool {
	for _, key := range []string{"redispatch", "retry", "repair_strategy"} {
		value := normalizedString(packet[key])
		if value == "local_patch" || value == "local_patch_only" {
			return true
		}
	}
	return false
}

func boundaryDisposition(path string, boundary Boundary) string {
	disposition := boundary.Dispositions[path]
	if disposition == "" {
		disposition = boundary.CandidatePaths[path]
	}
	return disposition
}

func criticalityBlocksShallowOutcome(criticality string) bool {
	switch criticality {
	case "critical", "important":
		return true
	default:
		return false
	}
}

func validPacketOutcome(outcome string) bool {
	switch outcome {
	case "read", "deep_read", "sampled", "inventory_only", "blocked", "excluded", "overflow":
		return true
	default:
		return false
	}
}

func validPacketAcceptance(acceptance string) bool {
	switch acceptance {
	case "pass", "fail_gap", "fail_quality", "fail_contract", "fail_systemic":
		return true
	default:
		return false
	}
}

func stringSet(values []string) map[string]bool {
	set := map[string]bool{}
	for _, value := range values {
		set[value] = true
	}
	return set
}

func validateExcludedPathNotInGraphArtifacts(path string, pkg Package, result *Result) {
	for _, row := range pkg.Evidence {
		if row.SourcePath == path {
			result.Errors = append(result.Errors, fmt.Sprintf("excluded path %s must not appear in evidence source paths", path))
		}
	}
	for _, row := range pkg.Nodes {
		for _, nodePath := range row.Paths {
			if nodePath == path {
				result.Errors = append(result.Errors, fmt.Sprintf("excluded path %s must not appear in node paths", path))
			}
		}
	}
	for _, row := range pkg.Edges {
		if row.SourceID == path || row.TargetID == path {
			result.Errors = append(result.Errors, fmt.Sprintf("excluded path %s must not appear in edge endpoints", path))
		}
	}
}

func boundaryListMembershipCount(path string, boundary Boundary) int {
	count := 0
	if boundary.IncludedPaths[path] {
		count++
	}
	if boundary.ExcludedPaths[path] {
		count++
	}
	if boundary.AmbiguousPaths[path] {
		count++
	}
	return count
}

func validateBoundaryListCandidates(label string, paths map[string]bool, candidates map[string]string, result *Result) {
	for path := range paths {
		if _, ok := candidates[path]; !ok {
			result.Errors = append(result.Errors, fmt.Sprintf("repository-universe %s path %s is missing from candidate_universe", label, path))
		}
	}
}

func acceptedGapPaths(paths rt.Paths) map[string]bool {
	accepted := map[string]bool{}
	raw, err := readJSONFile(filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json"), "coverage-ledger.json")
	if err != nil {
		return accepted
	}
	obj, ok := raw.(map[string]any)
	if !ok {
		return accepted
	}
	gaps, ok := obj["open_gaps"].([]any)
	if !ok {
		return accepted
	}
	for _, gap := range gaps {
		gapObj, ok := gap.(map[string]any)
		if !ok {
			continue
		}
		status := normalizedString(gapObj["status"])
		reason := normalizedString(gapObj["reason"])
		coverageState := normalizedString(gapObj["coverage_state"])
		if blockedGapStatusOrReason(status) || blockedGapStatusOrReason(reason) || blockedGapStatusOrReason(coverageState) {
			continue
		}
		if status != "low_risk_open_gap" && coverageState != "low_risk_open_gap" {
			continue
		}
		if normalizedString(gapObj["owner"]) == "" ||
			reason == "" ||
			normalizedString(gapObj["evidence_expectation"]) == "" ||
			normalizedString(gapObj["revisit_condition"]) == "" {
			continue
		}
		path := normalizedString(gapObj["path"])
		if path != "" {
			accepted[path] = true
		}
		for _, item := range normalizedStringSlice(gapObj["paths"]) {
			accepted[item] = true
		}
	}
	return accepted
}

func includedDispositionRequiresCoverage(disposition string) bool {
	switch disposition {
	case "deep_read", "sampled", "inventory_only":
		return true
	default:
		return false
	}
}

func validBoundaryDisposition(disposition string) bool {
	switch disposition {
	case "deep_read", "sampled", "inventory_only", "excluded", "blocked":
		return true
	default:
		return false
	}
}

func validBoundaryCriticality(criticality string) bool {
	switch criticality {
	case "critical", "important", "low_risk":
		return true
	default:
		return false
	}
}

func blockedGapStatusOrReason(value string) bool {
	switch value {
	case "blocked", "unknown", "subagent_blocked", "critical_open_gap":
		return true
	default:
		return false
	}
}

func buildIdentities(pkg *Package) {
	for _, row := range pkg.Evidence {
		pkg.Identities.Evidence[row.ID+"|"+row.SourcePath+"|"+row.ContentHash] = true
	}
	for _, row := range pkg.Nodes {
		pkg.Identities.Nodes[row.ID] = true
	}
	for _, row := range pkg.Edges {
		pkg.Identities.Edges[row.ID+"|"+row.SourceID+"|"+row.TargetID+"|"+row.Type] = true
	}
	for _, row := range pkg.Observations {
		pkg.Identities.Observations[row.ID] = true
	}
	for _, path := range pkg.CoveragePaths {
		pkg.Identities.CoveragePaths[path] = true
	}
}

func readJSONFile(path string, label string) (any, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("%s: %w", label, err)
	}
	if len(data) >= 3 && data[0] == 0xEF && data[1] == 0xBB && data[2] == 0xBF {
		return nil, fmt.Errorf("%s contains UTF-8 BOM", label)
	}
	var raw any
	if err := json.Unmarshal(data, &raw); err != nil {
		return nil, fmt.Errorf("%s: %w", label, err)
	}
	return raw, nil
}

func evidenceRows(raw any) ([]map[string]any, error) {
	if arr, ok := raw.([]any); ok {
		return objectRows(arr)
	}
	obj, ok := raw.(map[string]any)
	if !ok {
		return nil, fmt.Errorf("must contain a top-level JSON object or array")
	}
	for _, key := range []string{"rows", "evidence"} {
		if arr, ok := obj[key].([]any); ok {
			return objectRows(arr)
		}
	}
	return []map[string]any{obj}, nil
}

func arrayRows(raw any, key string) ([]map[string]any, error) {
	return arrayRowsForKeys(raw, key, "rows")
}

func arrayRowsForKeys(raw any, keys ...string) ([]map[string]any, error) {
	if arr, ok := raw.([]any); ok {
		return objectRows(arr)
	}
	obj, ok := raw.(map[string]any)
	if !ok {
		return nil, fmt.Errorf("must contain a top-level JSON object or array")
	}
	for _, candidate := range keys {
		if arr, ok := obj[candidate].([]any); ok {
			return objectRows(arr)
		}
	}
	return nil, fmt.Errorf("must define a top-level %s array", keys[0])
}

func mergedArrayRowsForKeys(raw any, keys ...string) ([]map[string]any, error) {
	if arr, ok := raw.([]any); ok {
		return objectRows(arr)
	}
	obj, ok := raw.(map[string]any)
	if !ok {
		return nil, fmt.Errorf("must contain a top-level JSON object or array")
	}
	merged := make([]any, 0)
	found := false
	for _, candidate := range keys {
		if arr, ok := obj[candidate].([]any); ok {
			found = true
			merged = append(merged, arr...)
		}
	}
	if found {
		return objectRows(merged)
	}
	return nil, fmt.Errorf("must define a top-level %s array", keys[0])
}

func looseObjectRows(raw any, key string, normalize func(any, int) (map[string]any, bool)) ([]map[string]any, error) {
	values, err := rawRowsForKeys(raw, key, "rows")
	if err != nil {
		return nil, err
	}
	objects := make([]map[string]any, 0, len(values))
	for i, row := range values {
		if obj, ok := normalize(row, i); ok {
			objects = append(objects, obj)
			continue
		}
		return nil, fmt.Errorf("rows[%d] must be an object", i)
	}
	return objects, nil
}

func rawRowsForKeys(raw any, keys ...string) ([]any, error) {
	if arr, ok := raw.([]any); ok {
		return arr, nil
	}
	obj, ok := raw.(map[string]any)
	if !ok {
		return nil, fmt.Errorf("must contain a top-level JSON object or array")
	}
	for _, candidate := range keys {
		if arr, ok := obj[candidate].([]any); ok {
			return arr, nil
		}
	}
	return nil, fmt.Errorf("must define a top-level %s array", keys[0])
}

func normalizeObservationRow(value any, _ int) (map[string]any, bool) {
	if obj, ok := value.(map[string]any); ok {
		return obj, true
	}
	if text := normalizedString(value); text != "" {
		return map[string]any{"summary": text, "observation_type": "note"}, true
	}
	return nil, false
}

func objectRows(rows []any) ([]map[string]any, error) {
	objects := make([]map[string]any, 0, len(rows))
	for i, row := range rows {
		obj, ok := row.(map[string]any)
		if !ok {
			return nil, fmt.Errorf("rows[%d] must be an object", i)
		}
		objects = append(objects, obj)
	}
	return objects, nil
}

func evidenceFromObject(row map[string]any, fileStem string, index int) EvidenceRow {
	id := firstNormalizedString(row, "id", "evidence_id")
	if id == "" {
		id = fmt.Sprintf("%s-%d", fileStem, index)
	}
	normalized := normalizedEvidenceObject(row)
	contentHash := normalizedString(row["content_hash"])
	if contentHash == "" {
		contentHash = hashNormalizedObject(normalized)
	}
	return EvidenceRow{
		ID:          id,
		SourceKind:  stringFromMap(normalized, "source_kind"),
		SourcePath:  stringFromMap(normalized, "source_path"),
		CommitSHA:   stringFromMap(normalized, "commit_sha"),
		Span:        stringFromMap(normalized, "span"),
		Extractor:   stringFromMap(normalized, "extractor"),
		ContentHash: contentHash,
		Attrs:       objectMapFromAliases(row, "attrs", "attrs_json"),
	}
}

func normalizedEvidenceObject(row map[string]any) map[string]any {
	normalized := make(map[string]any, len(row))
	for key, value := range row {
		normalized[key] = normalizeEvidenceValue(key, value)
	}
	return normalized
}

func normalizeEvidenceValue(key string, value any) any {
	switch typed := value.(type) {
	case string:
		if isEvidenceStringField(key) || isPathField(key) {
			return normalizedString(typed)
		}
		return typed
	case []any:
		values := make([]any, 0, len(typed))
		for _, item := range typed {
			values = append(values, normalizeEvidenceValue(key, item))
		}
		return values
	case map[string]any:
		values := make(map[string]any, len(typed))
		for childKey, item := range typed {
			values[childKey] = normalizeEvidenceValue(childKey, item)
		}
		return values
	default:
		return value
	}
}

func isEvidenceStringField(key string) bool {
	switch key {
	case "source_kind", "source_path", "commit_sha", "span", "extractor":
		return true
	default:
		return false
	}
}

func isPathField(key string) bool {
	return key == "path" || strings.HasSuffix(key, "_path") || strings.HasSuffix(key, "_paths")
}

func stringFromMap(values map[string]any, key string) string {
	text, _ := values[key].(string)
	return text
}

func firstNormalizedString(values map[string]any, keys ...string) string {
	for _, key := range keys {
		text := normalizedString(values[key])
		if text != "" {
			return text
		}
	}
	return ""
}

func firstValue(values map[string]any, keys ...string) any {
	for _, key := range keys {
		if value, ok := values[key]; ok {
			return value
		}
	}
	return nil
}

func hashNormalizedObject(obj map[string]any) string {
	data, err := json.Marshal(obj)
	if err != nil {
		return ""
	}
	sum := sha256.Sum256(data)
	return hex.EncodeToString(sum[:])
}

func objectMap(value any) map[string]any {
	obj, ok := value.(map[string]any)
	if !ok {
		return map[string]any{}
	}
	return obj
}

func objectMapFromAliases(row map[string]any, keys ...string) map[string]any {
	for _, key := range keys {
		if obj := objectMap(row[key]); len(obj) > 0 {
			return obj
		}
	}
	return map[string]any{}
}

func nodePaths(row map[string]any, attrs map[string]any) []string {
	paths := normalizedStringSlice(row["paths"])
	for _, key := range []string{"path", "source_path", "file_path"} {
		if path := normalizedString(row[key]); path != "" {
			paths = append(paths, path)
		}
		if path := normalizedString(attrs[key]); path != "" {
			paths = append(paths, path)
		}
	}
	return uniqueStrings(paths)
}

func intFromValue(value any) int {
	switch typed := value.(type) {
	case float64:
		return int(typed)
	case int:
		return typed
	default:
		return 0
	}
}

func normalizedStringSlice(value any) []string {
	raw, ok := value.([]any)
	if !ok {
		return []string{}
	}
	values := []string{}
	for _, item := range raw {
		text := normalizedString(item)
		if text != "" {
			values = append(values, text)
		}
	}
	return values
}

func evidenceRefs(row map[string]any) []string {
	values := normalizedStringSlice(row["evidence_ids"])
	if single := normalizedString(row["evidence_id"]); single != "" {
		values = append(values, single)
	}
	return uniqueStrings(values)
}

func uniqueStrings(values []string) []string {
	seen := map[string]bool{}
	out := make([]string, 0, len(values))
	for _, value := range values {
		if value == "" || seen[value] {
			continue
		}
		seen[value] = true
		out = append(out, value)
	}
	return out
}

func generatedRowID(prefix string, row map[string]any, index int, parts ...string) string {
	seed := strings.Join(parts, "\x00")
	if seed == strings.Repeat("\x00", len(parts)-1) {
		data, err := json.Marshal(row)
		if err == nil {
			seed = string(data)
		}
	}
	if seed == "" {
		seed = fmt.Sprintf("%d", index)
	}
	sum := sha256.Sum256([]byte(seed))
	return prefix + "-" + hex.EncodeToString(sum[:])[:16]
}

func normalizedIdentityString(value any) string {
	text := normalizedString(value)
	switch strings.ToUpper(text) {
	case "", "NO_ID", "UNKNOWN", "TBD", "NULL", "NONE":
		return ""
	default:
		return text
	}
}

func normalizedString(value any) string {
	text, _ := value.(string)
	text = filepath.ToSlash(strings.TrimSpace(text))
	return strings.TrimPrefix(text, "./")
}
