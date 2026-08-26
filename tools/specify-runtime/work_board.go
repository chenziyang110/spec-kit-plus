package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"runtime"
	"strconv"
	"strings"
	"time"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runcontrol"
)

const defaultWorkLeaseSeconds int64 = 30 * 60
const maximumWorkLeaseSeconds int64 = 24 * 60 * 60

func runWork(args []string, stdout io.Writer) int {
	if len(args) == 0 {
		return writeEnvelope(stdout, workBoardUsageEnvelope("missing work subcommand"))
	}
	if args[0] == "--help" || args[0] == "-h" || args[0] == "help" {
		return writeWorkHelp(stdout)
	}
	switch args[0] {
	case "begin":
		return workBegin(args[1:], stdout)
	case "show":
		return workShow(args[1:], stdout)
	case "claim":
		return workClaim(args[1:], stdout)
	case "scope-add":
		return workScopeAdd(args[1:], stdout)
	case "checkpoint":
		return workCheckpoint(args[1:], stdout)
	case "block":
		return workTransition(args[1:], stdout, runcontrol.WorkBlocked)
	case "finish":
		return workTransition(args[1:], stdout, runcontrol.WorkCompleted)
	case "abandon":
		return workTransition(args[1:], stdout, runcontrol.WorkAbandoned)
	case "interrupt":
		return workInterrupt(args[1:], stdout)
	case "resume":
		return workResume(args[1:], stdout)
	default:
		return writeEnvelope(stdout, workBoardUsageEnvelope(fmt.Sprintf("unknown work subcommand %q", args[0])))
	}
}

func runBoard(args []string, stdout io.Writer) int {
	if len(args) == 0 {
		return writeEnvelope(stdout, workBoardUsageEnvelope("missing board subcommand"))
	}
	if args[0] == "--help" || args[0] == "-h" || args[0] == "help" {
		return writeBoardHelp(stdout)
	}
	switch args[0] {
	case "show":
		return boardShow(args[1:], stdout)
	case "owner":
		return boardOwner(args[1:], stdout)
	case "reconcile":
		return boardReconcile(args[1:], stdout)
	case "branch-policy":
		return boardBranchPolicy(args[1:], stdout)
	case "feature-bootstrap":
		return boardFeatureBootstrap(args[1:], stdout)
	default:
		return writeEnvelope(stdout, workBoardUsageEnvelope(fmt.Sprintf("unknown board subcommand %q", args[0])))
	}
}

func writeWorkHelp(stdout io.Writer) int {
	_, _ = fmt.Fprintln(stdout, "specify-runtime work commands:")
	for _, command := range []string{"begin", "show", "claim", "scope-add", "checkpoint", "block", "finish", "abandon", "interrupt", "resume"} {
		_, _ = fmt.Fprintf(stdout, "  %s\n", command)
	}
	return 0
}

func writeBoardHelp(stdout io.Writer) int {
	_, _ = fmt.Fprintln(stdout, "specify-runtime board commands:")
	for _, command := range []string{"show", "owner", "reconcile", "branch-policy", "feature-bootstrap"} {
		_, _ = fmt.Fprintf(stdout, "  %s\n", command)
	}
	return 0
}

func workBegin(args []string, stdout io.Writer) int {
	parsed, err := parseRunCommandArgs(args, 0,
		"--project-root", "--work-id", "--parent-work-id", "--run-id", "--task-ref",
		"--summary", "--agent-id", "--adapter-id", "--workspace-root", "--base-commit",
		"--next-action", "--lease-seconds", "--intents-json", "--format",
	)
	if err != nil {
		return writeEnvelope(stdout, workBoardUsageEnvelope(err.Error()))
	}
	if err := validateWorkBoardFormat(parsed); err != nil {
		return writeEnvelope(stdout, workBoardUsageEnvelope(err.Error()))
	}
	for _, required := range []string{"--summary", "--agent-id", "--adapter-id"} {
		if strings.TrimSpace(parsed.option(required, "")) == "" {
			return writeEnvelope(stdout, workBoardUsageEnvelope("work begin requires "+required))
		}
	}
	leaseUntil, err := workLeaseUntil(parsed)
	if err != nil {
		return writeEnvelope(stdout, workBoardUsageEnvelope(err.Error()))
	}
	intents, err := parseWriteIntentsJSON(parsed.option("--intents-json", "[]"))
	if err != nil {
		return writeEnvelope(stdout, workBoardUsageEnvelope(err.Error()))
	}
	ctx := context.Background()
	projectRoot := parsed.option("--project-root", ".")
	repository, err := runcontrol.ResolveRepository(ctx, projectRoot)
	if err != nil {
		return writeEnvelope(stdout, workBoardErrorEnvelope("resolve Work Board repository", err))
	}
	workspaceRoot, err := resolveWorkBoardWorkspace(ctx, repository, parsed.option("--workspace-root", repository.Root))
	if err != nil {
		return writeEnvelope(stdout, workBoardErrorEnvelope("validate Work Board workspace", err))
	}
	baseCommit := strings.TrimSpace(parsed.option("--base-commit", ""))
	if baseCommit == "" {
		baseCommit, _ = runcontrol.ReadHeadCommit(ctx, workspaceRoot)
	}
	store, err := runcontrol.Open(ctx, repository.DatabasePath)
	if err != nil {
		return writeEnvelope(stdout, workBoardErrorEnvelope("open Work Board", err))
	}
	work, writeIntents, operationErr := store.BeginWork(ctx, runcontrol.BeginWorkParams{
		WorkID:        parsed.option("--work-id", ""),
		ParentWorkID:  parsed.option("--parent-work-id", ""),
		RunID:         parsed.option("--run-id", ""),
		TaskRef:       parsed.option("--task-ref", ""),
		Summary:       parsed.option("--summary", ""),
		AgentID:       parsed.option("--agent-id", ""),
		AdapterID:     parsed.option("--adapter-id", ""),
		WorkspaceRoot: workspaceRoot,
		BaseCommit:    baseCommit,
		NextAction:    parsed.option("--next-action", ""),
		LeaseUntil:    leaseUntil,
		WriteIntents:  intents,
	})
	closeErr := store.Close()
	if operationErr != nil {
		return writeEnvelope(stdout, workBoardErrorEnvelope("begin work", operationErr))
	}
	if closeErr != nil {
		return writeEnvelope(stdout, workBoardErrorEnvelope("close Work Board", closeErr))
	}
	env := NewEnvelope("ok", "work registered on shared board")
	env.Data["work"] = workItemDTO(work, writeIntents)
	env.ShowArgv = workShowArgv(work.WorkID, projectRoot)
	env.NextArgv = []string{"specify-runtime", "board", "show", "--project-root", projectRoot, "--format", "json"}
	return writeEnvelope(stdout, env)
}

func workShow(args []string, stdout io.Writer) int {
	parsed, err := parseRunCommandArgs(args, 1, "--project-root", "--format")
	if err != nil {
		return writeEnvelope(stdout, workBoardUsageEnvelope(err.Error()))
	}
	if err := validateWorkBoardFormat(parsed); err != nil {
		return writeEnvelope(stdout, workBoardUsageEnvelope(err.Error()))
	}
	workID := strings.TrimSpace(parsed.positionals[0])
	ctx := context.Background()
	view, err := runcontrol.OpenViewForRepository(ctx, parsed.option("--project-root", "."))
	if err != nil {
		return writeEnvelope(stdout, workBoardErrorEnvelope("open Work Board", err))
	}
	work, intents, operationErr := view.GetWork(ctx, workID)
	closeErr := view.Close()
	if operationErr != nil {
		return writeEnvelope(stdout, workBoardErrorEnvelope("show work", operationErr))
	}
	if closeErr != nil {
		return writeEnvelope(stdout, workBoardErrorEnvelope("close Work Board", closeErr))
	}
	env := NewEnvelope("ok", "work loaded")
	env.Data["work"] = workItemDTO(work, intents)
	env.ShowArgv = workShowArgv(work.WorkID, parsed.option("--project-root", "."))
	return writeEnvelope(stdout, env)
}

func workClaim(args []string, stdout io.Writer) int {
	parsed, err := parseRunCommandArgs(args, 0,
		"--project-root", "--current-work-id", "--current-work-fence", "--task-ref",
		"--write-scope-json", "--reason", "--format",
	)
	if err != nil {
		return writeEnvelope(stdout, workBoardUsageEnvelope(err.Error()))
	}
	if err := validateWorkBoardFormat(parsed); err != nil {
		return writeEnvelope(stdout, workBoardUsageEnvelope(err.Error()))
	}
	taskRef := strings.TrimSpace(parsed.option("--task-ref", ""))
	if taskRef == "" {
		return writeEnvelope(stdout, workBoardUsageEnvelope("work claim requires --task-ref"))
	}
	rawScope, present := parsed.options["--write-scope-json"]
	if !present {
		return writeEnvelope(stdout, workBoardUsageEnvelope("work claim requires --write-scope-json"))
	}
	writeScope, err := parseStringListJSON(rawScope, "--write-scope-json")
	if err != nil {
		return writeEnvelope(stdout, workBoardUsageEnvelope(err.Error()))
	}
	projectRoot := parsed.option("--project-root", ".")
	claim, err := claimCurrentWorkScope(currentWorkScopeClaimRequest{
		ProjectRoot:    projectRoot,
		Args:           args,
		AllowedTaskRef: []string{taskRef},
		WriteScope:     writeScope,
		Reason:         parsed.option("--reason", "claim-before-write for "+taskRef),
	})
	if err != nil {
		env := workBoardErrorEnvelope("claim work scope", err)
		env.Status = "blocked"
		env.Summary = "work scope claim blocked"
		if workID := strings.TrimSpace(optionValue(args, "--current-work-id", os.Getenv("SPECIFY_WORK_ID"))); workID != "" {
			env.ShowArgv = workShowArgv(workID, projectRoot)
		}
		return writeEnvelope(stdout, env)
	}
	env := NewEnvelope("ok", "complete write scope claimed all-or-none")
	env.Data["work_claim"] = claim
	env.ShowArgv = workShowArgv(anyString(claim["work_id"]), projectRoot)
	return writeEnvelope(stdout, env)
}

func workScopeAdd(args []string, stdout io.Writer) int {
	parsed, err := parseRunCommandArgs(args, 1,
		"--project-root", "--expected-revision", "--fence", "--path", "--operation",
		"--reason", "--confidence", "--format",
	)
	if err != nil {
		return writeEnvelope(stdout, workBoardUsageEnvelope(err.Error()))
	}
	if err := validateWorkBoardFormat(parsed); err != nil {
		return writeEnvelope(stdout, workBoardUsageEnvelope(err.Error()))
	}
	revision, fence, err := workRevisionAndFence(parsed)
	if err != nil {
		return writeEnvelope(stdout, workBoardUsageEnvelope(err.Error()))
	}
	if strings.TrimSpace(parsed.option("--path", "")) == "" {
		return writeEnvelope(stdout, workBoardUsageEnvelope("work scope-add requires --path"))
	}
	ctx := context.Background()
	projectRoot := parsed.option("--project-root", ".")
	store, err := runcontrol.OpenForRepository(ctx, projectRoot)
	if err != nil {
		return writeEnvelope(stdout, workBoardErrorEnvelope("open Work Board", err))
	}
	work, intent, operationErr := store.AddWorkIntent(ctx, runcontrol.AddWorkIntentParams{
		WorkID:           strings.TrimSpace(parsed.positionals[0]),
		ExpectedRevision: revision,
		Fence:            fence,
		Spec: runcontrol.WriteIntentSpec{
			Path:       parsed.option("--path", ""),
			Operation:  runcontrol.WriteOperation(parsed.option("--operation", string(runcontrol.WriteModify))),
			Reason:     parsed.option("--reason", ""),
			Confidence: runcontrol.WriteIntentConfidence(parsed.option("--confidence", string(runcontrol.IntentConfirmed))),
		},
	})
	closeErr := store.Close()
	if operationErr != nil {
		return writeEnvelope(stdout, workBoardErrorEnvelope("add work scope", operationErr))
	}
	if closeErr != nil {
		return writeEnvelope(stdout, workBoardErrorEnvelope("close Work Board", closeErr))
	}
	env := NewEnvelope("ok", "write intent added")
	env.Data["work"] = workItemDTO(work, nil)
	env.Data["write_intent"] = writeIntentDTO(intent)
	env.ShowArgv = workShowArgv(work.WorkID, projectRoot)
	return writeEnvelope(stdout, env)
}

func workCheckpoint(args []string, stdout io.Writer) int {
	parsed, err := parseRunCommandArgs(args, 1,
		"--project-root", "--expected-revision", "--fence", "--lease-seconds",
		"--next-action", "--observed-paths-json", "--format",
	)
	if err != nil {
		return writeEnvelope(stdout, workBoardUsageEnvelope(err.Error()))
	}
	if err := validateWorkBoardFormat(parsed); err != nil {
		return writeEnvelope(stdout, workBoardUsageEnvelope(err.Error()))
	}
	revision, fence, err := workRevisionAndFence(parsed)
	if err != nil {
		return writeEnvelope(stdout, workBoardUsageEnvelope(err.Error()))
	}
	leaseUntil, err := workLeaseUntil(parsed)
	if err != nil {
		return writeEnvelope(stdout, workBoardUsageEnvelope(err.Error()))
	}
	observed, err := parseStringListJSON(parsed.option("--observed-paths-json", "[]"), "--observed-paths-json")
	if err != nil {
		return writeEnvelope(stdout, workBoardUsageEnvelope(err.Error()))
	}
	ctx := context.Background()
	projectRoot := parsed.option("--project-root", ".")
	store, err := runcontrol.OpenForRepository(ctx, projectRoot)
	if err != nil {
		return writeEnvelope(stdout, workBoardErrorEnvelope("open Work Board", err))
	}
	work, operationErr := store.CheckpointWork(ctx, runcontrol.CheckpointWorkParams{
		WorkID:           strings.TrimSpace(parsed.positionals[0]),
		ExpectedRevision: revision,
		Fence:            fence,
		LeaseUntil:       leaseUntil,
		NextAction:       parsed.option("--next-action", ""),
		ObservedPaths:    observed,
	})
	closeErr := store.Close()
	if operationErr != nil {
		return writeEnvelope(stdout, workBoardErrorEnvelope("checkpoint work", operationErr))
	}
	if closeErr != nil {
		return writeEnvelope(stdout, workBoardErrorEnvelope("close Work Board", closeErr))
	}
	env := NewEnvelope("ok", "work checkpoint recorded")
	env.Data["work"] = workItemDTO(work, nil)
	env.ShowArgv = workShowArgv(work.WorkID, projectRoot)
	return writeEnvelope(stdout, env)
}

func workTransition(args []string, stdout io.Writer, target runcontrol.WorkStatus) int {
	parsed, err := parseRunCommandArgs(args, 1,
		"--project-root", "--expected-revision", "--fence", "--reason", "--next-action", "--format",
	)
	if err != nil {
		return writeEnvelope(stdout, workBoardUsageEnvelope(err.Error()))
	}
	if err := validateWorkBoardFormat(parsed); err != nil {
		return writeEnvelope(stdout, workBoardUsageEnvelope(err.Error()))
	}
	revision, fence, err := workRevisionAndFence(parsed)
	if err != nil {
		return writeEnvelope(stdout, workBoardUsageEnvelope(err.Error()))
	}
	if strings.TrimSpace(parsed.option("--reason", "")) == "" {
		return writeEnvelope(stdout, workBoardUsageEnvelope("work transition requires --reason"))
	}
	ctx := context.Background()
	projectRoot := parsed.option("--project-root", ".")
	store, err := runcontrol.OpenForRepository(ctx, projectRoot)
	if err != nil {
		return writeEnvelope(stdout, workBoardErrorEnvelope("open Work Board", err))
	}
	work, operationErr := store.TransitionWork(ctx, runcontrol.TransitionWorkParams{
		WorkID:           strings.TrimSpace(parsed.positionals[0]),
		ExpectedRevision: revision,
		Fence:            fence,
		Target:           target,
		Reason:           parsed.option("--reason", ""),
		NextAction:       parsed.option("--next-action", ""),
	})
	closeErr := store.Close()
	if operationErr != nil {
		return writeEnvelope(stdout, workBoardErrorEnvelope("transition work", operationErr))
	}
	if closeErr != nil {
		return writeEnvelope(stdout, workBoardErrorEnvelope("close Work Board", closeErr))
	}
	env := NewEnvelope("ok", "work status updated")
	env.Data["work"] = workItemDTO(work, nil)
	env.ShowArgv = workShowArgv(work.WorkID, projectRoot)
	return writeEnvelope(stdout, env)
}

func workInterrupt(args []string, stdout io.Writer) int {
	parsed, err := parseRunCommandArgs(args, 1,
		"--project-root", "--expected-revision", "--fence", "--reason", "--next-action", "--format",
	)
	if err != nil {
		return writeEnvelope(stdout, workBoardUsageEnvelope(err.Error()))
	}
	if err := validateWorkBoardFormat(parsed); err != nil {
		return writeEnvelope(stdout, workBoardUsageEnvelope(err.Error()))
	}
	revision, fence, err := workRevisionAndFence(parsed)
	if err != nil {
		return writeEnvelope(stdout, workBoardUsageEnvelope(err.Error()))
	}
	if strings.TrimSpace(parsed.option("--reason", "")) == "" {
		return writeEnvelope(stdout, workBoardUsageEnvelope("work interrupt requires --reason"))
	}

	ctx := context.Background()
	projectRoot := parsed.option("--project-root", ".")
	store, err := runcontrol.OpenForRepository(ctx, projectRoot)
	if err != nil {
		return writeEnvelope(stdout, workBoardErrorEnvelope("open Work Board", err))
	}
	workID := strings.TrimSpace(parsed.positionals[0])
	current, intents, operationErr := store.GetWork(ctx, workID)
	observedPaths := []string(nil)
	inspectionWarning := ""
	if operationErr == nil {
		observedPaths, operationErr = runcontrol.InspectWorkspaceChanges(ctx, current.WorkspaceRoot)
		if operationErr != nil {
			inspectionWarning = operationErr.Error()
			operationErr = nil
			for _, intent := range intents {
				if intent.Status == runcontrol.WriteIntentActive || intent.Status == runcontrol.WriteIntentRecovery {
					observedPaths = append(observedPaths, intent.Path)
				}
			}
		}
	}
	var interrupted runcontrol.WorkItem
	if operationErr == nil {
		interrupted, operationErr = store.InterruptWork(ctx, runcontrol.InterruptWorkParams{
			WorkID:           workID,
			ExpectedRevision: revision,
			Fence:            fence,
			Reason:           parsed.option("--reason", ""),
			NextAction:       parsed.option("--next-action", ""),
			ObservedPaths:    observedPaths,
		})
	}
	closeErr := store.Close()
	if operationErr != nil {
		return writeEnvelope(stdout, workBoardErrorEnvelope("interrupt work", operationErr))
	}
	if closeErr != nil {
		return writeEnvelope(stdout, workBoardErrorEnvelope("close Work Board", closeErr))
	}
	env := NewEnvelope("ok", "work interrupted for explicit recovery")
	env.Data["work"] = workItemDTO(interrupted, nil)
	if inspectionWarning != "" {
		env.Data["inspection_warning"] = inspectionWarning
		env.Data["inspection_fallback"] = "declared_scopes_preserved"
	}
	env.ShowArgv = workShowArgv(interrupted.WorkID, projectRoot)
	return writeEnvelope(stdout, env)
}

func workResume(args []string, stdout io.Writer) int {
	parsed, err := parseRunCommandArgs(args, 1,
		"--project-root", "--expected-revision", "--agent-id", "--adapter-id",
		"--workspace-root", "--base-commit", "--next-action", "--lease-seconds", "--format",
	)
	if err != nil {
		return writeEnvelope(stdout, workBoardUsageEnvelope(err.Error()))
	}
	if err := validateWorkBoardFormat(parsed); err != nil {
		return writeEnvelope(stdout, workBoardUsageEnvelope(err.Error()))
	}
	revision, err := positiveWorkOption(parsed, "--expected-revision")
	if err != nil {
		return writeEnvelope(stdout, workBoardUsageEnvelope(err.Error()))
	}
	for _, required := range []string{"--agent-id", "--adapter-id"} {
		if strings.TrimSpace(parsed.option(required, "")) == "" {
			return writeEnvelope(stdout, workBoardUsageEnvelope("work resume requires "+required))
		}
	}
	leaseUntil, err := workLeaseUntil(parsed)
	if err != nil {
		return writeEnvelope(stdout, workBoardUsageEnvelope(err.Error()))
	}
	ctx := context.Background()
	projectRoot := parsed.option("--project-root", ".")
	repository, err := runcontrol.ResolveRepository(ctx, projectRoot)
	if err != nil {
		return writeEnvelope(stdout, workBoardErrorEnvelope("resolve Work Board repository", err))
	}
	store, err := runcontrol.Open(ctx, repository.DatabasePath)
	if err != nil {
		return writeEnvelope(stdout, workBoardErrorEnvelope("open Work Board", err))
	}
	workID := strings.TrimSpace(parsed.positionals[0])
	currentWork, _, err := store.GetWork(ctx, workID)
	if err != nil {
		_ = store.Close()
		return writeEnvelope(stdout, workBoardErrorEnvelope("load interrupted work", err))
	}
	workspaceCandidate := currentWork.WorkspaceRoot
	_, workspaceExplicit := parsed.options["--workspace-root"]
	if workspaceExplicit {
		workspaceCandidate = parsed.option("--workspace-root", "")
	}
	workspaceRoot, err := resolveWorkBoardWorkspace(ctx, repository, workspaceCandidate)
	if err != nil {
		_ = store.Close()
		if !workspaceExplicit {
			err = fmt.Errorf(
				"%w: interrupted workspace %q is unavailable: %v; pass --workspace-root with an inspected replacement worktree or abandon the interrupted work",
				runcontrol.ErrWorkspaceNotUsable,
				workspaceCandidate,
				err,
			)
		}
		return writeEnvelope(stdout, workBoardErrorEnvelope("validate Work Board workspace", err))
	}
	baseCommit := strings.TrimSpace(parsed.option("--base-commit", ""))
	if baseCommit == "" {
		baseCommit = currentWork.BaseCommit
		if workspaceExplicit || baseCommit == "" {
			baseCommit, _ = runcontrol.ReadHeadCommit(ctx, workspaceRoot)
		}
	}
	work, operationErr := store.ResumeWork(ctx, runcontrol.ResumeWorkParams{
		WorkID:           workID,
		ExpectedRevision: revision,
		AgentID:          parsed.option("--agent-id", ""),
		AdapterID:        parsed.option("--adapter-id", ""),
		WorkspaceRoot:    workspaceRoot,
		BaseCommit:       baseCommit,
		NextAction:       parsed.option("--next-action", ""),
		LeaseUntil:       leaseUntil,
	})
	closeErr := store.Close()
	if operationErr != nil {
		return writeEnvelope(stdout, workBoardErrorEnvelope("resume work", operationErr))
	}
	if closeErr != nil {
		return writeEnvelope(stdout, workBoardErrorEnvelope("close Work Board", closeErr))
	}
	env := NewEnvelope("ok", "interrupted work resumed under a new fence")
	env.Data["work"] = workItemDTO(work, nil)
	env.ShowArgv = workShowArgv(work.WorkID, projectRoot)
	return writeEnvelope(stdout, env)
}

func boardShow(args []string, stdout io.Writer) int {
	parsed, err := parseRunCommandArgs(args, 0, "--project-root", "--status", "--format")
	if err != nil {
		return writeEnvelope(stdout, workBoardUsageEnvelope(err.Error()))
	}
	if err := validateWorkBoardFormat(parsed); err != nil {
		return writeEnvelope(stdout, workBoardUsageEnvelope(err.Error()))
	}
	statuses, err := parseWorkStatuses(parsed.option("--status", ""))
	if err != nil {
		return writeEnvelope(stdout, workBoardUsageEnvelope(err.Error()))
	}
	if len(statuses) == 0 {
		statuses = []runcontrol.WorkStatus{
			runcontrol.WorkActive,
			runcontrol.WorkBlocked,
			runcontrol.WorkInterrupted,
		}
	}
	ctx := context.Background()
	projectRoot := parsed.option("--project-root", ".")
	view, err := runcontrol.OpenViewForRepository(ctx, projectRoot)
	if err != nil {
		if errors.Is(err, runcontrol.ErrNotFound) {
			env := NewEnvelope("ok", "shared Work Board is empty")
			env.ShowArgv = []string{"specify-runtime", "board", "show", "--project-root", projectRoot, "--format", "json"}
			return writeEnvelope(stdout, env)
		}
		return writeEnvelope(stdout, workBoardErrorEnvelope("open Work Board", err))
	}
	items, operationErr := view.ListWork(ctx, runcontrol.ListWorkParams{Statuses: statuses})
	boardItems := make([]any, 0, len(items))
	if operationErr == nil {
		for _, work := range items {
			_, intents, getErr := view.GetWork(ctx, work.WorkID)
			if getErr != nil {
				operationErr = getErr
				break
			}
			boardItems = append(boardItems, workItemDTO(work, intents))
		}
	}
	closeErr := view.Close()
	if operationErr != nil {
		return writeEnvelope(stdout, workBoardErrorEnvelope("show Work Board", operationErr))
	}
	if closeErr != nil {
		return writeEnvelope(stdout, workBoardErrorEnvelope("close Work Board", closeErr))
	}
	env := NewEnvelope("ok", "shared Work Board loaded")
	env.Items = boardItems
	env.Data["count"] = len(boardItems)
	env.ShowArgv = []string{"specify-runtime", "board", "show", "--project-root", projectRoot, "--format", "json"}
	return writeEnvelope(stdout, env)
}

func boardOwner(args []string, stdout io.Writer) int {
	parsed, err := parseRunCommandArgs(args, 1, "--project-root", "--format")
	if err != nil {
		return writeEnvelope(stdout, workBoardUsageEnvelope(err.Error()))
	}
	if err := validateWorkBoardFormat(parsed); err != nil {
		return writeEnvelope(stdout, workBoardUsageEnvelope(err.Error()))
	}
	ctx := context.Background()
	projectRoot := parsed.option("--project-root", ".")
	view, err := runcontrol.OpenViewForRepository(ctx, projectRoot)
	if err != nil {
		if errors.Is(err, runcontrol.ErrNotFound) {
			env := NewEnvelope("ok", "no active write owner")
			return writeEnvelope(stdout, env)
		}
		return writeEnvelope(stdout, workBoardErrorEnvelope("open Work Board", err))
	}
	owners, operationErr := view.FindWorkOwners(ctx, parsed.positionals[0])
	closeErr := view.Close()
	if operationErr != nil {
		return writeEnvelope(stdout, workBoardErrorEnvelope("find work owner", operationErr))
	}
	if closeErr != nil {
		return writeEnvelope(stdout, workBoardErrorEnvelope("close Work Board", closeErr))
	}
	env := NewEnvelope("ok", "active write owners loaded")
	for _, owner := range owners {
		item := workItemDTO(owner.Work, nil)
		item["matched_write_intent"] = writeIntentDTO(owner.Intent)
		env.Items = append(env.Items, item)
	}
	env.Data["path"] = parsed.positionals[0]
	env.Data["count"] = len(owners)
	return writeEnvelope(stdout, env)
}

func boardReconcile(args []string, stdout io.Writer) int {
	parsed, err := parseRunCommandArgs(args, 0, "--project-root", "--format")
	if err != nil {
		return writeEnvelope(stdout, workBoardUsageEnvelope(err.Error()))
	}
	if err := validateWorkBoardFormat(parsed); err != nil {
		return writeEnvelope(stdout, workBoardUsageEnvelope(err.Error()))
	}
	ctx := context.Background()
	projectRoot := parsed.option("--project-root", ".")
	store, err := runcontrol.OpenForRepository(ctx, projectRoot)
	if err != nil {
		return writeEnvelope(stdout, workBoardErrorEnvelope("open Work Board", err))
	}
	reconciliation, operationErr := store.ReconcileRepositoryWork(ctx, time.Now().UTC())
	closeErr := store.Close()
	if operationErr != nil {
		return writeEnvelope(stdout, workBoardErrorEnvelope("reconcile Work Board", operationErr))
	}
	if closeErr != nil {
		return writeEnvelope(stdout, workBoardErrorEnvelope("close Work Board", closeErr))
	}
	env := NewEnvelope("ok", "expired work leases reconciled")
	for _, work := range reconciliation.Interrupted {
		env.Items = append(env.Items, workItemDTO(work, nil))
	}
	warnings := make([]any, 0, len(reconciliation.InspectionWarnings))
	for _, warning := range reconciliation.InspectionWarnings {
		warnings = append(warnings, map[string]any{
			"workspace_root": warning.WorkspaceRoot,
			"reason":         warning.Reason,
			"fallback":       warning.Fallback,
		})
	}
	env.Data["interrupted_count"] = len(reconciliation.Interrupted)
	env.Data["inspection_warnings"] = warnings
	env.NextArgv = []string{"specify-runtime", "board", "show", "--project-root", projectRoot, "--format", "json"}
	return writeEnvelope(stdout, env)
}

func boardBranchPolicy(args []string, stdout io.Writer) int {
	parsed, err := parseRunCommandArgs(args, 0, "--project-root", "--current-work-id", "--format")
	if err != nil {
		return writeEnvelope(stdout, workBoardUsageEnvelope(err.Error()))
	}
	if err := validateWorkBoardFormat(parsed); err != nil {
		return writeEnvelope(stdout, workBoardUsageEnvelope(err.Error()))
	}
	ctx := context.Background()
	projectRoot := parsed.option("--project-root", ".")
	store, err := runcontrol.OpenForRepository(ctx, projectRoot)
	if err != nil {
		return writeEnvelope(stdout, workBoardErrorEnvelope("open Work Board", err))
	}
	now := time.Now().UTC()
	_, operationErr := store.ReconcileRepositoryWork(ctx, now)
	currentWorkID := strings.TrimSpace(parsed.option("--current-work-id", os.Getenv("SPECIFY_WORK_ID")))
	var decision runcontrol.FeatureBranchDecision
	if operationErr == nil {
		decision, operationErr = store.ResolveFeatureBranchPolicy(ctx, currentWorkID, now)
	}
	closeErr := store.Close()
	if operationErr != nil {
		return writeEnvelope(stdout, workBoardErrorEnvelope("resolve feature branch policy", operationErr))
	}
	if closeErr != nil {
		return writeEnvelope(stdout, workBoardErrorEnvelope("close Work Board", closeErr))
	}

	env := NewEnvelope("ok", "existing feature branch behavior remains enabled")
	if decision.Policy == runcontrol.FeatureBranchPolicyKeepCurrent {
		env.Summary = "keep the current branch while other live or recovery-held Work Board ownership remains"
	}
	env.Data["policy"] = decision.Policy
	env.Data["current_work_id"] = currentWorkID
	env.Data["concurrent_work_count"] = len(decision.ConcurrentWork)
	for _, work := range decision.ConcurrentWork {
		env.Items = append(env.Items, workItemDTO(work, nil))
	}
	env.ShowArgv = []string{"specify-runtime", "board", "branch-policy", "--project-root", projectRoot, "--format", "json"}
	return writeEnvelope(stdout, env)
}

func boardFeatureBootstrap(args []string, stdout io.Writer) int {
	parsed, err := parseRunCommandArgs(args, 0,
		"--project-root", "--work-id", "--feature-id", "--feature-dir", "--summary",
		"--agent-id", "--adapter-id", "--workspace-root", "--base-commit",
		"--next-action", "--lease-seconds", "--format",
	)
	if err != nil {
		return writeEnvelope(stdout, workBoardUsageEnvelope(err.Error()))
	}
	if err := validateWorkBoardFormat(parsed); err != nil {
		return writeEnvelope(stdout, workBoardUsageEnvelope(err.Error()))
	}
	for _, required := range []string{"--feature-id", "--feature-dir", "--summary", "--agent-id", "--adapter-id"} {
		if strings.TrimSpace(parsed.option(required, "")) == "" {
			return writeEnvelope(stdout, workBoardUsageEnvelope("board feature-bootstrap requires "+required))
		}
	}
	leaseUntil, err := workLeaseUntil(parsed)
	if err != nil {
		return writeEnvelope(stdout, workBoardUsageEnvelope(err.Error()))
	}

	ctx := context.Background()
	projectRoot := parsed.option("--project-root", ".")
	repository, err := runcontrol.ResolveRepository(ctx, projectRoot)
	if err != nil {
		return writeEnvelope(stdout, workBoardErrorEnvelope("resolve Work Board repository", err))
	}
	featureID := strings.TrimSpace(parsed.option("--feature-id", ""))
	featurePath, err := normalizeFeatureBootstrapDirectory(repository.Root, featureID, parsed.option("--feature-dir", ""))
	if err != nil {
		return writeEnvelope(stdout, workBoardUsageEnvelope(err.Error()))
	}
	workspaceRoot, err := resolveWorkBoardWorkspace(ctx, repository, parsed.option("--workspace-root", repository.Root))
	if err != nil {
		return writeEnvelope(stdout, workBoardErrorEnvelope("validate Work Board workspace", err))
	}
	baseCommit := strings.TrimSpace(parsed.option("--base-commit", ""))
	if baseCommit == "" {
		baseCommit, _ = runcontrol.ReadHeadCommit(ctx, workspaceRoot)
	}

	store, err := runcontrol.Open(ctx, repository.DatabasePath)
	if err != nil {
		return writeEnvelope(stdout, workBoardErrorEnvelope("open Work Board", err))
	}
	now := time.Now().UTC()
	_, operationErr := store.ReconcileRepositoryWork(ctx, now)
	var work runcontrol.WorkItem
	var intents []runcontrol.WriteIntent
	if operationErr == nil {
		work, intents, operationErr = store.BeginWork(ctx, runcontrol.BeginWorkParams{
			WorkID:        parsed.option("--work-id", ""),
			TaskRef:       "feature:" + featureID,
			Summary:       parsed.option("--summary", ""),
			AgentID:       parsed.option("--agent-id", ""),
			AdapterID:     parsed.option("--adapter-id", ""),
			WorkspaceRoot: workspaceRoot,
			BaseCommit:    baseCommit,
			NextAction:    parsed.option("--next-action", "run create-new-feature with the returned feature branch policy"),
			LeaseUntil:    leaseUntil,
			WriteIntents: []runcontrol.WriteIntentSpec{{
				Path:       featurePath,
				Operation:  runcontrol.WriteCreate,
				Reason:     "reserve exact feature directory before bootstrap",
				Confidence: runcontrol.IntentConfirmed,
			}},
		})
	}
	var decision runcontrol.FeatureBranchDecision
	if operationErr == nil {
		decision, operationErr = store.ResolveFeatureBranchPolicy(ctx, work.WorkID, now)
	}
	closeErr := store.Close()
	if operationErr != nil {
		return writeEnvelope(stdout, workBoardErrorEnvelope("bootstrap feature work", operationErr))
	}
	if closeErr != nil {
		return writeEnvelope(stdout, workBoardErrorEnvelope("close Work Board", closeErr))
	}

	env := NewEnvelope("ok", "feature bootstrap reserved on the shared Work Board")
	env.Data["work"] = workItemDTO(work, intents)
	env.Data["feature_id"] = featureID
	env.Data["feature_dir"] = featurePath
	env.Data["feature_branch_policy"] = featureBranchPolicyDTO(decision, work.WorkID)
	env.ShowArgv = workShowArgv(work.WorkID, projectRoot)
	env.NextArgv = []string{"specify-runtime", "board", "show", "--project-root", projectRoot, "--format", "json"}
	return writeEnvelope(stdout, env)
}

func normalizeFeatureBootstrapDirectory(projectRoot, featureID, featureDir string) (string, error) {
	if !safeSegment(featureID) {
		return "", fmt.Errorf("--feature-id %q must be a safe path segment", featureID)
	}
	root, err := filepath.Abs(projectRoot)
	if err != nil {
		return "", fmt.Errorf("resolve project root: %w", err)
	}
	candidate := strings.TrimSpace(featureDir)
	if !filepath.IsAbs(candidate) {
		candidate = filepath.Join(root, candidate)
	}
	candidate, err = filepath.Abs(candidate)
	if err != nil {
		return "", fmt.Errorf("resolve --feature-dir: %w", err)
	}
	relative, err := filepath.Rel(root, candidate)
	if err != nil {
		return "", fmt.Errorf("resolve --feature-dir relative to project root: %w", err)
	}
	relative = filepath.ToSlash(filepath.Clean(relative))
	expected := filepath.ToSlash(filepath.Join(".specify", "features", featureID))
	matches := relative == expected
	if runtime.GOOS == "windows" {
		matches = strings.EqualFold(relative, expected)
	}
	if !matches {
		return "", fmt.Errorf("--feature-dir must resolve to the exact project path %q", expected)
	}
	return expected, nil
}

func featureBranchPolicyDTO(decision runcontrol.FeatureBranchDecision, currentWorkID string) map[string]any {
	concurrent := make([]any, 0, len(decision.ConcurrentWork))
	for _, work := range decision.ConcurrentWork {
		concurrent = append(concurrent, workItemDTO(work, nil))
	}
	return map[string]any{
		"policy":                decision.Policy,
		"current_work_id":       currentWorkID,
		"concurrent_work_count": len(decision.ConcurrentWork),
		"concurrent_work":       concurrent,
	}
}

func workItemDTO(work runcontrol.WorkItem, intents []runcontrol.WriteIntent) map[string]any {
	payload := map[string]any{
		"work_id":         work.WorkID,
		"parent_work_id":  work.ParentWorkID,
		"run_id":          work.RunID,
		"task_ref":        work.TaskRef,
		"summary":         work.Summary,
		"agent_id":        work.AgentID,
		"adapter_id":      work.AdapterID,
		"workspace_root":  work.WorkspaceRoot,
		"base_commit":     work.BaseCommit,
		"status":          work.Status,
		"next_action":     work.NextAction,
		"last_reason":     work.LastReason,
		"fence":           work.Fence,
		"revision":        work.Revision,
		"lease_until_ms":  work.LeaseUntilMS,
		"heartbeat_at_ms": work.HeartbeatAtMS,
		"recovery_hold":   work.RecoveryHold,
		"observed_paths":  append([]string(nil), work.ObservedPaths...),
		"stale":           (work.Status == runcontrol.WorkActive || work.Status == runcontrol.WorkBlocked) && work.LeaseUntilMS <= time.Now().UTC().UnixMilli(),
		"created_at_ms":   work.CreatedAtMS,
		"updated_at_ms":   work.UpdatedAtMS,
	}
	if intents != nil {
		projected := make([]any, 0, len(intents))
		for _, intent := range intents {
			projected = append(projected, writeIntentDTO(intent))
		}
		payload["write_intents"] = projected
	}
	return payload
}

func writeIntentDTO(intent runcontrol.WriteIntent) map[string]any {
	return map[string]any{
		"intent_id":      intent.IntentID,
		"work_id":        intent.WorkID,
		"path":           intent.Path,
		"operation":      intent.Operation,
		"reason":         intent.Reason,
		"confidence":     intent.Confidence,
		"status":         intent.Status,
		"revision":       intent.Revision,
		"created_at_ms":  intent.CreatedAtMS,
		"updated_at_ms":  intent.UpdatedAtMS,
		"released_at_ms": intent.ReleasedAtMS,
	}
}

func workBoardErrorEnvelope(action string, err error) Envelope {
	env := runControlErrorEnvelope(action, err)
	var conflict *runcontrol.WorkIntentConflictError
	if errors.As(err, &conflict) {
		env.Status = "blocked"
		env.Data["error_code"] = "work_intent_conflict"
		items := make([]any, 0, len(conflict.Conflicts))
		for _, item := range conflict.Conflicts {
			items = append(items, map[string]any{
				"requested_path": item.RequestedPath,
				"owner_path":     item.OwnerPath,
				"owner_work_id":  item.OwnerWorkID,
				"owner_agent_id": item.OwnerAgentID,
				"owner_summary":  item.OwnerSummary,
				"owner_status":   item.OwnerStatus,
			})
		}
		env.Data["conflicts"] = items
	}
	return env
}

func workBoardUsageEnvelope(summary string) Envelope {
	env := NewEnvelope("usage-error", summary)
	env.ShowArgv = []string{"specify-runtime", "board", "help"}
	return env
}

func validateWorkBoardFormat(parsed parsedRunCommand) error {
	if format, present := parsed.options["--format"]; present && strings.TrimSpace(format) != "json" {
		return errors.New("Work Board commands support only --format json")
	}
	return nil
}

func workLeaseUntil(parsed parsedRunCommand) (time.Time, error) {
	raw := strings.TrimSpace(parsed.option("--lease-seconds", strconv.FormatInt(defaultWorkLeaseSeconds, 10)))
	seconds, err := strconv.ParseInt(raw, 10, 64)
	if err != nil || seconds <= 0 || seconds > maximumWorkLeaseSeconds {
		return time.Time{}, fmt.Errorf("--lease-seconds must be between 1 and %d", maximumWorkLeaseSeconds)
	}
	return time.Now().UTC().Add(time.Duration(seconds) * time.Second), nil
}

func workRevisionAndFence(parsed parsedRunCommand) (int64, int64, error) {
	revision, err := positiveWorkOption(parsed, "--expected-revision")
	if err != nil {
		return 0, 0, err
	}
	fence, err := positiveWorkOption(parsed, "--fence")
	if err != nil {
		return 0, 0, err
	}
	return revision, fence, nil
}

func positiveWorkOption(parsed parsedRunCommand, name string) (int64, error) {
	raw := strings.TrimSpace(parsed.option(name, ""))
	value, err := strconv.ParseInt(raw, 10, 64)
	if err != nil || value <= 0 {
		return 0, fmt.Errorf("%s must be a positive integer", name)
	}
	return value, nil
}

func parseWriteIntentsJSON(raw string) ([]runcontrol.WriteIntentSpec, error) {
	var input []struct {
		Path       string `json:"path"`
		Operation  string `json:"operation"`
		Reason     string `json:"reason"`
		Confidence string `json:"confidence"`
	}
	if err := json.Unmarshal([]byte(raw), &input); err != nil {
		return nil, errors.New("--intents-json must be a JSON array of write intents")
	}
	intents := make([]runcontrol.WriteIntentSpec, 0, len(input))
	for _, item := range input {
		intents = append(intents, runcontrol.WriteIntentSpec{
			Path: item.Path, Operation: runcontrol.WriteOperation(item.Operation), Reason: item.Reason,
			Confidence: runcontrol.WriteIntentConfidence(item.Confidence),
		})
	}
	return intents, nil
}

func parseStringListJSON(raw, optionName string) ([]string, error) {
	var values []string
	if err := json.Unmarshal([]byte(raw), &values); err != nil {
		return nil, fmt.Errorf("%s must be a JSON string array", optionName)
	}
	return values, nil
}

func parseWorkStatuses(raw string) ([]runcontrol.WorkStatus, error) {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return nil, nil
	}
	parts := strings.Split(raw, ",")
	statuses := make([]runcontrol.WorkStatus, 0, len(parts))
	for _, part := range parts {
		status := runcontrol.WorkStatus(strings.TrimSpace(part))
		switch status {
		case runcontrol.WorkActive, runcontrol.WorkBlocked, runcontrol.WorkInterrupted,
			runcontrol.WorkCompleted, runcontrol.WorkAbandoned:
			statuses = append(statuses, status)
		default:
			return nil, fmt.Errorf("unsupported --status %q", part)
		}
	}
	return statuses, nil
}

func workShowArgv(workID, projectRoot string) []string {
	return []string{"specify-runtime", "work", "show", workID, "--project-root", projectRoot, "--format", "json"}
}

func resolveWorkBoardWorkspace(
	ctx context.Context,
	repository runcontrol.Repository,
	workspaceRoot string,
) (string, error) {
	workspace, err := runcontrol.ResolveRepository(ctx, strings.TrimSpace(workspaceRoot))
	if err != nil {
		return "", err
	}
	left := filepath.Clean(repository.CommonDir)
	right := filepath.Clean(workspace.CommonDir)
	sameRepository := left == right
	if runtime.GOOS == "windows" {
		sameRepository = strings.EqualFold(left, right)
	}
	if !sameRepository {
		return "", fmt.Errorf(
			"%w: workspace %q belongs to a different Git repository",
			runcontrol.ErrInvalidArgument,
			workspace.Root,
		)
	}
	return workspace.Root, nil
}
