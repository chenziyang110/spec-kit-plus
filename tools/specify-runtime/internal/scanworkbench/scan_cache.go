package scanworkbench

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"

	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/scanartifacts"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/scanreceipt"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/store"
)

const (
	scanCacheProtocolV1 = "project_cognition_scan_cache.v1"
	scanCacheFileName   = "scan-bundles.json"
)

type ScanCachePayload struct {
	Status      string `json:"status"`
	Protocol    string `json:"protocol"`
	Contract    string `json:"contract"`
	BundleCount int    `json:"bundle_count"`
	PathCount   int    `json:"path_count"`
	CachePath   string `json:"cache_path"`
}

type scanCacheFile struct {
	Protocol string            `json:"protocol"`
	Contract string            `json:"contract"`
	Bundles  []scanCacheBundle `json:"bundles"`
}

type scanCacheBundle struct {
	BundleID      string            `json:"bundle_id"`
	ScopePaths    []string          `json:"scope_paths"`
	SourceDigests map[string]string `json:"source_digests"`
	PolicyDigests map[string]string `json:"policy_digests"`
	Confidence    string            `json:"confidence"`
	RowsDigest    string            `json:"rows_digest"`
	Rows          scanCacheRows     `json:"rows"`
	Lineage       scanCacheLineage  `json:"lineage"`
}

type scanCacheRows struct {
	Coverage     []map[string]any `json:"coverage"`
	Evidence     []map[string]any `json:"evidence"`
	Nodes        []map[string]any `json:"nodes"`
	Edges        []map[string]any `json:"edges"`
	Observations []map[string]any `json:"observations"`
	Claims       []map[string]any `json:"claims,omitempty"`
}

type scanCacheLineage struct {
	GenerationID string   `json:"source_generation_id"`
	PacketIDs    []string `json:"source_packet_ids"`
}

type repositoryUniverseFile struct {
	Candidates []map[string]any `json:"candidate_universe"`
}

type reusableCacheSelection struct {
	Bundles       []scanCacheBundle
	PendingPaths  []string
	MissReasons   map[string]int
	CachePresent  bool
	ReusedPaths   int
	CurrentSource map[string]string
	CurrentPolicy map[string]string
}

// SnapshotValidatedScanCache stores only runtime-accepted scan facts. Packet,
// attempt, and receipt identities are lineage, never reusable current state.
func SnapshotValidatedScanCache(paths rt.Paths) (ScanCachePayload, error) {
	if err := validateRuntimeControlDir(paths); err != nil {
		return ScanCachePayload{}, err
	}
	release, err := acquireWorkbenchLock(paths)
	if err != nil {
		return ScanCachePayload{}, err
	}
	defer release()
	return snapshotValidatedScanCacheUnlocked(paths)
}

func snapshotValidatedScanCacheUnlocked(paths rt.Paths) (ScanCachePayload, error) {
	receiptBefore, receiptRequired, err := scanreceipt.VerifySnapshot(paths)
	if err != nil {
		return ScanCachePayload{}, fmt.Errorf("verify scan receipt before cache snapshot: %w", err)
	}
	if !receiptRequired {
		return ScanCachePayload{}, fmt.Errorf("validated scan cache requires a v2 scan receipt")
	}
	result := scanartifacts.Validate(paths, scanartifacts.ValidateOptions{RequireStatusJSON: false})
	if len(result.Errors) > 0 {
		return ScanCachePayload{}, fmt.Errorf("scan package is not cacheable: %s", strings.Join(result.Errors, "; "))
	}

	var queue queueFile
	if err := readJSON(filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"), &queue); err != nil {
		return ScanCachePayload{}, fmt.Errorf("read scan queue for cache: %w", err)
	}
	if err := requireV2Workbench(queue); err != nil {
		return ScanCachePayload{}, err
	}
	if len(queue.Packets) == 0 {
		return ScanCachePayload{}, fmt.Errorf("scan cache requires at least one accepted packet")
	}

	var universe repositoryUniverseFile
	if err := readJSON(filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), &universe); err != nil {
		return ScanCachePayload{}, fmt.Errorf("read repository universe for cache: %w", err)
	}
	policyByPath, err := candidatePolicyDigests(universe.Candidates)
	if err != nil {
		return ScanCachePayload{}, err
	}

	results := make([]workerResult, len(queue.Packets))
	ownerByPath := map[string]int{}
	allAssigned := map[string]bool{}
	for index, packet := range queue.Packets {
		if packet.State != "accepted" {
			return ScanCachePayload{}, fmt.Errorf("scan cache requires accepted packet %s, got %s", packet.PacketID, packet.State)
		}
		for path := range normalizedSet(packet.AssignedPaths) {
			if _, exists := ownerByPath[path]; exists {
				return ScanCachePayload{}, fmt.Errorf("scan cache path %s is assigned to multiple packets", path)
			}
			ownerByPath[path] = index
			allAssigned[path] = true
		}
		if err := readJSON(filepath.Join(paths.RuntimeDir, "workbench", "worker-results", packet.PacketID+".json"), &results[index]); err != nil {
			return ScanCachePayload{}, fmt.Errorf("read accepted packet %s for cache: %w", packet.PacketID, err)
		}
	}
	for index, packet := range queue.Packets {
		if err := validateWorkerResult(packet, results[index], allAssigned); err != nil {
			return ScanCachePayload{}, fmt.Errorf("validate accepted packet %s for cache: %w", packet.PacketID, err)
		}
	}

	allRows, err := mergeAcceptedCacheRows(results)
	if err != nil {
		return ScanCachePayload{}, err
	}
	components, dependencies, err := cachePathComponents(allAssigned, allRows)
	if err != nil {
		return ScanCachePayload{}, err
	}

	contract := currentScanCacheContract()
	bundles := make([]scanCacheBundle, 0, len(components))
	for _, scopePaths := range components {
		rows := filterCacheRowsForScope(allRows, dependencies, normalizedSet(scopePaths))
		packetIDs := map[string]bool{}
		confidence := "verified"
		for _, path := range scopePaths {
			owner := ownerByPath[path]
			packetIDs[queue.Packets[owner].PacketID] = true
			confidence = conservativeConfidence(confidence, results[owner].Confidence)
		}
		lineagePacketIDs := make([]string, 0, len(packetIDs))
		for packetID := range packetIDs {
			lineagePacketIDs = append(lineagePacketIDs, packetID)
		}
		sort.Strings(lineagePacketIDs)
		bundle, err := buildScanCacheBundle(paths, queue.GenerationID, scopePaths, rows, confidence, lineagePacketIDs, policyByPath, contract)
		if err != nil {
			return ScanCachePayload{}, err
		}
		bundles = append(bundles, bundle)
	}
	receiptAfter, receiptRequiredAfter, err := scanreceipt.VerifySnapshot(paths)
	if err != nil {
		return ScanCachePayload{}, fmt.Errorf("verify scan receipt after cache snapshot: %w", err)
	}
	if !receiptRequiredAfter || receiptAfter != receiptBefore {
		return ScanCachePayload{}, fmt.Errorf("scan artifacts changed while validated cache was being captured")
	}
	cache := scanCacheFile{Protocol: scanCacheProtocolV1, Contract: contract, Bundles: bundles}
	if err := writeJSONAtomic(scanCachePath(paths), cache); err != nil {
		return ScanCachePayload{}, fmt.Errorf("write scan cache: %w", err)
	}
	return ScanCachePayload{
		Status: "refreshed", Protocol: cache.Protocol, Contract: cache.Contract,
		BundleCount: len(cache.Bundles), PathCount: len(allAssigned), CachePath: cacheRuntimePath(),
	}, nil
}

type scanCacheRowDependencies struct {
	Coverage     map[string]map[string]bool
	Evidence     map[string]map[string]bool
	Nodes        map[string]map[string]bool
	Edges        map[string]map[string]bool
	Observations map[string]map[string]bool
	Claims       map[string]map[string]bool
}

func mergeAcceptedCacheRows(results []workerResult) (scanCacheRows, error) {
	merged := scanCacheRows{}
	var err error
	for _, result := range results {
		if merged.Coverage, err = mergeObjectRows(merged.Coverage, result.Coverage, "path", "cache coverage"); err != nil {
			return scanCacheRows{}, err
		}
		if merged.Evidence, err = mergeObjectRows(merged.Evidence, result.Evidence, "id", "cache evidence"); err != nil {
			return scanCacheRows{}, err
		}
		if merged.Nodes, err = mergeObjectRows(merged.Nodes, result.Nodes, "id", "cache node"); err != nil {
			return scanCacheRows{}, err
		}
		if merged.Edges, err = mergeObjectRows(merged.Edges, result.Edges, "id", "cache edge"); err != nil {
			return scanCacheRows{}, err
		}
		if merged.Observations, err = mergeObjectRows(merged.Observations, result.Observations, "id", "cache observation"); err != nil {
			return scanCacheRows{}, err
		}
		if merged.Claims, err = mergeObjectRows(merged.Claims, result.Claims, "id", "cache claim"); err != nil {
			return scanCacheRows{}, err
		}
	}
	return merged, nil
}

// cachePathComponents derives the smallest safe reuse scopes from accepted
// facts. Paths are connected only when one semantic row depends on all of
// them, such as a shared node, cross-path edge, or multi-source claim.
func cachePathComponents(allAssigned map[string]bool, rows scanCacheRows) ([][]string, scanCacheRowDependencies, error) {
	paths := make([]string, 0, len(allAssigned))
	for path := range allAssigned {
		paths = append(paths, path)
	}
	sort.Strings(paths)
	if len(paths) == 0 {
		return nil, scanCacheRowDependencies{}, fmt.Errorf("scan cache requires assigned paths")
	}
	pathIndex := make(map[string]int, len(paths))
	for index, path := range paths {
		pathIndex[path] = index
	}
	groups := newPacketGroups(len(paths))
	dependencies := scanCacheRowDependencies{
		Coverage: map[string]map[string]bool{}, Evidence: map[string]map[string]bool{},
		Nodes: map[string]map[string]bool{}, Edges: map[string]map[string]bool{},
		Observations: map[string]map[string]bool{}, Claims: map[string]map[string]bool{},
	}
	connect := func(owner string, scope map[string]bool) error {
		if len(scope) == 0 {
			return fmt.Errorf("%s has no resolvable path dependency", owner)
		}
		ordered := sortedPathSet(scope)
		first, ok := pathIndex[ordered[0]]
		if !ok {
			return fmt.Errorf("%s depends on path %s outside the scan set", owner, ordered[0])
		}
		for _, path := range ordered[1:] {
			index, exists := pathIndex[path]
			if !exists {
				return fmt.Errorf("%s depends on path %s outside the scan set", owner, path)
			}
			groups.union(first, index)
		}
		return nil
	}

	evidenceByID := map[string]map[string]bool{}
	for _, row := range rows.Evidence {
		id := stringValue(row["id"])
		path := normalizePath(stringValue(row["source_path"]))
		scope := normalizedSet([]string{path})
		if err := connect("evidence "+id, scope); err != nil {
			return nil, scanCacheRowDependencies{}, err
		}
		evidenceByID[id] = scope
		dependencies.Evidence[id] = scope
	}
	resolveEvidence := func(owner string, refs []string) (map[string]bool, error) {
		scope := map[string]bool{}
		for _, ref := range refs {
			refScope, ok := evidenceByID[ref]
			if !ok {
				return nil, fmt.Errorf("%s references unknown evidence %s", owner, ref)
			}
			mergePathSet(scope, refScope)
		}
		if len(scope) == 0 {
			return nil, fmt.Errorf("%s has no evidence path dependency", owner)
		}
		return scope, nil
	}

	for _, row := range rows.Coverage {
		path := normalizePath(stringValue(row["path"]))
		owner := "coverage " + path
		scope := normalizedSet([]string{path})
		evidenceScope, err := resolveEvidence(owner, stringValues(row["evidence_ids"]))
		if err != nil {
			return nil, scanCacheRowDependencies{}, err
		}
		mergePathSet(scope, evidenceScope)
		if err := connect(owner, scope); err != nil {
			return nil, scanCacheRowDependencies{}, err
		}
		dependencies.Coverage[path] = scope
	}

	nodeByID := map[string]map[string]bool{}
	for _, row := range rows.Nodes {
		id := stringValue(row["id"])
		owner := "node " + id
		scope := normalizedSet(stringValues(row["paths"]))
		evidenceScope, err := resolveEvidence(owner, stringValues(row["evidence_ids"]))
		if err != nil {
			return nil, scanCacheRowDependencies{}, err
		}
		mergePathSet(scope, evidenceScope)
		if err := connect(owner, scope); err != nil {
			return nil, scanCacheRowDependencies{}, err
		}
		nodeByID[id] = scope
		dependencies.Nodes[id] = scope
	}
	resolveEndpoint := func(owner string, endpoint string) (map[string]bool, error) {
		scope := map[string]bool{}
		if nodeScope, ok := nodeByID[endpoint]; ok {
			mergePathSet(scope, nodeScope)
		}
		path := normalizePath(endpoint)
		if allAssigned[path] {
			scope[path] = true
		}
		if len(scope) == 0 {
			return nil, fmt.Errorf("%s has unknown endpoint %s", owner, endpoint)
		}
		return scope, nil
	}

	for _, row := range rows.Edges {
		id := stringValue(row["id"])
		owner := "edge " + id
		scope, err := resolveEndpoint(owner, stringValue(row["source_id"]))
		if err != nil {
			return nil, scanCacheRowDependencies{}, err
		}
		targetScope, err := resolveEndpoint(owner, stringValue(row["target_id"]))
		if err != nil {
			return nil, scanCacheRowDependencies{}, err
		}
		mergePathSet(scope, targetScope)
		evidenceScope, err := resolveEvidence(owner, stringValues(row["evidence_ids"]))
		if err != nil {
			return nil, scanCacheRowDependencies{}, err
		}
		mergePathSet(scope, evidenceScope)
		if err := connect(owner, scope); err != nil {
			return nil, scanCacheRowDependencies{}, err
		}
		dependencies.Edges[id] = scope
	}

	for _, row := range rows.Observations {
		id := stringValue(row["id"])
		owner := "observation " + id
		scope, err := resolveEvidence(owner, stringValues(row["evidence_ids"]))
		if err != nil {
			return nil, scanCacheRowDependencies{}, err
		}
		if err := connect(owner, scope); err != nil {
			return nil, scanCacheRowDependencies{}, err
		}
		dependencies.Observations[id] = scope
	}

	for _, row := range rows.Claims {
		id := stringValue(row["id"])
		owner := "claim " + id
		nodeID := stringValue(row["node_id"])
		scope, ok := nodeByID[nodeID]
		if !ok {
			return nil, scanCacheRowDependencies{}, fmt.Errorf("%s references unknown node %s", owner, nodeID)
		}
		scope = clonePathSet(scope)
		refs := append(stringValues(row["supporting_evidence_ids"]), stringValues(row["contradicting_evidence_ids"])...)
		refs = append(refs, stringValues(row["verification_evidence_ids"])...)
		evidenceScope, err := resolveEvidence(owner, refs)
		if err != nil {
			return nil, scanCacheRowDependencies{}, err
		}
		mergePathSet(scope, evidenceScope)
		if err := connect(owner, scope); err != nil {
			return nil, scanCacheRowDependencies{}, err
		}
		dependencies.Claims[id] = scope
	}

	byRoot := map[int][]string{}
	for index, path := range paths {
		root := groups.find(index)
		byRoot[root] = append(byRoot[root], path)
	}
	components := make([][]string, 0, len(byRoot))
	for _, component := range byRoot {
		sort.Strings(component)
		components = append(components, component)
	}
	sort.Slice(components, func(i, j int) bool { return strings.Join(components[i], "\x00") < strings.Join(components[j], "\x00") })
	return components, dependencies, nil
}

func filterCacheRowsForScope(rows scanCacheRows, dependencies scanCacheRowDependencies, scope map[string]bool) scanCacheRows {
	return scanCacheRows{
		Coverage:     filterCacheRows(rows.Coverage, "path", true, dependencies.Coverage, scope),
		Evidence:     filterCacheRows(rows.Evidence, "id", false, dependencies.Evidence, scope),
		Nodes:        filterCacheRows(rows.Nodes, "id", false, dependencies.Nodes, scope),
		Edges:        filterCacheRows(rows.Edges, "id", false, dependencies.Edges, scope),
		Observations: filterCacheRows(rows.Observations, "id", false, dependencies.Observations, scope),
		Claims:       filterCacheRows(rows.Claims, "id", false, dependencies.Claims, scope),
	}
}

func filterCacheRows(rows []map[string]any, key string, normalizeKey bool, dependencies map[string]map[string]bool, scope map[string]bool) []map[string]any {
	filtered := make([]map[string]any, 0, len(rows))
	for _, row := range rows {
		identity := stringValue(row[key])
		if normalizeKey {
			identity = normalizePath(identity)
		}
		if pathSetsIntersect(dependencies[identity], scope) {
			filtered = append(filtered, row)
		}
	}
	return filtered
}

func mergePathSet(target map[string]bool, source map[string]bool) {
	for path := range source {
		target[path] = true
	}
}

func clonePathSet(source map[string]bool) map[string]bool {
	clone := make(map[string]bool, len(source))
	mergePathSet(clone, source)
	return clone
}

func sortedPathSet(paths map[string]bool) []string {
	ordered := make([]string, 0, len(paths))
	for path := range paths {
		ordered = append(ordered, path)
	}
	sort.Strings(ordered)
	return ordered
}

func pathSetsIntersect(left map[string]bool, right map[string]bool) bool {
	for path := range left {
		if right[path] {
			return true
		}
	}
	return false
}

func buildScanCacheBundle(paths rt.Paths, generationID string, scopePaths []string, rows scanCacheRows, confidence string, packetIDs []string, policyByPath map[string]string, contract string) (scanCacheBundle, error) {
	bundle := scanCacheBundle{
		ScopePaths: append([]string{}, scopePaths...), SourceDigests: map[string]string{}, PolicyDigests: map[string]string{},
		Confidence: confidence, Rows: rows,
		Lineage: scanCacheLineage{GenerationID: generationID, PacketIDs: append([]string{}, packetIDs...)},
	}
	sort.Strings(bundle.ScopePaths)
	sort.Strings(bundle.Lineage.PacketIDs)
	if err := validateScanCacheBundleRows(bundle); err != nil {
		return scanCacheBundle{}, fmt.Errorf("validate reusable path scope %v: %w", bundle.ScopePaths, err)
	}
	for _, path := range bundle.ScopePaths {
		sourceDigest, err := repositorySourceDigest(paths.Root, path)
		if err != nil {
			return scanCacheBundle{}, err
		}
		policyDigest := policyByPath[path]
		if policyDigest == "" {
			return scanCacheBundle{}, fmt.Errorf("cache path %s has no repository-universe policy fingerprint", path)
		}
		bundle.SourceDigests[path] = sourceDigest
		bundle.PolicyDigests[path] = policyDigest
	}
	rowsDigest, err := digestWithPrefix(bundle.Rows)
	if err != nil {
		return scanCacheBundle{}, err
	}
	bundle.RowsDigest = rowsDigest
	bundleID, err := expectedScanCacheBundleID(bundle, contract)
	if err != nil {
		return scanCacheBundle{}, err
	}
	bundle.BundleID = bundleID
	return bundle, nil
}

func validateScanCacheBundleRows(bundle scanCacheBundle) error {
	checkPacket := queuePacket{PacketID: "cache-bundle-check", AssignedPaths: bundle.ScopePaths}
	checkResult := workerResult{
		PacketID: "cache-bundle-check", AssignedPaths: bundle.ScopePaths, PathsRead: bundle.ScopePaths,
		Ledger:   workerLedger{Todo: []string{}, Doing: []string{}, Done: bundle.ScopePaths, Blocked: []string{}, Overflow: []string{}},
		Coverage: bundle.Rows.Coverage, Evidence: bundle.Rows.Evidence, Nodes: bundle.Rows.Nodes, Edges: bundle.Rows.Edges,
		Observations: bundle.Rows.Observations, Claims: bundle.Rows.Claims, Confidence: bundle.Confidence, Acceptance: "pass",
	}
	return validateWorkerResult(checkPacket, checkResult, normalizedSet(bundle.ScopePaths))
}

func expectedScanCacheBundleID(bundle scanCacheBundle, contract string) (string, error) {
	digest, err := digestWithPrefix(struct {
		Contract      string            `json:"contract"`
		ScopePaths    []string          `json:"scope_paths"`
		SourceDigests map[string]string `json:"source_digests"`
		PolicyDigests map[string]string `json:"policy_digests"`
		Confidence    string            `json:"confidence"`
		RowsDigest    string            `json:"rows_digest"`
		Lineage       scanCacheLineage  `json:"lineage"`
	}{contract, bundle.ScopePaths, bundle.SourceDigests, bundle.PolicyDigests, bundle.Confidence, bundle.RowsDigest, bundle.Lineage})
	if err != nil {
		return "", err
	}
	return "scb-" + strings.TrimPrefix(digest, "sha256:")[:16], nil
}

func validateScanCacheBundleIntegrity(bundle scanCacheBundle, contract string) error {
	if len(bundle.ScopePaths) == 0 || len(normalizedSet(bundle.ScopePaths)) != len(bundle.ScopePaths) {
		return fmt.Errorf("cache bundle %s has an empty or duplicate scope", bundle.BundleID)
	}
	ordered := append([]string{}, bundle.ScopePaths...)
	sort.Strings(ordered)
	for index, path := range ordered {
		if path == "" || path != normalizePath(path) || bundle.ScopePaths[index] != path {
			return fmt.Errorf("cache bundle %s scope paths are not canonical and sorted", bundle.BundleID)
		}
	}
	if len(bundle.SourceDigests) != len(bundle.ScopePaths) || len(bundle.PolicyDigests) != len(bundle.ScopePaths) {
		return fmt.Errorf("cache bundle %s digest coverage does not match its scope", bundle.BundleID)
	}
	for _, path := range bundle.ScopePaths {
		if bundle.SourceDigests[path] == "" || bundle.PolicyDigests[path] == "" {
			return fmt.Errorf("cache bundle %s is missing digests for %s", bundle.BundleID, path)
		}
	}
	if strings.TrimSpace(bundle.Lineage.GenerationID) == "" || len(bundle.Lineage.PacketIDs) == 0 || len(normalizedIdentitySet(bundle.Lineage.PacketIDs)) != len(bundle.Lineage.PacketIDs) {
		return fmt.Errorf("cache bundle %s lineage is missing or duplicated", bundle.BundleID)
	}
	orderedPacketIDs := append([]string{}, bundle.Lineage.PacketIDs...)
	sort.Strings(orderedPacketIDs)
	for index, packetID := range orderedPacketIDs {
		if strings.TrimSpace(packetID) == "" || bundle.Lineage.PacketIDs[index] != packetID {
			return fmt.Errorf("cache bundle %s packet lineage is not canonical and sorted", bundle.BundleID)
		}
	}
	rowsDigest, err := digestWithPrefix(bundle.Rows)
	if err != nil || rowsDigest != bundle.RowsDigest {
		return fmt.Errorf("cache bundle %s row digest is invalid", bundle.BundleID)
	}
	expectedID, err := expectedScanCacheBundleID(bundle, contract)
	if err != nil || expectedID != bundle.BundleID {
		return fmt.Errorf("cache bundle %s identity is invalid", bundle.BundleID)
	}
	if err := validateScanCacheBundleRows(bundle); err != nil {
		return fmt.Errorf("cache bundle %s rows are invalid: %w", bundle.BundleID, err)
	}
	return nil
}

func selectReusableScanCache(paths rt.Paths, classifications []pathClassification, selectedPaths []string, fullRebuild bool) reusableCacheSelection {
	selection := reusableCacheSelection{
		Bundles: []scanCacheBundle{}, PendingPaths: append([]string{}, selectedPaths...),
		MissReasons: map[string]int{}, CurrentSource: map[string]string{}, CurrentPolicy: map[string]string{},
	}
	sort.Strings(selection.PendingPaths)
	selected := normalizedSet(selectedPaths)
	for _, classification := range classifications {
		if !selected[classification.Path] {
			continue
		}
		digest, err := pathClassificationDigest(classification)
		if err != nil {
			selection.MissReasons["policy_digest_unavailable"]++
			continue
		}
		selection.CurrentPolicy[classification.Path] = digest
		source, err := repositorySourceDigest(paths.Root, classification.Path)
		if err != nil {
			selection.MissReasons["source_digest_unavailable"]++
			continue
		}
		selection.CurrentSource[classification.Path] = source
	}
	if fullRebuild {
		selection.MissReasons["full_rebuild"] = len(selected)
		return selection
	}

	cache, err := loadScanCache(paths)
	if err != nil {
		selection.MissReasons["cache_unavailable"] = len(selected)
		return selection
	}
	selection.CachePresent = true
	if cache.Protocol != scanCacheProtocolV1 || cache.Contract != currentScanCacheContract() {
		selection.MissReasons["contract_stale"] = len(selected)
		return selection
	}

	reused := map[string]bool{}
	accountedMiss := map[string]bool{}
	for _, bundle := range cache.Bundles {
		currentScope := []string{}
		allSelected := true
		for _, path := range bundle.ScopePaths {
			if selected[path] {
				currentScope = append(currentScope, path)
			} else {
				allSelected = false
			}
		}
		if len(currentScope) == 0 {
			continue
		}
		reason := ""
		if !allSelected || len(currentScope) != len(bundle.ScopePaths) {
			reason = "dependency_scope_changed"
		}
		if reason == "" {
			if integrityErr := validateScanCacheBundleIntegrity(bundle, cache.Contract); integrityErr != nil {
				reason = "cache_integrity_mismatch"
			}
		}
		if reason == "" {
			for _, path := range bundle.ScopePaths {
				if selection.CurrentSource[path] == "" || bundle.SourceDigests[path] != selection.CurrentSource[path] {
					reason = "source_digest_changed"
					break
				}
			}
		}
		if reason == "" {
			for _, path := range bundle.ScopePaths {
				if selection.CurrentPolicy[path] == "" || bundle.PolicyDigests[path] != selection.CurrentPolicy[path] {
					reason = "policy_digest_changed"
					break
				}
			}
		}
		if reason == "" {
			for _, path := range bundle.ScopePaths {
				if reused[path] {
					reason = "cache_scope_overlap"
					break
				}
			}
		}
		if reason != "" {
			for _, path := range currentScope {
				if !accountedMiss[path] {
					selection.MissReasons[reason]++
					accountedMiss[path] = true
				}
			}
			continue
		}
		selection.Bundles = append(selection.Bundles, bundle)
		for _, path := range bundle.ScopePaths {
			reused[path] = true
		}
	}
	sort.Slice(selection.Bundles, func(i, j int) bool { return selection.Bundles[i].BundleID < selection.Bundles[j].BundleID })
	selection.PendingPaths = selection.PendingPaths[:0]
	for _, path := range selectedPaths {
		if reused[path] {
			selection.ReusedPaths++
			continue
		}
		selection.PendingPaths = append(selection.PendingPaths, path)
		if !accountedMiss[path] {
			selection.MissReasons["cache_entry_missing"]++
		}
	}
	sort.Strings(selection.PendingPaths)
	return selection
}

func resumeCompatibleWorkbench(paths rt.Paths, preparationDigest string, policyDigest string, pathCount int, force bool, fullRebuild bool) (PreparePayload, bool, error) {
	workbench := filepath.Join(paths.RuntimeDir, "workbench")
	if _, err := os.Lstat(workbench); err != nil {
		if os.IsNotExist(err) {
			return PreparePayload{}, false, nil
		}
		return PreparePayload{}, false, fmt.Errorf("inspect existing scan workbench: %w", err)
	}
	if force || fullRebuild {
		return PreparePayload{}, false, nil
	}
	var queue queueFile
	if err := readJSON(filepath.Join(workbench, "scan-queue.json"), &queue); err != nil {
		return PreparePayload{}, false, fmt.Errorf("scan workbench already exists but is incompatible; rerun scan-prepare with --force to replace it: %w", err)
	}
	if err := requireV2Workbench(queue); err != nil {
		return PreparePayload{}, false, fmt.Errorf("%w; rerun scan-prepare with --force to replace it", err)
	}
	if queue.PreparationDigest == "" {
		return PreparePayload{}, false, fmt.Errorf("scan workbench has no preparation digest; rerun scan-prepare with --force to replace it")
	}
	if queue.PreparationDigest != preparationDigest {
		allAccepted := len(queue.Packets) > 0
		for _, packet := range queue.Packets {
			allAccepted = allAccepted && packet.State == "accepted"
		}
		cache, cacheErr := loadScanCache(paths)
		if allAccepted && cacheErr == nil && cacheCoversAcceptedWorkbench(cache, queue) == nil {
			return PreparePayload{}, false, nil
		}
		return PreparePayload{}, false, fmt.Errorf("scan workbench inputs changed while results are not safely cached; rerun scan-prepare with --force to replace it")
	}
	if err := recoverPendingScanCacheReplays(paths, queue); err != nil {
		return PreparePayload{}, false, fmt.Errorf("resume validated scan cache replay: %w", err)
	}
	if err := readJSON(filepath.Join(workbench, "scan-queue.json"), &queue); err != nil {
		return PreparePayload{}, false, fmt.Errorf("read scan queue after cache replay recovery: %w", err)
	}

	packetIDs := make([]string, 0, len(queue.Packets))
	acceptedPaths := map[string]bool{}
	pendingPaths := map[string]bool{}
	cacheHits := 0
	for _, packet := range queue.Packets {
		packetIDs = append(packetIDs, packet.PacketID)
		if packet.CacheBundleID != "" {
			cacheHits++
		}
		for path := range normalizedSet(packet.AssignedPaths) {
			if packet.State == "accepted" {
				acceptedPaths[path] = true
			} else {
				pendingPaths[path] = true
			}
		}
	}
	nextAction := "dispatch_scan_packets"
	if len(pendingPaths) == 0 {
		nextAction = "validate_scan"
		if _, err := os.Stat(filepath.Join(paths.RuntimeDir, "scan-receipt.json")); err == nil {
			nextAction = "build_from_scan"
		}
	}
	return PreparePayload{
		Status: "resumed", PathCount: pathCount, ReusedPathCount: len(acceptedPaths), PendingPathCount: len(pendingPaths),
		PacketCount: len(queue.Packets), CacheHitBundleCount: cacheHits, CacheMissReasons: map[string]int{},
		PacketIDs: packetIDs, ScanSetPath: queue.ScanSetPath, WorkbenchPath: ".specify/project-cognition/workbench",
		PolicyDigest: policyDigest, PreparationDigest: preparationDigest, NextAction: nextAction,
	}, true, nil
}

func preflightExistingWorkbench(paths rt.Paths, force bool, fullRebuild bool) error {
	if force || fullRebuild {
		return nil
	}
	workbench := filepath.Join(paths.RuntimeDir, "workbench")
	if _, err := os.Lstat(workbench); err != nil {
		if os.IsNotExist(err) {
			return nil
		}
		return fmt.Errorf("inspect existing scan workbench: %w", err)
	}
	var queue queueFile
	if err := readJSON(filepath.Join(workbench, "scan-queue.json"), &queue); err != nil {
		return fmt.Errorf("scan workbench already exists but is incompatible; rerun scan-prepare with --force to replace it: %w", err)
	}
	if err := requireV2Workbench(queue); err != nil {
		return fmt.Errorf("%w; rerun scan-prepare with --force to replace it", err)
	}
	if queue.PreparationDigest == "" {
		return fmt.Errorf("scan workbench has no preparation digest; rerun scan-prepare with --force to replace it")
	}
	return nil
}

func replayScanCacheBundles(paths rt.Paths, generationID string, bundles []scanCacheBundle) error {
	for index, bundle := range bundles {
		packet := queuePacket{
			PacketID: cachePacketID(generationID, index+1), AssignedPaths: append([]string{}, bundle.ScopePaths...),
			AttemptID: "cache-" + strings.ToLower(strings.TrimPrefix(generationID, "GEN-")) + fmt.Sprintf("-%03d", index+1),
		}
		if err := replayScanCachePacket(paths, packet, bundle); err != nil {
			return err
		}
	}
	return nil
}

func recoverPendingScanCacheReplays(paths rt.Paths, queue queueFile) error {
	pending := []queuePacket{}
	for _, packet := range queue.Packets {
		if packet.CacheBundleID == "" || packet.State == "accepted" {
			continue
		}
		if packet.State != "leased" {
			return fmt.Errorf("cache replay packet %s has unexpected state %s; rerun scan-prepare with --force", packet.PacketID, packet.State)
		}
		pending = append(pending, packet)
	}
	if len(pending) == 0 {
		return nil
	}
	cache, err := loadScanCache(paths)
	if err != nil {
		return fmt.Errorf("load persistent scan cache: %w", err)
	}
	contract := currentScanCacheContract()
	if cache.Protocol != scanCacheProtocolV1 || cache.Contract != contract {
		return fmt.Errorf("persistent scan cache contract changed; rerun scan-prepare with --force")
	}
	var universe repositoryUniverseFile
	if err := readJSON(filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), &universe); err != nil {
		return fmt.Errorf("read repository universe for cache replay recovery: %w", err)
	}
	policyByPath, err := candidatePolicyDigests(universe.Candidates)
	if err != nil {
		return err
	}
	bundlesByID := map[string]scanCacheBundle{}
	for _, bundle := range cache.Bundles {
		if _, duplicate := bundlesByID[bundle.BundleID]; duplicate {
			return fmt.Errorf("persistent scan cache repeats bundle %s", bundle.BundleID)
		}
		bundlesByID[bundle.BundleID] = bundle
	}
	for _, packet := range pending {
		bundle, ok := bundlesByID[packet.CacheBundleID]
		if !ok {
			return fmt.Errorf("cache replay packet %s references missing bundle %s", packet.PacketID, packet.CacheBundleID)
		}
		if err := validateScanCacheBundleIntegrity(bundle, contract); err != nil {
			return err
		}
		if !sameSet(normalizedSet(packet.AssignedPaths), normalizedSet(bundle.ScopePaths)) {
			return fmt.Errorf("cache replay packet %s scope does not match bundle %s", packet.PacketID, bundle.BundleID)
		}
		for _, path := range bundle.ScopePaths {
			sourceDigest, digestErr := repositorySourceDigest(paths.Root, path)
			if digestErr != nil || sourceDigest != bundle.SourceDigests[path] {
				return fmt.Errorf("cache replay packet %s source changed for %s", packet.PacketID, path)
			}
			if policyByPath[path] == "" || policyByPath[path] != bundle.PolicyDigests[path] {
				return fmt.Errorf("cache replay packet %s policy changed for %s", packet.PacketID, path)
			}
		}
		if err := replayScanCachePacket(paths, packet, bundle); err != nil {
			return err
		}
	}
	return nil
}

func replayScanCachePacket(paths rt.Paths, packet queuePacket, bundle scanCacheBundle) error {
	result := workerResult{
		Protocol: "map_scan_result.v2", PacketID: packet.PacketID, AttemptID: packet.AttemptID, Sequence: 1,
		FamilyID: "runtime-cache-replay", AssignedPaths: append([]string{}, bundle.ScopePaths...),
		PathsRead: append([]string{}, bundle.ScopePaths...),
		Ledger:    workerLedger{Todo: []string{}, Doing: []string{}, Done: append([]string{}, bundle.ScopePaths...), Blocked: []string{}, Overflow: []string{}},
		Coverage:  bundle.Rows.Coverage, Evidence: bundle.Rows.Evidence, Nodes: bundle.Rows.Nodes, Edges: bundle.Rows.Edges,
		Observations: bundle.Rows.Observations, Claims: bundle.Rows.Claims,
		Confidence: bundle.Confidence, Acceptance: "partial",
	}
	data, err := json.Marshal(result)
	if err != nil {
		return fmt.Errorf("encode cache bundle %s: %w", bundle.BundleID, err)
	}
	tmp, err := os.CreateTemp("", "specify-scan-cache-replay-*.json")
	if err != nil {
		return fmt.Errorf("create cache replay input: %w", err)
	}
	tmpPath := tmp.Name()
	if _, err := tmp.Write(data); err != nil {
		_ = tmp.Close()
		_ = os.Remove(tmpPath)
		return fmt.Errorf("write cache replay input: %w", err)
	}
	if err := tmp.Close(); err != nil {
		_ = os.Remove(tmpPath)
		return fmt.Errorf("close cache replay input: %w", err)
	}
	_, acceptErr := acceptUnlocked(paths, AcceptInput{PacketID: packet.PacketID, AttemptID: packet.AttemptID, ResultPath: tmpPath})
	_ = os.Remove(tmpPath)
	if acceptErr != nil {
		return fmt.Errorf("replay cache bundle %s: %w", bundle.BundleID, acceptErr)
	}
	return nil
}

func cacheCoversAcceptedWorkbench(cache scanCacheFile, queue queueFile) error {
	contract := currentScanCacheContract()
	if cache.Protocol != scanCacheProtocolV1 || cache.Contract != contract {
		return fmt.Errorf("persistent scan cache contract does not match the current workbench")
	}
	type cachedPathOwner struct {
		packetIDs map[string]bool
	}
	covered := map[string]cachedPathOwner{}
	for _, bundle := range cache.Bundles {
		if err := validateScanCacheBundleIntegrity(bundle, contract); err != nil {
			return err
		}
		if bundle.Lineage.GenerationID != queue.GenerationID {
			return fmt.Errorf("cache bundle %s belongs to generation %s, not %s", bundle.BundleID, bundle.Lineage.GenerationID, queue.GenerationID)
		}
		packetIDs := normalizedIdentitySet(bundle.Lineage.PacketIDs)
		if len(packetIDs) == 0 {
			return fmt.Errorf("cache bundle %s has no packet lineage", bundle.BundleID)
		}
		for _, path := range bundle.ScopePaths {
			if _, duplicate := covered[path]; duplicate {
				return fmt.Errorf("persistent scan cache repeats path %s", path)
			}
			covered[path] = cachedPathOwner{packetIDs: packetIDs}
		}
	}
	assignedCount := 0
	for _, packet := range queue.Packets {
		if packet.State != "accepted" {
			return fmt.Errorf("packet %s is not accepted", packet.PacketID)
		}
		for path := range normalizedSet(packet.AssignedPaths) {
			assignedCount++
			owner, ok := covered[path]
			if !ok || !owner.packetIDs[packet.PacketID] {
				return fmt.Errorf("persistent scan cache does not cover %s from packet %s", path, packet.PacketID)
			}
		}
	}
	if len(covered) != assignedCount {
		return fmt.Errorf("persistent scan cache path coverage does not match the current workbench")
	}
	return nil
}

func normalizedIdentitySet(values []string) map[string]bool {
	result := map[string]bool{}
	for _, value := range values {
		if identity := strings.TrimSpace(value); identity != "" {
			result[identity] = true
		}
	}
	return result
}

func preparationFingerprint(root string, scanSetPath string, files []string, classifications []pathClassification, input PrepareInput, policyDigest string) (string, error) {
	type pathState struct {
		Path         string `json:"path"`
		SourceDigest string `json:"source_digest"`
		PolicyDigest string `json:"policy_digest"`
	}
	states := make([]pathState, 0, len(classifications))
	for _, classification := range classifications {
		sourceDigest, err := repositorySourceDigest(root, classification.Path)
		if err != nil {
			return "", err
		}
		classificationDigest, err := pathClassificationDigest(classification)
		if err != nil {
			return "", err
		}
		states = append(states, pathState{classification.Path, sourceDigest, classificationDigest})
	}
	sort.Slice(states, func(i, j int) bool { return states[i].Path < states[j].Path })
	return digestWithPrefix(struct {
		Protocol               string      `json:"protocol"`
		Contract               string      `json:"contract"`
		ScanSetPath            string      `json:"scan_set_path"`
		Files                  []string    `json:"files"`
		PathStates             []pathState `json:"path_states"`
		MaxPaths               int         `json:"max_paths"`
		MaxBytes               int64       `json:"max_bytes"`
		WorkerBudgetTokens     int64       `json:"worker_budget_tokens"`
		IncludeGitIgnored      bool        `json:"include_gitignored"`
		RequireConfirmedPolicy bool        `json:"require_confirmed_policy"`
		PolicyDigest           string      `json:"policy_digest"`
	}{workbenchProtocolV2, currentScanCacheContract(), scanSetPath, files, states, effectiveMaxPaths(input), effectiveMaxBytes(input), effectiveWorkerBudget(input), input.IncludeGitIgnored, input.RequireConfirmedPolicy, policyDigest})
}

func candidatePolicyDigests(candidates []map[string]any) (map[string]string, error) {
	result := map[string]string{}
	for _, candidate := range candidates {
		path := normalizePath(stringValue(candidate["path"]))
		if path == "" {
			return nil, fmt.Errorf("repository-universe candidate is missing path")
		}
		digest, err := digestWithPrefix(candidate)
		if err != nil {
			return nil, fmt.Errorf("digest repository-universe candidate %s: %w", path, err)
		}
		result[path] = digest
	}
	return result, nil
}

func pathClassificationDigest(classification pathClassification) (string, error) {
	return digestWithPrefix(repositoryUniverse([]pathClassification{classification}, "")["candidate_universe"].([]map[string]any)[0])
}

func repositorySourceDigest(root string, path string) (string, error) {
	data, err := os.ReadFile(filepath.Join(root, filepath.FromSlash(path)))
	if err != nil {
		return "", fmt.Errorf("digest repository source %s: %w", path, err)
	}
	sum := sha256.Sum256(data)
	return "sha256:" + hex.EncodeToString(sum[:]), nil
}

func digestWithPrefix(value any) (string, error) {
	digest, err := normalizedJSONDigest(value)
	if err != nil {
		return "", err
	}
	return "sha256:" + digest, nil
}

func currentScanCacheContract() string {
	digest, _ := digestWithPrefix(struct {
		ResultProtocol string `json:"result_protocol"`
		Acceptance     string `json:"acceptance_protocol"`
		GraphSchema    int    `json:"graph_schema"`
		FormatDetector string `json:"format_detector"`
		Workbench      string `json:"workbench_protocol"`
	}{"map_scan_result.v2", acceptanceReceiptProtocolV1, store.SchemaVersion, formatDetectorVersion, workbenchProtocolV2})
	return digest
}

func loadScanCache(paths rt.Paths) (scanCacheFile, error) {
	var cache scanCacheFile
	if err := readJSON(scanCachePath(paths), &cache); err != nil {
		return scanCacheFile{}, err
	}
	return cache, nil
}

func scanCachePath(paths rt.Paths) string {
	return filepath.Join(paths.RuntimeDir, "cache", scanCacheFileName)
}

func cacheRuntimePath() string {
	return filepath.ToSlash(filepath.Join(rt.SpecifyDir, rt.CognitionDir, "cache", scanCacheFileName))
}

func cachePacketID(generationID string, sequence int) string {
	suffix := strings.ToLower(strings.TrimPrefix(generationID, "GEN-"))
	return fmt.Sprintf("reuse-%s-%03d", suffix, sequence)
}

func renderCachePacket(packetID string, bundle scanCacheBundle) string {
	var builder strings.Builder
	builder.WriteString("# Reused Map Scan Scope\n\n")
	builder.WriteString("Runtime cache replay for `")
	builder.WriteString(packetID)
	builder.WriteString("` from content- and contract-matched validated facts. No Agent dispatch is required.\n\n")
	for _, path := range bundle.ScopePaths {
		builder.WriteString("- `")
		builder.WriteString(path)
		builder.WriteString("`\n")
	}
	return builder.String()
}

func deltaPacketID(generationID string, sequence int) string {
	suffix := strings.ToLower(strings.TrimPrefix(generationID, "GEN-"))
	return fmt.Sprintf("delta-%s-%03d", suffix, sequence)
}

func conservativeConfidence(left string, right string) string {
	ranks := map[string]int{"weak": 1, "partial": 2, "low": 2, "medium": 3, "high": 4, "verified": 5}
	left = strings.TrimSpace(left)
	right = strings.TrimSpace(right)
	if left == "" {
		return right
	}
	if right == "" {
		return left
	}
	if ranks[right] == 0 || (ranks[left] != 0 && ranks[left] <= ranks[right]) {
		return left
	}
	return right
}

func effectiveMaxPaths(input PrepareInput) int {
	if input.MaxPaths > 0 {
		return input.MaxPaths
	}
	if input.PacketSize > 0 {
		return input.PacketSize
	}
	return defaultPacketSize
}

func effectiveMaxBytes(input PrepareInput) int64 {
	if input.MaxBytes > 0 {
		return input.MaxBytes
	}
	return defaultPacketBytes
}

func effectiveWorkerBudget(input PrepareInput) int64 {
	if input.WorkerBudgetTokens > 0 {
		return input.WorkerBudgetTokens
	}
	return defaultEffectiveWorkerTokens
}

type packetGroups struct {
	parent []int
	rank   []int
}

func newPacketGroups(size int) *packetGroups {
	groups := &packetGroups{parent: make([]int, size), rank: make([]int, size)}
	for index := range groups.parent {
		groups.parent[index] = index
	}
	return groups
}

func (g *packetGroups) find(value int) int {
	if g.parent[value] != value {
		g.parent[value] = g.find(g.parent[value])
	}
	return g.parent[value]
}

func (g *packetGroups) union(left int, right int) {
	leftRoot := g.find(left)
	rightRoot := g.find(right)
	if leftRoot == rightRoot {
		return
	}
	if g.rank[leftRoot] < g.rank[rightRoot] {
		leftRoot, rightRoot = rightRoot, leftRoot
	}
	g.parent[rightRoot] = leftRoot
	if g.rank[leftRoot] == g.rank[rightRoot] {
		g.rank[leftRoot]++
	}
}
