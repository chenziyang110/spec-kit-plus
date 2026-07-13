// Package reconcile validates bounded live repository evidence and feeds it
// back into the active project-cognition graph generation.
package reconcile

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"time"

	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/claim"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/ignore"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/query"
	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/store"
)

const CurrentContractVersion = 1

var sha256Pattern = regexp.MustCompile(`^sha256:[0-9a-f]{64}$`)

type Packet struct {
	ContractVersion      int    `json:"claim_reconciliation_contract_version"`
	ExpectedGenerationID string `json:"expected_generation_id"`
	Workflow             string `json:"workflow"`
	ObservedAt           string `json:"observed_at"`
	Items                []Item `json:"items"`
}

type Item struct {
	ClaimID       string        `json:"claim_id"`
	ExpectedState claim.State   `json:"expected_state"`
	Reason        string        `json:"reason"`
	Evidence      []Evidence    `json:"evidence"`
	Verification  *Verification `json:"verification,omitempty"`
}

type Evidence struct {
	SourceKind          string `json:"source_kind"`
	SourcePath          string `json:"source_path"`
	Span                string `json:"span"`
	Role                string `json:"role"`
	ExpectedContentHash string `json:"expected_content_hash"`
}

type Verification struct {
	Result  claim.VerificationResult `json:"result"`
	Command string                   `json:"command"`
}

type Payload struct {
	Status             string                            `json:"status"`
	ResultState        string                            `json:"result_state"`
	ContractVersion    int                               `json:"claim_reconciliation_contract_version"`
	ReconciliationID   string                            `json:"reconciliation_id"`
	ActiveGenerationID string                            `json:"active_generation_id"`
	Replayed           bool                              `json:"replayed"`
	ReconciledClaims   []store.ClaimReconciliationRecord `json:"reconciled_claims"`
	RecommendedAction  string                            `json:"recommended_next_action"`
	EpistemicContract  query.EpistemicContract           `json:"epistemic_contract"`
}

type ErrorPayload struct {
	Status            string   `json:"status"`
	ResultState       string   `json:"result_state"`
	ContractVersion   int      `json:"claim_reconciliation_contract_version"`
	ErrorCode         string   `json:"error_code"`
	Errors            []string `json:"errors"`
	RecommendedAction string   `json:"recommended_next_action"`
}

func ParsePacket(data []byte) (Packet, error) {
	decoder := json.NewDecoder(bytes.NewReader(data))
	decoder.DisallowUnknownFields()
	var packet Packet
	if err := decoder.Decode(&packet); err != nil {
		return Packet{}, fmt.Errorf("decode claim reconciliation packet: %w", err)
	}
	var trailing any
	if err := decoder.Decode(&trailing); !errors.Is(err, io.EOF) {
		if err == nil {
			return Packet{}, fmt.Errorf("decode claim reconciliation packet: multiple JSON values are not allowed")
		}
		return Packet{}, fmt.Errorf("decode claim reconciliation packet trailing data: %w", err)
	}
	return normalizeAndValidatePacket(packet)
}

func Run(paths rt.Paths, packet Packet) (Payload, error) {
	packet, err := normalizeAndValidatePacket(packet)
	if err != nil {
		return Payload{}, err
	}
	preparedEvidence, err := prepareEvidence(paths, packet)
	if err != nil {
		return Payload{}, err
	}
	packetJSON, err := json.Marshal(packet)
	if err != nil {
		return Payload{}, fmt.Errorf("encode canonical claim reconciliation packet: %w", err)
	}
	packetDigest := digestHex(packetJSON)
	reconciliationID := "claim-reconciliation:" + packetDigest[:24]
	commitSHA, err := rt.GitHead(paths.Root)
	if err != nil || strings.TrimSpace(commitSHA) == "" {
		commitSHA = "working-tree-unavailable"
	}

	batch := store.ClaimReconciliationBatch{
		ID: reconciliationID, PacketHash: "sha256:" + packetDigest, GenerationID: packet.ExpectedGenerationID,
		Workflow: packet.Workflow, ObservedAt: packet.ObservedAt, CommitSHA: commitSHA,
		Items: make([]store.ClaimReconciliationItem, 0, len(packet.Items)),
	}
	for itemIndex, item := range packet.Items {
		storeItem := store.ClaimReconciliationItem{
			ClaimID: item.ClaimID, ExpectedState: item.ExpectedState, Reason: item.Reason,
			Evidence: make([]store.ClaimReconciliationEvidence, 0, len(item.Evidence)),
		}
		for evidenceIndex, evidence := range item.Evidence {
			identity := fmt.Sprintf("%s\x00%s\x00%d\x00%d\x00%s\x00%s\x00%s", reconciliationID, item.ClaimID, itemIndex, evidenceIndex, evidence.SourcePath, evidence.Span, evidence.Role)
			storeItem.Evidence = append(storeItem.Evidence, store.ClaimReconciliationEvidence{
				ID: "E-reconcile-" + digestHex([]byte(identity))[:24], SourceKind: evidence.SourceKind,
				SourcePath: evidence.SourcePath, Span: evidence.Span, ContentHash: preparedEvidence[itemIndex][evidenceIndex], Role: evidence.Role,
			})
		}
		if item.Verification != nil {
			storeItem.Verification = &store.ClaimReconciliationVerification{
				ID:     "V-reconcile-" + digestHex([]byte(reconciliationID + "\x00" + item.ClaimID))[:24],
				Result: item.Verification.Result, Command: item.Verification.Command,
			}
		}
		batch.Items = append(batch.Items, storeItem)
	}

	st, err := store.Open(paths)
	if err != nil {
		return Payload{}, fmt.Errorf("open graph store for claim reconciliation: %w", err)
	}
	defer st.Close()
	result, err := st.ApplyClaimReconciliation(context.Background(), batch)
	if err != nil {
		return Payload{}, err
	}
	action := "rerun_compass_once"
	if result.ResultState != "ready" {
		action = "collect_claim_specific_live_evidence"
	}
	return Payload{
		Status: "ok", ResultState: result.ResultState, ContractVersion: CurrentContractVersion,
		ReconciliationID: result.ID, ActiveGenerationID: result.ActiveGenerationID, Replayed: result.Replayed,
		ReconciledClaims: result.Claims, RecommendedAction: action, EpistemicContract: query.NewEpistemicContract(),
	}, nil
}

func BlockedPayload(err error) ErrorPayload {
	message := "claim reconciliation failed"
	if err != nil {
		message = err.Error()
	}
	return ErrorPayload{
		Status: "error", ResultState: "blocked", ContractVersion: CurrentContractVersion,
		ErrorCode: "invalid_claim_reconciliation", Errors: []string{message}, RecommendedAction: "repair_reconciliation_input",
	}
}

func normalizeAndValidatePacket(packet Packet) (Packet, error) {
	packet = clonePacket(packet)
	packet.ExpectedGenerationID = strings.TrimSpace(packet.ExpectedGenerationID)
	packet.Workflow = strings.TrimSpace(packet.Workflow)
	packet.ObservedAt = strings.TrimSpace(packet.ObservedAt)
	if packet.ContractVersion != CurrentContractVersion {
		return Packet{}, fmt.Errorf("claim_reconciliation_contract_version %d is unsupported; expected %d", packet.ContractVersion, CurrentContractVersion)
	}
	if packet.ExpectedGenerationID == "" || packet.Workflow == "" || packet.ObservedAt == "" {
		return Packet{}, fmt.Errorf("expected_generation_id, workflow, and observed_at are required")
	}
	if _, err := time.Parse(time.RFC3339, packet.ObservedAt); err != nil {
		return Packet{}, fmt.Errorf("observed_at must be RFC3339: %w", err)
	}
	if len(packet.Items) == 0 {
		return Packet{}, fmt.Errorf("claim reconciliation requires at least one item")
	}
	seenClaims := map[string]bool{}
	for itemIndex := range packet.Items {
		item := &packet.Items[itemIndex]
		item.ClaimID = strings.TrimSpace(item.ClaimID)
		item.Reason = strings.TrimSpace(item.Reason)
		if item.ClaimID == "" || item.Reason == "" || !validClaimState(item.ExpectedState) {
			return Packet{}, fmt.Errorf("item %d requires claim_id, valid expected_state, and reason", itemIndex)
		}
		if seenClaims[item.ClaimID] {
			return Packet{}, fmt.Errorf("duplicate claim_id %q", item.ClaimID)
		}
		seenClaims[item.ClaimID] = true
		if len(item.Evidence) == 0 && item.Verification == nil {
			return Packet{}, fmt.Errorf("claim %q requires evidence or verification", item.ClaimID)
		}
		hasSupporting := false
		hasContradicting := false
		for evidenceIndex := range item.Evidence {
			evidence := &item.Evidence[evidenceIndex]
			evidence.SourceKind = strings.TrimSpace(evidence.SourceKind)
			normalizedPath, err := normalizeRepositoryRelativePath(evidence.SourcePath)
			if err != nil {
				return Packet{}, fmt.Errorf("claim %q evidence %d source_path: %w", item.ClaimID, evidenceIndex, err)
			}
			evidence.SourcePath = normalizedPath
			evidence.Span = strings.TrimSpace(evidence.Span)
			evidence.Role = strings.TrimSpace(evidence.Role)
			evidence.ExpectedContentHash = strings.ToLower(strings.TrimSpace(evidence.ExpectedContentHash))
			if !validSourceKind(evidence.SourceKind) || evidence.SourcePath == "" || evidence.Span == "" || !sha256Pattern.MatchString(evidence.ExpectedContentHash) {
				return Packet{}, fmt.Errorf("claim %q evidence %d requires valid source_kind, source_path, span, and sha256 content hash", item.ClaimID, evidenceIndex)
			}
			switch evidence.Role {
			case "supporting":
				hasSupporting = true
			case "contradicting":
				hasContradicting = true
			default:
				return Packet{}, fmt.Errorf("claim %q evidence %d role %q is invalid", item.ClaimID, evidenceIndex, evidence.Role)
			}
		}
		if item.Verification != nil {
			item.Verification.Command = strings.TrimSpace(item.Verification.Command)
			if item.Verification.Command == "" || !validVerificationResult(item.Verification.Result) {
				return Packet{}, fmt.Errorf("claim %q verification requires a valid result and command", item.ClaimID)
			}
			if item.Verification.Result == claim.VerificationPassed && !hasSupporting {
				return Packet{}, fmt.Errorf("claim %q passed verification requires supporting evidence", item.ClaimID)
			}
			if item.Verification.Result == claim.VerificationContradicted && !hasContradicting {
				return Packet{}, fmt.Errorf("claim %q contradicted verification requires contradicting evidence", item.ClaimID)
			}
		}
		sort.Slice(item.Evidence, func(i, j int) bool {
			left := item.Evidence[i]
			right := item.Evidence[j]
			return left.SourcePath+"\x00"+left.Span+"\x00"+left.Role+"\x00"+left.ExpectedContentHash < right.SourcePath+"\x00"+right.Span+"\x00"+right.Role+"\x00"+right.ExpectedContentHash
		})
	}
	sort.Slice(packet.Items, func(i, j int) bool { return packet.Items[i].ClaimID < packet.Items[j].ClaimID })
	return packet, nil
}

func prepareEvidence(paths rt.Paths, packet Packet) ([][]string, error) {
	matcher := ignore.Load(paths.Root)
	root, err := filepath.Abs(paths.Root)
	if err != nil {
		return nil, fmt.Errorf("resolve project root for claim reconciliation: %w", err)
	}
	out := make([][]string, len(packet.Items))
	for itemIndex, item := range packet.Items {
		out[itemIndex] = make([]string, len(item.Evidence))
		for evidenceIndex, evidence := range item.Evidence {
			relative, fullPath, err := safeEvidencePath(root, evidence.SourcePath)
			if err != nil {
				return nil, fmt.Errorf("claim %q evidence path: %w", item.ClaimID, err)
			}
			if matcher.Ignored(relative) {
				return nil, fmt.Errorf("claim %q evidence path %q is excluded by project cognition ignore rules", item.ClaimID, relative)
			}
			info, err := os.Stat(fullPath)
			if err != nil {
				return nil, fmt.Errorf("read claim %q evidence path %q: %w", item.ClaimID, relative, err)
			}
			if !info.Mode().IsRegular() {
				return nil, fmt.Errorf("claim %q evidence path %q is not a regular file", item.ClaimID, relative)
			}
			data, err := os.ReadFile(fullPath)
			if err != nil {
				return nil, fmt.Errorf("read claim %q evidence path %q: %w", item.ClaimID, relative, err)
			}
			actual := "sha256:" + digestHex(data)
			if actual != evidence.ExpectedContentHash {
				return nil, fmt.Errorf("claim %q evidence hash mismatch for %q: expected %s, observed %s", item.ClaimID, relative, evidence.ExpectedContentHash, actual)
			}
			out[itemIndex][evidenceIndex] = actual
		}
	}
	return out, nil
}

func safeEvidencePath(root, candidate string) (string, string, error) {
	clean, err := normalizeRepositoryRelativePath(candidate)
	if err != nil {
		return "", "", err
	}
	full := filepath.Join(root, filepath.FromSlash(clean))
	resolved, err := filepath.EvalSymlinks(full)
	if err != nil {
		return "", "", err
	}
	relative, err := filepath.Rel(root, resolved)
	if err != nil {
		return "", "", err
	}
	relative = filepath.ToSlash(relative)
	if relative == ".." || strings.HasPrefix(relative, "../") || filepath.IsAbs(relative) {
		return "", "", fmt.Errorf("%q resolves outside the repository", candidate)
	}
	return clean, resolved, nil
}

func normalizeRepositoryRelativePath(candidate string) (string, error) {
	candidate = strings.ReplaceAll(strings.TrimSpace(candidate), `\`, "/")
	if candidate == "" || path.IsAbs(candidate) || strings.HasPrefix(candidate, "/") || (len(candidate) >= 2 && candidate[1] == ':') {
		return "", fmt.Errorf("%q must be repository-relative", candidate)
	}
	clean := path.Clean(candidate)
	if clean == "." || clean == ".." || strings.HasPrefix(clean, "../") {
		return "", fmt.Errorf("%q escapes the repository", candidate)
	}
	return clean, nil
}

func clonePacket(packet Packet) Packet {
	packet.Items = append([]Item(nil), packet.Items...)
	for index := range packet.Items {
		packet.Items[index].Evidence = append([]Evidence(nil), packet.Items[index].Evidence...)
		if packet.Items[index].Verification != nil {
			verification := *packet.Items[index].Verification
			packet.Items[index].Verification = &verification
		}
	}
	return packet
}

func validClaimState(state claim.State) bool {
	switch state {
	case claim.StateCandidate, claim.StateSupported, claim.StateVerified, claim.StateContradicted, claim.StateStale:
		return true
	default:
		return false
	}
}

func validSourceKind(kind string) bool {
	switch kind {
	case "source", "test", "config", "doc":
		return true
	default:
		return false
	}
}

func validVerificationResult(result claim.VerificationResult) bool {
	switch result {
	case claim.VerificationPassed, claim.VerificationFailed, claim.VerificationBlocked, claim.VerificationInconclusive, claim.VerificationContradicted:
		return true
	default:
		return false
	}
}

func digestHex(data []byte) string {
	digest := sha256.Sum256(data)
	return hex.EncodeToString(digest[:])
}
