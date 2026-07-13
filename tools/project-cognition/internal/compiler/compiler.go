package compiler

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"path/filepath"
	"reflect"
	"sort"
	"strings"

	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/scanartifacts"
)

const ContractVersion = 1

const legacyProposalID = "legacy-scan-package"

type CognitionProposal struct {
	ProposalVersion    int
	ProposalID         string
	SourceGenerationID string
	Scope              []string
	Package            scanartifacts.Package
}

type CompiledProposal struct {
	Package scanartifacts.Package
}

type Decision struct {
	Category string `json:"category"`
	Identity string `json:"identity"`
	Reason   string `json:"reason"`
}

type MergeRecord struct {
	Category       string `json:"category"`
	SourceIdentity string `json:"source_identity"`
	TargetIdentity string `json:"target_identity"`
	Reason         string `json:"reason"`
}

type Result struct {
	ContractVersion     int            `json:"contract_version"`
	Status              string         `json:"status"`
	ProposalID          string         `json:"proposal_id"`
	ProposalFingerprint string         `json:"proposal_fingerprint"`
	CompiledFingerprint string         `json:"compiled_fingerprint"`
	Counts              map[string]int `json:"counts"`
	MergeRecords        []MergeRecord  `json:"merge_records"`
	Rejections          []Decision     `json:"rejections"`
	Conflicts           []Decision     `json:"conflicts"`
	Unknowns            []Decision     `json:"unknowns"`
	PublicationAllowed  bool           `json:"publication_allowed"`
}

func EmptyResult() Result {
	return Result{
		ContractVersion: ContractVersion,
		Status:          "not_run",
		Counts:          emptyCounts(),
		MergeRecords:    []MergeRecord{},
		Rejections:      []Decision{},
		Conflicts:       []Decision{},
		Unknowns:        []Decision{},
	}
}

func AdaptLegacy(pkg scanartifacts.Package) CognitionProposal {
	return CognitionProposal{
		ProposalVersion: ContractVersion,
		ProposalID:      legacyProposalID,
		Scope:           append([]string(nil), pkg.CoveragePaths...),
		Package:         pkg,
	}
}

func Compile(proposal CognitionProposal) (CompiledProposal, Result) {
	result := EmptyResult()
	result.Status = "compiled"
	result.ProposalID = strings.TrimSpace(proposal.ProposalID)
	if result.ProposalID == "" {
		result.ProposalID = legacyProposalID
	}

	canonicalProposal := canonicalizeProposal(proposal)
	result.ProposalFingerprint = fingerprint(canonicalProposal)
	if proposal.ProposalVersion != ContractVersion {
		result.Conflicts = append(result.Conflicts, Decision{
			Category: "proposal",
			Identity: result.ProposalID,
			Reason:   "unsupported_proposal_version",
		})
	}

	pkg := canonicalProposal.Package
	pkg.Evidence = mergeEvidence(pkg.Evidence, &result)
	pkg.Nodes = mergeNodes(pkg.Nodes, &result)
	pkg.Edges = mergeEdges(pkg.Edges, &result)
	pkg.Observations = mergeObservations(pkg.Observations, &result)
	pkg.CoveragePaths = uniqueSortedStrings(pkg.CoveragePaths)
	pkg.AcceptedGaps = cloneBoolMap(pkg.AcceptedGaps)

	validatePaths(pkg, &result)
	validateReferences(pkg, &result)
	rebuildIdentities(&pkg)
	sortDecisions(&result)

	result.Counts = packageCounts(pkg)
	result.PublicationAllowed = len(result.Conflicts) == 0
	if !result.PublicationAllowed {
		result.Status = "blocked"
	}
	result.CompiledFingerprint = fingerprint(struct {
		Package    scanartifacts.Package
		Merges     []MergeRecord
		Rejections []Decision
		Conflicts  []Decision
		Unknowns   []Decision
	}{pkg, result.MergeRecords, result.Rejections, result.Conflicts, result.Unknowns})

	return CompiledProposal{Package: pkg}, result
}

func canonicalizeProposal(proposal CognitionProposal) CognitionProposal {
	proposal.ProposalID = strings.TrimSpace(proposal.ProposalID)
	proposal.SourceGenerationID = strings.TrimSpace(proposal.SourceGenerationID)
	proposal.Scope = uniqueSortedStrings(proposal.Scope)
	pkg := clonePackage(proposal.Package)
	for i := range pkg.Evidence {
		pkg.Evidence[i].ID = strings.TrimSpace(pkg.Evidence[i].ID)
		pkg.Evidence[i].SourcePath = normalizePath(pkg.Evidence[i].SourcePath)
	}
	for i := range pkg.Nodes {
		pkg.Nodes[i].ID = strings.TrimSpace(pkg.Nodes[i].ID)
		pkg.Nodes[i].Paths = uniqueSortedPaths(pkg.Nodes[i].Paths)
		pkg.Nodes[i].CanonicalPaths = uniqueSortedPaths(pkg.Nodes[i].CanonicalPaths)
		pkg.Nodes[i].CompatibilityPaths = uniqueSortedPaths(pkg.Nodes[i].CompatibilityPaths)
		pkg.Nodes[i].EvidenceIDs = uniqueSortedStrings(pkg.Nodes[i].EvidenceIDs)
	}
	for i := range pkg.Edges {
		pkg.Edges[i].ID = strings.TrimSpace(pkg.Edges[i].ID)
		pkg.Edges[i].SourceID = strings.TrimSpace(pkg.Edges[i].SourceID)
		pkg.Edges[i].TargetID = strings.TrimSpace(pkg.Edges[i].TargetID)
		pkg.Edges[i].EvidenceIDs = uniqueSortedStrings(pkg.Edges[i].EvidenceIDs)
	}
	for i := range pkg.Observations {
		pkg.Observations[i].ID = strings.TrimSpace(pkg.Observations[i].ID)
		pkg.Observations[i].EvidenceIDs = uniqueSortedStrings(pkg.Observations[i].EvidenceIDs)
	}
	pkg.CoveragePaths = uniqueSortedPaths(pkg.CoveragePaths)
	sortRows(pkg.Evidence, func(row scanartifacts.EvidenceRow) string { return row.ID })
	sortRows(pkg.Nodes, func(row scanartifacts.NodeRow) string { return row.ID })
	sortRows(pkg.Edges, func(row scanartifacts.EdgeRow) string { return row.ID })
	sortRows(pkg.Observations, func(row scanartifacts.ObservationRow) string { return row.ID })
	proposal.Package = pkg
	return proposal
}

func mergeEvidence(rows []scanartifacts.EvidenceRow, result *Result) []scanartifacts.EvidenceRow {
	return mergeRows(rows, "evidence", func(row scanartifacts.EvidenceRow) string { return row.ID }, result)
}

func mergeNodes(rows []scanartifacts.NodeRow, result *Result) []scanartifacts.NodeRow {
	return mergeRows(rows, "node", func(row scanartifacts.NodeRow) string { return row.ID }, result)
}

func mergeEdges(rows []scanartifacts.EdgeRow, result *Result) []scanartifacts.EdgeRow {
	return mergeRows(rows, "edge", func(row scanartifacts.EdgeRow) string { return row.ID }, result)
}

func mergeObservations(rows []scanartifacts.ObservationRow, result *Result) []scanartifacts.ObservationRow {
	return mergeRows(rows, "observation", func(row scanartifacts.ObservationRow) string { return row.ID }, result)
}

func mergeRows[T any](rows []T, category string, identity func(T) string, result *Result) []T {
	out := make([]T, 0, len(rows))
	seen := map[string]T{}
	for _, row := range rows {
		id := identity(row)
		if id == "" {
			result.Conflicts = append(result.Conflicts, Decision{Category: category, Reason: "missing_identity"})
			continue
		}
		previous, exists := seen[id]
		if !exists {
			seen[id] = row
			out = append(out, row)
			continue
		}
		if reflect.DeepEqual(previous, row) {
			result.MergeRecords = append(result.MergeRecords, MergeRecord{
				Category:       category,
				SourceIdentity: id,
				TargetIdentity: id,
				Reason:         "duplicate_equivalent",
			})
			continue
		}
		result.Conflicts = append(result.Conflicts, Decision{Category: category, Identity: id, Reason: "identity_conflict"})
	}
	return out
}

func validatePaths(pkg scanartifacts.Package, result *Result) {
	for _, evidence := range pkg.Evidence {
		validatePath("evidence", evidence.ID, evidence.SourcePath, result)
	}
	for _, node := range pkg.Nodes {
		for _, candidate := range append(append(append([]string{}, node.Paths...), node.CanonicalPaths...), node.CompatibilityPaths...) {
			validatePath("node", node.ID, candidate, result)
		}
	}
	for _, candidate := range pkg.CoveragePaths {
		validatePath("coverage", candidate, candidate, result)
	}
}

func validatePath(category, identity, candidate string, result *Result) {
	if candidate == "" {
		return
	}
	normalized := normalizePath(candidate)
	reason := ""
	switch {
	case normalized == ".specify" || strings.HasPrefix(normalized, ".specify/"):
		reason = "reserved_runtime_path"
	case filepath.IsAbs(candidate) || filepath.VolumeName(candidate) != "":
		reason = "absolute_path"
	case normalized == ".." || strings.HasPrefix(normalized, "../"):
		reason = "path_outside_repository"
	}
	if reason != "" {
		result.Conflicts = append(result.Conflicts, Decision{Category: category, Identity: identity, Reason: reason})
	}
}

func validateReferences(pkg scanartifacts.Package, result *Result) {
	evidenceIDs := map[string]bool{}
	for _, evidence := range pkg.Evidence {
		evidenceIDs[evidence.ID] = true
	}
	nodeIDs := map[string]bool{}
	for _, node := range pkg.Nodes {
		nodeIDs[node.ID] = true
		validateEvidenceReferences("node", node.ID, node.EvidenceIDs, evidenceIDs, result)
		if len(node.EvidenceIDs) == 0 {
			result.Unknowns = append(result.Unknowns, Decision{Category: "node", Identity: node.ID, Reason: "no_evidence_reference"})
		}
	}
	for _, edge := range pkg.Edges {
		validateEvidenceReferences("edge", edge.ID, edge.EvidenceIDs, evidenceIDs, result)
		if !nodeIDs[edge.SourceID] {
			result.Conflicts = append(result.Conflicts, Decision{Category: "edge", Identity: edge.ID, Reason: "missing_source_node:" + edge.SourceID})
		}
		if !nodeIDs[edge.TargetID] {
			result.Conflicts = append(result.Conflicts, Decision{Category: "edge", Identity: edge.ID, Reason: "missing_target_node:" + edge.TargetID})
		}
	}
	for _, observation := range pkg.Observations {
		validateEvidenceReferences("observation", observation.ID, observation.EvidenceIDs, evidenceIDs, result)
	}
}

func validateEvidenceReferences(category, identity string, references []string, evidenceIDs map[string]bool, result *Result) {
	for _, evidenceID := range references {
		if !evidenceIDs[evidenceID] {
			result.Conflicts = append(result.Conflicts, Decision{Category: category, Identity: identity, Reason: "missing_evidence:" + evidenceID})
		}
	}
}

func rebuildIdentities(pkg *scanartifacts.Package) {
	identities := scanartifacts.IdentitySet{
		Evidence:      map[string]bool{},
		Nodes:         map[string]bool{},
		Edges:         map[string]bool{},
		Observations:  map[string]bool{},
		CoveragePaths: map[string]bool{},
	}
	for _, row := range pkg.Evidence {
		identities.Evidence[row.ID+"|"+row.SourcePath+"|"+row.ContentHash] = true
	}
	for _, row := range pkg.Nodes {
		identities.Nodes[row.ID] = true
	}
	for _, row := range pkg.Edges {
		identities.Edges[row.ID+"|"+row.SourceID+"|"+row.TargetID+"|"+row.Type] = true
	}
	for _, row := range pkg.Observations {
		identities.Observations[row.ID] = true
	}
	for _, candidate := range pkg.CoveragePaths {
		identities.CoveragePaths[candidate] = true
	}
	pkg.Identities = identities
}

func sortDecisions(result *Result) {
	result.MergeRecords = uniqueMergeRecords(result.MergeRecords)
	result.Rejections = uniqueDecisions(result.Rejections)
	result.Conflicts = uniqueDecisions(result.Conflicts)
	result.Unknowns = uniqueDecisions(result.Unknowns)
	sort.Slice(result.MergeRecords, func(i, j int) bool { return stableJSON(result.MergeRecords[i]) < stableJSON(result.MergeRecords[j]) })
	sort.Slice(result.Rejections, func(i, j int) bool { return stableJSON(result.Rejections[i]) < stableJSON(result.Rejections[j]) })
	sort.Slice(result.Conflicts, func(i, j int) bool { return stableJSON(result.Conflicts[i]) < stableJSON(result.Conflicts[j]) })
	sort.Slice(result.Unknowns, func(i, j int) bool { return stableJSON(result.Unknowns[i]) < stableJSON(result.Unknowns[j]) })
}

func uniqueDecisions(values []Decision) []Decision {
	seen := map[string]bool{}
	out := make([]Decision, 0, len(values))
	for _, value := range values {
		key := stableJSON(value)
		if seen[key] {
			continue
		}
		seen[key] = true
		out = append(out, value)
	}
	return out
}

func uniqueMergeRecords(values []MergeRecord) []MergeRecord {
	seen := map[string]bool{}
	out := make([]MergeRecord, 0, len(values))
	for _, value := range values {
		key := stableJSON(value)
		if seen[key] {
			continue
		}
		seen[key] = true
		out = append(out, value)
	}
	return out
}

func sortRows[T any](rows []T, identity func(T) string) {
	sort.Slice(rows, func(i, j int) bool {
		leftID, rightID := identity(rows[i]), identity(rows[j])
		if leftID != rightID {
			return leftID < rightID
		}
		return stableJSON(rows[i]) < stableJSON(rows[j])
	})
}

func uniqueSortedPaths(values []string) []string {
	normalized := make([]string, 0, len(values))
	for _, value := range values {
		if candidate := normalizePath(value); candidate != "" {
			normalized = append(normalized, candidate)
		}
	}
	return uniqueSortedStrings(normalized)
}

func uniqueSortedStrings(values []string) []string {
	seen := map[string]bool{}
	out := make([]string, 0, len(values))
	for _, value := range values {
		value = strings.TrimSpace(value)
		if value == "" || seen[value] {
			continue
		}
		seen[value] = true
		out = append(out, value)
	}
	sort.Strings(out)
	return out
}

func normalizePath(value string) string {
	normalized := filepath.ToSlash(strings.TrimSpace(value))
	return strings.TrimPrefix(normalized, "./")
}

func cloneBoolMap(values map[string]bool) map[string]bool {
	out := make(map[string]bool, len(values))
	for key, value := range values {
		out[key] = value
	}
	return out
}

func clonePackage(pkg scanartifacts.Package) scanartifacts.Package {
	cloned := scanartifacts.Package{
		Evidence:      make([]scanartifacts.EvidenceRow, len(pkg.Evidence)),
		Nodes:         make([]scanartifacts.NodeRow, len(pkg.Nodes)),
		Edges:         make([]scanartifacts.EdgeRow, len(pkg.Edges)),
		Observations:  make([]scanartifacts.ObservationRow, len(pkg.Observations)),
		CoveragePaths: append([]string(nil), pkg.CoveragePaths...),
		AcceptedGaps:  cloneBoolMap(pkg.AcceptedGaps),
		Identities: scanartifacts.IdentitySet{
			Evidence:      cloneBoolMap(pkg.Identities.Evidence),
			Nodes:         cloneBoolMap(pkg.Identities.Nodes),
			Edges:         cloneBoolMap(pkg.Identities.Edges),
			Observations:  cloneBoolMap(pkg.Identities.Observations),
			CoveragePaths: cloneBoolMap(pkg.Identities.CoveragePaths),
		},
	}
	for i, row := range pkg.Evidence {
		row.Attrs = cloneAttrs(row.Attrs)
		cloned.Evidence[i] = row
	}
	for i, row := range pkg.Nodes {
		row.Paths = append([]string(nil), row.Paths...)
		row.CanonicalPaths = append([]string(nil), row.CanonicalPaths...)
		row.CompatibilityPaths = append([]string(nil), row.CompatibilityPaths...)
		row.EvidenceIDs = append([]string(nil), row.EvidenceIDs...)
		row.Attrs = cloneAttrs(row.Attrs)
		cloned.Nodes[i] = row
	}
	for i, row := range pkg.Edges {
		row.EvidenceIDs = append([]string(nil), row.EvidenceIDs...)
		row.Attrs = cloneAttrs(row.Attrs)
		cloned.Edges[i] = row
	}
	for i, row := range pkg.Observations {
		row.EvidenceIDs = append([]string(nil), row.EvidenceIDs...)
		row.Attrs = cloneAttrs(row.Attrs)
		cloned.Observations[i] = row
	}
	return cloned
}

func cloneAttrs(values map[string]any) map[string]any {
	if values == nil {
		return nil
	}
	out := make(map[string]any, len(values))
	for key, value := range values {
		out[key] = cloneValue(value)
	}
	return out
}

func cloneValue(value any) any {
	switch typed := value.(type) {
	case map[string]any:
		return cloneAttrs(typed)
	case []any:
		out := make([]any, len(typed))
		for i, item := range typed {
			out[i] = cloneValue(item)
		}
		return out
	case []string:
		return append([]string(nil), typed...)
	default:
		return value
	}
}

func packageCounts(pkg scanartifacts.Package) map[string]int {
	return map[string]int{
		"evidence":       len(pkg.Evidence),
		"nodes":          len(pkg.Nodes),
		"edges":          len(pkg.Edges),
		"observations":   len(pkg.Observations),
		"coverage_paths": len(pkg.CoveragePaths),
	}
}

func emptyCounts() map[string]int {
	return map[string]int{"evidence": 0, "nodes": 0, "edges": 0, "observations": 0, "coverage_paths": 0}
}

func fingerprint(value any) string {
	encoded, err := json.Marshal(value)
	if err != nil {
		return ""
	}
	sum := sha256.Sum256(encoded)
	return hex.EncodeToString(sum[:])
}

func stableJSON(value any) string {
	encoded, _ := json.Marshal(value)
	return string(encoded)
}
