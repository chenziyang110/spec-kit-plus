package main

import (
	"context"
	"fmt"
	"path/filepath"
	"strings"
	"time"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runcontrol"
)

func doBlockFinish(root string, session DoSession, digest string, input doFinishInput) (DoSession, error) {
	blocker := *input.Blocker
	if input.Knowledge != nil || input.KnowledgeStatus != "" && input.KnowledgeStatus != "pending" {
		return session, fmt.Errorf("blocked exit cannot publish successful knowledge")
	}
	if len(blocker.EvidenceDigests) != 0 {
		return session, fmt.Errorf("blocker evidence digests are runtime-owned")
	}
	if session.Blocker != nil {
		previous := *session.Blocker
		previous.EvidenceDigests = nil
		if doDigest(previous) == doDigest(blocker) {
			return session, doEnsureBlockedWork(root, session)
		}
		return session, fmt.Errorf("preserve the current blocker; resolve it with fresh evidence before replacing it")
	}
	if input.ExpectedRevision != session.Revision {
		return session, fmt.Errorf("session revision conflict")
	}
	if session.KnowledgeStatus == "saved" || session.KnowledgeStatus == "not_applicable" {
		return session, fmt.Errorf("completed operation cannot acquire a retroactive blocker")
	}
	if blocker.Owner != "human" && blocker.Owner != "external" {
		return session, fmt.Errorf("agent-owned failures must use active recovery rather than a terminal blocked exit")
	}
	for _, value := range []string{blocker.Category, blocker.Cause, blocker.NextAction, blocker.UnblockCriteria, blocker.ResumePoint} {
		if strings.TrimSpace(value) == "" || len(value) > 4096 {
			return session, fmt.Errorf("blocked exit requires bounded category, cause, next action, unblock criteria, and resume point")
		}
	}
	if len(blocker.AttemptedRecovery) == 0 || len(blocker.AttemptedRecovery) > 16 || len(blocker.EvidenceRefs) == 0 || len(blocker.EvidenceRefs) > 16 {
		return session, fmt.Errorf("blocked exit requires bounded attempted recovery and actual evidence refs")
	}
	blocker.EvidenceDigests = map[string]string{}
	for _, ref := range blocker.EvidenceRefs {
		p, err := doPath(root, ref, false)
		if err != nil {
			return session, err
		}
		if !doScopeContains(session.OutputScope, p) && !doScopeContains(session.WriteScope, p) {
			return session, fmt.Errorf("blocker evidence is outside the declared operation scope")
		}
		raw, err := secureProjectReadFile(root, p)
		if err != nil {
			return session, err
		}
		if len(raw) == 0 || len(raw) > 2*1024*1024 {
			return session, fmt.Errorf("blocker evidence must be nonempty and bounded")
		}
		blocker.EvidenceDigests[p] = doBytesDigest(raw)
	}
	if err := doRequireWork(root, session); err != nil {
		return session, err
	}
	session.Blocker = &blocker
	session.Revision++
	session.UpdatedAt = doNow()
	if err := doWriteSession(root, session, digest, nil); err != nil {
		return session, err
	}
	return session, doEnsureBlockedWork(root, session)
}

func doEnsureBlockedWork(root string, session DoSession) error {
	store, err := runcontrol.OpenForRepository(context.Background(), root)
	if err != nil {
		return err
	}
	defer store.Close()
	work, _, err := store.GetWork(context.Background(), session.WorkID)
	if err != nil {
		return err
	}
	if session.Blocker == nil || work.Fence != session.WorkFence || work.TaskRef != "do:"+session.ID {
		return fmt.Errorf("blocked Work identity or fence changed; recover the actual owner")
	}
	if work.Status == runcontrol.WorkBlocked {
		return nil
	}
	_, err = store.TransitionWork(context.Background(), runcontrol.TransitionWorkParams{WorkID: work.WorkID, ExpectedRevision: work.Revision, Fence: session.WorkFence, Target: runcontrol.WorkBlocked, Reason: session.Blocker.Cause, NextAction: session.Blocker.NextAction})
	return err
}

func doResolveBlocker(root string, session DoSession, digest string, input doResumeInput) (DoSession, error) {
	if input.ExpectedRevision != session.Revision {
		return session, fmt.Errorf("session revision conflict")
	}
	recovery, err := doReadRecovery(root, session, input.Recovery)
	if err != nil {
		return session, err
	}
	for _, previous := range session.Blocker.EvidenceDigests {
		if previous == recovery.EvidenceSHA256 {
			return session, fmt.Errorf("unchanged failure evidence does not resolve the blocker")
		}
	}
	session, err = doAdoptRecoveredWorkFence(root, session, input.WorkFence, true)
	if err != nil {
		return session, err
	}
	store, err := runcontrol.OpenForRepository(context.Background(), root)
	if err != nil {
		return session, err
	}
	defer store.Close()
	work, _, err := store.GetWork(context.Background(), session.WorkID)
	if err != nil {
		return session, err
	}
	if work.TaskRef != "do:"+session.ID || work.Fence != session.WorkFence {
		return session, fmt.Errorf("blocked Work identity or fence changed; recover the actual owner")
	}
	if work.Status == runcontrol.WorkBlocked {
		if _, err = store.TransitionWork(context.Background(), runcontrol.TransitionWorkParams{WorkID: work.WorkID, ExpectedRevision: work.Revision, Fence: session.WorkFence, Target: runcontrol.WorkActive, Reason: input.Recovery.Reason, NextAction: "resume the exact interrupted operation gate"}); err != nil {
			return session, err
		}
	} else if work.Status != runcontrol.WorkActive {
		return session, fmt.Errorf("interrupted ownership requires Work recovery before session recovery")
	}
	session.BlockerHistory = append(session.BlockerHistory, *session.Blocker)
	session.Blocker = nil
	doRememberResume(&session, doDigest(input), recovery.EvidenceSHA256)
	session.Revision++
	session.UpdatedAt = doNow()
	return session, doWriteSession(root, session, digest, nil)
}

func doReadRecovery(root string, session DoSession, recovery DoRecovery) (DoRecovery, error) {
	if strings.TrimSpace(recovery.Reason) == "" || len(recovery.Reason) > 4096 || !recovery.ProcessesStopped || !recovery.SideEffectsInspected {
		return recovery, fmt.Errorf("recovery requires inspected side effects, stopped prior processes, and a bounded concrete reason")
	}
	if recovery.EvidenceSHA256 != "" {
		return recovery, fmt.Errorf("recovery evidence_sha256 is runtime-owned")
	}
	p, err := doPath(root, recovery.EvidenceRef, false)
	if err != nil {
		return recovery, err
	}
	if !doScopeContains(session.OutputScope, p) && !doScopeContains(session.WriteScope, p) {
		return recovery, fmt.Errorf("recovery evidence is outside the declared scope")
	}
	raw, err := secureProjectReadFile(root, p)
	if err != nil {
		return recovery, err
	}
	if len(raw) == 0 || len(raw) > 2*1024*1024 {
		return recovery, fmt.Errorf("recovery evidence must be nonempty and bounded")
	}
	recovery.EvidenceRef = p
	recovery.EvidenceSHA256 = doBytesDigest(raw)
	return recovery, nil
}

func doRememberResume(session *DoSession, requestDigest, evidenceDigest string) {
	if session.ResumeReceipts == nil {
		session.ResumeReceipts = map[string]string{}
	}
	session.ResumeReceipts[requestDigest] = evidenceDigest
}

// A resumed Work already carries the owner's new fence. Rebinding requires that
// explicit token; simply reading a newer fence never renews a stale Do owner.
func doAdoptRecoveredWorkFence(root string, session DoSession, requestedFence int64, allowBlocked bool) (DoSession, error) {
	store, err := runcontrol.OpenForRepository(context.Background(), root)
	if err != nil {
		return session, err
	}
	defer store.Close()
	work, _, err := store.GetWork(context.Background(), session.WorkID)
	if err != nil {
		return session, err
	}
	workspace, err := filepath.Abs(root)
	if err != nil || filepath.Clean(work.WorkspaceRoot) != filepath.Clean(workspace) || work.TaskRef != "do:"+session.ID {
		return session, fmt.Errorf("Work recovery belongs to a different operation or workspace")
	}
	if requestedFence != 0 {
		if requestedFence < session.WorkFence || requestedFence != work.Fence || work.Status != runcontrol.WorkActive {
			return session, fmt.Errorf("work_fence must match an already active recovered Work owner")
		}
		session.WorkFence = requestedFence
	}
	if work.Fence != session.WorkFence || (work.Status != runcontrol.WorkActive && !(allowBlocked && work.Status == runcontrol.WorkBlocked)) {
		return session, fmt.Errorf("complete Work recovery, then pass its explicit work_fence to do resume")
	}
	_, err = store.RenewWorkLease(context.Background(), runcontrol.RenewWorkLeaseParams{WorkID: work.WorkID, Fence: work.Fence, LeaseUntil: time.Now().UTC().Add(30 * time.Minute)})
	return session, err
}
