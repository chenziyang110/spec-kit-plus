package main

import (
	"context"
	"fmt"
	"os"
	"path"
	"time"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runcontrol"
)

// This is an evidence-backed exclusion from one Do operation, not a Work
// ownership claim. Runtime captures the exact current bytes; later changes
// require another explicit inspection rather than inheriting an ignore rule.
type DoExternalChangesInput struct {
	Paths []string `json:"paths"`
}

type DoExternalChangeAudit struct {
	DefinitionEpoch   int               `json:"definition_epoch"`
	DefinitionDigest  string            `json:"definition_digest"`
	SourceFingerprint string            `json:"source_fingerprint"`
	SourceRevision    string            `json:"source_revision"`
	BaselineSHA256    string            `json:"baseline_sha256"`
	PathDigests       map[string]string `json:"path_digests"`
	Recovery          DoRecovery        `json:"recovery"`
	RecordedAt        string            `json:"recorded_at"`
}

func doResumeExternalChanges(root string, session DoSession, oldDigest string, input doResumeInput) (DoSession, error) {
	if input.ExternalChanges == nil || input.AttemptID != "" || input.Replan != nil {
		return session, fmt.Errorf("external_changes is a separate session inspection, not attempt recovery or replan")
	}
	if len(input.ExternalChanges.Paths) == 0 || len(input.ExternalChanges.Paths) > 128 {
		return session, fmt.Errorf("external_changes requires 1 to 128 exact paths")
	}
	sources, fingerprint, sourceRevision, _, err := doCaptureSource(root, session.Definition, session.WriteScope)
	if err != nil {
		return session, err
	}
	changed, err := runcontrol.InspectWorkspaceDelta(context.Background(), root, session.BaselineJSON)
	if err != nil {
		return session, err
	}
	delta := map[string]bool{}
	for _, p := range changed {
		delta[p] = true
	}
	digests := map[string]string{}
	for _, requested := range input.ExternalChanges.Paths {
		p, err := doPath(root, requested, false)
		if err != nil {
			return session, err
		}
		if p != requested || digests[p] != "" || !delta[p] {
			return session, fmt.Errorf("external_changes must list unique canonical current changed paths: %s", requested)
		}
		if doScopeContains(session.WriteScope, p) || doScopeContains(session.OutputScope, p) || doScopeContains(session.MetadataWriteScope, p) || doScopeContains([]string{path.Dir(doSessionRef(session.ID))}, p) || doSourceInputPath(session, sources, p) {
			return session, fmt.Errorf("external_changes cannot exclude operation source, input, output, or metadata: %s", p)
		}
		digest, err := doExternalPathDigest(root, p)
		if err != nil {
			return session, err
		}
		digests[p] = digest
	}
	recovery, extra, err := doPrepareRecovery(root, session, input)
	if err != nil {
		return session, err
	}
	// Replays verify the existing inspection and exact current state as well;
	// a repeated request cannot turn a changed path into an enduring exemption.
	requestDigest := doDigest(input)
	if previous, ok := session.ResumeReceipts[requestDigest]; ok {
		if previous != recovery.EvidenceSHA256 {
			return session, fmt.Errorf("external change inspection evidence changed")
		}
		for _, audit := range session.ExternalChanges {
			if audit.Recovery.EvidenceSHA256 == previous && doDigest(audit.PathDigests) == doDigest(digests) && audit.DefinitionEpoch == doCurrentDefinitionEpoch(session) && audit.DefinitionDigest == session.DefinitionDigest && audit.SourceFingerprint == fingerprint && audit.SourceRevision == sourceRevision && audit.BaselineSHA256 == doBytesDigest([]byte(session.BaselineJSON)) {
				if err := doVerifyRecoveryEvidence(root, audit.Recovery); err != nil {
					return session, err
				}
				return session, nil
			}
		}
		return session, fmt.Errorf("external change inspection is stale; submit fresh evidence")
	}
	if input.ExpectedRevision != session.Revision {
		return session, fmt.Errorf("session revision conflict")
	}
	if len(session.ExternalChanges) >= 128 {
		return session, fmt.Errorf("external change inspection limit reached")
	}
	session, err = doAdoptRecoveredWorkFence(root, session, input.WorkFence, true)
	if err != nil {
		return session, err
	}
	session.ExternalChanges = append(session.ExternalChanges, DoExternalChangeAudit{DefinitionEpoch: doCurrentDefinitionEpoch(session), DefinitionDigest: session.DefinitionDigest, SourceFingerprint: fingerprint, SourceRevision: sourceRevision, BaselineSHA256: doBytesDigest([]byte(session.BaselineJSON)), PathDigests: digests, Recovery: recovery, RecordedAt: doNow()})
	doRememberResume(&session, requestDigest, recovery.EvidenceSHA256)
	session.Validation = nil
	session.Revision++
	session.UpdatedAt = doNow()
	return session, doWriteSession(root, session, oldDigest, extra)
}

// Current and initial inputs are both protected so removing a source from a
// future definition does not silently reclassify its earlier mutation.
func doSourceInputPath(session DoSession, sources map[string]string, p string) bool {
	if doCurrentSourceInputPath(sources, p) {
		return true
	}
	for input := range session.InitialSources {
		if doScopeContains([]string{input}, p) || doScopeContains([]string{p}, input) {
			return true
		}
	}
	for _, attempt := range session.Attempts {
		for _, recorded := range []map[string]string{attempt.Sources, attempt.AfterSources} {
			if doCurrentSourceInputPath(recorded, p) {
				return true
			}
		}
	}
	return false
}

func doCurrentSourceInputPath(sources map[string]string, p string) bool {
	for input := range sources {
		if doScopeContains([]string{input}, p) || doScopeContains([]string{p}, input) {
			return true
		}
	}
	return false
}

func doExternalPathDigest(root, p string) (string, error) {
	target, err := secureProjectPath(root, p)
	if err != nil {
		return "", err
	}
	info, err := os.Lstat(target)
	if os.IsNotExist(err) {
		return "missing", nil
	}
	if err != nil {
		return "", err
	}
	if !info.Mode().IsRegular() || info.Size() > 16*1024*1024 {
		return "", fmt.Errorf("external change inspection requires exact regular files of at most 16 MiB, or a deleted file: %s", p)
	}
	raw, err := secureProjectReadFile(root, p)
	if err != nil {
		return "", err
	}
	after, err := os.Lstat(target)
	if err != nil || !after.Mode().IsRegular() || !after.ModTime().Equal(info.ModTime()) || after.Size() != info.Size() || int64(len(raw)) != info.Size() {
		return "", fmt.Errorf("external changed path changed during inspection: %s", p)
	}
	return doDigest(map[string]any{"bytes": doBytesDigest(raw), "mode": info.Mode().Perm()}), nil
}

func doExternalChangeDisposition(root string, session DoSession, fingerprint, p string) (bool, error) {
	for i := len(session.ExternalChanges) - 1; i >= 0; i-- {
		audit := session.ExternalChanges[i]
		wanted, ok := audit.PathDigests[p]
		if !ok {
			continue
		}
		if audit.DefinitionEpoch != doCurrentDefinitionEpoch(session) || audit.DefinitionDigest != session.DefinitionDigest || audit.SourceFingerprint != fingerprint || audit.BaselineSHA256 != doBytesDigest([]byte(session.BaselineJSON)) {
			return true, fmt.Errorf("external change inspection is stale for the current operation: %s", p)
		}
		if _, err := time.Parse(time.RFC3339Nano, audit.RecordedAt); err != nil {
			return true, fmt.Errorf("external change inspection has no valid recording time: %s", p)
		}
		if err := doVerifyRecoveryEvidence(root, audit.Recovery); err != nil {
			return true, fmt.Errorf("external change inspection evidence: %w", err)
		}
		got, err := doExternalPathDigest(root, p)
		if err != nil || got != wanted {
			return true, fmt.Errorf("external changed path differs from its inspection; inspect again: %s", p)
		}
		return true, nil
	}
	return false, nil
}
