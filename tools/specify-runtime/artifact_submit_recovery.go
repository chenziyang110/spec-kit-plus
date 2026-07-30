package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"strings"
)

const (
	acceptanceRepairJournalFilename = ".human-acceptance-repair.json"
	acceptanceRepairBackupFilename  = ".human-acceptance-repair-backup.json"
)

// SubmitRecoveryBackup is the only file-backed artifact submission route. It
// accepts the runtime-created acceptance repair backup bound by its sibling
// journal; ordinary artifact content must be supplied inline.
func (service *ArtifactService) SubmitRecoveryBackup(leaseID, recoveryFile string) Envelope {
	content, err := service.readAuthorizedRecoveryBackup(leaseID, recoveryFile)
	if err != nil {
		env := NewEnvelope("blocked", "artifact recovery file is not authorized")
		env.Blockers = append(env.Blockers, err.Error())
		env.Blockers = append(env.Blockers, "--recovery-file is reserved for the runtime-created human acceptance repair backup; submit ordinary semantic content inline with --content")
		return env
	}
	env := service.submit(ArtifactSubmitRequest{LeaseID: leaseID, Content: content}, true)
	if env.Status == "ok" {
		env.Data["input_channel"] = "runtime-recovery-backup"
	}
	return env
}

func (service *ArtifactService) readAuthorizedRecoveryBackup(leaseID, recoveryFile string) ([]byte, error) {
	lease, err := service.readLease(strings.TrimSpace(leaseID))
	if err != nil {
		return nil, fmt.Errorf("artifact lease is unavailable: %w", err)
	}
	if lease.Used {
		return nil, fmt.Errorf("artifact lease has already been claimed")
	}
	metadata, ok := LookupArtifactType(lease.CanonicalPath)
	if !ok || metadata.TypeID != "feature-human-acceptance" {
		return nil, fmt.Errorf("recovery submission requires a lease for human-acceptance.json")
	}

	canonicalDir := filepath.Dir(filepath.FromSlash(lease.CanonicalPath))
	expectedRelative := filepath.ToSlash(filepath.Join(canonicalDir, acceptanceRepairBackupFilename))
	expectedPath, err := secureProjectPath(service.projectRoot, expectedRelative)
	if err != nil {
		return nil, fmt.Errorf("resolve expected recovery backup: %w", err)
	}
	providedPath, err := resolveProjectContainedPath(service.projectRoot, recoveryFile)
	if err != nil {
		return nil, fmt.Errorf("recovery file path is invalid: %w", err)
	}
	if !sameArtifactRecoveryPath(providedPath, expectedPath) {
		return nil, fmt.Errorf("recovery file must be the lease target's sibling %s", acceptanceRepairBackupFilename)
	}

	backup, err := readBoundedRecoveryFile(expectedPath, "acceptance repair backup")
	if err != nil {
		return nil, err
	}
	journalRelative := filepath.ToSlash(filepath.Join(canonicalDir, acceptanceRepairJournalFilename))
	journalPath, err := secureProjectPath(service.projectRoot, journalRelative)
	if err != nil {
		return nil, fmt.Errorf("resolve acceptance repair journal: %w", err)
	}
	journalRaw, err := readBoundedRecoveryFile(journalPath, "acceptance repair journal")
	if err != nil {
		return nil, err
	}
	var journal map[string]any
	if err := json.Unmarshal(journalRaw, &journal); err != nil {
		return nil, fmt.Errorf("acceptance repair journal is invalid JSON: %w", err)
	}
	if err := validateAcceptanceRecoveryJournal(journal, backup); err != nil {
		return nil, err
	}
	return backup, nil
}

func readBoundedRecoveryFile(path, label string) ([]byte, error) {
	info, err := os.Stat(path)
	if err != nil {
		return nil, fmt.Errorf("%s is unavailable: %w", label, err)
	}
	if !info.Mode().IsRegular() {
		return nil, fmt.Errorf("%s must be a regular file", label)
	}
	if info.Size() <= 0 || info.Size() > maxAgentJSONInputBytes {
		return nil, fmt.Errorf("%s must contain 1 to %d bytes", label, maxAgentJSONInputBytes)
	}
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("%s is unavailable: %w", label, err)
	}
	return raw, nil
}

func validateAcceptanceRecoveryJournal(journal map[string]any, backup []byte) error {
	version, versionOK := jsonInteger(journal["version"])
	expectedRevision, revisionOK := jsonInteger(journal["expected_revision"])
	phase := artifactRecoveryString(journal["phase"])
	route := artifactRecoveryString(journal["route"])
	findingID := artifactRecoveryString(journal["finding_id"])
	if version != 1 || !versionOK || !revisionOK || expectedRevision < 0 ||
		!oneOfArtifactRecovery(phase, "prepared", "acceptance-invalidated", "workflow-reopened") ||
		!oneOfArtifactRecovery(route, "sp-review", "spx-review") || findingID == "" ||
		artifactRecoveryString(journal["target_stage"]) != "review" ||
		artifactRecoveryString(journal["owning_stage_command"]) != route ||
		artifactRecoveryString(journal["acceptance_file"]) != "human-acceptance.json" ||
		artifactRecoveryString(journal["backup_file"]) != acceptanceRepairBackupFilename ||
		!validArtifactSHA256(artifactRecoveryString(journal["invalidated_acceptance_sha256"])) {
		return fmt.Errorf("acceptance repair journal metadata is invalid")
	}
	expectedDigest := artifactRecoveryString(journal["backup_sha256"])
	actualDigest := fmt.Sprintf("%x", sha256.Sum256(backup))
	if !validArtifactSHA256(expectedDigest) || !strings.EqualFold(expectedDigest, actualDigest) {
		return fmt.Errorf("acceptance repair backup digest does not match its journal")
	}

	var payload map[string]any
	if err := json.Unmarshal(backup, &payload); err != nil {
		return fmt.Errorf("acceptance repair backup is invalid JSON: %w", err)
	}
	status := artifactRecoveryString(payload["status"])
	if status != "rejected" && status != "blocked" {
		return fmt.Errorf("acceptance repair backup must preserve a rejected or blocked state")
	}
	if _, ok := payload["source"].(map[string]any); !ok {
		return fmt.Errorf("acceptance repair backup is missing source metadata")
	}
	if _, ok := payload["overall"].(map[string]any); !ok {
		return fmt.Errorf("acceptance repair backup is missing verdict metadata")
	}
	findings, ok := payload["findings"].([]any)
	if !ok {
		return fmt.Errorf("acceptance repair backup is missing findings")
	}
	for _, item := range findings {
		finding, ok := item.(map[string]any)
		if ok && artifactRecoveryString(finding["id"]) == findingID &&
			artifactRecoveryString(finding["route"]) == route &&
			artifactRecoveryString(finding["status"]) == "open" {
			return nil
		}
	}
	return fmt.Errorf("acceptance repair backup does not preserve the journal's open finding and route")
}

func sameArtifactRecoveryPath(left, right string) bool {
	left = filepath.Clean(left)
	right = filepath.Clean(right)
	if runtime.GOOS == "windows" {
		return strings.EqualFold(left, right)
	}
	return left == right
}

func validArtifactSHA256(value string) bool {
	if len(value) != sha256.Size*2 {
		return false
	}
	decoded, err := hex.DecodeString(value)
	return err == nil && len(decoded) == sha256.Size
}

func artifactRecoveryString(value any) string {
	text, _ := value.(string)
	return strings.TrimSpace(text)
}

func oneOfArtifactRecovery(value string, allowed ...string) bool {
	for _, candidate := range allowed {
		if value == candidate {
			return true
		}
	}
	return false
}
