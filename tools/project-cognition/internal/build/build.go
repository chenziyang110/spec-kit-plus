package build

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"time"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtimegate"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/scanartifacts"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/store"
)

const (
	rewriteStatusFromDBMetadata = "rewrite_status_from_db_metadata"
	graphStorePath              = ".specify/project-cognition/project-cognition.db"
)

var unsafeIDPartPattern = regexp.MustCompile(`[^A-Za-z0-9._-]+`)

type Payload struct {
	Status                 string                            `json:"status"`
	Readiness              string                            `json:"readiness"`
	Errors                 []string                          `json:"errors"`
	Warnings               []string                          `json:"warnings"`
	ScanArtifactCounts     map[string]int                    `json:"scan_artifact_counts"`
	DBCounts               map[string]int                    `json:"db_counts"`
	IdentityReconciliation map[string]ReconciliationCategory `json:"identity_reconciliation"`
	Rejections             []store.RowDecision               `json:"rejections"`
	MergeRecords           []store.MergeRecord               `json:"merge_records"`
	RecoveryAction         string                            `json:"recovery_action,omitempty"`
	StatusPath             string                            `json:"status_path"`
	GraphStorePath         string                            `json:"graph_store_path"`
	ActiveGenerationID     string                            `json:"active_generation_id,omitempty"`
	LegacyRuntimeReplaced  bool                              `json:"legacy_runtime_replaced"`
}

type ReconciliationCategory struct {
	Status     string   `json:"status"`
	Missing    []string `json:"missing"`
	Unexpected []string `json:"unexpected"`
}

func Run(paths rt.Paths) (Payload, error) {
	pkg, scanResult := scanartifacts.Load(paths, scanartifacts.ValidateOptions{RequireStatusJSON: false})
	payload := basePayload(paths)
	payload.Errors = append(payload.Errors, scanResult.Errors...)
	payload.Warnings = append(payload.Warnings, scanResult.Warnings...)
	payload.ScanArtifactCounts = scanCounts(pkg)
	if len(scanResult.Errors) > 0 {
		return payload, nil
	}

	_, err := rt.ReadStatus(paths)
	if errors.Is(err, rt.ErrUnsupportedLegacy) {
		payload.LegacyRuntimeReplaced = true
	} else if err != nil {
		payload.Errors = append(payload.Errors, fmt.Sprintf("read status: %v", err))
		return payload, err
	}

	replacedDB, err := store.ReplaceIncompatibleDatabase(paths)
	if err != nil {
		payload.Errors = append(payload.Errors, fmt.Sprintf("recover graph store: %v", err))
		return payload, err
	}
	if replacedDB {
		payload.LegacyRuntimeReplaced = true
	}

	st, err := store.Open(paths)
	if err != nil {
		payload.Errors = append(payload.Errors, fmt.Sprintf("open graph store: %v", err))
		return payload, err
	}
	defer st.Close()

	input := importInputFromPackage(pkg)
	generationID, err := st.ImportGeneration(context.Background(), input)
	if err != nil {
		payload.Errors = append(payload.Errors, fmt.Sprintf("import generation: %v", err))
		return payload, err
	}
	payload.ActiveGenerationID = generationID
	payload.Rejections = input.Rejections
	payload.MergeRecords = input.MergeRecords

	snapshot, err := st.ActiveIdentitySnapshot(context.Background())
	if err != nil {
		payload.Errors = append(payload.Errors, fmt.Sprintf("read DB identity snapshot: %v", err))
		return payload, err
	}
	payload.DBCounts = dbCounts(snapshot)
	payload.IdentityReconciliation = summarizeReconciliation(pkg.Identities, snapshot)
	if errors := reconciliationErrors(payload.IdentityReconciliation, snapshot); len(errors) > 0 {
		payload.Errors = append(payload.Errors, errors...)
		return payload, nil
	}

	status := rt.DefaultStatus(paths)
	status.Status = "ok"
	status.Freshness = rt.ReadyFreshness
	status.Readiness = rt.ReadyReadiness
	status.RecommendedNextAction = "use_project_cognition"
	status.GraphReady = true
	status.ActiveGenerationID = generationID
	status.QueryContractVersion = 1
	status.UpdateContractVersion = 1
	if err := rt.WriteStatus(paths, status); err != nil {
		payload.Status = "blocked"
		payload.Readiness = rt.BlockedReadiness
		payload.RecoveryAction = rewriteStatusFromDBMetadata
		payload.Errors = append(payload.Errors, fmt.Sprintf("write status: %v", err))
		return payload, err
	}

	agreement := runtimegate.Check(paths)
	if len(agreement.Errors) > 0 || agreement.Status == "blocked" {
		payload.Status = "blocked"
		payload.Readiness = agreement.Readiness
		payload.Errors = append(payload.Errors, agreement.Errors...)
		payload.Warnings = append(payload.Warnings, agreement.Warnings...)
		payload.RecoveryAction = agreement.RecoveryAction
		return payload, nil
	}

	payload.Status = "ok"
	payload.Readiness = rt.ReadyReadiness
	return payload, nil
}

func basePayload(paths rt.Paths) Payload {
	return Payload{
		Status:                 "blocked",
		Readiness:              rt.BlockedReadiness,
		Errors:                 []string{},
		Warnings:               []string{},
		ScanArtifactCounts:     emptyCounts(),
		DBCounts:               emptyCounts(),
		IdentityReconciliation: emptyReconciliation(),
		Rejections:             []store.RowDecision{},
		MergeRecords:           []store.MergeRecord{},
		StatusPath:             rt.RelativeRuntimePath(paths, paths.StatusPath),
		GraphStorePath:         graphStorePath,
	}
}

func importInputFromPackage(pkg scanartifacts.Package) store.ImportInput {
	rejections := coverageRejections(pkg)
	return store.ImportInput{
		GenerationID: newGenerationID(),
		Kind:         "full",
		SourceCommit: firstSourceCommit(pkg.Evidence),
		Evidence:     evidenceImports(pkg.Evidence),
		Nodes:        nodeImports(pkg.Nodes),
		Edges:        edgeImports(pkg.Edges),
		Observations: observationImports(pkg.Observations),
		PathIndex:    pathIndexImports(pkg.Nodes),
		Rejections:   rejections,
		MergeRecords: []store.MergeRecord{},
	}
}

func evidenceImports(rows []scanartifacts.EvidenceRow) []store.EvidenceImport {
	out := make([]store.EvidenceImport, 0, len(rows))
	for _, row := range rows {
		out = append(out, store.EvidenceImport{
			ID:          row.ID,
			SourceKind:  row.SourceKind,
			SourcePath:  row.SourcePath,
			CommitSHA:   row.CommitSHA,
			Span:        row.Span,
			Extractor:   row.Extractor,
			ContentHash: row.ContentHash,
			Attrs:       row.Attrs,
		})
	}
	return out
}

func nodeImports(rows []scanartifacts.NodeRow) []store.NodeImport {
	out := make([]store.NodeImport, 0, len(rows))
	for _, row := range rows {
		out = append(out, store.NodeImport{
			ID:          row.ID,
			Type:        row.Type,
			Title:       row.Title,
			Confidence:  row.Confidence,
			EvidenceIDs: row.EvidenceIDs,
			Attrs:       row.Attrs,
		})
	}
	return out
}

func edgeImports(rows []scanartifacts.EdgeRow) []store.EdgeImport {
	out := make([]store.EdgeImport, 0, len(rows))
	for _, row := range rows {
		out = append(out, store.EdgeImport{
			ID:          row.ID,
			Type:        row.Type,
			SourceID:    row.SourceID,
			TargetID:    row.TargetID,
			Confidence:  row.Confidence,
			EvidenceIDs: row.EvidenceIDs,
			Attrs:       row.Attrs,
		})
	}
	return out
}

func observationImports(rows []scanartifacts.ObservationRow) []store.ObservationImport {
	out := make([]store.ObservationImport, 0, len(rows))
	for _, row := range rows {
		out = append(out, store.ObservationImport{
			ID:              row.ID,
			ObservationType: row.ObservationType,
			Summary:         row.Summary,
			EvidenceIDs:     row.EvidenceIDs,
			Attrs:           row.Attrs,
		})
	}
	return out
}

func pathIndexImports(nodes []scanartifacts.NodeRow) []store.PathIndexImport {
	out := []store.PathIndexImport{}
	for _, node := range nodes {
		confidence := node.Confidence
		if confidence == "" {
			confidence = "provisional"
		}
		evidenceID := ""
		if len(node.EvidenceIDs) > 0 {
			evidenceID = node.EvidenceIDs[0]
		}
		for _, path := range node.Paths {
			out = append(out, store.PathIndexImport{
				ID:         pathIndexID(path, node.ID),
				Path:       path,
				NodeID:     node.ID,
				Relation:   "owns",
				Confidence: confidence,
				EvidenceID: evidenceID,
			})
		}
	}
	return out
}

func pathIndexID(path, nodeID string) string {
	normalizedPath := filepath.ToSlash(strings.TrimSpace(path))
	normalizedPath = strings.TrimPrefix(normalizedPath, "./")
	hash := sha256.Sum256([]byte(normalizedPath + "\x00" + nodeID))
	return "PI-" + sanitizeIDPart(normalizedPath) + "-" + sanitizeIDPart(nodeID) + "-" + hex.EncodeToString(hash[:])[:16]
}

func coverageRejections(pkg scanartifacts.Package) []store.RowDecision {
	relatedPaths := map[string]bool{}
	for _, node := range pkg.Nodes {
		for _, path := range node.Paths {
			relatedPaths[path] = true
		}
	}
	rejections := []store.RowDecision{}
	for _, path := range pkg.CoveragePaths {
		if !relatedPaths[path] {
			rejections = append(rejections, store.RowDecision{
				Category: "coverage",
				Identity: path,
				Reason:   "no_node_relation",
			})
		}
	}
	return rejections
}

func scanCounts(pkg scanartifacts.Package) map[string]int {
	return map[string]int{
		"evidence":       len(pkg.Identities.Evidence),
		"nodes":          len(pkg.Identities.Nodes),
		"edges":          len(pkg.Identities.Edges),
		"observations":   len(pkg.Identities.Observations),
		"coverage_paths": len(pkg.Identities.CoveragePaths),
	}
}

func dbCounts(snapshot store.IdentitySnapshot) map[string]int {
	return map[string]int{
		"evidence":       len(snapshot.Evidence),
		"nodes":          len(snapshot.Nodes),
		"edges":          len(snapshot.Edges),
		"observations":   len(snapshot.Observations),
		"coverage_paths": len(snapshot.CoveragePaths),
	}
}

func summarizeReconciliation(expected scanartifacts.IdentitySet, actual store.IdentitySnapshot) map[string]ReconciliationCategory {
	return map[string]ReconciliationCategory{
		"evidence":       compareIdentityMaps(expected.Evidence, actual.Evidence),
		"nodes":          compareIdentityMaps(expected.Nodes, actual.Nodes),
		"edges":          compareIdentityMaps(expected.Edges, actual.Edges),
		"observations":   compareIdentityMaps(expected.Observations, actual.Observations),
		"coverage_paths": compareIdentityMaps(expected.CoveragePaths, actual.CoveragePaths),
	}
}

func compareIdentityMaps(expected, actual map[string]bool) ReconciliationCategory {
	missing := []string{}
	unexpected := []string{}
	for identity := range expected {
		if !actual[identity] {
			missing = append(missing, identity)
		}
	}
	for identity := range actual {
		if !expected[identity] {
			unexpected = append(unexpected, identity)
		}
	}
	sort.Strings(missing)
	sort.Strings(unexpected)
	status := "mismatch"
	if len(missing) == 0 && len(unexpected) == 0 {
		status = "ok"
	}
	return ReconciliationCategory{Status: status, Missing: missing, Unexpected: unexpected}
}

func reconciliationErrors(reconciliation map[string]ReconciliationCategory, snapshot store.IdentitySnapshot) []string {
	errors := []string{}
	for category, result := range reconciliation {
		missing := uncoveredMissingIdentities(category, result.Missing, snapshot)
		if len(missing) > 0 {
			errors = append(errors, "missing scan "+identityErrorNoun(category)+" identities: "+strings.Join(missing, ", "))
		}
		if len(result.Unexpected) > 0 {
			errors = append(errors, "unexpected DB "+identityErrorNoun(category)+" identities: "+strings.Join(result.Unexpected, ", "))
		}
	}
	sort.Strings(errors)
	return errors
}

func uncoveredMissingIdentities(category string, identities []string, snapshot store.IdentitySnapshot) []string {
	missing := []string{}
	for _, identity := range identities {
		if !identityCoveredByDecision(category, identity, snapshot) {
			missing = append(missing, identity)
		}
	}
	return missing
}

func identityCoveredByDecision(category string, identity string, snapshot store.IdentitySnapshot) bool {
	for _, rejection := range snapshot.Rejections {
		if sameIdentityCategory(rejection.Category, category) && rejection.Identity == identity {
			return true
		}
	}
	for _, record := range snapshot.MergeRecords {
		if sameIdentityCategory(record.Category, category) && record.SourceIdentity == identity {
			return true
		}
	}
	return false
}

func sameIdentityCategory(actual string, expected string) bool {
	return canonicalIdentityCategory(actual) == canonicalIdentityCategory(expected)
}

func canonicalIdentityCategory(category string) string {
	switch strings.TrimSuffix(strings.TrimSpace(category), "s") {
	case "coverage", "coverage_path":
		return "coverage_path"
	default:
		return strings.TrimSuffix(strings.TrimSpace(category), "s")
	}
}

func identityErrorNoun(category string) string {
	switch canonicalIdentityCategory(category) {
	case "coverage_path":
		return "coverage path"
	case "node":
		return "node"
	case "edge":
		return "edge"
	case "observation":
		return "observation"
	default:
		return category
	}
}

func emptyCounts() map[string]int {
	return map[string]int{
		"evidence":       0,
		"nodes":          0,
		"edges":          0,
		"observations":   0,
		"coverage_paths": 0,
	}
}

func emptyReconciliation() map[string]ReconciliationCategory {
	empty := map[string]bool{}
	return map[string]ReconciliationCategory{
		"evidence":       compareIdentityMaps(empty, empty),
		"nodes":          compareIdentityMaps(empty, empty),
		"edges":          compareIdentityMaps(empty, empty),
		"observations":   compareIdentityMaps(empty, empty),
		"coverage_paths": compareIdentityMaps(empty, empty),
	}
}

func sanitizeIDPart(value string) string {
	value = filepath.ToSlash(strings.TrimSpace(value))
	value = strings.TrimPrefix(value, "./")
	value = unsafeIDPartPattern.ReplaceAllString(value, "-")
	value = strings.Trim(value, "-")
	if value == "" {
		return "empty"
	}
	return value
}

func newGenerationID() string {
	return "GEN-" + time.Now().UTC().Format("20060102T150405.000000000Z")
}

func firstSourceCommit(rows []scanartifacts.EvidenceRow) string {
	for _, row := range rows {
		if row.CommitSHA != "" {
			return row.CommitSHA
		}
	}
	return ""
}
