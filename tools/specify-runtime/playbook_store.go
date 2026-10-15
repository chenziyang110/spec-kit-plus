package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"reflect"
	"sort"
	"strings"
	"time"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/filelock"
)

type playbookUsage struct {
	SchemaVersion    int                         `json:"schema_version"`
	PlaybookID       string                      `json:"method_id"`
	Revision         int                         `json:"revision"`
	DefinitionDigest string                      `json:"definition_digest"`
	SessionID        string                      `json:"session_id"`
	Verification     DoPlaybookValidationReceipt `json:"verification"`
}

type playbookIndexEntry struct {
	ID                string              `json:"id"`
	Revision          int                 `json:"revision"`
	ContentDigest     string              `json:"content_digest"`
	Title             string              `json:"title"`
	Operation         string              `json:"operation"`
	Target            string              `json:"target"`
	Owner             string              `json:"owner"`
	Variant           string              `json:"variant"`
	Aliases           []string            `json:"aliases"`
	Applicability     map[string][]string `json:"applicability"`
	SourceFingerprint map[string]string   `json:"source_fingerprint"`
}

func loadPlaybookDocument(projectRoot, id string) (PlaybookDocument, error) {
	target, err := playbookCanonicalPath(projectRoot, id)
	if err != nil {
		return PlaybookDocument{}, err
	}
	return readPlaybookDocument(projectRoot, target, id, 0)
}

func loadPlaybookRevision(root, id string, revision int) (PlaybookDocument, error) {
	if revision < 1 || revision > 999999 {
		return PlaybookDocument{}, fmt.Errorf("playbook_revision_invalid")
	}
	target, err := playbookStorePath(root, id, fmt.Sprintf("revisions/%06d.json", revision))
	if err != nil {
		return PlaybookDocument{}, err
	}
	return readPlaybookDocument(root, target, id, revision)
}

func readPlaybookDocument(root, target, id string, revision int) (PlaybookDocument, error) {
	raw, err := playbookReadBoundedFile(target)
	if err != nil {
		return PlaybookDocument{}, err
	}
	return decodePlaybookDocument(root, raw, id, revision)
}

func decodePlaybookDocument(root string, raw []byte, id string, revision int) (PlaybookDocument, error) {
	var document PlaybookDocument
	if err := decodePlaybookJSON(raw, &document); err != nil {
		return document, err
	}
	if document.SchemaVersion != playbookSchemaVersion || document.ID != id || document.ID != playbookID(document.Definition) || document.Revision < 1 || (revision > 0 && document.Revision != revision) || document.Status != "verified" {
		return document, fmt.Errorf("playbook_document_identity_invalid")
	}
	if err := validatePlaybookDefinition(root, document.Definition); err != nil {
		return document, err
	}
	digest, err := playbookDefinitionDigest(document.Definition)
	if err != nil || digest != document.ContentDigest {
		return document, fmt.Errorf("playbook_document_digest_mismatch")
	}
	if document.Verification.MethodID != id || document.Verification.DefinitionDigest != digest || document.Verification.Outcome != "passed" || document.Verification.SessionID == "" || !reflect.DeepEqual(document.SourceFingerprint, document.Verification.Sources) {
		return document, fmt.Errorf("playbook_document_verification_invalid")
	}
	if err := playbookValidateFingerprint(root, document.SourceFingerprint); err != nil {
		return document, err
	}
	if err := validatePlaybookVerificationInstance(root, document.Definition, document.Verification); err != nil {
		return document, err
	}
	return document, nil
}

func playbookReadBoundedFile(target string) ([]byte, error) {
	info, err := os.Lstat(target)
	if err != nil {
		return nil, err
	}
	if !info.Mode().IsRegular() || info.Size() > playbookMaxJSONBytes {
		return nil, fmt.Errorf("playbook_document_nonregular_or_oversized")
	}
	return os.ReadFile(target)
}

func playbookValidateFingerprint(root string, fingerprint map[string]string) error {
	if len(fingerprint) < 1 || len(fingerprint) > 192 {
		return fmt.Errorf("playbook_source_fingerprint_invalid")
	}
	for source, digest := range fingerprint {
		if _, err := playbookSafePath(root, source, false); err != nil {
			return err
		}
		if !playbookDigestPattern.MatchString(digest) {
			return fmt.Errorf("playbook_source_fingerprint_invalid")
		}
	}
	return nil
}

func playbookStorePath(root, id, suffix string) (string, error) {
	canonical, err := playbookCanonicalPath(root, id)
	if err != nil {
		return "", err
	}
	rootAbs, err := filepath.Abs(root)
	if err != nil {
		return "", err
	}
	target := filepath.Join(filepath.Dir(canonical), filepath.FromSlash(suffix))
	rel, err := filepath.Rel(rootAbs, target)
	if err != nil {
		return "", err
	}
	secured, err := secureProjectPath(root, filepath.ToSlash(rel))
	if err != nil {
		return "", fmt.Errorf("playbook_store_path_unsafe")
	}
	return secured, nil
}

func playbookWithLock(root string, fn func() (map[string]any, error)) (map[string]any, error) {
	lockPath, err := secureProjectPath(root, ".specify/runtime/locks/playbooks.lock")
	if err != nil {
		return nil, fmt.Errorf("playbook_store_path_unsafe")
	}
	if err := os.MkdirAll(filepath.Dir(lockPath), 0o755); err != nil {
		return nil, err
	}
	release, err := filelock.Acquire(lockPath)
	if err != nil {
		return nil, err
	}
	defer release()
	return fn()
}

func updatePlaybook(root string, request PlaybookUpdateRequest) (map[string]any, error) {
	if err := validatePlaybookDefinition(root, request.Definition); err != nil {
		return nil, err
	}
	request.Definition = playbookNormalizeDefinition(request.Definition)
	if strings.TrimSpace(request.ChangeSummary) == "" || len(request.ChangeSummary) > 2048 {
		return nil, fmt.Errorf("playbook_change_summary_required")
	}
	policy, _, err := (learningService{projectRoot: root}).loadLearningPolicy(true)
	if err != nil {
		return nil, err
	}
	if redactLearningTextWithPolicy(request.ChangeSummary, policy).text != request.ChangeSummary {
		return nil, fmt.Errorf("playbook_sensitive_change_summary_rejected")
	}
	id := playbookID(request.Definition)
	if request.ID != "" && request.ID != id {
		return nil, fmt.Errorf("playbook_identity_change_requires_new_method")
	}
	request.ID = id
	if request.BaseDigest != "" && !playbookDigestPattern.MatchString(request.BaseDigest) {
		return nil, fmt.Errorf("playbook_base_digest_invalid")
	}
	if request.SessionID != "" && !playbookSafeSessionID(request.SessionID) {
		return nil, fmt.Errorf("playbook_session_id_invalid")
	}
	digest, err := playbookDefinitionDigest(request.Definition)
	if err != nil {
		return nil, err
	}
	return playbookWithLock(root, func() (map[string]any, error) {
		canonical, err := playbookCanonicalPath(root, id)
		if err != nil {
			return nil, err
		}
		currentRaw, readErr := playbookReadBoundedFile(canonical)
		exists := readErr == nil
		var current PlaybookDocument
		if exists {
			current, err = decodePlaybookDocument(root, currentRaw, id, 0)
			if err != nil {
				return nil, err
			}
		} else if !os.IsNotExist(readErr) {
			return nil, readErr
		}
		// The durable usage record is the idempotency key. It must be checked
		// before CAS so a retry remains a no-op after its own successful update.
		if request.SessionID != "" && !request.ProposalOnly {
			if usage, found, err := readPlaybookUsage(root, id, request.SessionID); err != nil {
				return nil, err
			} else if found {
				if usage.DefinitionDigest != digest {
					return nil, fmt.Errorf("playbook_session_already_bound_to_other_definition")
				}
				usagePath, _ := playbookStorePath(root, id, "usage/"+request.SessionID+".json")
				usageRaw, err := playbookReadBoundedFile(usagePath)
				if err != nil {
					return nil, err
				}
				return map[string]any{"status": "already_recorded", "id": id, "revision": usage.Revision, "content_digest": digest, "session_id": request.SessionID, "changed_paths": []string{}, "knowledge_receipt": playbookKnowledgeReceipt(root, usagePath, usageRaw, id, usage.Revision)}, nil
			}
		}
		baseRevision := 0
		if exists {
			baseRevision = current.Revision
			if request.BaseDigest == "" || request.BaseDigest != current.ContentDigest {
				return nil, fmt.Errorf("playbook_revision_conflict_reload_current")
			}
		} else if request.BaseDigest != "" {
			return nil, fmt.Errorf("playbook_revision_conflict_expected_absent")
		}
		if request.ProposalOnly || request.SessionID == "" {
			if exists && digest == current.ContentDigest {
				return map[string]any{"status": "no_change", "id": id, "revision": current.Revision, "content_digest": digest, "changed_paths": []string{}}, nil
			}
			return writePlaybookProposal(root, request, digest, currentRaw, exists)
		}
		verification, err := validateDoSessionForPlaybook(root, request.SessionID, id, baseRevision, request.BaseDigest, digest)
		if err != nil {
			return nil, fmt.Errorf("playbook_session_verification_required: %w", err)
		}
		if verification.Outcome != "passed" || verification.SessionID != request.SessionID || verification.MethodID != id || verification.DefinitionDigest != digest || verification.BaseDigest != request.BaseDigest || verification.BaseRevision != baseRevision {
			return nil, fmt.Errorf("playbook_session_verification_binding_mismatch")
		}
		sources, err := playbookSourceFingerprint(root, request.Definition)
		if err != nil {
			return nil, err
		}
		if !reflect.DeepEqual(sources, verification.Sources) {
			return nil, fmt.Errorf("playbook_sources_changed_since_session_verification")
		}
		if err := playbookValidateFingerprint(root, sources); err != nil {
			return nil, err
		}
		now := time.Now().UTC().Format(time.RFC3339Nano)
		document := PlaybookDocument{SchemaVersion: playbookSchemaVersion, ID: id, Revision: baseRevision + 1, ContentDigest: digest, Status: "verified", Definition: request.Definition, SourceFingerprint: sources, Verification: verification, CreatedAt: now, UpdatedAt: now}
		if exists {
			document.CreatedAt = current.CreatedAt
		}
		noChange := exists && digest == current.ContentDigest
		if noChange {
			document = current
		}
		usage := playbookUsage{SchemaVersion: playbookSchemaVersion, PlaybookID: id, Revision: document.Revision, DefinitionDigest: digest, SessionID: request.SessionID, Verification: verification}
		usagePath, err := playbookStorePath(root, id, "usage/"+request.SessionID+".json")
		if err != nil {
			return nil, err
		}
		usageRaw, err := playbookMarshal(usage)
		if err != nil {
			return nil, err
		}
		updates := []fileTransactionUpdate{{Path: usagePath, Content: usageRaw, Perm: 0o644}}
		preconditions := []fileTransactionPrecondition{{Path: usagePath, MustNotExist: true}}
		if exists {
			preconditions = append(preconditions, fileTransactionPrecondition{Path: canonical, ExpectedSHA256: fileContentSHA256(currentRaw)})
		} else {
			preconditions = append(preconditions, fileTransactionPrecondition{Path: canonical, MustNotExist: true})
		}
		if !noChange {
			documentRaw, err := playbookMarshal(document)
			if err != nil {
				return nil, err
			}
			revisionPath, err := playbookStorePath(root, id, fmt.Sprintf("revisions/%06d.json", document.Revision))
			if err != nil {
				return nil, err
			}
			markdownPath, err := playbookStorePath(root, id, "PLAYBOOK.md")
			if err != nil {
				return nil, err
			}
			updates = append(updates, fileTransactionUpdate{Path: canonical, Content: documentRaw, Perm: 0o644}, fileTransactionUpdate{Path: revisionPath, Content: documentRaw, Perm: 0o644}, fileTransactionUpdate{Path: markdownPath, Content: []byte(renderPlaybookMarkdown(document)), Perm: 0o644})
			preconditions = append(preconditions, fileTransactionPrecondition{Path: revisionPath, MustNotExist: true})
		}
		indexUpdate, err := playbookDerivedIndexUpdate(root, &document)
		if err != nil {
			return nil, err
		}
		updates = append(updates, indexUpdate)
		ownedPaths := make([]string, 0, len(updates))
		for _, update := range updates {
			ownedPaths = append(ownedPaths, playbookRelativePath(root, update.Path))
		}
		if err := doRegisterPlaybookWrites(root, request.SessionID, ownedPaths); err != nil {
			return nil, err
		}
		sessionCondition, err := playbookSessionPrecondition(root, request.SessionID, true)
		if err != nil {
			return nil, err
		}
		preconditions = append(preconditions, sessionCondition)
		_, err = applyFileTransactionWithVerification(root, "playbook-update", updates, preconditions, func() error {
			currentSources, err := playbookSourceFingerprint(root, request.Definition)
			if err != nil {
				return err
			}
			if !reflect.DeepEqual(currentSources, sources) {
				return fmt.Errorf("playbook_sources_changed_during_update")
			}
			confirmed, err := validateDoSessionForPlaybook(root, request.SessionID, id, baseRevision, request.BaseDigest, digest)
			if err != nil {
				return err
			}
			if confirmed.EvidenceDigest != verification.EvidenceDigest || confirmed.SourceFingerprint != verification.SourceFingerprint || confirmed.DefinitionDigest != verification.DefinitionDigest || confirmed.Outcome != "passed" || !reflect.DeepEqual(confirmed.Sources, verification.Sources) {
				return fmt.Errorf("playbook_session_changed_during_update")
			}
			return nil
		})
		if err != nil {
			return nil, err
		}
		status := "updated"
		if !exists {
			status = "created"
		}
		if noChange {
			status = "no_change"
		}
		paths := make([]string, 0, len(updates))
		for _, update := range updates {
			paths = append(paths, playbookRelativePath(root, update.Path))
		}
		sort.Strings(paths)
		return map[string]any{"status": status, "id": id, "revision": document.Revision, "content_digest": digest, "session_id": request.SessionID, "provenance": "agent_tool_observation", "claim_ready": false, "changed_paths": paths, "show_argv": playbookShowArgv(id, "summary", document.Revision, ""), "knowledge_receipt": playbookKnowledgeReceipt(root, usagePath, usageRaw, id, document.Revision)}, nil
	})
}

func writePlaybookProposal(root string, request PlaybookUpdateRequest, digest string, currentRaw []byte, exists bool) (map[string]any, error) {
	proposal := PlaybookProposal{SchemaVersion: playbookSchemaVersion, ID: request.ID, BaseDigest: request.BaseDigest, DefinitionDigest: digest, Definition: request.Definition, ChangeSummary: request.ChangeSummary, CreatedAt: time.Now().UTC().Format(time.RFC3339Nano)}
	proposalPath, err := playbookStorePath(root, request.ID, "proposals/"+digest+".json")
	if err != nil {
		return nil, err
	}
	if stored, err := readPlaybookProposal(root, request.ID, digest); err == nil {
		if stored.BaseDigest != request.BaseDigest {
			return nil, fmt.Errorf("playbook_proposal_base_changed_revalidate_definition")
		}
		return map[string]any{"status": "proposal_exists", "id": request.ID, "proposal_digest": digest, "changed_paths": []string{}, "show_argv": playbookShowArgv(request.ID, "summary", 0, digest)}, nil
	} else if !os.IsNotExist(err) {
		return nil, err
	}
	raw, err := playbookMarshal(proposal)
	if err != nil {
		return nil, err
	}
	canonical, err := playbookCanonicalPath(root, request.ID)
	if err != nil {
		return nil, err
	}
	preconditions := []fileTransactionPrecondition{{Path: proposalPath, MustNotExist: true}}
	if exists {
		preconditions = append(preconditions, fileTransactionPrecondition{Path: canonical, ExpectedSHA256: fileContentSHA256(currentRaw)})
	} else {
		preconditions = append(preconditions, fileTransactionPrecondition{Path: canonical, MustNotExist: true})
	}
	if request.SessionID != "" {
		if err := doRegisterPlaybookProposalWrites(root, request.SessionID, []string{playbookRelativePath(root, proposalPath)}); err != nil {
			return nil, err
		}
		sessionCondition, err := playbookSessionPrecondition(root, request.SessionID, false)
		if err != nil {
			return nil, err
		}
		preconditions = append(preconditions, sessionCondition)
	}
	_, err = applyFileTransactionWithPreconditions(root, "playbook-proposal", []fileTransactionUpdate{{Path: proposalPath, Content: raw, Perm: 0o644}}, preconditions)
	if err != nil {
		return nil, err
	}
	return map[string]any{"status": "proposed", "id": request.ID, "proposal_digest": digest, "claim_ready": false, "reason": "verified_session_required_before_current_publication", "changed_paths": []string{playbookRelativePath(root, proposalPath)}, "show_argv": playbookShowArgv(request.ID, "summary", 0, digest)}, nil
}

// The metadata owner may have expanded the session since the initial evidence
// check. Bind publication to that exact persisted state under the shared file
// transaction lock so concurrent finish/record cannot silently retarget it.
func playbookSessionPrecondition(root, sessionID string, requirePassed bool) (fileTransactionPrecondition, error) {
	session, digest, err := loadDoSession(root, sessionID)
	if err != nil {
		return fileTransactionPrecondition{}, err
	}
	if session.KnowledgeStatus != "pending" || (requirePassed && session.ExecutionOutcome != "passed") {
		return fileTransactionPrecondition{}, fmt.Errorf("playbook_session_changed_before_publication")
	}
	target, err := secureProjectPath(root, doSessionRef(sessionID))
	if err != nil {
		return fileTransactionPrecondition{}, err
	}
	return fileTransactionPrecondition{Path: target, ExpectedSHA256: digest}, nil
}

func readPlaybookUsage(root, id, sessionID string) (playbookUsage, bool, error) {
	var usage playbookUsage
	if !playbookSafeSessionID(sessionID) {
		return usage, false, fmt.Errorf("playbook_session_id_invalid")
	}
	target, err := playbookStorePath(root, id, "usage/"+sessionID+".json")
	if err != nil {
		return usage, false, err
	}
	raw, err := playbookReadBoundedFile(target)
	if os.IsNotExist(err) {
		return usage, false, nil
	}
	if err != nil {
		return usage, false, err
	}
	if decodePlaybookJSON(raw, &usage) != nil || usage.SchemaVersion != playbookSchemaVersion || usage.PlaybookID != id || usage.SessionID != sessionID || usage.Verification.SessionID != sessionID || usage.DefinitionDigest != usage.Verification.DefinitionDigest || usage.Verification.MethodID != id || usage.Verification.Outcome != "passed" || usage.Revision < 1 {
		return usage, false, fmt.Errorf("playbook_usage_integrity_failed")
	}
	document, err := loadPlaybookRevision(root, id, usage.Revision)
	if err != nil || document.ContentDigest != usage.DefinitionDigest {
		return usage, false, fmt.Errorf("playbook_usage_revision_binding_failed")
	}
	if err := validatePlaybookVerificationInstance(root, document.Definition, usage.Verification); err != nil {
		return usage, false, err
	}
	return usage, true, nil
}

func playbookKnowledgeReceipt(root, target string, raw []byte, id string, revision int) map[string]any {
	return map[string]any{"path": playbookRelativePath(root, target), "sha256": fileContentSHA256(raw), "method_id": id, "revision": revision}
}

func playbookSafeSessionID(value string) bool {
	if value == "" || len(value) > 128 || value == "." || value == ".." {
		return false
	}
	for _, character := range value {
		if !(character >= 'a' && character <= 'z' || character >= 'A' && character <= 'Z' || character >= '0' && character <= '9' || character == '-' || character == '_') {
			return false
		}
	}
	return true
}

func playbookMarshal(value any) ([]byte, error) {
	raw, err := json.MarshalIndent(value, "", "  ")
	if err != nil {
		return nil, fmt.Errorf("playbook_encoding_failed")
	}
	return append(raw, '\n'), nil
}

func playbookRelativePath(root, target string) string {
	absolute, _ := filepath.Abs(root)
	relative, err := filepath.Rel(absolute, target)
	if err != nil {
		return ""
	}
	return filepath.ToSlash(relative)
}

func readPlaybookDocuments(root string) ([]PlaybookDocument, []string, error) {
	storePath, err := secureProjectPath(root, ".specify/playbooks")
	if err != nil {
		return nil, nil, fmt.Errorf("playbook_store_path_unsafe")
	}
	entries, err := os.ReadDir(storePath)
	if os.IsNotExist(err) {
		return []PlaybookDocument{}, []string{}, nil
	}
	if err != nil {
		return nil, nil, err
	}
	if len(entries) > 10000 {
		return nil, nil, fmt.Errorf("playbook_catalog_capacity_exceeded")
	}
	documents := []PlaybookDocument{}
	warnings := []string{}
	for _, entry := range entries {
		if !playbookIDPattern.MatchString(entry.Name()) {
			continue
		}
		if !entry.IsDir() {
			warnings = append(warnings, "playbook_store_entry_unsafe")
			continue
		}
		document, err := loadPlaybookDocument(root, entry.Name())
		if os.IsNotExist(err) {
			continue
		}
		if err != nil {
			warnings = append(warnings, "playbook_document_invalid_excluded")
			continue
		}
		documents = append(documents, document)
	}
	sort.Slice(documents, func(i, j int) bool { return documents[i].ID < documents[j].ID })
	return documents, uniqueSortedTrimmed(warnings), nil
}

func readPlaybookProposal(root, id, digest string) (PlaybookProposal, error) {
	var proposal PlaybookProposal
	if !playbookDigestPattern.MatchString(digest) {
		return proposal, fmt.Errorf("playbook_proposal_digest_invalid")
	}
	target, err := playbookStorePath(root, id, "proposals/"+digest+".json")
	if err != nil {
		return proposal, err
	}
	raw, err := playbookReadBoundedFile(target)
	if err != nil {
		return proposal, err
	}
	if err := decodePlaybookJSON(raw, &proposal); err != nil {
		return proposal, err
	}
	actualDigest, err := playbookDefinitionDigest(proposal.Definition)
	if err != nil || proposal.SchemaVersion != playbookSchemaVersion || proposal.ID != id || playbookID(proposal.Definition) != id || proposal.DefinitionDigest != digest || actualDigest != digest {
		return proposal, fmt.Errorf("playbook_proposal_integrity_failed")
	}
	if proposal.BaseDigest != "" && !playbookDigestPattern.MatchString(proposal.BaseDigest) {
		return proposal, fmt.Errorf("playbook_proposal_base_digest_invalid")
	}
	if err := validatePlaybookDefinition(root, proposal.Definition); err != nil {
		return proposal, err
	}
	if _, err := time.Parse(time.RFC3339Nano, proposal.CreatedAt); err != nil {
		return proposal, fmt.Errorf("playbook_proposal_timestamp_invalid")
	}
	return proposal, nil
}

// A first attempt that could not establish success still leaves a discoverable
// candidate. Current methods always win over their proposals; a corrupt current
// document must not silently fall back to an unverified definition.
func readPlaybookUnpublishedProposals(root string) ([]PlaybookProposal, []string, error) {
	storePath, err := secureProjectPath(root, ".specify/playbooks")
	if err != nil {
		return nil, nil, fmt.Errorf("playbook_store_path_unsafe")
	}
	entries, err := os.ReadDir(storePath)
	if os.IsNotExist(err) {
		return []PlaybookProposal{}, []string{}, nil
	}
	if err != nil {
		return nil, nil, err
	}
	if len(entries) > 10000 {
		return nil, nil, fmt.Errorf("playbook_catalog_capacity_exceeded")
	}
	proposals := []PlaybookProposal{}
	warnings := []string{}
	for _, entry := range entries {
		if !playbookIDPattern.MatchString(entry.Name()) || !entry.IsDir() {
			continue
		}
		canonical, err := playbookCanonicalPath(root, entry.Name())
		if err != nil {
			warnings = append(warnings, "playbook_store_entry_unsafe")
			continue
		}
		if _, err := os.Lstat(canonical); !os.IsNotExist(err) {
			continue
		}
		latest, candidateWarnings := readPlaybookLatestProposal(root, entry.Name(), "")
		warnings = append(warnings, candidateWarnings...)
		if latest.ID != "" {
			proposals = append(proposals, latest)
		}
	}
	return proposals, uniqueSortedTrimmed(warnings), nil
}

func readPlaybookLatestProposal(root, id, baseDigest string) (PlaybookProposal, []string) {
	var latest PlaybookProposal
	directory, err := playbookStorePath(root, id, "proposals")
	if err != nil {
		return latest, []string{"playbook_store_entry_unsafe"}
	}
	candidates, err := os.ReadDir(directory)
	if os.IsNotExist(err) {
		return latest, nil
	}
	if err != nil || len(candidates) > 1000 {
		return latest, []string{"playbook_proposal_catalog_unavailable"}
	}
	warnings := []string{}
	var latestTime time.Time
	for _, candidate := range candidates {
		digest := strings.TrimSuffix(candidate.Name(), ".json")
		if candidate.IsDir() || !strings.HasSuffix(candidate.Name(), ".json") || !playbookDigestPattern.MatchString(digest) {
			continue
		}
		proposal, err := readPlaybookProposal(root, id, digest)
		if err != nil {
			warnings = append(warnings, "playbook_proposal_invalid_excluded")
			continue
		}
		// A proposal based on another revision remains inspectable by its exact
		// digest but cannot silently become the next current-method candidate.
		if proposal.BaseDigest != baseDigest {
			continue
		}
		created, _ := time.Parse(time.RFC3339Nano, proposal.CreatedAt)
		if latest.ID == "" || created.After(latestTime) || (created.Equal(latestTime) && digest < latest.DefinitionDigest) {
			latest, latestTime = proposal, created
		}
	}
	return latest, uniqueSortedTrimmed(warnings)
}

// The compact index and Markdown are derived projections. Reads rebuild the
// catalog in memory from canonical documents; a missing/tampered cache cannot
// hide methods or become an executable authority, and reads never repair files.
func playbookDerivedIndexUpdate(root string, replacement *PlaybookDocument) (fileTransactionUpdate, error) {
	documents, _, err := readPlaybookDocuments(root)
	if err != nil {
		return fileTransactionUpdate{}, err
	}
	entries := []playbookIndexEntry{}
	replaced := false
	for _, document := range documents {
		if replacement != nil && document.ID == replacement.ID {
			document = *replacement
			replaced = true
		}
		entries = append(entries, playbookIndexFromDocument(document))
	}
	if replacement != nil && !replaced {
		entries = append(entries, playbookIndexFromDocument(*replacement))
	}
	sort.Slice(entries, func(i, j int) bool { return entries[i].ID < entries[j].ID })
	raw, err := playbookMarshal(map[string]any{"schema_version": playbookSchemaVersion, "derived": true, "entries": entries})
	if err != nil {
		return fileTransactionUpdate{}, err
	}
	target, err := secureProjectPath(root, ".specify/playbooks/index.json")
	if err != nil {
		return fileTransactionUpdate{}, fmt.Errorf("playbook_store_path_unsafe")
	}
	return fileTransactionUpdate{Path: target, Content: raw, Perm: 0o644}, nil
}

func playbookIndexFromDocument(document PlaybookDocument) playbookIndexEntry {
	definition := document.Definition
	return playbookIndexEntry{ID: document.ID, Revision: document.Revision, ContentDigest: document.ContentDigest, Title: definition.Title, Operation: definition.Operation, Target: definition.Target, Owner: definition.Owner, Variant: definition.Variant, Aliases: definition.Aliases, Applicability: definition.Applicability, SourceFingerprint: document.SourceFingerprint}
}

func renderPlaybookMarkdown(document PlaybookDocument) string {
	var output strings.Builder
	fmt.Fprintf(&output, "# %s\n\n", document.Definition.Title)
	output.WriteString("Generated from playbook.json. Edit through specify-runtime playbook update.\n\n")
	fmt.Fprintf(&output, "- ID: `%s`\n- Revision: `%d`\n- Content digest: `%s`\n- Status: verified in the recorded execution context\n- Evidence provenance: agent_tool_observation; the runtime did not execute these commands\n\n", document.ID, document.Revision, document.ContentDigest)
	fmt.Fprintf(&output, "## Goal\n\n%s\n\n## Applicability\n\n", document.Definition.Goal)
	keys := make([]string, 0, len(document.Definition.Applicability))
	for key := range document.Definition.Applicability {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	for _, key := range keys {
		fmt.Fprintf(&output, "- %s: %s\n", key, strings.Join(document.Definition.Applicability[key], ", "))
	}
	if len(keys) == 0 {
		output.WriteString("No additional environment constraints were recorded. Verify the current project sources before use.\n")
	}
	output.WriteString("\n## Steps\n\n")
	for index, step := range document.Definition.Steps {
		argv, _ := json.Marshal(step.Argv)
		fmt.Fprintf(&output, "### %d. %s\n\n%s\n\n- Working directory: `%s`\n- Required: `%t`\n- Effect: `%s`\n- Argv: `%s`\n- Expected: %s\n\n", index+1, step.ID, step.Purpose, step.Cwd, step.Required, step.SideEffect, string(argv), step.ExpectedResult)
		if len(step.SourceWrites) > 0 {
			fmt.Fprintf(&output, "- Declared source writes: %s\n\n", strings.Join(step.SourceWrites, ", "))
		}
	}
	output.WriteString("## Verification\n\n")
	for _, check := range document.Definition.Checks {
		argv, _ := json.Marshal(check.Argv)
		fmt.Fprintf(&output, "### %s\n\n%s\n\n- Kind: `%s`\n- Required: `%t`\n- Argv: `%s`\n- Result path: `%s`\n- Expected: %s\n\n", check.ID, check.Purpose, check.Kind, check.Required, string(argv), check.ResultPath, check.ExpectedResult)
	}
	output.WriteString("## Source basis\n\n")
	for _, source := range document.Definition.SourceFiles {
		fmt.Fprintf(&output, "- `%s`\n", source)
	}
	fmt.Fprintf(&output, "\n## Evidence\n\nInitial verification session: `%s`. This historical success does not establish a new execution result.\n", document.Verification.SessionID)
	return output.String()
}

func playbookSourceStatus(root string, document PlaybookDocument) string {
	current, err := playbookSourceFingerprint(root, document.Definition)
	if err != nil {
		return "unavailable"
	}
	if reflect.DeepEqual(current, document.SourceFingerprint) {
		return "matched_prior_validation"
	}
	usageDir, err := playbookStorePath(root, document.ID, "usage")
	if err != nil {
		return "changed"
	}
	entries, err := os.ReadDir(usageDir)
	if err != nil {
		return "changed"
	}
	for _, entry := range entries {
		if entry.IsDir() || !strings.HasSuffix(entry.Name(), ".json") {
			continue
		}
		usage, found, err := readPlaybookUsage(root, document.ID, strings.TrimSuffix(entry.Name(), ".json"))
		if err == nil && found && usage.DefinitionDigest == document.ContentDigest && reflect.DeepEqual(current, usage.Verification.Sources) {
			return "matched_prior_validation"
		}
	}
	return "changed"
}
