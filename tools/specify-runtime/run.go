package main

import (
	"context"
	"encoding/json"
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
	default:
		return writeEnvelope(stdout, runUsageEnvelope(fmt.Sprintf("unknown run subcommand %q", args[0])))
	}
}

func writeRunHelp(stdout io.Writer) int {
	_, _ = fmt.Fprintln(stdout, "specify-runtime run commands:")
	for _, command := range []string{"create", "show", "events", "cancel", "launch", "supervise"} {
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
	workspacePolicy, err := parsed.workspacePolicy()
	if err != nil {
		return writeEnvelope(stdout, runUsageEnvelope(err.Error()))
	}
	projectRoot := parsed.option("--project-root", ".")

	ctx, stopSignals := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stopSignals()
	if _, operationErr := enqueueRunForCLI(ctx, projectRoot, createParams); operationErr != nil {
		return writeEnvelope(stdout, runControlErrorEnvelope("launch run", operationErr))
	}
	result, operationErr := superviseRunForCLI(ctx, projectRoot, createParams.RunID, adapterID, workspacePolicy, childArgv, stderr)
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
	workspacePolicy, err := parsed.workspacePolicy()
	if err != nil {
		return writeEnvelope(stdout, runUsageEnvelope(err.Error()))
	}
	projectRoot := parsed.option("--project-root", ".")

	ctx, stopSignals := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stopSignals()
	result, operationErr := superviseRunForCLI(ctx, projectRoot, runID, adapterID, workspacePolicy, childArgv, stderr)
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
	workspacePolicy runcontrol.WorkspacePolicy,
	childArgv []string,
	childOutput io.Writer,
) (runcontrol.SupervisedRun, error) {
	repository, err := runcontrol.ResolveRepository(ctx, projectRoot)
	if err != nil {
		return runcontrol.SupervisedRun{}, fmt.Errorf("resolve run repository: %w", err)
	}
	return runcontrol.SuperviseRun(ctx, repository, runcontrol.SuperviseRunParams{
		RunID:           runID,
		AdapterID:       adapterID,
		WorkspacePolicy: workspacePolicy,
		Argv:            childArgv,
		ChildStdin:      os.Stdin,
		ChildStdout:     childOutput,
		ChildStderr:     childOutput,
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
	summary := fmt.Sprintf("run executed in %s workspace", result.Workspace.Mode)
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

type parsedRunCommand struct {
	positionals []string
	options     map[string]string
}

func runResultCommand(args []string, stdout io.Writer) int {
	if len(args) == 0 {
		return writeEnvelope(stdout, usageEnvelope("missing result subcommand"))
	}
	switch args[0] {
	case "list":
		return runResultList(args[1:], stdout)
	case "show":
		return runResultShow(args[1:], stdout)
	case "reopen":
		return runResultReopen(args[1:], stdout)
	case "depend":
		return runResultDepend(args[1:], stdout)
	default:
		return runResult(args, stdout)
	}
}

func runCandidateCommand(args []string, stdout io.Writer) int {
	if len(args) == 0 {
		return writeEnvelope(stdout, usageEnvelope("missing candidate subcommand"))
	}
	switch args[0] {
	case "build":
		return runCandidateBuild(args[1:], stdout)
	case "show":
		return runCandidateShow(args[1:], stdout)
	case "review":
		return runCandidateReview(args[1:], stdout)
	default:
		return writeEnvelope(stdout, usageEnvelope(fmt.Sprintf("unknown candidate subcommand %q", args[0])))
	}
}

func runCASCommand(args []string, stdout io.Writer) int {
	if len(args) == 0 {
		return writeEnvelope(stdout, usageEnvelope("missing cas subcommand"))
	}
	if args[0] != "publish" {
		return writeEnvelope(stdout, usageEnvelope(fmt.Sprintf("unknown cas subcommand %q", args[0])))
	}
	return runCASPublish(args[1:], stdout)
}

func runSyncCommand(args []string, stdout io.Writer) int {
	if len(args) == 0 {
		return writeEnvelope(stdout, usageEnvelope("missing sync subcommand"))
	}
	if args[0] != "safe" {
		return writeEnvelope(stdout, usageEnvelope(fmt.Sprintf("unknown sync subcommand %q", args[0])))
	}
	return runSyncSafe(args[1:], stdout)
}

func runAcceptCommand(args []string, stdout io.Writer) int {
	if len(args) > 0 && args[0] == "receipt" {
		return runAcceptReceipt(args[1:], stdout)
	}
	return runAccept(args, stdout)
}

func parseRunSuperviseArgs(args []string) (parsedRunCommand, []string, error) {
	return parseRunChildArgs(
		args,
		1,
		"run supervise",
		"--project-root",
		"--adapter-id",
		"--workspace-policy",
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
		"--workspace-policy",
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
	if positionalCount >= 0 && len(parsed.positionals) != positionalCount {
		return parsedRunCommand{}, fmt.Errorf("run command requires %d positional argument(s)", positionalCount)
	}
	if positionalCount < 0 && len(parsed.positionals) > 1 {
		return parsedRunCommand{}, errors.New("run command accepts at most one positional argument")
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

func (parsed parsedRunCommand) workspacePolicy() (runcontrol.WorkspacePolicy, error) {
	policy := runcontrol.WorkspacePolicy(strings.TrimSpace(parsed.option("--workspace-policy", string(runcontrol.WorkspacePolicyAuto))))
	switch policy {
	case runcontrol.WorkspacePolicyAuto, runcontrol.WorkspacePolicyPrimary, runcontrol.WorkspacePolicyIsolated:
		return policy, nil
	default:
		return "", fmt.Errorf("--workspace-policy must be auto, primary, or isolated")
	}
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
		"attempt_id":                   result.Attempt.AttemptID,
		"exit_code":                    result.ExitCode,
		"workspace_generation":         result.Workspace.Generation,
		"workspace_id":                 result.Workspace.WorkspaceID,
		"workspace_mode":               result.Workspace.Mode,
		"workspace_root":               result.Workspace.RootPath,
		"private_ref":                  result.Workspace.PrivateRef,
		"snapshot_id":                  result.Snapshot.SnapshotID,
		"workspace_attestation_id":     result.Attestation.AttestationID,
		"workspace_attestation_sha256": result.Attestation.AttestationDigest,
	}
	if result.Result.ResultID != "" {
		payload["result_id"] = result.Result.ResultID
		payload["result_revision"] = result.Result.ResultRevision
		payload["result_manifest_sha256"] = result.Result.ManifestSHA256
		payload["result_eligibility"] = result.Result.Eligibility
		payload["resource_attestation_sha256"] = result.Result.ResourceAttestationSHA256
		payload["target_ref"] = result.Result.TargetRef
		payload["result_commit_oid"] = result.Result.ResultCommitOID
	}
	return payload
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
		errors.Is(err, runcontrol.ErrResourceConflict),
		errors.Is(err, runcontrol.ErrUnsupportedSchema),
		errors.Is(err, runcontrol.ErrCandidateBinding),
		errors.Is(err, runcontrol.ErrTargetWorktreeDirty),
		errors.Is(err, runcontrol.ErrResultDependencyCycle),
		errors.Is(err, runcontrol.ErrResultConflict),
		errors.Is(err, runcontrol.ErrCandidateStale),
		errors.Is(err, runcontrol.ErrCandidateBuildConflict),
		errors.Is(err, runcontrol.ErrAcceptanceRequired),
		errors.Is(err, runcontrol.ErrPublicationUnknown),
		errors.Is(err, runcontrol.ErrReviewBinding),
		errors.Is(err, runcontrol.ErrSyncUnsafe):
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

func runResultList(args []string, stdout io.Writer) int {
	parsed, err := parseRunCommandArgs(args, -1, "--project-root", "--format", "--run-id")
	if err != nil {
		return writeEnvelope(stdout, usageEnvelope(err.Error()))
	}
	if err := parsed.validateJSONFormat(); err != nil {
		return writeEnvelope(stdout, usageEnvelope(err.Error()))
	}
	runID := strings.TrimSpace(parsed.option("--run-id", ""))
	if runID == "" && len(parsed.positionals) == 1 {
		runID = strings.TrimSpace(parsed.positionals[0])
	}
	if runID == "" {
		return writeEnvelope(stdout, usageEnvelope("result list requires <run-id> or --run-id"))
	}
	if len(parsed.positionals) > 1 {
		return writeEnvelope(stdout, usageEnvelope("result list accepts at most one positional <run-id>"))
	}
	ctx := context.Background()
	view, err := runcontrol.OpenViewForRepository(ctx, parsed.option("--project-root", "."))
	if err != nil {
		return writeEnvelope(stdout, runControlErrorEnvelope("open run control", err))
	}
	results, operationErr := view.ListRunResults(ctx, runID)
	closeErr := view.Close()
	if operationErr != nil {
		return writeEnvelope(stdout, runControlErrorEnvelope("list run results", operationErr))
	}
	if closeErr != nil {
		return writeEnvelope(stdout, runControlErrorEnvelope("close run control", closeErr))
	}
	env := NewEnvelope("ok", "run results loaded")
	env.Data["run_id"] = runID
	for _, result := range results {
		env.Items = append(env.Items, runResultDTO(result))
	}
	env.ShowArgv = []string{"specify-runtime", "result", "list", runID, "--project-root", parsed.option("--project-root", "."), "--format", "json"}
	return writeEnvelope(stdout, env)
}

func runResultShow(args []string, stdout io.Writer) int {
	parsed, err := parseRunCommandArgs(args, -1, "--project-root", "--format", "--result-id")
	if err != nil {
		return writeEnvelope(stdout, usageEnvelope(err.Error()))
	}
	if err := parsed.validateJSONFormat(); err != nil {
		return writeEnvelope(stdout, usageEnvelope(err.Error()))
	}
	resultID := strings.TrimSpace(parsed.option("--result-id", ""))
	if resultID == "" && len(parsed.positionals) == 1 {
		resultID = strings.TrimSpace(parsed.positionals[0])
	}
	if resultID == "" {
		return writeEnvelope(stdout, usageEnvelope("result show requires <result-id> or --result-id"))
	}
	if len(parsed.positionals) > 1 {
		return writeEnvelope(stdout, usageEnvelope("result show accepts at most one positional <result-id>"))
	}
	ctx := context.Background()
	view, err := runcontrol.OpenViewForRepository(ctx, parsed.option("--project-root", "."))
	if err != nil {
		return writeEnvelope(stdout, runControlErrorEnvelope("open run control", err))
	}
	result, operationErr := view.GetRunResult(ctx, resultID)
	var paths []string
	if operationErr == nil {
		paths, operationErr = view.ListRunResultPaths(ctx, resultID)
	}
	var dependencies []runcontrol.ResultDependency
	if operationErr == nil {
		dependencies, operationErr = view.ListResultDependencies(ctx, resultID)
	}
	var supersession map[string]any
	if operationErr == nil {
		if edge, edgeErr := view.GetResultSupersession(ctx, resultID); edgeErr == nil {
			supersession = resultSupersessionDTO(edge)
		} else if !errors.Is(edgeErr, runcontrol.ErrNotFound) {
			operationErr = edgeErr
		}
	}
	closeErr := view.Close()
	if operationErr != nil {
		return writeEnvelope(stdout, runControlErrorEnvelope("show run result", operationErr))
	}
	if closeErr != nil {
		return writeEnvelope(stdout, runControlErrorEnvelope("close run control", closeErr))
	}
	env := NewEnvelope("ok", "run result loaded")
	env.Data["result"] = runResultDTO(result)
	env.Data["paths"] = paths
	dependencyItems := make([]any, 0, len(dependencies))
	for _, dependency := range dependencies {
		dependencyItems = append(dependencyItems, resultDependencyDTO(dependency))
	}
	env.Data["dependencies"] = dependencyItems
	if supersession != nil {
		env.Data["supersession"] = supersession
	}
	env.ShowArgv = []string{"specify-runtime", "result", "show", resultID, "--project-root", parsed.option("--project-root", "."), "--format", "json"}
	return writeEnvelope(stdout, env)
}

func runResultReopen(args []string, stdout io.Writer) int {
	parsed, err := parseRunCommandArgs(args, 1, "--project-root", "--format", "--basis-result", "--basis-result-id", "--expected-revision", "--reason")
	if err != nil {
		return writeEnvelope(stdout, usageEnvelope(err.Error()))
	}
	if err := parsed.validateJSONFormat(); err != nil {
		return writeEnvelope(stdout, usageEnvelope(err.Error()))
	}
	runID := strings.TrimSpace(parsed.positionals[0])
	basisResultID := strings.TrimSpace(parsed.option("--basis-result", parsed.option("--basis-result-id", "")))
	if basisResultID == "" {
		return writeEnvelope(stdout, usageEnvelope("result reopen requires --basis-result"))
	}
	revision, err := strconv.ParseInt(strings.TrimSpace(parsed.option("--expected-revision", "")), 10, 64)
	if err != nil || revision <= 0 {
		return writeEnvelope(stdout, usageEnvelope("result reopen requires a positive --expected-revision"))
	}
	reason := strings.TrimSpace(parsed.option("--reason", ""))
	if reason == "" {
		return writeEnvelope(stdout, usageEnvelope("result reopen requires --reason"))
	}
	ctx := context.Background()
	store, err := runcontrol.OpenForRepository(ctx, parsed.option("--project-root", "."))
	if err != nil {
		return writeEnvelope(stdout, runControlErrorEnvelope("open run control", err))
	}
	run, operationErr := store.ReopenRun(ctx, runcontrol.ReopenRunParams{
		RunID:            runID,
		BasisResultID:    basisResultID,
		ExpectedRevision: revision,
		Reason:           reason,
	})
	closeErr := store.Close()
	if operationErr != nil {
		return writeEnvelope(stdout, runControlErrorEnvelope("reopen run from result", operationErr))
	}
	if closeErr != nil {
		return writeEnvelope(stdout, runControlErrorEnvelope("close run control", closeErr))
	}
	env := NewEnvelope("ok", "run reopened from sealed result")
	env.Data["run"] = runDTO(run)
	env.Data["basis_result_id"] = basisResultID
	env.ShowArgv = runShowArgv(run.RunID, parsed.option("--project-root", "."))
	return writeEnvelope(stdout, env)
}

func runResultDepend(args []string, stdout io.Writer) int {
	parsed, err := parseRunCommandArgs(args, 1, "--project-root", "--format", "--on", "--upstream-result-id", "--kind", "--reason")
	if err != nil {
		return writeEnvelope(stdout, usageEnvelope(err.Error()))
	}
	if err := parsed.validateJSONFormat(); err != nil {
		return writeEnvelope(stdout, usageEnvelope(err.Error()))
	}
	resultID := strings.TrimSpace(parsed.positionals[0])
	dependsOnID := strings.TrimSpace(parsed.option("--on", parsed.option("--upstream-result-id", "")))
	if dependsOnID == "" {
		return writeEnvelope(stdout, usageEnvelope("result depend requires --on"))
	}
	kindValue := strings.TrimSpace(parsed.option("--kind", ""))
	var kind runcontrol.ResultDependencyKind
	switch kindValue {
	case string(runcontrol.ResultDependencyRequires):
		kind = runcontrol.ResultDependencyRequires
	case string(runcontrol.ResultDependencyAfter):
		kind = runcontrol.ResultDependencyAfter
	case string(runcontrol.ResultDependencyConflictsWith):
		kind = runcontrol.ResultDependencyConflictsWith
	default:
		return writeEnvelope(stdout, usageEnvelope("result depend requires --kind requires|after|conflicts_with"))
	}
	reason := strings.TrimSpace(parsed.option("--reason", ""))
	if reason == "" {
		return writeEnvelope(stdout, usageEnvelope("result depend requires --reason"))
	}
	ctx := context.Background()
	store, err := runcontrol.OpenForRepository(ctx, parsed.option("--project-root", "."))
	if err != nil {
		return writeEnvelope(stdout, runControlErrorEnvelope("open run control", err))
	}
	dependency, operationErr := store.AddResultDependency(ctx, runcontrol.AddResultDependencyParams{
		ResultID:          resultID,
		DependsOnResultID: dependsOnID,
		Kind:              kind,
		Reason:            reason,
	})
	closeErr := store.Close()
	if operationErr != nil {
		return writeEnvelope(stdout, runControlErrorEnvelope("record result dependency", operationErr))
	}
	if closeErr != nil {
		return writeEnvelope(stdout, runControlErrorEnvelope("close run control", closeErr))
	}
	env := NewEnvelope("ok", "result dependency recorded")
	env.Data["dependency"] = resultDependencyDTO(dependency)
	env.ShowArgv = []string{"specify-runtime", "result", "show", resultID, "--project-root", parsed.option("--project-root", "."), "--format", "json"}
	return writeEnvelope(stdout, env)
}

func runCandidateBuild(args []string, stdout io.Writer) int {
	parsed, err := parseMultiOptionCommandArgs(args, 0, map[string]bool{
		"--project-root": false,
		"--format":       false,
		"--target-ref":   false,
		"--result":       true,
		"--result-id":    true,
	})
	if err != nil {
		return writeEnvelope(stdout, usageEnvelope(err.Error()))
	}
	if err := parsed.validateJSONFormat(); err != nil {
		return writeEnvelope(stdout, usageEnvelope(err.Error()))
	}
	targetRef := strings.TrimSpace(parsed.option("--target-ref", ""))
	if targetRef == "" {
		return writeEnvelope(stdout, usageEnvelope("candidate build requires --target-ref"))
	}
	resultIDs := append([]string{}, parsed.values("--result")...)
	resultIDs = append(resultIDs, parsed.values("--result-id")...)
	resultIDs = compactStrings(resultIDs)
	if len(resultIDs) == 0 {
		return writeEnvelope(stdout, usageEnvelope("candidate build requires at least one --result"))
	}
	ctx, stopSignals := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stopSignals()
	repository, err := runcontrol.ResolveRepository(ctx, parsed.option("--project-root", "."))
	if err != nil {
		return writeEnvelope(stdout, runControlErrorEnvelope("resolve run repository", err))
	}
	candidate, operationErr := runcontrol.BuildFrozenCandidate(ctx, repository, runcontrol.BuildFrozenCandidateParams{
		TargetRef: targetRef,
		ResultIDs: resultIDs,
	})
	if operationErr != nil {
		return writeEnvelope(stdout, runControlErrorEnvelope("build frozen candidate", operationErr))
	}
	env := NewEnvelope("ok", "frozen candidate built")
	env.Data["candidate"] = frozenCandidateDTO(candidate)
	env.ShowArgv = []string{"specify-runtime", "candidate", "show", candidate.CandidateID, "--project-root", parsed.option("--project-root", "."), "--format", "json"}
	return writeEnvelope(stdout, env)
}

func runCandidateShow(args []string, stdout io.Writer) int {
	parsed, err := parseRunCommandArgs(args, -1, "--project-root", "--format", "--candidate-id")
	if err != nil {
		return writeEnvelope(stdout, usageEnvelope(err.Error()))
	}
	if err := parsed.validateJSONFormat(); err != nil {
		return writeEnvelope(stdout, usageEnvelope(err.Error()))
	}
	candidateID := strings.TrimSpace(parsed.option("--candidate-id", ""))
	if candidateID == "" && len(parsed.positionals) == 1 {
		candidateID = strings.TrimSpace(parsed.positionals[0])
	}
	if candidateID == "" {
		return writeEnvelope(stdout, usageEnvelope("candidate show requires <candidate-id> or --candidate-id"))
	}
	if len(parsed.positionals) > 1 {
		return writeEnvelope(stdout, usageEnvelope("candidate show accepts at most one positional <candidate-id>"))
	}
	ctx := context.Background()
	view, err := runcontrol.OpenViewForRepository(ctx, parsed.option("--project-root", "."))
	if err != nil {
		return writeEnvelope(stdout, runControlErrorEnvelope("open run control", err))
	}
	candidate, operationErr := view.GetFrozenCandidate(ctx, candidateID)
	var review runcontrol.CandidateReview
	var acceptance runcontrol.CandidateAcceptance
	var publication runcontrol.CandidatePublication
	var syncReceipt runcontrol.CandidateSync
	var reviewPresent, acceptancePresent, publicationPresent, syncPresent bool
	if operationErr == nil {
		review, operationErr = view.GetLatestCandidateReview(ctx, candidateID)
		if errors.Is(operationErr, runcontrol.ErrNotFound) {
			operationErr = nil
		} else {
			reviewPresent = operationErr == nil
		}
	}
	if operationErr == nil {
		acceptance, operationErr = view.GetLatestCandidateAcceptance(ctx, candidateID)
		if errors.Is(operationErr, runcontrol.ErrNotFound) {
			operationErr = nil
		} else {
			acceptancePresent = operationErr == nil
		}
	}
	if operationErr == nil {
		publication, operationErr = view.GetLatestCandidatePublication(ctx, candidateID)
		if errors.Is(operationErr, runcontrol.ErrNotFound) {
			operationErr = nil
		} else {
			publicationPresent = operationErr == nil
		}
	}
	if operationErr == nil {
		syncReceipt, operationErr = view.GetLatestCandidateSync(ctx, candidateID)
		if errors.Is(operationErr, runcontrol.ErrNotFound) {
			operationErr = nil
		} else {
			syncPresent = operationErr == nil
		}
	}
	closeErr := view.Close()
	if operationErr != nil {
		return writeEnvelope(stdout, runControlErrorEnvelope("show frozen candidate", operationErr))
	}
	if closeErr != nil {
		return writeEnvelope(stdout, runControlErrorEnvelope("close run control", closeErr))
	}
	env := NewEnvelope("ok", "frozen candidate loaded")
	env.Data["candidate"] = frozenCandidateDTO(candidate)
	if reviewPresent {
		env.Data["review"] = candidateReviewDTO(review)
	}
	if acceptancePresent {
		env.Data["acceptance"] = candidateAcceptanceDTO(acceptance)
	}
	if publicationPresent {
		env.Data["publication"] = candidatePublicationDTO(publication)
	}
	if syncPresent {
		env.Data["sync"] = candidateSyncDTO(syncReceipt)
	}
	env.ShowArgv = []string{"specify-runtime", "candidate", "show", candidateID, "--project-root", parsed.option("--project-root", "."), "--format", "json"}
	return writeEnvelope(stdout, env)
}

func runCandidateReview(args []string, stdout io.Writer) int {
	parsed, literalArgv, err := parseRunChildArgs(args, 1, "candidate review", "--project-root", "--format", "--reviewer", "--candidate-id")
	if err != nil {
		return writeEnvelope(stdout, usageEnvelope(err.Error()))
	}
	if err := parsed.validateJSONFormat(); err != nil {
		return writeEnvelope(stdout, usageEnvelope(err.Error()))
	}
	candidateID := strings.TrimSpace(parsed.positionals[0])
	if aliasID := strings.TrimSpace(parsed.option("--candidate-id", "")); aliasID != "" {
		candidateID = aliasID
	}
	reviewer := strings.TrimSpace(parsed.option("--reviewer", ""))
	if reviewer == "" {
		return writeEnvelope(stdout, usageEnvelope("candidate review requires --reviewer"))
	}
	ctx, stopSignals := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stopSignals()
	repository, err := runcontrol.ResolveRepository(ctx, parsed.option("--project-root", "."))
	if err != nil {
		return writeEnvelope(stdout, runControlErrorEnvelope("resolve run repository", err))
	}
	review, operationErr := runcontrol.ReviewFrozenCandidate(ctx, repository, runcontrol.ReviewFrozenCandidateParams{
		CandidateID: candidateID,
		Reviewer:    reviewer,
		Commands:    [][]string{literalArgv},
	})
	if operationErr != nil {
		return writeEnvelope(stdout, runControlErrorEnvelope("review frozen candidate", operationErr))
	}
	env := NewEnvelope("ok", "frozen candidate reviewed")
	env.Data["review"] = candidateReviewDTO(review)
	env.ShowArgv = []string{"specify-runtime", "candidate", "show", candidateID, "--project-root", parsed.option("--project-root", "."), "--format", "json"}
	return writeEnvelope(stdout, env)
}

func runAcceptReceipt(args []string, stdout io.Writer) int {
	parsed, err := parseRunCommandArgs(args, -1, "--project-root", "--format", "--review-digest", "--decision", "--actor", "--candidate-id", "--input-json")
	if err != nil {
		return writeEnvelope(stdout, usageEnvelope(err.Error()))
	}
	if err := parsed.validateJSONFormat(); err != nil {
		return writeEnvelope(stdout, usageEnvelope(err.Error()))
	}
	var input struct {
		CandidateID  string `json:"candidate_id"`
		ReviewDigest string `json:"review_digest"`
		Decision     string `json:"decision"`
		Actor        string `json:"actor"`
	}
	if raw := strings.TrimSpace(parsed.option("--input-json", "")); raw != "" {
		if err := json.Unmarshal([]byte(raw), &input); err != nil {
			return writeEnvelope(stdout, usageEnvelope("accept receipt --input-json must be a JSON object"))
		}
	}
	candidateID := ""
	if len(parsed.positionals) == 1 {
		candidateID = strings.TrimSpace(parsed.positionals[0])
	}
	if aliasID := strings.TrimSpace(parsed.option("--candidate-id", "")); aliasID != "" {
		candidateID = aliasID
	}
	if candidateID == "" {
		candidateID = strings.TrimSpace(input.CandidateID)
	}
	reviewDigest := strings.TrimSpace(parsed.option("--review-digest", input.ReviewDigest))
	actor := strings.TrimSpace(parsed.option("--actor", input.Actor))
	decisionValue := strings.TrimSpace(parsed.option("--decision", input.Decision))
	if candidateID == "" || reviewDigest == "" || actor == "" {
		return writeEnvelope(stdout, usageEnvelope("accept receipt requires candidate_id, review_digest, and actor"))
	}
	var decision runcontrol.CandidateAcceptanceDecision
	switch decisionValue {
	case string(runcontrol.CandidateAccepted):
		decision = runcontrol.CandidateAccepted
	case string(runcontrol.CandidateRejected):
		decision = runcontrol.CandidateRejected
	default:
		return writeEnvelope(stdout, usageEnvelope("accept receipt requires --decision accepted|rejected"))
	}
	ctx, stopSignals := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stopSignals()
	repository, err := runcontrol.ResolveRepository(ctx, parsed.option("--project-root", "."))
	if err != nil {
		return writeEnvelope(stdout, runControlErrorEnvelope("resolve run repository", err))
	}
	acceptance, operationErr := runcontrol.RecordCandidateAcceptance(ctx, repository, runcontrol.CandidateAcceptanceParams{
		CandidateID:  candidateID,
		ReviewDigest: reviewDigest,
		Decision:     decision,
		Actor:        actor,
	})
	if operationErr != nil {
		return writeEnvelope(stdout, runControlErrorEnvelope("record candidate acceptance", operationErr))
	}
	env := NewEnvelope("ok", "candidate acceptance receipt recorded")
	env.Data["acceptance"] = candidateAcceptanceDTO(acceptance)
	env.ShowArgv = []string{"specify-runtime", "candidate", "show", candidateID, "--project-root", parsed.option("--project-root", "."), "--format", "json"}
	return writeEnvelope(stdout, env)
}

func runCASPublish(args []string, stdout io.Writer) int {
	parsed, err := parseRunCommandArgs(args, 1, "--project-root", "--format", "--acceptance-digest", "--expected-sha256", "--candidate-id")
	if err != nil {
		return writeEnvelope(stdout, usageEnvelope(err.Error()))
	}
	if err := parsed.validateJSONFormat(); err != nil {
		return writeEnvelope(stdout, usageEnvelope(err.Error()))
	}
	candidateID := strings.TrimSpace(parsed.positionals[0])
	if aliasID := strings.TrimSpace(parsed.option("--candidate-id", "")); aliasID != "" {
		candidateID = aliasID
	}
	acceptanceDigest := strings.TrimSpace(parsed.option("--acceptance-digest", parsed.option("--expected-sha256", "")))
	if acceptanceDigest == "" {
		return writeEnvelope(stdout, usageEnvelope("cas publish requires --acceptance-digest"))
	}
	ctx, stopSignals := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stopSignals()
	repository, err := runcontrol.ResolveRepository(ctx, parsed.option("--project-root", "."))
	if err != nil {
		return writeEnvelope(stdout, runControlErrorEnvelope("resolve run repository", err))
	}
	publication, operationErr := runcontrol.PublishFrozenCandidate(ctx, repository, runcontrol.PublishFrozenCandidateParams{
		CandidateID:      candidateID,
		AcceptanceDigest: acceptanceDigest,
	})
	if operationErr != nil {
		return writeEnvelope(stdout, runControlErrorEnvelope("publish frozen candidate", operationErr))
	}
	env := NewEnvelope("ok", "candidate publication recorded")
	env.Data["publication"] = candidatePublicationDTO(publication)
	env.ShowArgv = []string{"specify-runtime", "candidate", "show", candidateID, "--project-root", parsed.option("--project-root", "."), "--format", "json"}
	return writeEnvelope(stdout, env)
}

func runSyncSafe(args []string, stdout io.Writer) int {
	parsed, err := parseRunCommandArgs(args, 1, "--project-root", "--format", "--publication-digest", "--target-ref", "--candidate-id")
	if err != nil {
		return writeEnvelope(stdout, usageEnvelope(err.Error()))
	}
	if err := parsed.validateJSONFormat(); err != nil {
		return writeEnvelope(stdout, usageEnvelope(err.Error()))
	}
	candidateID := strings.TrimSpace(parsed.positionals[0])
	if aliasID := strings.TrimSpace(parsed.option("--candidate-id", "")); aliasID != "" {
		candidateID = aliasID
	}
	publicationDigest := strings.TrimSpace(parsed.option("--publication-digest", ""))
	targetRef := strings.TrimSpace(parsed.option("--target-ref", ""))
	if publicationDigest == "" || targetRef == "" {
		return writeEnvelope(stdout, usageEnvelope("sync safe requires --publication-digest and --target-ref"))
	}
	ctx, stopSignals := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stopSignals()
	repository, err := runcontrol.ResolveRepository(ctx, parsed.option("--project-root", "."))
	if err != nil {
		return writeEnvelope(stdout, runControlErrorEnvelope("resolve run repository", err))
	}
	syncReceipt, operationErr := runcontrol.SyncPublishedCandidate(ctx, repository, runcontrol.SyncPublishedCandidateParams{
		CandidateID:       candidateID,
		PublicationDigest: publicationDigest,
		TargetRef:         targetRef,
	})
	if operationErr != nil {
		return writeEnvelope(stdout, runControlErrorEnvelope("safe-sync published candidate", operationErr))
	}
	env := NewEnvelope("ok", "published candidate synchronized safely")
	env.Data["sync"] = candidateSyncDTO(syncReceipt)
	env.ShowArgv = []string{"specify-runtime", "candidate", "show", candidateID, "--project-root", parsed.option("--project-root", "."), "--format", "json"}
	return writeEnvelope(stdout, env)
}

type parsedMultiOptionCommand struct {
	positionals []string
	options     map[string]string
	optionLists map[string][]string
}

func parseMultiOptionCommandArgs(args []string, positionalCount int, allowed map[string]bool) (parsedMultiOptionCommand, error) {
	parsed := parsedMultiOptionCommand{
		positionals: []string{},
		options:     map[string]string{},
		optionLists: map[string][]string{},
	}
	for index := 0; index < len(args); index++ {
		argument := args[index]
		if !strings.HasPrefix(argument, "--") {
			parsed.positionals = append(parsed.positionals, argument)
			continue
		}
		repeatable, ok := allowed[argument]
		if !ok {
			return parsedMultiOptionCommand{}, fmt.Errorf("unknown option %q", argument)
		}
		if index+1 >= len(args) || strings.HasPrefix(args[index+1], "--") {
			return parsedMultiOptionCommand{}, fmt.Errorf("option %s requires a value", argument)
		}
		value := args[index+1]
		if repeatable {
			parsed.optionLists[argument] = append(parsed.optionLists[argument], value)
		} else {
			if _, duplicate := parsed.options[argument]; duplicate {
				return parsedMultiOptionCommand{}, fmt.Errorf("option %s was repeated", argument)
			}
			parsed.options[argument] = value
		}
		index++
	}
	if len(parsed.positionals) != positionalCount {
		return parsedMultiOptionCommand{}, fmt.Errorf("command requires %d positional argument(s)", positionalCount)
	}
	return parsed, nil
}

func (parsed parsedMultiOptionCommand) option(name, fallback string) string {
	if value, ok := parsed.options[name]; ok {
		return value
	}
	return fallback
}

func (parsed parsedMultiOptionCommand) values(name string) []string {
	values := append([]string{}, parsed.optionLists[name]...)
	if value, ok := parsed.options[name]; ok && strings.TrimSpace(value) != "" {
		values = append(values, value)
	}
	return values
}

func (parsed parsedMultiOptionCommand) validateJSONFormat() error {
	if format, present := parsed.options["--format"]; present && strings.TrimSpace(format) != "json" {
		return errors.New("commands support only --format json")
	}
	return nil
}

func compactStrings(values []string) []string {
	result := make([]string, 0, len(values))
	for _, value := range values {
		value = strings.TrimSpace(value)
		if value != "" {
			result = append(result, value)
		}
	}
	return result
}

func runResultDTO(result runcontrol.RunResult) map[string]any {
	return map[string]any{
		"result_id":                    result.ResultID,
		"run_id":                       result.RunID,
		"result_revision":              result.ResultRevision,
		"attempt_id":                   result.AttemptID,
		"activity_id":                  result.ActivityID,
		"workspace_id":                 result.WorkspaceID,
		"workspace_generation":         result.WorkspaceGeneration,
		"fence":                        result.Fence,
		"snapshot_id":                  result.SnapshotID,
		"target_ref":                   result.TargetRef,
		"base_commit_oid":              result.BaseCommitOID,
		"result_tree_oid":              result.ResultTreeOID,
		"result_commit_oid":            result.ResultCommitOID,
		"hidden_ref":                   result.HiddenRef,
		"manifest_sha256":              result.ManifestSHA256,
		"workspace_attestation_sha256": result.WorkspaceAttestationSHA256,
		"resource_attestation_sha256":  result.ResourceAttestationSHA256,
		"eligibility":                  result.Eligibility,
		"validation_evidence_json":     result.ValidationEvidenceJSON,
		"worker_result_digests_json":   result.WorkerResultDigestsJSON,
		"external_effects_json":        result.ExternalEffectsJSON,
		"created_at_ms":                result.CreatedAtMS,
	}
}

func resultSupersessionDTO(edge runcontrol.ResultSupersession) map[string]any {
	return map[string]any{
		"old_result_id": edge.OldResultID,
		"new_result_id": edge.NewResultID,
		"run_id":        edge.RunID,
		"reason":        edge.Reason,
		"created_at_ms": edge.CreatedAtMS,
	}
}

func resultDependencyDTO(edge runcontrol.ResultDependency) map[string]any {
	return map[string]any{
		"dependency_id":        edge.DependencyID,
		"result_id":            edge.ResultID,
		"depends_on_result_id": edge.DependsOnResultID,
		"kind":                 edge.Kind,
		"reason":               edge.Reason,
		"created_at_ms":        edge.CreatedAtMS,
	}
}

func frozenCandidateDTO(candidate runcontrol.FrozenCandidate) map[string]any {
	return map[string]any{
		"candidate_id":        candidate.CandidateID,
		"build_id":            candidate.BuildID,
		"target_ref":          candidate.TargetRef,
		"expected_target_oid": candidate.ExpectedTargetOID,
		"tree_oid":            candidate.TreeOID,
		"commit_oid":          candidate.CommitOID,
		"hidden_ref":          candidate.HiddenRef,
		"manifest_sha256":     candidate.ManifestSHA256,
		"member_result_ids":   candidate.MemberResultIDs,
		"status":              candidate.Status,
		"created_at_ms":       candidate.CreatedAtMS,
	}
}

func candidateReviewDTO(review runcontrol.CandidateReview) map[string]any {
	return map[string]any{
		"review_id":                 review.ReviewID,
		"candidate_id":              review.CandidateID,
		"candidate_manifest_sha256": review.CandidateManifestSHA256,
		"candidate_tree_oid":        review.CandidateTreeOID,
		"candidate_commit_oid":      review.CandidateCommitOID,
		"reviewer":                  review.Reviewer,
		"status":                    review.Status,
		"evidence_digest":           review.EvidenceDigest,
		"review_digest":             review.ReviewDigest,
		"created_at_ms":             review.CreatedAtMS,
	}
}

func candidateAcceptanceDTO(acceptance runcontrol.CandidateAcceptance) map[string]any {
	return map[string]any{
		"acceptance_id":     acceptance.AcceptanceID,
		"candidate_id":      acceptance.CandidateID,
		"review_id":         acceptance.ReviewID,
		"review_digest":     acceptance.ReviewDigest,
		"evidence_digest":   acceptance.EvidenceDigest,
		"decision":          acceptance.Decision,
		"actor":             acceptance.Actor,
		"acceptance_digest": acceptance.AcceptanceDigest,
		"created_at_ms":     acceptance.CreatedAtMS,
	}
}

func candidatePublicationDTO(publication runcontrol.CandidatePublication) map[string]any {
	return map[string]any{
		"publication_id":          publication.PublicationID,
		"candidate_id":            publication.CandidateID,
		"acceptance_id":           publication.AcceptanceID,
		"target_ref":              publication.TargetRef,
		"target_before":           publication.TargetBefore,
		"target_after":            publication.TargetAfter,
		"expected_index_tree_oid": publication.ExpectedIndexTreeOID,
		"status":                  publication.Status,
		"publication_digest":      publication.PublicationDigest,
		"created_at_ms":           publication.CreatedAtMS,
		"updated_at_ms":           publication.UpdatedAtMS,
	}
}

func candidateSyncDTO(syncReceipt runcontrol.CandidateSync) map[string]any {
	return map[string]any{
		"sync_id":        syncReceipt.SyncID,
		"candidate_id":   syncReceipt.CandidateID,
		"publication_id": syncReceipt.PublicationID,
		"worktree_root":  syncReceipt.WorktreeRoot,
		"status":         syncReceipt.Status,
		"sync_digest":    syncReceipt.SyncDigest,
		"created_at_ms":  syncReceipt.CreatedAtMS,
	}
}
