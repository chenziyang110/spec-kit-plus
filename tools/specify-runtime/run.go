package main

import (
	"context"
	"errors"
	"fmt"
	"io"
	"os"
	"os/signal"
	"strconv"
	"strings"
	"syscall"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runcontrol"
)

func runRun(args []string, stdout, stderr io.Writer) int {
	if len(args) == 0 {
		return writeEnvelope(stdout, runUsageEnvelope("missing run subcommand"))
	}
	if args[0] == "--help" || args[0] == "-h" || args[0] == "help" {
		return writeRunHelp(stdout)
	}
	switch args[0] {
	case "create":
		return runCreate(args[1:], stdout)
	case "show":
		return runShow(args[1:], stdout)
	case "events":
		return runEvents(args[1:], stdout)
	case "cancel":
		return runCancel(args[1:], stdout)
	case "launch":
		return runLaunch(args[1:], stdout, stderr)
	case "supervise":
		return runSupervise(args[1:], stdout, stderr)
	case "integrate":
		return runIntegrateCandidate(args[1:], stdout)
	default:
		return writeEnvelope(stdout, runUsageEnvelope(fmt.Sprintf("unknown run subcommand %q", args[0])))
	}
}

func writeRunHelp(stdout io.Writer) int {
	_, _ = fmt.Fprintln(stdout, "specify-runtime run commands:")
	for _, command := range []string{"create", "show", "events", "cancel", "launch", "supervise", "integrate"} {
		_, _ = fmt.Fprintf(stdout, "  %s\n", command)
	}
	return 0
}

func runCreate(args []string, stdout io.Writer) int {
	parsed, err := parseRunCommandArgs(args, 0,
		"--project-root", "--run-id", "--kind", "--subject-type", "--subject-id",
		"--target-ref", "--intent-sha256", "--format",
	)
	if err != nil {
		return writeEnvelope(stdout, runUsageEnvelope(err.Error()))
	}
	if err := parsed.validateJSONFormat(); err != nil {
		return writeEnvelope(stdout, runUsageEnvelope(err.Error()))
	}
	createParams, err := runCreateParams(parsed, "run create")
	if err != nil {
		return writeEnvelope(stdout, runUsageEnvelope(err.Error()))
	}

	ctx := context.Background()
	projectRoot := parsed.option("--project-root", ".")
	run, operationErr := enqueueRunForCLI(ctx, projectRoot, createParams)
	if operationErr != nil {
		return writeEnvelope(stdout, runControlErrorEnvelope("create run", operationErr))
	}

	env := NewEnvelope("ok", "run recorded")
	env.Data["run"] = runDTO(run)
	env.ShowArgv = runShowArgv(run.RunID, projectRoot)
	env.NextArgv = append([]string{}, env.ShowArgv...)
	return writeEnvelope(stdout, env)
}

func runLaunch(args []string, stdout, stderr io.Writer) int {
	parsed, childArgv, err := parseRunLaunchArgs(args)
	if err != nil {
		return writeEnvelope(stdout, runUsageEnvelope(err.Error()))
	}
	if err := parsed.validateJSONFormat(); err != nil {
		return writeEnvelope(stdout, runUsageEnvelope(err.Error()))
	}
	createParams, err := runCreateParams(parsed, "run launch")
	if err != nil {
		return writeEnvelope(stdout, runUsageEnvelope(err.Error()))
	}
	adapterID := strings.TrimSpace(parsed.option("--adapter-id", ""))
	if adapterID == "" {
		return writeEnvelope(stdout, runUsageEnvelope("run launch requires --adapter-id"))
	}
	projectRoot := parsed.option("--project-root", ".")

	ctx, stopSignals := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stopSignals()
	if _, operationErr := enqueueRunForCLI(ctx, projectRoot, createParams); operationErr != nil {
		return writeEnvelope(stdout, runControlErrorEnvelope("launch run", operationErr))
	}
	result, operationErr := superviseRunForCLI(ctx, projectRoot, createParams.RunID, adapterID, childArgv, stderr)
	return writeRunSupervisionEnvelope(stdout, ctx, createParams.RunID, projectRoot, result, operationErr)
}

func runShow(args []string, stdout io.Writer) int {
	parsed, err := parseRunCommandArgs(args, 1, "--project-root", "--format")
	if err != nil {
		return writeEnvelope(stdout, runUsageEnvelope(err.Error()))
	}
	if err := parsed.validateJSONFormat(); err != nil {
		return writeEnvelope(stdout, runUsageEnvelope(err.Error()))
	}
	runID := strings.TrimSpace(parsed.positionals[0])
	if runID == "" {
		return writeEnvelope(stdout, runUsageEnvelope("run show requires <run-id>"))
	}

	ctx := context.Background()
	view, err := runcontrol.OpenViewForRepository(ctx, parsed.option("--project-root", "."))
	if err != nil {
		return writeEnvelope(stdout, runControlErrorEnvelope("open run control", err))
	}
	run, operationErr := view.GetRun(ctx, runID)
	closeErr := view.Close()
	if operationErr != nil {
		return writeEnvelope(stdout, runControlErrorEnvelope("show run", operationErr))
	}
	if closeErr != nil {
		return writeEnvelope(stdout, runControlErrorEnvelope("close run control", closeErr))
	}

	env := NewEnvelope("ok", "run loaded")
	env.Data["run"] = runDTO(run)
	env.ShowArgv = runShowArgv(run.RunID, parsed.option("--project-root", "."))
	return writeEnvelope(stdout, env)
}

func runEvents(args []string, stdout io.Writer) int {
	parsed, err := parseRunCommandArgs(args, 1, "--project-root", "--format")
	if err != nil {
		return writeEnvelope(stdout, runUsageEnvelope(err.Error()))
	}
	if err := parsed.validateJSONFormat(); err != nil {
		return writeEnvelope(stdout, runUsageEnvelope(err.Error()))
	}
	runID := strings.TrimSpace(parsed.positionals[0])
	if runID == "" {
		return writeEnvelope(stdout, runUsageEnvelope("run events requires <run-id>"))
	}

	ctx := context.Background()
	view, err := runcontrol.OpenViewForRepository(ctx, parsed.option("--project-root", "."))
	if err != nil {
		return writeEnvelope(stdout, runControlErrorEnvelope("open run control", err))
	}
	_, operationErr := view.GetRun(ctx, runID)
	var events []runcontrol.Event
	if operationErr == nil {
		events, operationErr = view.ListRunEvents(ctx, runID)
	}
	closeErr := view.Close()
	if operationErr != nil {
		return writeEnvelope(stdout, runControlErrorEnvelope("list run events", operationErr))
	}
	if closeErr != nil {
		return writeEnvelope(stdout, runControlErrorEnvelope("close run control", closeErr))
	}

	env := NewEnvelope("ok", "run events loaded")
	for _, event := range events {
		env.Items = append(env.Items, runEventDTO(event))
	}
	env.Data["run_id"] = runID
	env.ShowArgv = runShowArgv(runID, parsed.option("--project-root", "."))
	return writeEnvelope(stdout, env)
}

func runCancel(args []string, stdout io.Writer) int {
	parsed, err := parseRunCommandArgs(args, 1, "--project-root", "--expected-revision", "--reason", "--format")
	if err != nil {
		return writeEnvelope(stdout, runUsageEnvelope(err.Error()))
	}
	if err := parsed.validateJSONFormat(); err != nil {
		return writeEnvelope(stdout, runUsageEnvelope(err.Error()))
	}
	runID := strings.TrimSpace(parsed.positionals[0])
	if runID == "" {
		return writeEnvelope(stdout, runUsageEnvelope("run cancel requires <run-id>"))
	}
	revisionRaw := strings.TrimSpace(parsed.option("--expected-revision", ""))
	revision, err := strconv.ParseInt(revisionRaw, 10, 64)
	if err != nil || revision <= 0 {
		return writeEnvelope(stdout, runUsageEnvelope("run cancel requires a positive --expected-revision"))
	}
	reason := strings.TrimSpace(parsed.option("--reason", ""))
	if reason == "" {
		return writeEnvelope(stdout, runUsageEnvelope("run cancel requires --reason"))
	}

	ctx := context.Background()
	store, err := runcontrol.OpenForRepository(ctx, parsed.option("--project-root", "."))
	if err != nil {
		return writeEnvelope(stdout, runControlErrorEnvelope("open run control", err))
	}
	run, operationErr := store.CancelRun(ctx, runID, revision, reason)
	closeErr := store.Close()
	if operationErr != nil {
		env := runControlErrorEnvelope("cancel run", operationErr)
		env.ShowArgv = runShowArgv(runID, parsed.option("--project-root", "."))
		return writeEnvelope(stdout, env)
	}
	if closeErr != nil {
		return writeEnvelope(stdout, runControlErrorEnvelope("close run control", closeErr))
	}

	env := NewEnvelope("ok", "run cancelled and fenced")
	env.Data["run"] = runDTO(run)
	env.ShowArgv = runShowArgv(run.RunID, parsed.option("--project-root", "."))
	return writeEnvelope(stdout, env)
}

func runSupervise(args []string, stdout, stderr io.Writer) int {
	parsed, childArgv, err := parseRunSuperviseArgs(args)
	if err != nil {
		return writeEnvelope(stdout, runUsageEnvelope(err.Error()))
	}
	if err := parsed.validateJSONFormat(); err != nil {
		return writeEnvelope(stdout, runUsageEnvelope(err.Error()))
	}
	runID := strings.TrimSpace(parsed.positionals[0])
	adapterID := strings.TrimSpace(parsed.option("--adapter-id", ""))
	if runID == "" || adapterID == "" {
		return writeEnvelope(stdout, runUsageEnvelope("run supervise requires <run-id> and --adapter-id"))
	}
	projectRoot := parsed.option("--project-root", ".")

	ctx, stopSignals := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stopSignals()
	result, operationErr := superviseRunForCLI(ctx, projectRoot, runID, adapterID, childArgv, stderr)
	return writeRunSupervisionEnvelope(stdout, ctx, runID, projectRoot, result, operationErr)
}

func runCreateParams(parsed parsedRunCommand, commandName string) (runcontrol.CreateRunParams, error) {
	required := []string{"--run-id", "--kind", "--subject-type", "--subject-id", "--target-ref", "--intent-sha256"}
	for _, name := range required {
		if strings.TrimSpace(parsed.option(name, "")) == "" {
			return runcontrol.CreateRunParams{}, fmt.Errorf("%s requires %s", commandName, name)
		}
	}
	return runcontrol.CreateRunParams{
		RunID:        strings.TrimSpace(parsed.option("--run-id", "")),
		Kind:         strings.TrimSpace(parsed.option("--kind", "")),
		SubjectType:  strings.TrimSpace(parsed.option("--subject-type", "")),
		SubjectID:    strings.TrimSpace(parsed.option("--subject-id", "")),
		TargetRef:    strings.TrimSpace(parsed.option("--target-ref", "")),
		IntentSHA256: strings.TrimSpace(parsed.option("--intent-sha256", "")),
	}, nil
}

func enqueueRunForCLI(ctx context.Context, projectRoot string, params runcontrol.CreateRunParams) (runcontrol.Run, error) {
	store, err := runcontrol.OpenForRepository(ctx, projectRoot)
	if err != nil {
		return runcontrol.Run{}, fmt.Errorf("open run control: %w", err)
	}
	run, operationErr := store.EnqueueRun(ctx, params)
	return run, errors.Join(operationErr, store.Close())
}

func superviseRunForCLI(
	ctx context.Context,
	projectRoot string,
	runID string,
	adapterID string,
	childArgv []string,
	childOutput io.Writer,
) (runcontrol.SupervisedRun, error) {
	repository, err := runcontrol.ResolveRepository(ctx, projectRoot)
	if err != nil {
		return runcontrol.SupervisedRun{}, fmt.Errorf("resolve run repository: %w", err)
	}
	return runcontrol.SuperviseRun(ctx, repository, runcontrol.SuperviseRunParams{
		RunID:       runID,
		AdapterID:   adapterID,
		Argv:        childArgv,
		ChildStdin:  os.Stdin,
		ChildStdout: childOutput,
		ChildStderr: childOutput,
	})
}

func writeRunSupervisionEnvelope(
	stdout io.Writer,
	ctx context.Context,
	runID string,
	projectRoot string,
	result runcontrol.SupervisedRun,
	operationErr error,
) int {
	if operationErr != nil {
		env := runControlErrorEnvelope("supervise run", operationErr)
		if errors.Is(operationErr, context.Canceled) {
			env.Status = "blocked"
			env.Summary = "run supervision interrupted and fenced"
		}
		env.ShowArgv = runShowArgv(runID, projectRoot)
		return writeEnvelope(stdout, env)
	}

	status := "ok"
	summary := "run executed in isolated workspace"
	if result.ExitCode != 0 {
		status = "error"
		summary = fmt.Sprintf("supervised process exited with code %d", result.ExitCode)
	}
	env := NewEnvelope(status, summary)
	env.Data["run"] = runDTO(result.Run)
	env.Data["execution"] = supervisedRunDTO(result)
	env.ShowArgv = runShowArgv(runID, projectRoot)
	return writeEnvelope(stdout, env)
}

func runIntegrateCandidate(args []string, stdout io.Writer) int {
	parsed, err := parseRunCommandArgs(args, 0, "--project-root", "--target-ref", "--format")
	if err != nil {
		return writeEnvelope(stdout, runUsageEnvelope(err.Error()))
	}
	if err := parsed.validateJSONFormat(); err != nil {
		return writeEnvelope(stdout, runUsageEnvelope(err.Error()))
	}
	targetRef := strings.TrimSpace(parsed.option("--target-ref", ""))
	if targetRef == "" {
		return writeEnvelope(stdout, runUsageEnvelope("run integrate requires --target-ref"))
	}
	projectRoot := parsed.option("--project-root", ".")
	ctx, stopSignals := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stopSignals()
	repository, err := runcontrol.ResolveRepository(ctx, projectRoot)
	if err != nil {
		return writeEnvelope(stdout, runControlErrorEnvelope("resolve run repository", err))
	}
	outcome, operationErr := runcontrol.IntegrateNext(ctx, repository, runcontrol.IntegrateNextParams{
		TargetRef: targetRef,
	})
	if operationErr != nil {
		return writeEnvelope(stdout, runControlErrorEnvelope("integrate candidate", operationErr))
	}
	status := "ok"
	summary := "candidate integrated into target ref"
	if outcome.Result.Status == runcontrol.ResultConflicted {
		status = "blocked"
		summary = "candidate conflicts with current target ref"
	}
	env := NewEnvelope(status, summary)
	env.Data["candidate"] = candidateDTO(outcome.Candidate)
	env.Data["integration"] = candidateIntegrationDTO(outcome.Integration)
	env.Data["result"] = integrationResultDTO(outcome.Result)
	env.ShowArgv = runShowArgv(outcome.Candidate.RunID, projectRoot)
	if status == "blocked" {
		env.Blockers = append(env.Blockers, map[string]any{
			"code":              "candidate-conflict",
			"candidate_id":      outcome.Candidate.CandidateID,
			"exact_next_action": "Resolve the isolated Candidate conflict in a replacement Run; the target worktree is clean.",
		})
	}
	return writeEnvelope(stdout, env)
}

type parsedRunCommand struct {
	positionals []string
	options     map[string]string
}

func parseRunSuperviseArgs(args []string) (parsedRunCommand, []string, error) {
	return parseRunChildArgs(
		args,
		1,
		"run supervise",
		"--project-root",
		"--adapter-id",
		"--format",
	)
}

func parseRunLaunchArgs(args []string) (parsedRunCommand, []string, error) {
	return parseRunChildArgs(
		args,
		0,
		"run launch",
		"--project-root",
		"--run-id",
		"--kind",
		"--subject-type",
		"--subject-id",
		"--target-ref",
		"--intent-sha256",
		"--adapter-id",
		"--format",
	)
}

func parseRunChildArgs(
	args []string,
	positionalCount int,
	commandName string,
	allowedOptions ...string,
) (parsedRunCommand, []string, error) {
	separator := -1
	for index, argument := range args {
		if argument == "--" {
			separator = index
			break
		}
	}
	if separator < 0 {
		return parsedRunCommand{}, nil, fmt.Errorf("%s requires -- before the child argv", commandName)
	}
	if separator == len(args)-1 {
		return parsedRunCommand{}, nil, fmt.Errorf("%s requires a child argv after --", commandName)
	}
	parsed, err := parseRunCommandArgs(args[:separator], positionalCount, allowedOptions...)
	if err != nil {
		return parsedRunCommand{}, nil, err
	}
	childArgv := append([]string(nil), args[separator+1:]...)
	if strings.TrimSpace(childArgv[0]) == "" {
		return parsedRunCommand{}, nil, fmt.Errorf("%s child executable is empty", commandName)
	}
	return parsed, childArgv, nil
}

func parseRunCommandArgs(args []string, positionalCount int, allowedOptions ...string) (parsedRunCommand, error) {
	allowed := make(map[string]bool, len(allowedOptions))
	for _, name := range allowedOptions {
		allowed[name] = true
	}
	parsed := parsedRunCommand{positionals: []string{}, options: map[string]string{}}
	for index := 0; index < len(args); index++ {
		argument := args[index]
		if !strings.HasPrefix(argument, "--") {
			parsed.positionals = append(parsed.positionals, argument)
			continue
		}
		if !allowed[argument] {
			return parsedRunCommand{}, fmt.Errorf("unknown run option %q", argument)
		}
		if _, duplicate := parsed.options[argument]; duplicate {
			return parsedRunCommand{}, fmt.Errorf("run option %s was repeated", argument)
		}
		if index+1 >= len(args) || strings.HasPrefix(args[index+1], "--") {
			return parsedRunCommand{}, fmt.Errorf("run option %s requires a value", argument)
		}
		parsed.options[argument] = args[index+1]
		index++
	}
	if len(parsed.positionals) != positionalCount {
		return parsedRunCommand{}, fmt.Errorf("run command requires %d positional argument(s)", positionalCount)
	}
	return parsed, nil
}

func (parsed parsedRunCommand) option(name, fallback string) string {
	if value, ok := parsed.options[name]; ok {
		return value
	}
	return fallback
}

func (parsed parsedRunCommand) validateJSONFormat() error {
	if format, present := parsed.options["--format"]; present && strings.TrimSpace(format) != "json" {
		return errors.New("run commands support only --format json")
	}
	return nil
}

func runDTO(run runcontrol.Run) map[string]any {
	return map[string]any{
		"run_id":        run.RunID,
		"kind":          run.Kind,
		"subject_type":  run.SubjectType,
		"subject_id":    run.SubjectID,
		"target_ref":    run.TargetRef,
		"intent_sha256": run.IntentSHA256,
		"status":        run.Status,
		"revision":      run.Revision,
		"current_fence": run.CurrentFence,
		"created_at_ms": run.CreatedAtMS,
		"updated_at_ms": run.UpdatedAtMS,
	}
}

func runEventDTO(event runcontrol.Event) map[string]any {
	return map[string]any{
		"event_id":           event.EventID,
		"aggregate_revision": event.AggregateRevision,
		"event_type":         event.EventType,
		"reason":             event.Reason,
		"created_at_ms":      event.CreatedAtMS,
	}
}

func supervisedRunDTO(result runcontrol.SupervisedRun) map[string]any {
	payload := map[string]any{
		"attempt_id":           result.Attempt.AttemptID,
		"exit_code":            result.ExitCode,
		"workspace_generation": result.Workspace.Generation,
		"workspace_id":         result.Workspace.WorkspaceID,
		"workspace_root":       result.Workspace.RootPath,
		"private_ref":          result.Workspace.PrivateRef,
	}
	if result.Candidate.CandidateID != "" {
		payload["candidate_id"] = result.Candidate.CandidateID
		payload["target_ref"] = result.Candidate.TargetRef
		payload["head_commit"] = result.Candidate.HeadCommit
		payload["candidate_status"] = result.Candidate.Status
	}
	return payload
}

func candidateDTO(candidate runcontrol.Candidate) map[string]any {
	return map[string]any{
		"candidate_id":         candidate.CandidateID,
		"run_id":               candidate.RunID,
		"attempt_id":           candidate.AttemptID,
		"workspace_id":         candidate.WorkspaceID,
		"workspace_generation": candidate.WorkspaceGeneration,
		"target_ref":           candidate.TargetRef,
		"base_commit":          candidate.BaseCommit,
		"private_ref":          candidate.PrivateRef,
		"head_commit":          candidate.HeadCommit,
		"status":               candidate.Status,
		"revision":             candidate.Revision,
	}
}

func candidateIntegrationDTO(integration runcontrol.CandidateIntegration) map[string]any {
	return map[string]any{
		"integration_id": integration.IntegrationID,
		"candidate_id":   integration.CandidateID,
		"target_ref":     integration.TargetRef,
		"status":         integration.Status,
		"target_before":  integration.TargetBefore,
		"target_after":   integration.TargetAfter,
		"reason":         integration.Reason,
		"revision":       integration.Revision,
	}
}

func integrationResultDTO(result runcontrol.Result) map[string]any {
	return map[string]any{
		"result_id":      result.ResultID,
		"integration_id": result.IntegrationID,
		"candidate_id":   result.CandidateID,
		"run_id":         result.RunID,
		"target_ref":     result.TargetRef,
		"target_before":  result.TargetBefore,
		"target_after":   result.TargetAfter,
		"status":         result.Status,
		"reason":         result.Reason,
	}
}

func runControlErrorEnvelope(action string, err error) Envelope {
	status := "error"
	switch {
	case errors.Is(err, runcontrol.ErrInvalidArgument),
		errors.Is(err, runcontrol.ErrNotFound):
		status = "invalid"
	case errors.Is(err, runcontrol.ErrNotGitRepository):
		status = "usage-error"
	case errors.Is(err, runcontrol.ErrAlreadyExists),
		errors.Is(err, runcontrol.ErrRevisionConflict),
		errors.Is(err, runcontrol.ErrInvalidTransition),
		errors.Is(err, runcontrol.ErrLiveAttempt),
		errors.Is(err, runcontrol.ErrStaleFence),
		errors.Is(err, runcontrol.ErrOpenActivity),
		errors.Is(err, runcontrol.ErrUsableWorkspace),
		errors.Is(err, runcontrol.ErrWorkspaceGeneration),
		errors.Is(err, runcontrol.ErrWorkspaceNotUsable),
		errors.Is(err, runcontrol.ErrUnsupportedSchema),
		errors.Is(err, runcontrol.ErrCandidateBinding),
		errors.Is(err, runcontrol.ErrIntegrationBusy),
		errors.Is(err, runcontrol.ErrTargetWorktreeDirty):
		status = "blocked"
	}
	env := NewEnvelope(status, action+" failed")
	env.Blockers = append(env.Blockers, err.Error())
	return env
}

func runUsageEnvelope(summary string) Envelope {
	env := NewEnvelope("usage-error", summary)
	env.ShowArgv = []string{"specify-runtime", "run", "help"}
	return env
}

func runShowArgv(runID, projectRoot string) []string {
	return []string{"specify-runtime", "run", "show", runID, "--project-root", projectRoot, "--format", "json"}
}
