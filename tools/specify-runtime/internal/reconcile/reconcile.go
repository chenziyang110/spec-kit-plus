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
	"path"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"time"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/claim"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/ignore"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/query"
	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/store"
)

const CurrentContractVersion = 2

const preparedPacketTTL = 5 * time.Minute

const (
	maxReconciliationItems       = 25
	maxEvidencePerClaim          = 25
	maxEvidenceFileBytes   int64 = 8 << 20
	maxEvidenceTotalBytes  int64 = 32 << 20
)

var sha256Pattern = regexp.MustCompile(`^sha256:[0-9a-f]{64}$`)
var boundedSpanPattern = regexp.MustCompile(`^(?:L[1-9][0-9]*(?:-L?[1-9][0-9]*)?|[1-9][0-9]*:[1-9][0-9]*-[1-9][0-9]*:[1-9][0-9]*)$`)

type Packet struct {
	ContractVersion      int                `json:"claim_reconciliation_contract_version"`
	PrepareID            string             `json:"prepare_id"`
	PacketHash           string             `json:"packet_hash"`
	ExpectedGenerationID string             `json:"expected_generation_id"`
	Workflow             string             `json:"workflow"`
	ObservedAt           string             `json:"observed_at"`
	ExpiresAt            string             `json:"expires_at"`
	RepositorySnapshot   RepositorySnapshot `json:"repository_snapshot"`
	Items                []Item             `json:"items"`
}

type RepositorySnapshot struct {
	Kind      string `json:"kind"`
	CommitSHA string `json:"commit_sha,omitempty"`
}

type Item struct {
	ClaimID          string        `json:"claim_id"`
	ExpectedState    claim.State   `json:"expected_state"`
	ExpectedRevision int64         `json:"expected_revision"`
	Reason           string        `json:"reason"`
	Evidence         []Evidence    `json:"evidence"`
	Verification     *Verification `json:"verification,omitempty"`
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
	return runAt(paths, packet, time.Now().UTC())
}

func runAt(paths rt.Paths, packet Packet, now time.Time) (Payload, error) {
	packet, err := normalizeAndValidatePacket(packet)
	if err != nil {
		return Payload{}, err
	}
	packetDigest := strings.TrimPrefix(packet.PacketHash, "sha256:")
	reconciliationID := "claim-reconciliation:" + packetDigest[:24]
	st, err := store.OpenExisting(paths)
	if err != nil {
		return Payload{}, fmt.Errorf("open graph store for claim reconciliation: %w", err)
	}
	defer st.Close()
	if replayed, found, err := st.ReplayClaimReconciliation(context.Background(), reconciliationID, packet.ExpectedGenerationID, packet.PacketHash); err != nil {
		return Payload{}, err
	} else if found {
		return payloadFromStoreResult(replayed), nil
	}
	if err := validateApplyWindow(packet, now); err != nil {
		return Payload{}, err
	}
	preparedEvidence, err := prepareEvidence(paths, packet)
	if err != nil {
		return Payload{}, err
	}

	batch := store.ClaimReconciliationBatch{
		ID: reconciliationID, PacketHash: packet.PacketHash, GenerationID: packet.ExpectedGenerationID,
		Workflow: packet.Workflow, ObservedAt: packet.ObservedAt, CommitSHA: packet.RepositorySnapshot.CommitSHA,
		Items: make([]store.ClaimReconciliationItem, 0, len(packet.Items)),
	}
	for itemIndex, item := range packet.Items {
		storeItem := store.ClaimReconciliationItem{
			ClaimID: item.ClaimID, ExpectedState: item.ExpectedState, ExpectedRevision: item.ExpectedRevision, Reason: item.Reason,
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

	result, err := st.ApplyClaimReconciliation(context.Background(), batch)
	if err != nil {
		return Payload{}, err
	}
	return payloadFromStoreResult(result), nil
}

func payloadFromStoreResult(result store.ClaimReconciliationResult) Payload {
	action := "rerun_compass_once"
	if result.ResultState != "ready" {
		action = "collect_claim_specific_live_evidence"
	}
	return Payload{
		Status: "ok", ResultState: result.ResultState, ContractVersion: CurrentContractVersion,
		ReconciliationID: result.ID, ActiveGenerationID: result.ActiveGenerationID, Replayed: result.Replayed,
		ReconciledClaims: result.Claims, RecommendedAction: action, EpistemicContract: query.NewEpistemicContract(),
	}
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
	packet.PrepareID = strings.TrimSpace(packet.PrepareID)
	packet.PacketHash = strings.ToLower(strings.TrimSpace(packet.PacketHash))
	packet.ExpectedGenerationID = strings.TrimSpace(packet.ExpectedGenerationID)
	packet.Workflow = strings.TrimSpace(packet.Workflow)
	packet.ObservedAt = strings.TrimSpace(packet.ObservedAt)
	packet.ExpiresAt = strings.TrimSpace(packet.ExpiresAt)
	packet.RepositorySnapshot.Kind = strings.TrimSpace(packet.RepositorySnapshot.Kind)
	packet.RepositorySnapshot.CommitSHA = strings.TrimSpace(packet.RepositorySnapshot.CommitSHA)
	if packet.ContractVersion != CurrentContractVersion {
		return Packet{}, fmt.Errorf("claim_reconciliation_contract_version %d is unsupported; expected %d", packet.ContractVersion, CurrentContractVersion)
	}
	if !strings.HasPrefix(packet.PrepareID, "claim-reconciliation-prepare:") || len(strings.TrimPrefix(packet.PrepareID, "claim-reconciliation-prepare:")) != 24 || !sha256Pattern.MatchString(packet.PacketHash) {
		return Packet{}, fmt.Errorf("prepare_id and sha256 packet_hash are required")
	}
	if packet.ExpectedGenerationID == "" || packet.Workflow == "" || packet.ObservedAt == "" || packet.ExpiresAt == "" {
		return Packet{}, fmt.Errorf("expected_generation_id, workflow, observed_at, and expires_at are required")
	}
	observedAt, err := time.Parse(time.RFC3339, packet.ObservedAt)
	if err != nil {
		return Packet{}, fmt.Errorf("observed_at must be RFC3339: %w", err)
	}
	expiresAt, err := time.Parse(time.RFC3339, packet.ExpiresAt)
	if err != nil {
		return Packet{}, fmt.Errorf("expires_at must be RFC3339: %w", err)
	}
	observedAt = observedAt.UTC()
	expiresAt = expiresAt.UTC()
	packet.ObservedAt = observedAt.Format(time.RFC3339Nano)
	packet.ExpiresAt = expiresAt.Format(time.RFC3339Nano)
	if expiresAt.Sub(observedAt) != preparedPacketTTL {
		return Packet{}, fmt.Errorf("expires_at must be exactly five minutes after observed_at")
	}
	switch packet.RepositorySnapshot.Kind {
	case "git_head":
		if packet.RepositorySnapshot.CommitSHA == "" {
			return Packet{}, fmt.Errorf("git_head repository snapshot requires commit_sha")
		}
	case "content_only":
		if packet.RepositorySnapshot.CommitSHA != "" {
			return Packet{}, fmt.Errorf("content_only repository snapshot must not include commit_sha")
		}
	default:
		return Packet{}, fmt.Errorf("repository_snapshot.kind %q is invalid", packet.RepositorySnapshot.Kind)
	}
	if len(packet.Items) == 0 || len(packet.Items) > maxReconciliationItems {
		return Packet{}, fmt.Errorf("claim reconciliation requires between 1 and %d items", maxReconciliationItems)
	}
	seenClaims := map[string]bool{}
	for itemIndex := range packet.Items {
		item := &packet.Items[itemIndex]
		item.ClaimID = strings.TrimSpace(item.ClaimID)
		item.Reason = strings.TrimSpace(item.Reason)
		if item.ClaimID == "" || item.Reason == "" || !validClaimState(item.ExpectedState) || item.ExpectedRevision < 1 {
			return Packet{}, fmt.Errorf("item %d requires claim_id, valid expected_state, positive expected_revision, and reason", itemIndex)
		}
		if seenClaims[item.ClaimID] {
			return Packet{}, fmt.Errorf("duplicate claim_id %q", item.ClaimID)
		}
		seenClaims[item.ClaimID] = true
		if len(item.Evidence) > maxEvidencePerClaim {
			return Packet{}, fmt.Errorf("claim %q permits at most %d evidence refs", item.ClaimID, maxEvidencePerClaim)
		}
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
			if !validSourceKind(evidence.SourceKind) || evidence.SourcePath == "" || !boundedSpanPattern.MatchString(evidence.Span) || !sha256Pattern.MatchString(evidence.ExpectedContentHash) {
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
			return left.SourceKind+"\x00"+left.SourcePath+"\x00"+left.Span+"\x00"+left.Role+"\x00"+left.ExpectedContentHash < right.SourceKind+"\x00"+right.SourcePath+"\x00"+right.Span+"\x00"+right.Role+"\x00"+right.ExpectedContentHash
		})
	}
	sort.Slice(packet.Items, func(i, j int) bool { return packet.Items[i].ClaimID < packet.Items[j].ClaimID })
	expectedHash, err := canonicalPacketHash(packet)
	if err != nil {
		return Packet{}, err
	}
	if packet.PacketHash != expectedHash {
		return Packet{}, fmt.Errorf("claim reconciliation packet hash mismatch: expected %s, observed %s", packet.PacketHash, expectedHash)
	}
	return packet, nil
}

func canonicalPacketHash(packet Packet) (string, error) {
	packet.PacketHash = ""
	data, err := json.Marshal(packet)
	if err != nil {
		return "", fmt.Errorf("encode canonical claim reconciliation packet: %w", err)
	}
	return "sha256:" + digestHex(data), nil
}

func validateApplyWindow(packet Packet, now time.Time) error {
	observedAt, _ := time.Parse(time.RFC3339, packet.ObservedAt)
	expiresAt, _ := time.Parse(time.RFC3339, packet.ExpiresAt)
	now = now.UTC()
	if observedAt.After(now.Add(5 * time.Minute)) {
		return fmt.Errorf("claim reconciliation observed_at must not be more than five minutes in the future")
	}
	if now.After(expiresAt) {
		return fmt.Errorf("claim reconciliation prepared packet expired at %s", packet.ExpiresAt)
	}
	return nil
}

func prepareEvidence(paths rt.Paths, packet Packet) ([][]string, error) {
	matcher := ignore.Load(paths.Root)
	root, err := filepath.Abs(paths.Root)
	if err != nil {
		return nil, fmt.Errorf("resolve project root for claim reconciliation: %w", err)
	}
	out := make([][]string, len(packet.Items))
	var totalBytes int64
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
			actual, size, err := hashRegularFile(fullPath)
			if err != nil {
				return nil, fmt.Errorf("read claim %q evidence path %q: %w", item.ClaimID, relative, err)
			}
			totalBytes += size
			if totalBytes > maxEvidenceTotalBytes {
				return nil, fmt.Errorf("claim reconciliation evidence exceeds the %d MiB total read limit", maxEvidenceTotalBytes>>20)
			}
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
