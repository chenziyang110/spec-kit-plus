package main

import (
	"fmt"
	"os"
	"path"
	"path/filepath"
	"reflect"
	"strings"

	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
)

// DoBinding is captured before cognition mutation, included in the existing
// durable intent digest, and copied into its receipt. It cannot be reconstructed
// later from an old update ID and newer source bytes.
type DoCognitionBinding struct {
	SessionID         string   `json:"session_id"`
	DefinitionEpoch   int      `json:"definition_epoch"`
	DefinitionDigest  string   `json:"definition_digest"`
	SourceFingerprint string   `json:"source_fingerprint"`
	ChangedPaths      []string `json:"changed_paths"`
}

func doCognitionScope(root, scope string) (string, error) {
	clean := path.Clean(filepath.ToSlash(scope))
	parts := strings.Split(clean, "/")
	if len(parts) != 4 || parts[0] != ".specify" || parts[1] != "do" || parts[2] != "sessions" || !doIDPattern.MatchString(parts[3]) {
		return "", fmt.Errorf("sp-do cognition requires the exact runtime-owned Do session scope")
	}
	if _, err := secureProjectPath(root, clean); err != nil {
		return "", err
	}
	return parts[3], nil
}

func doCurrentCognitionBinding(root, sessionID string) (*DoCognitionBinding, error) {
	session, _, err := loadDoSession(root, sessionID)
	if err != nil {
		return nil, err
	}
	validation := doValidate(root, session, false)
	if validation.Status != "passed" || len(validation.ChangedSourcePaths) == 0 {
		return nil, fmt.Errorf("Do cognition requires completed source-bound execution and actual owned source changes: %s", strings.Join(validation.Blockers, "; "))
	}
	return &DoCognitionBinding{SessionID: session.ID, DefinitionEpoch: max(1, session.DefinitionEpoch), DefinitionDigest: session.DefinitionDigest, SourceFingerprint: validation.SourceFingerprint, ChangedPaths: normalizedCloseoutPaths(validation.ChangedSourcePaths)}, nil
}

func doCognitionWriterPaths(paths rt.Paths, intent closeoutIntent) ([]string, error) {
	root := ".specify/project-cognition/"
	files := []string{root + "status.json", root + "project-cognition.db", root + "project-cognition.db-wal", root + "project-cognition.db-shm", root + "project-cognition.db-journal", root + ".update.lock", root + "validate-build-receipt.json", root + "closeout-intents/" + intent.ID + ".json"}
	pending, err := listCloseoutIntents(paths)
	if err != nil {
		return nil, err
	}
	for _, previous := range pending {
		_, scope, err := resolveCloseoutApplyScope(paths.Root, previous.Scope)
		if err != nil {
			return nil, err
		}
		files = append(files, root+"closeout-intents/"+previous.ID+".json", path.Join(scope, mutationCognitionReceiptFileName))
	}
	entries, err := os.ReadDir(filepath.Join(paths.RuntimeDir, "closeout-repairs"))
	if err != nil && !os.IsNotExist(err) {
		return nil, err
	}
	for _, entry := range entries {
		id := strings.TrimSuffix(entry.Name(), ".json")
		if entry.IsDir() || !strings.HasSuffix(entry.Name(), ".json") || !validCloseoutIntentID(id) {
			continue
		}
		record, err := loadCloseoutRepair(paths, id)
		if err != nil {
			return nil, err
		}
		files = append(files, root+"closeout-intents/"+record.Original.ID+".json", root+"closeout-intents/"+record.Replacement.ID+".json")
	}
	return uniqueSortedTrimmed(files), nil
}

func doBeginCognitionCloseout(paths rt.Paths, workflow, scope, reason, payload, deltaSession, commitRange string, changedPaths []string, deltaDigest string) (*DoCognitionBinding, func(), error) {
	noop := func() {}
	if err := doCheckCognitionScopeOwner(scope, workflow); err != nil {
		return nil, noop, err
	}
	if workflow != "sp-do" {
		return nil, noop, nil
	}
	id, err := doCognitionScope(paths.Root, scope)
	if err != nil {
		return nil, noop, err
	}
	binding, err := doCurrentCognitionBinding(paths.Root, id)
	if err != nil {
		return nil, noop, err
	}
	if !equalCloseoutPaths(binding.ChangedPaths, changedPaths) {
		return nil, noop, fmt.Errorf("cognition payload paths differ from actual Do-owned source changes")
	}
	intent := closeoutIntent{Workflow: workflow, Scope: scope, Reason: reason, PayloadJSON: payload, DeltaSessionID: deltaSession, CommitRange: commitRange, DeltaDigest: deltaDigest, DoBinding: binding}
	digest := storedCloseoutIntentDigest(intent)
	intent.ID = "intent-" + digest[:24]
	files, err := doCognitionWriterPaths(paths, intent)
	if err != nil {
		return nil, noop, err
	}
	if err := doRegisterOwnerMetadataWrites(paths.Root, id, "cognition", files); err != nil {
		return nil, noop, err
	}
	// Acquire Do before the existing cognition update lock. The source basis is
	// rechecked after registration and again at receipt publication.
	release, err := doSessionLock(paths.Root, id)
	if err != nil {
		return nil, noop, err
	}
	current, err := doCurrentCognitionBinding(paths.Root, id)
	if err != nil || !reflect.DeepEqual(current, binding) {
		release()
		return nil, noop, fmt.Errorf("Do execution/source changed before cognition could acquire its operation lock")
	}
	return binding, release, nil
}

func doCheckCognitionBinding(root, scope string, binding *DoCognitionBinding) error {
	id, err := doCognitionScope(root, scope)
	if err != nil {
		return err
	}
	if binding == nil || binding.SessionID != id {
		return fmt.Errorf("Do cognition receipt lacks its pre-update source binding; use planner-first cognition closeout apply")
	}
	current, err := doCurrentCognitionBinding(root, id)
	if err != nil {
		return err
	}
	if !reflect.DeepEqual(current, binding) {
		return fmt.Errorf("Do cognition source binding is stale; its exact source must be refreshed again")
	}
	return nil
}

// A ready receipt may be durable just before its intent is removed. Releasing
// the Do Work in that recovery window would strand the exact owner required by
// replay. Check the whole exact scope, including a receipt later overwritten by
// an explicit mark-dirty record; unrelated scopes are not this Do's receipt.
func doRequireCognitionIntentsClosed(root string, session DoSession) error {
	// Every real Do cognition writer registers its precise intent before
	// persisting it. A session that never acquired such ownership must not be
	// made dependent on unrelated cognition state by this cleanup gate.
	ownsCognitionIntent := false
	for _, p := range session.MetadataWriteScope {
		if path.Dir(p) == ".specify/project-cognition/closeout-intents" {
			ownsCognitionIntent = true
			break
		}
	}
	if !ownsCognitionIntent {
		return nil
	}
	paths, err := rt.ResolvePaths(root)
	if err != nil {
		return err
	}
	intents, err := listCloseoutIntents(paths)
	if err != nil {
		return err
	}
	scope := path.Dir(doSessionRef(session.ID))
	for _, intent := range intents {
		if intent.Workflow == "sp-do" && path.Clean(intent.Scope) == scope {
			return fmt.Errorf("cognition closeout intent %s remains pending for this Do scope; replay the exact intent before finishing", intent.ID)
		}
	}
	return nil
}

func doCheckCognitionScopeOwner(scope, workflow string) error {
	ownerScope := strings.ToLower(path.Clean(filepath.ToSlash(scope)))
	if workflow != "sp-do" && (ownerScope == ".specify/do" || strings.HasPrefix(ownerScope, ".specify/do/")) {
		return fmt.Errorf("Do cognition receipt scope requires its sp-do owner")
	}
	return nil
}

func doPrepareCognitionReceipt(scopeDir string, receipt *mutationCognitionReceipt, bindings []*DoCognitionBinding) error {
	if err := doCheckCognitionScopeOwner(receipt.Scope, receipt.Workflow); err != nil {
		return err
	}
	if receipt.Workflow != "sp-do" {
		paths, err := rt.ResolvePaths(scopeDir)
		if err != nil {
			return err
		}
		relative, err := filepath.Rel(paths.Root, scopeDir)
		if err != nil {
			return err
		}
		return doCheckCognitionScopeOwner(relative, receipt.Workflow)
	}
	paths, err := rt.ResolvePaths(scopeDir)
	if err != nil {
		return err
	}
	id, err := doCognitionScope(paths.Root, receipt.Scope)
	if err != nil {
		return err
	}
	if filepath.Clean(scopeDir) != filepath.Join(paths.Root, filepath.FromSlash(receipt.Scope)) {
		return fmt.Errorf("Do cognition receipt location differs from its exact scope")
	}
	session, _, err := loadDoSession(paths.Root, id)
	if err != nil {
		return err
	}
	if session.KnowledgeStatus != "pending" {
		return fmt.Errorf("completed Do knowledge cannot acquire a new cognition receipt")
	}
	if err := doRequireWork(paths.Root, session); err != nil {
		return err
	}
	if len(bindings) > 0 {
		receipt.DoBinding = bindings[0]
	}
	if receipt.ResultState == "blocked" || receipt.ResultState == "needs_rebuild" {
		return nil
	}
	if receipt.ResultState == "mark-dirty" && receipt.DoBinding == nil {
		// Explicit graph debt has no historical successful update to relabel.
		receipt.DoBinding, err = doCurrentCognitionBinding(paths.Root, id)
		if err != nil {
			return err
		}
	}
	return doCheckCognitionBinding(paths.Root, receipt.Scope, receipt.DoBinding)
}

// Recovery resolves the existing exact intent before acquiring cognition's
// update lock. Its immutable binding is checked again by the original replay
// transaction, so this adds Do ownership without replacing its existing CAS.
func doBeginCognitionReplay(paths rt.Paths, id, expected, scope string) (func(), error) {
	noop := func() {}
	if id == "" {
		absolute, _, err := resolveCloseoutApplyScope(paths.Root, scope)
		if err != nil {
			return noop, nil // the original replay parser reports invalid input
		}
		receipt, err := loadMutationCognitionReceipt(absolute)
		if err != nil || receipt == nil {
			return noop, nil
		}
		id, expected = receipt.IntentID, receipt.IntentDigest
	}
	intent, err := loadCloseoutIntent(paths, id)
	if err != nil || intent.Workflow != "sp-do" {
		return noop, nil // preserve other workflows' original recovery behavior
	}
	if intent.InputDigest != expected {
		return noop, fmt.Errorf("replay expected digest does not match selected Do intent")
	}
	sessionID, err := doCognitionScope(paths.Root, intent.Scope)
	if err != nil {
		return noop, err
	}
	release, err := doSessionLock(paths.Root, sessionID)
	if err != nil {
		return noop, err
	}
	if err := doCheckCognitionBinding(paths.Root, intent.Scope, intent.DoBinding); err != nil {
		release()
		return noop, err
	}
	session, _, err := loadDoSession(paths.Root, sessionID)
	if err == nil {
		err = doRequireWork(paths.Root, session)
	}
	if err != nil {
		release()
		return noop, err
	}
	return release, nil
}
