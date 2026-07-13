package reconcile

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"

	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/claim"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/ignore"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/query"
	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/store"
)

const CurrentPrepareContractVersion = 1

type PrepareRequest struct {
	ContractVersion int           `json:"claim_reconciliation_prepare_contract_version"`
	Workflow        string        `json:"workflow"`
	Items           []PrepareItem `json:"items"`
}

type PrepareItem struct {
	ClaimID      string            `json:"claim_id"`
	Reason       string            `json:"reason"`
	Evidence     []PrepareEvidence `json:"evidence"`
	Verification *Verification     `json:"verification,omitempty"`
}

type PrepareEvidence struct {
	SourcePath string `json:"source_path"`
	Span       string `json:"span"`
	Role       string `json:"role"`
}

type PreparePayload struct {
	Status             string                  `json:"status"`
	ResultState        string                  `json:"result_state"`
	ContractVersion    int                     `json:"claim_reconciliation_prepare_contract_version"`
	PrepareID          string                  `json:"prepare_id"`
	ExpiresAt          string                  `json:"expires_at"`
	PreparedPacketPath string                  `json:"prepared_packet_path"`
	ApplyArgv          []string                `json:"apply_argv"`
	EpistemicContract  query.EpistemicContract `json:"epistemic_contract"`
}

type PrepareErrorPayload struct {
	Status            string   `json:"status"`
	ResultState       string   `json:"result_state"`
	ContractVersion   int      `json:"claim_reconciliation_prepare_contract_version"`
	ErrorCode         string   `json:"error_code"`
	Errors            []string `json:"errors"`
	RecommendedAction string   `json:"recommended_next_action"`
}

func ParsePrepareRequest(data []byte) (PrepareRequest, error) {
	decoder := json.NewDecoder(bytes.NewReader(data))
	decoder.DisallowUnknownFields()
	var request PrepareRequest
	if err := decoder.Decode(&request); err != nil {
		return PrepareRequest{}, fmt.Errorf("decode claim reconciliation prepare request: %w", err)
	}
	var trailing any
	if err := decoder.Decode(&trailing); !errors.Is(err, io.EOF) {
		if err == nil {
			return PrepareRequest{}, fmt.Errorf("decode claim reconciliation prepare request: multiple JSON values are not allowed")
		}
		return PrepareRequest{}, fmt.Errorf("decode claim reconciliation prepare request trailing data: %w", err)
	}
	return normalizeAndValidatePrepareRequest(request)
}

func Prepare(paths rt.Paths, request PrepareRequest) (PreparePayload, error) {
	return prepareAt(paths, request, time.Now().UTC())
}

func prepareAt(paths rt.Paths, request PrepareRequest, observedAt time.Time) (PreparePayload, error) {
	request, err := normalizeAndValidatePrepareRequest(request)
	if err != nil {
		return PreparePayload{}, err
	}
	st, err := store.OpenExisting(paths)
	if err != nil {
		return PreparePayload{}, fmt.Errorf("open graph store for claim reconciliation prepare: %w", err)
	}
	claimIDs := make([]string, 0, len(request.Items))
	for _, item := range request.Items {
		claimIDs = append(claimIDs, item.ClaimID)
	}
	snapshot, err := st.ReadClaimReconciliationSnapshot(context.Background(), claimIDs)
	closeErr := st.Close()
	if err != nil {
		return PreparePayload{}, err
	}
	if closeErr != nil {
		return PreparePayload{}, fmt.Errorf("close graph store after claim reconciliation prepare: %w", closeErr)
	}

	packet := Packet{
		ContractVersion: CurrentContractVersion, ExpectedGenerationID: snapshot.GenerationID,
		Workflow: request.Workflow, ObservedAt: observedAt.UTC().Format(time.RFC3339Nano), ExpiresAt: observedAt.UTC().Add(preparedPacketTTL).Format(time.RFC3339Nano),
		Items: make([]Item, 0, len(request.Items)),
	}
	packet.RepositorySnapshot = readRepositorySnapshot(paths.Root)
	matcher := ignore.Load(paths.Root)
	root, err := filepath.Abs(paths.Root)
	if err != nil {
		return PreparePayload{}, fmt.Errorf("resolve project root for claim reconciliation prepare: %w", err)
	}
	for _, requestedItem := range request.Items {
		head := snapshot.Claims[requestedItem.ClaimID]
		item := Item{
			ClaimID: requestedItem.ClaimID, ExpectedState: head.State, ExpectedRevision: head.Revision,
			Reason: requestedItem.Reason, Verification: requestedItem.Verification,
			Evidence: make([]Evidence, 0, len(requestedItem.Evidence)),
		}
		for _, requestedEvidence := range requestedItem.Evidence {
			relative, fullPath, err := safeEvidencePath(root, requestedEvidence.SourcePath)
			if err != nil {
				return PreparePayload{}, fmt.Errorf("claim %q evidence path: %w", item.ClaimID, err)
			}
			if matcher.Ignored(relative) {
				return PreparePayload{}, fmt.Errorf("claim %q evidence path %q is excluded by project cognition ignore rules", item.ClaimID, relative)
			}
			contentHash, err := hashRegularFile(fullPath)
			if err != nil {
				return PreparePayload{}, fmt.Errorf("read claim %q evidence path %q: %w", item.ClaimID, relative, err)
			}
			item.Evidence = append(item.Evidence, Evidence{
				SourceKind: deriveSourceKind(relative), SourcePath: relative, Span: requestedEvidence.Span,
				Role: requestedEvidence.Role, ExpectedContentHash: contentHash,
			})
		}
		sort.Slice(item.Evidence, func(i, j int) bool {
			left := item.Evidence[i]
			right := item.Evidence[j]
			return left.SourceKind+"\x00"+left.SourcePath+"\x00"+left.Span+"\x00"+left.Role+"\x00"+left.ExpectedContentHash < right.SourceKind+"\x00"+right.SourcePath+"\x00"+right.Span+"\x00"+right.Role+"\x00"+right.ExpectedContentHash
		})
		packet.Items = append(packet.Items, item)
	}
	if after := readRepositorySnapshot(paths.Root); after != packet.RepositorySnapshot {
		return PreparePayload{}, fmt.Errorf("repository snapshot changed while preparing claim reconciliation")
	}
	prepareDigest, err := canonicalPrepareDigest(packet)
	if err != nil {
		return PreparePayload{}, err
	}
	packet.PrepareID = "claim-reconciliation-prepare:" + prepareDigest[:24]
	packet.PacketHash, err = canonicalPacketHash(packet)
	if err != nil {
		return PreparePayload{}, err
	}
	packet, err = normalizeAndValidatePacket(packet)
	if err != nil {
		return PreparePayload{}, err
	}
	packetJSON, err := json.Marshal(packet)
	if err != nil {
		return PreparePayload{}, fmt.Errorf("encode prepared claim reconciliation packet: %w", err)
	}
	packetDigest := strings.TrimPrefix(packet.PacketHash, "sha256:")
	preparedPath, err := writePreparedPacket(paths, packetDigest[:24], packetJSON)
	if err != nil {
		return PreparePayload{}, err
	}
	return PreparePayload{
		Status: "ok", ResultState: "prepared", ContractVersion: CurrentPrepareContractVersion,
		PrepareID: packet.PrepareID, ExpiresAt: packet.ExpiresAt, PreparedPacketPath: preparedPath,
		ApplyArgv:         []string{"project-cognition", "claim-reconcile", "apply", "--input", preparedPath, "--format", "json"},
		EpistemicContract: query.NewEpistemicContract(),
	}, nil
}

func canonicalPrepareDigest(packet Packet) (string, error) {
	packet.PrepareID = ""
	packet.PacketHash = ""
	data, err := json.Marshal(packet)
	if err != nil {
		return "", fmt.Errorf("encode canonical claim reconciliation preparation: %w", err)
	}
	return digestHex(data), nil
}

func readRepositorySnapshot(root string) RepositorySnapshot {
	commitSHA, err := rt.GitHead(root)
	if err != nil || strings.TrimSpace(commitSHA) == "" {
		return RepositorySnapshot{Kind: "content_only"}
	}
	return RepositorySnapshot{Kind: "git_head", CommitSHA: strings.TrimSpace(commitSHA)}
}

func PrepareBlockedPayload(err error) PrepareErrorPayload {
	message := "claim reconciliation prepare failed"
	if err != nil {
		message = err.Error()
	}
	return PrepareErrorPayload{
		Status: "error", ResultState: "blocked", ContractVersion: CurrentPrepareContractVersion,
		ErrorCode: "invalid_claim_reconciliation_prepare", Errors: []string{message}, RecommendedAction: "repair_reconciliation_intent",
	}
}

func normalizeAndValidatePrepareRequest(request PrepareRequest) (PrepareRequest, error) {
	request = clonePrepareRequest(request)
	request.Workflow = strings.TrimSpace(request.Workflow)
	if request.ContractVersion != CurrentPrepareContractVersion {
		return PrepareRequest{}, fmt.Errorf("claim_reconciliation_prepare_contract_version %d is unsupported; expected %d", request.ContractVersion, CurrentPrepareContractVersion)
	}
	if request.Workflow == "" {
		return PrepareRequest{}, fmt.Errorf("workflow is required")
	}
	if len(request.Items) == 0 {
		return PrepareRequest{}, fmt.Errorf("claim reconciliation prepare requires at least one item")
	}
	seenClaims := map[string]bool{}
	for itemIndex := range request.Items {
		item := &request.Items[itemIndex]
		item.ClaimID = strings.TrimSpace(item.ClaimID)
		item.Reason = strings.TrimSpace(item.Reason)
		if item.ClaimID == "" || item.Reason == "" {
			return PrepareRequest{}, fmt.Errorf("item %d requires claim_id and reason", itemIndex)
		}
		if seenClaims[item.ClaimID] {
			return PrepareRequest{}, fmt.Errorf("duplicate claim_id %q", item.ClaimID)
		}
		seenClaims[item.ClaimID] = true
		if len(item.Evidence) == 0 && item.Verification == nil {
			return PrepareRequest{}, fmt.Errorf("claim %q requires evidence or verification", item.ClaimID)
		}
		seenEvidence := map[string]bool{}
		hasSupporting := false
		hasContradicting := false
		for evidenceIndex := range item.Evidence {
			evidence := &item.Evidence[evidenceIndex]
			normalizedPath, err := normalizeRepositoryRelativePath(evidence.SourcePath)
			if err != nil {
				return PrepareRequest{}, fmt.Errorf("claim %q evidence %d source_path: %w", item.ClaimID, evidenceIndex, err)
			}
			evidence.SourcePath = normalizedPath
			evidence.Span = strings.TrimSpace(evidence.Span)
			evidence.Role = strings.TrimSpace(evidence.Role)
			if evidence.Span == "" {
				return PrepareRequest{}, fmt.Errorf("claim %q evidence %d requires a bounded span", item.ClaimID, evidenceIndex)
			}
			switch evidence.Role {
			case "supporting":
				hasSupporting = true
			case "contradicting":
				hasContradicting = true
			default:
				return PrepareRequest{}, fmt.Errorf("claim %q evidence %d role %q is invalid", item.ClaimID, evidenceIndex, evidence.Role)
			}
			identity := evidence.SourcePath + "\x00" + evidence.Span + "\x00" + evidence.Role
			if seenEvidence[identity] {
				return PrepareRequest{}, fmt.Errorf("claim %q contains duplicate evidence for %q", item.ClaimID, evidence.SourcePath)
			}
			seenEvidence[identity] = true
		}
		if item.Verification != nil {
			item.Verification.Command = strings.TrimSpace(item.Verification.Command)
			if item.Verification.Command == "" || !validVerificationResult(item.Verification.Result) {
				return PrepareRequest{}, fmt.Errorf("claim %q verification requires a valid result and command", item.ClaimID)
			}
			if item.Verification.Result == claim.VerificationPassed && !hasSupporting {
				return PrepareRequest{}, fmt.Errorf("claim %q passed verification requires supporting evidence", item.ClaimID)
			}
			if item.Verification.Result == claim.VerificationContradicted && !hasContradicting {
				return PrepareRequest{}, fmt.Errorf("claim %q contradicted verification requires contradicting evidence", item.ClaimID)
			}
		}
		sort.Slice(item.Evidence, func(i, j int) bool {
			left := item.Evidence[i]
			right := item.Evidence[j]
			return left.SourcePath+"\x00"+left.Span+"\x00"+left.Role < right.SourcePath+"\x00"+right.Span+"\x00"+right.Role
		})
	}
	sort.Slice(request.Items, func(i, j int) bool { return request.Items[i].ClaimID < request.Items[j].ClaimID })
	return request, nil
}

func clonePrepareRequest(request PrepareRequest) PrepareRequest {
	request.Items = append([]PrepareItem(nil), request.Items...)
	for index := range request.Items {
		request.Items[index].Evidence = append([]PrepareEvidence(nil), request.Items[index].Evidence...)
		if request.Items[index].Verification != nil {
			verification := *request.Items[index].Verification
			request.Items[index].Verification = &verification
		}
	}
	return request
}

func deriveSourceKind(relative string) string {
	lower := strings.ToLower(filepath.ToSlash(relative))
	base := filepath.Base(lower)
	extension := filepath.Ext(base)
	if strings.Contains(lower, "/test/") || strings.Contains(lower, "/tests/") || strings.HasSuffix(base, "_test.go") || strings.Contains(base, ".test.") || strings.Contains(base, ".spec.") {
		return "test"
	}
	if strings.HasPrefix(lower, "docs/") || strings.HasPrefix(lower, "doc/") || extension == ".md" || extension == ".rst" || extension == ".adoc" {
		return "doc"
	}
	if strings.HasPrefix(lower, "config/") || strings.Contains(lower, "/config/") {
		return "config"
	}
	switch extension {
	case ".yaml", ".yml", ".toml", ".ini", ".conf", ".properties":
		return "config"
	default:
		return "source"
	}
}

func hashRegularFile(fullPath string) (string, error) {
	info, err := os.Stat(fullPath)
	if err != nil {
		return "", err
	}
	if !info.Mode().IsRegular() {
		return "", fmt.Errorf("is not a regular file")
	}
	data, err := os.ReadFile(fullPath)
	if err != nil {
		return "", err
	}
	return "sha256:" + digestHex(data), nil
}

func writePreparedPacket(paths rt.Paths, digest string, packetJSON []byte) (string, error) {
	dir := filepath.Join(paths.RuntimeDir, "claim-reconciliations", "prepared")
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return "", fmt.Errorf("create prepared claim reconciliation directory: %w", err)
	}
	target := filepath.Join(dir, "claim-reconciliation-"+digest+".json")
	if existing, err := os.ReadFile(target); err == nil {
		if bytes.Equal(existing, packetJSON) {
			return rt.RelativeRuntimePath(paths, target), nil
		}
		return "", fmt.Errorf("prepared claim reconciliation path %q conflicts with different content", rt.RelativeRuntimePath(paths, target))
	} else if !errors.Is(err, os.ErrNotExist) {
		return "", fmt.Errorf("read prepared claim reconciliation packet: %w", err)
	}
	tmp, err := os.CreateTemp(dir, ".claim-reconciliation-*.tmp")
	if err != nil {
		return "", fmt.Errorf("create prepared claim reconciliation packet: %w", err)
	}
	tmpName := tmp.Name()
	cleanup := func() {
		_ = tmp.Close()
		_ = os.Remove(tmpName)
	}
	if err := tmp.Chmod(0o600); err != nil {
		cleanup()
		return "", fmt.Errorf("secure prepared claim reconciliation packet: %w", err)
	}
	if _, err := tmp.Write(packetJSON); err != nil {
		cleanup()
		return "", fmt.Errorf("write prepared claim reconciliation packet: %w", err)
	}
	if err := tmp.Sync(); err != nil {
		cleanup()
		return "", fmt.Errorf("sync prepared claim reconciliation packet: %w", err)
	}
	if err := tmp.Close(); err != nil {
		_ = os.Remove(tmpName)
		return "", fmt.Errorf("close prepared claim reconciliation packet: %w", err)
	}
	if err := os.Rename(tmpName, target); err != nil {
		_ = os.Remove(tmpName)
		return "", fmt.Errorf("publish prepared claim reconciliation packet: %w", err)
	}
	return rt.RelativeRuntimePath(paths, target), nil
}
