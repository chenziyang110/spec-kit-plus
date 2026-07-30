package main

import (
	"context"
	"errors"
	"fmt"
	"io"
	"strconv"
	"strings"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runcontrol"
)

func runRun(args []string, stdout io.Writer) int {
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
	default:
		return writeEnvelope(stdout, runUsageEnvelope(fmt.Sprintf("unknown run subcommand %q", args[0])))
	}
}

func writeRunHelp(stdout io.Writer) int {
	_, _ = fmt.Fprintln(stdout, "specify-runtime run commands:")
	for _, command := range []string{"create", "show", "events", "cancel"} {
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
	required := []string{"--run-id", "--kind", "--subject-type", "--subject-id", "--target-ref", "--intent-sha256"}
	for _, name := range required {
		if strings.TrimSpace(parsed.option(name, "")) == "" {
			return writeEnvelope(stdout, runUsageEnvelope("run create requires "+name))
		}
	}

	ctx := context.Background()
	store, err := runcontrol.OpenForRepository(ctx, parsed.option("--project-root", "."))
	if err != nil {
		return writeEnvelope(stdout, runControlErrorEnvelope("open run control", err))
	}
	run, operationErr := store.EnqueueRun(ctx, runcontrol.CreateRunParams{
		RunID:        strings.TrimSpace(parsed.option("--run-id", "")),
		Kind:         strings.TrimSpace(parsed.option("--kind", "")),
		SubjectType:  strings.TrimSpace(parsed.option("--subject-type", "")),
		SubjectID:    strings.TrimSpace(parsed.option("--subject-id", "")),
		TargetRef:    strings.TrimSpace(parsed.option("--target-ref", "")),
		IntentSHA256: strings.TrimSpace(parsed.option("--intent-sha256", "")),
	})
	closeErr := store.Close()
	if operationErr != nil {
		return writeEnvelope(stdout, runControlErrorEnvelope("create run", operationErr))
	}
	if closeErr != nil {
		return writeEnvelope(stdout, runControlErrorEnvelope("close run control", closeErr))
	}

	env := NewEnvelope("ok", "run recorded")
	env.Data["run"] = runDTO(run)
	env.ShowArgv = runShowArgv(run.RunID, parsed.option("--project-root", "."))
	env.NextArgv = append([]string{}, env.ShowArgv...)
	return writeEnvelope(stdout, env)
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

type parsedRunCommand struct {
	positionals []string
	options     map[string]string
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
		errors.Is(err, runcontrol.ErrUnsupportedSchema):
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
