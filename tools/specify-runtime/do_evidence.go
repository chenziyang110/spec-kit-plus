package main

import (
	"bytes"
	"context"
	"encoding/json"
	"encoding/xml"
	"fmt"
	"io"
	"os"
	"path"
	"path/filepath"
	"reflect"
	"runtime"
	"sort"
	"strconv"
	"strings"
	"time"

	cognitionquery "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/query"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runcontrol"
	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
)

type doAction struct {
	id, kind, cwd      string
	argv, dependencies []string
	sourceWrites       []string
	required           bool
	check              *PlaybookCheck
	nativeAction       *PlaybookNativeAction
}

func doFindAction(session DoSession, kind, id string) (doAction, error) {
	if kind == "step" {
		for _, step := range session.Definition.Steps {
			if step.ID == id {
				return doAction{id: id, kind: kind, cwd: step.Cwd, argv: step.Argv, dependencies: step.DependsOn, sourceWrites: step.SourceWrites, required: step.Required, nativeAction: step.NativeAction}, nil
			}
		}
	}
	if kind == "check" {
		for _, check := range session.Definition.Checks {
			if check.ID == id {
				c := check
				return doAction{id: id, kind: kind, cwd: c.Cwd, argv: c.Argv, dependencies: c.DependsOn, required: c.Required, check: &c, nativeAction: c.NativeAction}, nil
			}
		}
	}
	return doAction{}, fmt.Errorf("unknown %s id %q", kind, id)
}

func doLatestAttempts(session DoSession) map[string]DoAttempt {
	result := map[string]DoAttempt{}
	for _, a := range session.Attempts {
		if !doAttemptInCurrentDefinition(session, a) && !doRetainedAttempt(session, a) {
			continue
		}
		result[a.TargetID] = a
	}
	return result
}

func doApplyRecordEvent(root string, session DoSession, event doRecordEvent, preexisting map[string]bool) (DoSession, []fileTransactionUpdate, error) {
	if !doIDPattern.MatchString(event.AttemptID) {
		return session, nil, fmt.Errorf("invalid attempt_id")
	}
	action, err := doFindAction(session, event.Kind, event.TargetID)
	if err != nil {
		return session, nil, err
	}
	index := -1
	for i, a := range session.Attempts {
		if a.ID == event.AttemptID {
			index = i
			break
		}
	}
	if event.Event == "started" {
		if index >= 0 {
			return session, nil, fmt.Errorf("attempt already exists")
		}
		if event.Status != "" || event.ToolCallID != "" || event.ExitCode != nil || len(event.ResultRefs) > 0 || event.NativeObservation != nil || event.NativeAction != nil {
			return session, nil, fmt.Errorf("started registers intent only; record observations after actual execution")
		}
		latest := doLatestAttempts(session)
		if previous, ok := latest[action.id]; ok {
			if err := doRetryRecoveryReady(root, previous); err != nil {
				return session, nil, err
			}
			if previous.Status == "running" || (previous.Status == "interrupted" && previous.Recovery == nil) {
				return session, nil, fmt.Errorf("inspect prior process and side effects through do resume before retry")
			}
			if previous.Status == "failed" && previous.Recovery == nil {
				return session, nil, fmt.Errorf("failed attempt needs evidence-backed repair before retry")
			}
		}
		for _, dependency := range action.dependencies {
			previous, ok := latest[dependency]
			if !ok || previous.Status != "passed" {
				return session, nil, fmt.Errorf("dependency %s has not passed", dependency)
			}
		}
		sources, fingerprint, revision, dirty, err := doCaptureSource(root, session.Definition, session.WriteScope)
		if err != nil {
			return session, nil, err
		}
		dependencyAttempts := map[string]string{}
		for _, dependency := range action.dependencies {
			if doAttemptResultFingerprint(latest[dependency]) != fingerprint {
				return session, nil, fmt.Errorf("dependency %s evidence is stale for the current source", dependency)
			}
			if err := doDependencyReady(root, session, latest, dependency, fingerprint); err != nil {
				return session, nil, err
			}
			dependencyAttempts[dependency] = latest[dependency].ID
		}
		session.Attempts = append(session.Attempts, DoAttempt{ID: event.AttemptID, TargetID: event.TargetID, Kind: event.Kind, Status: "running", DefinitionDigest: session.DefinitionDigest, DefinitionEpoch: doCurrentDefinitionEpoch(session), SourceFingerprint: fingerprint, Sources: sources, SourceRevision: revision, DirtyPaths: dirty, RegisteredAt: doNow(), DependencyAttempts: dependencyAttempts, Argv: append([]string{}, action.argv...), Cwd: action.cwd, NativeAction: normalizePlaybookNativeAction(action.nativeAction)})
		session.ExecutionOutcome = "pending"
		return session, nil, nil
	}
	if event.Event != "completed" {
		return session, nil, fmt.Errorf("event must be started or completed")
	}
	if index < 0 || !preexisting[event.AttemptID] {
		return session, nil, fmt.Errorf("a started checkpoint from an earlier record is required before recording completion")
	}
	attempt := session.Attempts[index]
	if attempt.Kind != event.Kind || attempt.TargetID != event.TargetID || !doAttemptInCurrentDefinition(session, attempt) {
		return session, nil, fmt.Errorf("completion must match the exact started action and definition epoch")
	}
	if attempt.Status != "running" {
		return session, nil, fmt.Errorf("attempt is already terminal; retain it and start a new attempt")
	}
	if event.EvidenceOrigin != "agent_tool_observation" || strings.TrimSpace(event.ToolCallID) == "" {
		return session, nil, fmt.Errorf("native tool observation origin and tool_call_id are required; runtime does not execute the command")
	}
	if len(event.ToolCallID) > 512 || len(event.Summary) > 4096 {
		return session, nil, fmt.Errorf("observation metadata exceeds limits")
	}
	if !reflect.DeepEqual(event.Argv, attempt.Argv) && !(len(event.Argv) == 0 && len(attempt.Argv) == 0) {
		return session, nil, fmt.Errorf("observed argv differs from the frozen action")
	}
	if action.nativeAction == nil {
		if strings.TrimSpace(event.Cwd) == "" {
			return session, nil, fmt.Errorf("observed cwd is required")
		}
		cwd, err := doPath(root, event.Cwd, true)
		if err != nil || cwd != path.Clean(attempt.Cwd) {
			return session, nil, fmt.Errorf("observed cwd differs from the frozen action")
		}
	}
	started, err := time.Parse(time.RFC3339Nano, event.StartedAt)
	if err != nil {
		return session, nil, fmt.Errorf("started_at must be RFC3339")
	}
	finished, err := time.Parse(time.RFC3339Nano, event.FinishedAt)
	if err != nil {
		return session, nil, fmt.Errorf("finished_at must be RFC3339")
	}
	registered, _ := time.Parse(time.RFC3339Nano, attempt.RegisteredAt)
	evidenceBoundary := registered
	if action.check != nil {
		latest := doLatestAttempts(session)
		for _, dependency := range action.dependencies {
			if prior, ok := latest[dependency]; ok && prior.Status == "passed" && doAttemptResultFingerprint(prior) == attempt.SourceFingerprint {
				producerStart, e := time.Parse(time.RFC3339Nano, prior.RegisteredAt)
				if e == nil && producerStart.Before(evidenceBoundary) {
					evidenceBoundary = producerStart
				}
			}
		}
	}
	if started.Before(registered.Add(-2*time.Second)) || finished.Before(started) || finished.After(time.Now().UTC().Add(2*time.Second)) {
		return session, nil, fmt.Errorf("observation times are outside the registered attempt")
	}
	if event.Status != "passed" && event.Status != "failed" && event.Status != "interrupted" {
		return session, nil, fmt.Errorf("status must be passed, failed, or interrupted")
	}
	if (event.TimedOut || event.Cancelled) && event.Status != "interrupted" {
		return session, nil, fmt.Errorf("timeout or cancellation is interrupted, never pass/fail")
	}
	if event.Status != "interrupted" && len(action.argv) > 0 && event.ExitCode == nil {
		return session, nil, fmt.Errorf("completed command observation requires actual exit_code")
	}
	if event.Status == "passed" && event.ExitCode != nil && *event.ExitCode != 0 {
		return session, nil, fmt.Errorf("nonzero command exit cannot be passed")
	}
	nativeRef, nativeDigest, nativeUpdates, err := doPrepareNativeObservation(root, session, action, attempt, event)
	if err != nil {
		return session, nil, err
	}
	afterSources, fingerprint, afterRevision, afterDirty, err := doCaptureSource(root, session.Definition, session.WriteScope)
	if err != nil {
		return session, nil, err
	}
	changedSources := doChangedSourceFiles(attempt.Sources, afterSources)
	if event.Status == "passed" && fingerprint != attempt.SourceFingerprint {
		if len(action.sourceWrites) == 0 || action.kind != "step" || afterRevision != attempt.SourceRevision {
			return session, nil, fmt.Errorf("source changed during a nonmutating attempt; use an explicitly scoped source-writing step and run final checks")
		}
		for _, p := range changedSources {
			if !doScopeContains(action.sourceWrites, p) || !doScopeContains(session.WriteScope, p) {
				return session, nil, fmt.Errorf("actual source change %s is outside this step's frozen source_writes", p)
			}
		}
	}
	if event.Status == "passed" {
		latest := doLatestAttempts(session)
		for _, dependency := range action.dependencies {
			prior, ok := latest[dependency]
			if !ok || prior.Status != "passed" || attempt.DependencyAttempts[dependency] != prior.ID || doAttemptResultFingerprint(prior) != attempt.SourceFingerprint {
				return session, nil, fmt.Errorf("dependency %s changed after this attempt started; validate the new producer result", dependency)
			}
		}
	}
	if len(event.ResultRefs) > 16 {
		return session, nil, fmt.Errorf("too many evidence files")
	}
	results := []DoResultRef{}
	updates := append([]fileTransactionUpdate{}, nativeUpdates...)
	for n, ref := range event.ResultRefs {
		if ref.SnapshotRef != "" || ref.SnapshotSHA256 != "" || ref.Size != 0 {
			return session, nil, fmt.Errorf("snapshot_ref, snapshot_sha256, and size are runtime-owned")
		}
		p, err := doPath(root, ref.Path, false)
		if err != nil {
			return session, nil, err
		}
		if !doScopeContains(session.OutputScope, p) && !doScopeContains(session.WriteScope, p) {
			return session, nil, fmt.Errorf("evidence path is outside declared output/write scope")
		}
		if ref.Kind != "file" && ref.Kind != "json" && ref.Kind != "junit" && ref.Kind != "log" {
			return session, nil, fmt.Errorf("unsupported result kind")
		}
		target, err := secureProjectPath(root, p)
		if err != nil {
			return session, nil, err
		}
		info, err := os.Stat(target)
		if err != nil {
			return session, nil, err
		}
		limit := int64(2 * 1024 * 1024)
		if ref.Kind == "file" {
			limit = doArtifactSizeLimit
		}
		if !info.Mode().IsRegular() || info.Size() == 0 || info.Size() > limit {
			return session, nil, fmt.Errorf("evidence must be a nonempty regular file; reports/logs are limited to 2 MiB and file artifacts to 2 GiB")
		}
		if event.Status == "passed" && info.ModTime().Before(evidenceBoundary.Add(-2*time.Second)) {
			return session, nil, fmt.Errorf("evidence file predates this attempt")
		}
		var raw []byte
		var digest string
		if ref.Kind == "file" {
			digest, _, err = doHashArtifact(root, p)
			if err == nil {
				raw, err = json.Marshal(doFileArtifactReceipt{SchemaVersion: doFileArtifactSchema, Path: p, SHA256: digest, Size: info.Size()})
			}
		} else {
			raw, err = os.ReadFile(target)
			digest = doBytesDigest(raw)
		}
		if err != nil {
			return session, nil, err
		}
		if ref.SHA256 != "" && ref.SHA256 != digest {
			return session, nil, fmt.Errorf("observed result digest mismatch")
		}
		snapshotRef := path.Join(path.Dir(doSessionRef(session.ID)), "evidence", event.AttemptID+"-"+strconv.Itoa(n)+".bin")
		snapshotPath, err := secureProjectPath(root, snapshotRef)
		if err != nil {
			return session, nil, err
		}
		results = append(results, DoResultRef{Path: p, Kind: ref.Kind, SHA256: digest, SnapshotRef: snapshotRef, SnapshotSHA256: doBytesDigest(raw), Size: info.Size()})
		updates = append(updates, fileTransactionUpdate{Path: snapshotPath, Content: raw, Perm: 0o600})
	}
	if action.check != nil && action.check.Kind != "observation" && event.Status == "passed" {
		if err := doCheckEvidence(root, *action.check, results, false); err != nil {
			return session, nil, err
		}
	}
	attempt.Status = event.Status
	attempt.EvidenceOrigin = event.EvidenceOrigin
	attempt.ToolCallID = event.ToolCallID
	attempt.StartedAt = event.StartedAt
	attempt.FinishedAt = event.FinishedAt
	attempt.ElapsedMS = finished.Sub(started).Milliseconds()
	attempt.ExitCode = event.ExitCode
	attempt.TimedOut = event.TimedOut
	attempt.Cancelled = event.Cancelled
	attempt.Summary = event.Summary
	attempt.Results = results
	attempt.NativeObservationRef = nativeRef
	attempt.NativeObservationSHA256 = nativeDigest
	attempt.AfterSourceFingerprint = fingerprint
	attempt.AfterSources = afterSources
	attempt.AfterDirtyPaths = afterDirty
	attempt.SourceChangedPaths = changedSources
	session.Attempts[index] = attempt
	if event.Status != "passed" {
		session.ExecutionOutcome = event.Status
	}
	return session, updates, nil
}

func doCheckEvidence(root string, check PlaybookCheck, results []DoResultRef, verifySnapshot bool) error {
	if check.Kind == "exit_code" {
		return nil
	}
	var selected *DoResultRef
	for i := range results {
		if results[i].Path == check.ResultPath && results[i].Kind == check.Kind {
			if selected != nil {
				return fmt.Errorf("duplicate result for check %s", check.ID)
			}
			selected = &results[i]
		}
	}
	if selected == nil {
		return fmt.Errorf("required %s evidence for check %s is missing", check.Kind, check.ID)
	}
	if check.Kind == "file" {
		if verifySnapshot {
			return doVerifyArtifactReceipt(root, *selected)
		}
		// Completion has just streamed and bounded the actual file above.
		return nil
	}
	ref := selected.Path
	if verifySnapshot {
		ref = selected.SnapshotRef
	}
	raw, err := secureProjectReadFile(root, ref)
	if err != nil {
		return err
	}
	if doBytesDigest(raw) != selected.SHA256 {
		return fmt.Errorf("check evidence digest changed")
	}
	switch check.Kind {
	case "file":
		return nil
	case "json":
		if err := playbookRejectDuplicateKeys(raw); err != nil {
			return fmt.Errorf("check JSON invalid: %w", err)
		}
		var data, expected any
		decoder := json.NewDecoder(bytes.NewReader(raw))
		decoder.UseNumber()
		if err := decoder.Decode(&data); err != nil {
			return err
		}
		decoder = json.NewDecoder(bytes.NewReader(check.ExpectedJSON))
		decoder.UseNumber()
		if err := decoder.Decode(&expected); err != nil {
			return err
		}
		actual, err := doJSONPointer(data, check.JSONPointer)
		if err != nil {
			return err
		}
		if !reflect.DeepEqual(actual, expected) {
			return fmt.Errorf("JSON assertion failed for %s", check.ID)
		}
		return nil
	case "junit":
		return doAuditJUnit(raw, check.MinCases)
	default:
		return fmt.Errorf("unsupported check kind %q", check.Kind)
	}
}

func doJSONPointer(value any, pointer string) (any, error) {
	if pointer == "" {
		return value, nil
	}
	if !strings.HasPrefix(pointer, "/") {
		return nil, fmt.Errorf("invalid JSON pointer")
	}
	for _, token := range strings.Split(strings.TrimPrefix(pointer, "/"), "/") {
		token = strings.ReplaceAll(strings.ReplaceAll(token, "~1", "/"), "~0", "~")
		switch current := value.(type) {
		case map[string]any:
			var ok bool
			value, ok = current[token]
			if !ok {
				return nil, fmt.Errorf("JSON pointer not found")
			}
		case []any:
			index, err := strconv.Atoi(token)
			if err != nil || index < 0 || index >= len(current) {
				return nil, fmt.Errorf("JSON array pointer not found")
			}
			value = current[index]
		default:
			return nil, fmt.Errorf("JSON pointer does not resolve")
		}
	}
	return value, nil
}

func doAuditJUnit(raw []byte, minCases int) error {
	decoder := xml.NewDecoder(bytes.NewReader(raw))
	cases := 0
	explicitlyExecuted := 0
	hasDisabled := false
	depth := 0
	rootSeen := false
	type suiteCounter struct {
		casesBefore int
		tests       int
		declared    bool
	}
	counters := []suiteCounter{}
	for {
		token, err := decoder.Token()
		if err == io.EOF {
			break
		}
		if err != nil {
			return fmt.Errorf("invalid JUnit XML: %w", err)
		}
		switch element := token.(type) {
		case xml.Directive:
			return fmt.Errorf("JUnit directives are not accepted")
		case xml.StartElement:
			if depth == 0 {
				if rootSeen || (element.Name.Local != "testsuite" && element.Name.Local != "testsuites") {
					return fmt.Errorf("invalid JUnit root")
				}
				rootSeen = true
			}
			depth++
			if element.Name.Local == "testcase" {
				cases++
				executed := false
				for _, attribute := range element.Attr {
					if attribute.Name.Local != "status" && attribute.Name.Local != "result" {
						continue
					}
					value := strings.ToLower(strings.TrimSpace(attribute.Value))
					passing := value == "passed" || value == "pass" || value == "success" || value == "successful"
					if attribute.Name.Local == "status" {
						passing = passing || value == "run"
					} else {
						passing = passing || value == "completed"
					}
					if !passing {
						return fmt.Errorf("JUnit testcase reports nonpassing or unsupported %s=%q", attribute.Name.Local, attribute.Value)
					}
					executed = true
				}
				if executed {
					explicitlyExecuted++
				}
			}
			if element.Name.Local == "failure" || element.Name.Local == "error" || element.Name.Local == "skipped" {
				return fmt.Errorf("JUnit has failed, errored, or skipped cases")
			}
			if element.Name.Local == "testsuite" || element.Name.Local == "testsuites" {
				counter := suiteCounter{casesBefore: cases}
				for _, attribute := range element.Attr {
					if attribute.Name.Local == "tests" {
						n, err := strconv.Atoi(attribute.Value)
						if err != nil || n < 0 || counter.declared {
							return fmt.Errorf("JUnit reports invalid tests count")
						}
						counter.tests, counter.declared = n, true
					}
					if attribute.Name.Local == "disabled" {
						n, err := strconv.Atoi(attribute.Value)
						if err != nil || n < 0 {
							return fmt.Errorf("JUnit reports invalid disabled count")
						}
						hasDisabled = hasDisabled || n > 0
					}
					if attribute.Name.Local == "failures" || attribute.Name.Local == "errors" || attribute.Name.Local == "skipped" {
						n, err := strconv.Atoi(attribute.Value)
						if err != nil || n != 0 {
							return fmt.Errorf("JUnit reports nonzero or invalid %s", attribute.Name.Local)
						}
					}
				}
				counters = append(counters, counter)
			}
		case xml.EndElement:
			if element.Name.Local == "testsuite" || element.Name.Local == "testsuites" {
				if len(counters) == 0 {
					return fmt.Errorf("invalid JUnit suite nesting")
				}
				counter := counters[len(counters)-1]
				counters = counters[:len(counters)-1]
				if counter.declared && counter.tests != cases-counter.casesBefore {
					return fmt.Errorf("JUnit declared %d tests but recorded %d cases in its suite", counter.tests, cases-counter.casesBefore)
				}
			}
			depth--
		}
	}
	if !rootSeen || cases < minCases || cases == 0 {
		return fmt.Errorf("JUnit executed %d cases; at least %d required", cases, minCases)
	}
	if hasDisabled && explicitlyExecuted != cases {
		return fmt.Errorf("JUnit reports disabled cases without explicit passing execution")
	}
	return nil
}

func doValidate(root string, session DoSession, requireCognition bool) DoValidation {
	validation := DoValidation{Status: "blocked", EvidenceOrigin: "agent_tool_observation", DefinitionDigest: session.DefinitionDigest, VerifiedAt: doNow(), Blockers: []string{}, ChangedSourcePaths: []string{}, CognitionCloseout: "not_applicable"}
	if err := doVerifyInstanceBinding(root, session); err != nil {
		validation.Blockers = append(validation.Blockers, err.Error())
		return validation
	}
	if session.Context["os"] != runtime.GOOS || session.Context["arch"] != runtime.GOARCH {
		validation.Blockers = append(validation.Blockers, "the current runtime platform differs from the frozen operation context")
	}
	if gaps := playbookCompatibility(session.Definition, session.Context); len(gaps) > 0 {
		validation.Blockers = append(validation.Blockers, gaps...)
	}
	if session.Blocker != nil {
		validation.Blockers = append(validation.Blockers, "external blocker: "+session.Blocker.Cause)
	}
	if session.KnowledgeStatus == "saved" {
		if session.Knowledge == nil {
			validation.Blockers = append(validation.Blockers, "saved knowledge is missing its receipt")
		} else if err := doVerifyKnowledge(root, session, *session.Knowledge); err != nil {
			validation.Blockers = append(validation.Blockers, err.Error())
		}
	}
	if err := validatePlaybookDefinition(root, session.Definition); err != nil {
		validation.Blockers = append(validation.Blockers, err.Error())
		return validation
	}
	currentSources, fingerprint, _, _, err := doCaptureSource(root, session.Definition, session.WriteScope)
	if err != nil {
		validation.Blockers = append(validation.Blockers, err.Error())
		return validation
	}
	validation.SourceFingerprint = fingerprint
	latest := doLatestAttempts(session)
	accepted := []DoAttempt{}
	visited := map[string]bool{}
	for _, step := range session.Definition.Steps {
		if step.Required {
			validation.RequiredSteps++
			doValidateRequiredClosure(root, session, latest, step.ID, "step", fingerprint, &validation, &accepted, visited)
		}
	}
	for _, check := range session.Definition.Checks {
		if check.Required {
			validation.RequiredChecks++
			doValidateRequiredClosure(root, session, latest, check.ID, "check", fingerprint, &validation, &accepted, visited)
		}
	}
	// Unreconciled effects belong to the whole session, including optional
	// actions and older definitions, rather than only its required closure.
	for _, attempt := range session.Attempts {
		if attempt.Status == "running" {
			validation.Blockers = append(validation.Blockers, "attempt "+attempt.ID+" is still running or its effect is unknown")
		}
		if attempt.Status == "interrupted" && attempt.Recovery == nil {
			validation.Blockers = append(validation.Blockers, "attempt "+attempt.ID+" is interrupted and needs evidence-backed recovery before closeout")
		}
		if attempt.Recovery != nil {
			if err := doRecoveryMatchesAttempt(attempt, *attempt.Recovery); err != nil {
				validation.Blockers = append(validation.Blockers, "attempt "+attempt.ID+" recovery evidence: "+err.Error())
			}
			if err := doVerifyRecoveryEvidence(root, *attempt.Recovery); err != nil {
				validation.Blockers = append(validation.Blockers, "attempt "+attempt.ID+" recovery evidence: "+err.Error())
			}
		}
	}
	changed, err := runcontrol.InspectWorkspaceDelta(context.Background(), root, session.BaselineJSON)
	if err != nil {
		validation.Blockers = append(validation.Blockers, err.Error())
	} else {
		view, viewErr := runcontrol.OpenViewForRepository(context.Background(), root)
		if viewErr == nil {
			defer view.Close()
		}
		for _, p := range changed {
			if doScopeContains([]string{path.Dir(doSessionRef(session.ID))}, p) {
				continue
			}
			if doCognitionRuntimeExpansionSnapshot(root, p) {
				continue
			}
			if owned, ownerErr := doCognitionCloseoutIntentOwnedBySession(root, session, fingerprint, p); owned {
				if ownerErr != nil {
					validation.Blockers = append(validation.Blockers, ownerErr.Error())
				}
				continue
			}
			if owned, ownerErr := doCognitionDeltaSessionOwnedBySession(root, session, fingerprint, p); owned {
				if ownerErr != nil {
					validation.Blockers = append(validation.Blockers, ownerErr.Error())
				}
				continue
			}
			metadataOwned := false
			for _, exact := range session.MetadataWriteScope {
				if p == exact {
					metadataOwned = true
					break
				}
			}
			if metadataOwned {
				continue
			}
			if doScopeContains(session.WriteScope, p) {
				validation.ChangedSourcePaths = append(validation.ChangedSourcePaths, p)
				continue
			}
			if doScopeContains(session.OutputScope, p) {
				continue
			}
			if doSourceInputPath(session, currentSources, p) {
				// Current input bytes are part of every required attempt's source
				// fingerprint above. Other Work ownership must never excuse stale
				// input evidence, nor block an actually reverified current input.
				if !doCurrentSourceInputPath(currentSources, p) {
					validation.Blockers = append(validation.Blockers, "previous operation input changed outside its current definition; explicitly bind and verify the input or captured snapshot: "+p)
				}
				continue
			}
			if inspected, inspectionErr := doExternalChangeDisposition(root, session, fingerprint, p); inspected {
				if inspectionErr != nil {
					validation.Blockers = append(validation.Blockers, inspectionErr.Error())
				}
				continue
			}
			// Independent concurrent owners are visible, but this session cannot
			// absorb their changes into its operation or learning evidence.
			ownedByOther := false
			if viewErr == nil {
				owners, _ := view.FindWorkOwners(context.Background(), p)
				for _, owner := range owners {
					if owner.Work.WorkID != session.WorkID {
						ownedByOther = true
					}
				}
			}
			if !ownedByOther {
				validation.Blockers = append(validation.Blockers, "unclaimed changed path: "+p)
			}
		}
	}
	if requireCognition {
		if err := doRequireCognitionIntentsClosed(root, session); err != nil {
			validation.Blockers = append(validation.Blockers, err.Error())
		}
	}
	if len(validation.ChangedSourcePaths) > 0 {
		validation.CognitionCloseout = "required"
		if requireCognition {
			scope := filepath.Join(root, filepath.FromSlash(path.Dir(doSessionRef(session.ID))))
			if err := requireMutationCognitionReceipt(scope, "sp-do"); err != nil {
				validation.Blockers = append(validation.Blockers, err.Error())
			} else if receipt, err := loadMutationCognitionReceipt(scope); err != nil || receipt == nil {
				validation.Blockers = append(validation.Blockers, "cognition receipt unavailable")
			} else {
				if receipt.Workflow != "sp-do" || path.Clean(receipt.Scope) != path.Dir(doSessionRef(session.ID)) {
					validation.Blockers = append(validation.Blockers, "cognition receipt must bind this exact Do scope and workflow")
				}
				if receipt.DoBinding == nil || receipt.DoBinding.SessionID != session.ID || receipt.DoBinding.DefinitionEpoch != max(1, session.DefinitionEpoch) || receipt.DoBinding.DefinitionDigest != session.DefinitionDigest || receipt.DoBinding.SourceFingerprint != fingerprint || !equalCloseoutPaths(receipt.DoBinding.ChangedPaths, validation.ChangedSourcePaths) {
					validation.Blockers = append(validation.Blockers, "cognition receipt lacks the current pre-update Do source binding; refresh the exact changed source")
				}
				recorded, recordedErr := time.Parse(time.RFC3339Nano, receipt.RecordedAt)
				created, _ := time.Parse(time.RFC3339Nano, session.CreatedAt)
				if recordedErr != nil || recorded.Truncate(time.Second).Before(created.Truncate(time.Second)) {
					validation.Blockers = append(validation.Blockers, "cognition receipt predates this operation")
				}
				wanted := append([]string(nil), validation.ChangedSourcePaths...)
				got := append([]string(nil), receipt.ChangedPaths...)
				sort.Strings(wanted)
				sort.Strings(got)
				if !reflect.DeepEqual(wanted, got) {
					validation.Blockers = append(validation.Blockers, "cognition receipt changed_paths differ from actual owned source changes")
				} else {
					validation.CognitionCloseout = receipt.ResultState
				}
			}
		}
	}
	evidence := map[string]any{"session_id": session.ID, "definition_digest": session.DefinitionDigest, "attempts": accepted, "source_fingerprint": fingerprint}
	if len(session.ExternalChanges) > 0 {
		evidence["external_changes"] = session.ExternalChanges
	}
	validation.EvidenceDigest = doDigest(evidence)
	if len(validation.Blockers) == 0 {
		validation.Status = "passed"
	}
	return validation
}

// A declared dependency is required by its consumer even when it was optional
// as a standalone action. Validate its observations and outputs as well.
func doValidateRequiredClosure(root string, session DoSession, latest map[string]DoAttempt, id, kind, fingerprint string, validation *DoValidation, accepted *[]DoAttempt, visited map[string]bool) {
	if visited[id] {
		return
	}
	visited[id] = true
	action, err := doFindAction(session, kind, id)
	if err != nil {
		validation.Blockers = append(validation.Blockers, err.Error())
		return
	}
	for _, dependency := range action.dependencies {
		dependencyKind := "step"
		if _, err := doFindAction(session, dependencyKind, dependency); err != nil {
			dependencyKind = "check"
		}
		doValidateRequiredClosure(root, session, latest, dependency, dependencyKind, fingerprint, validation, accepted, visited)
	}
	doValidateAttempt(root, session, latest, id, kind, fingerprint, validation, accepted)
}

func doValidateAttempt(root string, session DoSession, latest map[string]DoAttempt, id, kind, fingerprint string, validation *DoValidation, accepted *[]DoAttempt) {
	attempt, ok := latest[id]
	if !ok || attempt.Status != "passed" {
		validation.Blockers = append(validation.Blockers, kind+" "+id+" has no current passed attempt")
		return
	}
	if attempt.Kind != kind || (!doAttemptInCurrentDefinition(session, attempt) && !doRetainedAttempt(session, attempt)) {
		validation.Blockers = append(validation.Blockers, kind+" "+id+" evidence binding is stale")
		return
	}
	if attempt.EvidenceOrigin != "agent_tool_observation" || attempt.ToolCallID == "" || attempt.TimedOut || attempt.Cancelled {
		validation.Blockers = append(validation.Blockers, kind+" "+id+" lacks a valid native-tool observation")
		return
	}
	action, err := doFindAction(session, kind, id)
	if err != nil {
		validation.Blockers = append(validation.Blockers, err.Error())
		return
	}
	if len(action.argv) > 0 && (attempt.ExitCode == nil || *attempt.ExitCode != 0) {
		validation.Blockers = append(validation.Blockers, kind+" "+id+" lacks a zero observed exit")
		return
	}
	if len(action.sourceWrites) == 0 {
		if attempt.SourceFingerprint != fingerprint {
			validation.Blockers = append(validation.Blockers, kind+" "+id+" evidence binding is stale")
			return
		}
	} else if err := doValidateMutationLineage(session, attempt, latest, fingerprint); err != nil {
		validation.Blockers = append(validation.Blockers, err.Error())
		return
	}
	if !reflect.DeepEqual(action.argv, attempt.Argv) && !(len(action.argv) == 0 && len(attempt.Argv) == 0) {
		validation.Blockers = append(validation.Blockers, "attempt argv was altered")
		return
	}
	if err := doValidateNativeAttempt(root, session, action, attempt); err != nil {
		validation.Blockers = append(validation.Blockers, err.Error())
		return
	}
	for _, dependency := range action.dependencies {
		prior, exists := latest[dependency]
		if !exists || prior.Status != "passed" || doAttemptResultFingerprint(prior) != attempt.SourceFingerprint || attempt.DependencyAttempts[dependency] != prior.ID {
			validation.Blockers = append(validation.Blockers, "dependency "+dependency+" is not freshly passed")
			return
		}
	}
	for _, ref := range attempt.Results {
		if !doScopeContains([]string{path.Join(path.Dir(doSessionRef(session.ID)), "evidence")}, ref.SnapshotRef) {
			validation.Blockers = append(validation.Blockers, "foreign evidence snapshot")
			return
		}
		raw, err := secureProjectReadFile(root, ref.SnapshotRef)
		if err != nil || doBytesDigest(raw) != ref.SnapshotSHA256 {
			validation.Blockers = append(validation.Blockers, "evidence snapshot missing or changed")
			return
		}
		if ref.Kind == "file" {
			if err := doVerifyArtifactReceipt(root, ref); err != nil {
				validation.Blockers = append(validation.Blockers, err.Error())
				return
			}
		} else if doBytesDigest(raw) != ref.SHA256 || int64(len(raw)) != ref.Size {
			validation.Blockers = append(validation.Blockers, "recorded report size or digest mismatch")
			return
		} else {
			digest, size, err := doHashArtifact(root, ref.Path)
			if err != nil || size != ref.Size || digest != ref.SHA256 {
				validation.Blockers = append(validation.Blockers, "current result file is missing or changed: "+ref.Path)
				return
			}
		}
	}
	if action.check != nil && action.check.Kind != "observation" {
		if err := doCheckEvidence(root, *action.check, attempt.Results, true); err != nil {
			validation.Blockers = append(validation.Blockers, err.Error())
			return
		}
	}
	*accepted = append(*accepted, attempt)
}

func doCognitionRuntimeExpansionSnapshot(root, p string) bool {
	paths, err := rt.ResolvePaths(root)
	if err != nil {
		return false
	}
	return cognitionquery.IsRuntimeExpansionSnapshot(paths, p)
}
