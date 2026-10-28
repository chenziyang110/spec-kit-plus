package query

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"reflect"
	"sort"
	"strings"

	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtimegate"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/store"
)

const ScopeAvailabilityVersion = 2

type TaskScope struct {
	ReadScope                []string `json:"read_scope"`
	WriteScope               []string `json:"write_scope"`
	AffectedPaths            []string `json:"affected_paths"`
	ReadDependenciesComplete bool     `json:"read_dependencies_complete"`
}

// ScopeBinding can be carried in a navigation capsule. Every field is derived
// anew on a public read; an older contract or changed bytes must be reassessed.
type ScopeBinding struct {
	ContractVersion    int                      `json:"contract_version"`
	ProjectRoot        string                   `json:"project_root"`
	TaskPacketPath     string                   `json:"task_packet_path"`
	TaskPacketSHA256   string                   `json:"task_packet_sha256"`
	SourceDigest       string                   `json:"source_digest"`
	NavigationSnapshot store.NavigationSnapshot `json:"navigation_snapshot"`
	StatusDigest       string                   `json:"status_digest"`
}

type ScopeDebt struct {
	ID        string   `json:"id"`
	Relation  string   `json:"relation"`
	Reason    string   `json:"reason"`
	Paths     []string `json:"paths"`
	ProofGaps []string `json:"proof_gaps,omitempty"`
}

type ScopePolicy struct {
	Classification string `json:"classification"`
	Basis          string `json:"basis"`
}

type ScopeAvailability struct {
	ContractVersion         int                   `json:"contract_version"`
	Status                  string                `json:"status"`
	Availability            string                `json:"availability"`
	ScopeReady              bool                  `json:"scope_ready"`
	Scope                   TaskScope             `json:"scope"`
	Policy                  ScopePolicy           `json:"scope_policy"`
	Binding                 ScopeBinding          `json:"binding"`
	GlobalStatus            rt.Status             `json:"global_status"`
	Agreement               runtimegate.Agreement `json:"runtime_agreement"`
	Debt                    []ScopeDebt           `json:"debt_assessments"`
	Reasons                 []string              `json:"reasons"`
	MinimalLiveReads        []string              `json:"minimal_live_reads"`
	ProofPaths              []string              `json:"proof_paths"`
	EpistemicContract       EpistemicContract     `json:"epistemic_contract"`
	ClaimReady              bool                  `json:"claim_ready"`
	SourceChangesAuthorized bool                  `json:"source_changes_authorized"`
	ReviewRequired          bool                  `json:"review_required"`
	HumanAcceptRequired     bool                  `json:"human_accept_required"`
	RecommendedNextAction   string                `json:"recommended_next_action"`
}

type scopeOwner struct{ path, node, relation, confidence, evidencePath, hash string }

func ParseScopeBinding(data []byte) (ScopeBinding, error) {
	var binding ScopeBinding
	decoder := json.NewDecoder(bytes.NewReader(data))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&binding); err != nil {
		return binding, fmt.Errorf("invalid scope availability binding: %w", err)
	}
	if decoder.Decode(new(any)) != io.EOF {
		return binding, fmt.Errorf("scope binding must contain exactly one object")
	}
	if binding.ContractVersion != ScopeAvailabilityVersion || binding.TaskPacketSHA256 == "" || binding.SourceDigest == "" || binding.StatusDigest == "" || binding.NavigationSnapshot.Digest == "" {
		return binding, fmt.Errorf("incompatible_scope_availability: rerun cognition check with the current task packet")
	}
	return binding, nil
}

// CheckScopeAvailability uses existing runtime, Store snapshot and closure
// owners. It does not write status, repair debt, or enter a workflow.
func CheckScopeAvailability(paths rt.Paths, packetPath string, previous *ScopeBinding) (ScopeAvailability, error) {
	payload := ScopeAvailability{ContractVersion: ScopeAvailabilityVersion, Status: "blocked", Availability: "unavailable", Policy: ScopePolicy{Classification: "baseline-unavailable", Basis: "runtime_baseline_unavailable"}, Debt: []ScopeDebt{}, Reasons: []string{}, MinimalLiveReads: []string{}, EpistemicContract: NewEpistemicContract(), ReviewRequired: true, HumanAcceptRequired: true, RecommendedNextAction: "verify_minimal_live_reads"}
	packetPath, err := scopePath(packetPath)
	if err != nil {
		return payload, fmt.Errorf("task packet: %w", err)
	}
	packet, err := scopeReadFile(paths.Root, packetPath)
	if err != nil {
		return payload, err
	}
	scope, err := parseTaskScope(packet)
	if err != nil {
		return payload, err
	}
	payload.Scope = scope
	payload.MinimalLiveReads = scopeStrings(append(append([]string{}, scope.ReadScope...), scope.WriteScope...))
	payload.Binding = ScopeBinding{ContractVersion: ScopeAvailabilityVersion, ProjectRoot: filepath.ToSlash(paths.Root), TaskPacketPath: packetPath, TaskPacketSHA256: scopeDigest(packet)}
	status, err := rt.ReadStatus(paths)
	if err != nil {
		payload.Reasons = append(payload.Reasons, "runtime_status_unavailable")
		return payload, nil
	}
	payload.GlobalStatus = status
	payload.Binding.StatusDigest = navigationStatusDigest(status)
	agreement, exists := runtimegate.CheckExisting(paths)
	payload.Agreement = agreement
	if !exists || agreement.Status != "ok" || !status.GraphReady || status.Readiness == rt.NeedsRebuildReadiness || status.Readiness == rt.UnsupportedReadiness {
		payload.Reasons = append(payload.Reasons, "runtime_baseline_unavailable")
		return payload, nil
	}
	st, err := store.OpenExisting(paths)
	if err != nil {
		payload.Reasons = append(payload.Reasons, "runtime_baseline_unavailable")
		return payload, nil
	}
	defer st.Close()
	ctx := context.Background()
	read, err := st.BeginNavigationRead(ctx)
	if err != nil {
		return payload, err
	}
	defer read.Close()
	payload.Binding.NavigationSnapshot = read.Snapshot
	owners, err := readScopeOwners(ctx, st)
	if err != nil {
		return payload, err
	}
	requested := payload.MinimalLiveReads
	taskProof, err := buildScopeSourceProof(ctx, paths.Root, st, owners, requested)
	if err != nil {
		return payload, err
	}
	closure := taskProof.Closure
	sourceBasis := taskProof.Basis
	payload.Scope.AffectedPaths = taskProof.Paths
	payload.MinimalLiveReads = scopeStrings(append(payload.MinimalLiveReads, payload.Scope.AffectedPaths...))
	payload.ProofPaths = append([]string{}, taskProof.Paths...)
	payload.Reasons = append(payload.Reasons, taskProof.Reasons...)
	writeClosure, err := st.AffectedClosureForPathsWithBudget(ctx, scope.WriteScope, store.ClosureBudget{MaxNodes: 1000})
	if err != nil {
		return payload, err
	}
	payload.Policy = scopeAvailabilityPolicy(scope.WriteScope, owners, writeClosure)
	payload.Availability = "ready"
	if !scope.ReadDependenciesComplete {
		payload.Reasons = append(payload.Reasons, "packet_read_dependencies_unknown")
	}
	debts := append([]rt.DebtRecord{}, status.DirtyDebts...)
	if len(debts) == 0 && (status.Dirty || status.Freshness != rt.ReadyFreshness || len(status.StaleReasons) > 0) {
		debts = append(debts, rt.DebtRecord{ID: "unattributed-global-debt", Paths: scopeStrings(append(status.DirtyScopePaths, status.StalePaths...)), Reason: "global_state_without_complete_debt_provenance"})
	}
	for _, debt := range debts {
		assessment := ScopeDebt{ID: debt.ID, Relation: "unknown", Reason: "debt_scope_or_current_owner_evidence_unknown", Paths: debt.Paths}
		debtProof, err := buildScopeSourceProof(ctx, paths.Root, st, owners, debt.Paths)
		if err != nil {
			return payload, err
		}
		assessment.ProofGaps = debtProof.Reasons
		if err := mergeScopeSourceBasis(sourceBasis, debtProof.Basis); err != nil {
			return payload, err
		}
		payload.ProofPaths = scopeStrings(append(payload.ProofPaths, debtProof.Paths...))
		if pathsOverlap(taskProof.Paths, debtProof.Paths) || pathsOverlap(requested, debt.Paths) || scopeIntersect(closure.NodeIDs, debtProof.Closure.NodeIDs) {
			assessment.Relation, assessment.Reason = "related", "owner_dependency_or_current_evidence_sources_intersect"
		} else if taskProof.Complete && debtProof.Complete {
			assessment.Relation, assessment.Reason = "unrelated", "complete_current_source_owner_closures_disjoint"
		}
		if assessment.Relation != "unrelated" {
			payload.MinimalLiveReads = scopeStrings(append(payload.MinimalLiveReads, debtProof.Paths...))
		}
		payload.Debt = append(payload.Debt, assessment)
		if assessment.Relation != "unrelated" {
			payload.Reasons = append(payload.Reasons, "debt_"+assessment.Relation+":"+assessment.ID)
		}
	}
	payload.Binding.SourceDigest = scopeObjectDigest(sourceBasis)
	// Stale paths may coexist with precise debt rows; never silently drop them.
	for _, stale := range status.StalePaths {
		covered := false
		for _, debt := range debts {
			if pathsOverlap([]string{stale}, debt.Paths) {
				covered = true
			}
		}
		if !covered {
			payload.Reasons = append(payload.Reasons, "unattributed_stale_path:"+stale)
		}
	}
	for _, reason := range scopeStrings(append(append([]string{}, status.DirtyReasons...), status.StaleReasons...)) {
		attributed := false
		for _, debt := range debts {
			if debt.Reason == reason {
				attributed = true
			}
		}
		if !attributed {
			payload.Reasons = append(payload.Reasons, "unattributed_global_reason:"+reason)
		}
	}
	if previous != nil && !reflect.DeepEqual(*previous, payload.Binding) {
		payload.Reasons = append(payload.Reasons, "stale_scope_availability")
	}
	if err := validateNavigationRead(paths, status, read); err != nil {
		return payload, err
	}
	packetAfter, err := scopeReadFile(paths.Root, packetPath)
	if err != nil || !bytes.Equal(packet, packetAfter) {
		return payload, fmt.Errorf("task packet changed during availability check; rerun cognition check")
	}
	if err := recheckScopeSourceBasis(paths.Root, payload.ProofPaths, sourceBasis); err != nil {
		return payload, err
	}
	packetAfter, err = scopeReadFile(paths.Root, packetPath)
	if err != nil || !bytes.Equal(packet, packetAfter) {
		return payload, fmt.Errorf("task packet changed during proof source recheck; rerun cognition check")
	}
	if err := validateNavigationRead(paths, status, read); err != nil {
		return payload, err
	}
	payload.Reasons = scopeStrings(payload.Reasons)
	if len(payload.Reasons) > 0 {
		payload.Availability = "degraded"
	} else {
		payload.ScopeReady, payload.Status, payload.RecommendedNextAction = true, "ok", "use_scoped_cognition_and_verify_live_sources"
	}
	return payload, nil
}

func parseTaskScope(data []byte) (TaskScope, error) {
	var err error
	var packet map[string]json.RawMessage
	if err := json.Unmarshal(data, &packet); err != nil || packet == nil {
		return TaskScope{}, fmt.Errorf("task packet must be a JSON object")
	}
	var scope TaskScope
	var version int
	_ = json.Unmarshal(packet["version"], &version)
	var pythonVersion int
	_ = json.Unmarshal(packet["packet_version"], &pythonVersion)
	var schema string
	_ = json.Unmarshal(packet["schema"], &schema)
	var id string
	_ = json.Unmarshal(packet["task_id"], &id)
	var feature string
	_ = json.Unmarshal(packet["feature_id"], &feature)
	if id != strings.TrimSpace(id) || feature != strings.TrimSpace(feature) {
		return scope, fmt.Errorf("task packet identity must be exact and nonempty")
	}
	switch {
	case version == 2 && pythonVersion == 0 && id != "" && feature != "":
		scope.ReadScope, err = scopePathArray(packet["read_scope"], "native read_scope")
		if err != nil {
			return scope, err
		}
		scope.WriteScope, err = scopePathArray(packet["write_scope"], "native write_scope")
		if err != nil {
			return scope, err
		}
		scope.ReadDependenciesComplete = true
	case pythonVersion == 2 && version == 0 && id != "" && feature != "":
		var fields map[string]json.RawMessage
		if err := json.Unmarshal(packet["scope"], &fields); err != nil || fields == nil {
			return scope, fmt.Errorf("invalid Python PacketScope")
		}
		scope.ReadScope, err = scopePathArray(fields["read_scope"], "Python read_scope")
		if err != nil {
			return scope, err
		}
		scope.WriteScope, err = scopePathArray(fields["write_scope"], "Python write_scope")
		if err != nil {
			return scope, err
		}
		scope.ReadDependenciesComplete = true
	case schema == "quick-worker-packet-v1":
		var workID string
		_ = json.Unmarshal(packet["work_item_id"], &workID)
		if workID == "" || workID != strings.TrimSpace(workID) {
			return scope, fmt.Errorf("Quick packet requires work_item_id")
		}
		scope.WriteScope, err = scopePathArray(packet["write_scope"], "Quick write_scope")
		if err != nil {
			return scope, err
		}
		// The current Quick compiler has no read_scope contract. Its prose scope
		// and evidence strings cannot safely masquerade as complete dependencies.
		scope.ReadScope = []string{}
		if raw, present := packet["read_scope"]; present {
			scope.ReadScope, err = scopePathArray(raw, "Quick read_scope")
			if err != nil {
				return scope, err
			}
			scope.ReadDependenciesComplete = true
		}
	default:
		return scope, fmt.Errorf("unsupported current task packet contract; recompile through its owning native/Python route")
	}
	for _, list := range [][]string{scope.ReadScope, scope.WriteScope} {
		for _, value := range list {
			if _, err := scopePath(value); err != nil {
				return scope, fmt.Errorf("invalid concrete task scope %q: %w", value, err)
			}
		}
	}
	scope.ReadScope, scope.WriteScope, scope.AffectedPaths = scopeStrings(scope.ReadScope), scopeStrings(scope.WriteScope), []string{}
	if len(scope.ReadScope)+len(scope.WriteScope) == 0 {
		return scope, fmt.Errorf("task packet requires a non-empty concrete read or write scope")
	}
	return scope, nil
}

func scopePathArray(raw json.RawMessage, label string) ([]string, error) {
	trimmed := bytes.TrimSpace(raw)
	if len(trimmed) == 0 || trimmed[0] != '[' {
		return nil, fmt.Errorf("%s requires an explicit array of concrete paths", label)
	}
	var paths []string
	if err := json.Unmarshal(trimmed, &paths); err != nil {
		return nil, fmt.Errorf("invalid %s: expected an array of strings", label)
	}
	return paths, nil
}

func scopePath(value string) (string, error) {
	if value == "" || value != strings.TrimSpace(value) || strings.ContainsAny(value, "\\*?[]{}:#\x00") || filepath.IsAbs(value) {
		return "", fmt.Errorf("expected an exact repository-relative path")
	}
	clean := filepath.ToSlash(filepath.Clean(value))
	if clean != value || clean == "." || clean == ".." || clean == ".git" || strings.HasPrefix(clean, "../") || strings.HasPrefix(clean, ".git/") {
		return "", fmt.Errorf("path must stay within the project")
	}
	if clean == ".specify/project-cognition" || strings.HasPrefix(clean, ".specify/project-cognition/") {
		return "", fmt.Errorf("private cognition storage is not a task source scope")
	}
	return clean, nil
}

func scopeReadFile(root, path string) ([]byte, error) {
	abs, err := scopeSafePath(root, path)
	if err != nil {
		return nil, err
	}
	return os.ReadFile(abs)
}

func scopeSafePath(root, path string) (string, error) {
	if _, err := scopePath(path); err != nil {
		return "", err
	}
	abs := filepath.Join(root, filepath.FromSlash(path))
	current := root
	for _, part := range strings.Split(path, "/") {
		current = filepath.Join(current, part)
		info, err := os.Lstat(current)
		if os.IsNotExist(err) {
			continue
		}
		if err != nil {
			return "", err
		}
		if info.Mode()&os.ModeSymlink != 0 {
			return "", fmt.Errorf("scope path crosses symlink: %s", path)
		}
	}
	return abs, nil
}

func scopeSourceBasis(root string, paths []string) ([]string, map[string]string, error) {
	basis := map[string]string{}
	for _, path := range scopeStrings(paths) {
		abs, err := scopeSafePath(root, path)
		if err != nil {
			return nil, nil, err
		}
		info, err := os.Lstat(abs)
		if os.IsNotExist(err) {
			basis[path] = "missing"
			continue
		}
		if err != nil {
			return nil, nil, err
		}
		if info.IsDir() {
			basis[path] = "directory"
			err = filepath.WalkDir(abs, func(current string, entry os.DirEntry, walkErr error) error {
				if walkErr != nil {
					return walkErr
				}
				if entry.Type()&os.ModeSymlink != 0 {
					return fmt.Errorf("scope contains symlink: %s", path)
				}
				if entry.IsDir() {
					return nil
				}
				rel, relErr := filepath.Rel(root, current)
				if relErr != nil {
					return relErr
				}
				data, readErr := scopeReadFile(root, filepath.ToSlash(rel))
				if readErr != nil {
					return readErr
				}
				basis[filepath.ToSlash(rel)] = scopeDigest(data)
				return nil
			})
			if err != nil {
				return nil, nil, err
			}
		} else if info.Mode().IsRegular() {
			data, err := scopeReadFile(root, path)
			if err != nil {
				return nil, nil, err
			}
			basis[path] = scopeDigest(data)
		} else {
			return nil, nil, fmt.Errorf("scope path is not a regular source: %s", path)
		}
	}
	files := []string{}
	for path, hash := range basis {
		if hash != "directory" {
			files = append(files, path)
		}
	}
	return scopeStrings(files), basis, nil
}

func readScopeOwners(ctx context.Context, st *store.Store) ([]scopeOwner, error) {
	rows, err := st.ScopeOwners(ctx)
	if err != nil {
		return nil, err
	}
	owners := []scopeOwner{}
	for _, row := range rows {
		owners = append(owners, scopeOwner{path: row.Path, node: row.NodeID, relation: row.Relation, confidence: row.Confidence, evidencePath: row.EvidencePath, hash: row.ContentHash})
	}
	return owners, nil
}

type scopeSourceProof struct {
	Paths    []string
	Basis    map[string]string
	Closure  store.AffectedClosure
	Reasons  []string
	Complete bool
}

// Both task and debt traverse the SAME Store-owned source evidence closure.
// A referenced evidence source may lead to another owner, graph neighbor, or
// claim source; stop only at a fixed point or an explicit conservative limit.
func buildScopeSourceProof(ctx context.Context, root string, st *store.Store, owners []scopeOwner, initial []string) (scopeSourceProof, error) {
	proof := scopeSourceProof{Paths: []string{}, Basis: map[string]string{}, Reasons: []string{}}
	for _, path := range scopeStrings(initial) {
		if _, err := scopePath(path); err != nil {
			proof.Reasons = append(proof.Reasons, "source_scope_invalid")
		} else {
			proof.Paths = append(proof.Paths, path)
		}
	}
	if len(proof.Paths) == 0 {
		proof.Reasons = append(proof.Reasons, "source_scope_empty")
		return proof, nil
	}
	_, initialBasis, err := scopeSourceBasis(root, proof.Paths)
	if err != nil {
		return proof, err
	}
	proof.Basis = initialBasis
	for round := 0; round < 1000; round++ {
		closure, err := st.AffectedClosureForPathsWithBudget(ctx, proof.Paths, store.ClosureBudget{MaxNodes: 1000})
		if err != nil {
			return proof, err
		}
		proof.Closure = closure
		if closure.Truncated {
			proof.Reasons = append(proof.Reasons, "source_closure_incomplete")
		}
		if len(closure.NodeIDs) == 0 {
			proof.Reasons = append(proof.Reasons, "source_owner_unknown")
		}
		for _, node := range closure.NodeIDs {
			if len(ownerPaths(owners, []string{node})) == 0 {
				proof.Reasons = append(proof.Reasons, "affected_node_owner_unknown:"+node)
			}
		}
		material, err := st.ScopeProofMaterialForNodeIDs(ctx, closure.NodeIDs)
		if err != nil {
			return proof, err
		}
		proof.Reasons = append(proof.Reasons, material.IncompleteReasons...)
		nextPaths := append(append([]string{}, proof.Paths...), ownerPaths(owners, closure.NodeIDs)...)
		for _, evidence := range material.Evidence {
			if _, err := scopePath(evidence.SourcePath); err != nil {
				proof.Reasons = append(proof.Reasons, "evidence_source_unknown:"+evidence.OwnerKind+":"+evidence.OwnerID)
			} else {
				nextPaths = append(nextPaths, evidence.SourcePath)
			}
		}
		nextPaths = scopeStrings(nextPaths)
		if len(nextPaths) > 1000 {
			proof.Reasons = append(proof.Reasons, "evidence_path_budget_exhausted")
			break
		}
		files, basis, err := scopeSourceBasis(root, nextPaths)
		if err != nil {
			return proof, err
		}
		if err := mergeScopeSourceBasis(proof.Basis, basis); err != nil {
			return proof, err
		}
		for _, file := range files {
			if !completeScopeOwner(file, owners, basis) {
				proof.Reasons = append(proof.Reasons, "source_coverage_unknown:"+file)
			}
		}
		for _, evidence := range material.Evidence {
			if evidence.ContentHash == "" || strings.TrimPrefix(evidence.ContentHash, "sha256:") != strings.TrimPrefix(basis[evidence.SourcePath], "sha256:") {
				proof.Reasons = append(proof.Reasons, "evidence_source_hash_unknown:"+evidence.OwnerKind+":"+evidence.OwnerID+":"+evidence.EvidenceID)
			}
		}
		stable := reflect.DeepEqual(nextPaths, proof.Paths)
		proof.Paths = nextPaths
		if stable {
			proof.Reasons = scopeStrings(proof.Reasons)
			proof.Complete = len(proof.Reasons) == 0
			return proof, nil
		}
	}
	proof.Reasons = scopeStrings(append(proof.Reasons, "source_proof_fixed_point_incomplete"))
	return proof, nil
}

func mergeScopeSourceBasis(target, source map[string]string) error {
	for path, hash := range source {
		if before, exists := target[path]; exists && before != hash {
			return fmt.Errorf("source proof bytes changed during availability check at %s; rerun cognition check", path)
		}
		target[path] = hash
	}
	return nil
}

func recheckScopeSourceBasis(root string, paths []string, before map[string]string) error {
	_, after, err := scopeSourceBasis(root, paths)
	if err != nil || !reflect.DeepEqual(before, after) {
		return fmt.Errorf("source proof bytes changed during availability check; rerun cognition check")
	}
	return nil
}

func completeScopeOwner(path string, owners []scopeOwner, basis map[string]string) bool {
	found := false
	for _, owner := range owners {
		if owner.path == path {
			if owner.node == "" || owner.relation != "owns" || (owner.confidence != "high" && owner.confidence != "verified") || owner.evidencePath != path || owner.hash == "" || strings.TrimPrefix(owner.hash, "sha256:") != strings.TrimPrefix(basis[path], "sha256:") {
				return false
			}
			found = true
		}
	}
	return found
}

func ownerPaths(owners []scopeOwner, nodes []string) []string {
	out := []string{}
	for _, owner := range owners {
		if scopeIntersect([]string{owner.node}, nodes) {
			out = append(out, owner.path)
		}
	}
	return scopeStrings(out)
}
func pathsOverlap(left, right []string) bool {
	for _, a := range left {
		for _, b := range right {
			if a == b || strings.HasPrefix(a, b+"/") || strings.HasPrefix(b, a+"/") {
				return true
			}
		}
	}
	return false
}
func scopeIntersect(left, right []string) bool {
	set := map[string]bool{}
	for _, v := range left {
		set[v] = true
	}
	for _, v := range right {
		if set[v] {
			return true
		}
	}
	return false
}
func scopeStrings(values []string) []string {
	set := map[string]bool{}
	for _, v := range values {
		set[v] = true
	}
	out := []string{}
	for v := range set {
		out = append(out, v)
	}
	sort.Strings(out)
	return out
}
func scopeDigest(data []byte) string {
	sum := sha256.Sum256(data)
	return fmt.Sprintf("sha256:%x", sum[:])
}
func scopeObjectDigest(value any) string { data, _ := json.Marshal(value); return scopeDigest(data) }

func scopeAvailabilityPolicy(writeScope []string, owners []scopeOwner, closure store.AffectedClosure) ScopePolicy {
	if closure.Truncated {
		return ScopePolicy{"baseline-unavailable", "complete_closure_unavailable"}
	}
	if len(writeScope) == 0 {
		return ScopePolicy{"read-only/no-change", "packet_declares_no_product_writes"}
	}
	direct := map[string]bool{}
	for _, path := range writeScope {
		found := false
		for _, owner := range owners {
			if pathsOverlap([]string{path}, []string{owner.path}) && (owner.path == path || strings.HasPrefix(owner.path, path+"/")) {
				direct[owner.node] = true
				found = true
			}
		}
		if !found {
			return ScopePolicy{"baseline-unavailable", "source_path_owner_unknown"}
		}
	}
	for _, node := range closure.NodeIDs {
		if !direct[node] {
			return ScopePolicy{"propagated", "typed_write_owner_dependency_closure"}
		}
	}
	return ScopePolicy{"local", "complete_closure_stays_with_direct_owners"}
}
