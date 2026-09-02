package main

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runcontrol"
)

func TestWorkBoardCLIRegistersShowsConflictsAndReleasesScopes(t *testing.T) {
	root := initCoordinationCLIRepository(t)
	intentsJSON := marshalWorkBoardCLIJSON(t, []map[string]any{{
		"path": "src/auth", "operation": "modify", "reason": "authentication refactor", "confidence": "confirmed",
	}})

	code, created := invokeCoordinationCLI(t,
		"work", "begin",
		"--project-root", root,
		"--work-id", "work-cli-auth",
		"--summary", "Refactor authentication",
		"--agent-id", "codex-a",
		"--adapter-id", "codex",
		"--lease-seconds", "1800",
		"--intents-json", intentsJSON,
		"--format", "json",
	)
	if code != 0 || created["status"] != "ok" {
		t.Fatalf("work begin = code %d envelope %#v", code, created)
	}
	work := requireObject(t, requireObject(t, created, "data"), "work")
	if work["work_id"] != "work-cli-auth" || work["status"] != "active" || work["revision"] != float64(1) || work["fence"] != float64(1) {
		t.Fatalf("created work = %#v", work)
	}

	conflictingJSON := marshalWorkBoardCLIJSON(t, []map[string]any{{
		"path": "src/auth/login.go", "operation": "modify", "reason": "login change", "confidence": "confirmed",
	}})
	code, conflict := invokeCoordinationCLI(t,
		"work", "begin",
		"--project-root", root,
		"--work-id", "work-cli-login",
		"--summary", "Change login",
		"--agent-id", "codex-b",
		"--adapter-id", "codex",
		"--lease-seconds", "1800",
		"--intents-json", conflictingJSON,
		"--format", "json",
	)
	if code != 10 || conflict["status"] != "blocked" {
		t.Fatalf("conflicting work begin = code %d envelope %#v", code, conflict)
	}
	conflictData := requireObject(t, conflict, "data")
	conflicts := conflictData["conflicts"].([]any)
	if len(conflicts) != 1 || requireObjectValue(t, conflicts[0])["owner_work_id"] != "work-cli-auth" {
		t.Fatalf("work conflicts = %#v", conflicts)
	}
	showArgv := requireStringArray(t, conflict, "show_argv")
	if len(showArgv) < 4 || showArgv[1] != "work" || showArgv[2] != "show" || showArgv[3] != "work-cli-auth" {
		t.Fatalf("active conflict show_argv = %#v", showArgv)
	}
	resolution := requireObject(t, conflictData, "resolution_action")
	if resolution["kind"] != "inspect-conflicting-work" ||
		resolution["owner_work_id"] != "work-cli-auth" ||
		resolution["owner_intent_status"] != "active" ||
		resolution["agent_recovery_candidate"] != false ||
		resolution["after_inspection"] != "wait-or-narrow-scope" {
		t.Fatalf("active conflict resolution_action = %#v", resolution)
	}

	code, board := invokeCoordinationCLI(t, "board", "show", "--project-root", root, "--format", "json")
	if code != 0 || board["status"] != "ok" {
		t.Fatalf("board show = code %d envelope %#v", code, board)
	}
	items := board["items"].([]any)
	if len(items) != 1 {
		t.Fatalf("board items = %#v, want one active work item", items)
	}
	shown := requireObjectValue(t, items[0])
	if shown["work_id"] != "work-cli-auth" || len(shown["write_intents"].([]any)) != 1 {
		t.Fatalf("shown board item = %#v", shown)
	}
	if _, ok := shown["observed_paths"].([]any); !ok {
		t.Fatalf("shown observed_paths = %#v, want an array", shown["observed_paths"])
	}

	code, completed := invokeCoordinationCLI(t,
		"work", "finish", "work-cli-auth",
		"--project-root", root,
		"--expected-revision", "1",
		"--fence", "1",
		"--reason", "verified",
		"--format", "json",
	)
	if code != 0 || requireObject(t, requireObject(t, completed, "data"), "work")["status"] != "completed" {
		t.Fatalf("work finish = code %d envelope %#v", code, completed)
	}

	code, replacement := invokeCoordinationCLI(t,
		"work", "begin",
		"--project-root", root,
		"--work-id", "work-cli-login",
		"--summary", "Change login",
		"--agent-id", "codex-b",
		"--adapter-id", "codex",
		"--lease-seconds", "1800",
		"--intents-json", conflictingJSON,
		"--format", "json",
	)
	if code != 0 || replacement["status"] != "ok" {
		t.Fatalf("replacement work begin = code %d envelope %#v", code, replacement)
	}
	code, liveBoard := invokeCoordinationCLI(t, "board", "show", "--project-root", root, "--format", "json")
	if code != 0 || len(liveBoard["items"].([]any)) != 1 || requireObjectValue(t, liveBoard["items"].([]any)[0])["work_id"] != "work-cli-login" {
		t.Fatalf("default live board = code %d envelope %#v", code, liveBoard)
	}
	code, historyBoard := invokeCoordinationCLI(t,
		"board", "show",
		"--project-root", root,
		"--status", "completed,abandoned",
		"--format", "json",
	)
	if code != 0 || len(historyBoard["items"].([]any)) != 1 || requireObjectValue(t, historyBoard["items"].([]any)[0])["work_id"] != "work-cli-auth" {
		t.Fatalf("completed board history = code %d envelope %#v", code, historyBoard)
	}

	code, owners := invokeCoordinationCLI(t,
		"board", "owner", "src/auth/login.go",
		"--project-root", root,
		"--format", "json",
	)
	if code != 0 || len(owners["items"].([]any)) != 1 || requireObjectValue(t, owners["items"].([]any)[0])["work_id"] != "work-cli-login" {
		t.Fatalf("board owner = code %d envelope %#v", code, owners)
	}
}

func TestWorkBoardCLIUnblocksSameOwnerWithoutInterruptingSession(t *testing.T) {
	root := initCoordinationCLIRepository(t)
	intentsJSON := marshalWorkBoardCLIJSON(t, []map[string]any{{
		"path": "src/same-owner", "operation": "modify", "reason": "same-owner repair", "confidence": "confirmed",
	}})
	code, created := invokeCoordinationCLI(t,
		"work", "begin", "--project-root", root, "--work-id", "work-cli-same-owner",
		"--summary", "Continue after local repair", "--agent-id", "codex-a", "--adapter-id", "codex",
		"--lease-seconds", "1800", "--intents-json", intentsJSON, "--format", "json",
	)
	if code != 0 {
		t.Fatalf("work begin = code %d payload %#v", code, created)
	}
	code, blocked := invokeCoordinationCLI(t,
		"work", "block", "work-cli-same-owner", "--project-root", root,
		"--expected-revision", "1", "--fence", "1", "--reason", "focused check failed",
		"--next-action", "repair and unblock", "--format", "json",
	)
	blockedWork := requireObject(t, requireObject(t, blocked, "data"), "work")
	if code != 0 || blockedWork["status"] != "blocked" || blockedWork["revision"] != float64(2) {
		t.Fatalf("work block = code %d payload %#v", code, blocked)
	}

	code, resumed := invokeCoordinationCLI(t,
		"work", "unblock", "work-cli-same-owner", "--project-root", root,
		"--expected-revision", "2", "--fence", "1", "--reason", "focused check now passes",
		"--next-action", "continue the same task", "--format", "json",
	)
	resumedWork := requireObject(t, requireObject(t, resumed, "data"), "work")
	if code != 0 || resumedWork["status"] != "active" || resumedWork["revision"] != float64(3) || resumedWork["fence"] != float64(1) {
		t.Fatalf("same-owner unblock = code %d payload %#v", code, resumed)
	}
	if resumedWork["agent_id"] != "codex-a" || resumedWork["adapter_id"] != "codex" {
		t.Fatalf("same-owner unblock changed ownership: %#v", resumedWork)
	}
	code, shown := invokeCoordinationCLI(t, "work", "show", "work-cli-same-owner", "--project-root", root, "--format", "json")
	if code != 0 {
		t.Fatalf("work show after unblock = code %d payload %#v", code, shown)
	}
	shownWork := requireObject(t, requireObject(t, shown, "data"), "work")
	intents := shownWork["write_intents"].([]any)
	if len(intents) != 1 || requireObjectValue(t, intents[0])["status"] != "active" {
		t.Fatalf("same-owner unblock lost declared scope: %#v", shownWork)
	}

	code, rejected := invokeCoordinationCLI(t,
		"work", "unblock", "work-cli-same-owner", "--project-root", root,
		"--expected-revision", "3", "--fence", "1", "--reason", "cannot unblock active work", "--format", "json",
	)
	if code == 0 || rejected["status"] != "blocked" {
		t.Fatalf("active work accepted unblock: code=%d payload=%#v", code, rejected)
	}
}

func TestLocalRunControlStoreFailuresRemainAgentOwned(t *testing.T) {
	err := &runcontrol.StoreAccessError{
		Stage: "enable-wal", Path: ".specify/runtime/run-control/run-control.sqlite",
		Cause: fmt.Errorf("unable to open database file (14)"),
	}
	for name, env := range map[string]Envelope{
		"work-board": workBoardErrorEnvelope("open Work Board", err),
		"execution":  executionControlErrorEnvelope("open execution control store", err),
		"overview":   executionOverviewErrorEnvelope(err),
		"quick":      scriptDomainError("quick", err),
	} {
		t.Run(name, func(t *testing.T) {
			if env.Status != "blocked" || env.Data["error_code"] != "run_control_store_unavailable" {
				t.Fatalf("envelope = %#v, want typed blocked storage failure", env)
			}
			if env.Data["owner"] != "agent" || env.Data["human_action_required"] != false {
				t.Fatalf("storage failure ownership = %#v, want agent-owned recovery", env.Data)
			}
			if env.Data["storage_stage"] != "enable-wal" || env.Data["storage_path"] != ".specify/runtime/run-control/run-control.sqlite" {
				t.Fatalf("storage diagnostics = %#v", env.Data)
			}
		})
	}
}

func TestWorkBeginMigratesLegacyStoreBeforeRegisteringNewScope(t *testing.T) {
	root := initCoordinationCLIRepository(t)
	ctx := context.Background()
	repository, err := runcontrol.ResolveRepository(ctx, root)
	if err != nil {
		t.Fatal(err)
	}
	legacy, err := runcontrol.Open(ctx, repository.LegacyDatabasePath)
	if err != nil {
		t.Fatal(err)
	}
	_, _, err = legacy.BeginWork(ctx, runcontrol.BeginWorkParams{
		WorkID: "legacy-owner", TaskRef: "implement:legacy#T001", Summary: "legacy owner",
		AgentID: "legacy-agent", AdapterID: "codex", WorkspaceRoot: root,
		LeaseUntil: time.Now().UTC().Add(time.Hour), WriteIntents: []runcontrol.WriteIntentSpec{{
			Path: "src/shared", Operation: runcontrol.WriteModify, Confidence: runcontrol.IntentConfirmed,
		}},
	})
	if err != nil {
		t.Fatal(err)
	}
	if err := legacy.Close(); err != nil {
		t.Fatal(err)
	}

	intentsJSON := marshalWorkBoardCLIJSON(t, []map[string]any{{
		"path": "src/shared/new.go", "operation": "create", "reason": "new work", "confidence": "confirmed",
	}})
	code, envelope := invokeCoordinationCLI(t,
		"work", "begin", "--project-root", root, "--work-id", "new-owner",
		"--summary", "new owner", "--agent-id", "new-agent", "--adapter-id", "codex",
		"--lease-seconds", "1800", "--intents-json", intentsJSON, "--format", "json",
	)
	if code != 10 || envelope["status"] != "blocked" {
		t.Fatalf("legacy scope was not migrated before conflict check: code=%d envelope=%#v", code, envelope)
	}
	data := requireObject(t, envelope, "data")
	if data["error_code"] != "work_intent_conflict" {
		t.Fatalf("conflict data = %#v", data)
	}
	if _, err := os.Stat(repository.DatabasePath); err != nil {
		t.Fatalf("canonical migrated database missing: %v", err)
	}
}

func TestBindWorkIntentConflictRecoveryProjectsEveryOwner(t *testing.T) {
	env := NewEnvelope("blocked", "begin work failed")
	err := &runcontrol.WorkIntentConflictError{Conflicts: []runcontrol.WorkIntentConflict{
		{
			RequestedPath: "src", OwnerPath: "src/active.go", OwnerWorkID: "work-active",
			OwnerAgentID: "codex-a", OwnerSummary: "active change", OwnerStatus: runcontrol.WriteIntentActive,
		},
		{
			RequestedPath: "src", OwnerPath: "src/recovery.go", OwnerWorkID: "work-recovery",
			OwnerAgentID: "codex-b", OwnerSummary: "recoverable change", OwnerStatus: runcontrol.WriteIntentRecovery,
		},
	}}

	bindWorkIntentConflictRecovery(&env, err, ".")

	resolution := env.Data["resolution_action"].(map[string]any)
	owners := resolution["conflicting_owners"].([]any)
	if len(owners) != 2 {
		t.Fatalf("conflicting_owners = %#v, want both owners", owners)
	}
	first := owners[0].(map[string]any)
	second := owners[1].(map[string]any)
	if first["owner_work_id"] != "work-active" || first["agent_recovery_candidate"] != false {
		t.Fatalf("active owner projection = %#v", first)
	}
	if second["owner_work_id"] != "work-recovery" || second["agent_recovery_candidate"] != true {
		t.Fatalf("recovery owner projection = %#v", second)
	}
	if resolution["all_conflicts_must_be_resolved"] != true {
		t.Fatalf("resolution action = %#v", resolution)
	}
}

func TestWorkBoardCLIClaimRequiresIdentityAndClaimsCompleteScopeAllOrNone(t *testing.T) {
	root := initCoordinationCLIRepository(t)
	code, claimant := invokeCoordinationCLI(t,
		"work", "begin",
		"--project-root", root,
		"--work-id", "work-cli-claimant",
		"--task-ref", "fast:claimant",
		"--summary", "Claim Fast write scope",
		"--agent-id", "codex-a",
		"--adapter-id", "codex",
		"--lease-seconds", "1800",
		"--format", "json",
	)
	if code != 0 || claimant["status"] != "ok" {
		t.Fatalf("claimant work begin = code %d envelope %#v", code, claimant)
	}

	code, missingIdentity := invokeCoordinationCLI(t,
		"work", "claim",
		"--project-root", root,
		"--task-ref", "fast:claimant",
		"--write-scope-json", `["src/fast.go"]`,
		"--format", "json",
	)
	if code == 0 || missingIdentity["status"] != "blocked" {
		t.Fatalf("claim without current identity = code %d envelope %#v, want blocked", code, missingIdentity)
	}

	ownerIntents := marshalWorkBoardCLIJSON(t, []map[string]any{{
		"path": "src/shared.go", "operation": "modify", "confidence": "confirmed",
	}})
	code, owner := invokeCoordinationCLI(t,
		"work", "begin",
		"--project-root", root,
		"--work-id", "work-cli-owner",
		"--task-ref", "debug:owner",
		"--summary", "Own shared scope",
		"--agent-id", "codex-b",
		"--adapter-id", "codex",
		"--lease-seconds", "1800",
		"--intents-json", ownerIntents,
		"--format", "json",
	)
	if code != 0 || owner["status"] != "ok" {
		t.Fatalf("owner work begin = code %d envelope %#v", code, owner)
	}

	code, conflict := invokeCoordinationCLI(t,
		"work", "claim",
		"--project-root", root,
		"--current-work-id", "work-cli-claimant",
		"--current-work-fence", "1",
		"--task-ref", "fast:claimant",
		"--write-scope-json", `["src/local.go","src/shared.go"]`,
		"--format", "json",
	)
	if code != 10 || conflict["status"] != "blocked" {
		t.Fatalf("conflicting complete claim = code %d envelope %#v, want blocked", code, conflict)
	}
	code, shown := invokeCoordinationCLI(t, "work", "show", "work-cli-claimant", "--project-root", root, "--format", "json")
	if code != 0 {
		t.Fatalf("show claimant after conflict = code %d envelope %#v", code, shown)
	}
	unchanged := requireObject(t, requireObject(t, shown, "data"), "work")
	if unchanged["revision"] != float64(1) || len(unchanged["write_intents"].([]any)) != 0 {
		t.Fatalf("failed batch claim mutated claimant = %#v", unchanged)
	}

	code, finished := invokeCoordinationCLI(t,
		"work", "finish", "work-cli-owner",
		"--project-root", root,
		"--expected-revision", "1",
		"--fence", "1",
		"--reason", "release for retry",
		"--format", "json",
	)
	if code != 0 || finished["status"] != "ok" {
		t.Fatalf("finish owner = code %d envelope %#v", code, finished)
	}
	code, claimed := invokeCoordinationCLI(t,
		"work", "claim",
		"--project-root", root,
		"--current-work-id", "work-cli-claimant",
		"--current-work-fence", "1",
		"--task-ref", "fast:claimant",
		"--write-scope-json", `["src/local.go","src/shared.go"]`,
		"--format", "json",
	)
	if code != 0 || claimed["status"] != "ok" {
		t.Fatalf("complete work claim = code %d envelope %#v", code, claimed)
	}
	receipt := requireObject(t, requireObject(t, claimed, "data"), "work_claim")
	if receipt["schema"] != "work-scope-claim-v1" || receipt["task_ref"] != "fast:claimant" ||
		receipt["claimed_intent_count"] != float64(2) || receipt["work_revision"] != float64(2) {
		t.Fatalf("work claim receipt = %#v", receipt)
	}
}

func TestWorkBoardCLIBranchPolicyKeepsCurrentOnlyForConcurrentWork(t *testing.T) {
	root := initCoordinationCLIRepository(t)
	intentsJSON := marshalWorkBoardCLIJSON(t, []map[string]any{{
		"path": "src/concurrent.go", "operation": "modify", "confidence": "confirmed",
	}})
	code, created := invokeCoordinationCLI(t,
		"work", "begin",
		"--project-root", root,
		"--work-id", "concurrent-agent-work",
		"--summary", "Concurrent agent task",
		"--agent-id", "agent-b",
		"--adapter-id", "codex",
		"--lease-seconds", "1800",
		"--intents-json", intentsJSON,
		"--format", "json",
	)
	if code != 0 || created["status"] != "ok" {
		t.Fatalf("work begin = code %d envelope %#v", code, created)
	}

	code, guarded := invokeCoordinationCLI(t,
		"board", "branch-policy",
		"--project-root", root,
		"--current-work-id", "current-agent-work",
		"--format", "json",
	)
	if code != 0 || guarded["status"] != "ok" {
		t.Fatalf("guarded branch policy = code %d envelope %#v", code, guarded)
	}
	guardedData := requireObject(t, guarded, "data")
	if guardedData["policy"] != "keep-current" || guardedData["concurrent_work_count"] != float64(1) {
		t.Fatalf("guarded branch policy = %#v", guardedData)
	}

	work := requireObject(t, requireObject(t, created, "data"), "work")
	code, finished := invokeCoordinationCLI(t,
		"work", "finish", "concurrent-agent-work",
		"--project-root", root,
		"--expected-revision", "1",
		"--fence", "1",
		"--reason", "done",
		"--format", "json",
	)
	if code != 0 || finished["status"] != "ok" || work["work_id"] != "concurrent-agent-work" {
		t.Fatalf("work finish = code %d envelope %#v", code, finished)
	}

	code, normal := invokeCoordinationCLI(t,
		"board", "branch-policy",
		"--project-root", root,
		"--current-work-id", "current-agent-work",
		"--format", "json",
	)
	if code != 0 || normal["status"] != "ok" {
		t.Fatalf("default branch policy = code %d envelope %#v", code, normal)
	}
	normalData := requireObject(t, normal, "data")
	if normalData["policy"] != "default" || normalData["concurrent_work_count"] != float64(0) {
		t.Fatalf("default branch policy = %#v", normalData)
	}
}

func TestWorkBoardCLIFeatureBootstrapRegistersExactScopeBeforeReturningPolicy(t *testing.T) {
	root := initCoordinationCLIRepository(t)
	existingIntents := marshalWorkBoardCLIJSON(t, []map[string]any{{
		"path": "src/existing.go", "operation": "modify", "confidence": "confirmed",
	}})
	code, existing := invokeCoordinationCLI(t,
		"work", "begin",
		"--project-root", root,
		"--work-id", "existing-feature-work",
		"--summary", "Existing feature work",
		"--agent-id", "agent-a",
		"--adapter-id", "codex",
		"--lease-seconds", "1800",
		"--intents-json", existingIntents,
		"--format", "json",
	)
	if code != 0 || existing["status"] != "ok" {
		t.Fatalf("existing work begin = code %d envelope %#v", code, existing)
	}

	featureID := "001-shared-board"
	featureDir := filepath.Join(root, ".specify", "features", featureID)
	code, bootstrapped := invokeCoordinationCLI(t,
		"board", "feature-bootstrap",
		"--project-root", root,
		"--work-id", "feature-bootstrap-work",
		"--feature-id", featureID,
		"--feature-dir", featureDir,
		"--summary", "Specify shared board feature",
		"--agent-id", "agent-b",
		"--adapter-id", "codex",
		"--lease-seconds", "1800",
		"--format", "json",
	)
	if code != 0 || bootstrapped["status"] != "ok" {
		t.Fatalf("feature bootstrap = code %d envelope %#v", code, bootstrapped)
	}
	data := requireObject(t, bootstrapped, "data")
	work := requireObject(t, data, "work")
	if work["work_id"] != "feature-bootstrap-work" || work["task_ref"] != "feature:"+featureID {
		t.Fatalf("feature bootstrap work = %#v", work)
	}
	intents := work["write_intents"].([]any)
	if len(intents) != 1 {
		t.Fatalf("feature bootstrap intents = %#v, want one exact feature directory", intents)
	}
	intent := requireObjectValue(t, intents[0])
	if intent["path"] != ".specify/features/"+featureID || intent["operation"] != "create" || intent["confidence"] != "confirmed" {
		t.Fatalf("feature bootstrap intent = %#v", intent)
	}
	policy := requireObject(t, data, "feature_branch_policy")
	if policy["policy"] != "keep-current" || policy["concurrent_work_count"] != float64(1) {
		t.Fatalf("feature bootstrap policy = %#v", policy)
	}

	code, duplicate := invokeCoordinationCLI(t,
		"board", "feature-bootstrap",
		"--project-root", root,
		"--work-id", "duplicate-feature-bootstrap",
		"--feature-id", featureID,
		"--feature-dir", featureDir,
		"--summary", "Duplicate feature bootstrap",
		"--agent-id", "agent-c",
		"--adapter-id", "codex",
		"--lease-seconds", "1800",
		"--format", "json",
	)
	if code != 10 || duplicate["status"] != "blocked" {
		t.Fatalf("duplicate feature bootstrap = code %d envelope %#v, want blocked", code, duplicate)
	}
}

func TestWorkBoardCLIFeatureBootstrapRejectsMismatchedOrEscapingDirectory(t *testing.T) {
	root := initCoordinationCLIRepository(t)
	for name, featureDir := range map[string]string{
		"mismatched": filepath.Join(root, ".specify", "features", "002-other"),
		"escaping":   filepath.Join(root, "..", "001-shared-board"),
	} {
		t.Run(name, func(t *testing.T) {
			code, payload := invokeCoordinationCLI(t,
				"board", "feature-bootstrap",
				"--project-root", root,
				"--feature-id", "001-shared-board",
				"--feature-dir", featureDir,
				"--summary", "Invalid feature bootstrap",
				"--agent-id", "agent-a",
				"--adapter-id", "codex",
				"--format", "json",
			)
			if code != 2 || payload["status"] != "usage-error" {
				t.Fatalf("invalid feature bootstrap = code %d envelope %#v", code, payload)
			}
		})
	}
}

func TestWorkBoardCLIConcurrentFeatureBootstrapsNeverBothReceiveDefaultPolicy(t *testing.T) {
	root := initCoordinationCLIRepository(t)
	type bootstrapResult struct {
		code    int
		payload map[string]any
	}
	results := make(chan bootstrapResult, 2)
	start := make(chan struct{})
	var wait sync.WaitGroup
	for index := 1; index <= 2; index++ {
		index := index
		wait.Add(1)
		go func() {
			defer wait.Done()
			<-start
			featureID := fmt.Sprintf("%03d-concurrent-feature", index)
			code, payload := invokeCoordinationCLI(t,
				"board", "feature-bootstrap",
				"--project-root", root,
				"--work-id", fmt.Sprintf("feature-bootstrap-%d", index),
				"--feature-id", featureID,
				"--feature-dir", filepath.Join(root, ".specify", "features", featureID),
				"--summary", fmt.Sprintf("Concurrent feature %d", index),
				"--agent-id", fmt.Sprintf("agent-%d", index),
				"--adapter-id", "codex",
				"--lease-seconds", "1800",
				"--format", "json",
			)
			results <- bootstrapResult{code: code, payload: payload}
		}()
	}
	close(start)
	wait.Wait()
	close(results)

	defaultCount := 0
	keepCurrentCount := 0
	for result := range results {
		if result.code != 0 || result.payload["status"] != "ok" {
			t.Fatalf("concurrent feature bootstrap = code %d envelope %#v", result.code, result.payload)
		}
		policy := requireObject(t, requireObject(t, result.payload, "data"), "feature_branch_policy")["policy"]
		switch policy {
		case "default":
			defaultCount++
		case "keep-current":
			keepCurrentCount++
		default:
			t.Fatalf("concurrent feature bootstrap policy = %#v", policy)
		}
	}
	if defaultCount > 1 || keepCurrentCount == 0 {
		t.Fatalf("concurrent policies = %d default / %d keep-current, want at most one default", defaultCount, keepCurrentCount)
	}
}

func TestWorkBoardCLIReconcilesDirtyInterruptedWorkAndResumesWithNewFence(t *testing.T) {
	root := initCoordinationCLIRepository(t)
	gitRun(t, root, "config", "user.name", "Work Board Test")
	gitRun(t, root, "config", "user.email", "work-board@example.invalid")
	gitRun(t, root, "config", "commit.gpgsign", "false")
	if err := os.MkdirAll(filepath.Join(root, "src"), 0o755); err != nil {
		t.Fatal(err)
	}
	filePath := filepath.Join(root, "src", "dirty.go")
	if err := os.WriteFile(filePath, []byte("package dirty\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	gitRun(t, root, "add", "src/dirty.go")
	gitRun(t, root, "commit", "-m", "baseline")

	intentsJSON := marshalWorkBoardCLIJSON(t, []map[string]any{{
		"path": "src/dirty.go", "operation": "modify", "reason": "edit dirty file", "confidence": "confirmed",
	}})
	code, created := invokeCoordinationCLI(t,
		"work", "begin",
		"--project-root", root,
		"--work-id", "work-cli-dirty",
		"--summary", "Edit dirty file",
		"--agent-id", "codex-a",
		"--adapter-id", "codex",
		"--lease-seconds", "1800",
		"--intents-json", intentsJSON,
		"--format", "json",
	)
	if code != 0 {
		t.Fatalf("work begin = code %d envelope %#v", code, created)
	}
	if err := os.WriteFile(filePath, []byte("package dirty\n\nconst changed = true\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	repository, err := runcontrol.ResolveRepository(context.Background(), root)
	if err != nil {
		t.Fatal(err)
	}
	database, err := sql.Open("sqlite", repository.DatabasePath)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := database.Exec(`UPDATE work_items SET lease_until_ms = 1 WHERE work_id = 'work-cli-dirty'`); err != nil {
		_ = database.Close()
		t.Fatal(err)
	}
	if err := database.Close(); err != nil {
		t.Fatal(err)
	}

	code, reconciled := invokeCoordinationCLI(t, "board", "reconcile", "--project-root", root, "--format", "json")
	if code != 0 || reconciled["status"] != "ok" {
		t.Fatalf("board reconcile = code %d envelope %#v", code, reconciled)
	}
	interrupted := reconciled["items"].([]any)
	if len(interrupted) != 1 {
		t.Fatalf("reconciled items = %#v", interrupted)
	}
	interruptedWork := requireObjectValue(t, interrupted[0])
	if interruptedWork["status"] != "interrupted" || interruptedWork["recovery_hold"] != true || interruptedWork["fence"] != float64(2) {
		t.Fatalf("interrupted work = %#v", interruptedWork)
	}

	code, resumed := invokeCoordinationCLI(t,
		"work", "resume", "work-cli-dirty",
		"--project-root", root,
		"--expected-revision", "2",
		"--agent-id", "codex-resumer",
		"--adapter-id", "codex",
		"--lease-seconds", "1800",
		"--next-action", "verify preserved edit",
		"--format", "json",
	)
	if code != 0 || resumed["status"] != "ok" {
		t.Fatalf("work resume = code %d envelope %#v", code, resumed)
	}
	resumedWork := requireObject(t, requireObject(t, resumed, "data"), "work")
	if resumedWork["status"] != "active" || resumedWork["recovery_hold"] != false || resumedWork["fence"] != float64(3) {
		t.Fatalf("resumed work = %#v", resumedWork)
	}
}

func TestWorkBoardCLIInterruptSupportsImmediateRestartRecoveryBeforeLeaseExpiry(t *testing.T) {
	root := initCoordinationCLIRepository(t)
	gitRun(t, root, "config", "user.name", "Work Board Test")
	gitRun(t, root, "config", "user.email", "work-board@example.invalid")
	gitRun(t, root, "config", "commit.gpgsign", "false")
	if err := os.MkdirAll(filepath.Join(root, "src"), 0o755); err != nil {
		t.Fatal(err)
	}
	filePath := filepath.Join(root, "src", "restart.go")
	if err := os.WriteFile(filePath, []byte("package restart\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	gitRun(t, root, "add", "src/restart.go")
	gitRun(t, root, "commit", "-m", "baseline")

	intentsJSON := marshalWorkBoardCLIJSON(t, []map[string]any{{
		"path": "src/restart.go", "operation": "modify", "reason": "edit before restart", "confidence": "confirmed",
	}})
	code, created := invokeCoordinationCLI(t,
		"work", "begin",
		"--project-root", root,
		"--work-id", "work-cli-restart",
		"--summary", "Resume after computer restart",
		"--agent-id", "codex-before-restart",
		"--adapter-id", "codex",
		"--lease-seconds", "1800",
		"--intents-json", intentsJSON,
		"--format", "json",
	)
	if code != 0 || created["status"] != "ok" {
		t.Fatalf("work begin = code %d envelope %#v", code, created)
	}
	if err := os.WriteFile(filePath, []byte("package restart\n\nconst preserved = true\n"), 0o644); err != nil {
		t.Fatal(err)
	}

	code, interrupted := invokeCoordinationCLI(t,
		"work", "interrupt", "work-cli-restart",
		"--project-root", root,
		"--expected-revision", "1",
		"--fence", "1",
		"--reason", "confirmed previous owner session ended after computer restart",
		"--format", "json",
	)
	if code != 0 || interrupted["status"] != "ok" {
		t.Fatalf("work interrupt = code %d envelope %#v", code, interrupted)
	}
	interruptedWork := requireObject(t, requireObject(t, interrupted, "data"), "work")
	if interruptedWork["status"] != "interrupted" || interruptedWork["recovery_hold"] != true ||
		interruptedWork["revision"] != float64(2) || interruptedWork["fence"] != float64(2) {
		t.Fatalf("interrupted work = %#v", interruptedWork)
	}
	if interruptedWork["recovery_action"] != "resume_or_abandon_after_inspection" {
		t.Fatalf("interrupted recovery_action = %#v", interruptedWork["recovery_action"])
	}
	if interruptedWork["recovery_detail"] != "inspect preserved workspace changes, then resume or abandon this work" {
		t.Fatalf("interrupted recovery_detail = %#v", interruptedWork["recovery_detail"])
	}
	observed := interruptedWork["observed_paths"].([]any)
	if len(observed) != 1 || observed[0] != "src/restart.go" {
		t.Fatalf("interrupted observed paths = %#v", observed)
	}

	recoveryIntents := marshalWorkBoardCLIJSON(t, []map[string]any{{
		"path": "src/restart.go", "operation": "modify", "reason": "replacement work", "confidence": "confirmed",
	}})
	code, recoveryConflict := invokeCoordinationCLI(t,
		"work", "begin",
		"--project-root", root,
		"--work-id", "work-cli-restart-replacement",
		"--summary", "Replacement after interrupted work",
		"--agent-id", "codex-b",
		"--adapter-id", "codex",
		"--lease-seconds", "1800",
		"--intents-json", recoveryIntents,
		"--format", "json",
	)
	if code != 10 || recoveryConflict["status"] != "blocked" {
		t.Fatalf("recovery conflict = code %d envelope %#v", code, recoveryConflict)
	}
	recoveryData := requireObject(t, recoveryConflict, "data")
	recoveryResolution := requireObject(t, recoveryData, "resolution_action")
	if recoveryResolution["owner_work_id"] != "work-cli-restart" ||
		recoveryResolution["owner_intent_status"] != "recovery" ||
		recoveryResolution["agent_recovery_candidate"] != true ||
		recoveryResolution["requires_owner_termination_evidence"] != true ||
		recoveryResolution["requires_preserved_change_inspection"] != true ||
		recoveryResolution["after_inspection"] != "resume-or-abandon-after-inspection" {
		t.Fatalf("recovery conflict resolution_action = %#v", recoveryResolution)
	}
	recoveryShowArgv := requireStringArray(t, recoveryConflict, "show_argv")
	if len(recoveryShowArgv) < 4 || recoveryShowArgv[3] != "work-cli-restart" {
		t.Fatalf("recovery conflict show_argv = %#v", recoveryShowArgv)
	}

	code, resumed := invokeCoordinationCLI(t,
		"work", "resume", "work-cli-restart",
		"--project-root", root,
		"--expected-revision", "2",
		"--agent-id", "codex-after-restart",
		"--adapter-id", "codex",
		"--lease-seconds", "1800",
		"--next-action", "continue preserved edit",
		"--format", "json",
	)
	if code != 0 || resumed["status"] != "ok" {
		t.Fatalf("work resume = code %d envelope %#v", code, resumed)
	}
	resumedWork := requireObject(t, requireObject(t, resumed, "data"), "work")
	if resumedWork["status"] != "active" || resumedWork["recovery_hold"] != false || resumedWork["fence"] != float64(3) {
		t.Fatalf("resumed work = %#v", resumedWork)
	}
}

func TestWorkBoardCLIResumeDefaultsToTheInterruptedWorktree(t *testing.T) {
	root := initCoordinationCLIRepository(t)
	gitRun(t, root, "config", "user.name", "Work Board Test")
	gitRun(t, root, "config", "user.email", "work-board@example.invalid")
	gitRun(t, root, "config", "commit.gpgsign", "false")
	readme := filepath.Join(root, "README.md")
	if err := os.WriteFile(readme, []byte("baseline\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	gitRun(t, root, "add", "README.md")
	gitRun(t, root, "commit", "-m", "baseline")
	linkedRoot := filepath.Join(t.TempDir(), "worker-worktree")
	gitRun(t, root, "worktree", "add", "--detach", linkedRoot, "HEAD")

	intentsJSON := marshalWorkBoardCLIJSON(t, []map[string]any{{
		"path": "README.md", "operation": "modify", "reason": "worker edit", "confidence": "confirmed",
	}})
	code, created := invokeCoordinationCLI(t,
		"work", "begin",
		"--project-root", root,
		"--workspace-root", linkedRoot,
		"--work-id", "work-cli-linked-resume",
		"--summary", "Resume linked worktree",
		"--agent-id", "codex-a",
		"--adapter-id", "codex",
		"--lease-seconds", "1800",
		"--intents-json", intentsJSON,
		"--format", "json",
	)
	if code != 0 {
		t.Fatalf("work begin = code %d envelope %#v", code, created)
	}
	if err := os.WriteFile(filepath.Join(linkedRoot, "README.md"), []byte("preserved worker edit\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	repository, err := runcontrol.ResolveRepository(context.Background(), root)
	if err != nil {
		t.Fatal(err)
	}
	database, err := sql.Open("sqlite", repository.DatabasePath)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := database.Exec(`UPDATE work_items SET lease_until_ms = 1 WHERE work_id = 'work-cli-linked-resume'`); err != nil {
		_ = database.Close()
		t.Fatal(err)
	}
	if err := database.Close(); err != nil {
		t.Fatal(err)
	}
	code, reconciled := invokeCoordinationCLI(t, "board", "reconcile", "--project-root", root, "--format", "json")
	if code != 0 || len(reconciled["items"].([]any)) != 1 {
		t.Fatalf("board reconcile = code %d envelope %#v", code, reconciled)
	}

	code, resumed := invokeCoordinationCLI(t,
		"work", "resume", "work-cli-linked-resume",
		"--project-root", root,
		"--expected-revision", "2",
		"--agent-id", "codex-resumer",
		"--adapter-id", "codex",
		"--lease-seconds", "1800",
		"--format", "json",
	)
	if code != 0 {
		t.Fatalf("work resume = code %d envelope %#v", code, resumed)
	}
	resumedWork := requireObject(t, requireObject(t, resumed, "data"), "work")
	if filepath.Clean(resumedWork["workspace_root"].(string)) != filepath.Clean(linkedRoot) {
		t.Fatalf("resumed workspace_root = %q, want interrupted worktree %q", resumedWork["workspace_root"], linkedRoot)
	}
}

func TestWorkBoardCLIReconcilePreservesScopeWhenWorkspaceCannotBeInspected(t *testing.T) {
	root := initCoordinationCLIRepository(t)
	missingWorkspace := filepath.Join(root, "missing-worker-worktree")
	intentsJSON := marshalWorkBoardCLIJSON(t, []map[string]any{{
		"path": "src/missing.go", "operation": "modify", "reason": "worker edit", "confidence": "confirmed",
	}})
	code, created := invokeCoordinationCLI(t,
		"work", "begin",
		"--project-root", root,
		"--work-id", "work-cli-missing-workspace",
		"--summary", "Recover missing workspace",
		"--agent-id", "codex-a",
		"--adapter-id", "codex",
		"--lease-seconds", "1800",
		"--intents-json", intentsJSON,
		"--format", "json",
	)
	if code != 0 {
		t.Fatalf("work begin = code %d envelope %#v", code, created)
	}
	repository, err := runcontrol.ResolveRepository(context.Background(), root)
	if err != nil {
		t.Fatal(err)
	}
	database, err := sql.Open("sqlite", repository.DatabasePath)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := database.Exec(
		`UPDATE work_items SET lease_until_ms = 1, workspace_root = ? WHERE work_id = 'work-cli-missing-workspace'`,
		missingWorkspace,
	); err != nil {
		_ = database.Close()
		t.Fatal(err)
	}
	if err := database.Close(); err != nil {
		t.Fatal(err)
	}

	code, reconciled := invokeCoordinationCLI(t, "board", "reconcile", "--project-root", root, "--format", "json")
	if code != 0 || reconciled["status"] != "ok" {
		t.Fatalf("board reconcile = code %d envelope %#v", code, reconciled)
	}
	items := reconciled["items"].([]any)
	if len(items) != 1 {
		t.Fatalf("reconciled items = %#v", items)
	}
	work := requireObjectValue(t, items[0])
	if work["status"] != "interrupted" || work["recovery_hold"] != true {
		t.Fatalf("missing workspace recovery = %#v", work)
	}
	warnings := requireObject(t, reconciled, "data")["inspection_warnings"].([]any)
	if len(warnings) != 1 {
		t.Fatalf("inspection warnings = %#v", warnings)
	}
	code, resumeBlocked := invokeCoordinationCLI(t,
		"work", "resume", "work-cli-missing-workspace",
		"--project-root", root,
		"--expected-revision", "2",
		"--agent-id", "codex-resumer",
		"--adapter-id", "codex",
		"--lease-seconds", "1800",
		"--format", "json",
	)
	if code != 10 || resumeBlocked["status"] != "blocked" {
		t.Fatalf("missing workspace resume = code %d envelope %#v, want blocked", code, resumeBlocked)
	}
	blockers := resumeBlocked["blockers"].([]any)
	if len(blockers) != 1 || !strings.Contains(blockers[0].(string), "--workspace-root") {
		t.Fatalf("missing workspace resume blockers = %#v", blockers)
	}

	code, abandoned := invokeCoordinationCLI(t,
		"work", "abandon", "work-cli-missing-workspace",
		"--project-root", root,
		"--expected-revision", "2",
		"--fence", "2",
		"--reason", "missing worker worktree inspected and retired",
		"--format", "json",
	)
	if code != 0 || requireObject(t, requireObject(t, abandoned, "data"), "work")["status"] != "abandoned" {
		t.Fatalf("work abandon = code %d envelope %#v", code, abandoned)
	}
}

func TestWorkBoardCLIRejectsWorkspaceFromAnotherRepository(t *testing.T) {
	root := initCoordinationCLIRepository(t)
	otherRoot := initCoordinationCLIRepository(t)
	intentsJSON := marshalWorkBoardCLIJSON(t, []map[string]any{{
		"path": "src/cross-repo.go", "operation": "modify", "confidence": "confirmed",
	}})
	code, payload := invokeCoordinationCLI(t,
		"work", "begin",
		"--project-root", root,
		"--work-id", "work-cli-cross-repo",
		"--summary", "Reject unrelated workspace",
		"--agent-id", "codex-a",
		"--adapter-id", "codex",
		"--workspace-root", otherRoot,
		"--lease-seconds", "1800",
		"--intents-json", intentsJSON,
		"--format", "json",
	)
	if code != 2 || payload["status"] != "invalid" {
		t.Fatalf("cross-repository work begin = code %d envelope %#v", code, payload)
	}
}

func marshalWorkBoardCLIJSON(t *testing.T, value any) string {
	t.Helper()
	encoded, err := json.Marshal(value)
	if err != nil {
		t.Fatal(err)
	}
	return string(encoded)
}
