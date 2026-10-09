package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"regexp"
	"runtime"
	"sort"
	"strconv"
	"strings"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/filelock"
)

var e2eIDPattern = regexp.MustCompile(`^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$`)
var e2eRunIDPattern = regexp.MustCompile(`^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$`)

type e2eScope struct {
	ID        string `json:"id"`
	Target    string `json:"target"`
	Operation string `json:"operation"`
}
type e2eCriterion struct {
	ID        string `json:"id"`
	Criterion string `json:"criterion"`
}
type e2eDependency struct {
	TaskID  string `json:"task_id"`
	Require string `json:"require"`
}
type e2eTaskSpec struct {
	ID         string          `json:"id"`
	Stage      int             `json:"stage"`
	ScopeIDs   []string        `json:"scope_ids"`
	DependsOn  []e2eDependency `json:"depends_on,omitempty"`
	Acceptance []e2eCriterion  `json:"acceptance"`
	Inputs     []string        `json:"inputs"`
	Outputs    []string        `json:"outputs"`
	Resources  []string        `json:"resources,omitempty"`
}
type e2ePlanInput struct {
	Mode  string        `json:"mode,omitempty"`
	Scope []e2eScope    `json:"scope"`
	Tasks []e2eTaskSpec `json:"tasks"`
}
type e2eRef struct {
	Ref    string `json:"ref"`
	SHA256 string `json:"sha256"`
}
type e2eBinding struct {
	Path       string `json:"path"`
	SHA256     string `json:"sha256"`
	ArchiveRef string `json:"archive_ref"`
}
type e2eDependencyBinding struct {
	TaskID     string       `json:"task_id"`
	Require    string       `json:"require"`
	Acceptance e2eRef       `json:"acceptance"`
	Outputs    []e2eBinding `json:"outputs"`
}
type e2eDiagnosticBinding struct {
	TaskID     string `json:"task_id"`
	Status     string `json:"status"`
	Submission e2eRef `json:"submission"`
	Review     e2eRef `json:"review"`
}
type e2eTaskState struct {
	Contract     e2eTaskSpec `json:"contract"`
	Status       string      `json:"status"`
	Attempt      int         `json:"attempt"`
	WorkerID     string      `json:"worker_id,omitempty"`
	AuthorIDs    []string    `json:"author_ids"`
	ValidatorID  string      `json:"validator_id,omitempty"`
	Packet       e2eRef      `json:"packet"`
	Submission   e2eRef      `json:"submission"`
	ReviewPacket e2eRef      `json:"review_packet"`
	Review       e2eRef      `json:"review"`
	Acceptance   e2eRef      `json:"acceptance"`
	Outcome      string      `json:"outcome,omitempty"`
	History      []e2eRef    `json:"history"`
	ReopenReason string      `json:"reopen_reason,omitempty"`
}
type e2eState struct {
	SchemaVersion string         `json:"schema_version"`
	RunID         string         `json:"run_id"`
	Revision      int            `json:"revision"`
	LeaderID      string         `json:"leader_id"`
	Mode          string         `json:"mode"`
	Status        string         `json:"status"`
	Scope         []e2eScope     `json:"scope"`
	Tasks         []e2eTaskState `json:"tasks"`
	Events        []e2eRef       `json:"events"`
	Closeout      e2eRef         `json:"closeout"`
}
type e2ePacket struct {
	SchemaVersion    string                 `json:"schema_version"`
	RunID            string                 `json:"run_id"`
	TaskID           string                 `json:"task_id"`
	AttemptID        string                 `json:"attempt_id"`
	WorkerID         string                 `json:"worker_id"`
	ContractSHA256   string                 `json:"contract_sha256"`
	ContractRef      e2eRef                 `json:"contract_ref"`
	Contract         e2eTaskSpec            `json:"contract"`
	Scope            []e2eScope             `json:"scope"`
	Inputs           []e2eBinding           `json:"inputs"`
	Dependencies     []e2eDependencyBinding `json:"dependencies"`
	Diagnostic       bool                   `json:"diagnostic"`
	DiagnosticInputs []e2eDiagnosticBinding `json:"diagnostic_inputs"`
	WorkerTaskPacket map[string]any         `json:"worker_task_packet"`
}

// A separate content-addressed contract gives even a task with no external
// inputs concrete original context without referring to mutable workflow state
// or making a packet include its own digest.
type e2eTaskContract struct {
	SchemaVersion  string      `json:"schema_version"`
	RunID          string      `json:"run_id"`
	TaskID         string      `json:"task_id"`
	Mode           string      `json:"mode"`
	ContractSHA256 string      `json:"contract_sha256"`
	Contract       e2eTaskSpec `json:"contract"`
	Scope          []e2eScope  `json:"scope"`
}
type e2eCheck struct {
	ScopeID       string   `json:"scope_id"`
	AcceptanceID  string   `json:"acceptance_id"`
	Status        string   `json:"status"`
	Expected      string   `json:"expected"`
	Actual        string   `json:"actual"`
	Reproduction  string   `json:"reproduction"`
	Preconditions string   `json:"preconditions"`
	EvidenceRefs  []string `json:"evidence_refs"`
	Method        string   `json:"method,omitempty"`
}
type e2eSubmissionInput struct {
	PacketSHA256 string          `json:"packet_sha256"`
	Outcome      string          `json:"outcome"`
	WorkerResult json.RawMessage `json:"worker_result"`
	Checks       []e2eCheck      `json:"checks"`
}
type e2eSubmission struct {
	SchemaVersion     string          `json:"schema_version"`
	Packet            e2eRef          `json:"packet"`
	WorkerID          string          `json:"worker_id"`
	WorkerResult      map[string]any  `json:"worker_result"`
	WorkerResultInput json.RawMessage `json:"worker_result_input"`
	Outcome           string          `json:"outcome"`
	Checks            []e2eCheck      `json:"checks"`
	Outputs           []e2eBinding    `json:"outputs"`
	Evidence          []e2eBinding    `json:"evidence"`
}
type e2eReviewPacket struct {
	SchemaVersion    string         `json:"schema_version"`
	RunID            string         `json:"run_id"`
	TaskID           string         `json:"task_id"`
	ValidatorID      string         `json:"validator_id"`
	Packet           e2eRef         `json:"packet"`
	Submission       e2eRef         `json:"submission"`
	Contract         e2eTaskSpec    `json:"contract"`
	Scope            []e2eScope     `json:"scope"`
	WorkerTaskPacket map[string]any `json:"worker_task_packet"`
}
type e2eReviewInput struct {
	ReviewPacketSHA256 string     `json:"review_packet_sha256"`
	SubmissionSHA256   string     `json:"submission_sha256"`
	Checks             []e2eCheck `json:"checks"`
}
type e2eReview struct {
	SchemaVersion string       `json:"schema_version"`
	Request       e2eRef       `json:"request"`
	Submission    e2eRef       `json:"submission"`
	ValidatorID   string       `json:"validator_id"`
	Checks        []e2eCheck   `json:"checks"`
	Evidence      []e2eBinding `json:"evidence"`
}
type e2eAcceptance struct {
	SchemaVersion string `json:"schema_version"`
	RunID         string `json:"run_id"`
	TaskID        string `json:"task_id"`
	LeaderID      string `json:"leader_id"`
	Packet        e2eRef `json:"packet"`
	Submission    e2eRef `json:"submission"`
	ReviewPacket  e2eRef `json:"review_packet"`
	Review        e2eRef `json:"review"`
	Outcome       string `json:"outcome"`
}

type e2eCloseout struct {
	SchemaVersion     string            `json:"schema_version"`
	RunID             string            `json:"run_id"`
	FromRevision      int               `json:"from_revision"`
	LeaderID          string            `json:"leader_id"`
	Mode              string            `json:"mode"`
	Outcome           string            `json:"outcome"`
	Status            string            `json:"status"`
	ProductPass       bool              `json:"product_pass"`
	Scope             []e2eScope        `json:"scope"`
	Acceptances       map[string]e2eRef `json:"acceptances"`
	UnacceptedTaskIDs []string          `json:"unaccepted_task_ids"`
	NonpassingTaskIDs []string          `json:"nonpassing_task_ids"`
}
type e2eService struct {
	projectRoot  string
	runID        string
	rootRef      string
	observed     map[string]string
	pendingBlobs map[string][]byte
	beforeCommit func() error
}

func runE2E(args []string, stdout io.Writer) int {
	if len(args) == 0 || args[0] == "help" || args[0] == "--help" || args[0] == "-h" {
		env := NewEnvelope("ok", "E2E verified-handoff commands")
		for _, id := range e2eCapabilityIDs() {
			descriptor, _ := e2eCapabilityDescriptor(id)
			env.Items = append(env.Items, descriptor)
		}
		return writeEnvelope(stdout, env)
	}
	if !e2eContains(e2eActions, args[0]) {
		return writeEnvelope(stdout, e2eFailure("usage-error", "unknown e2e command", fmt.Errorf("%s", args[0])))
	}
	if hasFlag(args[1:], "--help") || hasFlag(args[1:], "-h") {
		descriptor, _ := e2eCapabilityDescriptor("e2e." + args[0])
		env := NewEnvelope("ok", "E2E command contract")
		env.Data = descriptor
		return writeEnvelope(stdout, env)
	}
	if err := e2eValidateOptions(args); err != nil {
		return writeEnvelope(stdout, e2eFailure("usage-error", "invalid e2e options", err))
	}
	root, err := filepath.Abs(optionValue(args, "--project-root", "."))
	if err != nil {
		return writeEnvelope(stdout, e2eFailure("usage-error", "invalid project root", err))
	}
	runID := optionValue(args, "--run-id", "")
	if !e2eRunIDPattern.MatchString(runID) {
		return writeEnvelope(stdout, e2eFailure("usage-error", "--run-id requires a safe non-empty identifier", nil))
	}
	service := &e2eService{projectRoot: root, runID: runID, rootRef: ".planning/e2e/" + runID, observed: map[string]string{}}
	return writeEnvelope(stdout, service.run(args[0], args[1:]))
}

func e2eValidateOptions(args []string) error {
	allowed := map[string]bool{"--run-id": true, "--project-root": true, "--format": true}
	if args[0] != "init" && args[0] != "status" {
		allowed["--expected-revision"] = true
	}
	switch args[0] {
	case "init":
		allowed["--leader-id"], allowed["--input-json"] = true, true
	case "scope-add":
		allowed["--leader-id"], allowed["--input-json"], allowed["--reason"], allowed["--evidence-ref"] = true, true, true, true
	case "task-start":
		allowed["--task-id"], allowed["--worker-id"], allowed["--diagnostic"] = true, true, true
	case "task-submit":
		allowed["--task-id"], allowed["--worker-id"], allowed["--result-json"] = true, true, true
	case "review-start":
		allowed["--task-id"], allowed["--validator-id"] = true, true
	case "review-submit":
		allowed["--task-id"], allowed["--validator-id"], allowed["--result-json"] = true, true, true
	case "task-accept":
		allowed["--task-id"], allowed["--leader-id"] = true, true
	case "reopen":
		allowed["--task-id"], allowed["--leader-id"], allowed["--reason"], allowed["--evidence-ref"] = true, true, true, true
	case "close":
		allowed["--leader-id"], allowed["--outcome"] = true, true
	}
	seen := map[string]bool{}
	for i := 1; i < len(args); i++ {
		flag := args[i]
		if !allowed[flag] || (seen[flag] && flag != "--evidence-ref") {
			return fmt.Errorf("unsupported or duplicate option %s", flag)
		}
		seen[flag] = true
		if flag == "--diagnostic" {
			continue
		}
		if i+1 >= len(args) || strings.TrimSpace(args[i+1]) == "" || strings.HasPrefix(args[i+1], "--") {
			return fmt.Errorf("%s requires a value", flag)
		}
		i++
	}
	if optionValue(args, "--format", "json") != "json" {
		return fmt.Errorf("e2e requires --format json")
	}
	return nil
}

func (service *e2eService) run(action string, args []string) Envelope {
	if action == "status" {
		return service.status()
	}
	lockPath, err := secureProjectPath(service.projectRoot, ".specify/runtime/e2e/locks/"+service.runID+".lock")
	if err != nil {
		return e2eFailure("blocked", "e2e mutation lock is unsafe", err)
	}
	if err := os.MkdirAll(filepath.Dir(lockPath), 0o755); err != nil {
		return e2eFailure("error", "cannot create e2e lock directory", err)
	}
	release, err := filelock.Acquire(lockPath)
	if err != nil {
		return e2eFailure("blocked", "cannot acquire e2e mutation lock", err)
	}
	defer release()
	if action == "init" {
		return service.initialize(args)
	}
	state, err := service.readState()
	if err != nil {
		return e2eFailure("blocked", "e2e state is unavailable", err)
	}
	revision, err := strconv.Atoi(optionValue(args, "--expected-revision", ""))
	if err != nil || revision != state.Revision {
		return service.failureWithState("blocked", "e2e revision changed; inspect status before retry", &state, fmt.Errorf("expected revision %d", state.Revision))
	}
	if action == "reopen" {
		return service.reopen(&state, args)
	}
	stale := service.staleTasks(&state)
	if len(stale) > 0 {
		ids := e2eInvalidate(&state, stale, "bound source, output, review or evidence bytes changed")
		state.Revision++
		if err := service.persist(&state, "invalidate", nil); err != nil {
			return e2eFailure("error", "cannot persist e2e invalidation", err)
		}
		env := service.failureWithState("blocked", "e2e bindings became stale; affected tasks and consumers were reopened", &state, nil)
		env.Data["invalidated_task_ids"] = ids
		return env
	}
	if state.Status != "active" && e2eRequiresActiveRun(action) {
		return service.failureWithState("blocked", "E2E run is closed; reopen the affected task with recovery evidence before continuing", &state, nil)
	}
	switch action {
	case "scope-add":
		return service.scopeAdd(&state, args)
	case "task-start":
		return service.taskStart(&state, args)
	case "task-submit":
		return service.taskSubmit(&state, args)
	case "review-start":
		return service.reviewStart(&state, args)
	case "review-submit":
		return service.reviewSubmit(&state, args)
	case "task-accept":
		return service.taskAccept(&state, args)
	case "close":
		return service.close(&state, args)
	}
	return e2eFailure("usage-error", "unsupported e2e action", nil)
}

func (service *e2eService) initialize(args []string) Envelope {
	path, err := secureProjectPath(service.projectRoot, service.rootRef+"/state.json")
	if err != nil {
		return e2eFailure("blocked", "e2e state path is unsafe", err)
	}
	if _, err := os.Lstat(path); err == nil {
		return e2eFailure("blocked", "e2e run already exists; use status to resume it", nil)
	} else if !os.IsNotExist(err) {
		return e2eFailure("blocked", "cannot inspect e2e state", err)
	}
	leader := optionValue(args, "--leader-id", "")
	if !e2eIdentity(leader) {
		return e2eFailure("usage-error", "init requires --leader-id", nil)
	}
	var input e2ePlanInput
	if err := service.input(args, "--input-json", &input); err != nil {
		return e2eFailure("invalid", "invalid e2e plan", err)
	}
	if err := e2eValidatePlan(input); err != nil {
		return e2eFailure("invalid", "invalid e2e full-scope plan", err)
	}
	state := e2eState{SchemaVersion: e2eWorkflowSchema, RunID: service.runID, Revision: 1, LeaderID: leader, Mode: input.Mode, Status: "active", Scope: input.Scope, Tasks: []e2eTaskState{}, Events: []e2eRef{}}
	for _, contract := range input.Tasks {
		state.Tasks = append(state.Tasks, e2eNewTask(contract, input.Mode))
	}
	if err := service.persist(&state, "init", nil); err != nil {
		return e2eFailure("error", "cannot initialize e2e run", err)
	}
	return service.envelope("ok", "E2E complete scope and seven-stage task contracts frozen", &state)
}

func (service *e2eService) status() Envelope {
	state, err := service.readState()
	if err != nil {
		return e2eFailure("blocked", "e2e state is unavailable", err)
	}
	stale := service.staleTasks(&state)
	if len(stale) > 0 {
		ids := e2eInvalidate(&state, stale, "read-only status detected stale bindings")
		env := service.failureWithState("blocked", "E2E has stale artifacts; no previous acceptance may be consumed", &state, nil)
		env.Data["stale_task_ids"], env.Data["state_mutated"] = ids, false
		return env
	}
	return service.envelope("ok", "E2E current scope, dependency and acceptance state", &state)
}

func (service *e2eService) taskStart(state *e2eState, args []string) Envelope {
	index, err := e2eTaskIndex(state, optionValue(args, "--task-id", ""))
	if err != nil {
		return service.failureWithState("invalid", "unknown e2e task", state, err)
	}
	task := &state.Tasks[index]
	if task.Status != "pending" {
		return service.failureWithState("blocked", "task-start requires a pending task; reopen rejected or accepted work explicitly", state, nil)
	}
	worker := optionValue(args, "--worker-id", "")
	if !e2eIdentity(worker) || worker == state.LeaderID {
		return service.failureWithState("blocked", "task requires a separately recorded worker identity", state, nil)
	}
	diagnostic := hasFlag(args, "--diagnostic")
	if diagnostic && task.Contract.Stage < 6 {
		return service.failureWithState("invalid", "diagnostic task-start is limited to audit/report stages 6 and 7", state, nil)
	}
	if task.Contract.Stage == 6 && e2eAncestorAuthorConflict(state, index, worker) {
		return service.failureWithState("blocked", "stage 6 audit worker participated in producing an audited dependency", state, nil)
	}
	packet := e2ePacket{SchemaVersion: "e2e-worker-packet-v1", RunID: state.RunID, TaskID: task.Contract.ID, AttemptID: fmt.Sprintf("%s-%04d", task.Contract.ID, task.Attempt+1), WorkerID: worker, Contract: task.Contract, ContractSHA256: e2eContractDigest(state, task.Contract), Scope: e2eScopeForTask(state, task.Contract), Dependencies: []e2eDependencyBinding{}, Diagnostic: diagnostic, DiagnosticInputs: []e2eDiagnosticBinding{}}
	for _, dep := range e2eDependencies(state, task.Contract) {
		depIndex, _ := e2eTaskIndex(state, dep.TaskID)
		producer := state.Tasks[depIndex]
		if producer.Status != "accepted" || (dep.Require == "passed" && producer.Outcome != "pass") {
			if !diagnostic {
				return service.failureWithState("blocked", "task prerequisites are not accepted with the required outcome", state, fmt.Errorf("%s requires %s %s", task.Contract.ID, dep.TaskID, dep.Require))
			}
			packet.DiagnosticInputs = append(packet.DiagnosticInputs, e2eDiagnosticBinding{TaskID: dep.TaskID, Status: producer.Status, Submission: producer.Submission, Review: producer.Review})
			continue
		}
		var submitted e2eSubmission
		if err := service.readSnapshot(producer.Submission, &submitted); err != nil {
			return service.failureWithState("blocked", "accepted producer outputs are unavailable", state, err)
		}
		packet.Dependencies = append(packet.Dependencies, e2eDependencyBinding{TaskID: dep.TaskID, Require: dep.Require, Acceptance: producer.Acceptance, Outputs: submitted.Outputs})
	}
	for i, other := range state.Tasks {
		if i == index || !e2eContains([]string{"running", "submitted", "reviewing", "verified"}, other.Status) {
			continue
		}
		if e2ePathsOverlap(task.Contract.Outputs, other.Contract.Outputs) || e2ePathsOverlap(task.Contract.Outputs, other.Contract.Inputs) || e2ePathsOverlap(task.Contract.Inputs, other.Contract.Outputs) || e2eOverlap(task.Contract.Resources, other.Contract.Resources) {
			return service.failureWithState("blocked", "active e2e task owns overlapping read/write paths or exclusive resources", state, fmt.Errorf("%s conflicts with %s", task.Contract.ID, other.Contract.ID))
		}
	}
	packet.Inputs, err = service.bindFiles(task.Contract.Inputs)
	if err != nil {
		return service.failureWithState("blocked", "task inputs are unavailable", state, err)
	}
	contract := e2eTaskContract{SchemaVersion: "e2e-task-contract-v1", RunID: state.RunID, TaskID: packet.TaskID, Mode: state.Mode, ContractSHA256: packet.ContractSHA256, Contract: packet.Contract, Scope: packet.Scope}
	contractRef, contractRaw, err := service.snapshot(contract)
	if err != nil {
		return service.failureWithState("error", "cannot render original task contract", state, err)
	}
	packet.ContractRef = contractRef
	packet.WorkerTaskPacket = e2eWorkerPacketView(packet)
	ref, raw, err := service.snapshot(packet)
	if err != nil {
		return service.failureWithState("error", "cannot render worker packet", state, err)
	}
	task.Status, task.WorkerID, task.Packet, task.Attempt = "running", worker, ref, task.Attempt+1
	if !e2eContains(task.AuthorIDs, worker) {
		task.AuthorIDs = append(task.AuthorIDs, worker)
	}
	state.Revision++
	if err := service.persist(state, "task-start", map[string][]byte{ref.Ref: raw, contractRef.Ref: contractRaw}); err != nil {
		return e2eFailure("error", "cannot start e2e task", err)
	}
	env := service.envelope("ok", "E2E worker packet frozen; dispatch the actual native worker", state)
	env.Data["packet"], env.Data["packet_ref"], env.Data["packet_sha256"], env.Data["attempt_id"] = packet, ref.Ref, ref.SHA256, packet.AttemptID
	env.Data["worker_task_packet"] = packet.WorkerTaskPacket
	env.Data["worker_task_packet_binding"] = map[string]any{"artifact_ref": ref.Ref, "artifact_sha256": ref.SHA256, "json_pointer": "/worker_task_packet"}
	env.Data["submission_template"] = e2eSubmissionTemplate(packet, ref)
	env.NextArgv = service.argv(state, "task-submit", "--task-id", task.Contract.ID, "--worker-id", worker, "--result-json", "<semantic-json|@path|->")
	return env
}

func (service *e2eService) taskSubmit(state *e2eState, args []string) Envelope {
	index, err := e2eTaskIndex(state, optionValue(args, "--task-id", ""))
	if err != nil {
		return service.failureWithState("invalid", "unknown e2e task", state, err)
	}
	task := &state.Tasks[index]
	if task.Status != "running" || optionValue(args, "--worker-id", "") != task.WorkerID {
		return service.failureWithState("blocked", "submission must match the active worker attempt", state, nil)
	}
	var input e2eSubmissionInput
	if err := service.input(args, "--result-json", &input); err != nil {
		return service.failureWithState("invalid", "invalid worker submission", state, err)
	}
	if input.PacketSHA256 != task.Packet.SHA256 || !e2eContains([]string{"pass", "failed", "blocked"}, input.Outcome) {
		return service.failureWithState("invalid", "submission packet or observed outcome does not match", state, nil)
	}
	var packet e2ePacket
	if err := service.readSnapshot(task.Packet, &packet); err != nil {
		return service.failureWithState("blocked", "worker packet is unavailable", state, err)
	}
	if packet.Diagnostic && input.Outcome == "pass" {
		return service.failureWithState("invalid", "diagnostic work cannot establish a passing outcome", state, nil)
	}
	workerResult, err := normalizeE2EWorkerResult(input.WorkerResult, input.Outcome)
	if err != nil {
		return service.failureWithState("invalid", "invalid WorkerTaskResult", state, err)
	}
	if asString(workerResult["task_id"]) != task.Contract.ID || asString(workerResult["packet_id"]) != task.Packet.SHA256 || asString(workerResult["status"]) == "pending" || strings.TrimSpace(asString(workerResult["summary"])) == "" {
		return service.failureWithState("invalid", "WorkerTaskResult must match the task and exact packet, with a real non-pending result", state, nil)
	}
	evidence, allPass, err := service.validateChecks(task.Contract, input.Checks, false)
	if err != nil {
		return service.failureWithState("invalid", "every assigned scope/acceptance row requires reproducible evidence", state, err)
	}
	if input.Outcome == "pass" && (!allPass || asString(workerResult["status"]) != "success" || len(asStringList(workerResult["blockers"])) > 0) {
		return service.failureWithState("invalid", "a passing outcome requires all checks passed and a successful unblocked worker result", state, nil)
	}
	outputs, err := service.bindFiles(task.Contract.Outputs)
	if err != nil {
		return service.failureWithState("invalid", "all declared stage outputs must exist before submission", state, err)
	}
	submission := e2eSubmission{SchemaVersion: "e2e-worker-result-v1", Packet: task.Packet, WorkerID: task.WorkerID, WorkerResult: workerResult, WorkerResultInput: input.WorkerResult, Outcome: input.Outcome, Checks: input.Checks, Outputs: outputs, Evidence: evidence}
	ref, raw, err := service.snapshot(submission)
	if err != nil {
		return e2eFailure("error", "cannot render e2e submission", err)
	}
	task.Status, task.Submission, task.Outcome = "submitted", ref, input.Outcome
	state.Revision++
	if err := service.persist(state, "task-submit", map[string][]byte{ref.Ref: raw}); err != nil {
		return e2eFailure("error", "cannot submit e2e result", err)
	}
	env := service.envelope("ok", "E2E worker result submitted; independent review and leader acceptance remain required", state)
	env.Data["submission_ref"], env.Data["submission_sha256"] = ref.Ref, ref.SHA256
	env.NextArgv = service.argv(state, "review-start", "--task-id", task.Contract.ID, "--validator-id", "<independent-agent-id>")
	return env
}

func (service *e2eService) reviewStart(state *e2eState, args []string) Envelope {
	index, err := e2eTaskIndex(state, optionValue(args, "--task-id", ""))
	if err != nil {
		return service.failureWithState("invalid", "unknown e2e task", state, err)
	}
	task := &state.Tasks[index]
	validator := optionValue(args, "--validator-id", "")
	if task.Status != "submitted" {
		return service.failureWithState("blocked", "review-start requires a current submitted result", state, nil)
	}
	if !e2eIdentity(validator) || validator == state.LeaderID || validator == task.WorkerID || e2eAuthorConflict(state, index, validator) {
		return service.failureWithState("blocked", "reviewer must be independently recorded from the leader and output authors", state, nil)
	}
	request := e2eReviewPacket{SchemaVersion: "e2e-review-packet-v1", RunID: state.RunID, TaskID: task.Contract.ID, ValidatorID: validator, Packet: task.Packet, Submission: task.Submission, Contract: task.Contract, Scope: e2eScopeForTask(state, task.Contract)}
	var submitted e2eSubmission
	if err := service.readSnapshot(task.Submission, &submitted); err != nil {
		return service.failureWithState("blocked", "submission is unavailable for independent review", state, err)
	}
	request.WorkerTaskPacket = e2eReviewWorkerPacketView(request, submitted)
	ref, raw, err := service.snapshot(request)
	if err != nil {
		return e2eFailure("error", "cannot render review packet", err)
	}
	task.Status, task.ValidatorID, task.ReviewPacket = "reviewing", validator, ref
	state.Revision++
	if err := service.persist(state, "review-start", map[string][]byte{ref.Ref: raw}); err != nil {
		return e2eFailure("error", "cannot start independent review", err)
	}
	env := service.envelope("ok", "E2E independent review packet frozen against the original task and exact submission", state)
	env.Data["review_packet"], env.Data["review_packet_ref"], env.Data["review_packet_sha256"] = request, ref.Ref, ref.SHA256
	env.Data["worker_task_packet"] = request.WorkerTaskPacket
	env.Data["worker_task_packet_binding"] = map[string]any{"artifact_ref": ref.Ref, "artifact_sha256": ref.SHA256, "json_pointer": "/worker_task_packet"}
	env.Data["review_template"] = map[string]any{"review_packet_sha256": ref.SHA256, "submission_sha256": task.Submission.SHA256, "checks": e2eCheckTemplate(task.Contract, true)}
	env.NextArgv = service.argv(state, "review-submit", "--task-id", task.Contract.ID, "--validator-id", validator, "--result-json", "<semantic-json|@path|->")
	return env
}

func (service *e2eService) reviewSubmit(state *e2eState, args []string) Envelope {
	index, err := e2eTaskIndex(state, optionValue(args, "--task-id", ""))
	if err != nil {
		return service.failureWithState("invalid", "unknown e2e task", state, err)
	}
	task := &state.Tasks[index]
	if task.Status != "reviewing" || optionValue(args, "--validator-id", "") != task.ValidatorID {
		return service.failureWithState("blocked", "review must match the active independent reviewer", state, nil)
	}
	var input e2eReviewInput
	if err := service.input(args, "--result-json", &input); err != nil {
		return service.failureWithState("invalid", "invalid independent review", state, err)
	}
	if input.ReviewPacketSHA256 != task.ReviewPacket.SHA256 || input.SubmissionSHA256 != task.Submission.SHA256 {
		return service.failureWithState("invalid", "review does not bind the exact current request and submission", state, nil)
	}
	evidence, allPass, err := service.validateChecks(task.Contract, input.Checks, true)
	if err != nil {
		return service.failureWithState("invalid", "review must account for every acceptance row", state, err)
	}
	review := e2eReview{SchemaVersion: "e2e-independent-review-v1", Request: task.ReviewPacket, Submission: task.Submission, ValidatorID: task.ValidatorID, Checks: input.Checks, Evidence: evidence}
	ref, raw, err := service.snapshot(review)
	if err != nil {
		return e2eFailure("error", "cannot render independent review", err)
	}
	task.Review, task.Status = ref, "verified"
	if !allPass {
		task.Status = "rejected"
	}
	state.Revision++
	if err := service.persist(state, "review-submit", map[string][]byte{ref.Ref: raw}); err != nil {
		return e2eFailure("error", "cannot persist independent review", err)
	}
	if !allPass {
		return service.failureWithState("blocked", "independent review rejected the output; preserve evidence and reopen for bounded repair", state, nil)
	}
	env := service.envelope("ok", "E2E result independently verified; leader acceptance remains required", state)
	env.Data["review_ref"], env.Data["review_sha256"] = ref.Ref, ref.SHA256
	env.NextArgv = service.argv(state, "task-accept", "--task-id", task.Contract.ID, "--leader-id", state.LeaderID)
	return env
}

func (service *e2eService) taskAccept(state *e2eState, args []string) Envelope {
	if optionValue(args, "--leader-id", "") != state.LeaderID {
		return service.failureWithState("blocked", "only the recorded E2E leader may accept a result", state, nil)
	}
	index, err := e2eTaskIndex(state, optionValue(args, "--task-id", ""))
	if err != nil {
		return service.failureWithState("invalid", "unknown e2e task", state, err)
	}
	task := &state.Tasks[index]
	if task.Status != "verified" {
		return service.failureWithState("blocked", "task-accept requires a current fully verified result", state, nil)
	}
	receipt := e2eAcceptance{SchemaVersion: "e2e-acceptance-v1", RunID: state.RunID, TaskID: task.Contract.ID, LeaderID: state.LeaderID, Packet: task.Packet, Submission: task.Submission, ReviewPacket: task.ReviewPacket, Review: task.Review, Outcome: task.Outcome}
	ref, raw, err := service.snapshot(receipt)
	if err != nil {
		return e2eFailure("error", "cannot render acceptance receipt", err)
	}
	task.Acceptance, task.Status = ref, "accepted"
	state.Revision++
	if err := service.persist(state, "task-accept", map[string][]byte{ref.Ref: raw}); err != nil {
		return e2eFailure("error", "cannot accept e2e result", err)
	}
	env := service.envelope("ok", "E2E exact submission and independent review accepted", state)
	env.Data["acceptance_ref"], env.Data["acceptance_sha256"], env.Data["accepted_outcome"] = ref.Ref, ref.SHA256, task.Outcome
	return env
}

func (service *e2eService) reopen(state *e2eState, args []string) Envelope {
	if optionValue(args, "--leader-id", "") != state.LeaderID {
		return service.failureWithState("blocked", "only the recorded leader may reopen E2E work", state, nil)
	}
	id, reason := optionValue(args, "--task-id", ""), strings.TrimSpace(optionValue(args, "--reason", ""))
	if _, err := e2eTaskIndex(state, id); err != nil || reason == "" {
		return service.failureWithState("invalid", "reopen requires a known task and causal reason", state, err)
	}
	evidence, err := service.bindFiles(optionValues(args, "--evidence-ref"))
	if err != nil || len(evidence) == 0 {
		return service.failureWithState("invalid", "reopen requires raw evidence for the failed gate", state, err)
	}
	seeds := service.staleTasks(state)
	seeds[id] = true
	ids := e2eInvalidate(state, seeds, reason)
	event := map[string]any{"schema_version": "e2e-reopen-v1", "run_id": state.RunID, "from_revision": state.Revision, "leader_id": state.LeaderID, "earliest_task_id": id, "reason": reason, "evidence": evidence, "invalidated_task_ids": ids}
	ref, raw, err := service.snapshot(event)
	if err != nil {
		return e2eFailure("error", "cannot render reopen event", err)
	}
	state.Events = append(state.Events, ref)
	state.Revision++
	if err := service.persist(state, "reopen", map[string][]byte{ref.Ref: raw}); err != nil {
		return e2eFailure("error", "cannot reopen e2e work", err)
	}
	env := service.envelope("ok", "E2E producer and affected consumers reopened; old evidence remains in history", state)
	env.Data["invalidated_task_ids"] = ids
	return env
}

func (service *e2eService) scopeAdd(state *e2eState, args []string) Envelope {
	if optionValue(args, "--leader-id", "") != state.LeaderID {
		return service.failureWithState("blocked", "only the recorded leader may expand E2E scope", state, nil)
	}
	reason := strings.TrimSpace(optionValue(args, "--reason", ""))
	evidence, err := service.bindFiles(optionValues(args, "--evidence-ref"))
	if err != nil || len(evidence) == 0 || reason == "" {
		return service.failureWithState("invalid", "scope-add requires discovery evidence and a causal reason", state, err)
	}
	var input e2ePlanInput
	if err := service.input(args, "--input-json", &input); err != nil || input.Mode != "" || len(input.Tasks) == 0 {
		return service.failureWithState("invalid", "scope-add accepts new scope/tasks, never a replacement mode or an empty task set", state, err)
	}
	merged := e2ePlanInput{Mode: state.Mode, Scope: append(append([]e2eScope{}, state.Scope...), input.Scope...), Tasks: []e2eTaskSpec{}}
	for _, task := range state.Tasks {
		merged.Tasks = append(merged.Tasks, task.Contract)
	}
	merged.Tasks = append(merged.Tasks, input.Tasks...)
	if err := e2eValidatePlan(merged); err != nil {
		return service.failureWithState("invalid", "expanded scope must retain all old targets and complete stage coverage", state, err)
	}
	seeds := map[string]bool{}
	for _, added := range input.Tasks {
		for _, old := range state.Tasks {
			if old.Contract.Stage >= added.Stage && e2eOverlap(old.Contract.ScopeIDs, added.ScopeIDs) {
				seeds[old.Contract.ID] = true
			}
		}
	}
	state.Scope = merged.Scope
	for _, task := range input.Tasks {
		state.Tasks = append(state.Tasks, e2eNewTask(task, state.Mode))
	}
	ids := e2eInvalidate(state, seeds, reason)
	event := map[string]any{"schema_version": "e2e-scope-expansion-v1", "run_id": state.RunID, "from_revision": state.Revision, "leader_id": state.LeaderID, "reason": reason, "evidence": evidence, "added_scope": input.Scope, "added_tasks": input.Tasks, "invalidated_task_ids": ids}
	ref, raw, err := service.snapshot(event)
	if err != nil {
		return e2eFailure("error", "cannot render scope expansion", err)
	}
	state.Events = append(state.Events, ref)
	state.Revision++
	if err := service.persist(state, "scope-add", map[string][]byte{ref.Ref: raw}); err != nil {
		return e2eFailure("error", "cannot expand e2e scope", err)
	}
	env := service.envelope("ok", "E2E denominator expanded without removing old scope or evidence", state)
	env.Data["invalidated_task_ids"] = ids
	return env
}

func (service *e2eService) close(state *e2eState, args []string) Envelope {
	if optionValue(args, "--leader-id", "") != state.LeaderID {
		return service.failureWithState("blocked", "only the recorded leader may close E2E work", state, nil)
	}
	outcome := optionValue(args, "--outcome", "")
	if !e2eContains([]string{"pass", "failed", "blocked"}, outcome) {
		return service.failureWithState("invalid", "close requires --outcome pass, failed, or blocked", state, nil)
	}
	unaccepted, nonpassing, reports := []string{}, []string{}, map[string]bool{}
	for _, task := range state.Tasks {
		if task.Status == "not_requested" {
			continue
		}
		if task.Status != "accepted" {
			unaccepted = append(unaccepted, task.Contract.ID)
		}
		if task.Outcome != "pass" {
			nonpassing = append(nonpassing, task.Contract.ID)
		}
		if task.Contract.Stage == 7 && task.Status == "accepted" {
			for _, scope := range task.Contract.ScopeIDs {
				reports[scope] = true
			}
		}
	}
	if outcome == "pass" && (len(unaccepted) > 0 || len(nonpassing) > 0) {
		return service.failureWithState("blocked", "full-scope close requires every mandatory task and row accepted with passing outcomes", state, fmt.Errorf("unaccepted=%v nonpassing=%v", unaccepted, nonpassing))
	}
	if outcome != "pass" {
		for _, scope := range state.Scope {
			if !reports[scope.ID] {
				return service.failureWithState("blocked", "blocked/failure close still requires independently accepted stage 7 reports for every scope", state, fmt.Errorf("missing report for %s", scope.ID))
			}
		}
	}
	status := "complete"
	if state.Mode == "planning" {
		status = "planning-complete"
	}
	if outcome != "pass" {
		status = "reported"
		if len(unaccepted) > 0 {
			status = "blocked"
		}
	}
	acceptances := map[string]e2eRef{}
	for _, task := range state.Tasks {
		if task.Status == "accepted" {
			acceptances[task.Contract.ID] = task.Acceptance
		}
	}
	report := map[string]any{"schema_version": "e2e-closeout-v1", "run_id": state.RunID, "from_revision": state.Revision, "leader_id": state.LeaderID, "mode": state.Mode, "outcome": outcome, "status": status, "product_pass": status == "complete", "scope": state.Scope, "acceptances": acceptances, "unaccepted_task_ids": unaccepted, "nonpassing_task_ids": nonpassing}
	ref, raw, err := service.snapshot(report)
	if err != nil {
		return e2eFailure("error", "cannot render E2E closeout", err)
	}
	state.Status, state.Closeout = status, ref
	state.Revision++
	if err := service.persist(state, "close", map[string][]byte{ref.Ref: raw}); err != nil {
		return e2eFailure("error", "cannot close E2E run", err)
	}
	env := service.envelope("ok", "E2E scope report recorded with truthful execution and completion claims", state)
	env.Data["closeout_ref"], env.Data["closeout_sha256"] = ref.Ref, ref.SHA256
	return env
}

func e2eValidatePlan(input e2ePlanInput) error {
	if input.Mode != "execution" && input.Mode != "planning" {
		return fmt.Errorf("mode must be execution or planning")
	}
	if len(input.Scope) == 0 || len(input.Tasks) == 0 {
		return fmt.Errorf("the complete scope and task denominator must not be empty")
	}
	scopes := map[string]bool{}
	for _, scope := range input.Scope {
		if !e2eIDPattern.MatchString(scope.ID) || scopes[scope.ID] || strings.TrimSpace(scope.Target) == "" || strings.TrimSpace(scope.Operation) == "" {
			return fmt.Errorf("scope entries require unique IDs, target and operation: %s", scope.ID)
		}
		scopes[scope.ID] = true
	}
	ids := map[string]bool{}
	coverage := map[string]map[int]bool{}
	for id := range scopes {
		coverage[id] = map[int]bool{}
	}
	for _, task := range input.Tasks {
		if !e2eIDPattern.MatchString(task.ID) || ids[task.ID] || task.Stage < 1 || task.Stage > 7 {
			return fmt.Errorf("task IDs must be unique and stages must be 1 through 7: %s", task.ID)
		}
		ids[task.ID] = true
		if !e2eUniqueNonEmpty(task.ScopeIDs) || len(task.ScopeIDs) == 0 || len(task.Acceptance) == 0 {
			return fmt.Errorf("task %s needs unique scope_ids and nonempty acceptance criteria", task.ID)
		}
		for _, scope := range task.ScopeIDs {
			if !scopes[scope] {
				return fmt.Errorf("task %s references unknown scope %s", task.ID, scope)
			}
			coverage[scope][task.Stage] = true
		}
		criteria := map[string]bool{}
		for _, criterion := range task.Acceptance {
			if !e2eIDPattern.MatchString(criterion.ID) || criteria[criterion.ID] || strings.TrimSpace(criterion.Criterion) == "" {
				return fmt.Errorf("task %s has duplicate or empty acceptance criterion", task.ID)
			}
			criteria[criterion.ID] = true
		}
		if task.Inputs == nil || len(task.Outputs) == 0 || !e2eUniqueNonEmpty(task.Inputs) || !e2eUniqueNonEmpty(task.Outputs) || !e2eUniqueNonEmpty(task.Resources) {
			return fmt.Errorf("task %s requires declared unique inputs, nonempty outputs, and unique resources", task.ID)
		}
		for _, ref := range append(append([]string{}, task.Inputs...), task.Outputs...) {
			if err := e2eAssetRef(ref); err != nil {
				return fmt.Errorf("task %s: %w", task.ID, err)
			}
		}
		if e2ePathsOverlap(task.Inputs, task.Outputs) {
			return fmt.Errorf("task %s cannot mutate its own frozen inputs; reopen the producer instead", task.ID)
		}
	}
	for scope, stages := range coverage {
		for stage := 1; stage <= 7; stage++ {
			if !stages[stage] {
				return fmt.Errorf("requested scope %s is missing stage %d task coverage", scope, stage)
			}
		}
	}
	state := e2eState{Mode: input.Mode}
	for _, task := range input.Tasks {
		seen := map[string]bool{}
		for _, dep := range task.DependsOn {
			if !ids[dep.TaskID] || dep.TaskID == task.ID || seen[dep.TaskID] || !e2eContains([]string{"accepted", "passed"}, dep.Require) {
				return fmt.Errorf("task %s has an invalid, duplicate, self or unknown dependency", task.ID)
			}
			seen[dep.TaskID] = true
		}
		state.Tasks = append(state.Tasks, e2eNewTask(task, input.Mode))
	}
	visiting, visited := map[string]bool{}, map[string]bool{}
	var walk func(string) error
	walk = func(id string) error {
		if visiting[id] {
			return fmt.Errorf("task dependency cycle at %s", id)
		}
		if visited[id] {
			return nil
		}
		visiting[id] = true
		i, _ := e2eTaskIndex(&state, id)
		for _, dep := range e2eDependencies(&state, state.Tasks[i].Contract) {
			if err := walk(dep.TaskID); err != nil {
				return err
			}
		}
		visiting[id], visited[id] = false, true
		return nil
	}
	for id := range ids {
		if err := walk(id); err != nil {
			return err
		}
	}
	for consumerIndex, consumer := range state.Tasks {
		if consumer.Status == "not_requested" {
			continue
		}
		for _, producer := range state.Tasks {
			if producer.Contract.ID == consumer.Contract.ID || !e2ePathsOverlap(producer.Contract.Outputs, consumer.Contract.Inputs) {
				continue
			}
			if !e2eDependsOnTask(&state, consumerIndex, producer.Contract.ID) {
				return fmt.Errorf("task %s reads output owned by %s without a producer dependency; stale leftovers cannot satisfy an input", consumer.Contract.ID, producer.Contract.ID)
			}
		}
	}
	return nil
}

func e2eDependsOnTask(state *e2eState, index int, producerID string) bool {
	visited := map[string]bool{}
	var walk func(int) bool
	walk = func(i int) bool {
		id := state.Tasks[i].Contract.ID
		if visited[id] {
			return false
		}
		visited[id] = true
		for _, dep := range e2eDependencies(state, state.Tasks[i].Contract) {
			if dep.TaskID == producerID {
				return true
			}
			j, err := e2eTaskIndex(state, dep.TaskID)
			if err == nil && walk(j) {
				return true
			}
		}
		return false
	}
	return walk(index)
}

func e2eNewTask(contract e2eTaskSpec, mode string) e2eTaskState {
	status := "pending"
	if mode == "planning" && contract.Stage >= 3 && contract.Stage <= 5 {
		status = "not_requested"
	}
	return e2eTaskState{Contract: contract, Status: status, History: []e2eRef{}, AuthorIDs: []string{}}
}

// Implicit stage prerequisites cannot be weakened by an agent-authored DAG.
// Every overlapping producer at the immediately preceding requested stage is
// consumed. Audit/report tasks additionally join all earlier requested stages.
func e2eDependencies(state *e2eState, task e2eTaskSpec) []e2eDependency {
	if state.Mode == "planning" && task.Stage >= 3 && task.Stage <= 5 {
		return nil
	}
	previous := task.Stage - 1
	if state.Mode == "planning" && task.Stage == 6 {
		previous = 2
	}
	deps := map[string]string{}
	for _, candidate := range state.Tasks {
		if candidate.Contract.ID == task.ID || candidate.Status == "not_requested" || !e2eOverlap(task.ScopeIDs, candidate.Contract.ScopeIDs) {
			continue
		}
		if candidate.Contract.Stage == previous || (task.Stage >= 6 && candidate.Contract.Stage < task.Stage) {
			require := "passed"
			if task.Stage >= 5 {
				require = "accepted"
			}
			deps[candidate.Contract.ID] = require
		}
	}
	for _, dep := range task.DependsOn {
		if deps[dep.TaskID] != "passed" {
			deps[dep.TaskID] = dep.Require
		}
	}
	ids := []string{}
	for id := range deps {
		ids = append(ids, id)
	}
	sort.Strings(ids)
	result := []e2eDependency{}
	for _, id := range ids {
		result = append(result, e2eDependency{TaskID: id, Require: deps[id]})
	}
	return result
}

func e2eAuthorConflict(state *e2eState, index int, identity string) bool {
	seen := map[string]bool{}
	var visit func(int) bool
	visit = func(i int) bool {
		task := state.Tasks[i]
		if seen[task.Contract.ID] {
			return false
		}
		seen[task.Contract.ID] = true
		if task.WorkerID == identity || e2eContains(task.AuthorIDs, identity) {
			return true
		}
		for _, dep := range e2eDependencies(state, task.Contract) {
			j, err := e2eTaskIndex(state, dep.TaskID)
			if err == nil && visit(j) {
				return true
			}
		}
		return false
	}
	return visit(index)
}

func e2eAncestorAuthorConflict(state *e2eState, index int, identity string) bool {
	for _, dep := range e2eDependencies(state, state.Tasks[index].Contract) {
		i, err := e2eTaskIndex(state, dep.TaskID)
		if err == nil && e2eAuthorConflict(state, i, identity) {
			return true
		}
	}
	return false
}

func e2eInvalidate(state *e2eState, seeds map[string]bool, reason string) []string {
	affected := map[string]bool{}
	for id := range seeds {
		affected[id] = true
	}
	changed := true
	for changed {
		changed = false
		for _, task := range state.Tasks {
			if affected[task.Contract.ID] {
				continue
			}
			for _, dep := range e2eDependencies(state, task.Contract) {
				if affected[dep.TaskID] {
					affected[task.Contract.ID], changed = true, true
					break
				}
			}
		}
	}
	ids := []string{}
	for index := range state.Tasks {
		task := &state.Tasks[index]
		if !affected[task.Contract.ID] || task.Status == "not_requested" {
			continue
		}
		for _, ref := range []e2eRef{task.Packet, task.Submission, task.ReviewPacket, task.Review, task.Acceptance} {
			if ref.Ref != "" && !e2eRefIn(task.History, ref) {
				task.History = append(task.History, ref)
			}
		}
		task.Status, task.WorkerID, task.ValidatorID, task.Outcome = "pending", "", "", ""
		task.Packet, task.Submission, task.ReviewPacket, task.Review, task.Acceptance = e2eRef{}, e2eRef{}, e2eRef{}, e2eRef{}, e2eRef{}
		task.ReopenReason = reason
		ids = append(ids, task.Contract.ID)
	}
	if state.Closeout.Ref != "" {
		state.Events = append(state.Events, state.Closeout)
	}
	state.Closeout, state.Status = e2eRef{}, "active"
	sort.Strings(ids)
	return ids
}

func (service *e2eService) staleTasks(state *e2eState) map[string]bool {
	stale := map[string]bool{}
	for index, task := range state.Tasks {
		if task.Packet.Ref == "" {
			continue
		}
		if err := service.verifyTask(state, index); err != nil {
			stale[task.Contract.ID] = true
		}
	}
	return stale
}

func (service *e2eService) verifyTask(state *e2eState, index int) error {
	task := state.Tasks[index]
	var packet e2ePacket
	if err := service.readSnapshot(task.Packet, &packet); err != nil {
		return err
	}
	if packet.SchemaVersion != "e2e-worker-packet-v1" || packet.RunID != state.RunID || packet.TaskID != task.Contract.ID || packet.WorkerID != task.WorkerID || packet.AttemptID != fmt.Sprintf("%s-%04d", task.Contract.ID, task.Attempt) || packet.ContractSHA256 != e2eContractDigest(state, task.Contract) || !e2eSameJSON(packet.Contract, task.Contract) || !e2eSameJSON(packet.Scope, e2eScopeForTask(state, task.Contract)) {
		return fmt.Errorf("worker packet binding changed")
	}
	if !e2eSameJSON(packet.WorkerTaskPacket, e2eWorkerPacketView(packet)) {
		return fmt.Errorf("standard WorkerTaskPacket view no longer matches E2E bindings")
	}
	if err := service.verifyBindings(packet.Inputs, task.Contract.Inputs); err != nil {
		return err
	}
	deps := map[string]e2eDependency{}
	for _, dep := range e2eDependencies(state, task.Contract) {
		deps[dep.TaskID] = dep
	}
	for _, binding := range packet.Dependencies {
		dep, ok := deps[binding.TaskID]
		if !ok || dep.Require != binding.Require {
			return fmt.Errorf("dependency contract changed")
		}
		i, _ := e2eTaskIndex(state, dep.TaskID)
		producer := state.Tasks[i]
		if producer.Status != "accepted" || producer.Acceptance != binding.Acceptance || (dep.Require == "passed" && producer.Outcome != "pass") {
			return fmt.Errorf("accepted dependency %s changed", dep.TaskID)
		}
		var receipt e2eAcceptance
		if err := service.readSnapshot(binding.Acceptance, &receipt); err != nil {
			return err
		}
		var submitted e2eSubmission
		if err := service.readSnapshot(producer.Submission, &submitted); err != nil {
			return err
		}
		left, _ := json.Marshal(binding.Outputs)
		right, _ := json.Marshal(submitted.Outputs)
		if !bytes.Equal(left, right) {
			return fmt.Errorf("accepted dependency output bindings changed")
		}
		if err := service.verifyBindings(binding.Outputs, producer.Contract.Outputs); err != nil {
			return err
		}
		delete(deps, binding.TaskID)
	}
	if packet.Diagnostic && task.Contract.Stage < 6 {
		return fmt.Errorf("invalid diagnostic stage")
	}
	for _, binding := range packet.DiagnosticInputs {
		if !packet.Diagnostic {
			return fmt.Errorf("diagnostic inputs cannot unlock ordinary dependencies")
		}
		if _, ok := deps[binding.TaskID]; !ok {
			return fmt.Errorf("unexpected diagnostic dependency")
		}
		i, _ := e2eTaskIndex(state, binding.TaskID)
		producer := state.Tasks[i]
		if producer.Status != binding.Status || producer.Submission != binding.Submission || producer.Review != binding.Review {
			return fmt.Errorf("diagnostic dependency %s changed", binding.TaskID)
		}
		delete(deps, binding.TaskID)
	}
	if len(deps) != 0 {
		return fmt.Errorf("packet omitted a required dependency")
	}
	if task.Submission.Ref == "" {
		if task.Status != "running" {
			return fmt.Errorf("task is missing its submission")
		}
		return nil
	}
	var submission e2eSubmission
	if err := service.readSnapshot(task.Submission, &submission); err != nil {
		return err
	}
	if submission.SchemaVersion != "e2e-worker-result-v1" || submission.Packet != task.Packet || submission.WorkerID != task.WorkerID || submission.Outcome != task.Outcome || (packet.Diagnostic && submission.Outcome == "pass") {
		return fmt.Errorf("submission binding changed")
	}
	if asString(submission.WorkerResult["task_id"]) != task.Contract.ID || asString(submission.WorkerResult["packet_id"]) != task.Packet.SHA256 {
		return fmt.Errorf("WorkerTaskResult identity changed")
	}
	normalized, err := normalizeE2EWorkerResult(submission.WorkerResultInput, submission.Outcome)
	if err != nil || !e2eSameJSON(normalized, submission.WorkerResult) {
		return fmt.Errorf("normalized WorkerTaskResult lost or changed reported validation: %v", err)
	}
	if err := service.verifyBindings(submission.Outputs, task.Contract.Outputs); err != nil {
		return err
	}
	if err := service.verifyBindings(submission.Evidence, e2eEvidenceRefs(submission.Checks)); err != nil {
		return err
	}
	_, allPass, err := service.validateChecks(task.Contract, submission.Checks, false)
	if err != nil || (submission.Outcome == "pass" && (!allPass || asString(submission.WorkerResult["status"]) != "success" || len(asStringList(submission.WorkerResult["blockers"])) != 0)) {
		return fmt.Errorf("submission acceptance rows changed: %v", err)
	}
	if task.ReviewPacket.Ref == "" {
		if task.Status != "submitted" {
			return fmt.Errorf("task is missing its independent review request")
		}
		return nil
	}
	var request e2eReviewPacket
	if err := service.readSnapshot(task.ReviewPacket, &request); err != nil {
		return err
	}
	if request.SchemaVersion != "e2e-review-packet-v1" || request.RunID != state.RunID || request.TaskID != task.Contract.ID || request.Packet != task.Packet || request.Submission != task.Submission || request.ValidatorID != task.ValidatorID || !e2eIdentity(task.ValidatorID) || task.ValidatorID == state.LeaderID || e2eAuthorConflict(state, index, task.ValidatorID) || !e2eSameJSON(request.Contract, task.Contract) || !e2eSameJSON(request.Scope, e2eScopeForTask(state, task.Contract)) {
		return fmt.Errorf("independent review request is stale or not independent")
	}
	if !e2eSameJSON(request.WorkerTaskPacket, e2eReviewWorkerPacketView(request, submission)) {
		return fmt.Errorf("standard review WorkerTaskPacket view changed")
	}
	if task.Review.Ref == "" {
		if task.Status != "reviewing" {
			return fmt.Errorf("task is missing its review result")
		}
		return nil
	}
	var review e2eReview
	if err := service.readSnapshot(task.Review, &review); err != nil {
		return err
	}
	if review.SchemaVersion != "e2e-independent-review-v1" || review.Request != task.ReviewPacket || review.Submission != task.Submission || review.ValidatorID != task.ValidatorID {
		return fmt.Errorf("independent review result changed")
	}
	if err := service.verifyBindings(review.Evidence, e2eEvidenceRefs(review.Checks)); err != nil {
		return err
	}
	_, reviewPass, err := service.validateChecks(task.Contract, review.Checks, true)
	if err != nil || (!reviewPass && task.Status != "rejected") {
		return fmt.Errorf("independent review did not pass every row: %v", err)
	}
	if task.Acceptance.Ref == "" {
		if task.Status != "verified" && task.Status != "rejected" {
			return fmt.Errorf("task is missing its acceptance receipt")
		}
		return nil
	}
	var receipt e2eAcceptance
	if err := service.readSnapshot(task.Acceptance, &receipt); err != nil {
		return err
	}
	if task.Status != "accepted" || !reviewPass || receipt.SchemaVersion != "e2e-acceptance-v1" || receipt.RunID != state.RunID || receipt.TaskID != task.Contract.ID || receipt.LeaderID != state.LeaderID || receipt.Packet != task.Packet || receipt.Submission != task.Submission || receipt.ReviewPacket != task.ReviewPacket || receipt.Review != task.Review || receipt.Outcome != task.Outcome {
		return fmt.Errorf("acceptance receipt no longer binds the exact verified result")
	}
	return nil
}

func (service *e2eService) validateChecks(task e2eTaskSpec, checks []e2eCheck, review bool) ([]e2eBinding, bool, error) {
	expected := map[string]bool{}
	for _, scope := range task.ScopeIDs {
		for _, criterion := range task.Acceptance {
			expected[scope+"\x00"+criterion.ID] = true
		}
	}
	allPass := true
	for _, check := range checks {
		key := check.ScopeID + "\x00" + check.AcceptanceID
		if !expected[key] {
			return nil, false, fmt.Errorf("unknown or duplicate acceptance row %s/%s", check.ScopeID, check.AcceptanceID)
		}
		delete(expected, key)
		if !e2eContains([]string{"passed", "failed", "blocked", "skipped", "not_run"}, check.Status) {
			return nil, false, fmt.Errorf("invalid check status")
		}
		if review && (!e2eContains([]string{"passed", "failed"}, check.Status) || !e2eContains([]string{"replayed", "inspected"}, check.Method)) {
			return nil, false, fmt.Errorf("review rows require passed/failed verdicts and inspected/replayed method")
		}
		for _, value := range []string{check.Expected, check.Actual, check.Reproduction, check.Preconditions} {
			if strings.TrimSpace(value) == "" {
				return nil, false, fmt.Errorf("each row needs expected, actual, reproduction and preconditions")
			}
		}
		if len(check.EvidenceRefs) == 0 || !e2eUniqueNonEmpty(check.EvidenceRefs) {
			return nil, false, fmt.Errorf("each row needs unique nonempty raw evidence references")
		}
		onlyLedger := true
		for _, ref := range check.EvidenceRefs {
			if filepath.Base(filepath.FromSlash(ref)) != "workflow-ledger.md" {
				onlyLedger = false
			}
		}
		if onlyLedger {
			return nil, false, fmt.Errorf("the mutable workflow ledger cannot be the sole evidence")
		}
		if check.Status != "passed" {
			allPass = false
		}
	}
	if len(expected) > 0 {
		missing := []string{}
		for key := range expected {
			missing = append(missing, strings.ReplaceAll(key, "\x00", "/"))
		}
		sort.Strings(missing)
		return nil, false, fmt.Errorf("missing %d assigned acceptance rows: %s", len(expected), strings.Join(missing, ", "))
	}
	evidence, err := service.bindFiles(e2eEvidenceRefs(checks))
	return evidence, allPass, err
}

func e2eEvidenceRefs(checks []e2eCheck) []string {
	refs := map[string]bool{}
	for _, check := range checks {
		for _, ref := range check.EvidenceRefs {
			refs[ref] = true
		}
	}
	result := []string{}
	for ref := range refs {
		result = append(result, ref)
	}
	sort.Strings(result)
	return result
}

func (service *e2eService) readState() (e2eState, error) {
	var state e2eState
	raw, err := service.readFile(service.rootRef + "/state.json")
	if err != nil {
		return state, err
	}
	if err := e2eDecode(raw, &state); err != nil {
		return state, err
	}
	if state.SchemaVersion != e2eWorkflowSchema || state.RunID != service.runID || state.Revision < 1 || !e2eIdentity(state.LeaderID) {
		return state, fmt.Errorf("E2E state identity is invalid")
	}
	plan := e2ePlanInput{Mode: state.Mode, Scope: state.Scope, Tasks: []e2eTaskSpec{}}
	for _, task := range state.Tasks {
		plan.Tasks = append(plan.Tasks, task.Contract)
		if !e2eContains([]string{"pending", "running", "submitted", "reviewing", "verified", "rejected", "accepted", "not_requested"}, task.Status) {
			return state, fmt.Errorf("invalid task status")
		}
		if (state.Mode == "planning" && task.Contract.Stage >= 3 && task.Contract.Stage <= 5) != (task.Status == "not_requested") {
			return state, fmt.Errorf("requested execution stage was silently removed")
		}
		if err := e2eValidateTaskState(task, state.LeaderID); err != nil {
			return state, err
		}
		for _, ref := range task.History {
			var snapshot map[string]any
			if err := service.readSnapshot(ref, &snapshot); err != nil {
				return state, fmt.Errorf("immutable task history is unavailable: %w", err)
			}
		}
	}
	if err := e2eValidatePlan(plan); err != nil {
		return state, err
	}
	for _, ref := range state.Events {
		var snapshot map[string]any
		if err := service.readSnapshot(ref, &snapshot); err != nil {
			return state, fmt.Errorf("immutable workflow history is unavailable: %w", err)
		}
	}
	if err := service.validateCloseoutState(state); err != nil {
		return state, err
	}
	return state, nil
}

func e2eValidateTaskState(task e2eTaskState, leader string) error {
	if task.Attempt < 0 || !e2eUniqueNonEmpty(task.AuthorIDs) {
		return fmt.Errorf("task %s has invalid attempt/authorship state", task.Contract.ID)
	}
	if task.Status == "pending" || task.Status == "not_requested" {
		if task.Packet.Ref != "" || task.Submission.Ref != "" || task.ReviewPacket.Ref != "" || task.Review.Ref != "" || task.Acceptance.Ref != "" || task.WorkerID != "" || task.ValidatorID != "" || task.Outcome != "" {
			return fmt.Errorf("unstarted task %s retained an active handoff", task.Contract.ID)
		}
		return nil
	}
	if task.Attempt < 1 || task.Packet.Ref == "" || !e2eIdentity(task.WorkerID) || task.WorkerID == leader || !e2eContains(task.AuthorIDs, task.WorkerID) {
		return fmt.Errorf("task %s status lacks a bound worker packet and author", task.Contract.ID)
	}
	if task.Status == "running" {
		if task.Submission.Ref != "" || task.Outcome != "" || task.ReviewPacket.Ref != "" || task.Review.Ref != "" || task.Acceptance.Ref != "" {
			return fmt.Errorf("running task %s retained a previous result or review", task.Contract.ID)
		}
		return nil
	}
	if task.Submission.Ref == "" || !e2eContains([]string{"pass", "failed", "blocked"}, task.Outcome) {
		return fmt.Errorf("task %s status lacks a bound submission and observed outcome", task.Contract.ID)
	}
	if task.Status == "submitted" {
		if task.ReviewPacket.Ref != "" || task.Review.Ref != "" || task.Acceptance.Ref != "" || task.ValidatorID != "" {
			return fmt.Errorf("submitted task %s retained a previous review", task.Contract.ID)
		}
		return nil
	}
	if task.ReviewPacket.Ref == "" || !e2eIdentity(task.ValidatorID) || task.ValidatorID == leader || e2eContains(task.AuthorIDs, task.ValidatorID) {
		return fmt.Errorf("task %s status lacks a bound independent review request", task.Contract.ID)
	}
	if task.Status == "reviewing" {
		if task.Review.Ref != "" || task.Acceptance.Ref != "" {
			return fmt.Errorf("reviewing task %s retained old review acceptance", task.Contract.ID)
		}
		return nil
	}
	if task.Review.Ref == "" {
		return fmt.Errorf("task %s status lacks an independent review result", task.Contract.ID)
	}
	if (task.Status == "accepted") != (task.Acceptance.Ref != "") {
		return fmt.Errorf("task %s acceptance status disagrees with its receipt", task.Contract.ID)
	}
	return nil
}

func (service *e2eService) validateCloseoutState(state e2eState) error {
	if !e2eContains([]string{"active", "complete", "planning-complete", "reported", "blocked"}, state.Status) {
		return fmt.Errorf("invalid E2E closeout status")
	}
	if state.Status == "active" {
		if state.Closeout.Ref != "" {
			return fmt.Errorf("active E2E state retained a terminal closeout")
		}
		return nil
	}
	if state.Closeout.Ref == "" {
		return fmt.Errorf("E2E terminal status requires an immutable closeout receipt")
	}
	var closeout e2eCloseout
	if err := service.readSnapshot(state.Closeout, &closeout); err != nil {
		return err
	}
	if closeout.SchemaVersion != "e2e-closeout-v1" || closeout.RunID != state.RunID || closeout.LeaderID != state.LeaderID || closeout.FromRevision+1 != state.Revision || closeout.Mode != state.Mode || closeout.Status != state.Status || closeout.ProductPass != (state.Status == "complete") || !e2eSameJSON(closeout.Scope, state.Scope) {
		return fmt.Errorf("E2E closeout no longer matches the exact runtime state")
	}
	unaccepted, nonpassing := []string{}, []string{}
	acceptances := map[string]e2eRef{}
	reports := map[string]bool{}
	for _, task := range state.Tasks {
		if task.Status == "not_requested" {
			continue
		}
		if task.Status != "accepted" {
			unaccepted = append(unaccepted, task.Contract.ID)
		} else {
			acceptances[task.Contract.ID] = task.Acceptance
		}
		if task.Outcome != "pass" {
			nonpassing = append(nonpassing, task.Contract.ID)
		}
		if task.Contract.Stage == 7 && task.Status == "accepted" {
			for _, scope := range task.Contract.ScopeIDs {
				reports[scope] = true
			}
		}
	}
	if !e2eSameJSON(acceptances, closeout.Acceptances) || !e2eSameJSON(unaccepted, closeout.UnacceptedTaskIDs) || !e2eSameJSON(nonpassing, closeout.NonpassingTaskIDs) {
		return fmt.Errorf("E2E closeout omitted or changed a task acceptance")
	}
	if state.Status == "complete" || state.Status == "planning-complete" {
		if len(unaccepted) != 0 || len(nonpassing) != 0 || closeout.Outcome != "pass" || (state.Mode == "execution") != (state.Status == "complete") {
			return fmt.Errorf("E2E passing completion lacks full accepted scope or has the wrong planning/execution claim")
		}
	} else {
		if closeout.Outcome != "failed" && closeout.Outcome != "blocked" {
			return fmt.Errorf("E2E unresolved report cannot claim passing completion")
		}
		if (len(unaccepted) > 0) != (state.Status == "blocked") {
			return fmt.Errorf("unaccepted mandatory work cannot be labeled terminal reported")
		}
		for _, scope := range state.Scope {
			if !reports[scope.ID] {
				return fmt.Errorf("closeout lacks an independently accepted report for scope %s", scope.ID)
			}
		}
	}
	return nil
}

func (service *e2eService) input(args []string, flag string, output any) error {
	value := optionValue(args, flag, "")
	if strings.TrimSpace(value) == "" {
		return fmt.Errorf("%s is required", flag)
	}
	raw, err := resolveAgentJSONInputBytes(value, service.projectRoot, "e2e "+flag)
	if err != nil {
		return err
	}
	return e2eDecode(raw, output)
}

func e2eDecode(raw []byte, output any) error {
	if err := e2eRejectDuplicateJSONKeys(raw); err != nil {
		return err
	}
	decoder := json.NewDecoder(bytes.NewReader(raw))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(output); err != nil {
		return err
	}
	var trailing any
	if err := decoder.Decode(&trailing); err != io.EOF {
		return fmt.Errorf("input must contain exactly one JSON object")
	}
	return nil
}

func e2eRejectDuplicateJSONKeys(raw []byte) error {
	decoder := json.NewDecoder(bytes.NewReader(raw))
	decoder.UseNumber()
	var value func() error
	value = func() error {
		token, err := decoder.Token()
		if err != nil {
			return err
		}
		delimiter, composite := token.(json.Delim)
		if !composite {
			return nil
		}
		switch delimiter {
		case '{':
			seen := map[string]bool{}
			for decoder.More() {
				token, err := decoder.Token()
				if err != nil {
					return err
				}
				key, ok := token.(string)
				if !ok || seen[key] {
					return fmt.Errorf("duplicate or invalid JSON object key %q", key)
				}
				seen[key] = true
				if err := value(); err != nil {
					return err
				}
			}
		case '[':
			for decoder.More() {
				if err := value(); err != nil {
					return err
				}
			}
		default:
			return fmt.Errorf("invalid JSON delimiter")
		}
		_, err = decoder.Token()
		return err
	}
	if err := value(); err != nil {
		return err
	}
	if _, err := decoder.Token(); err != io.EOF {
		return fmt.Errorf("input must contain exactly one JSON value")
	}
	return nil
}

func (service *e2eService) readFile(ref string) ([]byte, error) {
	path, err := secureProjectPath(service.projectRoot, ref)
	if err != nil {
		return nil, err
	}
	info, err := os.Lstat(path)
	if err != nil || !info.Mode().IsRegular() {
		if err == nil {
			err = fmt.Errorf("evidence/input must be a regular file: %s", ref)
		}
		return nil, err
	}
	raw, err := os.ReadFile(path)
	if err == nil {
		service.observed[ref] = fileContentSHA256(raw)
	}
	return raw, err
}

func (service *e2eService) bindFiles(refs []string) ([]e2eBinding, error) {
	if !e2eUniqueNonEmpty(refs) {
		return nil, fmt.Errorf("file references must be unique nonempty paths")
	}
	bindings := []e2eBinding{}
	for _, ref := range refs {
		if err := e2eAssetRef(ref); err != nil {
			return nil, err
		}
		raw, err := service.readFile(ref)
		if err != nil {
			return nil, fmt.Errorf("%s: %w", ref, err)
		}
		digest := fileContentSHA256(raw)
		archiveRef := service.rootRef + "/blobs/" + digest + ".bin"
		if service.pendingBlobs == nil {
			service.pendingBlobs = map[string][]byte{}
		}
		service.pendingBlobs[archiveRef] = append([]byte(nil), raw...)
		bindings = append(bindings, e2eBinding{Path: ref, SHA256: digest, ArchiveRef: archiveRef})
	}
	return bindings, nil
}

func (service *e2eService) verifyBindings(bindings []e2eBinding, refs []string) error {
	if len(bindings) != len(refs) {
		return fmt.Errorf("frozen file denominator changed")
	}
	expected := map[string]bool{}
	for _, ref := range refs {
		expected[ref] = true
	}
	for _, binding := range bindings {
		if !expected[binding.Path] {
			return fmt.Errorf("unknown or duplicate bound path %s", binding.Path)
		}
		delete(expected, binding.Path)
		if err := e2eAssetRef(binding.Path); err != nil {
			return err
		}
		raw, err := service.readFile(binding.Path)
		if err != nil {
			return err
		}
		if fileContentSHA256(raw) != binding.SHA256 {
			return fmt.Errorf("bound bytes changed: %s", binding.Path)
		}
		if err := service.verifyBlob(binding.ArchiveRef, binding.SHA256); err != nil {
			return err
		}
	}
	return nil
}

func (service *e2eService) snapshot(value any) (e2eRef, []byte, error) {
	raw, err := json.MarshalIndent(value, "", "  ")
	if err != nil {
		return e2eRef{}, nil, err
	}
	raw = append(raw, '\n')
	digest := fileContentSHA256(raw)
	return e2eRef{Ref: service.rootRef + "/snapshots/" + digest + ".json", SHA256: digest}, raw, nil
}

func (service *e2eService) readSnapshot(ref e2eRef, output any) error {
	if !regexp.MustCompile(`^[0-9a-f]{64}$`).MatchString(ref.SHA256) || ref.Ref != service.rootRef+"/snapshots/"+ref.SHA256+".json" {
		return fmt.Errorf("invalid immutable snapshot reference")
	}
	raw, err := service.readFile(ref.Ref)
	if err != nil {
		return err
	}
	if fileContentSHA256(raw) != ref.SHA256 {
		return fmt.Errorf("immutable snapshot bytes changed: %s", ref.Ref)
	}
	if err := e2eDecode(raw, output); err != nil {
		return err
	}
	return service.verifyArchivedBindings(raw)
}

func (service *e2eService) verifyBlob(ref, digest string) error {
	if !regexp.MustCompile(`^[0-9a-f]{64}$`).MatchString(digest) || ref != service.rootRef+"/blobs/"+digest+".bin" {
		return fmt.Errorf("invalid immutable raw artifact binding")
	}
	raw, err := service.readFile(ref)
	if err != nil {
		return fmt.Errorf("immutable raw artifact unavailable: %w", err)
	}
	if fileContentSHA256(raw) != digest {
		return fmt.Errorf("immutable raw artifact bytes changed: %s", ref)
	}
	return nil
}

func (service *e2eService) verifyArchivedBindings(raw []byte) error {
	// Only the runtime's typed binding fields own archived artifacts. Raw and
	// normalized WorkerTaskResult metadata remains opaque, including coincidentally
	// named archive_ref/sha256 fields from native runners or external tools.
	var header struct {
		SchemaVersion string `json:"schema_version"`
	}
	if err := json.Unmarshal(raw, &header); err != nil {
		return err
	}
	bindings := []e2eBinding{}
	switch header.SchemaVersion {
	case "e2e-worker-packet-v1":
		var packet e2ePacket
		if err := e2eDecode(raw, &packet); err != nil {
			return err
		}
		var contract e2eTaskContract
		if err := service.readSnapshot(packet.ContractRef, &contract); err != nil {
			return fmt.Errorf("original task contract unavailable: %w", err)
		}
		if contract.SchemaVersion != "e2e-task-contract-v1" || contract.RunID != packet.RunID || contract.TaskID != packet.TaskID || contract.ContractSHA256 != packet.ContractSHA256 || !e2eSameJSON(contract.Contract, packet.Contract) || !e2eSameJSON(contract.Scope, packet.Scope) || contract.ContractSHA256 != e2eContractDigest(&e2eState{Mode: contract.Mode, Scope: contract.Scope}, contract.Contract) {
			return fmt.Errorf("original task contract does not match its worker packet")
		}
		bindings = append(bindings, packet.Inputs...)
		for _, dependency := range packet.Dependencies {
			bindings = append(bindings, dependency.Outputs...)
		}
	case "e2e-worker-result-v1":
		var submission e2eSubmission
		if err := e2eDecode(raw, &submission); err != nil {
			return err
		}
		bindings = append(bindings, submission.Outputs...)
		bindings = append(bindings, submission.Evidence...)
	case "e2e-independent-review-v1":
		var review e2eReview
		if err := e2eDecode(raw, &review); err != nil {
			return err
		}
		bindings = append(bindings, review.Evidence...)
	case "e2e-reopen-v1", "e2e-scope-expansion-v1":
		// Events are append-only records with one explicitly owned binding field.
		var event struct {
			Evidence []e2eBinding `json:"evidence"`
		}
		if err := json.Unmarshal(raw, &event); err != nil {
			return err
		}
		bindings = append(bindings, event.Evidence...)
	case "e2e-task-contract-v1", "e2e-review-packet-v1", "e2e-acceptance-v1", "e2e-closeout-v1":
		// These schemas own no raw artifact bindings.
	default:
		return fmt.Errorf("unknown immutable E2E snapshot schema %q", header.SchemaVersion)
	}
	for _, binding := range bindings {
		if err := service.verifyBlob(binding.ArchiveRef, binding.SHA256); err != nil {
			return err
		}
	}
	return nil
}

func (service *e2eService) persist(state *e2eState, kind string, snapshots map[string][]byte) error {
	files := map[string][]byte{}
	for ref, raw := range snapshots {
		files[ref] = raw
	}
	for ref, raw := range service.pendingBlobs {
		files[ref] = raw
	}
	stateRaw, err := json.MarshalIndent(state, "", "  ")
	if err != nil {
		return err
	}
	stateRaw = append(stateRaw, '\n')
	statePath, err := secureProjectPath(service.projectRoot, service.rootRef+"/state.json")
	if err != nil {
		return err
	}
	updates := []fileTransactionUpdate{{Path: statePath, Content: stateRaw}}
	preconditions := []fileTransactionPrecondition{}
	for ref, digest := range service.observed {
		path, err := secureProjectPath(service.projectRoot, ref)
		if err != nil {
			return err
		}
		preconditions = append(preconditions, fileTransactionPrecondition{Path: path, ExpectedSHA256: digest})
	}
	if _, ok := service.observed[service.rootRef+"/state.json"]; !ok {
		preconditions = append(preconditions, fileTransactionPrecondition{Path: statePath, MustNotExist: true})
	}
	for ref, raw := range files {
		path, err := secureProjectPath(service.projectRoot, ref)
		if err != nil {
			return err
		}
		if existing, err := os.ReadFile(path); err == nil {
			if !bytes.Equal(existing, raw) {
				return fmt.Errorf("immutable snapshot collision: %s", ref)
			}
			if _, ok := service.observed[ref]; !ok {
				preconditions = append(preconditions, fileTransactionPrecondition{Path: path, ExpectedSHA256: fileContentSHA256(raw)})
			}
			continue
		} else if !os.IsNotExist(err) {
			return err
		}
		preconditions = append(preconditions, fileTransactionPrecondition{Path: path, MustNotExist: true})
		updates = append(updates, fileTransactionUpdate{Path: path, Content: raw, Perm: 0o444})
	}
	if service.beforeCommit != nil {
		if err := service.beforeCommit(); err != nil {
			return err
		}
	}
	_, err = applyFileTransactionWithPreconditions(service.projectRoot, "e2e."+kind, updates, preconditions)
	return err
}

func (service *e2eService) envelope(status, summary string, state *e2eState) Envelope {
	env := NewEnvelope(status, summary)
	tasks := []any{}
	for _, task := range state.Tasks {
		tasks = append(tasks, map[string]any{"id": task.Contract.ID, "stage": task.Contract.Stage, "scope_ids": task.Contract.ScopeIDs, "status": task.Status, "outcome": task.Outcome, "attempt": task.Attempt, "worker_id": task.WorkerID, "validator_id": task.ValidatorID, "depends_on": e2eDependencies(state, task.Contract), "packet": task.Packet, "submission": task.Submission, "review": task.Review, "acceptance": task.Acceptance, "history_count": len(task.History), "reopen_reason": task.ReopenReason})
	}
	env.Data = map[string]any{"schema_version": state.SchemaVersion, "run_id": state.RunID, "revision": state.Revision, "mode": state.Mode, "status": state.Status, "product_pass": state.Status == "complete", "scope": state.Scope, "tasks": tasks, "state_ref": service.rootRef + "/state.json"}
	env.ShowArgv = []string{"specify-runtime", "e2e", "status", "--run-id", state.RunID, "--project-root", service.projectRoot, "--format", "json"}
	if state.Status != "active" {
		if state.Status == "blocked" || state.Status == "reported" {
			earliest := -1
			for index, task := range state.Tasks {
				if task.Status == "not_requested" || (task.Status == "accepted" && task.Outcome == "pass") {
					continue
				}
				if earliest < 0 || task.Contract.Stage < state.Tasks[earliest].Contract.Stage {
					earliest = index
				}
			}
			if earliest >= 0 {
				env.NextArgv = service.argv(state, "reopen", "--task-id", state.Tasks[earliest].Contract.ID, "--leader-id", state.LeaderID, "--reason", "<recovery-reason>", "--evidence-ref", "<recovery-evidence-path>")
			}
		}
		return env
	}
	for _, task := range state.Tasks {
		switch task.Status {
		case "running":
			env.NextArgv = service.argv(state, "task-submit", "--task-id", task.Contract.ID, "--worker-id", task.WorkerID, "--result-json", "<semantic-json|@path|->")
			return env
		case "submitted":
			env.NextArgv = service.argv(state, "review-start", "--task-id", task.Contract.ID, "--validator-id", "<independent-agent-id>")
			return env
		case "reviewing":
			env.NextArgv = service.argv(state, "review-submit", "--task-id", task.Contract.ID, "--validator-id", task.ValidatorID, "--result-json", "<semantic-json|@path|->")
			return env
		case "verified":
			env.NextArgv = service.argv(state, "task-accept", "--task-id", task.Contract.ID, "--leader-id", state.LeaderID)
			return env
		case "rejected":
			env.NextArgv = service.argv(state, "reopen", "--task-id", task.Contract.ID, "--leader-id", state.LeaderID, "--reason", "<causal-repair-reason>", "--evidence-ref", "<reproduction-evidence-path>")
			return env
		case "pending":
			ready := true
			for _, dep := range e2eDependencies(state, task.Contract) {
				index, _ := e2eTaskIndex(state, dep.TaskID)
				producer := state.Tasks[index]
				if producer.Status != "accepted" || (dep.Require == "passed" && producer.Outcome != "pass") {
					ready = false
				}
			}
			if ready {
				env.NextArgv = service.argv(state, "task-start", "--task-id", task.Contract.ID, "--worker-id", "<native-worker-id>")
				return env
			}
		}
	}
	for _, task := range state.Tasks {
		if task.Status == "pending" && task.Contract.Stage >= 6 {
			env.NextArgv = service.argv(state, "task-start", "--task-id", task.Contract.ID, "--worker-id", "<independent-audit-worker-id>", "--diagnostic")
			return env
		}
	}
	env.NextArgv = service.argv(state, "close", "--leader-id", state.LeaderID, "--outcome", "<pass|failed|blocked>")
	return env
}

func (service *e2eService) failureWithState(status, summary string, state *e2eState, err error) Envelope {
	env := service.envelope(status, summary, state)
	if err != nil {
		env.Blockers = append(env.Blockers, err.Error())
	}
	return env
}

func e2eFailure(status, summary string, err error) Envelope {
	env := NewEnvelope(status, summary)
	if err != nil {
		env.Blockers = append(env.Blockers, err.Error())
	}
	return env
}

func (service *e2eService) argv(state *e2eState, action string, extra ...string) []string {
	args := []string{"specify-runtime", "e2e", action, "--run-id", state.RunID, "--project-root", service.projectRoot, "--expected-revision", strconv.Itoa(state.Revision), "--format", "json"}
	return append(args, extra...)
}

func e2eSubmissionTemplate(packet e2ePacket, ref e2eRef) map[string]any {
	return map[string]any{"packet_sha256": ref.SHA256, "outcome": "<pass|failed|blocked>", "worker_result": map[string]any{"task_id": packet.TaskID, "packet_id": ref.SHA256, "status": "pending", "summary": "<actual worker result>", "validation_results": []any{}}, "checks": e2eCheckTemplate(packet.Contract, false)}
}

// The enclosing E2E packet owns attempt/target/digest bindings. This nested view
// is the existing WorkerTaskPacket contract consumed by native dispatchers;
// feature/story IDs remain empty for project-wide E2E instead of inventing a
// formal feature workflow. The result binds the enclosing packet's SHA256.
func e2eWorkerPacketView(packet e2ePacket) map[string]any {
	reads := append([]string{packet.ContractRef.Ref}, packet.Contract.Inputs...)
	for _, binding := range packet.Inputs {
		reads = append(reads, binding.ArchiveRef)
	}
	for _, dependency := range packet.Dependencies {
		reads = append(reads, dependency.Acceptance.Ref)
		for _, binding := range dependency.Outputs {
			reads = append(reads, binding.Path, binding.ArchiveRef)
		}
	}
	for _, diagnostic := range packet.DiagnosticInputs {
		if diagnostic.Submission.Ref != "" {
			reads = append(reads, diagnostic.Submission.Ref)
		}
		if diagnostic.Review.Ref != "" {
			reads = append(reads, diagnostic.Review.Ref)
		}
	}
	return e2eStandardWorkerPacket(packet.RunID, packet.TaskID, packet.Contract, reads, packet.Contract.Outputs, false)
}

func e2eReviewWorkerPacketView(packet e2eReviewPacket, submission e2eSubmission) map[string]any {
	reads := []string{packet.Packet.Ref, packet.Submission.Ref}
	for _, binding := range append(append([]e2eBinding{}, submission.Outputs...), submission.Evidence...) {
		reads = append(reads, binding.Path, binding.ArchiveRef)
	}
	return e2eStandardWorkerPacket(packet.RunID, packet.TaskID, packet.Contract, reads, []string{}, true)
}

func e2eStandardWorkerPacket(runID, taskID string, contract e2eTaskSpec, readPaths, writePaths []string, review bool) map[string]any {
	seen := map[string]bool{}
	reads := []string{}
	for _, ref := range readPaths {
		if ref != "" && !seen[ref] {
			reads = append(reads, ref)
			seen[ref] = true
		}
	}
	sort.Strings(reads)
	references, context := []any{}, []any{}
	for index, ref := range reads {
		references = append(references, map[string]any{"path": ref, "reason": "Read the exact original task contract, task input, accepted handoff, or immutable raw evidence bound by the enclosing E2E packet"})
		context = append(context, map[string]any{"path": ref, "kind": "task_reference", "purpose": "Bound E2E task contract/input/evidence", "required_for": []string{taskID}, "read_order": index + 1, "must_read": true})
	}
	criteria := []string{}
	for _, scope := range contract.ScopeIDs {
		for _, criterion := range contract.Acceptance {
			criteria = append(criteria, scope+"/"+criterion.ID+": "+criterion.Criterion)
		}
	}
	role := "execution-worker"
	objective := fmt.Sprintf("E2E run %s task %s, stage %d: produce every assigned output and account for the full frozen scope/acceptance set", runID, taskID, contract.Stage)
	rules := []string{"Consume the enclosing E2E packet's exact target, attempt, source hashes and accepted dependency receipts before work", "Own only declared test assets and disposable authorized fixtures; preserve product and formal Review/Accept ownership", "Record expected/actual outcomes, preconditions, replay steps and raw evidence for every assigned acceptance row", "A worker result is a submission; only an independent review followed by the leader's runtime acceptance unlocks consumers", "Never write E2E runtime state, snapshots or archived blobs directly"}
	handoff := []string{"Return the existing WorkerTaskResult inline with this task_id and packet_id equal to the enclosing E2E packet SHA256", "Return all scope/acceptance check rows for e2e task-submit; raw evidence remains available for immutable archival", "Report failed, blocked, skipped and unavailable work explicitly; never turn a diagnostic report into a passing execution claim"}
	if review {
		role = "independent-validator"
		objective = fmt.Sprintf("Independently validate E2E run %s task %s against its original contract, complete scope and exact submitted outputs", runID, taskID)
		rules = append(rules, "Do not modify the reviewed product, test, output, or source files; an author cannot validate that revision", "Inspect original archived evidence and replay decisive checks using authorized isolated fixtures; identify every unmet scope/acceptance row")
		handoff = []string{"Return every independent review row inline for e2e review-submit", "Bind review_packet_sha256 and submission_sha256 from the enclosing review request; distinguish inspected from replayed checks", "Reject incomplete or contradictory results and name every required repair; independent verification is not leader acceptance"}
	}
	return map[string]any{
		"feature_id": "", "story_id": "", "task_id": taskID, "objective": objective, "packet_version": 2, "agent_role": role,
		"intent": map[string]any{"outcome": objective, "constraints": rules, "success_signals": criteria},
		"scope":  map[string]any{"read_scope": reads, "write_scope": writePaths}, "interfaces": map[string]any{"consumes": reads, "produces": writePaths},
		"context_bundle": context, "required_references": references, "hard_rules": rules, "forbidden_drift": []string{"Do not remove requested target/operation IDs or acceptance criteria", "Do not reuse stale or rejected acceptance receipts", "Do not weaken assertions, modify product behavior, or write runtime-owned files"},
		"validation_gates": []string{"Every assigned scope/acceptance row has inspectable raw evidence and a reproducible expected/actual check", "All consumed source/output bindings still match the enclosing packet"},
		"done_criteria":    criteria, "acceptance_criteria": criteria, "handoff_requirements": handoff, "platform_guardrails": []string{"Use the exact target/build/environment recorded by the enclosing E2E packet; one platform cannot certify another"},
		"dispatch_policy": map[string]any{"mode": "hard_fail", "must_acknowledge_rules": true}, "validation_policy": map[string]any{"mode": "task", "budget_scope": "task", "heavy_gate_owner": "worker"},
	}
}

// Preserve reported validation before compatibility normalization can discard
// malformed rows, disagreeing aliases, or nonzero native runner exit codes.
// The raw input remains beside the normalized WorkerTaskResult in the snapshot.
func normalizeE2EWorkerResult(raw []byte, outcome string) (map[string]any, error) {
	if err := validateQuickResultValidationInput(raw); err != nil {
		return nil, fmt.Errorf("E2E worker validation must be lossless: %w", err)
	}
	var input map[string]any
	if err := json.Unmarshal(raw, &input); err != nil || input == nil {
		return nil, fmt.Errorf("WorkerTaskResult must be an object")
	}
	for _, fields := range [][2]string{{"task_id", "taskId"}, {"packet_id", "packetId"}} {
		if err := validateQuickCheckAliases(input, fields[0], fields[1], false); err != nil {
			return nil, fmt.Errorf("E2E worker identity aliases: %w", err)
		}
	}
	status := ""
	for _, field := range []string{"status", "reported_status", "result_status"} {
		value, present := input[field]
		if !present {
			continue
		}
		text, ok := value.(string)
		if !ok || strings.TrimSpace(text) == "" {
			return nil, fmt.Errorf("WorkerTaskResult %s must be a nonempty status", field)
		}
		normalized := resultStatusAliases[strings.ToLower(strings.TrimSpace(text))]
		if normalized == "" {
			normalized = "failed"
		}
		if status != "" && status != normalized {
			return nil, fmt.Errorf("WorkerTaskResult status aliases conflict")
		}
		status = normalized
	}
	checkExit := func(row map[string]any) (any, error) {
		var previous *int
		for _, field := range []string{"exit_code", "exitCode", "returncode", "return_code"} {
			value, present := row[field]
			if !present {
				continue
			}
			code, ok := hookJSONInteger(value)
			if !ok {
				return nil, fmt.Errorf("worker validation %s must be an integer", field)
			}
			if previous != nil && *previous != code {
				return nil, fmt.Errorf("worker validation exit-code aliases conflict")
			}
			current := code
			previous = &current
			if outcome == "pass" && code != 0 {
				return nil, fmt.Errorf("passing E2E outcome cannot consume runner exit code %d", code)
			}
		}
		if previous == nil {
			return nil, nil
		}
		return *previous, nil
	}
	if _, err := checkExit(input); err != nil {
		return nil, err
	}
	var previous []any
	seen := false
	for _, field := range []string{"validation_results", "validationResults"} {
		value, present := input[field]
		if !present {
			continue
		}
		rows, _ := value.([]any)
		signature := []any{}
		for _, rawRow := range rows {
			row := rawRow.(map[string]any)
			exit, err := checkExit(row)
			if err != nil {
				return nil, err
			}
			normalized := normalizeValidationResults(map[string]any{"validation_results": []any{row}})[0]
			signature = append(signature, map[string]any{"validation": normalized, "exit_code": exit})
		}
		if seen && !e2eSameJSON(previous, signature) {
			return nil, fmt.Errorf("validation result aliases disagree after preserving exit-code evidence")
		}
		previous, seen = signature, true
	}
	normalized, err := normalizeWorkerTaskResult(raw)
	if err != nil {
		return nil, err
	}
	if outcome == "pass" {
		for _, row := range normalized["validation_results"].([]map[string]string) {
			if row["status"] != "passed" {
				return nil, fmt.Errorf("passing E2E outcome includes nonpassing worker validation: %s", row["command"])
			}
		}
	}
	return normalized, nil
}

func e2eCheckTemplate(task e2eTaskSpec, review bool) []any {
	rows := []any{}
	for _, scope := range task.ScopeIDs {
		for _, criterion := range task.Acceptance {
			row := map[string]any{"scope_id": scope, "acceptance_id": criterion.ID, "status": "<passed|failed|blocked|skipped|not_run>", "expected": criterion.Criterion, "actual": "", "reproduction": "", "preconditions": "", "evidence_refs": []string{}}
			if review {
				row["status"], row["method"] = "<passed|failed>", "<inspected|replayed>"
			}
			rows = append(rows, row)
		}
	}
	return rows
}

func e2eContractDigest(state *e2eState, task e2eTaskSpec) string {
	raw, _ := json.Marshal(map[string]any{"contract": task, "scope": e2eScopeForTask(state, task), "mode": state.Mode})
	return fileContentSHA256(raw)
}

func e2eSameJSON(left, right any) bool {
	a, err := json.Marshal(left)
	if err != nil {
		return false
	}
	b, err := json.Marshal(right)
	return err == nil && bytes.Equal(a, b)
}
func e2eScopeForTask(state *e2eState, task e2eTaskSpec) []e2eScope {
	result := []e2eScope{}
	for _, scope := range state.Scope {
		if e2eContains(task.ScopeIDs, scope.ID) {
			result = append(result, scope)
		}
	}
	return result
}
func e2eTaskIndex(state *e2eState, id string) (int, error) {
	for index, task := range state.Tasks {
		if task.Contract.ID == id {
			return index, nil
		}
	}
	return -1, fmt.Errorf("unknown task %q", id)
}
func e2eIdentity(value string) bool {
	return strings.TrimSpace(value) != "" && strings.TrimSpace(value) == value && len(value) <= 256 && !strings.ContainsAny(value, "\r\n\x00")
}
func e2eContains(values []string, value string) bool {
	for _, candidate := range values {
		if candidate == value {
			return true
		}
	}
	return false
}
func e2eOverlap(a, b []string) bool {
	for _, value := range a {
		if e2eContains(b, value) {
			return true
		}
	}
	return false
}
func e2eUniqueNonEmpty(values []string) bool {
	seen := map[string]bool{}
	for _, value := range values {
		if value == "" || strings.TrimSpace(value) != value || seen[value] {
			return false
		}
		seen[value] = true
	}
	return true
}
func e2eRefIn(values []e2eRef, value e2eRef) bool {
	for _, candidate := range values {
		if candidate == value {
			return true
		}
	}
	return false
}
func e2ePathsOverlap(a, b []string) bool {
	for _, left := range a {
		left = e2eFilePathKey(left)
		for _, right := range b {
			right = e2eFilePathKey(right)
			if left == right || strings.HasPrefix(left, right+"/") || strings.HasPrefix(right, left+"/") {
				return true
			}
		}
	}
	return false
}
func e2eAssetRef(ref string) error {
	if runtime.GOOS == "windows" {
		// Ordinary project-file references cannot name NTFS streams or Win32
		// aliases that trim trailing dots/spaces from a path component.
		for _, component := range strings.Split(ref, "/") {
			if strings.Contains(component, ":") || strings.HasSuffix(component, ".") || strings.HasSuffix(component, " ") {
				return fmt.Errorf("asset reference must be a canonical Windows project file: %s", ref)
			}
		}
	}
	key := e2eFilePathKey(ref)
	if ref == "" || filepath.IsAbs(ref) || strings.Contains(ref, "\\") || filepath.ToSlash(filepath.Clean(filepath.FromSlash(ref))) != ref || ref == "." || ref == ".." || strings.HasPrefix(ref, "../") || key == ".git" || strings.HasPrefix(key, ".git/") || e2eRuntimeOwnedPath(ref) {
		return fmt.Errorf("asset reference must be a canonical project-contained file outside runtime state: %s", ref)
	}
	return nil
}
