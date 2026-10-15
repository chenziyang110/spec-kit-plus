package main

import (
	"context"
	"encoding/json"
	"fmt"
	"path"
	"path/filepath"
	"strings"
	"time"
	"unicode/utf8"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runcontrol"
)

const doRecoveryTextLimit = 64 * 1024

// Presence matters for the input oneOf: an explicit empty/null field is not
// omission. Keep this on the request boundary, not persisted DoRecovery, whose
// normalized file reference and runtime-owned digest remain backward compatible.
func (input *doResumeInput) UnmarshalJSON(raw []byte) error {
	type plain doResumeInput
	var value plain
	if err := decodePlaybookJSON(raw, &value); err != nil {
		return err
	}
	var fields map[string]json.RawMessage
	if err := json.Unmarshal(raw, &fields); err != nil {
		return err
	}
	if value.Replan != nil && value.Replan.Mode == "unstarted" {
		_, hasAttempt := fields["attempt_id"]
		if _, present := fields["recovery"]; present || hasAttempt {
			return fmt.Errorf("unstarted replan does not fabricate failed-attempt recovery")
		}
		*input = doResumeInput(value)
		return nil
	}
	var recovery map[string]json.RawMessage
	if err := json.Unmarshal(fields["recovery"], &recovery); err != nil {
		return err
	}
	_, hasRef := recovery["evidence_ref"]
	_, hasText := recovery["evidence_text"]
	if hasRef == hasText {
		return fmt.Errorf("recovery requires exactly one of evidence_ref or evidence_text")
	}
	if (hasRef && value.Recovery.EvidenceRef == "") || (hasText && value.Recovery.EvidenceText == "") {
		return fmt.Errorf("recovery evidence must be a nonempty string, not null")
	}
	*input = doResumeInput(value)
	return nil
}

func (input doResumeInput) MarshalJSON() ([]byte, error) {
	if input.Replan != nil && input.Replan.Mode == "unstarted" && input.AttemptID == "" && input.Recovery == (DoRecovery{}) {
		value := map[string]any{"expected_revision": input.ExpectedRevision, "replan": input.Replan}
		if input.WorkFence != 0 {
			value["work_fence"] = input.WorkFence
		}
		return json.Marshal(value)
	}
	type plain doResumeInput
	return json.Marshal(plain(input))
}

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
	recovery, extra, err := doPrepareRecovery(root, session, input)
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
	return session, doWriteSession(root, session, digest, extra)
}

// Inline evidence is owned by the Work's already claimed session directory.
// Bind its immutable filename to the complete request so exact replay reads
// the same bytes without accepting a caller-selected metadata write path.
func doRecoveryEvidenceRef(session DoSession, input doResumeInput) string {
	if input.Recovery.EvidenceText != "" {
		return path.Join(path.Dir(doSessionRef(session.ID)), "evidence", "recovery-"+doDigest(input)+".txt")
	}
	return input.Recovery.EvidenceRef
}

// Prepare immutable evidence without writing. The owner/fence checks and the
// session CAS must succeed before doWriteSession commits these bytes together
// with the recovery receipt (and definition epochs when replanning).
func doPrepareRecovery(root string, session DoSession, input doResumeInput) (DoRecovery, []fileTransactionUpdate, error) {
	recovery := input.Recovery
	if strings.TrimSpace(recovery.Reason) == "" || len(recovery.Reason) > 4096 || !recovery.SideEffectsInspected {
		return recovery, nil, fmt.Errorf("recovery requires inspected side effects and a bounded concrete reason")
	}
	if err := doRecoveryMatchesOperation(session, input); err != nil {
		return recovery, nil, err
	}
	if recovery.EvidenceSHA256 != "" {
		return recovery, nil, fmt.Errorf("recovery evidence_sha256 is runtime-owned")
	}
	if (recovery.EvidenceRef == "") == (recovery.EvidenceText == "") {
		return recovery, nil, fmt.Errorf("recovery requires exactly one of evidence_ref or evidence_text")
	}
	if recovery.EvidenceText != "" {
		if strings.TrimSpace(recovery.EvidenceText) == "" || len(recovery.EvidenceText) > doRecoveryTextLimit || !utf8.ValidString(recovery.EvidenceText) {
			return recovery, nil, fmt.Errorf("recovery evidence_text must be nonempty UTF-8 and at most 64 KiB")
		}
		ref := doRecoveryEvidenceRef(session, input)
		target, err := secureProjectPath(root, ref)
		if err != nil {
			return recovery, nil, err
		}
		raw := []byte(recovery.EvidenceText)
		if recovery.NativeActionSettled {
			if err := doNativeSensitiveCheck(root, map[string]string{"reason": recovery.Reason, "evidence": recovery.EvidenceText}); err != nil {
				return recovery, nil, err
			}
		}
		recovery.EvidenceText = "" // Persist one immutable snapshot, not duplicate text in session history.
		recovery.EvidenceRef = ref
		recovery.EvidenceSHA256 = doBytesDigest(raw)
		return recovery, []fileTransactionUpdate{{Path: target, Content: raw, Perm: 0o600}}, nil
	}
	p, err := doPath(root, recovery.EvidenceRef, false)
	if err != nil {
		return recovery, nil, err
	}
	if !doScopeContains(session.OutputScope, p) && !doScopeContains(session.WriteScope, p) {
		return recovery, nil, fmt.Errorf("recovery evidence is outside the declared scope")
	}
	raw, err := secureProjectReadFile(root, p)
	if err != nil {
		return recovery, nil, err
	}
	if len(raw) == 0 || len(raw) > 2*1024*1024 {
		return recovery, nil, fmt.Errorf("recovery evidence must be nonempty and bounded")
	}
	recovery.EvidenceRef = p
	recovery.EvidenceSHA256 = doBytesDigest(raw)
	return recovery, nil, nil
}

func doRememberResume(session *DoSession, requestDigest, evidenceDigest string) {
	if session.ResumeReceipts == nil {
		session.ResumeReceipts = map[string]string{}
	}
	session.ResumeReceipts[requestDigest] = evidenceDigest
}

func doVerifyRecoveryEvidence(root string, recovery DoRecovery) error {
	if strings.TrimSpace(recovery.Reason) == "" || (!recovery.ProcessesStopped && !recovery.NativeActionSettled) || !recovery.SideEffectsInspected || recovery.EvidenceText != "" || recovery.EvidenceRef == "" || !playbookDigestPattern.MatchString(recovery.EvidenceSHA256) {
		return fmt.Errorf("recovery lacks its completed action/effect inspection and bound evidence")
	}
	raw, err := secureProjectReadFile(root, recovery.EvidenceRef)
	if err != nil || len(raw) == 0 || len(raw) > 2*1024*1024 || doBytesDigest(raw) != recovery.EvidenceSHA256 {
		return fmt.Errorf("inspection record is missing or changed")
	}
	return nil
}

func doRecoveryMatchesAttempt(attempt DoAttempt, recovery DoRecovery) error {
	if attempt.NativeAction != nil {
		if !recovery.NativeActionSettled {
			return fmt.Errorf("native recovery requires native_action_settled after inspecting the actual tool operation")
		}
	} else if !recovery.ProcessesStopped {
		return fmt.Errorf("process recovery requires stopped prior processes")
	}
	return nil
}

func doRecoveryMatchesOperation(session DoSession, input doResumeInput) error {
	if input.AttemptID != "" {
		for _, attempt := range session.Attempts {
			if attempt.ID == input.AttemptID {
				return doRecoveryMatchesAttempt(attempt, input.Recovery)
			}
		}
		return fmt.Errorf("recovery attempt does not belong to this session")
	}
	// Work/blocker recovery is session-wide. Mixed procedures must reconcile
	// both kinds of in-flight effects; a native flag cannot excuse a process.
	for _, step := range session.Definition.Steps {
		if err := doRecoveryMatchesAttempt(DoAttempt{NativeAction: step.NativeAction}, input.Recovery); err != nil {
			return err
		}
	}
	for _, check := range session.Definition.Checks {
		if err := doRecoveryMatchesAttempt(DoAttempt{NativeAction: check.NativeAction}, input.Recovery); err != nil {
			return err
		}
	}
	return nil
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
