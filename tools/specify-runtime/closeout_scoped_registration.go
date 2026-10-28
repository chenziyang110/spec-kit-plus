package main

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"io"
	"strings"

	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/scopedregistration"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/store"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/update"
)

const closeoutRegistrationDraftSchema = "cognition-scoped-registration-draft.v1"

// Completed replay reads the native parent registration receipt. It must not
// invoke the update writer or republish either receipt to prove idempotence.
func requireCompletedCloseoutRegistration(paths rt.Paths, intent closeoutIntent) error {
	_, canonical, err := scopedregistration.Parse([]byte(intent.ScopedRegistrationJSON))
	if err != nil {
		return err
	}
	st, err := store.OpenExisting(paths)
	if err != nil {
		return err
	}
	defer st.Close()
	generation, err := st.ActiveGenerationID(context.Background())
	if err != nil {
		return err
	}
	var attrsRaw string
	if err := st.DB().QueryRowContext(context.Background(), `SELECT attrs_json FROM updates WHERE generation_id = ? AND id = ?`, generation, intent.UpdateID).Scan(&attrsRaw); err != nil {
		return fmt.Errorf("completed registration parent is unavailable in the current generation: %w", err)
	}
	var attrs struct {
		IntentID     string `json:"closeout_intent_id"`
		Registration struct {
			PacketSHA string `json:"packet_sha256"`
			Receipt   struct {
				Status         string   `json:"status"`
				RegistrationID string   `json:"registration_id"`
				GenerationID   string   `json:"active_generation_id"`
				PacketSHA      string   `json:"packet_sha256"`
				ValidationDebt []string `json:"validation_debt"`
			} `json:"receipt"`
		} `json:"scoped_registration"`
	}
	if err := json.Unmarshal([]byte(attrsRaw), &attrs); err != nil {
		return fmt.Errorf("completed registration parent receipt is invalid: %w", err)
	}
	digest := fmt.Sprintf("%x", sha256.Sum256(canonical))
	receipt := attrs.Registration.Receipt
	if attrs.IntentID != intent.ID || attrs.Registration.PacketSHA != digest || receipt.PacketSHA != digest || receipt.RegistrationID != intent.UpdateID || receipt.GenerationID != generation || receipt.Status != "ok" || len(receipt.ValidationDebt) != 0 {
		return fmt.Errorf("completed registration receipt does not prove the exact current parent packet")
	}
	return nil
}

// A workflow supplies semantic local keys and evidence paths. Its existing
// native proof supplies identity, source versions and integrity fields.
type closeoutRegistrationDraft struct {
	Schema string                          `json:"schema"`
	Delta  scopedregistration.Delta        `json:"delta"`
	Result scopedregistration.ResultIntent `json:"result"`
}

func prepareCloseoutRegistration(paths rt.Paths, workflow, scope, payloadJSON string, strong *closeoutBinding, doBinding *DoCognitionBinding, owned []string) (string, error) {
	if strings.TrimSpace(payloadJSON) == "" {
		return "", nil
	}
	var payload struct {
		Registration json.RawMessage `json:"scoped_registration"`
	}
	if err := json.Unmarshal([]byte(payloadJSON), &payload); err != nil {
		return "", err
	}
	if len(payload.Registration) == 0 || bytes.Equal(bytes.TrimSpace(payload.Registration), []byte("null")) {
		return "", nil
	}
	var draft closeoutRegistrationDraft
	decoder := json.NewDecoder(bytes.NewReader(payload.Registration))
	decoder.UseNumber()
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&draft); err != nil {
		return "", fmt.Errorf("scoped_registration draft: %w", err)
	}
	var trailing any
	if err := decoder.Decode(&trailing); err != io.EOF {
		return "", fmt.Errorf("scoped_registration draft must contain one JSON value")
	}
	if draft.Schema != closeoutRegistrationDraftSchema {
		return "", fmt.Errorf("scoped_registration schema must be %s", closeoutRegistrationDraftSchema)
	}
	request := scopedregistration.Request{Schema: scopedregistration.Schema, Delta: draft.Delta, Result: draft.Result}
	if workflow == "sp-do" {
		if doBinding == nil {
			return "", fmt.Errorf("scoped registration requires the existing Do proof")
		}
		request.Proof = scopedregistration.ProofBinding{Kind: "do_native", DoRef: scope}
	} else {
		if strong == nil {
			return "", fmt.Errorf("scoped registration requires the current sealed closeout binding")
		}
		request.Proof = scopedregistration.ProofBinding{Kind: "closeout_binding", BindingID: strong.ID, Workflow: workflow, Scope: scope}
	}
	if !equalCloseoutPaths(scopedRegistrationChangedPaths(request), owned) {
		return "", fmt.Errorf("scoped registration must account for the complete native owned delta, including old rename paths")
	}
	basis, err := buildScopedRegistrationProofBasis(paths.Root, request)
	if err != nil {
		return "", err
	}
	if err := prepareCloseoutRegistrationIDs(&request); err != nil {
		return "", err
	}
	for i := range request.Delta.Evidence {
		row := &request.Delta.Evidence[i]
		if row.SourceKind != "file" {
			continue
		}
		ref := normalizeCloseoutPath(row.SourcePath)
		proof := basis.Source[ref]
		parts := strings.Split(proof, ":")
		if len(parts) < 2 || parts[0] != "file" || !isLowerHexSHA256(parts[1]) {
			return "", fmt.Errorf("scoped evidence %s is not covered by native source proof", ref)
		}
		derived := "sha256:" + parts[1]
		if row.ContentHash != "" && row.ContentHash != derived && row.ContentHash != parts[1] {
			return "", fmt.Errorf("scoped evidence %s contradicts native content hash", ref)
		}
		row.SourcePath, row.ContentHash = ref, derived
	}
	if err := preflightScopedVerifiedEvidenceCoverage(request); err != nil {
		return "", err
	}
	raw, err := json.Marshal(request)
	if err != nil {
		return "", err
	}
	// Use the shared request parser, including its lossless number handling.
	_, canonical, err := scopedregistration.Parse(raw)
	return string(canonical), err
}

func prepareCloseoutRegistrationIDs(request *scopedregistration.Request) error {
	ids := map[string]string{}
	bind := func(kind, local string) (string, error) {
		local = strings.TrimSpace(local)
		if local == "" {
			return "", fmt.Errorf("scoped %s row requires a stable semantic local key", kind)
		}
		if _, exists := ids[local]; exists {
			return "", fmt.Errorf("duplicate scoped semantic local key %s", local)
		}
		id := kind + "-scoped-" + closeoutIntentDigest(closeoutRegistrationDraftSchema, kind, local)[:24]
		ids[local] = id
		return id, nil
	}
	var err error
	for i := range request.Delta.Evidence {
		request.Delta.Evidence[i].ID, err = bind("E", request.Delta.Evidence[i].ID)
		if err != nil {
			return err
		}
	}
	for i := range request.Delta.Nodes {
		request.Delta.Nodes[i].ID, err = bind("N", request.Delta.Nodes[i].ID)
		if err != nil {
			return err
		}
	}
	for i := range request.Delta.Edges {
		request.Delta.Edges[i].ID, err = bind("R", request.Delta.Edges[i].ID)
		if err != nil {
			return err
		}
	}
	for i := range request.Delta.Observations {
		request.Delta.Observations[i].ID, err = bind("O", request.Delta.Observations[i].ID)
		if err != nil {
			return err
		}
	}
	for i := range request.Delta.Claims {
		request.Delta.Claims[i].ID, err = bind("C", request.Delta.Claims[i].ID)
		if err != nil {
			return err
		}
		for j := range request.Delta.Claims[i].Verifications {
			v := &request.Delta.Claims[i].Verifications[j]
			if v.ObservedAt == "" {
				return fmt.Errorf("claim verification needs its actual observation time")
			}
			if v.ID == "" {
				v.ID = fmt.Sprintf("%s-verification-%d", request.Delta.Claims[i].ID, j)
			}
			v.ID = "V-scoped-" + closeoutIntentDigest(request.Delta.Claims[i].ID, v.ID)[:24]
		}
	}
	mapID := func(value string) string {
		if id, exists := ids[value]; exists {
			return id
		}
		return value
	}
	mapIDs := func(values []string) {
		for i := range values {
			values[i] = mapID(values[i])
		}
	}
	for i := range request.Delta.Nodes {
		mapIDs(request.Delta.Nodes[i].EvidenceIDs)
	}
	for i := range request.Delta.Edges {
		row := &request.Delta.Edges[i]
		row.SourceID, row.TargetID = mapID(row.SourceID), mapID(row.TargetID)
		mapIDs(row.EvidenceIDs)
	}
	for i := range request.Delta.Observations {
		mapIDs(request.Delta.Observations[i].EvidenceIDs)
	}
	for i := range request.Delta.Claims {
		row := &request.Delta.Claims[i]
		row.NodeID = mapID(row.NodeID)
		mapIDs(row.SupportingEvidenceIDs)
		mapIDs(row.ContradictingEvidenceIDs)
		for j := range row.Verifications {
			row.Verifications[j].EvidenceID = mapID(row.Verifications[j].EvidenceID)
		}
	}
	for i := range request.Delta.ChangedPaths {
		row := &request.Delta.ChangedPaths[i]
		row.NodeID = mapID(row.NodeID)
		mapIDs(row.EvidenceRefs)
	}
	for i := range request.Delta.Aliases {
		row := &request.Delta.Aliases[i]
		row.TargetID, row.EvidenceID = mapID(row.TargetID), mapID(row.EvidenceID)
		row.ID = "A-scoped-" + closeoutIntentDigest(row.Alias, row.TargetID, row.Language)[:24]
		if row.NormalizedAlias == "" {
			row.NormalizedAlias = strings.ToLower(strings.TrimSpace(row.Alias))
		}
		if row.TargetType == "" {
			row.TargetType = "node"
		}
		if row.Source == "" {
			row.Source = "workflow-scoped-registration"
		}
	}
	for i := range request.Delta.PathIndex {
		row := &request.Delta.PathIndex[i]
		row.NodeID, row.EvidenceID = mapID(row.NodeID), mapID(row.EvidenceID)
		row.ID = "P-scoped-" + closeoutIntentDigest(row.Path, row.NodeID, row.Relation)[:24]
	}
	return nil
}

func applyCloseoutRegistrationLocked(runtime *update.LockedRuntime, paths rt.Paths, intent closeoutIntent, parent update.UpdatePayload) (*scopedregistration.Payload, error) {
	if intent.ScopedRegistrationJSON == "" {
		return nil, nil
	}
	request, canonical, err := scopedregistration.Parse([]byte(intent.ScopedRegistrationJSON))
	if err != nil {
		return nil, err
	}
	basis, err := buildScopedRegistrationProofBasis(paths.Root, request)
	if err != nil {
		return nil, err
	}
	basis.ParentUpdateID, basis.ParentIntentID = parent.UpdateID, intent.ID
	if err := requireCurrentCloseoutBindingLocked(runtime, paths, intent); err != nil {
		return nil, err
	}
	result, err := scopedregistration.ApplyWithProofBasis(context.Background(), paths, request, canonical, basis, &scopedregistration.Guards{BeforeCommit: func() error {
		if err := scopedRegistrationProofSourceUnchanged(paths.Root, basis); err != nil {
			return err
		}
		return requireCurrentCloseoutBindingLocked(runtime, paths, intent)
	}})
	if err != nil {
		return &result, err
	}
	if err := scopedRegistrationProofSourceUnchanged(paths.Root, basis); err != nil {
		if debtErr := markScopedRegistrationPublicationDrift(paths, result, request, err.Error()); debtErr != nil {
			return &result, fmt.Errorf("%w; could not record scoped source debt: %v", err, debtErr)
		}
		return &result, err
	}
	if err := requireCurrentCloseoutBindingLocked(runtime, paths, intent); err != nil {
		if debtErr := markScopedRegistrationPublicationDrift(paths, result, request, err.Error()); debtErr != nil {
			return &result, fmt.Errorf("%w; could not record scoped binding debt: %v", err, debtErr)
		}
		return &result, err
	}
	if result.Status != "ok" || len(result.ValidationDebt) != 0 || request.Result.State != "registered" {
		return &result, fmt.Errorf("scoped registration remains incomplete: %s; %s", result.Status, strings.Join(result.ValidationDebt, ", "))
	}
	return &result, nil
}
