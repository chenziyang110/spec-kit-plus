package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/filelock"
)

type ArtifactDeleteRequest struct {
	LeaseID string
}

type ArtifactRestoreRequest struct {
	ArchiveID string
}

type artifactArchiveRecord struct {
	ArchiveID     string `json:"archive_id"`
	CanonicalPath string `json:"canonical_path"`
	PayloadName   string `json:"payload_name"`
	SHA256        string `json:"sha256"`
	ArchivedAt    string `json:"archived_at"`
}

func (service *ArtifactService) Delete(request ArtifactDeleteRequest) Envelope {
	lease, claimPath, err := service.claimLease(request.LeaseID)
	if err != nil {
		env := NewEnvelope("blocked", "artifact lease is unavailable")
		env.Blockers = append(env.Blockers, err.Error())
		return env
	}
	metadata, ok := LookupArtifactType(lease.CanonicalPath)
	if !ok || !artifactTypeAllows(metadata, "delete") {
		env := NewEnvelope("invalid", "workflow artifact is not generic-delete writable")
		if ok {
			env.Blockers = append(env.Blockers, fmt.Sprintf("%s may be deleted only through %s", lease.CanonicalPath, metadata.Owner))
			env.Data["owner"] = metadata.Owner
			env.Data["type_id"] = metadata.TypeID
		} else {
			env.Blockers = append(env.Blockers, "the leased path has no registered workflow artifact owner")
		}
		return service.finishLease(lease, claimPath, env)
	}
	target, err := secureProjectPath(service.projectRoot, lease.CanonicalPath)
	if err != nil {
		return service.finishLease(lease, claimPath, artifactDeleteFailure("artifact path safety check failed", err))
	}
	lockPath, err := service.artifactLockPath(lease.CanonicalPath)
	if err != nil {
		return service.finishLease(lease, claimPath, artifactDeleteFailure("artifact lock path safety check failed", err))
	}
	releaseLock, err := filelock.Acquire(lockPath)
	if err != nil {
		return service.finishLease(lease, claimPath, artifactDeleteFailure("failed to acquire artifact write lock", err))
	}
	defer releaseLock()

	target, err = secureProjectPath(service.projectRoot, lease.CanonicalPath)
	if err != nil {
		return service.finishLease(lease, claimPath, artifactDeleteFailure("artifact path safety check failed", err))
	}
	currentExists, currentSHA256, err := snapshotArtifactTarget(target)
	if err != nil {
		return service.finishLease(lease, claimPath, artifactDeleteFailure("artifact target cannot be inspected", err))
	}
	if !currentExists {
		env := NewEnvelope("blocked", "artifact target does not exist")
		env.Blockers = append(env.Blockers, "only an existing artifact can be deleted")
		return service.finishLease(lease, claimPath, env)
	}
	if currentExists != lease.TargetExists || currentSHA256 != lease.TargetSHA256 {
		env := NewEnvelope("blocked", "artifact target changed after lease preparation")
		env.Blockers = append(env.Blockers, "prepare a new lease from the current canonical artifact before deleting")
		env.NextArgv = []string{"specify-runtime", "artifact", "prepare", "--path", lease.CanonicalPath}
		return service.finishLease(lease, claimPath, env)
	}

	archiveDir, err := service.artifactArchiveDir(lease.ID)
	if err != nil {
		return service.finishLease(lease, claimPath, artifactDeleteFailure("artifact archive path safety check failed", err))
	}
	if err := os.MkdirAll(archiveDir, 0o700); err != nil {
		return service.finishLease(lease, claimPath, artifactDeleteFailure("artifact archive directory cannot be created", err))
	}
	archiveDir, err = service.artifactArchiveDir(lease.ID)
	if err != nil {
		return service.finishLease(lease, claimPath, artifactDeleteFailure("artifact archive path safety check failed", err))
	}
	payloadName := "payload" + strings.ToLower(filepath.Ext(lease.CanonicalPath))
	payloadPath := filepath.Join(archiveDir, payloadName)
	metadataPath := filepath.Join(archiveDir, "metadata.json")
	for _, path := range []string{payloadPath, metadataPath} {
		if _, err := os.Lstat(path); err == nil {
			return service.finishLease(lease, claimPath, artifactDeleteFailure("artifact archive target already exists", fmt.Errorf("%s", path)))
		} else if !os.IsNotExist(err) {
			return service.finishLease(lease, claimPath, artifactDeleteFailure("artifact archive target cannot be inspected", err))
		}
	}
	record := artifactArchiveRecord{
		ArchiveID: lease.ID, CanonicalPath: lease.CanonicalPath, PayloadName: payloadName,
		SHA256: currentSHA256, ArchivedAt: nowUTC().Format("2006-01-02T15:04:05Z07:00"),
	}
	raw, err := json.MarshalIndent(record, "", "  ")
	if err != nil {
		return service.finishLease(lease, claimPath, artifactDeleteFailure("artifact archive metadata cannot be encoded", err))
	}
	if err := atomicWriteFile(metadataPath, append(raw, '\n'), 0o600); err != nil {
		return service.finishLease(lease, claimPath, artifactDeleteFailure("artifact archive metadata cannot be written", err))
	}
	if err := os.Rename(target, payloadPath); err != nil {
		_ = os.Remove(metadataPath)
		_ = os.Remove(archiveDir)
		return service.finishLease(lease, claimPath, artifactDeleteFailure("artifact cannot be moved into the recoverable archive", err))
	}

	env := NewEnvelope("ok", "canonical artifact moved to recoverable archive")
	env.Data["archive_id"] = lease.ID
	env.Data["canonical_path"] = lease.CanonicalPath
	env.Data["sha256"] = currentSHA256
	env.NextArgv = []string{"specify-runtime", "artifact", "restore", "--archive", lease.ID}
	return service.finishLease(lease, claimPath, env)
}

func (service *ArtifactService) Restore(request ArtifactRestoreRequest) Envelope {
	archiveID := strings.TrimSpace(request.ArchiveID)
	archiveDir, err := service.artifactArchiveDir(archiveID)
	if err != nil {
		return artifactDeleteFailure("artifact archive id is invalid", err)
	}
	metadataPath := filepath.Join(archiveDir, "metadata.json")
	raw, err := os.ReadFile(metadataPath)
	if err != nil {
		return artifactDeleteFailure("artifact archive metadata is unavailable", err)
	}
	var record artifactArchiveRecord
	if err := json.Unmarshal(raw, &record); err != nil {
		return artifactDeleteFailure("artifact archive metadata is invalid", err)
	}
	if record.ArchiveID != archiveID || record.PayloadName != filepath.Base(record.PayloadName) || record.PayloadName == "." {
		return artifactDeleteFailure("artifact archive metadata is invalid", fmt.Errorf("archive identity or payload name mismatch"))
	}
	canonicalPath, err := registeredArtifactPath(record.CanonicalPath)
	if err != nil || canonicalPath != record.CanonicalPath {
		return artifactDeleteFailure("artifact archive canonical path is invalid", fmt.Errorf("%s", record.CanonicalPath))
	}
	metadata, ok := LookupArtifactType(canonicalPath)
	if !ok || !artifactTypeAllows(metadata, "delete") {
		return artifactDeleteFailure("artifact archive owner no longer permits restore", fmt.Errorf("%s", canonicalPath))
	}
	lockPath, err := service.artifactLockPath(canonicalPath)
	if err != nil {
		return artifactDeleteFailure("artifact lock path safety check failed", err)
	}
	releaseLock, err := filelock.Acquire(lockPath)
	if err != nil {
		return artifactDeleteFailure("failed to acquire artifact write lock", err)
	}
	defer releaseLock()

	target, err := secureProjectPath(service.projectRoot, canonicalPath)
	if err != nil {
		return artifactDeleteFailure("artifact path safety check failed", err)
	}
	if exists, _, err := snapshotArtifactTarget(target); err != nil {
		return artifactDeleteFailure("artifact target cannot be inspected", err)
	} else if exists {
		env := NewEnvelope("blocked", "artifact restore target already exists")
		env.Blockers = append(env.Blockers, "delete or reconcile the current canonical artifact through its owner before restoring")
		return env
	}
	payloadPath := filepath.Join(archiveDir, record.PayloadName)
	info, err := os.Lstat(payloadPath)
	if err != nil {
		return artifactDeleteFailure("artifact archive payload is unavailable", err)
	}
	if info.Mode()&os.ModeSymlink != 0 || !info.Mode().IsRegular() {
		return artifactDeleteFailure("artifact archive payload is invalid", fmt.Errorf("payload must be a regular non-symlink file"))
	}
	_, payloadSHA256, err := snapshotArtifactTarget(payloadPath)
	if err != nil || payloadSHA256 != record.SHA256 {
		if err == nil {
			err = fmt.Errorf("archive payload sha256 mismatch")
		}
		return artifactDeleteFailure("artifact archive payload failed integrity validation", err)
	}
	if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil {
		return artifactDeleteFailure("artifact parent directory cannot be created", err)
	}
	target, err = secureProjectPath(service.projectRoot, canonicalPath)
	if err != nil {
		return artifactDeleteFailure("artifact path safety check failed", err)
	}
	if err := os.Rename(payloadPath, target); err != nil {
		return artifactDeleteFailure("artifact archive payload cannot be restored", err)
	}
	env := NewEnvelope("ok", "canonical artifact restored from recoverable archive")
	env.Data["archive_id"] = archiveID
	env.Data["canonical_path"] = canonicalPath
	env.Data["sha256"] = record.SHA256
	env.ShowArgv = []string{"specify-runtime", "artifact", "show", "--path", canonicalPath, "--view", "summary"}
	return env
}

func (service *ArtifactService) artifactArchiveDir(archiveID string) (string, error) {
	if !safeSegment(archiveID) {
		return "", fmt.Errorf("archive id %q must be a safe path segment", archiveID)
	}
	return secureProjectPath(service.projectRoot, filepath.ToSlash(filepath.Join(".specify", "runtime", "artifact-trash", archiveID)))
}

func artifactDeleteFailure(summary string, err error) Envelope {
	env := NewEnvelope("blocked", summary)
	env.Blockers = append(env.Blockers, err.Error())
	return env
}
