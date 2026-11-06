package main

import (
	"fmt"
	"reflect"
	"sort"
	"strings"
)

func doAttemptResultFingerprint(attempt DoAttempt) string {
	if attempt.AfterSourceFingerprint != "" {
		return attempt.AfterSourceFingerprint
	}
	return attempt.SourceFingerprint
}

// A missing directory is represented in the initial bounded source snapshot.
// When a generator creates or removes children, the directory placeholder is
// replaced by the actual file keys; only actual file changes enter the scope.
func doChangedSourceFiles(before, after map[string]string) []string {
	keys := map[string]bool{}
	for p := range before {
		keys[p] = true
	}
	for p := range after {
		keys[p] = true
	}
	missing := doBytesDigest([]byte("missing owned source"))
	changed := []string{}
	for p := range keys {
		if before[p] == after[p] {
			continue
		}
		placeholder := false
		if before[p] == missing || after[p] == missing {
			for child := range keys {
				if strings.HasPrefix(child, p+"/") {
					placeholder = true
					break
				}
			}
		}
		if !placeholder {
			changed = append(changed, p)
		}
	}
	sort.Strings(changed)
	return changed
}

func doValidateMutationLineage(session DoSession, attempt DoAttempt, latest map[string]DoAttempt, finalFingerprint string) error {
	action, err := doFindAction(session, attempt.Kind, attempt.TargetID)
	if err != nil || len(action.sourceWrites) == 0 || attempt.AfterSourceFingerprint == "" || attempt.AfterSources == nil {
		return fmt.Errorf("source-writing attempt lacks its runtime-owned before/after source proof")
	}
	before := doSourceDigest(attempt.Sources, attempt.SourceRevision, attempt.DirtyPaths, attempt.ExternalFingerprint)
	after := doSourceDigest(attempt.AfterSources, attempt.SourceRevision, attempt.AfterDirtyPaths, attempt.ExternalFingerprint)
	if before != attempt.SourceFingerprint || after != attempt.AfterSourceFingerprint {
		return fmt.Errorf("source-writing attempt fingerprint proof changed")
	}
	changed := doChangedSourceFiles(attempt.Sources, attempt.AfterSources)
	if !reflect.DeepEqual(uniqueSortedTrimmed(changed), uniqueSortedTrimmed(attempt.SourceChangedPaths)) {
		return fmt.Errorf("source-writing attempt change list differs from actual source snapshots")
	}
	for _, p := range changed {
		if !doScopeContains(action.sourceWrites, p) || !doScopeContains(session.WriteScope, p) {
			return fmt.Errorf("source-writing attempt changed a file outside its declared scope")
		}
	}
	if !doMutationReachesFinal(session, attempt, latest, finalFingerprint, map[string]bool{}) {
		return fmt.Errorf("source-writing attempt has no current causal path to the final source; evidence is stale")
	}
	return nil
}

func doMutationReachesFinal(session DoSession, attempt DoAttempt, latest map[string]DoAttempt, finalFingerprint string, seen map[string]bool) bool {
	if doAttemptResultFingerprint(attempt) == finalFingerprint {
		return true
	}
	if seen[attempt.ID] {
		return false
	}
	seen[attempt.ID] = true
	for _, next := range latest {
		if next.Status != "passed" || next.DependencyAttempts[attempt.TargetID] != attempt.ID || next.SourceFingerprint != doAttemptResultFingerprint(attempt) {
			continue
		}
		action, err := doFindAction(session, next.Kind, next.TargetID)
		if err == nil && len(action.sourceWrites) > 0 && doMutationReachesFinal(session, next, latest, finalFingerprint, seen) {
			return true
		}
	}
	return false
}
