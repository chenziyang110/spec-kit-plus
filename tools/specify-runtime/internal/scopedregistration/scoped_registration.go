package scopedregistration

import (
	"bytes"
	"context"
	"crypto/sha256"
	"database/sql"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path"
	"path/filepath"
	"sort"
	"strings"

	changemodel "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/changes/model"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/claim"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/compiler"
	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/scanartifacts"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/store"
)

const Schema = "cognition-scoped-registration.v1"

type Request struct {
	Schema string        `json:"schema"`
	Proof  ProofBinding  `json:"proof"`
	Work   WorkBinding   `json:"work"`
	Source SourceBinding `json:"source"`
	Delta  Delta         `json:"delta"`
	Result ResultIntent  `json:"result"`
}

type ProofBinding struct {
	Kind      string `json:"kind"`
	BindingID string `json:"binding_id"`
	Workflow  string `json:"workflow"`
	Scope     string `json:"scope"`
	DoRef     string `json:"do_ref"`
}

type WorkBinding struct {
	WorkID             string          `json:"work_id"`
	AttemptID          string          `json:"attempt_id"`
	AcceptedOutputRefs []AcceptedRef   `json:"accepted_output_refs"`
	Attrs              json.RawMessage `json:"attrs,omitempty"`
}

type AcceptedRef struct {
	Path   string `json:"path"`
	SHA256 string `json:"sha256"`
}

type SourceBinding struct {
	ActiveGenerationID string       `json:"active_generation_id"`
	SourceRevision     string       `json:"source_revision"`
	SourceHashes       []SourceHash `json:"source_hashes"`
}

type SourceHash struct {
	Path   string `json:"path"`
	SHA256 string `json:"sha256"`
}

type Delta struct {
	ChangedPaths []PathChange      `json:"changed_paths"`
	Evidence     []Evidence        `json:"evidence"`
	Nodes        []Node            `json:"nodes"`
	Edges        []Edge            `json:"edges"`
	Observations []Observation     `json:"observations"`
	Claims       []Claim           `json:"claims"`
	Aliases      []Alias           `json:"aliases"`
	PathIndex    []PathIndex       `json:"path_index"`
	Retirements  []Retirement      `json:"retirements"`
	Obligations  ObligationSummary `json:"obligations"`
}

type PathChange struct {
	Operation    string   `json:"operation"`
	Path         string   `json:"path"`
	OldPath      string   `json:"old_path"`
	NodeID       string   `json:"node_id"`
	EvidenceRefs []string `json:"evidence_refs"`
}

type Evidence struct {
	ID          string         `json:"id"`
	SourceKind  string         `json:"source_kind"`
	SourcePath  string         `json:"source_path"`
	CommitSHA   string         `json:"commit_sha"`
	Span        string         `json:"span"`
	Extractor   string         `json:"extractor"`
	ContentHash string         `json:"content_hash"`
	Attrs       map[string]any `json:"attrs"`
}

type Node struct {
	ID          string         `json:"id"`
	Type        string         `json:"type"`
	Title       string         `json:"title"`
	Confidence  string         `json:"confidence"`
	EvidenceIDs []string       `json:"evidence_ids"`
	Attrs       map[string]any `json:"attrs"`
}

type Edge struct {
	ID          string         `json:"id"`
	Type        string         `json:"type"`
	SourceID    string         `json:"source_id"`
	TargetID    string         `json:"target_id"`
	Confidence  string         `json:"confidence"`
	EvidenceIDs []string       `json:"evidence_ids"`
	Attrs       map[string]any `json:"attrs"`
}

type Observation struct {
	ID              string         `json:"id"`
	ObservationType string         `json:"observation_type"`
	Summary         string         `json:"summary"`
	EvidenceIDs     []string       `json:"evidence_ids"`
	Attrs           map[string]any `json:"attrs"`
}

type Claim struct {
	ID                       string               `json:"id"`
	NodeID                   string               `json:"node_id"`
	GraphClaimType           string               `json:"graph_claim_type"`
	Summary                  string               `json:"summary"`
	RequestedState           claim.State          `json:"requested_state"`
	SupportingEvidenceIDs    []string             `json:"supporting_evidence_ids"`
	ContradictingEvidenceIDs []string             `json:"contradicting_evidence_ids"`
	Verifications            []claim.Verification `json:"verifications"`
	Attrs                    map[string]any       `json:"attrs"`
}

type Alias struct {
	ID              string `json:"id"`
	Alias           string `json:"alias"`
	NormalizedAlias string `json:"normalized_alias"`
	TargetType      string `json:"target_type"`
	TargetID        string `json:"target_id"`
	Language        string `json:"language"`
	Source          string `json:"source"`
	Confidence      string `json:"confidence"`
	EvidenceID      string `json:"evidence_id"`
}

type PathIndex struct {
	ID         string `json:"id"`
	Path       string `json:"path"`
	NodeID     string `json:"node_id"`
	Relation   string `json:"relation"`
	Confidence string `json:"confidence"`
	EvidenceID string `json:"evidence_id"`
}

type Retirement struct {
	Kind   string `json:"kind"`
	ID     string `json:"id"`
	Path   string `json:"path"`
	Reason string `json:"reason"`
}

type ObligationSummary struct {
	Owners              []string `json:"owners"`
	Consumers           []string `json:"consumers"`
	Interfaces          []string `json:"interfaces"`
	StateContracts      []string `json:"state_contracts"`
	GeneratedChain      []string `json:"generated_chain"`
	VerificationEntries []string `json:"verification_entries"`
	InvalidatedAliases  []string `json:"invalidated_aliases"`
	Unknowns            []string `json:"unknowns"`
}

type ResultIntent struct {
	State  string `json:"state"`
	Reason string `json:"reason"`
}

type Payload struct {
	Schema             string                `json:"schema"`
	Status             string                `json:"status"`
	RegistrationID     string                `json:"registration_id"`
	ActiveGenerationID string                `json:"active_generation_id"`
	SourceRevision     string                `json:"source_revision"`
	PacketSHA256       string                `json:"packet_sha256"`
	Replayed           bool                  `json:"replayed"`
	Registered         map[string][]string   `json:"registered"`
	Retired            map[string][]string   `json:"retired"`
	StaleClaims        []string              `json:"stale_claims"`
	AffectedClosure    store.AffectedClosure `json:"affected_closure"`
	NegativeQueries    []map[string]string   `json:"negative_queries"`
	ObligationSummary  ObligationSummary     `json:"obligation_summary"`
	ValidationDebt     []string              `json:"validation_debt"`
	ClaimReady         bool                  `json:"claim_ready"`
	Compilation        compiler.Result       `json:"compilation"`
	NextArgv           [][]string            `json:"next_argv"`
	Details            map[string]any        `json:"details"`
}

type ProofBasis struct {
	Kind                   string            `json:"kind"`
	BindingID              string            `json:"binding_id,omitempty"`
	Workflow               string            `json:"workflow,omitempty"`
	Scope                  string            `json:"scope,omitempty"`
	WorkID                 string            `json:"work_id,omitempty"`
	AttemptID              string            `json:"attempt_id,omitempty"`
	SourceRevision         string            `json:"source_revision,omitempty"`
	Source                 map[string]string `json:"source,omitempty"`
	OwnedDelta             []string          `json:"owned_delta,omitempty"`
	Digest                 string            `json:"digest,omitempty"`
	AcceptedOutputSHA256   string            `json:"accepted_output_sha256,omitempty"`
	DependencyRefs         []string          `json:"dependency_refs,omitempty"`
	RequiredDependencyRefs []string          `json:"required_dependency_refs,omitempty"`
	ParentUpdateID         string            `json:"parent_update_id,omitempty"`
	ParentIntentID         string            `json:"parent_intent_id,omitempty"`
}

type nativeProof = ProofBasis

func Parse(data []byte) (Request, []byte, error) {
	trimmed := bytes.TrimSpace(data)
	var request Request
	decoder := json.NewDecoder(bytes.NewReader(trimmed))
	decoder.UseNumber()
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&request); err != nil {
		return Request{}, nil, err
	}
	var extra any
	if err := decoder.Decode(&extra); err != io.EOF {
		if err == nil {
			err = fmt.Errorf("unexpected trailing JSON")
		}
		return Request{}, nil, err
	}
	if strings.TrimSpace(request.Schema) != Schema {
		return Request{}, nil, fmt.Errorf("schema must be %q", Schema)
	}
	canonical, err := json.Marshal(request)
	if err != nil {
		return Request{}, nil, err
	}
	return request, canonical, nil
}

func Apply(ctx context.Context, paths rt.Paths, request Request, canonical []byte) (Payload, error) {
	return ApplyWithGuards(ctx, paths, request, canonical, nil)
}

type Guards struct {
	ProofBasis   *ProofBasis
	BeforeCommit func() error
}

func ApplyWithGuards(ctx context.Context, paths rt.Paths, request Request, canonical []byte, guards *Guards) (Payload, error) {
	return applyWithGuards(ctx, paths, request, canonical, guards, nil)
}

func ApplyWithProofBasis(ctx context.Context, paths rt.Paths, request Request, canonical []byte, basis ProofBasis, guards *Guards) (Payload, error) {
	return applyWithGuards(ctx, paths, request, canonical, guards, &basis)
}

func applyWithGuards(ctx context.Context, paths rt.Paths, request Request, canonical []byte, guards *Guards, suppliedBasis *ProofBasis) (Payload, error) {
	packetSHA := sha256Hex(canonical)
	payload := Payload{
		Schema:            Schema,
		Status:            "blocked",
		RegistrationID:    "",
		SourceRevision:    "",
		PacketSHA256:      packetSHA,
		Registered:        emptyRegistered(),
		Retired:           map[string][]string{"aliases": []string{}, "paths": []string{}, "claims": []string{}},
		StaleClaims:       []string{},
		NegativeQueries:   []map[string]string{},
		ObligationSummary: request.Delta.Obligations,
		ValidationDebt:    validationDebt(request),
		ClaimReady:        false,
		Details:           map[string]any{},
	}
	if err := validateRequest(paths.Root, request); err != nil {
		return payload, err
	}
	if strings.TrimSpace(request.Result.State) == "registered" && len(payload.ValidationDebt) > 0 {
		return payload, fmt.Errorf("scoped registration has unresolved validation debt: %s", strings.Join(payload.ValidationDebt, ", "))
	}
	proof, err := proofBasis(paths.Root, request.Proof, guards, suppliedBasis)
	if err != nil {
		return payload, err
	}
	registrationID, err := scopedRegistrationID(request, proof, packetSHA)
	if err != nil {
		return payload, err
	}
	payload.RegistrationID = registrationID
	payload.SourceRevision = proof.SourceRevision
	payload.Details["native_proof"] = nativeProofPayload(proof)
	if err := verifyRequestMatchesProofBasis(request, proof); err != nil {
		return payload, err
	}
	if err := verifyProofSource(paths.Root, proof); err != nil {
		return payload, err
	}
	st, err := store.OpenExisting(paths)
	if err != nil {
		return payload, fmt.Errorf("open active cognition store: %w", err)
	}
	defer st.Close()
	activeGenerationID, err := st.ActiveGenerationID(ctx)
	if err != nil {
		return payload, err
	}
	payload.ActiveGenerationID = activeGenerationID
	if activeGenerationID == "" {
		return payload, fmt.Errorf("project-cognition.db has no active generation")
	}
	if expected := strings.TrimSpace(request.Source.ActiveGenerationID); expected != "" && expected != activeGenerationID {
		return payload, fmt.Errorf("active generation mismatch: got %s want %s", activeGenerationID, expected)
	}
	if err := proofCoversDelta(proof, request); err != nil {
		return payload, err
	}
	coverage, err := evidenceCoverageAgainstProof(paths.Root, proof, request)
	if err != nil {
		return payload, err
	}
	if len(coverage.Debt) > 0 {
		payload.ValidationDebt = uniqueSorted(append(payload.ValidationDebt, coverage.Debt...))
		payload.Details["native_source_evidence_debt"] = coverage.Debt
		payload.Details["native_source_uncovered_evidence"] = sortedStringKeys(coverage.UncoveredEvidence)
		if strings.TrimSpace(request.Result.State) == "registered" {
			return payload, nativeSourceEvidenceDebtError(coverage)
		}
		request = provisionalizeUncoveredEvidence(request, coverage.UncoveredEvidence)
	}
	existingNodes, err := activeRegistrationIDs(ctx, st.DB(), activeGenerationID, "nodes")
	if err != nil {
		return payload, err
	}
	existingEvidence, err := activeRegistrationIDs(ctx, st.DB(), activeGenerationID, "evidence")
	if err != nil {
		return payload, err
	}
	compiled, err := compileRequest(request, existingNodes, existingEvidence)
	if err != nil {
		return payload, err
	}
	payload.Compilation = compiled.Result
	if len(compiled.Result.Conflicts) > 0 {
		return payload, fmt.Errorf("scoped registration compilation conflicts remain: %v", compiled.Result.Conflicts)
	}
	if replay, ok, finalized, storedResult, err := replayRegistration(ctx, st.DB(), registrationID, activeGenerationID, packetSHA); err != nil {
		return payload, err
	} else if ok {
		if finalized {
			replay.Replayed = true
			return replay, nil
		}
		payload, err = finalizeScopedRegistration(ctx, paths, st, request, proof, payload, storedResult, true)
		if err != nil {
			return payload, err
		}
		return payload, nil
	}
	storeResult, err := st.ApplyScopedRegistration(ctx, store.ScopedRegistrationInput{
		RegistrationID:       registrationID,
		ExpectedGenerationID: activeGenerationID,
		PacketSHA256:         packetSHA,
		ParentUpdateID:       proof.ParentUpdateID,
		ParentIntentID:       proof.ParentIntentID,
		ResultState:          strings.TrimSpace(request.Result.State),
		Reason:               request.Result.Reason,
		Package:              compiled.Package,
		PathIndex:            storePathIndex(request.Delta.PathIndex),
		Aliases:              scopedAliases(request),
		Retirements:          storeRetirements(request.Delta.Retirements),
		ChangedPaths:         changedPaths(request),
		NewClaimIDs:          newClaimIDs(request),
		NegativeProbes:       storeNegativeProbes(request),
		BeforeCommit: func() error {
			if guards != nil && guards.BeforeCommit != nil {
				return guards.BeforeCommit()
			}
			return nil
		},
		Attrs: map[string]any{
			"schema":        Schema,
			"packet_sha256": packetSHA,
			"work":          proofWorkBinding(proof),
			"source":        proof.Source,
			"native_proof":  payload.Details["native_proof"],
			"receipt":       payload,
		},
	})
	if err != nil {
		return payload, err
	}
	payload, err = finalizeScopedRegistration(ctx, paths, st, request, proof, payload, storeResult, false)
	if err != nil {
		return payload, err
	}
	return payload, nil
}

func finalizeScopedRegistration(ctx context.Context, paths rt.Paths, st *store.Store, request Request, proof ProofBasis, payload Payload, storeResult store.ScopedRegistrationResult, replayed bool) (Payload, error) {
	payload.Replayed = replayed
	payload.ActiveGenerationID = storeResult.ActiveGenerationID
	payload.Registered = storeResult.Registered
	payload.Retired = storeResult.Retired
	payload.StaleClaims = storeResult.StaleClaims
	payload.NegativeQueries = negativeEvidencePayload(storeResult.NegativeQueries)
	closure, err := st.AffectedClosureForPathsAndNodeIDsWithBudget(ctx, changedPaths(request), registeredNodeIDs(payload.Registered), store.ClosureBudget{MaxNodes: 200})
	if err != nil {
		return payload, err
	}
	payload.AffectedClosure = closure
	if closure.Truncated {
		payload.ValidationDebt = uniqueSorted(append(payload.ValidationDebt, "affected_closure_truncated"))
	}
	payload.Details["evidence_attrs"] = evidenceAttrsPayload(request)
	payload.NextArgv = nextArgv(request, payload)
	if len(payload.ValidationDebt) > 0 {
		payload.Status = "partial"
	} else {
		payload.Status = "ok"
	}
	if proof.ParentUpdateID == "" {
		if err := updateRuntimeStatus(paths, payload, changedPaths(request), strings.TrimSpace(request.Result.State)); err != nil {
			return payload, err
		}
	} else if err := verifyParentRuntimeStatus(paths, proof, payload); err != nil {
		return payload, err
	}
	if err := st.UpdateScopedRegistrationReceipt(ctx, payload.ActiveGenerationID, payload.RegistrationID, payload.PacketSHA256, map[string]any{
		"schema":                     Schema,
		"packet_sha256":              payload.PacketSHA256,
		"work":                       proofWorkBinding(proof),
		"source":                     proof.Source,
		"native_proof":               payload.Details["native_proof"],
		"receipt":                    payload,
		"scoped_registration_result": storeResult,
	}); err != nil {
		return payload, err
	}
	return payload, nil
}

func proofBasis(root string, binding ProofBinding, guards *Guards, supplied *ProofBasis) (ProofBasis, error) {
	if supplied != nil {
		return normalizeProofBasis(*supplied), nil
	}
	if guards != nil && guards.ProofBasis != nil {
		return normalizeProofBasis(*guards.ProofBasis), nil
	}
	legacy, err := loadNativeProof(root, binding)
	if err != nil {
		return ProofBasis{}, err
	}
	return normalizeProofBasis(legacy), nil
}

func normalizeProofBasis(proof ProofBasis) ProofBasis {
	proof.Kind = strings.TrimSpace(proof.Kind)
	proof.BindingID = strings.TrimSpace(proof.BindingID)
	proof.Workflow = strings.TrimSpace(proof.Workflow)
	proof.Scope = strings.TrimSpace(proof.Scope)
	proof.WorkID = strings.TrimSpace(proof.WorkID)
	proof.AttemptID = strings.TrimSpace(proof.AttemptID)
	proof.SourceRevision = strings.TrimSpace(proof.SourceRevision)
	if proof.SourceRevision == "" {
		proof.SourceRevision = strings.TrimSpace(proof.AttemptID)
	}
	if proof.SourceRevision == "" {
		proof.SourceRevision = strings.TrimSpace(proof.Digest)
	}
	proof.Digest = strings.TrimSpace(proof.Digest)
	proof.AcceptedOutputSHA256 = strings.ToLower(strings.TrimPrefix(strings.TrimSpace(proof.AcceptedOutputSHA256), "sha256:"))
	proof.OwnedDelta = normalizePathList(proof.OwnedDelta)
	proof.DependencyRefs = normalizePathList(proof.DependencyRefs)
	proof.RequiredDependencyRefs = normalizePathList(proof.RequiredDependencyRefs)
	proof.ParentUpdateID = strings.TrimSpace(proof.ParentUpdateID)
	proof.ParentIntentID = strings.TrimSpace(proof.ParentIntentID)
	if proof.Source == nil {
		proof.Source = map[string]string{}
	}
	return proof
}

func nativeProofPayload(proof ProofBasis) map[string]any {
	return map[string]any{
		"kind": proof.Kind, "binding_id": proof.BindingID, "workflow": proof.Workflow,
		"scope": proof.Scope, "work_id": proof.WorkID, "attempt_id": proof.AttemptID,
		"source_revision": proof.SourceRevision, "source": proof.Source, "owned_delta": proof.OwnedDelta,
		"digest": proof.Digest, "accepted_output_sha256": proof.AcceptedOutputSHA256,
		"dependency_refs": proof.DependencyRefs, "required_dependency_refs": proof.RequiredDependencyRefs,
		"parent_update_id": proof.ParentUpdateID, "parent_intent_id": proof.ParentIntentID,
	}
}

func scopedRegistrationID(request Request, proof ProofBasis, packetSHA string) (string, error) {
	if strings.TrimSpace(proof.ParentUpdateID) != "" {
		if strings.TrimSpace(proof.ParentIntentID) == "" {
			return "", fmt.Errorf("parent_intent_id is required when parent_update_id is supplied")
		}
		return strings.TrimSpace(proof.ParentUpdateID), nil
	}
	if strings.TrimSpace(proof.ParentIntentID) != "" {
		return "", fmt.Errorf("parent_update_id is required when parent_intent_id is supplied")
	}
	return "scoped-registration:" + stablePart(request.Proof.Kind+"-"+request.Proof.BindingID+"-"+request.Proof.DoRef+"-"+packetSHA[:12]), nil
}

func verifyRequestMatchesProofBasis(request Request, proof ProofBasis) error {
	if v := strings.TrimSpace(request.Work.WorkID); v != "" && proof.WorkID != "" && v != proof.WorkID {
		return fmt.Errorf("work_id contradicts native proof: got %s want %s", v, proof.WorkID)
	}
	if v := strings.TrimSpace(request.Work.AttemptID); v != "" && proof.AttemptID != "" && v != proof.AttemptID {
		return fmt.Errorf("attempt_id contradicts native proof: got %s want %s", v, proof.AttemptID)
	}
	if v := strings.TrimSpace(request.Source.SourceRevision); v != "" && proof.SourceRevision != "" && v != proof.SourceRevision {
		return fmt.Errorf("source_revision contradicts native proof: got %s want %s", v, proof.SourceRevision)
	}
	// accepted_output_refs are audit-only compatibility input. The canonical
	// output basis in the receipt comes from the native owner proof; contradictory
	// attempt/work identity remains rejected above because it changes lineage.
	return nil
}

func scopedAliases(request Request) []store.AliasImport {
	aliases := storeAliases(request.Delta.Aliases)
	seen := map[string]bool{}
	for _, row := range aliases {
		seen[row.TargetID+"\x00"+normalizeAlias(row.NormalizedAlias+" "+row.Alias)] = true
	}
	add := func(nodeID, alias, source, evidenceID string) {
		nodeID = strings.TrimSpace(nodeID)
		alias = strings.TrimSpace(alias)
		if nodeID == "" || alias == "" {
			return
		}
		norm := normalizeAlias(alias)
		key := nodeID + "\x00" + norm
		if seen[key] {
			return
		}
		seen[key] = true
		aliases = append(aliases, store.AliasImport{ID: "A-scoped-" + stablePart(nodeID+"-"+norm+"-"+source), Alias: alias, NormalizedAlias: norm, TargetType: "node", TargetID: nodeID, Language: "unknown", Source: source, Confidence: "partial", EvidenceID: evidenceID})
	}
	for _, node := range request.Delta.Nodes {
		evidenceID := ""
		if len(node.EvidenceIDs) > 0 {
			evidenceID = node.EvidenceIDs[0]
		}
		add(node.ID, node.ID, "scoped_registration_node_id", evidenceID)
		add(node.ID, node.Title, "scoped_registration_title", evidenceID)
	}
	return aliases
}

func updateRuntimeStatus(paths rt.Paths, payload Payload, changed []string, scopeOutcome string) error {
	status, err := rt.ReadStatus(paths)
	if err != nil {
		return fmt.Errorf("read runtime status for scoped registration: %w", err)
	}
	if strings.TrimSpace(status.Status) == "" {
		status.Status = "ok"
	}
	if strings.TrimSpace(status.Freshness) == "" {
		status.Freshness = rt.PartialRefreshFreshness
	}
	if strings.TrimSpace(status.Readiness) == "" {
		status.Readiness = rt.BlockedReadiness
	}
	if strings.TrimSpace(status.RecommendedNextAction) == "" {
		status.RecommendedNextAction = "query"
	}
	status.ActiveGenerationID = payload.ActiveGenerationID
	status.LastUpdateID = payload.RegistrationID
	if strings.TrimSpace(scopeOutcome) == "" {
		scopeOutcome = "partial"
	}
	status.LastUpdateOutcome = scopeOutcome
	status.LastUpdateScopeOutcome = scopeOutcome
	if payload.Status == "ok" && len(payload.ValidationDebt) == 0 && strings.TrimSpace(scopeOutcome) == "registered" {
		status.LastFinalizedUpdateID = payload.RegistrationID
	}
	status.LastRefreshReason = "scoped-registration"
	status.LastRefreshBasis = payload.PacketSHA256
	status.LastRefreshChangedFilesBasis = normalizePathList(changed)
	// Preserve global freshness, dirty/stale scope, and unrelated debt; scoped
	// registration only receipt-binds its own update so public consumers do not
	// report status/DB divergence for a successfully guarded local mutation.
	status.LastUpdatePartialReasons = append([]string{}, payload.ValidationDebt...)
	return rt.WriteStatus(paths, status)
}

func verifyParentRuntimeStatus(paths rt.Paths, proof ProofBasis, payload Payload) error {
	status, err := rt.ReadStatus(paths)
	if err != nil {
		return fmt.Errorf("read runtime status for parent scoped registration: %w", err)
	}
	if got := strings.TrimSpace(status.LastUpdateID); got != strings.TrimSpace(proof.ParentUpdateID) {
		return fmt.Errorf("parent scoped registration status/latest update mismatch: got %q want %q", got, strings.TrimSpace(proof.ParentUpdateID))
	}
	if got := strings.TrimSpace(status.ActiveGenerationID); got != "" && got != payload.ActiveGenerationID {
		return fmt.Errorf("parent scoped registration status generation mismatch: got %q want %q", got, payload.ActiveGenerationID)
	}
	return nil
}

func normalizePathList(values []string) []string {
	out := []string{}
	seen := map[string]bool{}
	for _, value := range values {
		path := normalizePath(value)
		if path != "" && !seen[path] {
			seen[path] = true
			out = append(out, path)
		}
	}
	sort.Strings(out)
	return out
}

func storePathIndex(rows []PathIndex) []store.PathIndexImport {
	out := make([]store.PathIndexImport, 0, len(rows))
	for _, row := range rows {
		out = append(out, store.PathIndexImport{ID: row.ID, Path: row.Path, NodeID: row.NodeID, Relation: row.Relation, Confidence: row.Confidence, EvidenceID: row.EvidenceID})
	}
	return out
}

func storeAliases(rows []Alias) []store.AliasImport {
	out := make([]store.AliasImport, 0, len(rows))
	for _, row := range rows {
		out = append(out, store.AliasImport{ID: row.ID, Alias: row.Alias, NormalizedAlias: row.NormalizedAlias, TargetType: row.TargetType, TargetID: row.TargetID, Language: row.Language, Source: row.Source, Confidence: row.Confidence, EvidenceID: row.EvidenceID})
	}
	return out
}

func storeRetirements(rows []Retirement) []store.ScopedRetirement {
	out := make([]store.ScopedRetirement, 0, len(rows))
	for _, row := range rows {
		out = append(out, store.ScopedRetirement{Kind: row.Kind, ID: row.ID, Path: row.Path, Reason: row.Reason})
	}
	return out
}

func newClaimIDs(request Request) []string {
	out := make([]string, 0, len(request.Delta.Claims))
	for _, row := range request.Delta.Claims {
		if strings.TrimSpace(row.ID) != "" {
			out = append(out, row.ID)
		}
	}
	return uniqueSorted(out)
}

func storeNegativeProbes(request Request) []store.ScopedNegativeProbe {
	out := []store.ScopedNegativeProbe{}
	for _, change := range request.Delta.ChangedPaths {
		switch strings.TrimSpace(change.Operation) {
		case string(changemodel.OperationDelete):
			if path := normalizePath(change.Path); path != "" {
				out = append(out, store.ScopedNegativeProbe{Intent: "negative-path", Query: path, Kind: "path"})
			}
		case string(changemodel.OperationRename):
			if path := normalizePath(change.OldPath); path != "" {
				out = append(out, store.ScopedNegativeProbe{Intent: "negative-path", Query: path, Kind: "path"})
			}
		}
	}
	for _, alias := range request.Delta.Obligations.InvalidatedAliases {
		if strings.TrimSpace(alias) != "" {
			out = append(out, store.ScopedNegativeProbe{Intent: "negative-alias", Query: alias, Kind: "alias"})
		}
	}
	return out
}

func evidenceAttrsPayload(request Request) map[string]map[string]any {
	out := map[string]map[string]any{}
	for _, row := range request.Delta.Evidence {
		if len(row.Attrs) > 0 {
			out[row.ID] = cloneAnyMap(row.Attrs)
		}
	}
	return out
}

func negativeEvidencePayload(rows []store.ScopedNegativeEvidence) []map[string]string {
	out := make([]map[string]string, 0, len(rows))
	for _, row := range rows {
		out = append(out, map[string]string{
			"intent":         row.Intent,
			"query":          row.Query,
			"kind":           row.Kind,
			"observed_count": fmt.Sprint(row.ObservedCount),
			"status":         row.Status,
			"argv":           row.Argv,
		})
	}
	return out
}

func proofWorkBinding(proof ProofBasis) map[string]string {
	return map[string]string{
		"kind":                   proof.Kind,
		"binding_id":             proof.BindingID,
		"workflow":               proof.Workflow,
		"scope":                  proof.Scope,
		"work_id":                proof.WorkID,
		"attempt_id":             proof.AttemptID,
		"digest":                 proof.Digest,
		"source_revision":        proof.SourceRevision,
		"accepted_output_sha256": proof.AcceptedOutputSHA256,
		"parent_update_id":       proof.ParentUpdateID,
		"parent_intent_id":       proof.ParentIntentID,
	}
}

type compiledPackage struct {
	Package scanartifacts.Package
	Result  compiler.Result
}

func compileRequest(request Request, existingNodeIDs, existingEvidenceIDs map[string]bool) (compiledPackage, error) {
	pkg := scanartifacts.Package{
		Evidence:     make([]scanartifacts.EvidenceRow, 0, len(request.Delta.Evidence)),
		Nodes:        make([]scanartifacts.NodeRow, 0, len(request.Delta.Nodes)),
		Edges:        make([]scanartifacts.EdgeRow, 0, len(request.Delta.Edges)),
		Observations: make([]scanartifacts.ObservationRow, 0, len(request.Delta.Observations)),
		Claims:       make([]scanartifacts.ClaimRow, 0, len(request.Delta.Claims)),
	}
	for _, row := range request.Delta.Evidence {
		attrs := cloneAnyMap(row.Attrs)
		sourcePath := row.SourcePath
		if row.SourceKind != "file" && strings.HasPrefix(path.Clean(filepath.ToSlash(strings.TrimSpace(sourcePath))), ".specify/") {
			attrs["runtime_source_path"] = sourcePath
			sourcePath = ""
		}
		pkg.Evidence = append(pkg.Evidence, scanartifacts.EvidenceRow{
			ID: row.ID, SourceKind: row.SourceKind, SourcePath: sourcePath, CommitSHA: row.CommitSHA,
			Span: row.Span, Extractor: row.Extractor, ContentHash: row.ContentHash, Attrs: attrs,
		})
	}
	for _, row := range request.Delta.Nodes {
		pkg.Nodes = append(pkg.Nodes, scanartifacts.NodeRow{
			ID: row.ID, Type: row.Type, Title: row.Title, Confidence: row.Confidence,
			EvidenceIDs: row.EvidenceIDs, Attrs: row.Attrs,
		})
	}
	for _, row := range request.Delta.Edges {
		pkg.Edges = append(pkg.Edges, scanartifacts.EdgeRow{
			ID: row.ID, Type: row.Type, SourceID: row.SourceID, TargetID: row.TargetID,
			Confidence: row.Confidence, EvidenceIDs: row.EvidenceIDs, Attrs: row.Attrs,
		})
	}
	for _, row := range request.Delta.Observations {
		pkg.Observations = append(pkg.Observations, scanartifacts.ObservationRow{
			ID: row.ID, ObservationType: row.ObservationType, Summary: row.Summary,
			EvidenceIDs: row.EvidenceIDs, Attrs: row.Attrs,
		})
	}
	for _, row := range request.Delta.Claims {
		pkg.Claims = append(pkg.Claims, scanartifacts.ClaimRow{
			ID: row.ID, NodeID: row.NodeID, GraphClaimType: row.GraphClaimType, Summary: row.Summary,
			RequestedState: row.RequestedState, SupportingEvidenceIDs: row.SupportingEvidenceIDs,
			ContradictingEvidenceIDs: row.ContradictingEvidenceIDs, Verifications: row.Verifications, Attrs: row.Attrs,
		})
	}
	compilerPkg := cloneScanPackage(pkg)
	originalNodes := map[string]bool{}
	for _, row := range compilerPkg.Nodes {
		originalNodes[row.ID] = true
	}
	originalEvidence := map[string]bool{}
	for _, row := range compilerPkg.Evidence {
		originalEvidence[row.ID] = true
	}
	for i := range compilerPkg.Evidence {
		if compilerPkg.Evidence[i].SourceKind != "file" {
			compilerPkg.Evidence[i].SourcePath = ""
		}
	}
	for id := range existingNodeIDs {
		if id != "" && !originalNodes[id] {
			compilerPkg.Nodes = append(compilerPkg.Nodes, scanartifacts.NodeRow{ID: id, Type: "existing_reference", Title: id, Confidence: "verified"})
		}
	}
	for id := range existingEvidenceIDs {
		if id != "" && !originalEvidence[id] {
			compilerPkg.Evidence = append(compilerPkg.Evidence, scanartifacts.EvidenceRow{ID: id, SourceKind: "existing_reference", SourcePath: "", Extractor: "scoped-registration-active-reference"})
		}
	}
	compiled, result := compiler.Compile(compiler.AdaptLegacy(compilerPkg))
	compiled.Package.Nodes = filterExistingReferenceNodes(compiled.Package.Nodes, originalNodes)
	compiled.Package.Evidence = filterExistingReferenceEvidence(compiled.Package.Evidence, originalEvidence)
	return compiledPackage{Package: compiled.Package, Result: result}, nil
}

func cloneAnyMap(input map[string]any) map[string]any {
	out := make(map[string]any, len(input)+1)
	for key, value := range input {
		out[key] = value
	}
	return out
}

func cloneScanPackage(pkg scanartifacts.Package) scanartifacts.Package {
	return scanartifacts.Package{
		Evidence:     append([]scanartifacts.EvidenceRow(nil), pkg.Evidence...),
		Nodes:        append([]scanartifacts.NodeRow(nil), pkg.Nodes...),
		Edges:        append([]scanartifacts.EdgeRow(nil), pkg.Edges...),
		Observations: append([]scanartifacts.ObservationRow(nil), pkg.Observations...),
		Claims:       append([]scanartifacts.ClaimRow(nil), pkg.Claims...),
	}
}

func filterExistingReferenceNodes(rows []scanartifacts.NodeRow, original map[string]bool) []scanartifacts.NodeRow {
	out := rows[:0]
	for _, row := range rows {
		if original[row.ID] || row.Type != "existing_reference" {
			out = append(out, row)
		}
	}
	return out
}

func filterExistingReferenceEvidence(rows []scanartifacts.EvidenceRow, original map[string]bool) []scanartifacts.EvidenceRow {
	out := rows[:0]
	for _, row := range rows {
		if original[row.ID] || row.SourceKind != "existing_reference" {
			out = append(out, row)
		}
	}
	return out
}

func activeRegistrationIDs(ctx context.Context, db *sql.DB, generationID, table string) (map[string]bool, error) {
	if table != "nodes" && table != "evidence" {
		return nil, fmt.Errorf("unsupported scoped registration active id table %s", table)
	}
	rows, err := db.QueryContext(ctx, `SELECT id FROM `+table+` WHERE generation_id = ?`, generationID)
	if err != nil {
		return nil, fmt.Errorf("read active scoped registration %s ids: %w", table, err)
	}
	defer rows.Close()
	out := map[string]bool{}
	for rows.Next() {
		var id string
		if err := rows.Scan(&id); err != nil {
			return nil, fmt.Errorf("scan active scoped registration %s id: %w", table, err)
		}
		out[id] = true
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate active scoped registration %s ids: %w", table, err)
	}
	return out, nil
}

func validateRequest(root string, request Request) error {
	switch strings.TrimSpace(request.Proof.Kind) {
	case "closeout_binding":
		if strings.TrimSpace(request.Proof.BindingID) == "" || strings.TrimSpace(request.Proof.Workflow) == "" || strings.TrimSpace(request.Proof.Scope) == "" {
			return fmt.Errorf("closeout_binding proof requires binding_id, workflow, and scope")
		}
	case "do_native":
		if strings.TrimSpace(request.Proof.DoRef) == "" {
			return fmt.Errorf("do_native proof requires do_ref")
		}
	default:
		return fmt.Errorf("unsupported proof.kind %q", request.Proof.Kind)
	}
	state := strings.TrimSpace(request.Result.State)
	if state != "registered" && state != "partial" {
		return fmt.Errorf("result.state must be registered or partial")
	}
	if strings.TrimSpace(request.Result.Reason) == "" {
		return fmt.Errorf("result.reason is required")
	}
	ids := map[string]string{}
	for _, hash := range request.Source.SourceHashes {
		if strings.TrimSpace(hash.Path) == "" || !isSHA256(hash.SHA256) {
			return fmt.Errorf("source hashes require path and sha256")
		}
		if _, err := containedProjectPath(root, hash.Path); err != nil {
			return err
		}
	}
	for _, row := range request.Delta.Evidence {
		if err := noteID(ids, "evidence", row.ID); err != nil {
			return err
		}
	}
	for _, row := range request.Delta.Nodes {
		if err := noteID(ids, "node", row.ID); err != nil {
			return err
		}
	}
	for _, row := range request.Delta.Edges {
		if err := noteID(ids, "edge", row.ID); err != nil {
			return err
		}
	}
	for _, row := range request.Delta.Claims {
		if err := noteID(ids, "claim", row.ID); err != nil {
			return err
		}
	}
	return nil
}

func loadNativeProof(root string, proof ProofBinding) (nativeProof, error) {
	switch strings.TrimSpace(proof.Kind) {
	case "closeout_binding":
		id := strings.TrimSpace(proof.BindingID)
		if !strings.HasPrefix(id, "cb-") || strings.ContainsAny(id, `/\`) {
			return nativeProof{}, fmt.Errorf("invalid closeout binding id")
		}
		raw, err := os.ReadFile(filepath.Join(root, ".specify", "runtime", "receipts", "cognition-bindings", id+".json"))
		if err != nil {
			return nativeProof{}, fmt.Errorf("read closeout binding proof %s: %w", id, err)
		}
		var binding struct {
			Schema     string            `json:"schema"`
			ID         string            `json:"binding_id"`
			AttemptID  string            `json:"attempt_id"`
			Workflow   string            `json:"workflow"`
			Scope      string            `json:"scope"`
			WorkID     string            `json:"work_id"`
			Source     map[string]string `json:"source"`
			OwnedDelta []string          `json:"owned_delta"`
			SealedAt   string            `json:"sealed_at"`
			Digest     string            `json:"sha256"`
		}
		if err := json.Unmarshal(raw, &binding); err != nil {
			return nativeProof{}, fmt.Errorf("decode closeout binding proof: %w", err)
		}
		if binding.ID != id || binding.Workflow != proof.Workflow || binding.Scope != proof.Scope || strings.TrimSpace(binding.SealedAt) == "" {
			return nativeProof{}, fmt.Errorf("closeout binding proof is not a sealed exact workflow/scope match")
		}
		return nativeProof{
			Kind: "closeout_binding", BindingID: binding.ID, Workflow: binding.Workflow, Scope: binding.Scope,
			WorkID: binding.WorkID, AttemptID: binding.AttemptID, Source: binding.Source, OwnedDelta: binding.OwnedDelta, Digest: binding.Digest,
		}, nil
	case "do_native":
		ref := normalizePath(proof.DoRef)
		if !strings.HasPrefix(ref, ".specify/do/sessions/") {
			return nativeProof{}, fmt.Errorf("do_native proof requires an exact .specify/do/sessions/<id> scope ref")
		}
		if _, err := containedProjectPath(root, ref); err != nil {
			return nativeProof{}, err
		}
		return nativeProof{Kind: "do_native", Workflow: "sp-do", Source: map[string]string{ref: "runtime-owner:do_current_cognition_binding"}, Digest: stablePart("do-native:" + ref)}, nil
	default:
		return nativeProof{}, fmt.Errorf("unsupported proof.kind %q", proof.Kind)
	}
}

func verifyProofSource(root string, proof nativeProof) error {
	if len(proof.Source) == 0 {
		return fmt.Errorf("native proof has no source snapshot")
	}
	for ref, digest := range proof.Source {
		if !strings.HasPrefix(digest, "file:") {
			continue
		}
		parts := strings.Split(digest, ":")
		if len(parts) < 2 || !isSHA256(parts[1]) {
			continue
		}
		path, err := containedProjectPath(root, ref)
		if err != nil {
			return err
		}
		data, err := os.ReadFile(path)
		if err != nil {
			return fmt.Errorf("read proof source %s: %w", ref, err)
		}
		if got := sha256Hex(data); got != strings.ToLower(parts[1]) {
			return fmt.Errorf("proof source hash mismatch for %s: got %s want %s", ref, got, strings.ToLower(parts[1]))
		}
	}
	return nil
}

type evidenceCoverage struct {
	Debt              []string
	UncoveredEvidence map[string]string
}

func evidenceCoverageAgainstProof(root string, proof ProofBasis, request Request) (evidenceCoverage, error) {
	coverage := evidenceCoverage{UncoveredEvidence: map[string]string{}}
	for _, evidence := range request.Delta.Evidence {
		if strings.TrimSpace(evidence.SourceKind) != "file" {
			continue
		}
		id := strings.TrimSpace(evidence.ID)
		path := normalizePath(evidence.SourcePath)
		if path == "" {
			coverage = coverage.withDebt(id, "missing_source_path")
			continue
		}
		proofValue := strings.TrimSpace(proof.Source[path])
		parts := strings.Split(proofValue, ":")
		if proofValue == "" || len(parts) < 2 || parts[0] != "file" || !isSHA256(parts[1]) {
			coverage = coverage.withDebt(id, "native_source_uncovered:"+path)
			continue
		}
		resolved, err := containedProjectPath(root, path)
		if err != nil {
			return coverage, err
		}
		data, err := os.ReadFile(resolved)
		if err != nil {
			return coverage, fmt.Errorf("read evidence source %s: %w", path, err)
		}
		current := sha256Hex(data)
		want := strings.ToLower(parts[1])
		if current != want {
			return coverage, fmt.Errorf("evidence source %s drifted from native proof: got %s want %s", path, current, want)
		}
		contentHash := strings.ToLower(strings.TrimPrefix(strings.TrimSpace(evidence.ContentHash), "sha256:"))
		if contentHash == "" || !isSHA256(contentHash) {
			coverage = coverage.withDebt(id, "content_hash_missing_or_invalid:"+path)
			continue
		}
		if contentHash != want {
			coverage = coverage.withDebt(id, "content_hash_mismatch:"+path)
			continue
		}
	}
	if len(coverage.UncoveredEvidence) == 0 {
		return coverage, nil
	}
	for _, row := range request.Delta.Claims {
		for _, evidenceID := range append(append([]string{}, row.SupportingEvidenceIDs...), row.ContradictingEvidenceIDs...) {
			if reason := coverage.UncoveredEvidence[strings.TrimSpace(evidenceID)]; reason != "" {
				coverage.Debt = append(coverage.Debt, "claim:"+strings.TrimSpace(row.ID)+":unverified_source_evidence:"+strings.TrimSpace(evidenceID)+":"+reason)
			}
		}
	}
	coverage.Debt = uniqueSorted(coverage.Debt)
	return coverage, nil
}

func nativeSourceEvidenceDebtError(coverage evidenceCoverage) error {
	joined := strings.Join(coverage.Debt, ", ")
	switch {
	case strings.Contains(joined, "content_hash_mismatch"):
		return fmt.Errorf("evidence content_hash does not match native proof: %s", joined)
	case strings.Contains(joined, "native_source_uncovered") || strings.Contains(joined, "missing_source_path"):
		return fmt.Errorf("source evidence is not covered by native source proof: %s", joined)
	case strings.Contains(joined, "content_hash_missing_or_invalid"):
		return fmt.Errorf("evidence has no verifiable sha256 content_hash for native source proof: %s", joined)
	default:
		return fmt.Errorf("scoped registration has unresolved native source evidence debt: %s", joined)
	}
}

func (coverage evidenceCoverage) withDebt(evidenceID, reason string) evidenceCoverage {
	evidenceID = strings.TrimSpace(evidenceID)
	reason = strings.TrimSpace(reason)
	if evidenceID == "" {
		evidenceID = "unknown"
	}
	if reason == "" {
		reason = "native_source_unverified"
	}
	coverage.UncoveredEvidence[evidenceID] = reason
	coverage.Debt = append(coverage.Debt, "evidence:"+evidenceID+":"+reason)
	return coverage
}

func provisionalizeUncoveredEvidence(request Request, badEvidence map[string]string) Request {
	if len(badEvidence) == 0 {
		return request
	}
	for i := range request.Delta.Nodes {
		if intersectsEvidence(request.Delta.Nodes[i].EvidenceIDs, badEvidence) {
			request.Delta.Nodes[i].Confidence = "partial"
			request.Delta.Nodes[i].Attrs = withScopedDebtAttr(request.Delta.Nodes[i].Attrs, badEvidence)
		}
	}
	for i := range request.Delta.Edges {
		if intersectsEvidence(request.Delta.Edges[i].EvidenceIDs, badEvidence) {
			request.Delta.Edges[i].Confidence = "partial"
			request.Delta.Edges[i].Attrs = withScopedDebtAttr(request.Delta.Edges[i].Attrs, badEvidence)
		}
	}
	for i := range request.Delta.Observations {
		if intersectsEvidence(request.Delta.Observations[i].EvidenceIDs, badEvidence) {
			request.Delta.Observations[i].Attrs = withScopedDebtAttr(request.Delta.Observations[i].Attrs, badEvidence)
		}
	}
	for i := range request.Delta.Claims {
		if intersectsEvidence(request.Delta.Claims[i].SupportingEvidenceIDs, badEvidence) || intersectsEvidence(request.Delta.Claims[i].ContradictingEvidenceIDs, badEvidence) {
			request.Delta.Claims[i].RequestedState = claim.StateCandidate
			request.Delta.Claims[i].SupportingEvidenceIDs = filterCoveredEvidence(request.Delta.Claims[i].SupportingEvidenceIDs, badEvidence)
			request.Delta.Claims[i].ContradictingEvidenceIDs = filterCoveredEvidence(request.Delta.Claims[i].ContradictingEvidenceIDs, badEvidence)
			request.Delta.Claims[i].Verifications = filterCoveredVerifications(request.Delta.Claims[i].Verifications, badEvidence)
			request.Delta.Claims[i].Attrs = withScopedDebtAttr(request.Delta.Claims[i].Attrs, badEvidence)
		}
	}
	return request
}

func intersectsEvidence(ids []string, badEvidence map[string]string) bool {
	for _, id := range ids {
		if badEvidence[strings.TrimSpace(id)] != "" {
			return true
		}
	}
	return false
}

func filterCoveredEvidence(ids []string, badEvidence map[string]string) []string {
	out := []string{}
	for _, id := range ids {
		if badEvidence[strings.TrimSpace(id)] == "" {
			out = append(out, id)
		}
	}
	return out
}

func filterCoveredVerifications(values []claim.Verification, badEvidence map[string]string) []claim.Verification {
	out := []claim.Verification{}
	for _, value := range values {
		if badEvidence[strings.TrimSpace(value.EvidenceID)] == "" {
			out = append(out, value)
		}
	}
	return out
}

func withScopedDebtAttr(attrs map[string]any, badEvidence map[string]string) map[string]any {
	if attrs == nil {
		attrs = map[string]any{}
	}
	copyAttrs := map[string]any{}
	for key, value := range attrs {
		copyAttrs[key] = value
	}
	copyAttrs["scoped_registration_evidence_debt"] = sortedStringKeys(badEvidence)
	return copyAttrs
}

func sortedStringKeys(values map[string]string) []string {
	out := make([]string, 0, len(values))
	for key := range values {
		if strings.TrimSpace(key) != "" {
			out = append(out, strings.TrimSpace(key))
		}
	}
	sort.Strings(out)
	return out
}

func proofCoversDelta(proof nativeProof, request Request) error {
	if proof.Kind == "do_native" {
		return nil
	}
	owned := map[string]bool{}
	for _, path := range proof.OwnedDelta {
		owned[normalizePath(path)] = true
	}
	for _, path := range changedPaths(request) {
		if path != "" && !owned[path] {
			return fmt.Errorf("native proof owned_delta does not cover changed path %s", path)
		}
	}
	return nil
}

func containedProjectPath(root, value string) (string, error) {
	value = filepath.Clean(filepath.FromSlash(strings.TrimSpace(value)))
	if value == "." || filepath.IsAbs(value) || strings.HasPrefix(value, ".."+string(filepath.Separator)) || value == ".." {
		return "", fmt.Errorf("path %q must be project-relative", value)
	}
	path := filepath.Join(root, value)
	resolved, err := filepath.Abs(path)
	if err != nil {
		return "", err
	}
	base, err := filepath.Abs(root)
	if err != nil {
		return "", err
	}
	rel, err := filepath.Rel(base, resolved)
	if err != nil || rel == ".." || strings.HasPrefix(rel, ".."+string(filepath.Separator)) || filepath.IsAbs(rel) {
		return "", fmt.Errorf("path %q escapes project root", value)
	}
	return resolved, nil
}

func noteID(ids map[string]string, category, id string) error {
	id = strings.TrimSpace(id)
	if id == "" {
		return fmt.Errorf("%s id is required", category)
	}
	if previous := ids[id]; previous != "" {
		return fmt.Errorf("id %s reused by %s and %s", id, previous, category)
	}
	ids[id] = category
	return nil
}

func replayRegistration(ctx context.Context, db *sql.DB, registrationID, generationID, packetSHA string) (Payload, bool, bool, store.ScopedRegistrationResult, error) {
	var attrsRaw string
	err := db.QueryRowContext(ctx, `SELECT attrs_json FROM updates WHERE id = ? AND generation_id = ?`, registrationID, generationID).Scan(&attrsRaw)
	if errors.Is(err, sql.ErrNoRows) {
		return Payload{}, false, false, store.ScopedRegistrationResult{}, nil
	}
	if err != nil {
		return Payload{}, false, false, store.ScopedRegistrationResult{}, fmt.Errorf("read scoped registration replay: %w", err)
	}
	attrs, err := decodeReplayAttrs(attrsRaw)
	if err != nil {
		return Payload{}, false, false, store.ScopedRegistrationResult{}, fmt.Errorf("decode scoped registration replay: %w", err)
	}
	if attrs.PacketSHA256 == "" {
		return Payload{}, false, false, store.ScopedRegistrationResult{}, nil
	}
	if attrs.PacketSHA256 != packetSHA {
		return Payload{}, false, false, store.ScopedRegistrationResult{}, fmt.Errorf("registration id %s already exists with a different packet sha256", registrationID)
	}
	attrs.Receipt.PacketSHA256 = packetSHA
	attrs.Receipt.ActiveGenerationID = generationID
	finalized := attrs.Receipt.Status == "ok" || attrs.Receipt.Status == "partial"
	if finalized && attrs.Receipt.Registered != nil && attrs.Receipt.Details != nil {
		return attrs.Receipt, true, true, attrs.ScopedRegistrationResult, nil
	}
	if attrs.ScopedRegistrationResult.ActiveGenerationID == "" {
		return Payload{}, true, false, store.ScopedRegistrationResult{}, fmt.Errorf("scoped registration %s committed without recoverable store result", registrationID)
	}
	return attrs.Receipt, true, false, attrs.ScopedRegistrationResult, nil
}

type replayAttrs struct {
	PacketSHA256             string
	Receipt                  Payload
	ScopedRegistrationResult store.ScopedRegistrationResult
}

func decodeReplayAttrs(attrsRaw string) (replayAttrs, error) {
	var attrs struct {
		PacketSHA256             string                         `json:"packet_sha256"`
		Receipt                  Payload                        `json:"receipt"`
		ScopedRegistrationResult store.ScopedRegistrationResult `json:"scoped_registration_result"`
		ScopedRegistration       struct {
			PacketSHA256             string                         `json:"packet_sha256"`
			Receipt                  Payload                        `json:"receipt"`
			ScopedRegistrationResult store.ScopedRegistrationResult `json:"scoped_registration_result"`
		} `json:"scoped_registration"`
	}
	decoder := json.NewDecoder(strings.NewReader(attrsRaw))
	decoder.UseNumber()
	if err := decoder.Decode(&attrs); err != nil {
		return replayAttrs{}, err
	}
	if attrs.PacketSHA256 != "" {
		return replayAttrs{PacketSHA256: attrs.PacketSHA256, Receipt: attrs.Receipt, ScopedRegistrationResult: attrs.ScopedRegistrationResult}, nil
	}
	return replayAttrs{PacketSHA256: attrs.ScopedRegistration.PacketSHA256, Receipt: attrs.ScopedRegistration.Receipt, ScopedRegistrationResult: attrs.ScopedRegistration.ScopedRegistrationResult}, nil
}

func emptyRegistered() map[string][]string {
	return map[string][]string{
		"evidence": []string{}, "nodes": []string{}, "edges": []string{}, "observations": []string{}, "claims": []string{}, "aliases": []string{}, "path_index": []string{},
	}
}

func changedPaths(request Request) []string {
	out := []string{}
	for _, change := range request.Delta.ChangedPaths {
		if path := normalizePath(change.Path); path != "" {
			out = append(out, path)
		}
		if path := normalizePath(change.OldPath); path != "" {
			out = append(out, path)
		}
	}
	for _, row := range request.Delta.PathIndex {
		if path := normalizePath(row.Path); path != "" {
			out = append(out, path)
		}
	}
	return uniqueSorted(out)
}

func registeredNodeIDs(values map[string][]string) []string {
	return uniqueSorted(values["nodes"])
}

func nextArgv(request Request, payload Payload) [][]string {
	out := [][]string{}
	for _, nodeID := range payload.Registered["nodes"] {
		out = append(out, []string{"specify-runtime", "cognition", "query", "--intent", "owner", "--query", nodeID, "--format", "json"})
	}
	for _, item := range append(append([]string{}, request.Delta.Obligations.Consumers...), request.Delta.Obligations.VerificationEntries...) {
		if strings.TrimSpace(item) != "" {
			out = append(out, []string{"specify-runtime", "cognition", "semantic-intake", "--input-json", "{\"raw_request\":" + jsonString(item) + "}", "--format", "json"})
		}
	}
	return out
}

func validationDebt(request Request) []string {
	debt := []string{}
	debt = append(debt, request.Delta.Obligations.Unknowns...)
	if !obligationFacetSatisfied(request, "owners", request.Delta.Obligations.Owners) {
		debt = append(debt, "owner_obligations_not_declared")
	}
	if !obligationFacetSatisfied(request, "consumers", request.Delta.Obligations.Consumers) {
		debt = append(debt, "consumer_obligations_not_declared")
	}
	if !obligationFacetSatisfied(request, "interfaces", request.Delta.Obligations.Interfaces) {
		debt = append(debt, "interface_obligations_not_declared")
	}
	if !obligationFacetSatisfied(request, "state_contracts", request.Delta.Obligations.StateContracts) {
		debt = append(debt, "state_contract_obligations_not_declared")
	}
	if !obligationFacetSatisfied(request, "generated_chain", request.Delta.Obligations.GeneratedChain) {
		debt = append(debt, "generated_chain_obligations_not_declared")
	}
	if !obligationFacetSatisfied(request, "verification_entries", request.Delta.Obligations.VerificationEntries) {
		debt = append(debt, "verification_entries_not_declared")
	}
	if len(request.Delta.Retirements) > 0 || len(request.Delta.Obligations.InvalidatedAliases) > 0 {
		if len(storeNegativeProbes(request)) == 0 {
			debt = append(debt, "invalidated_alias_or_removed_path_negative_evidence_not_declared")
		}
	}
	if strings.TrimSpace(request.Result.State) != "registered" {
		debt = append(debt, "result_state_partial")
	}
	return uniqueSorted(debt)
}

func obligationFacetSatisfied(request Request, facet string, values []string) bool {
	if len(values) > 0 {
		return true
	}
	for _, unknown := range request.Delta.Obligations.Unknowns {
		normalized := strings.ToLower(strings.TrimSpace(unknown))
		if normalized == facet+":not_applicable" || normalized == "not_applicable:"+facet || normalized == facet+":unresolved" || normalized == "unresolved:"+facet {
			return true
		}
	}
	return false
}

func jsonString(value string) string {
	data, _ := json.Marshal(value)
	return string(data)
}

func normalizePath(value string) string {
	value = filepath.ToSlash(strings.TrimSpace(value))
	for strings.HasPrefix(value, "./") {
		value = strings.TrimPrefix(value, "./")
	}
	return strings.TrimRight(value, "/")
}

func normalizeAlias(value string) string {
	value = strings.ToLower(strings.TrimSpace(value))
	fields := strings.FieldsFunc(value, func(r rune) bool {
		return !(r == '_' || r == '-' || r == '/' || r == '.' || (r >= '0' && r <= '9') || (r >= 'a' && r <= 'z'))
	})
	return strings.Join(fields, " ")
}

func defaultString(value, fallback string) string {
	value = strings.TrimSpace(value)
	if value == "" {
		return fallback
	}
	return value
}

func isSHA256(value string) bool {
	value = strings.ToLower(strings.TrimSpace(value))
	if len(value) != 64 {
		return false
	}
	_, err := hex.DecodeString(value)
	return err == nil
}

func sha256Hex(data []byte) string {
	sum := sha256.Sum256(data)
	return hex.EncodeToString(sum[:])
}

func stablePart(value string) string {
	value = strings.ToLower(strings.TrimSpace(value))
	replacer := strings.NewReplacer("/", "-", "\\", "-", " ", "-", ".", "-", ":", "-")
	value = strings.Trim(replacer.Replace(value), "-")
	if value == "" {
		return "unknown"
	}
	if len(value) > 80 {
		return value[:48] + "-" + sha256Hex([]byte(value))[:16]
	}
	return value
}

func uniqueSorted(values []string) []string {
	seen := map[string]bool{}
	out := []string{}
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
