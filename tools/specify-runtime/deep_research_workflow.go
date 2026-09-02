package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/url"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"time"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/filelock"
)

const (
	deepResearchStateSchema       = "spec-kit-deep-research-state-v1"
	deepResearchManifestSchema    = "spec-kit-deep-research-track-manifest-v1"
	deepResearchTrackProtocol     = "deep_research_track_result.v1"
	deepResearchEvidenceSchema    = "spec-kit-research-evidence-v1"
	deepResearchRejectionSchema   = "spec-kit-deep-research-track-rejection-v1"
	deepResearchSynthesisSchema   = "spec-kit-deep-research-synthesis-v1"
	deepResearchAuditRequestV1    = "spec-kit-deep-research-audit-request-v1"
	deepResearchAuditV1           = "spec-kit-deep-research-audit-v1"
	deepResearchHandoffV1         = "spec-kit-deep-research-handoff-v1"
	deepResearchStateFilename     = "state.json"
	deepResearchManifestFilename  = "track-manifest.json"
	deepResearchSynthesisFilename = "synthesis.json"
	deepResearchAuditRequestFile  = "audit-request.json"
	deepResearchAuditFilename     = "audit.json"
	deepResearchHandoffFilename   = "handoff-to-plan.json"
)

var (
	deepResearchTrackIDPattern       = regexp.MustCompile(`^TRK-[0-9]{3,}$`)
	deepResearchAttemptIDPattern     = regexp.MustCompile(`^ATTEMPT-[0-9]{3,}$`)
	deepResearchCapabilityPattern    = regexp.MustCompile(`^CAP-[0-9]{3,}$`)
	deepResearchFindingPattern       = regexp.MustCompile(`^FND-[0-9]{3,}$`)
	deepResearchEvidencePattern      = regexp.MustCompile(`^EVD-[0-9]{3,}$`)
	deepResearchSpikePattern         = regexp.MustCompile(`^SPK-[0-9]{3,}$`)
	deepResearchContradictionPattern = regexp.MustCompile(`^CON-[0-9]{3,}$`)
	deepResearchHandoffPattern       = regexp.MustCompile(`^PH-[0-9]{3,}$`)
	deepResearchWorkerPattern        = regexp.MustCompile(`^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$`)
	deepResearchSHA256Pattern        = regexp.MustCompile(`^[0-9a-f]{64}$`)
)

var deepResearchAuditCheckIDs = []string{
	"capability_closure",
	"evidence_integrity",
	"source_quality",
	"contradictions",
	"spikes",
	"planning_handoff",
}

type deepResearchService struct {
	projectRoot               string
	beforeSourceBoundMutation func() error
}

type deepResearchState struct {
	SchemaVersion string                    `json:"schema_version"`
	Revision      int                       `json:"revision"`
	FeatureDir    string                    `json:"feature_dir"`
	ArtifactRoot  string                    `json:"artifact_root"`
	Mode          string                    `json:"mode"`
	Status        string                    `json:"status"`
	Phase         string                    `json:"phase"`
	ClaimStatus   string                    `json:"claim_status"`
	Source        deepResearchSource        `json:"source"`
	ManifestRef   string                    `json:"manifest_ref"`
	AcceptedRefs  []string                  `json:"accepted_track_result_refs"`
	Synthesis     deepResearchArtifactState `json:"synthesis"`
	Audit         deepResearchAuditState    `json:"audit"`
	Publication   deepResearchArtifactState `json:"publication"`
	Blockers      []any                     `json:"blockers"`
}

type deepResearchSource struct {
	SpecRef        string   `json:"spec_ref"`
	SpecSHA256     string   `json:"spec_sha256"`
	CapabilityRefs []string `json:"capability_refs"`
	ReasonRefs     []string `json:"reason_refs"`
}

type deepResearchArtifactState struct {
	Ref    *string `json:"ref"`
	SHA256 *string `json:"sha256"`
}

type deepResearchAuditState struct {
	Required      bool    `json:"required"`
	Status        string  `json:"status"`
	RequestRef    *string `json:"request_ref"`
	RequestSHA256 *string `json:"request_sha256"`
	ResultRef     *string `json:"result_ref"`
	ResultSHA256  *string `json:"result_sha256"`
}

type deepResearchTrackManifest struct {
	SchemaVersion string              `json:"schema_version"`
	GenerationID  string              `json:"generation_id"`
	Status        string              `json:"status"`
	LeaderID      string              `json:"leader_id"`
	Tracks        []deepResearchTrack `json:"tracks"`
}

type deepResearchTrack struct {
	TrackID          string                       `json:"track_id"`
	Title            string                       `json:"title"`
	State            string                       `json:"state"`
	CapabilityRefs   []string                     `json:"capability_refs"`
	ReadPaths        []string                     `json:"read_paths"`
	Questions        []string                     `json:"questions"`
	SourceClasses    []string                     `json:"source_classes"`
	RequiresSpike    bool                         `json:"requires_spike"`
	CompletionSignal string                       `json:"completion_signal"`
	WorkerID         string                       `json:"worker_id,omitempty"`
	AttemptID        string                       `json:"attempt_id,omitempty"`
	AttemptNumber    int                          `json:"attempt_number"`
	ResultRef        string                       `json:"result_ref,omitempty"`
	ResultSHA256     string                       `json:"result_sha256,omitempty"`
	LastYieldReason  string                       `json:"last_yield_reason,omitempty"`
	Rejections       []deepResearchTrackRejection `json:"rejections"`
}

type deepResearchTrackRejection struct {
	AttemptID       string `json:"attempt_id"`
	WorkerID        string `json:"worker_id"`
	ResultRef       string `json:"result_ref"`
	ResultSHA256    string `json:"result_sha256"`
	RejectionRef    string `json:"rejection_ref"`
	RejectionSHA256 string `json:"rejection_sha256"`
	Reason          string `json:"reason"`
}

type deepResearchFeasibilityGate struct {
	SpecStatus     string
	Decision       string
	CapabilityRefs []string
	ReasonRefs     []string
}

type deepResearchSourceReadinessError struct {
	Code                string
	FeatureRef          string
	SpecStatus          string
	WorkflowStage       string
	WorkflowStatus      string
	OwnerWorkflow       string
	Owner               string
	HumanActionRequired bool
	ResolutionAction    any
	Details             []any
	Message             string
}

func (err *deepResearchSourceReadinessError) Error() string {
	if err == nil || strings.TrimSpace(err.Message) == "" {
		return "deep-research source cannot produce an executable Plan handoff"
	}
	return err.Message
}

type deepResearchPublishedBinding struct {
	HandoffRef      string
	HandoffSHA256   string
	SourceSpecSHA   string
	StateRevision   int
	ClaimStatus     string
	HandoffIDs      []string
	CapabilityRefs  []string
	ArtifactDigests map[string]string
}

func runDeepResearch(args []string, stdout io.Writer) int {
	if len(args) == 0 {
		return writeEnvelope(stdout, deepResearchFailure("usage-error", "missing deep-research subcommand", nil))
	}
	if args[0] == "--help" || args[0] == "-h" || args[0] == "help" {
		return writeDeepResearchHelp(stdout)
	}
	if deepResearchHelpRequested(args[1:]) {
		return writeDeepResearchSubcommandHelp(stdout, args[0])
	}
	if err := deepResearchValidateOptions(args); err != nil {
		return writeEnvelope(stdout, deepResearchFailure("usage-error", "deep-research command options are invalid", err))
	}
	service := deepResearchService{projectRoot: optionValue(args, "--project-root", ".")}
	var env Envelope
	switch args[0] {
	case "init":
		env = service.initialize(args[1:])
	case "status":
		env = service.status(args[1:])
	case "track-prepare":
		env = service.trackPrepare(args[1:])
	case "track-lease":
		env = service.trackLease(args[1:])
	case "track-submit":
		env = service.trackSubmit(args[1:])
	case "track-reject":
		env = service.trackReject(args[1:])
	case "track-accept":
		env = service.trackAccept(args[1:])
	case "track-yield":
		env = service.trackYield(args[1:])
	case "synthesize":
		env = service.synthesize(args[1:])
	case "audit-prepare":
		env = service.auditPrepare(args[1:])
	case "audit-accept":
		env = service.auditAccept(args[1:])
	case "validate":
		env = service.validate(args[1:])
	case "publish":
		env = service.publish(args[1:])
	case "verify-handoff":
		env = service.verifyHandoffCommand(args[1:])
	case "not-needed":
		env = service.notNeeded(args[1:])
	default:
		env = deepResearchFailure("usage-error", fmt.Sprintf("unknown deep-research subcommand %q", args[0]), nil)
	}
	return writeEnvelope(stdout, env)
}

func deepResearchHelpRequested(args []string) bool {
	for _, arg := range args {
		if arg == "--help" || arg == "-h" {
			return true
		}
	}
	return false
}

func writeDeepResearchSubcommandHelp(stdout io.Writer, subcommand string) int {
	_, _ = fmt.Fprintf(stdout, "Usage: specify-runtime deep-research %s [options]\n", subcommand)
	_, _ = fmt.Fprintf(stdout, "Discover the machine-readable contract with: specify-runtime api show deep-research.%s --format json\n", subcommand)
	return 0
}

func writeDeepResearchHelp(stdout io.Writer) int {
	_, _ = fmt.Fprintln(stdout, "Usage: specify-runtime deep-research <subcommand> [options]")
	_, _ = fmt.Fprintln(stdout, "Subcommands: init, status, track-prepare, track-lease, track-submit, track-reject, track-accept, track-yield, synthesize, audit-prepare, audit-accept, validate, publish, verify-handoff, not-needed")
	return 0
}

func deepResearchValidateOptions(args []string) error {
	if len(args) == 0 {
		return fmt.Errorf("missing deep-research subcommand")
	}
	common := []string{"--project-root", "--format"}
	perCommand := map[string][]string{
		"init":           {"--feature-dir", "--mode", "--leader-id", "--expected-revision"},
		"status":         {"--feature-dir"},
		"track-prepare":  {"--feature-dir", "--input-json", "--expected-revision"},
		"track-lease":    {"--feature-dir", "--worker-id", "--expected-revision"},
		"track-submit":   {"--feature-dir", "--track-id", "--attempt-id", "--result-json", "--expected-revision"},
		"track-reject":   {"--feature-dir", "--track-id", "--attempt-id", "--leader-id", "--reason", "--expected-revision"},
		"track-accept":   {"--feature-dir", "--track-id", "--attempt-id", "--leader-id", "--expected-revision"},
		"track-yield":    {"--feature-dir", "--track-id", "--attempt-id", "--reason", "--expected-revision"},
		"synthesize":     {"--feature-dir", "--leader-id", "--input-json", "--expected-revision"},
		"audit-prepare":  {"--feature-dir", "--expected-revision"},
		"audit-accept":   {"--feature-dir", "--auditor-id", "--input-json", "--expected-revision"},
		"validate":       {"--feature-dir", "--expected-revision"},
		"publish":        {"--feature-dir", "--expected-revision"},
		"verify-handoff": {"--feature-dir", "--handoff-ref", "--expected-sha256"},
		"not-needed":     {"--feature-dir", "--leader-id", "--input-json"},
	}
	commandOptions, known := perCommand[args[0]]
	if !known {
		return nil
	}
	allowed := map[string]bool{}
	for _, option := range append(common, commandOptions...) {
		allowed[option] = true
	}
	seen := map[string]bool{}
	for index := 1; index < len(args); index++ {
		name := args[index]
		if !strings.HasPrefix(name, "--") || !allowed[name] {
			return fmt.Errorf("unknown option %q", name)
		}
		if seen[name] {
			return fmt.Errorf("option %s was repeated", name)
		}
		seen[name] = true
		if index+1 >= len(args) || strings.HasPrefix(args[index+1], "--") {
			return fmt.Errorf("option %s requires a value", name)
		}
		if name == "--format" && strings.TrimSpace(args[index+1]) != "json" {
			return fmt.Errorf("--format must be json")
		}
		index++
	}
	return nil
}

func (service deepResearchService) initialize(args []string) Envelope {
	featurePath, featureRef, root, rootRef, err := service.resolveFeature(optionValue(args, "--feature-dir", ""))
	if err != nil {
		return deepResearchFailure("usage-error", "deep-research feature is invalid", err)
	}
	leaderID := strings.TrimSpace(optionValue(args, "--leader-id", ""))
	if !deepResearchWorkerPattern.MatchString(leaderID) {
		return deepResearchFailure("usage-error", "deep-research init requires a valid --leader-id", nil)
	}
	mode := strings.ToLower(strings.TrimSpace(optionValue(args, "--mode", "")))
	if !deepResearchContains([]string{"repo-only", "external-enabled", "external-blocked"}, mode) {
		return deepResearchFailure("usage-error", "deep-research init --mode must be repo-only, external-enabled, or external-blocked", nil)
	}
	gate, specRaw, err := deepResearchReadFeasibilityGate(filepath.Join(featurePath, "spec-contract.json"))
	if err != nil {
		return deepResearchFailure("blocked", "specification feasibility gate is unavailable", err)
	}
	if gate.Decision != "required" {
		return deepResearchFailure("blocked", "deep-research is not selected by the specification", fmt.Errorf("spec-contract.json feasibility_gate.decision is %s", gate.Decision))
	}
	if readinessErr := service.requirePlanningReadySource(featurePath, featureRef, gate); readinessErr != nil {
		return deepResearchFailure("blocked", "deep-research source is not ready for the research-to-Plan route", readinessErr)
	}
	specRef := filepath.ToSlash(filepath.Join(featureRef, "spec-contract.json"))
	state := deepResearchState{
		SchemaVersion: deepResearchStateSchema,
		Revision:      1,
		FeatureDir:    featureRef,
		ArtifactRoot:  rootRef,
		Mode:          mode,
		Status:        "active",
		Phase:         "scoped",
		ClaimStatus:   "pending",
		Source: deepResearchSource{
			SpecRef:        specRef,
			SpecSHA256:     deepResearchDigest(specRaw),
			CapabilityRefs: gate.CapabilityRefs,
			ReasonRefs:     gate.ReasonRefs,
		},
		ManifestRef:  filepath.ToSlash(filepath.Join(rootRef, deepResearchManifestFilename)),
		AcceptedRefs: []string{},
		Synthesis:    deepResearchArtifactState{},
		Audit: deepResearchAuditState{
			Required: true,
			Status:   "pending",
		},
		Publication: deepResearchArtifactState{},
		Blockers:    []any{},
	}
	manifest := deepResearchTrackManifest{
		SchemaVersion: deepResearchManifestSchema,
		GenerationID:  "drg-" + state.Source.SpecSHA256[:16],
		Status:        "idle",
		LeaderID:      leaderID,
		Tracks:        []deepResearchTrack{},
	}
	return service.withMutationLock(root, func() Envelope {
		statePath := filepath.Join(root, deepResearchStateFilename)
		if _, statErr := os.Lstat(statePath); statErr == nil {
			previous, readErr := deepResearchReadState(root)
			if readErr != nil {
				return deepResearchFailure("blocked", "existing deep-research state is invalid", readErr)
			}
			if !hasFlag(args, "--expected-revision") {
				return deepResearchFailure("blocked", "deep-research workspace already exists", fmt.Errorf("resume with deep-research status or reinitialize with the current --expected-revision"))
			}
			if revisionErr := deepResearchCheckExpectedRevision(args, previous, true); revisionErr != nil {
				return deepResearchFailure("blocked", "deep-research revision changed", revisionErr)
			}
			if previous.FeatureDir != featureRef || previous.ArtifactRoot != rootRef {
				return deepResearchFailure("blocked", "existing deep-research state belongs to another feature", nil)
			}
			state.Revision = previous.Revision + 1
		} else if !errors.Is(statErr, os.ErrNotExist) {
			return deepResearchFailure("error", "cannot inspect deep-research workspace", statErr)
		}
		updates, updateErr := deepResearchJSONUpdates(map[string]any{
			statePath: state,
			filepath.Join(root, deepResearchManifestFilename): manifest,
		})
		if updateErr != nil {
			return deepResearchFailure("error", "cannot render deep-research workspace", updateErr)
		}
		if transactionErr := service.applySourceBoundTransaction(featurePath, featureRef, state.Source.SpecSHA256, false, "deep-research.init", updates); transactionErr != nil {
			return deepResearchFailure("error", "cannot initialize deep-research workspace", transactionErr)
		}
		env := NewEnvelope("ok", "deep-research workspace initialized")
		env.Data = deepResearchStateData(state)
		env.NextArgv = service.commandArgv(state, "track-prepare")
		return env
	})
}

func (service deepResearchService) status(args []string) Envelope {
	_, _, root, _, err := service.resolveFeature(optionValue(args, "--feature-dir", ""))
	if err != nil {
		return deepResearchFailure("usage-error", "deep-research feature is invalid", err)
	}
	state, err := deepResearchReadState(root)
	if err != nil {
		return deepResearchFailure("blocked", "deep-research state is unavailable", err)
	}
	manifest, err := deepResearchReadManifest(root)
	if err != nil {
		return deepResearchFailure("blocked", "deep-research track manifest is unavailable", err)
	}
	env := NewEnvelope("ok", "deep-research status")
	env.Data = deepResearchStateData(state)
	env.Data["tracks"] = deepResearchTrackCounts(manifest)
	next := ""
	freshnessErr := service.requireFreshSpec(state)
	if state.Phase == "published" {
		freshnessErr = service.requireFreshSpecWithPlanState(state, true)
	}
	if freshnessErr != nil {
		env.Status = "blocked"
		env.Summary = "deep-research specification source is stale"
		env.Blockers = append(env.Blockers, freshnessErr.Error())
		env.Data["source_freshness"] = "stale"
		bindDeepResearchSourceReadiness(&env, freshnessErr)
	} else {
		env.Data["source_freshness"] = "current"
		next = deepResearchNextSubcommand(state, manifest)
	}
	env.Data["next_action"] = next
	if next != "" {
		env.NextArgv = service.commandArgv(state, next)
	}
	return env
}

func (service deepResearchService) trackPrepare(args []string) Envelope {
	_, _, root, _, err := service.resolveFeature(optionValue(args, "--feature-dir", ""))
	if err != nil {
		return deepResearchFailure("usage-error", "deep-research feature is invalid", err)
	}
	input, err := service.inputObject(args, "--input-json", "deep-research track-prepare")
	if err != nil {
		return deepResearchFailure("usage-error", "deep-research track input is invalid", err)
	}
	rawTracks, ok := input["tracks"].([]any)
	if !ok || len(rawTracks) == 0 {
		return deepResearchFailure("invalid", "deep-research track-prepare requires a non-empty tracks array", nil)
	}
	return service.withMutationLock(root, func() Envelope {
		state, readErr := deepResearchReadState(root)
		if readErr != nil {
			return deepResearchFailure("blocked", "deep-research state is unavailable", readErr)
		}
		if revisionErr := deepResearchCheckExpectedRevision(args, state, true); revisionErr != nil {
			return deepResearchFailure("blocked", "deep-research revision changed", revisionErr)
		}
		if state.Phase != "scoped" {
			return deepResearchFailure("blocked", "deep-research tracks can only be prepared from scoped state", fmt.Errorf("current phase is %s", state.Phase))
		}
		if freshnessErr := service.requireFreshSpec(state); freshnessErr != nil {
			return deepResearchFailure("blocked", "deep-research specification source is stale", freshnessErr)
		}
		manifest, manifestErr := deepResearchReadManifest(root)
		if manifestErr != nil {
			return deepResearchFailure("blocked", "deep-research track manifest is unavailable", manifestErr)
		}
		tracks := make([]deepResearchTrack, 0, len(rawTracks))
		seenIDs := map[string]bool{}
		coveredCapabilities := map[string]bool{}
		for index, raw := range rawTracks {
			row, rowOK := raw.(map[string]any)
			if !rowOK {
				return deepResearchFailure("invalid", "deep-research track is invalid", fmt.Errorf("tracks[%d] must be an object", index))
			}
			track, parseErr := service.parseTrack(row, state)
			if parseErr != nil {
				return deepResearchFailure("invalid", "deep-research track is invalid", fmt.Errorf("tracks[%d]: %w", index, parseErr))
			}
			if seenIDs[track.TrackID] {
				return deepResearchFailure("invalid", "deep-research track id is duplicated", fmt.Errorf("%s", track.TrackID))
			}
			seenIDs[track.TrackID] = true
			for _, capabilityRef := range track.CapabilityRefs {
				coveredCapabilities[capabilityRef] = true
			}
			tracks = append(tracks, track)
		}
		if !deepResearchSameStringSet(deepResearchSortedKeys(coveredCapabilities), state.Source.CapabilityRefs) {
			return deepResearchFailure("invalid", "deep-research tracks must cover every selected capability", fmt.Errorf("track capability coverage does not equal feasibility_gate.capability_refs"))
		}
		manifest.Tracks = tracks
		manifest.Status = "active"
		state.Phase = "researching"
		state.Revision++
		if writeErr := service.writeStateAndManifest(root, state, manifest, "deep-research.track-prepare"); writeErr != nil {
			return deepResearchFailure("error", "cannot persist deep-research tracks", writeErr)
		}
		env := NewEnvelope("ok", "deep-research tracks prepared")
		env.Data = deepResearchStateData(state)
		env.Data["track_ids"] = deepResearchTrackIDs(manifest)
		env.Data["tracks"] = deepResearchTrackCounts(manifest)
		env.NextArgv = service.commandArgv(state, "track-lease")
		return env
	})
}

func (service deepResearchService) trackLease(args []string) Envelope {
	_, _, root, _, err := service.resolveFeature(optionValue(args, "--feature-dir", ""))
	if err != nil {
		return deepResearchFailure("usage-error", "deep-research feature is invalid", err)
	}
	workerID := strings.TrimSpace(optionValue(args, "--worker-id", ""))
	if !deepResearchWorkerPattern.MatchString(workerID) {
		return deepResearchFailure("usage-error", "deep-research track-lease requires a valid --worker-id", nil)
	}
	return service.withMutationLock(root, func() Envelope {
		state, readErr := deepResearchReadState(root)
		if readErr != nil {
			return deepResearchFailure("blocked", "deep-research state is unavailable", readErr)
		}
		if revisionErr := deepResearchCheckExpectedRevision(args, state, true); revisionErr != nil {
			return deepResearchFailure("blocked", "deep-research revision changed", revisionErr)
		}
		if state.Phase != "researching" {
			return deepResearchFailure("blocked", "deep-research tracks are not leasable", fmt.Errorf("current phase is %s", state.Phase))
		}
		if freshnessErr := service.requireFreshSpec(state); freshnessErr != nil {
			return deepResearchFailure("blocked", "deep-research specification source is stale", freshnessErr)
		}
		manifest, manifestErr := deepResearchReadManifest(root)
		if manifestErr != nil {
			return deepResearchFailure("blocked", "deep-research track manifest is unavailable", manifestErr)
		}
		if workerID == manifest.LeaderID {
			return deepResearchFailure("blocked", "deep-research track requires an independent worker", fmt.Errorf("worker %s is the research leader", workerID))
		}
		trackIndex := -1
		for index := range manifest.Tracks {
			if manifest.Tracks[index].State == "pending" {
				trackIndex = index
				break
			}
		}
		if trackIndex < 0 {
			return deepResearchFailure("blocked", "no pending deep-research track is available", nil)
		}
		track := manifest.Tracks[trackIndex]
		track.State = "leased"
		track.WorkerID = workerID
		track.AttemptNumber++
		track.AttemptID = deepResearchNextAttemptID(manifest)
		track.LastYieldReason = ""
		manifest.Tracks[trackIndex] = track
		state.Revision++
		if writeErr := service.writeStateAndManifest(root, state, manifest, "deep-research.track-lease"); writeErr != nil {
			return deepResearchFailure("error", "cannot lease deep-research track", writeErr)
		}
		env := NewEnvelope("ok", "deep-research track leased")
		env.Data = deepResearchStateData(state)
		env.Data["track_id"] = track.TrackID
		env.Data["attempt_id"] = track.AttemptID
		env.Data["worker_id"] = workerID
		env.Data["result_protocol"] = deepResearchTrackProtocol
		env.Data["packet"] = deepResearchTrackPacket(track, state)
		env.Data["tracks"] = deepResearchTrackCounts(manifest)
		return env
	})
}

func (service deepResearchService) trackYield(args []string) Envelope {
	_, _, root, _, err := service.resolveFeature(optionValue(args, "--feature-dir", ""))
	if err != nil {
		return deepResearchFailure("usage-error", "deep-research feature is invalid", err)
	}
	trackID := strings.ToUpper(strings.TrimSpace(optionValue(args, "--track-id", "")))
	attemptID := strings.ToUpper(strings.TrimSpace(optionValue(args, "--attempt-id", "")))
	reason := strings.TrimSpace(optionValue(args, "--reason", ""))
	if !deepResearchTrackIDPattern.MatchString(trackID) || !deepResearchAttemptIDPattern.MatchString(attemptID) || reason == "" {
		return deepResearchFailure("usage-error", "deep-research track-yield requires --track-id, --attempt-id, and --reason", nil)
	}
	return service.withMutationLock(root, func() Envelope {
		state, readErr := deepResearchReadState(root)
		if readErr != nil {
			return deepResearchFailure("blocked", "deep-research state is unavailable", readErr)
		}
		if revisionErr := deepResearchCheckExpectedRevision(args, state, true); revisionErr != nil {
			return deepResearchFailure("blocked", "deep-research revision changed", revisionErr)
		}
		manifest, manifestErr := deepResearchReadManifest(root)
		if manifestErr != nil {
			return deepResearchFailure("blocked", "deep-research track manifest is unavailable", manifestErr)
		}
		index := deepResearchFindTrack(manifest, trackID)
		if index < 0 || manifest.Tracks[index].State != "leased" || manifest.Tracks[index].AttemptID != attemptID {
			return deepResearchFailure("blocked", "deep-research track lease no longer matches", nil)
		}
		track := manifest.Tracks[index]
		track.State = "pending"
		track.WorkerID = ""
		track.AttemptID = ""
		track.LastYieldReason = reason
		manifest.Tracks[index] = track
		state.Revision++
		if writeErr := service.writeStateAndManifest(root, state, manifest, "deep-research.track-yield"); writeErr != nil {
			return deepResearchFailure("error", "cannot yield deep-research track", writeErr)
		}
		env := NewEnvelope("ok", "deep-research track yielded")
		env.Data = deepResearchStateData(state)
		env.Data["track_id"] = trackID
		env.Data["tracks"] = deepResearchTrackCounts(manifest)
		env.NextArgv = service.commandArgv(state, "track-lease")
		return env
	})
}

func (service deepResearchService) trackSubmit(args []string) Envelope {
	featurePath, featureRef, root, _, err := service.resolveFeature(optionValue(args, "--feature-dir", ""))
	if err != nil {
		return deepResearchFailure("usage-error", "deep-research feature is invalid", err)
	}
	trackID := strings.ToUpper(strings.TrimSpace(optionValue(args, "--track-id", "")))
	attemptID := strings.ToUpper(strings.TrimSpace(optionValue(args, "--attempt-id", "")))
	if !deepResearchTrackIDPattern.MatchString(trackID) || !deepResearchAttemptIDPattern.MatchString(attemptID) {
		return deepResearchFailure("usage-error", "deep-research track-submit requires valid --track-id and --attempt-id", nil)
	}
	result, err := service.inputObject(args, "--result-json", "deep-research track-submit")
	if err != nil {
		return deepResearchFailure("usage-error", "deep-research track result is invalid", err)
	}
	return service.withMutationLock(root, func() Envelope {
		state, readErr := deepResearchReadState(root)
		if readErr != nil {
			return deepResearchFailure("blocked", "deep-research state is unavailable", readErr)
		}
		if revisionErr := deepResearchCheckExpectedRevision(args, state, true); revisionErr != nil {
			return deepResearchFailure("blocked", "deep-research revision changed", revisionErr)
		}
		if state.Phase != "researching" {
			return deepResearchFailure("blocked", "deep-research track results are not accepted at this phase", fmt.Errorf("current phase is %s", state.Phase))
		}
		if freshnessErr := service.requireFreshSpec(state); freshnessErr != nil {
			return deepResearchFailure("blocked", "deep-research specification source is stale", freshnessErr)
		}
		manifest, manifestErr := deepResearchReadManifest(root)
		if manifestErr != nil {
			return deepResearchFailure("blocked", "deep-research track manifest is unavailable", manifestErr)
		}
		trackIndex := deepResearchFindTrack(manifest, trackID)
		if trackIndex < 0 {
			return deepResearchFailure("invalid", "deep-research track is unknown", fmt.Errorf("%s", trackID))
		}
		track := manifest.Tracks[trackIndex]
		if track.State != "leased" || track.AttemptID != attemptID {
			return deepResearchFailure("blocked", "deep-research track lease no longer matches", fmt.Errorf("track %s is %s", trackID, track.State))
		}
		canonical, evidenceObjects, normalizeErr := service.normalizeTrackResult(featurePath, featureRef, state, manifest, track, result)
		if normalizeErr != nil {
			return deepResearchFailure("invalid", "deep-research track result is invalid", normalizeErr)
		}
		resultRaw, marshalErr := deepResearchMarshal(canonical)
		if marshalErr != nil {
			return deepResearchFailure("error", "cannot render deep-research track result", marshalErr)
		}
		resultRelative := filepath.ToSlash(filepath.Join("research", "handoffs", track.TrackID+".json"))
		track.ResultRef = filepath.ToSlash(filepath.Join(featureRef, resultRelative))
		track.ResultSHA256 = deepResearchDigest(resultRaw)
		if canonical["status"] == "blocked" {
			track.State = "submitted-blocked"
		} else {
			track.State = "submitted"
		}
		manifest.Tracks[trackIndex] = track
		state.Revision++
		values := map[string]any{
			filepath.Join(root, deepResearchStateFilename):                 state,
			filepath.Join(root, deepResearchManifestFilename):              manifest,
			filepath.Join(featurePath, filepath.FromSlash(resultRelative)): canonical,
		}
		for evidenceID, evidence := range evidenceObjects {
			values[filepath.Join(featurePath, "research-evidence", evidenceID+".json")] = evidence
		}
		updates, updateErr := deepResearchJSONUpdates(values)
		if updateErr != nil {
			return deepResearchFailure("error", "cannot render deep-research track artifacts", updateErr)
		}
		if _, transactionErr := applyFileTransaction(service.projectRoot, "deep-research.track-submit", updates); transactionErr != nil {
			return deepResearchFailure("error", "cannot persist deep-research track result", transactionErr)
		}
		env := NewEnvelope("ok", "deep-research track result submitted")
		env.Data = deepResearchStateData(state)
		env.Data["track_id"] = track.TrackID
		env.Data["attempt_id"] = track.AttemptID
		env.Data["result_ref"] = track.ResultRef
		env.Data["result_sha256"] = track.ResultSHA256
		env.Data["worker_status"] = canonical["status"]
		env.NextArgv = service.commandArgv(state, "track-accept")
		return env
	})
}

func (service deepResearchService) trackReject(args []string) Envelope {
	featurePath, featureRef, root, _, err := service.resolveFeature(optionValue(args, "--feature-dir", ""))
	if err != nil {
		return deepResearchFailure("usage-error", "deep-research feature is invalid", err)
	}
	trackID := strings.ToUpper(strings.TrimSpace(optionValue(args, "--track-id", "")))
	attemptID := strings.ToUpper(strings.TrimSpace(optionValue(args, "--attempt-id", "")))
	leaderID := strings.TrimSpace(optionValue(args, "--leader-id", ""))
	reason := strings.TrimSpace(optionValue(args, "--reason", ""))
	if !deepResearchTrackIDPattern.MatchString(trackID) || !deepResearchAttemptIDPattern.MatchString(attemptID) || !deepResearchWorkerPattern.MatchString(leaderID) || reason == "" {
		return deepResearchFailure("usage-error", "deep-research track-reject requires valid track, attempt, leader, and reason values", nil)
	}
	return service.withMutationLock(root, func() Envelope {
		state, readErr := deepResearchReadState(root)
		if readErr != nil {
			return deepResearchFailure("blocked", "deep-research state is unavailable", readErr)
		}
		if revisionErr := deepResearchCheckExpectedRevision(args, state, true); revisionErr != nil {
			return deepResearchFailure("blocked", "deep-research revision changed", revisionErr)
		}
		if state.Phase != "researching" {
			return deepResearchFailure("blocked", "deep-research track rejection is not available at this phase", fmt.Errorf("current phase is %s", state.Phase))
		}
		if freshnessErr := service.requireFreshSpec(state); freshnessErr != nil {
			return deepResearchFailure("blocked", "deep-research specification source is stale", freshnessErr)
		}
		manifest, manifestErr := deepResearchReadManifest(root)
		if manifestErr != nil {
			return deepResearchFailure("blocked", "deep-research track manifest is unavailable", manifestErr)
		}
		if manifest.LeaderID != leaderID {
			return deepResearchFailure("blocked", "only the generation leader can reject a deep-research track", nil)
		}
		trackIndex := deepResearchFindTrack(manifest, trackID)
		if trackIndex < 0 {
			return deepResearchFailure("invalid", "deep-research track is unknown", fmt.Errorf("%s", trackID))
		}
		track := manifest.Tracks[trackIndex]
		if !deepResearchContains([]string{"submitted", "submitted-blocked"}, track.State) || track.AttemptID != attemptID {
			return deepResearchFailure("blocked", "deep-research submitted result no longer matches", fmt.Errorf("track %s is %s", trackID, track.State))
		}
		result, resultRaw, resultErr := service.readTrackResult(featurePath, track)
		if resultErr != nil {
			return deepResearchFailure("blocked", "deep-research track result is unavailable", resultErr)
		}
		if deepResearchDigest(resultRaw) != track.ResultSHA256 {
			return deepResearchFailure("blocked", "deep-research track result was modified after submission", nil)
		}
		rejectionRelative := filepath.ToSlash(filepath.Join("research", "rejections", track.TrackID+"-"+track.AttemptID+".json"))
		rejectionRef := filepath.ToSlash(filepath.Join(featureRef, rejectionRelative))
		rejectionRecord := map[string]any{
			"schema_version":          deepResearchRejectionSchema,
			"generation_id":           manifest.GenerationID,
			"track_id":                track.TrackID,
			"attempt_id":              track.AttemptID,
			"worker_id":               track.WorkerID,
			"reason":                  reason,
			"submitted_result_ref":    track.ResultRef,
			"submitted_result_sha256": track.ResultSHA256,
			"submitted_result":        result,
		}
		rejectionRaw, marshalErr := deepResearchMarshal(rejectionRecord)
		if marshalErr != nil {
			return deepResearchFailure("error", "cannot render deep-research track rejection", marshalErr)
		}
		track.Rejections = append(track.Rejections, deepResearchTrackRejection{
			AttemptID:       track.AttemptID,
			WorkerID:        track.WorkerID,
			ResultRef:       track.ResultRef,
			ResultSHA256:    track.ResultSHA256,
			RejectionRef:    rejectionRef,
			RejectionSHA256: deepResearchDigest(rejectionRaw),
			Reason:          reason,
		})
		state.Revision++
		retryExhausted := track.AttemptNumber >= 2
		if retryExhausted {
			track.State = "blocked"
			state.Status = "blocked"
			state.ClaimStatus = "blocked"
			state.Blockers = []any{fmt.Sprintf("track %s was rejected after its single retry: %s", track.TrackID, reason)}
		} else {
			track.State = "pending"
			track.WorkerID = ""
			track.AttemptID = ""
			track.ResultRef = ""
			track.ResultSHA256 = ""
			track.LastYieldReason = "rejected: " + reason
			state.Status = "active"
			state.ClaimStatus = "pending"
			state.Blockers = []any{}
		}
		manifest.Tracks[trackIndex] = track
		values := map[string]any{
			filepath.Join(root, deepResearchStateFilename):                    state,
			filepath.Join(root, deepResearchManifestFilename):                 manifest,
			filepath.Join(featurePath, filepath.FromSlash(rejectionRelative)): rejectionRecord,
		}
		updates, updateErr := deepResearchJSONUpdates(values)
		if updateErr != nil {
			return deepResearchFailure("error", "cannot render deep-research rejection state", updateErr)
		}
		if _, transactionErr := applyFileTransaction(service.projectRoot, "deep-research.track-reject", updates); transactionErr != nil {
			return deepResearchFailure("error", "cannot reject deep-research track", transactionErr)
		}
		if retryExhausted {
			env := deepResearchFailure("blocked", "deep-research track retry was rejected", fmt.Errorf("track %s exhausted its single retry", track.TrackID))
			env.Data = deepResearchStateData(state)
			return env
		}
		env := NewEnvelope("ok", "deep-research track rejected and requeued")
		env.Data = deepResearchStateData(state)
		env.Data["track_id"] = track.TrackID
		env.Data["rejected_attempt_id"] = attemptID
		env.Data["rejection_ref"] = rejectionRef
		env.Data["tracks"] = deepResearchTrackCounts(manifest)
		env.NextArgv = service.commandArgv(state, "track-lease")
		return env
	})
}

func (service deepResearchService) trackAccept(args []string) Envelope {
	featurePath, _, root, _, err := service.resolveFeature(optionValue(args, "--feature-dir", ""))
	if err != nil {
		return deepResearchFailure("usage-error", "deep-research feature is invalid", err)
	}
	trackID := strings.ToUpper(strings.TrimSpace(optionValue(args, "--track-id", "")))
	attemptID := strings.ToUpper(strings.TrimSpace(optionValue(args, "--attempt-id", "")))
	leaderID := strings.TrimSpace(optionValue(args, "--leader-id", ""))
	if !deepResearchTrackIDPattern.MatchString(trackID) || !deepResearchAttemptIDPattern.MatchString(attemptID) || !deepResearchWorkerPattern.MatchString(leaderID) {
		return deepResearchFailure("usage-error", "deep-research track-accept requires valid track, attempt, and leader identities", nil)
	}
	return service.withMutationLock(root, func() Envelope {
		state, readErr := deepResearchReadState(root)
		if readErr != nil {
			return deepResearchFailure("blocked", "deep-research state is unavailable", readErr)
		}
		if revisionErr := deepResearchCheckExpectedRevision(args, state, true); revisionErr != nil {
			return deepResearchFailure("blocked", "deep-research revision changed", revisionErr)
		}
		if freshnessErr := service.requireFreshSpec(state); freshnessErr != nil {
			return deepResearchFailure("blocked", "deep-research specification source is stale", freshnessErr)
		}
		manifest, manifestErr := deepResearchReadManifest(root)
		if manifestErr != nil {
			return deepResearchFailure("blocked", "deep-research track manifest is unavailable", manifestErr)
		}
		if manifest.LeaderID != leaderID {
			return deepResearchFailure("blocked", "only the generation leader can accept a deep-research track", nil)
		}
		trackIndex := deepResearchFindTrack(manifest, trackID)
		if trackIndex < 0 {
			return deepResearchFailure("invalid", "deep-research track is unknown", fmt.Errorf("%s", trackID))
		}
		track := manifest.Tracks[trackIndex]
		if !deepResearchContains([]string{"submitted", "submitted-blocked"}, track.State) || track.AttemptID != attemptID {
			return deepResearchFailure("blocked", "deep-research submitted result no longer matches", fmt.Errorf("track %s is %s", trackID, track.State))
		}
		result, resultRaw, resultErr := service.readTrackResult(featurePath, track)
		if resultErr != nil {
			return deepResearchFailure("blocked", "deep-research track result is unavailable", resultErr)
		}
		if deepResearchDigest(resultRaw) != track.ResultSHA256 {
			return deepResearchFailure("blocked", "deep-research track result was modified after submission", nil)
		}
		if evidenceErr := service.verifyTrackEvidence(featurePath, state, track, result); evidenceErr != nil {
			return deepResearchFailure("blocked", "deep-research track evidence is invalid", evidenceErr)
		}
		state.Revision++
		if strings.TrimSpace(asString(result["status"])) == "blocked" {
			track.State = "blocked"
			manifest.Tracks[trackIndex] = track
			state.Status = "blocked"
			state.ClaimStatus = "blocked"
			state.Blockers = deepResearchAnySlice(result["blockers"])
			if len(state.Blockers) == 0 {
				state.Blockers = []any{"track " + track.TrackID + " reported blocked"}
			}
			if writeErr := service.writeStateAndManifest(root, state, manifest, "deep-research.track-blocked"); writeErr != nil {
				return deepResearchFailure("error", "cannot persist blocked deep-research track", writeErr)
			}
			env := deepResearchFailure("blocked", "deep-research track reported a blocking condition", fmt.Errorf("track %s", track.TrackID))
			env.Data = deepResearchStateData(state)
			return env
		}
		track.State = "accepted"
		manifest.Tracks[trackIndex] = track
		state.AcceptedRefs = deepResearchAppendUnique(state.AcceptedRefs, track.ResultRef)
		if deepResearchAllTracksAccepted(manifest) {
			manifest.Status = "accepted"
		}
		if writeErr := service.writeStateAndManifest(root, state, manifest, "deep-research.track-accept"); writeErr != nil {
			return deepResearchFailure("error", "cannot accept deep-research track", writeErr)
		}
		env := NewEnvelope("ok", "deep-research track accepted")
		env.Data = deepResearchStateData(state)
		env.Data["track_id"] = track.TrackID
		env.Data["tracks"] = deepResearchTrackCounts(manifest)
		if deepResearchAllTracksAccepted(manifest) {
			env.NextArgv = service.commandArgv(state, "synthesize")
		} else {
			env.NextArgv = service.commandArgv(state, "track-lease")
		}
		return env
	})
}

func (service deepResearchService) normalizeTrackResult(featurePath, featureRef string, state deepResearchState, manifest deepResearchTrackManifest, track deepResearchTrack, payload map[string]any) (map[string]any, map[string]map[string]any, error) {
	if strings.TrimSpace(asString(payload["protocol"])) != deepResearchTrackProtocol {
		return nil, nil, fmt.Errorf("protocol must be %s", deepResearchTrackProtocol)
	}
	status := strings.ToLower(strings.TrimSpace(asString(payload["status"])))
	if !deepResearchContains([]string{"complete", "blocked"}, status) {
		return nil, nil, fmt.Errorf("status must be complete or blocked")
	}
	pathsRead, err := service.normalizedProjectPathList(payload["paths_read"], "paths_read", true)
	if err != nil || len(pathsRead) == 0 {
		return nil, nil, firstDeepResearchError(err, fmt.Errorf("paths_read must not be empty"))
	}
	for _, pathRead := range pathsRead {
		if !deepResearchPathCovered(pathRead, track.ReadPaths) {
			return nil, nil, fmt.Errorf("paths_read contains unassigned path %s", pathRead)
		}
	}
	blockers, err := deepResearchStrictStrings(payload["blockers"], "blockers", status == "blocked")
	if err != nil && payload["blockers"] != nil {
		return nil, nil, err
	}
	if status == "blocked" {
		if len(blockers) == 0 {
			return nil, nil, fmt.Errorf("blocked track result requires blockers")
		}
		return map[string]any{
			"schema_version": deepResearchTrackProtocol,
			"generation_id":  manifest.GenerationID,
			"track_id":       track.TrackID,
			"attempt_id":     track.AttemptID,
			"worker_id":      track.WorkerID,
			"status":         status,
			"paths_read":     pathsRead,
			"findings":       []any{},
			"evidence_refs":  []string{},
			"spike_refs":     []string{},
			"constraints":    []string{},
			"risks":          []string{},
			"contradictions": []any{},
			"blockers":       blockers,
		}, map[string]map[string]any{}, nil
	}

	rawEvidence, ok := payload["evidence"].([]any)
	if !ok || len(rawEvidence) == 0 {
		return nil, nil, fmt.Errorf("complete track result requires a non-empty evidence array")
	}
	evidenceObjects := map[string]map[string]any{}
	for index, raw := range rawEvidence {
		row, rowOK := raw.(map[string]any)
		if !rowOK {
			return nil, nil, fmt.Errorf("evidence[%d] must be an object", index)
		}
		evidenceID := strings.ToUpper(strings.TrimSpace(asString(row["evidence_id"])))
		if !deepResearchEvidencePattern.MatchString(evidenceID) {
			return nil, nil, fmt.Errorf("evidence[%d].evidence_id is invalid", index)
		}
		if _, duplicate := evidenceObjects[evidenceID]; duplicate {
			return nil, nil, fmt.Errorf("evidence_id %s is duplicated", evidenceID)
		}
		if collisionErr := service.rejectEvidenceCollision(featurePath, manifest.GenerationID, track.TrackID, evidenceID); collisionErr != nil {
			return nil, nil, collisionErr
		}
		canonical, normalizeErr := service.normalizeEvidence(featurePath, featureRef, state, manifest, track, pathsRead, row)
		if normalizeErr != nil {
			return nil, nil, fmt.Errorf("evidence[%d]: %w", index, normalizeErr)
		}
		evidenceObjects[evidenceID] = canonical
	}
	evidenceIDs := deepResearchSortedMapKeys(evidenceObjects)

	spikeRefs, err := deepResearchStrictStrings(payload["spike_refs"], "spike_refs", track.RequiresSpike)
	if err != nil {
		return nil, nil, err
	}
	for _, spikeRef := range spikeRefs {
		if err := service.validateSpikeManifest(featurePath, featureRef, spikeRef, track); err != nil {
			return nil, nil, err
		}
	}
	if track.RequiresSpike && len(spikeRefs) == 0 {
		return nil, nil, fmt.Errorf("track %s requires at least one completed spike", track.TrackID)
	}

	rawFindings, ok := payload["findings"].([]any)
	if !ok || len(rawFindings) == 0 {
		return nil, nil, fmt.Errorf("complete track result requires a non-empty findings array")
	}
	findings := make([]any, 0, len(rawFindings))
	seenFindings := map[string]bool{}
	for index, raw := range rawFindings {
		row, rowOK := raw.(map[string]any)
		if !rowOK {
			return nil, nil, fmt.Errorf("findings[%d] must be an object", index)
		}
		findingID := strings.ToUpper(strings.TrimSpace(asString(row["finding_id"])))
		kind := strings.ToLower(strings.TrimSpace(asString(row["kind"])))
		summary := strings.TrimSpace(asString(row["summary"]))
		if !deepResearchFindingPattern.MatchString(findingID) || seenFindings[findingID] {
			return nil, nil, fmt.Errorf("findings[%d].finding_id is invalid or duplicated", index)
		}
		if !deepResearchContains([]string{"fact", "inference", "recommendation"}, kind) || summary == "" {
			return nil, nil, fmt.Errorf("findings[%d] requires kind fact|inference|recommendation and a summary", index)
		}
		capabilityRefs, refsErr := deepResearchStrictStrings(row["capability_refs"], "finding capability_refs", true)
		if refsErr != nil || !deepResearchStringSubset(capabilityRefs, track.CapabilityRefs) {
			return nil, nil, firstDeepResearchError(refsErr, fmt.Errorf("finding capability_refs escape the assigned track"))
		}
		findingEvidence, refsErr := deepResearchStrictStrings(row["evidence_refs"], "finding evidence_refs", true)
		if refsErr != nil || !deepResearchStringSubset(findingEvidence, evidenceIDs) {
			return nil, nil, firstDeepResearchError(refsErr, fmt.Errorf("finding evidence_refs must name evidence submitted by this track"))
		}
		findingSpikes, refsErr := deepResearchStrictStrings(row["spike_refs"], "finding spike_refs", false)
		if refsErr != nil || !deepResearchStringSubset(findingSpikes, spikeRefs) {
			return nil, nil, firstDeepResearchError(refsErr, fmt.Errorf("finding spike_refs must name submitted spikes"))
		}
		seenFindings[findingID] = true
		findings = append(findings, map[string]any{
			"finding_id":      findingID,
			"kind":            kind,
			"summary":         summary,
			"capability_refs": capabilityRefs,
			"evidence_refs":   findingEvidence,
			"spike_refs":      findingSpikes,
		})
	}
	constraints, err := deepResearchOptionalStrings(payload["constraints"], "constraints")
	if err != nil {
		return nil, nil, err
	}
	risks, err := deepResearchOptionalStrings(payload["risks"], "risks")
	if err != nil {
		return nil, nil, err
	}
	contradictions, err := deepResearchNormalizeContradictions(payload["contradictions"], evidenceIDs)
	if err != nil {
		return nil, nil, err
	}
	return map[string]any{
		"schema_version": deepResearchTrackProtocol,
		"generation_id":  manifest.GenerationID,
		"track_id":       track.TrackID,
		"attempt_id":     track.AttemptID,
		"worker_id":      track.WorkerID,
		"status":         status,
		"paths_read":     pathsRead,
		"findings":       findings,
		"evidence_refs":  evidenceIDs,
		"spike_refs":     spikeRefs,
		"constraints":    constraints,
		"risks":          risks,
		"contradictions": contradictions,
		"blockers":       []string{},
	}, evidenceObjects, nil
}

func (service deepResearchService) normalizeEvidence(featurePath, featureRef string, state deepResearchState, manifest deepResearchTrackManifest, track deepResearchTrack, pathsRead []string, row map[string]any) (map[string]any, error) {
	evidenceID := strings.ToUpper(strings.TrimSpace(asString(row["evidence_id"])))
	sourceType := strings.ToLower(strings.TrimSpace(asString(row["source_type"])))
	sourceRef := strings.TrimSpace(asString(row["source_ref"]))
	claim := strings.TrimSpace(asString(row["claim"]))
	if !deepResearchContains([]string{"repository", "primary_external", "secondary_external", "experiment"}, sourceType) {
		return nil, fmt.Errorf("source_type is invalid")
	}
	if (state.Mode == "repo-only" || state.Mode == "external-blocked") && (sourceType == "primary_external" || sourceType == "secondary_external") {
		return nil, fmt.Errorf("%s mode rejects external evidence", state.Mode)
	}
	if sourceRef == "" || claim == "" {
		return nil, fmt.Errorf("source_ref and claim are required")
	}
	capabilityRefs, err := deepResearchStrictStrings(row["capability_refs"], "evidence capability_refs", true)
	if err != nil || !deepResearchStringSubset(capabilityRefs, track.CapabilityRefs) {
		return nil, firstDeepResearchError(err, fmt.Errorf("evidence capability_refs escape the assigned track"))
	}
	quality, ok := row["quality"].(map[string]any)
	if !ok {
		return nil, fmt.Errorf("quality must be an object")
	}
	authority := strings.ToLower(strings.TrimSpace(asString(quality["authority"])))
	independence := strings.ToLower(strings.TrimSpace(asString(quality["independence"])))
	recency := strings.ToLower(strings.TrimSpace(asString(quality["recency"])))
	limitations, err := deepResearchOptionalStrings(quality["limitations"], "quality.limitations")
	if err != nil {
		return nil, err
	}
	if !deepResearchContains([]string{"repository", "primary", "secondary", "experiment"}, authority) ||
		!deepResearchContains([]string{"direct", "independent", "corroborated", "single-source"}, independence) ||
		!deepResearchContains([]string{"current", "dated", "unknown"}, recency) {
		return nil, fmt.Errorf("quality authority, independence, or recency is invalid")
	}
	canonicalSourceRef := sourceRef
	var sourceSHA any
	var sourceTitle any
	var retrievedOn any
	switch sourceType {
	case "repository":
		normalized, normalizeErr := service.normalizedProjectPath(sourceRef, false, true)
		if normalizeErr != nil {
			return nil, normalizeErr
		}
		if !deepResearchPathCovered(normalized, pathsRead) {
			return nil, fmt.Errorf("repository evidence source %s is absent from paths_read", normalized)
		}
		raw, readErr := deepResearchReadRegularProjectFile(service.projectRoot, normalized)
		if readErr != nil {
			return nil, readErr
		}
		canonicalSourceRef = normalized
		sourceSHA = deepResearchDigest(raw)
		sourceTitle = nil
		retrievedOn = nil
	case "primary_external", "secondary_external":
		parsed, parseErr := url.Parse(sourceRef)
		if parseErr != nil || (parsed.Scheme != "https" && parsed.Scheme != "http") || parsed.Host == "" {
			return nil, fmt.Errorf("external evidence source_ref must be an http(s) URL")
		}
		title := strings.TrimSpace(asString(row["source_title"]))
		date := strings.TrimSpace(asString(row["retrieved_on"]))
		if title == "" {
			return nil, fmt.Errorf("external evidence requires source_title")
		}
		if _, dateErr := time.Parse("2006-01-02", date); dateErr != nil {
			return nil, fmt.Errorf("external evidence retrieved_on must be YYYY-MM-DD")
		}
		sourceSHA = nil
		sourceTitle = title
		retrievedOn = date
	case "experiment":
		if err := service.validateSpikeManifest(featurePath, featureRef, sourceRef, track); err != nil {
			return nil, err
		}
		canonicalSourceRef = deepResearchCanonicalSpikeRef(featureRef, sourceRef)
		raw, readErr := deepResearchReadRegularProjectFile(service.projectRoot, canonicalSourceRef)
		if readErr != nil {
			return nil, readErr
		}
		sourceSHA = deepResearchDigest(raw)
		sourceTitle = nil
		retrievedOn = nil
	}
	return map[string]any{
		"schema_version":  deepResearchEvidenceSchema,
		"generation_id":   manifest.GenerationID,
		"evidence_id":     evidenceID,
		"track_id":        track.TrackID,
		"source_type":     sourceType,
		"source_ref":      canonicalSourceRef,
		"source_sha256":   sourceSHA,
		"source_title":    sourceTitle,
		"retrieved_on":    retrievedOn,
		"claim":           claim,
		"capability_refs": capabilityRefs,
		"quality": map[string]any{
			"authority":    authority,
			"independence": independence,
			"recency":      recency,
			"limitations":  limitations,
		},
	}, nil
}

func (service deepResearchService) rejectEvidenceCollision(featurePath, generationID, trackID, evidenceID string) error {
	path := filepath.Join(featurePath, "research-evidence", evidenceID+".json")
	payload, err := deepResearchReadObject(path)
	if errors.Is(err, os.ErrNotExist) {
		return nil
	}
	if err != nil {
		return fmt.Errorf("existing evidence %s is invalid: %w", evidenceID, err)
	}
	if strings.TrimSpace(asString(payload["generation_id"])) == generationID && strings.TrimSpace(asString(payload["track_id"])) == trackID {
		return nil
	}
	return fmt.Errorf("evidence_id %s is already owned by another generation or track", evidenceID)
}

func (service deepResearchService) validateSpikeManifest(featurePath, featureRef, ref string, track deepResearchTrack) error {
	canonicalRef := deepResearchCanonicalSpikeRef(featureRef, ref)
	expectedPrefix := strings.TrimSuffix(featureRef, "/") + "/research-spikes/"
	if !strings.HasPrefix(canonicalRef, expectedPrefix) || filepath.Base(filepath.FromSlash(canonicalRef)) != "manifest.json" {
		return fmt.Errorf("spike ref must be <feature-dir>/research-spikes/SPK-###/manifest.json: %s", ref)
	}
	spikeID := filepath.Base(filepath.Dir(filepath.FromSlash(canonicalRef)))
	if !deepResearchSpikePattern.MatchString(spikeID) {
		return fmt.Errorf("spike ref has invalid SPK id: %s", ref)
	}
	payload, err := deepResearchReadObject(filepath.Join(service.projectRoot, filepath.FromSlash(canonicalRef)))
	if err != nil {
		return fmt.Errorf("spike manifest is unavailable: %w", err)
	}
	if strings.TrimSpace(asString(payload["schema_version"])) != "spec-kit-deep-research-spike-v1" ||
		strings.TrimSpace(asString(payload["spike_id"])) != spikeID ||
		strings.ToLower(strings.TrimSpace(asString(payload["status"]))) != "completed" {
		return fmt.Errorf("spike manifest %s must be a completed v1 manifest", ref)
	}
	capabilityRefs, refsErr := deepResearchStrictStrings(payload["capability_refs"], "spike capability_refs", true)
	if refsErr != nil || !deepResearchStringSubset(capabilityRefs, track.CapabilityRefs) {
		return firstDeepResearchError(refsErr, fmt.Errorf("spike capability_refs escape the assigned track"))
	}
	if strings.TrimSpace(asString(payload["question"])) == "" || strings.TrimSpace(asString(payload["result"])) == "" {
		return fmt.Errorf("spike manifest requires question and result")
	}
	commands, ok := payload["commands"].([]any)
	if !ok || len(commands) == 0 {
		return fmt.Errorf("spike manifest requires executed commands")
	}
	for index, raw := range commands {
		command, commandOK := raw.(map[string]any)
		if !commandOK || strings.TrimSpace(asString(command["command"])) == "" || strings.TrimSpace(asString(command["output_summary"])) == "" {
			return fmt.Errorf("spike commands[%d] is invalid", index)
		}
		if _, ok := hookJSONInteger(command["exit_code"]); !ok {
			return fmt.Errorf("spike commands[%d].exit_code must be an integer", index)
		}
	}
	_ = featurePath
	return nil
}

func (service deepResearchService) readTrackResult(featurePath string, track deepResearchTrack) (map[string]any, []byte, error) {
	path, err := service.projectRelativePath(track.ResultRef)
	if err != nil {
		return nil, nil, err
	}
	if !deepResearchPathWithin(path, featurePath) {
		return nil, nil, fmt.Errorf("track result escapes the feature")
	}
	raw, err := deepResearchReadRegularFile(path)
	if err != nil {
		return nil, nil, err
	}
	var payload map[string]any
	if err := json.Unmarshal(raw, &payload); err != nil || payload == nil {
		return nil, nil, fmt.Errorf("track result must contain a JSON object")
	}
	return payload, raw, nil
}

func (service deepResearchService) verifyTrackEvidence(featurePath string, state deepResearchState, track deepResearchTrack, result map[string]any) error {
	if strings.TrimSpace(asString(result["schema_version"])) != deepResearchTrackProtocol ||
		strings.TrimSpace(asString(result["track_id"])) != track.TrackID ||
		strings.TrimSpace(asString(result["attempt_id"])) != track.AttemptID ||
		strings.TrimSpace(asString(result["worker_id"])) != track.WorkerID {
		return fmt.Errorf("track result identity is stale")
	}
	evidenceRefs, err := deepResearchStrictStrings(result["evidence_refs"], "track evidence_refs", false)
	if err != nil {
		return err
	}
	for _, evidenceID := range evidenceRefs {
		if !deepResearchEvidencePattern.MatchString(evidenceID) {
			return fmt.Errorf("track evidence id is invalid: %s", evidenceID)
		}
		payload, readErr := deepResearchReadObject(filepath.Join(featurePath, "research-evidence", evidenceID+".json"))
		if readErr != nil {
			return readErr
		}
		if strings.TrimSpace(asString(payload["schema_version"])) != deepResearchEvidenceSchema ||
			strings.TrimSpace(asString(payload["evidence_id"])) != evidenceID ||
			strings.TrimSpace(asString(payload["track_id"])) != track.TrackID {
			return fmt.Errorf("evidence %s identity is invalid", evidenceID)
		}
		if sourceErr := service.verifyEvidenceSource(payload); sourceErr != nil {
			return fmt.Errorf("evidence %s source is stale: %w", evidenceID, sourceErr)
		}
	}
	for _, spikeRef := range deepResearchStrings(result["spike_refs"]) {
		if err := service.validateSpikeManifest(featurePath, state.FeatureDir, spikeRef, track); err != nil {
			return err
		}
	}
	return nil
}

func (service deepResearchService) verifyEvidenceSource(payload map[string]any) error {
	sourceType := strings.TrimSpace(asString(payload["source_type"]))
	if sourceType != "repository" && sourceType != "experiment" {
		return nil
	}
	ref := strings.TrimSpace(asString(payload["source_ref"]))
	raw, err := deepResearchReadRegularProjectFile(service.projectRoot, ref)
	if err != nil {
		return err
	}
	expected := strings.TrimSpace(asString(payload["source_sha256"]))
	if !deepResearchSHA256Pattern.MatchString(expected) || deepResearchDigest(raw) != expected {
		return fmt.Errorf("source digest changed")
	}
	return nil
}

func (service deepResearchService) synthesize(args []string) Envelope {
	featurePath, featureRef, root, _, err := service.resolveFeature(optionValue(args, "--feature-dir", ""))
	if err != nil {
		return deepResearchFailure("usage-error", "deep-research feature is invalid", err)
	}
	leaderID := strings.TrimSpace(optionValue(args, "--leader-id", ""))
	if !deepResearchWorkerPattern.MatchString(leaderID) {
		return deepResearchFailure("usage-error", "deep-research synthesize requires a valid --leader-id", nil)
	}
	input, err := service.inputObject(args, "--input-json", "deep-research synthesize")
	if err != nil {
		return deepResearchFailure("usage-error", "deep-research synthesis input is invalid", err)
	}
	return service.withMutationLock(root, func() Envelope {
		state, readErr := deepResearchReadState(root)
		if readErr != nil {
			return deepResearchFailure("blocked", "deep-research state is unavailable", readErr)
		}
		if revisionErr := deepResearchCheckExpectedRevision(args, state, true); revisionErr != nil {
			return deepResearchFailure("blocked", "deep-research revision changed", revisionErr)
		}
		if state.Phase != "researching" {
			return deepResearchFailure("blocked", "deep-research synthesis is not available at this phase", fmt.Errorf("current phase is %s", state.Phase))
		}
		if freshnessErr := service.requireFreshSpec(state); freshnessErr != nil {
			return deepResearchFailure("blocked", "deep-research specification source is stale", freshnessErr)
		}
		manifest, manifestErr := deepResearchReadManifest(root)
		if manifestErr != nil {
			return deepResearchFailure("blocked", "deep-research track manifest is unavailable", manifestErr)
		}
		if manifest.LeaderID != leaderID {
			return deepResearchFailure("blocked", "only the generation leader can synthesize deep research", nil)
		}
		if !deepResearchAllTracksAccepted(manifest) {
			return deepResearchFailure("blocked", "deep-research synthesis requires every track to be accepted", nil)
		}
		corpus, corpusErr := service.acceptedCorpus(featurePath, state, manifest)
		if corpusErr != nil {
			return deepResearchFailure("blocked", "accepted deep-research corpus is invalid", corpusErr)
		}
		canonical, normalizeErr := deepResearchNormalizeSynthesis(state, manifest, corpus, input)
		if normalizeErr != nil {
			return deepResearchFailure("invalid", "deep-research synthesis does not close the planning contract", normalizeErr)
		}
		synthesisRaw, marshalErr := deepResearchMarshal(canonical)
		if marshalErr != nil {
			return deepResearchFailure("error", "cannot render deep-research synthesis", marshalErr)
		}
		markdown := deepResearchRenderMarkdown(canonical)
		synthesisRef := filepath.ToSlash(filepath.Join(featureRef, "research", deepResearchSynthesisFilename))
		synthesisSHA := deepResearchDigest(synthesisRaw)
		state.Synthesis = deepResearchArtifactState{
			Ref:    deepResearchStringPointer(synthesisRef),
			SHA256: deepResearchStringPointer(synthesisSHA),
		}
		state.Phase = "synthesized"
		state.Status = "active"
		state.ClaimStatus = "pending"
		state.Audit = deepResearchAuditState{Required: true, Status: "pending"}
		state.Revision++
		manifest.Status = "synthesized"
		updates, updateErr := deepResearchJSONAndTextUpdates(map[string]any{
			filepath.Join(root, deepResearchStateFilename):     state,
			filepath.Join(root, deepResearchManifestFilename):  manifest,
			filepath.Join(root, deepResearchSynthesisFilename): canonical,
		}, map[string][]byte{
			filepath.Join(featurePath, "deep-research.md"): markdown,
		})
		if updateErr != nil {
			return deepResearchFailure("error", "cannot render deep-research synthesis artifacts", updateErr)
		}
		if _, transactionErr := applyFileTransaction(service.projectRoot, "deep-research.synthesize", updates); transactionErr != nil {
			return deepResearchFailure("error", "cannot persist deep-research synthesis", transactionErr)
		}
		env := NewEnvelope("ok", "deep-research synthesis completed")
		env.Data = deepResearchStateData(state)
		env.Data["synthesis_ref"] = synthesisRef
		env.Data["synthesis_sha256"] = synthesisSHA
		env.Data["handoff_ids"] = deepResearchSynthesisHandoffIDs(canonical)
		env.NextArgv = service.commandArgv(state, "audit-prepare")
		return env
	})
}

func (service deepResearchService) auditPrepare(args []string) Envelope {
	featurePath, featureRef, root, _, err := service.resolveFeature(optionValue(args, "--feature-dir", ""))
	if err != nil {
		return deepResearchFailure("usage-error", "deep-research feature is invalid", err)
	}
	return service.withMutationLock(root, func() Envelope {
		state, readErr := deepResearchReadState(root)
		if readErr != nil {
			return deepResearchFailure("blocked", "deep-research state is unavailable", readErr)
		}
		if revisionErr := deepResearchCheckExpectedRevision(args, state, true); revisionErr != nil {
			return deepResearchFailure("blocked", "deep-research revision changed", revisionErr)
		}
		if state.Phase != "synthesized" || state.Synthesis.Ref == nil || state.Synthesis.SHA256 == nil {
			return deepResearchFailure("blocked", "deep-research audit requires a current synthesis", nil)
		}
		if freshnessErr := service.requireFreshSpec(state); freshnessErr != nil {
			return deepResearchFailure("blocked", "deep-research specification source is stale", freshnessErr)
		}
		manifest, manifestErr := deepResearchReadManifest(root)
		if manifestErr != nil {
			return deepResearchFailure("blocked", "deep-research track manifest is unavailable", manifestErr)
		}
		corpus, corpusErr := service.acceptedCorpus(featurePath, state, manifest)
		if corpusErr != nil {
			return deepResearchFailure("blocked", "accepted deep-research corpus is invalid", corpusErr)
		}
		synthesisRaw, readSynthesisErr := deepResearchReadRegularFile(filepath.Join(root, deepResearchSynthesisFilename))
		if readSynthesisErr != nil || deepResearchDigest(synthesisRaw) != *state.Synthesis.SHA256 {
			return deepResearchFailure("blocked", "deep-research synthesis is stale", firstDeepResearchError(readSynthesisErr, fmt.Errorf("synthesis digest changed")))
		}
		request := map[string]any{
			"schema_version":       deepResearchAuditRequestV1,
			"generation_id":        manifest.GenerationID,
			"feature_dir":          featureRef,
			"source_spec_ref":      state.Source.SpecRef,
			"source_spec_sha256":   state.Source.SpecSHA256,
			"capability_refs":      state.Source.CapabilityRefs,
			"synthesis_ref":        *state.Synthesis.Ref,
			"synthesis_sha256":     *state.Synthesis.SHA256,
			"track_result_digests": corpus.TrackResultDigests,
			"evidence_digests":     corpus.EvidenceDigests,
			"spike_digests":        corpus.SpikeDigests,
			"required_checks":      append([]string(nil), deepResearchAuditCheckIDs...),
			"excluded_auditor_ids": deepResearchResearcherIDs(manifest),
		}
		requestRaw, marshalErr := deepResearchMarshal(request)
		if marshalErr != nil {
			return deepResearchFailure("error", "cannot render deep-research audit request", marshalErr)
		}
		requestRef := filepath.ToSlash(filepath.Join(featureRef, "research", deepResearchAuditRequestFile))
		requestSHA := deepResearchDigest(requestRaw)
		state.Audit = deepResearchAuditState{
			Required:      true,
			Status:        "prepared",
			RequestRef:    deepResearchStringPointer(requestRef),
			RequestSHA256: deepResearchStringPointer(requestSHA),
		}
		state.Phase = "audit"
		state.Revision++
		updates, updateErr := deepResearchJSONUpdates(map[string]any{
			filepath.Join(root, deepResearchStateFilename):    state,
			filepath.Join(root, deepResearchAuditRequestFile): request,
		})
		if updateErr != nil {
			return deepResearchFailure("error", "cannot render deep-research audit state", updateErr)
		}
		if _, transactionErr := applyFileTransaction(service.projectRoot, "deep-research.audit-prepare", updates); transactionErr != nil {
			return deepResearchFailure("error", "cannot prepare deep-research audit", transactionErr)
		}
		env := NewEnvelope("ok", "deep-research independent audit prepared")
		env.Data = deepResearchStateData(state)
		env.Data["audit_request_ref"] = requestRef
		env.Data["audit_request_sha256"] = requestSHA
		env.Data["audit_packet"] = request
		env.NextArgv = service.commandArgv(state, "audit-accept")
		return env
	})
}

func (service deepResearchService) auditAccept(args []string) Envelope {
	_, featureRef, root, _, err := service.resolveFeature(optionValue(args, "--feature-dir", ""))
	if err != nil {
		return deepResearchFailure("usage-error", "deep-research feature is invalid", err)
	}
	auditorID := strings.TrimSpace(optionValue(args, "--auditor-id", ""))
	if !deepResearchWorkerPattern.MatchString(auditorID) {
		return deepResearchFailure("usage-error", "deep-research audit-accept requires a valid --auditor-id", nil)
	}
	input, err := service.inputObject(args, "--input-json", "deep-research audit-accept")
	if err != nil {
		return deepResearchFailure("usage-error", "deep-research audit result is invalid", err)
	}
	return service.withMutationLock(root, func() Envelope {
		state, readErr := deepResearchReadState(root)
		if readErr != nil {
			return deepResearchFailure("blocked", "deep-research state is unavailable", readErr)
		}
		if revisionErr := deepResearchCheckExpectedRevision(args, state, true); revisionErr != nil {
			return deepResearchFailure("blocked", "deep-research revision changed", revisionErr)
		}
		if state.Phase != "audit" || state.Audit.Status != "prepared" || state.Audit.RequestRef == nil || state.Audit.RequestSHA256 == nil {
			return deepResearchFailure("blocked", "deep-research audit is not prepared", nil)
		}
		if freshnessErr := service.requireFreshSpec(state); freshnessErr != nil {
			return deepResearchFailure("blocked", "deep-research specification source is stale", freshnessErr)
		}
		manifest, manifestErr := deepResearchReadManifest(root)
		if manifestErr != nil {
			return deepResearchFailure("blocked", "deep-research track manifest is unavailable", manifestErr)
		}
		if deepResearchContains(deepResearchResearcherIDs(manifest), auditorID) {
			return deepResearchFailure("blocked", "deep-research audit requires an independent identity", fmt.Errorf("auditor %s participated in research or synthesis", auditorID))
		}
		requestRaw, requestErr := deepResearchReadRegularFile(filepath.Join(root, deepResearchAuditRequestFile))
		if requestErr != nil || deepResearchDigest(requestRaw) != *state.Audit.RequestSHA256 {
			return deepResearchFailure("blocked", "deep-research audit request is stale", firstDeepResearchError(requestErr, fmt.Errorf("audit request digest changed")))
		}
		if strings.TrimSpace(asString(input["schema_version"])) != deepResearchAuditV1 || strings.TrimSpace(asString(input["audit_request_sha256"])) != *state.Audit.RequestSHA256 {
			return deepResearchFailure("invalid", "deep-research audit result is not bound to the prepared request", nil)
		}
		status := strings.ToLower(strings.TrimSpace(asString(input["status"])))
		if !deepResearchContains([]string{"accepted", "rejected"}, status) {
			return deepResearchFailure("invalid", "deep-research audit status must be accepted or rejected", nil)
		}
		checks, checksPass, checksErr := deepResearchNormalizeAuditChecks(input["checks"])
		if checksErr != nil {
			return deepResearchFailure("invalid", "deep-research audit checks are invalid", checksErr)
		}
		findings, findingsErr := deepResearchNormalizeAuditFindings(input["findings"])
		if findingsErr != nil {
			return deepResearchFailure("invalid", "deep-research audit findings are invalid", findingsErr)
		}
		canonical := map[string]any{
			"schema_version":       deepResearchAuditV1,
			"generation_id":        manifest.GenerationID,
			"feature_dir":          featureRef,
			"auditor_id":           auditorID,
			"audit_request_ref":    *state.Audit.RequestRef,
			"audit_request_sha256": *state.Audit.RequestSHA256,
			"status":               status,
			"checks":               checks,
			"findings":             findings,
		}
		auditRaw, marshalErr := deepResearchMarshal(canonical)
		if marshalErr != nil {
			return deepResearchFailure("error", "cannot render deep-research audit result", marshalErr)
		}
		auditRef := filepath.ToSlash(filepath.Join(featureRef, "research", deepResearchAuditFilename))
		auditSHA := deepResearchDigest(auditRaw)
		state.Audit.ResultRef = deepResearchStringPointer(auditRef)
		state.Audit.ResultSHA256 = deepResearchStringPointer(auditSHA)
		state.Revision++
		if status == "accepted" && checksPass {
			state.Audit.Status = "accepted"
			state.Phase = "audited"
		} else {
			state.Audit.Status = "rejected"
			state.Status = "blocked"
			state.ClaimStatus = "blocked"
			state.Blockers = []any{map[string]any{
				"category":    "independent_audit",
				"owner":       "deep-research leader",
				"exact_cause": "independent audit rejected the research package",
				"next_action": "/sp.deep-research",
			}}
		}
		updates, updateErr := deepResearchJSONUpdates(map[string]any{
			filepath.Join(root, deepResearchStateFilename): state,
			filepath.Join(root, deepResearchAuditFilename): canonical,
		})
		if updateErr != nil {
			return deepResearchFailure("error", "cannot render deep-research audit artifacts", updateErr)
		}
		if _, transactionErr := applyFileTransaction(service.projectRoot, "deep-research.audit-accept", updates); transactionErr != nil {
			return deepResearchFailure("error", "cannot persist deep-research audit result", transactionErr)
		}
		if state.Audit.Status != "accepted" {
			env := deepResearchFailure("blocked", "deep-research independent audit rejected the package", nil)
			env.Data = deepResearchStateData(state)
			return env
		}
		env := NewEnvelope("ok", "deep-research independent audit accepted")
		env.Data = deepResearchStateData(state)
		env.Data["audit_ref"] = auditRef
		env.Data["audit_sha256"] = auditSHA
		env.NextArgv = service.commandArgv(state, "validate")
		return env
	})
}

func (service deepResearchService) validate(args []string) Envelope {
	featurePath, featureRef, root, _, err := service.resolveFeature(optionValue(args, "--feature-dir", ""))
	if err != nil {
		return deepResearchFailure("usage-error", "deep-research feature is invalid", err)
	}
	return service.withMutationLock(root, func() Envelope {
		state, readErr := deepResearchReadState(root)
		if readErr != nil {
			return deepResearchFailure("blocked", "deep-research state is unavailable", readErr)
		}
		if revisionErr := deepResearchCheckExpectedRevision(args, state, true); revisionErr != nil {
			return deepResearchFailure("blocked", "deep-research revision changed", revisionErr)
		}
		if state.Phase != "audited" || state.Audit.Status != "accepted" {
			return deepResearchFailure("blocked", "deep-research validation requires an accepted independent audit", nil)
		}
		manifest, manifestErr := deepResearchReadManifest(root)
		if manifestErr != nil {
			return deepResearchFailure("blocked", "deep-research track manifest is unavailable", manifestErr)
		}
		if validationErr := service.validateCurrentPackage(featurePath, root, state, manifest, false); validationErr != nil {
			return deepResearchFailure("blocked", "deep-research package failed validation", validationErr)
		}
		state.Phase = "validated"
		state.Status = "validated"
		state.ClaimStatus = "complete"
		state.Blockers = []any{}
		state.Revision++
		manifest.Status = "validated"
		updates, updateErr := deepResearchJSONUpdates(map[string]any{
			filepath.Join(root, deepResearchStateFilename):    state,
			filepath.Join(root, deepResearchManifestFilename): manifest,
		})
		if updateErr != nil {
			return deepResearchFailure("error", "cannot render deep-research validation", updateErr)
		}
		if writeErr := service.applySourceBoundTransaction(featurePath, featureRef, state.Source.SpecSHA256, false, "deep-research.validate", updates); writeErr != nil {
			return deepResearchFailure("error", "cannot persist deep-research validation", writeErr)
		}
		env := NewEnvelope("ok", "deep-research package validated")
		env.Data = deepResearchStateData(state)
		env.NextArgv = service.commandArgv(state, "publish")
		return env
	})
}

func (service deepResearchService) publish(args []string) Envelope {
	featurePath, featureRef, root, _, err := service.resolveFeature(optionValue(args, "--feature-dir", ""))
	if err != nil {
		return deepResearchFailure("usage-error", "deep-research feature is invalid", err)
	}
	return service.withMutationLock(root, func() Envelope {
		state, readErr := deepResearchReadState(root)
		if readErr != nil {
			return deepResearchFailure("blocked", "deep-research state is unavailable", readErr)
		}
		if revisionErr := deepResearchCheckExpectedRevision(args, state, true); revisionErr != nil {
			return deepResearchFailure("blocked", "deep-research revision changed", revisionErr)
		}
		if state.Phase == "published" {
			binding, verifyErr := service.verifyPublishedHandoff(featurePath, featureRef, "", "")
			if verifyErr != nil {
				return deepResearchFailure("blocked", "published deep-research handoff is stale", verifyErr)
			}
			return deepResearchBindingEnvelope("deep-research handoff already published", binding)
		}
		if state.Phase != "validated" || state.ClaimStatus != "complete" {
			return deepResearchFailure("blocked", "deep-research publish requires validated complete research", nil)
		}
		manifest, manifestErr := deepResearchReadManifest(root)
		if manifestErr != nil {
			return deepResearchFailure("blocked", "deep-research track manifest is unavailable", manifestErr)
		}
		if validationErr := service.validateCurrentPackage(featurePath, root, state, manifest, false); validationErr != nil {
			return deepResearchFailure("blocked", "deep-research package failed publication validation", validationErr)
		}
		synthesis, synthesisErr := deepResearchReadObject(filepath.Join(root, deepResearchSynthesisFilename))
		if synthesisErr != nil {
			return deepResearchFailure("blocked", "deep-research synthesis is unavailable", synthesisErr)
		}
		artifactDigests, digestErr := service.currentArtifactDigests(featurePath, state, manifest, synthesis)
		if digestErr != nil {
			return deepResearchFailure("blocked", "deep-research artifacts cannot be fingerprinted", digestErr)
		}
		finalRevision := state.Revision + 1
		handoff := map[string]any{
			"schema_version":     deepResearchHandoffV1,
			"status":             "ready_for_plan",
			"feature_dir":        featureRef,
			"source_spec_ref":    state.Source.SpecRef,
			"source_spec_sha256": state.Source.SpecSHA256,
			"state_revision":     finalRevision,
			"claim_status":       state.ClaimStatus,
			"capability_refs":    append([]string(nil), state.Source.CapabilityRefs...),
			"handoff_ids":        deepResearchSynthesisHandoffIDs(synthesis),
			"artifact_digests":   artifactDigests,
			"next_command":       "/sp.plan",
		}
		handoffRaw, marshalErr := deepResearchMarshal(handoff)
		if marshalErr != nil {
			return deepResearchFailure("error", "cannot render deep-research handoff", marshalErr)
		}
		handoffRef := filepath.ToSlash(filepath.Join(featureRef, "research", deepResearchHandoffFilename))
		handoffSHA := deepResearchDigest(handoffRaw)
		state.Phase = "published"
		state.Status = "published"
		state.Revision = finalRevision
		state.Publication = deepResearchArtifactState{Ref: deepResearchStringPointer(handoffRef), SHA256: deepResearchStringPointer(handoffSHA)}
		manifest.Status = "published"
		updates, updateErr := deepResearchJSONUpdates(map[string]any{
			filepath.Join(root, deepResearchStateFilename):    state,
			filepath.Join(root, deepResearchManifestFilename): manifest,
			filepath.Join(root, deepResearchHandoffFilename):  handoff,
		})
		if updateErr != nil {
			return deepResearchFailure("error", "cannot render deep-research publication", updateErr)
		}
		if transactionErr := service.applySourceBoundTransaction(featurePath, featureRef, state.Source.SpecSHA256, false, "deep-research.publish", updates); transactionErr != nil {
			return deepResearchFailure("error", "cannot publish deep-research handoff", transactionErr)
		}
		binding := deepResearchPublishedBinding{
			HandoffRef:      handoffRef,
			HandoffSHA256:   handoffSHA,
			SourceSpecSHA:   state.Source.SpecSHA256,
			StateRevision:   state.Revision,
			ClaimStatus:     state.ClaimStatus,
			HandoffIDs:      deepResearchSynthesisHandoffIDs(synthesis),
			CapabilityRefs:  append([]string(nil), state.Source.CapabilityRefs...),
			ArtifactDigests: artifactDigests,
		}
		return deepResearchBindingEnvelope("deep-research handoff published", binding)
	})
}

func (service deepResearchService) verifyHandoffCommand(args []string) Envelope {
	featurePath, featureRef, _, _, err := service.resolveFeature(optionValue(args, "--feature-dir", ""))
	if err != nil {
		return deepResearchFailure("usage-error", "deep-research feature is invalid", err)
	}
	binding, err := service.verifyPublishedHandoff(
		featurePath,
		featureRef,
		strings.TrimSpace(optionValue(args, "--handoff-ref", "")),
		strings.TrimSpace(optionValue(args, "--expected-sha256", "")),
	)
	if err != nil {
		return deepResearchFailure("blocked", "deep-research handoff verification failed", err)
	}
	return deepResearchBindingEnvelope("deep-research handoff verified", binding)
}

func (service deepResearchService) notNeeded(args []string) Envelope {
	featurePath, featureRef, root, rootRef, err := service.resolveFeature(optionValue(args, "--feature-dir", ""))
	if err != nil {
		return deepResearchFailure("usage-error", "deep-research feature is invalid", err)
	}
	leaderID := strings.TrimSpace(optionValue(args, "--leader-id", ""))
	if !deepResearchWorkerPattern.MatchString(leaderID) {
		return deepResearchFailure("usage-error", "deep-research not-needed requires a valid --leader-id", nil)
	}
	input, err := service.inputObject(args, "--input-json", "deep-research not-needed")
	if err != nil {
		return deepResearchFailure("usage-error", "deep-research not-needed input is invalid", err)
	}
	gate, specRaw, err := deepResearchReadFeasibilityGate(filepath.Join(featurePath, "spec-contract.json"))
	if err != nil {
		return deepResearchFailure("blocked", "specification feasibility gate is unavailable", err)
	}
	if gate.Decision != "required" {
		return deepResearchFailure("blocked", "deep-research is not selected by the specification", fmt.Errorf("spec-contract.json feasibility_gate.decision is %s", gate.Decision))
	}
	if readinessErr := service.requirePlanningReadySource(featurePath, featureRef, gate); readinessErr != nil {
		return deepResearchFailure("blocked", "deep-research source is not ready for the research-to-Plan route", readinessErr)
	}
	dispositions, proofDigests, err := service.normalizeNotNeededDispositions(input["capability_dispositions"], gate.CapabilityRefs)
	if err != nil {
		return deepResearchFailure("invalid", "deep-research not-needed proof is incomplete", err)
	}
	specRef := filepath.ToSlash(filepath.Join(featureRef, "spec-contract.json"))
	specSHA := deepResearchDigest(specRaw)
	generationID := "drg-" + specSHA[:16]
	synthesis := map[string]any{
		"schema_version":            deepResearchSynthesisSchema,
		"generation_id":             generationID,
		"decision":                  "not_needed",
		"source_spec_ref":           specRef,
		"source_spec_sha256":        specSHA,
		"capability_dispositions":   dispositions,
		"planning_handoffs":         []any{},
		"evidence_dispositions":     []any{},
		"contradiction_resolutions": []any{},
		"recommended_next_command":  "/sp.plan",
	}
	synthesisRaw, err := deepResearchMarshal(synthesis)
	if err != nil {
		return deepResearchFailure("error", "cannot render not-needed synthesis", err)
	}
	markdown := deepResearchRenderNotNeeded(dispositions)
	synthesisRef := filepath.ToSlash(filepath.Join(featureRef, "research", deepResearchSynthesisFilename))
	markdownRef := filepath.ToSlash(filepath.Join(featureRef, "deep-research.md"))
	artifactDigests := map[string]string{
		synthesisRef: deepResearchDigest(synthesisRaw),
		markdownRef:  deepResearchDigest(markdown),
	}
	for ref, digest := range proofDigests {
		artifactDigests[ref] = digest
	}
	handoffRef := filepath.ToSlash(filepath.Join(featureRef, "research", deepResearchHandoffFilename))
	handoff := map[string]any{
		"schema_version":     deepResearchHandoffV1,
		"status":             "ready_for_plan",
		"feature_dir":        featureRef,
		"source_spec_ref":    specRef,
		"source_spec_sha256": specSHA,
		"state_revision":     1,
		"claim_status":       "not_needed",
		"capability_refs":    append([]string(nil), gate.CapabilityRefs...),
		"handoff_ids":        []string{},
		"artifact_digests":   artifactDigests,
		"next_command":       "/sp.plan",
	}
	handoffRaw, err := deepResearchMarshal(handoff)
	if err != nil {
		return deepResearchFailure("error", "cannot render not-needed handoff", err)
	}
	handoffSHA := deepResearchDigest(handoffRaw)
	state := deepResearchState{
		SchemaVersion: deepResearchStateSchema,
		Revision:      1,
		FeatureDir:    featureRef,
		ArtifactRoot:  rootRef,
		Mode:          "not-needed",
		Status:        "published",
		Phase:         "published",
		ClaimStatus:   "not_needed",
		Source: deepResearchSource{
			SpecRef:        specRef,
			SpecSHA256:     specSHA,
			CapabilityRefs: append([]string(nil), gate.CapabilityRefs...),
			ReasonRefs:     append([]string(nil), gate.ReasonRefs...),
		},
		ManifestRef:  filepath.ToSlash(filepath.Join(rootRef, deepResearchManifestFilename)),
		AcceptedRefs: []string{},
		Synthesis: deepResearchArtifactState{
			Ref:    deepResearchStringPointer(synthesisRef),
			SHA256: deepResearchStringPointer(deepResearchDigest(synthesisRaw)),
		},
		Audit: deepResearchAuditState{Required: false, Status: "not_required"},
		Publication: deepResearchArtifactState{
			Ref:    deepResearchStringPointer(handoffRef),
			SHA256: deepResearchStringPointer(handoffSHA),
		},
		Blockers: []any{},
	}
	manifest := deepResearchTrackManifest{
		SchemaVersion: deepResearchManifestSchema,
		GenerationID:  generationID,
		Status:        "published",
		LeaderID:      leaderID,
		Tracks:        []deepResearchTrack{},
	}
	return service.withMutationLock(root, func() Envelope {
		if _, statErr := os.Lstat(filepath.Join(root, deepResearchStateFilename)); statErr == nil {
			binding, verifyErr := service.verifyPublishedHandoff(featurePath, featureRef, handoffRef, handoffSHA)
			if verifyErr == nil && binding.ClaimStatus == "not_needed" {
				return deepResearchBindingEnvelope("deep-research not-needed handoff already published", binding)
			}
			return deepResearchFailure("blocked", "deep-research workspace already exists", fmt.Errorf("resume or reinitialize the current workspace instead of replacing it"))
		} else if !errors.Is(statErr, os.ErrNotExist) {
			return deepResearchFailure("error", "cannot inspect deep-research workspace", statErr)
		}
		updates, updateErr := deepResearchJSONAndTextUpdates(map[string]any{
			filepath.Join(root, deepResearchStateFilename):     state,
			filepath.Join(root, deepResearchManifestFilename):  manifest,
			filepath.Join(root, deepResearchSynthesisFilename): synthesis,
			filepath.Join(root, deepResearchHandoffFilename):   handoff,
		}, map[string][]byte{
			filepath.Join(featurePath, "deep-research.md"): markdown,
		})
		if updateErr != nil {
			return deepResearchFailure("error", "cannot render not-needed research artifacts", updateErr)
		}
		if transactionErr := service.applySourceBoundTransaction(featurePath, featureRef, specSHA, false, "deep-research.not-needed", updates); transactionErr != nil {
			return deepResearchFailure("error", "cannot publish not-needed research handoff", transactionErr)
		}
		return deepResearchBindingEnvelope("deep-research not-needed handoff published", deepResearchPublishedBinding{
			HandoffRef:      handoffRef,
			HandoffSHA256:   handoffSHA,
			SourceSpecSHA:   specSHA,
			StateRevision:   1,
			ClaimStatus:     "not_needed",
			HandoffIDs:      []string{},
			CapabilityRefs:  append([]string(nil), gate.CapabilityRefs...),
			ArtifactDigests: artifactDigests,
		})
	})
}

type deepResearchCorpus struct {
	Results            map[string]map[string]any
	TrackResultDigests map[string]string
	EvidenceIDs        []string
	EvidenceDigests    map[string]string
	SpikeRefs          []string
	SpikeDigests       map[string]string
	ContradictionIDs   []string
}

func (service deepResearchService) acceptedCorpus(featurePath string, state deepResearchState, manifest deepResearchTrackManifest) (deepResearchCorpus, error) {
	corpus := deepResearchCorpus{
		Results:            map[string]map[string]any{},
		TrackResultDigests: map[string]string{},
		EvidenceDigests:    map[string]string{},
		SpikeDigests:       map[string]string{},
	}
	evidenceSet := map[string]bool{}
	spikeSet := map[string]bool{}
	contradictionSet := map[string]bool{}
	for _, track := range manifest.Tracks {
		if track.State != "accepted" {
			return corpus, fmt.Errorf("track %s is %s", track.TrackID, track.State)
		}
		result, raw, err := service.readTrackResult(featurePath, track)
		if err != nil {
			return corpus, err
		}
		if deepResearchDigest(raw) != track.ResultSHA256 {
			return corpus, fmt.Errorf("track result %s digest changed", track.TrackID)
		}
		if strings.TrimSpace(asString(result["status"])) != "complete" {
			return corpus, fmt.Errorf("accepted track %s is not complete", track.TrackID)
		}
		if err := service.verifyTrackEvidence(featurePath, state, track, result); err != nil {
			return corpus, err
		}
		corpus.Results[track.TrackID] = result
		corpus.TrackResultDigests[track.ResultRef] = track.ResultSHA256
		for _, evidenceID := range deepResearchStrings(result["evidence_refs"]) {
			if evidenceSet[evidenceID] {
				return corpus, fmt.Errorf("evidence %s is claimed by multiple accepted tracks", evidenceID)
			}
			evidenceSet[evidenceID] = true
			evidenceRef := filepath.ToSlash(filepath.Join(state.FeatureDir, "research-evidence", evidenceID+".json"))
			rawEvidence, err := deepResearchReadRegularProjectFile(service.projectRoot, evidenceRef)
			if err != nil {
				return corpus, err
			}
			corpus.EvidenceDigests[evidenceRef] = deepResearchDigest(rawEvidence)
		}
		for _, spikeRef := range deepResearchStrings(result["spike_refs"]) {
			canonical := deepResearchCanonicalSpikeRef(state.FeatureDir, spikeRef)
			spikeSet[canonical] = true
			rawSpike, err := deepResearchReadRegularProjectFile(service.projectRoot, canonical)
			if err != nil {
				return corpus, err
			}
			corpus.SpikeDigests[canonical] = deepResearchDigest(rawSpike)
		}
		for _, contradiction := range deepResearchObjectSlice(result["contradictions"]) {
			contradictionID := strings.TrimSpace(asString(contradiction["contradiction_id"]))
			if contradictionSet[contradictionID] {
				return corpus, fmt.Errorf("contradiction %s is duplicated across tracks", contradictionID)
			}
			contradictionSet[contradictionID] = true
		}
	}
	corpus.EvidenceIDs = deepResearchSortedKeys(evidenceSet)
	corpus.SpikeRefs = deepResearchSortedKeys(spikeSet)
	corpus.ContradictionIDs = deepResearchSortedKeys(contradictionSet)
	return corpus, nil
}

func deepResearchNormalizeSynthesis(state deepResearchState, manifest deepResearchTrackManifest, corpus deepResearchCorpus, payload map[string]any) (map[string]any, error) {
	dispositionsRaw, ok := payload["capability_dispositions"].([]any)
	if !ok || len(dispositionsRaw) == 0 {
		return nil, fmt.Errorf("capability_dispositions must be non-empty")
	}
	capabilitySet := deepResearchStringSet(state.Source.CapabilityRefs)
	dispositionByCapability := map[string]map[string]any{}
	for index, raw := range dispositionsRaw {
		row, rowOK := raw.(map[string]any)
		if !rowOK {
			return nil, fmt.Errorf("capability_dispositions[%d] must be an object", index)
		}
		capabilityRef := strings.TrimSpace(asString(row["capability_ref"]))
		disposition := strings.ToLower(strings.TrimSpace(asString(row["disposition"])))
		if !capabilitySet[capabilityRef] || dispositionByCapability[capabilityRef] != nil {
			return nil, fmt.Errorf("capability disposition %s is unknown or duplicated", capabilityRef)
		}
		if !deepResearchContains([]string{"plannable", "constrained_but_plannable"}, disposition) {
			return nil, fmt.Errorf("capability %s is not ready for Plan: %s", capabilityRef, disposition)
		}
		reasonRefs, err := deepResearchStrictStrings(row["reason_refs"], "capability reason_refs", true)
		if err != nil || !deepResearchRefsKnown(reasonRefs, corpus) {
			return nil, firstDeepResearchError(err, fmt.Errorf("capability %s has unknown reason refs", capabilityRef))
		}
		dispositionByCapability[capabilityRef] = map[string]any{
			"capability_ref": capabilityRef,
			"disposition":    disposition,
			"reason_refs":    reasonRefs,
		}
	}
	if len(dispositionByCapability) != len(capabilitySet) {
		return nil, fmt.Errorf("every selected capability requires exactly one disposition")
	}

	handoffsRaw, ok := payload["planning_handoffs"].([]any)
	if !ok || len(handoffsRaw) == 0 {
		return nil, fmt.Errorf("planning_handoffs must be non-empty")
	}
	handoffByID := map[string]map[string]any{}
	coveredCapabilities := map[string]bool{}
	usedSpikes := map[string]bool{}
	for index, raw := range handoffsRaw {
		row, rowOK := raw.(map[string]any)
		if !rowOK {
			return nil, fmt.Errorf("planning_handoffs[%d] must be an object", index)
		}
		handoffID := strings.ToUpper(strings.TrimSpace(asString(row["handoff_id"])))
		status := strings.ToLower(strings.TrimSpace(asString(row["status"])))
		decision := strings.TrimSpace(asString(row["decision"]))
		if !deepResearchHandoffPattern.MatchString(handoffID) || handoffByID[handoffID] != nil {
			return nil, fmt.Errorf("planning handoff id is invalid or duplicated: %s", handoffID)
		}
		if !deepResearchContains([]string{"mandatory", "optional", "user-decision"}, status) || decision == "" {
			return nil, fmt.Errorf("planning handoff %s requires status and decision", handoffID)
		}
		capabilityRefs, err := deepResearchStrictStrings(row["capability_refs"], "handoff capability_refs", true)
		if err != nil || !deepResearchStringSubset(capabilityRefs, state.Source.CapabilityRefs) {
			return nil, firstDeepResearchError(err, fmt.Errorf("handoff %s references unknown capabilities", handoffID))
		}
		evidenceRefs, err := deepResearchStrictStrings(row["evidence_refs"], "handoff evidence_refs", false)
		if err != nil || !deepResearchStringSubset(evidenceRefs, corpus.EvidenceIDs) {
			return nil, firstDeepResearchError(err, fmt.Errorf("handoff %s references unknown evidence", handoffID))
		}
		spikeRefs, err := deepResearchStrictStrings(row["spike_refs"], "handoff spike_refs", false)
		if err != nil {
			return nil, err
		}
		canonicalSpikes := make([]string, 0, len(spikeRefs))
		for _, ref := range spikeRefs {
			canonical := deepResearchCanonicalSpikeRef(state.FeatureDir, ref)
			if !deepResearchContains(corpus.SpikeRefs, canonical) {
				return nil, fmt.Errorf("handoff %s references unknown spike %s", handoffID, ref)
			}
			canonicalSpikes = append(canonicalSpikes, canonical)
			usedSpikes[canonical] = true
		}
		if len(evidenceRefs)+len(canonicalSpikes) == 0 {
			return nil, fmt.Errorf("handoff %s has no evidence or spike", handoffID)
		}
		constraints, err := deepResearchOptionalStrings(row["constraints"], "handoff constraints")
		if err != nil {
			return nil, err
		}
		risks, err := deepResearchOptionalStrings(row["risks"], "handoff risks")
		if err != nil {
			return nil, err
		}
		rejectedOptions, err := deepResearchOptionalStrings(row["rejected_options"], "handoff rejected_options")
		if err != nil {
			return nil, err
		}
		validation, err := deepResearchStrictStrings(row["validation"], "handoff validation", true)
		if err != nil {
			return nil, err
		}
		for _, capabilityRef := range capabilityRefs {
			coveredCapabilities[capabilityRef] = true
		}
		handoffByID[handoffID] = map[string]any{
			"handoff_id":       handoffID,
			"capability_refs":  capabilityRefs,
			"status":           status,
			"decision":         decision,
			"evidence_refs":    evidenceRefs,
			"spike_refs":       canonicalSpikes,
			"constraints":      constraints,
			"risks":            risks,
			"rejected_options": rejectedOptions,
			"validation":       validation,
		}
	}
	if !deepResearchSameStringSet(deepResearchSortedKeys(coveredCapabilities), state.Source.CapabilityRefs) {
		return nil, fmt.Errorf("every plannable capability must map to at least one PH handoff")
	}
	if !deepResearchSameStringSet(deepResearchSortedKeys(usedSpikes), corpus.SpikeRefs) {
		return nil, fmt.Errorf("every accepted spike must be consumed by a planning handoff")
	}

	evidenceDispositionsRaw, ok := payload["evidence_dispositions"].([]any)
	if !ok {
		return nil, fmt.Errorf("evidence_dispositions must be an array")
	}
	evidenceDispositionByID := map[string]map[string]any{}
	for index, raw := range evidenceDispositionsRaw {
		row, rowOK := raw.(map[string]any)
		if !rowOK {
			return nil, fmt.Errorf("evidence_dispositions[%d] must be an object", index)
		}
		evidenceRef := strings.ToUpper(strings.TrimSpace(asString(row["evidence_ref"])))
		disposition := strings.ToLower(strings.TrimSpace(asString(row["disposition"])))
		reason := strings.TrimSpace(asString(row["reason"]))
		if !deepResearchContains(corpus.EvidenceIDs, evidenceRef) || evidenceDispositionByID[evidenceRef] != nil {
			return nil, fmt.Errorf("evidence disposition %s is unknown or duplicated", evidenceRef)
		}
		if !deepResearchContains([]string{"consumed", "deferred", "excluded"}, disposition) || reason == "" {
			return nil, fmt.Errorf("evidence %s disposition or reason is invalid", evidenceRef)
		}
		handoffRefs, err := deepResearchStrictStrings(row["handoff_refs"], "evidence handoff_refs", disposition == "consumed")
		if err != nil {
			return nil, err
		}
		for _, handoffRef := range handoffRefs {
			if handoffByID[handoffRef] == nil {
				return nil, fmt.Errorf("evidence %s references unknown handoff %s", evidenceRef, handoffRef)
			}
		}
		evidenceDispositionByID[evidenceRef] = map[string]any{
			"evidence_ref": evidenceRef,
			"disposition":  disposition,
			"handoff_refs": handoffRefs,
			"reason":       reason,
		}
	}
	if len(evidenceDispositionByID) != len(corpus.EvidenceIDs) {
		return nil, fmt.Errorf("every accepted evidence object requires a disposition")
	}

	resolutionsRaw, ok := payload["contradiction_resolutions"].([]any)
	if !ok {
		return nil, fmt.Errorf("contradiction_resolutions must be an array")
	}
	resolutionByID := map[string]map[string]any{}
	for index, raw := range resolutionsRaw {
		row, rowOK := raw.(map[string]any)
		if !rowOK {
			return nil, fmt.Errorf("contradiction_resolutions[%d] must be an object", index)
		}
		contradictionID := strings.ToUpper(strings.TrimSpace(asString(row["contradiction_id"])))
		resolution := strings.TrimSpace(asString(row["resolution"]))
		if !deepResearchContains(corpus.ContradictionIDs, contradictionID) || resolutionByID[contradictionID] != nil || resolution == "" {
			return nil, fmt.Errorf("contradiction resolution %s is unknown, duplicated, or empty", contradictionID)
		}
		evidenceRefs, err := deepResearchStrictStrings(row["evidence_refs"], "contradiction evidence_refs", true)
		if err != nil || !deepResearchStringSubset(evidenceRefs, corpus.EvidenceIDs) {
			return nil, firstDeepResearchError(err, fmt.Errorf("contradiction %s references unknown evidence", contradictionID))
		}
		resolutionByID[contradictionID] = map[string]any{
			"contradiction_id": contradictionID,
			"resolution":       resolution,
			"evidence_refs":    evidenceRefs,
		}
	}
	if len(resolutionByID) != len(corpus.ContradictionIDs) {
		return nil, fmt.Errorf("every contradiction requires exactly one resolution")
	}
	if strings.TrimSpace(asString(payload["recommended_next_command"])) != "/sp.plan" {
		return nil, fmt.Errorf("recommended_next_command must be /sp.plan for a plannable package")
	}
	return map[string]any{
		"schema_version":            deepResearchSynthesisSchema,
		"generation_id":             manifest.GenerationID,
		"decision":                  "ready_for_plan",
		"source_spec_ref":           state.Source.SpecRef,
		"source_spec_sha256":        state.Source.SpecSHA256,
		"track_result_digests":      corpus.TrackResultDigests,
		"capability_dispositions":   deepResearchSortedObjectMap(dispositionByCapability, "capability_ref"),
		"planning_handoffs":         deepResearchSortedObjectMap(handoffByID, "handoff_id"),
		"evidence_dispositions":     deepResearchSortedObjectMap(evidenceDispositionByID, "evidence_ref"),
		"contradiction_resolutions": deepResearchSortedObjectMap(resolutionByID, "contradiction_id"),
		"recommended_next_command":  "/sp.plan",
	}, nil
}

func deepResearchNormalizeAuditChecks(value any) ([]any, bool, error) {
	rawChecks, ok := value.([]any)
	if !ok {
		return nil, false, fmt.Errorf("checks must be an array")
	}
	byID := map[string]map[string]any{}
	allPass := true
	for index, raw := range rawChecks {
		row, rowOK := raw.(map[string]any)
		if !rowOK {
			return nil, false, fmt.Errorf("checks[%d] must be an object", index)
		}
		checkID := strings.ToLower(strings.TrimSpace(asString(row["check_id"])))
		status := strings.ToLower(strings.TrimSpace(asString(row["status"])))
		if !deepResearchContains(deepResearchAuditCheckIDs, checkID) || byID[checkID] != nil {
			return nil, false, fmt.Errorf("audit check %s is unknown or duplicated", checkID)
		}
		if status != "pass" && status != "fail" {
			return nil, false, fmt.Errorf("audit check %s status must be pass or fail", checkID)
		}
		evidenceRefs, err := deepResearchOptionalStrings(row["evidence_refs"], "audit evidence_refs")
		if err != nil {
			return nil, false, err
		}
		if status != "pass" {
			allPass = false
		}
		byID[checkID] = map[string]any{
			"check_id":      checkID,
			"status":        status,
			"evidence_refs": evidenceRefs,
		}
	}
	if len(byID) != len(deepResearchAuditCheckIDs) {
		return nil, false, fmt.Errorf("audit must report every required check exactly once")
	}
	return deepResearchSortedObjectMap(byID, "check_id"), allPass, nil
}

func deepResearchNormalizeAuditFindings(value any) ([]any, error) {
	if value == nil {
		return []any{}, nil
	}
	rawFindings, ok := value.([]any)
	if !ok {
		return nil, fmt.Errorf("findings must be an array")
	}
	findings := make([]any, 0, len(rawFindings))
	for index, raw := range rawFindings {
		row, rowOK := raw.(map[string]any)
		if !rowOK {
			return nil, fmt.Errorf("findings[%d] must be an object", index)
		}
		severity := strings.ToLower(strings.TrimSpace(asString(row["severity"])))
		summary := strings.TrimSpace(asString(row["summary"]))
		if !deepResearchContains([]string{"low", "medium", "high", "blocking"}, severity) || summary == "" {
			return nil, fmt.Errorf("findings[%d] requires severity and summary", index)
		}
		findings = append(findings, map[string]any{"severity": severity, "summary": summary})
	}
	return findings, nil
}

func (service deepResearchService) validateCurrentPackage(featurePath, root string, state deepResearchState, manifest deepResearchTrackManifest, allowPlanActive bool) error {
	if err := service.requireFreshSpecWithPlanState(state, allowPlanActive); err != nil {
		return err
	}
	if !deepResearchAllTracksAccepted(manifest) {
		return fmt.Errorf("not every research track is accepted")
	}
	corpus, err := service.acceptedCorpus(featurePath, state, manifest)
	if err != nil {
		return err
	}
	synthesis, err := deepResearchReadObject(filepath.Join(root, deepResearchSynthesisFilename))
	if err != nil {
		return err
	}
	canonical, err := deepResearchNormalizeSynthesis(state, manifest, corpus, synthesis)
	if err != nil {
		return err
	}
	canonicalRaw, err := deepResearchMarshal(canonical)
	if err != nil {
		return err
	}
	storedRaw, err := deepResearchReadRegularFile(filepath.Join(root, deepResearchSynthesisFilename))
	if err != nil {
		return err
	}
	if state.Synthesis.Ref == nil || state.Synthesis.SHA256 == nil || deepResearchDigest(storedRaw) != *state.Synthesis.SHA256 || string(storedRaw) != string(canonicalRaw) {
		return fmt.Errorf("synthesis is not the current canonical closure")
	}
	markdownRaw, err := deepResearchReadRegularFile(filepath.Join(featurePath, "deep-research.md"))
	if err != nil {
		return err
	}
	if string(markdownRaw) != string(deepResearchRenderMarkdown(canonical)) {
		return fmt.Errorf("deep-research.md is stale relative to synthesis.json")
	}
	if state.Audit.Status != "accepted" || state.Audit.RequestRef == nil || state.Audit.RequestSHA256 == nil || state.Audit.ResultRef == nil || state.Audit.ResultSHA256 == nil {
		return fmt.Errorf("independent audit binding is incomplete")
	}
	request, err := deepResearchReadObject(filepath.Join(root, deepResearchAuditRequestFile))
	if err != nil {
		return err
	}
	requestRaw, err := deepResearchReadRegularFile(filepath.Join(root, deepResearchAuditRequestFile))
	if err != nil || deepResearchDigest(requestRaw) != *state.Audit.RequestSHA256 {
		return firstDeepResearchError(err, fmt.Errorf("audit request digest changed"))
	}
	if strings.TrimSpace(asString(request["schema_version"])) != deepResearchAuditRequestV1 ||
		strings.TrimSpace(asString(request["generation_id"])) != manifest.GenerationID ||
		strings.TrimSpace(asString(request["source_spec_sha256"])) != state.Source.SpecSHA256 ||
		strings.TrimSpace(asString(request["synthesis_sha256"])) != *state.Synthesis.SHA256 ||
		!deepResearchStringMapEqual(deepResearchStringMap(request["track_result_digests"]), corpus.TrackResultDigests) ||
		!deepResearchStringMapEqual(deepResearchStringMap(request["evidence_digests"]), corpus.EvidenceDigests) ||
		!deepResearchStringMapEqual(deepResearchStringMap(request["spike_digests"]), corpus.SpikeDigests) {
		return fmt.Errorf("audit request no longer matches the current research package")
	}
	audit, err := deepResearchReadObject(filepath.Join(root, deepResearchAuditFilename))
	if err != nil {
		return err
	}
	auditRaw, err := deepResearchReadRegularFile(filepath.Join(root, deepResearchAuditFilename))
	if err != nil || deepResearchDigest(auditRaw) != *state.Audit.ResultSHA256 {
		return firstDeepResearchError(err, fmt.Errorf("audit result digest changed"))
	}
	if strings.TrimSpace(asString(audit["schema_version"])) != deepResearchAuditV1 ||
		strings.TrimSpace(asString(audit["generation_id"])) != manifest.GenerationID ||
		strings.TrimSpace(asString(audit["audit_request_sha256"])) != *state.Audit.RequestSHA256 ||
		strings.TrimSpace(asString(audit["status"])) != "accepted" ||
		deepResearchContains(deepResearchResearcherIDs(manifest), strings.TrimSpace(asString(audit["auditor_id"]))) {
		return fmt.Errorf("independent audit result is stale or not independent")
	}
	_, checksPass, err := deepResearchNormalizeAuditChecks(audit["checks"])
	if err != nil || !checksPass {
		return firstDeepResearchError(err, fmt.Errorf("independent audit checks did not pass"))
	}
	return nil
}

func (service deepResearchService) currentArtifactDigests(featurePath string, state deepResearchState, manifest deepResearchTrackManifest, synthesis map[string]any) (map[string]string, error) {
	digests := map[string]string{}
	refs := []string{
		filepath.ToSlash(filepath.Join(state.FeatureDir, "deep-research.md")),
		filepath.ToSlash(filepath.Join(state.FeatureDir, "research", deepResearchSynthesisFilename)),
		filepath.ToSlash(filepath.Join(state.FeatureDir, "research", deepResearchAuditRequestFile)),
		filepath.ToSlash(filepath.Join(state.FeatureDir, "research", deepResearchAuditFilename)),
	}
	corpus, err := service.acceptedCorpus(featurePath, state, manifest)
	if err != nil {
		return nil, err
	}
	for ref := range corpus.TrackResultDigests {
		refs = append(refs, ref)
	}
	for ref := range corpus.EvidenceDigests {
		refs = append(refs, ref)
	}
	for ref := range corpus.SpikeDigests {
		refs = append(refs, ref)
	}
	for _, track := range manifest.Tracks {
		for _, rejection := range track.Rejections {
			raw, readErr := deepResearchReadRegularProjectFile(service.projectRoot, rejection.RejectionRef)
			if readErr != nil || deepResearchDigest(raw) != rejection.RejectionSHA256 {
				return nil, firstDeepResearchError(readErr, fmt.Errorf("track rejection %s digest changed", rejection.RejectionRef))
			}
			refs = append(refs, rejection.RejectionRef)
		}
	}
	sort.Strings(refs)
	for _, ref := range refs {
		raw, readErr := deepResearchReadRegularProjectFile(service.projectRoot, ref)
		if readErr != nil {
			return nil, readErr
		}
		digests[ref] = deepResearchDigest(raw)
	}
	return digests, nil
}

func (service deepResearchService) verifyPublishedHandoff(featurePath, featureRef, requestedRef, expectedSHA string) (deepResearchPublishedBinding, error) {
	var binding deepResearchPublishedBinding
	canonicalRef := filepath.ToSlash(filepath.Join(featureRef, "research", deepResearchHandoffFilename))
	if requestedRef == "" {
		requestedRef = canonicalRef
	}
	requestedRef = filepath.ToSlash(strings.TrimSpace(requestedRef))
	if requestedRef != canonicalRef {
		return binding, fmt.Errorf("handoff_ref must be %s", canonicalRef)
	}
	handoffRaw, err := deepResearchReadRegularProjectFile(service.projectRoot, requestedRef)
	if err != nil {
		return binding, err
	}
	handoffSHA := deepResearchDigest(handoffRaw)
	if expectedSHA != "" && (!deepResearchSHA256Pattern.MatchString(expectedSHA) || expectedSHA != handoffSHA) {
		return binding, fmt.Errorf("handoff sha256 is stale")
	}
	var handoff map[string]any
	if err := json.Unmarshal(handoffRaw, &handoff); err != nil || handoff == nil {
		return binding, fmt.Errorf("handoff-to-plan.json must contain a JSON object")
	}
	root := filepath.Join(featurePath, "research")
	state, err := deepResearchReadState(root)
	if err != nil {
		return binding, err
	}
	manifest, err := deepResearchReadManifest(root)
	if err != nil {
		return binding, err
	}
	if state.Phase != "published" || state.Status != "published" || state.Publication.Ref == nil || state.Publication.SHA256 == nil ||
		*state.Publication.Ref != canonicalRef || *state.Publication.SHA256 != handoffSHA {
		return binding, fmt.Errorf("runtime publication state does not match handoff-to-plan.json")
	}
	if err := service.requireFreshSpecWithPlanState(state, true); err != nil {
		return binding, err
	}
	if strings.TrimSpace(asString(handoff["schema_version"])) != deepResearchHandoffV1 ||
		strings.TrimSpace(asString(handoff["status"])) != "ready_for_plan" ||
		strings.TrimSpace(asString(handoff["feature_dir"])) != featureRef ||
		strings.TrimSpace(asString(handoff["source_spec_ref"])) != state.Source.SpecRef ||
		strings.TrimSpace(asString(handoff["source_spec_sha256"])) != state.Source.SpecSHA256 ||
		strings.TrimSpace(asString(handoff["claim_status"])) != state.ClaimStatus ||
		strings.TrimSpace(asString(handoff["next_command"])) != "/sp.plan" {
		return binding, fmt.Errorf("handoff-to-plan.json identity or transition is invalid")
	}
	stateRevision, ok := hookJSONInteger(handoff["state_revision"])
	if !ok || stateRevision != state.Revision {
		return binding, fmt.Errorf("handoff-to-plan.json state_revision is stale")
	}
	capabilityRefs, err := deepResearchStrictStrings(handoff["capability_refs"], "handoff capability_refs", state.ClaimStatus != "not_needed")
	if err != nil || !deepResearchSameStringSet(capabilityRefs, state.Source.CapabilityRefs) {
		return binding, firstDeepResearchError(err, fmt.Errorf("handoff capability refs are stale"))
	}
	handoffIDs, err := deepResearchStrictStrings(handoff["handoff_ids"], "handoff handoff_ids", state.ClaimStatus == "complete")
	if err != nil {
		return binding, err
	}
	if state.ClaimStatus == "not_needed" && len(handoffIDs) != 0 {
		return binding, fmt.Errorf("not-needed handoff must not invent PH ids")
	}
	if state.ClaimStatus == "complete" {
		if err := service.validateCurrentPackage(featurePath, root, state, manifest, true); err != nil {
			return binding, err
		}
		synthesis, readErr := deepResearchReadObject(filepath.Join(root, deepResearchSynthesisFilename))
		if readErr != nil || !deepResearchSameStringSet(handoffIDs, deepResearchSynthesisHandoffIDs(synthesis)) {
			return binding, firstDeepResearchError(readErr, fmt.Errorf("handoff IDs do not match synthesis"))
		}
	} else if state.ClaimStatus != "not_needed" {
		return binding, fmt.Errorf("published claim_status must be complete or not_needed")
	}
	artifactDigests := deepResearchStringMap(handoff["artifact_digests"])
	if len(artifactDigests) == 0 {
		return binding, fmt.Errorf("handoff artifact_digests must not be empty")
	}
	for ref, digest := range artifactDigests {
		if !deepResearchSHA256Pattern.MatchString(digest) {
			return binding, fmt.Errorf("artifact digest for %s is invalid", ref)
		}
		raw, readErr := deepResearchReadRegularProjectFile(service.projectRoot, ref)
		if readErr != nil || deepResearchDigest(raw) != digest {
			return binding, firstDeepResearchError(readErr, fmt.Errorf("artifact %s digest changed", ref))
		}
	}
	return deepResearchPublishedBinding{
		HandoffRef:      canonicalRef,
		HandoffSHA256:   handoffSHA,
		SourceSpecSHA:   state.Source.SpecSHA256,
		StateRevision:   state.Revision,
		ClaimStatus:     state.ClaimStatus,
		HandoffIDs:      handoffIDs,
		CapabilityRefs:  capabilityRefs,
		ArtifactDigests: artifactDigests,
	}, nil
}

func (service deepResearchService) normalizeNotNeededDispositions(value any, capabilityRefs []string) ([]any, map[string]string, error) {
	rawRows, ok := value.([]any)
	if !ok || len(rawRows) == 0 {
		return nil, nil, fmt.Errorf("capability_dispositions must be non-empty")
	}
	capabilitySet := deepResearchStringSet(capabilityRefs)
	byCapability := map[string]map[string]any{}
	proofDigests := map[string]string{}
	for index, raw := range rawRows {
		row, rowOK := raw.(map[string]any)
		if !rowOK {
			return nil, nil, fmt.Errorf("capability_dispositions[%d] must be an object", index)
		}
		capabilityRef := strings.TrimSpace(asString(row["capability_ref"]))
		reason := strings.TrimSpace(asString(row["reason"]))
		if !capabilitySet[capabilityRef] || byCapability[capabilityRef] != nil || reason == "" {
			return nil, nil, fmt.Errorf("not-needed capability %s is unknown, duplicated, or missing a reason", capabilityRef)
		}
		evidenceRefs, err := deepResearchStrictStrings(row["evidence_refs"], "not-needed evidence_refs", true)
		if err != nil {
			return nil, nil, err
		}
		canonicalRefs := make([]string, 0, len(evidenceRefs))
		for _, ref := range evidenceRefs {
			normalized, normalizeErr := service.normalizedProjectPath(ref, false, true)
			if normalizeErr != nil {
				return nil, nil, normalizeErr
			}
			rawProof, readErr := deepResearchReadRegularProjectFile(service.projectRoot, normalized)
			if readErr != nil {
				return nil, nil, readErr
			}
			canonicalRefs = append(canonicalRefs, normalized)
			proofDigests[normalized] = deepResearchDigest(rawProof)
		}
		byCapability[capabilityRef] = map[string]any{
			"capability_ref": capabilityRef,
			"disposition":    "not_needed",
			"reason":         reason,
			"evidence_refs":  canonicalRefs,
		}
	}
	if len(byCapability) != len(capabilitySet) {
		return nil, nil, fmt.Errorf("every selected capability requires evidence-backed not-needed disposition")
	}
	return deepResearchSortedObjectMap(byCapability, "capability_ref"), proofDigests, nil
}

func (service deepResearchService) resolveFeature(featureDir string) (string, string, string, string, error) {
	featureDir = strings.TrimSpace(featureDir)
	if featureDir == "" {
		return "", "", "", "", fmt.Errorf("--feature-dir is required")
	}
	featureRef, err := service.normalizedProjectPath(featureDir, false, true)
	if err != nil {
		return "", "", "", "", err
	}
	featurePath, err := secureProjectPath(service.projectRoot, featureRef)
	if err != nil {
		return "", "", "", "", err
	}
	info, err := os.Lstat(featurePath)
	if err != nil {
		return "", "", "", "", err
	}
	if info.Mode()&os.ModeSymlink != 0 || !info.IsDir() {
		return "", "", "", "", fmt.Errorf("feature-dir must be a regular project directory")
	}
	rootRef := filepath.ToSlash(filepath.Join(featureRef, "research"))
	root, err := secureProjectPath(service.projectRoot, rootRef)
	if err != nil {
		return "", "", "", "", err
	}
	return featurePath, featureRef, root, rootRef, nil
}

func (service deepResearchService) applySourceBoundTransaction(featurePath, featureRef, expectedSpecSHA string, allowPlanActive bool, kind string, updates []fileTransactionUpdate) error {
	workflowLockRef := filepath.ToSlash(filepath.Join(featureRef, ".workflow.lock"))
	workflowLockPath, err := secureProjectPath(service.projectRoot, workflowLockRef)
	if err != nil {
		return fmt.Errorf("validate source workflow lock: %w", err)
	}
	if info, statErr := os.Lstat(workflowLockPath); statErr == nil && !info.Mode().IsRegular() {
		return fmt.Errorf("source workflow lock %q must be a regular file", workflowLockPath)
	} else if statErr != nil && !errors.Is(statErr, os.ErrNotExist) {
		return fmt.Errorf("inspect source workflow lock: %w", statErr)
	}
	releaseWorkflow, err := filelock.Acquire(workflowLockPath)
	if err != nil {
		return fmt.Errorf("acquire source workflow lock: %w", err)
	}
	defer releaseWorkflow()
	revalidatedLockPath, err := secureProjectPath(service.projectRoot, workflowLockRef)
	if err != nil {
		return fmt.Errorf("revalidate source workflow lock: %w", err)
	}
	if !sameFilesystemPath(workflowLockPath, revalidatedLockPath) {
		return fmt.Errorf("source workflow lock changed during acquisition")
	}
	if info, statErr := os.Lstat(workflowLockPath); statErr != nil || !info.Mode().IsRegular() {
		return fmt.Errorf("source workflow lock %q changed during acquisition", workflowLockPath)
	}

	specPath := filepath.Join(featurePath, "spec-contract.json")
	gate, specRaw, err := deepResearchReadFeasibilityGate(specPath)
	if err != nil {
		return err
	}
	if deepResearchDigest(specRaw) != expectedSpecSHA {
		return fmt.Errorf("spec-contract.json digest changed before %s", kind)
	}
	if err := service.requirePlanningReadySourceWithPlanState(featurePath, featureRef, gate, allowPlanActive); err != nil {
		return err
	}
	preconditions := []fileTransactionPrecondition{{Path: specPath, ExpectedSHA256: expectedSpecSHA}}
	workflowPath := filepath.Join(featurePath, "workflow.json")
	workflowRaw, workflowErr := os.ReadFile(workflowPath)
	if workflowErr == nil {
		preconditions = append(preconditions, fileTransactionPrecondition{Path: workflowPath, ExpectedSHA256: fileContentSHA256(workflowRaw)})
	} else if errors.Is(workflowErr, os.ErrNotExist) {
		preconditions = append(preconditions, fileTransactionPrecondition{Path: workflowPath, MustNotExist: true})
	} else {
		return workflowErr
	}
	if service.beforeSourceBoundMutation != nil {
		if err := service.beforeSourceBoundMutation(); err != nil {
			return err
		}
	}
	if _, err := applyFileTransactionWithPreconditions(service.projectRoot, kind, updates, preconditions); err != nil {
		currentGate, _, readErr := deepResearchReadFeasibilityGate(specPath)
		if readErr == nil {
			if readinessErr := service.requirePlanningReadySourceWithPlanState(featurePath, featureRef, currentGate, allowPlanActive); readinessErr != nil {
				return readinessErr
			}
		}
		return err
	}
	return nil
}

func (service deepResearchService) withMutationLock(root string, action func() Envelope) Envelope {
	projectRoot, err := filepath.Abs(service.projectRoot)
	if err != nil {
		return deepResearchFailure("error", "cannot resolve project root", err)
	}
	lockDir, err := secureProjectPath(projectRoot, ".specify/runtime/deep-research/locks")
	if err != nil {
		return deepResearchFailure("error", "cannot resolve deep-research lock directory", err)
	}
	if err := os.MkdirAll(lockDir, 0o755); err != nil {
		return deepResearchFailure("error", "cannot create deep-research lock directory", err)
	}
	lockName := deepResearchDigest([]byte(filepath.Clean(root)))[:24] + ".lock"
	lockPath, err := secureProjectPath(projectRoot, filepath.ToSlash(filepath.Join(".specify", "runtime", "deep-research", "locks", lockName)))
	if err != nil {
		return deepResearchFailure("error", "cannot resolve deep-research lock", err)
	}
	release, err := filelock.Acquire(lockPath)
	if err != nil {
		return deepResearchFailure("blocked", "cannot acquire deep-research workflow lock", err)
	}
	defer release()
	return action()
}

func (service deepResearchService) inputObject(args []string, flag, label string) (map[string]any, error) {
	if !hasFlag(args, flag) || strings.TrimSpace(optionValue(args, flag, "")) == "" {
		return nil, fmt.Errorf("%s requires %s", label, flag)
	}
	raw, err := resolveAgentJSONInputBytes(optionValue(args, flag, ""), service.projectRoot, label)
	if err != nil {
		return nil, err
	}
	var payload map[string]any
	if err := json.Unmarshal(raw, &payload); err != nil || payload == nil {
		return nil, firstDeepResearchError(err, fmt.Errorf("%s must contain a JSON object", flag))
	}
	return payload, nil
}

func (service deepResearchService) normalizedProjectPathList(value any, label string, allowDot bool) ([]string, error) {
	values, err := deepResearchStrictStrings(value, label, false)
	if err != nil {
		return nil, err
	}
	out := make([]string, 0, len(values))
	seen := map[string]bool{}
	for _, value := range values {
		normalized, normalizeErr := service.normalizedProjectPath(value, allowDot, false)
		if normalizeErr != nil {
			return nil, fmt.Errorf("%s contains invalid path %q: %w", label, value, normalizeErr)
		}
		if !seen[normalized] {
			seen[normalized] = true
			out = append(out, normalized)
		}
	}
	sort.Strings(out)
	return out, nil
}

func (service deepResearchService) normalizedProjectPath(value string, allowDot, requireExists bool) (string, error) {
	value = strings.TrimSpace(value)
	if value == "" {
		return "", fmt.Errorf("project path is required")
	}
	root, err := filepath.Abs(service.projectRoot)
	if err != nil {
		return "", err
	}
	var candidate string
	if filepath.IsAbs(value) {
		candidate, err = filepath.Abs(value)
	} else {
		candidate, err = secureProjectPath(root, filepath.ToSlash(filepath.Clean(filepath.FromSlash(value))))
	}
	if err != nil {
		return "", err
	}
	relative, err := filepath.Rel(root, candidate)
	if err != nil || relative == ".." || strings.HasPrefix(relative, ".."+string(filepath.Separator)) {
		return "", fmt.Errorf("path must stay inside the project root")
	}
	relative = filepath.ToSlash(relative)
	if relative == "." && !allowDot {
		return "", fmt.Errorf("project root is not a valid file reference")
	}
	if relative == ".git" || strings.HasPrefix(relative, ".git/") {
		return "", fmt.Errorf(".git is outside the deep-research boundary")
	}
	secured, err := secureProjectPath(root, relative)
	if err != nil {
		return "", err
	}
	if requireExists {
		if _, err := os.Lstat(secured); err != nil {
			return "", err
		}
	}
	return relative, nil
}

func (service deepResearchService) projectRelativePath(ref string) (string, error) {
	normalized, err := service.normalizedProjectPath(ref, false, true)
	if err != nil {
		return "", err
	}
	return secureProjectPath(service.projectRoot, normalized)
}

func (service deepResearchService) parseTrack(row map[string]any, state deepResearchState) (deepResearchTrack, error) {
	var track deepResearchTrack
	track.TrackID = strings.ToUpper(strings.TrimSpace(asString(row["track_id"])))
	track.Title = strings.TrimSpace(asString(row["title"]))
	track.CompletionSignal = strings.TrimSpace(asString(row["completion_signal"]))
	if !deepResearchTrackIDPattern.MatchString(track.TrackID) || track.Title == "" || track.CompletionSignal == "" {
		return track, fmt.Errorf("track_id, title, and completion_signal are required")
	}
	capabilityRefs, err := deepResearchStrictStrings(row["capability_refs"], "track capability_refs", true)
	if err != nil || !deepResearchStringSubset(capabilityRefs, state.Source.CapabilityRefs) {
		return track, firstDeepResearchError(err, fmt.Errorf("track capability_refs escape the selected feasibility gate"))
	}
	readPaths, err := service.normalizedProjectPathList(row["read_paths"], "track read_paths", true)
	if err != nil || len(readPaths) == 0 {
		return track, firstDeepResearchError(err, fmt.Errorf("track read_paths must not be empty"))
	}
	questions, err := deepResearchStrictStrings(row["questions"], "track questions", true)
	if err != nil {
		return track, err
	}
	sourceClasses, err := deepResearchStrictStrings(row["source_classes"], "track source_classes", true)
	if err != nil {
		return track, err
	}
	for _, sourceClass := range sourceClasses {
		if !deepResearchContains([]string{"repository", "primary_external", "secondary_external", "experiment"}, sourceClass) {
			return track, fmt.Errorf("unsupported source class %s", sourceClass)
		}
		if state.Mode == "repo-only" && strings.Contains(sourceClass, "external") {
			return track, fmt.Errorf("repo-only mode cannot prepare external source tracks")
		}
	}
	requiresSpike, ok := row["requires_spike"].(bool)
	if !ok {
		return track, fmt.Errorf("requires_spike must be a boolean")
	}
	track.State = "pending"
	track.CapabilityRefs = capabilityRefs
	track.ReadPaths = readPaths
	track.Questions = questions
	track.SourceClasses = sourceClasses
	track.RequiresSpike = requiresSpike
	track.Rejections = []deepResearchTrackRejection{}
	return track, nil
}

func (service deepResearchService) requireFreshSpec(state deepResearchState) error {
	return service.requireFreshSpecWithPlanState(state, false)
}

func (service deepResearchService) requireFreshSpecWithPlanState(state deepResearchState, allowPlanActive bool) error {
	raw, err := deepResearchReadRegularProjectFile(service.projectRoot, state.Source.SpecRef)
	if err != nil {
		return err
	}
	if deepResearchDigest(raw) != state.Source.SpecSHA256 {
		return fmt.Errorf("spec-contract.json digest changed after deep-research initialization")
	}
	gate, _, err := deepResearchReadFeasibilityGate(filepath.Join(service.projectRoot, filepath.FromSlash(state.Source.SpecRef)))
	if err != nil {
		return err
	}
	if gate.Decision != "required" || !deepResearchSameStringSet(gate.CapabilityRefs, state.Source.CapabilityRefs) {
		return fmt.Errorf("specification feasibility gate changed after deep-research initialization")
	}
	featurePath := filepath.Dir(filepath.Join(service.projectRoot, filepath.FromSlash(state.Source.SpecRef)))
	return service.requirePlanningReadySourceWithPlanState(featurePath, state.FeatureDir, gate, allowPlanActive)
}

func (service deepResearchService) requirePlanningReadySource(featurePath, featureRef string, gate deepResearchFeasibilityGate) error {
	return service.requirePlanningReadySourceWithPlanState(featurePath, featureRef, gate, false)
}

func (service deepResearchService) requirePlanningReadySourceWithPlanState(featurePath, featureRef string, gate deepResearchFeasibilityGate, allowPlanActive bool) error {
	if gate.SpecStatus != "planning-ready" {
		return &deepResearchSourceReadinessError{
			Code: "source_spec_not_planning_ready", FeatureRef: featureRef, SpecStatus: gate.SpecStatus,
			OwnerWorkflow: "/sp.specify", Owner: "agent", HumanActionRequired: false,
			ResolutionAction: map[string]any{
				"kind": "return-to-source-owner", "owner_workflow": "/sp.specify",
				"next_action":      "run Specify against the existing feature and make spec-contract.json planning-ready without discarding accepted research or Design evidence",
				"unblock_criteria": "spec-contract.json status is planning-ready and its required Specify workflow state is no longer blocked",
			},
			Message: fmt.Sprintf("spec-contract.json status is %q; deep-research requires planning-ready source truth", gate.SpecStatus),
		}
	}
	workflowPath := filepath.Join(featurePath, "workflow.json")
	if _, err := os.Lstat(workflowPath); errors.Is(err, os.ErrNotExist) {
		return nil
	} else if err != nil {
		return &deepResearchSourceReadinessError{
			Code: "source_workflow_unavailable", FeatureRef: featureRef, SpecStatus: gate.SpecStatus,
			OwnerWorkflow: "/sp.specify", Owner: "agent", HumanActionRequired: false,
			Message: fmt.Sprintf("inspect source workflow state: %v", err),
		}
	}
	shown := NewWorkflowService(service.projectRoot).Show(WorkflowShowRequest{FeatureDir: featureRef})
	stage := strings.ToLower(strings.TrimSpace(asString(shown.Data["stage"])))
	status := strings.ToLower(strings.TrimSpace(asString(shown.Data["status"])))
	if shown.Status == "ok" && (stage == "specify" && status == "completed" || allowPlanActive && stage == "plan" && status == "active") {
		return nil
	}
	code := "source_workflow_not_plan_enterable"
	if shown.Status == "blocked" && status == "blocked" {
		code = "source_workflow_blocked"
	}
	ownerWorkflow := "/sp.specify"
	if stage != "" {
		ownerWorkflow = "/sp." + stage
	}
	owner := "agent"
	humanRequired := false
	if len(shown.Blockers) > 0 {
		if blocker, ok := shown.Blockers[0].(map[string]any); ok {
			if value := strings.TrimSpace(asString(blocker["owner"])); value != "" {
				owner = value
			}
			humanRequired, _ = blocker["human_action_required"].(bool)
		}
	}
	resolutionAction := shown.Data["resolution_action"]
	if resolutionAction == nil {
		resolutionAction = map[string]any{
			"kind": "return-to-source-owner", "owner_workflow": ownerWorkflow,
			"show_argv": stringValuesAsAny(shown.ShowArgv), "next_argv": stringValuesAsAny(shown.NextArgv),
			"unblock_criteria": "workflow show permits entering or resuming Plan without a persisted blocker",
		}
	}
	return &deepResearchSourceReadinessError{
		Code: code, FeatureRef: featureRef, SpecStatus: gate.SpecStatus,
		WorkflowStage: stage, WorkflowStatus: status, OwnerWorkflow: ownerWorkflow,
		Owner: owner, HumanActionRequired: humanRequired, ResolutionAction: resolutionAction,
		Details: append([]any(nil), shown.Blockers...),
		Message: fmt.Sprintf("workflow state %s/%s cannot produce an executable /sp.plan handoff", stage, status),
	}
}

func (service deepResearchService) writeStateAndManifest(root string, state deepResearchState, manifest deepResearchTrackManifest, kind string) error {
	updates, err := deepResearchJSONUpdates(map[string]any{
		filepath.Join(root, deepResearchStateFilename):    state,
		filepath.Join(root, deepResearchManifestFilename): manifest,
	})
	if err != nil {
		return err
	}
	_, err = applyFileTransaction(service.projectRoot, kind, updates)
	return err
}

func (service deepResearchService) commandArgv(state deepResearchState, subcommand string) []string {
	argv := []string{"specify-runtime", "deep-research", subcommand, "--feature-dir", state.FeatureDir}
	if deepResearchContains([]string{"track-prepare", "track-lease", "track-submit", "track-reject", "track-accept", "track-yield", "synthesize", "audit-prepare", "audit-accept", "validate", "publish"}, subcommand) {
		argv = append(argv, "--expected-revision", strconv.Itoa(state.Revision))
	}
	return append(argv, "--format", "json")
}

func deepResearchReadState(root string) (deepResearchState, error) {
	var state deepResearchState
	raw, err := deepResearchReadRegularFile(filepath.Join(root, deepResearchStateFilename))
	if err != nil {
		return state, err
	}
	if err := json.Unmarshal(raw, &state); err != nil {
		return state, err
	}
	if state.SchemaVersion != deepResearchStateSchema || state.Revision < 1 || state.FeatureDir == "" || state.ArtifactRoot == "" || state.ManifestRef == "" {
		return state, fmt.Errorf("state.json has an unsupported deep-research runtime contract")
	}
	if !deepResearchContains([]string{"scoped", "researching", "synthesized", "audit", "audited", "validated", "published"}, state.Phase) {
		return state, fmt.Errorf("state.json has an invalid phase")
	}
	if state.Source.SpecRef == "" || !deepResearchSHA256Pattern.MatchString(state.Source.SpecSHA256) {
		return state, fmt.Errorf("state.json has an invalid specification binding")
	}
	if state.AcceptedRefs == nil {
		state.AcceptedRefs = []string{}
	}
	if state.Blockers == nil {
		state.Blockers = []any{}
	}
	return state, nil
}

func deepResearchReadManifest(root string) (deepResearchTrackManifest, error) {
	var manifest deepResearchTrackManifest
	raw, err := deepResearchReadRegularFile(filepath.Join(root, deepResearchManifestFilename))
	if err != nil {
		return manifest, err
	}
	if err := json.Unmarshal(raw, &manifest); err != nil {
		return manifest, err
	}
	if manifest.SchemaVersion != deepResearchManifestSchema || strings.TrimSpace(manifest.GenerationID) == "" || !deepResearchWorkerPattern.MatchString(manifest.LeaderID) {
		return manifest, fmt.Errorf("track-manifest.json has an unsupported deep-research runtime contract")
	}
	if manifest.Tracks == nil {
		manifest.Tracks = []deepResearchTrack{}
	}
	seen := map[string]bool{}
	for index := range manifest.Tracks {
		track := manifest.Tracks[index]
		if !deepResearchTrackIDPattern.MatchString(track.TrackID) || seen[track.TrackID] {
			return manifest, fmt.Errorf("track-manifest.json contains an invalid or duplicate track id")
		}
		seen[track.TrackID] = true
		if track.Rejections == nil {
			track.Rejections = []deepResearchTrackRejection{}
		}
		seenAttempts := map[string]bool{}
		for _, rejection := range track.Rejections {
			if !deepResearchAttemptIDPattern.MatchString(rejection.AttemptID) ||
				!deepResearchWorkerPattern.MatchString(rejection.WorkerID) ||
				!deepResearchSHA256Pattern.MatchString(rejection.ResultSHA256) ||
				!deepResearchSHA256Pattern.MatchString(rejection.RejectionSHA256) ||
				strings.TrimSpace(rejection.ResultRef) == "" ||
				strings.TrimSpace(rejection.RejectionRef) == "" ||
				strings.TrimSpace(rejection.Reason) == "" || seenAttempts[rejection.AttemptID] {
				return manifest, fmt.Errorf("track-manifest.json contains an invalid or duplicate rejection")
			}
			seenAttempts[rejection.AttemptID] = true
		}
		manifest.Tracks[index] = track
	}
	return manifest, nil
}

func deepResearchReadFeasibilityGate(path string) (deepResearchFeasibilityGate, []byte, error) {
	var gate deepResearchFeasibilityGate
	raw, err := deepResearchReadRegularFile(path)
	if err != nil {
		return gate, nil, err
	}
	var spec map[string]any
	if err := json.Unmarshal(raw, &spec); err != nil || spec == nil {
		return gate, nil, firstDeepResearchError(err, fmt.Errorf("spec-contract.json must contain a JSON object"))
	}
	gate.SpecStatus = strings.ToLower(strings.TrimSpace(asString(spec["status"])))
	payload, ok := spec["feasibility_gate"].(map[string]any)
	if !ok {
		return gate, nil, fmt.Errorf("spec-contract.json is missing feasibility_gate")
	}
	gate.Decision = strings.ToLower(strings.TrimSpace(asString(payload["decision"])))
	if !deepResearchContains([]string{"required", "not_selected"}, gate.Decision) {
		return gate, nil, fmt.Errorf("feasibility_gate.decision must be required or not_selected")
	}
	capabilityRefs, err := deepResearchStrictStrings(payload["capability_refs"], "feasibility_gate.capability_refs", gate.Decision == "required")
	if err != nil {
		return gate, nil, err
	}
	for _, capabilityRef := range capabilityRefs {
		if !deepResearchCapabilityPattern.MatchString(capabilityRef) {
			return gate, nil, fmt.Errorf("invalid feasibility capability ref %s", capabilityRef)
		}
	}
	if gate.Decision == "not_selected" && len(capabilityRefs) != 0 {
		return gate, nil, fmt.Errorf("not_selected feasibility gate cannot carry capability refs")
	}
	reasonRefs, err := deepResearchOptionalStrings(payload["reason_refs"], "feasibility_gate.reason_refs")
	if err != nil {
		return gate, nil, err
	}
	gate.CapabilityRefs = capabilityRefs
	gate.ReasonRefs = reasonRefs
	return gate, raw, nil
}

func deepResearchCheckExpectedRevision(args []string, state deepResearchState, required bool) error {
	raw := strings.TrimSpace(optionValue(args, "--expected-revision", ""))
	if raw == "" {
		if required {
			return fmt.Errorf("--expected-revision is required for this mutation")
		}
		return nil
	}
	expected, err := strconv.Atoi(raw)
	if err != nil || expected < 1 {
		return fmt.Errorf("--expected-revision must be a positive integer")
	}
	if expected != state.Revision {
		return fmt.Errorf("expected revision %d but current revision is %d", expected, state.Revision)
	}
	return nil
}

func deepResearchStateData(state deepResearchState) map[string]any {
	return map[string]any{
		"revision":             state.Revision,
		"feature_dir":          state.FeatureDir,
		"artifact_root":        state.ArtifactRoot,
		"mode":                 state.Mode,
		"status":               state.Status,
		"phase":                state.Phase,
		"claim_status":         state.ClaimStatus,
		"source_spec_ref":      state.Source.SpecRef,
		"source_spec_sha256":   state.Source.SpecSHA256,
		"capability_refs":      append([]string(nil), state.Source.CapabilityRefs...),
		"accepted_result_refs": append([]string(nil), state.AcceptedRefs...),
		"blockers":             append([]any(nil), state.Blockers...),
	}
}

func deepResearchTrackCounts(manifest deepResearchTrackManifest) map[string]any {
	counts := map[string]any{"total": len(manifest.Tracks)}
	for _, state := range []string{"pending", "leased", "submitted", "submitted-blocked", "accepted", "blocked"} {
		counts[state] = 0
	}
	for _, track := range manifest.Tracks {
		value, _ := counts[track.State].(int)
		counts[track.State] = value + 1
	}
	return counts
}

func deepResearchNextSubcommand(state deepResearchState, manifest deepResearchTrackManifest) string {
	if state.Status == "blocked" {
		return ""
	}
	switch state.Phase {
	case "scoped":
		return "track-prepare"
	case "researching":
		if deepResearchAllTracksAccepted(manifest) {
			return "synthesize"
		}
		for _, track := range manifest.Tracks {
			if deepResearchContains([]string{"submitted", "submitted-blocked"}, track.State) {
				return "track-accept"
			}
		}
		for _, track := range manifest.Tracks {
			if track.State == "leased" {
				return "track-submit"
			}
		}
		for _, track := range manifest.Tracks {
			if track.State == "pending" {
				return "track-lease"
			}
		}
		return ""
	case "synthesized":
		return "audit-prepare"
	case "audit":
		return "audit-accept"
	case "audited":
		return "validate"
	case "validated":
		return "publish"
	case "published":
		return "/sp.plan"
	default:
		return ""
	}
}

func deepResearchTrackIDs(manifest deepResearchTrackManifest) []string {
	ids := make([]string, 0, len(manifest.Tracks))
	for _, track := range manifest.Tracks {
		ids = append(ids, track.TrackID)
	}
	sort.Strings(ids)
	return ids
}

func deepResearchFindTrack(manifest deepResearchTrackManifest, trackID string) int {
	for index := range manifest.Tracks {
		if manifest.Tracks[index].TrackID == trackID {
			return index
		}
	}
	return -1
}

func deepResearchNextAttemptID(manifest deepResearchTrackManifest) string {
	next := 1
	for _, track := range manifest.Tracks {
		next += track.AttemptNumber
	}
	return fmt.Sprintf("ATTEMPT-%03d", next)
}

func deepResearchTrackPacket(track deepResearchTrack, state deepResearchState) map[string]any {
	return map[string]any{
		"protocol":          deepResearchTrackProtocol,
		"generation_source": state.Source.SpecSHA256,
		"track_id":          track.TrackID,
		"attempt_id":        track.AttemptID,
		"title":             track.Title,
		"capability_refs":   track.CapabilityRefs,
		"read_paths":        track.ReadPaths,
		"questions":         track.Questions,
		"source_classes":    track.SourceClasses,
		"requires_spike":    track.RequiresSpike,
		"completion_signal": track.CompletionSignal,
	}
}

func deepResearchAllTracksAccepted(manifest deepResearchTrackManifest) bool {
	if len(manifest.Tracks) == 0 {
		return false
	}
	for _, track := range manifest.Tracks {
		if track.State != "accepted" {
			return false
		}
	}
	return true
}

func deepResearchNormalizeContradictions(value any, evidenceIDs []string) ([]any, error) {
	if value == nil {
		return []any{}, nil
	}
	rows, ok := value.([]any)
	if !ok {
		return nil, fmt.Errorf("contradictions must be an array")
	}
	byID := map[string]map[string]any{}
	for index, raw := range rows {
		row, rowOK := raw.(map[string]any)
		if !rowOK {
			return nil, fmt.Errorf("contradictions[%d] must be an object", index)
		}
		contradictionID := strings.ToUpper(strings.TrimSpace(asString(row["contradiction_id"])))
		summary := strings.TrimSpace(asString(row["summary"]))
		if !deepResearchContradictionPattern.MatchString(contradictionID) || byID[contradictionID] != nil || summary == "" {
			return nil, fmt.Errorf("contradictions[%d] has an invalid, duplicate, or incomplete identity", index)
		}
		refs, err := deepResearchStrictStrings(row["evidence_refs"], "contradiction evidence_refs", true)
		if err != nil || !deepResearchStringSubset(refs, evidenceIDs) {
			return nil, firstDeepResearchError(err, fmt.Errorf("contradiction %s references unknown evidence", contradictionID))
		}
		byID[contradictionID] = map[string]any{
			"contradiction_id": contradictionID,
			"summary":          summary,
			"evidence_refs":    refs,
		}
	}
	return deepResearchSortedObjectMap(byID, "contradiction_id"), nil
}

func deepResearchCanonicalSpikeRef(featureRef, ref string) string {
	featureRef = strings.TrimSuffix(filepath.ToSlash(strings.TrimSpace(featureRef)), "/")
	ref = filepath.ToSlash(strings.TrimSpace(ref))
	if strings.HasPrefix(ref, featureRef+"/") {
		return ref
	}
	ref = strings.TrimPrefix(ref, "./")
	if deepResearchSpikePattern.MatchString(ref) {
		ref = filepath.ToSlash(filepath.Join("research-spikes", ref, "manifest.json"))
	}
	return filepath.ToSlash(filepath.Join(featureRef, ref))
}

func deepResearchSynthesisHandoffIDs(synthesis map[string]any) []string {
	ids := []string{}
	for _, row := range deepResearchObjectSlice(synthesis["planning_handoffs"]) {
		id := strings.ToUpper(strings.TrimSpace(asString(row["handoff_id"])))
		if deepResearchHandoffPattern.MatchString(id) {
			ids = append(ids, id)
		}
	}
	sort.Strings(ids)
	return ids
}

func deepResearchResearcherIDs(manifest deepResearchTrackManifest) []string {
	set := map[string]bool{}
	if manifest.LeaderID != "" {
		set[manifest.LeaderID] = true
	}
	for _, track := range manifest.Tracks {
		if track.WorkerID != "" {
			set[track.WorkerID] = true
		}
	}
	return deepResearchSortedKeys(set)
}

func deepResearchBindingEnvelope(summary string, binding deepResearchPublishedBinding) Envelope {
	env := NewEnvelope("ok", summary)
	env.Data = map[string]any{
		"handoff_ref":        binding.HandoffRef,
		"handoff_sha256":     binding.HandoffSHA256,
		"source_spec_sha256": binding.SourceSpecSHA,
		"state_revision":     binding.StateRevision,
		"claim_status":       binding.ClaimStatus,
		"handoff_ids":        append([]string(nil), binding.HandoffIDs...),
		"capability_refs":    append([]string(nil), binding.CapabilityRefs...),
		"artifact_digests":   binding.ArtifactDigests,
	}
	env.NextArgv = []string{"/sp.plan"}
	return env
}

func deepResearchRenderMarkdown(synthesis map[string]any) []byte {
	var builder strings.Builder
	builder.WriteString("# Deep Research\n\n")
	builder.WriteString("> Derived human-readable projection. Canonical truth lives in the runtime-owned `research/*.json`, `research/handoffs/*.json`, and `research-evidence/*.json` artifacts.\n\n")
	builder.WriteString("**Status**: Complete\n\n")
	builder.WriteString("## Metadata\n\n")
	builder.WriteString("- Generation: `" + strings.TrimSpace(asString(synthesis["generation_id"])) + "`\n")
	builder.WriteString("- Source specification: `" + strings.TrimSpace(asString(synthesis["source_spec_ref"])) + "`\n")
	builder.WriteString("- Source SHA-256: `" + strings.TrimSpace(asString(synthesis["source_spec_sha256"])) + "`\n\n")

	builder.WriteString("## Feasibility Decision\n\n")
	builder.WriteString("**Recommendation**: Continue to `/sp.plan` using the verified runtime handoff.\n\n")
	builder.WriteString("**Reason**: Every selected capability has a closed, evidence-backed planning disposition.\n\n")

	builder.WriteString("## Capability Matrix\n\n")
	for _, row := range deepResearchObjectSlice(synthesis["capability_dispositions"]) {
		builder.WriteString("- `" + asString(row["capability_ref"]) + "` — " + asString(row["disposition"]) + "; evidence: " + deepResearchInlineCodeList(deepResearchStrings(row["reason_refs"])) + "\n")
	}
	builder.WriteString("\n## Research Orchestration\n\n")
	trackDigests := deepResearchStringMap(synthesis["track_result_digests"])
	for _, ref := range deepResearchSortedStringMapKeys(trackDigests) {
		builder.WriteString("- `" + ref + "` (`" + trackDigests[ref] + "`)\n")
	}

	builder.WriteString("\n## Implementation Chain Evidence\n\n")
	for _, row := range deepResearchObjectSlice(synthesis["evidence_dispositions"]) {
		evidenceID := strings.TrimSpace(asString(row["evidence_ref"]))
		builder.WriteString("- `research-evidence/" + evidenceID + ".json` — " + asString(row["disposition"]) + ": " + asString(row["reason"]) + "\n")
	}

	builder.WriteString("\n## Contradictions\n\n")
	resolutions := deepResearchObjectSlice(synthesis["contradiction_resolutions"])
	if len(resolutions) == 0 {
		builder.WriteString("- No unresolved contradictions remain.\n")
	} else {
		for _, row := range resolutions {
			builder.WriteString("- `" + asString(row["contradiction_id"]) + "` — " + asString(row["resolution"]) + "\n")
		}
	}

	builder.WriteString("\n## Synthesis Decisions\n\n")
	handoffs := deepResearchObjectSlice(synthesis["planning_handoffs"])
	for _, row := range handoffs {
		builder.WriteString("- `" + asString(row["handoff_id"]) + "`: " + asString(row["decision"]) + "\n")
	}

	builder.WriteString("\n## Planning Handoff\n\n")
	builder.WriteString("**Handoff IDs**: " + deepResearchInlineCodeList(deepResearchSynthesisHandoffIDs(synthesis)) + "\n\n")
	builder.WriteString("**Recommended approach**: " + deepResearchJoinObjectField(handoffs, "decision") + "\n\n")
	builder.WriteString("**Architecture implications**: Preserve the evidence-backed implementation chain and its named boundaries.\n\n")
	builder.WriteString("**Module boundaries**: " + deepResearchJoinObjectStringArrays(handoffs, "constraints") + "\n\n")
	builder.WriteString("**API / library choices**: Use only choices explicitly proven by the bound evidence and spikes.\n\n")
	builder.WriteString("**Data flow notes**: Carry each `CAP-###` decision through its `PH-###` binding without re-authoring the conclusion.\n\n")
	builder.WriteString("**Demo artifacts to reference**: " + deepResearchJoinObjectStringArrays(handoffs, "spike_refs") + "\n\n")
	builder.WriteString("**Constraints `/sp.plan` must preserve**: " + deepResearchJoinObjectStringArrays(handoffs, "constraints") + "\n\n")
	builder.WriteString("**Validation implications**: " + deepResearchJoinObjectStringArrays(handoffs, "validation") + "\n\n")
	builder.WriteString("**Residual risks requiring design mitigation**: " + deepResearchJoinObjectStringArrays(handoffs, "risks") + "\n\n")
	builder.WriteString("**Decisions already proven by research**: " + deepResearchJoinObjectField(handoffs, "decision") + "\n")

	builder.WriteString("\n## Evidence Quality Rubric\n\n")
	builder.WriteString("- Evidence identity, source freshness, authority metadata, and immutable digests are checked by `specify-runtime deep-research verify-handoff`.\n")
	builder.WriteString("- Independent audit covers capability closure, evidence integrity, source quality, contradictions, spikes, and planning handoff completeness.\n")

	builder.WriteString("\n## Planning Traceability Index\n\n")
	builder.WriteString("| Plan Decision | Handoff ID | Evidence / Spike ID | Evidence Quality | Plan Action |\n")
	builder.WriteString("|---|---|---|---|---|\n")
	for _, row := range handoffs {
		refs := append(deepResearchStrings(row["evidence_refs"]), deepResearchStrings(row["spike_refs"])...)
		builder.WriteString("| " + deepResearchEscapeTable(asString(row["decision"])) + " | `" + asString(row["handoff_id"]) + "` | " + deepResearchInlineCodeList(refs) + " | Runtime verified | Preserve and validate |\n")
	}

	builder.WriteString("\n## Research Exclusions\n\n- Anything not named by the selected capability and handoff IDs remains outside this research claim.\n")
	builder.WriteString("\n## Sources\n\n- Consume the canonical evidence objects and exact artifact digests from `research/handoff-to-plan.json`.\n")
	builder.WriteString("\n## Next Command\n\n`/sp.plan`\n")
	return []byte(builder.String())
}

func deepResearchRenderNotNeeded(dispositions []any) []byte {
	var builder strings.Builder
	builder.WriteString("# Deep Research\n\n")
	builder.WriteString("> Derived human-readable projection. Canonical truth lives in the runtime-owned Deep Research handoff.\n\n")
	builder.WriteString("**Status**: Not needed\n\n")
	builder.WriteString("## Feasibility Decision\n\n")
	builder.WriteString("**Recommendation**: Continue directly to `/sp.plan`.\n\n")
	builder.WriteString("**Reason**: ")
	reasons := []string{}
	for _, raw := range dispositions {
		row, _ := raw.(map[string]any)
		reasons = append(reasons, asString(row["capability_ref"])+": "+asString(row["reason"]))
	}
	builder.WriteString(strings.Join(reasons, "; ") + "\n\n")
	builder.WriteString("## Planning Handoff\n\n")
	builder.WriteString("**Handoff IDs**: Not needed\n\n")
	builder.WriteString("**Recommended approach**: Plan against the already proven repository implementation chain.\n\n")
	builder.WriteString("**Constraints `/sp.plan` must preserve**: Keep the evidence-backed existing boundary; do not invent a replacement path.\n\n")
	builder.WriteString("## Next Command\n\n`/sp.plan`\n")
	return []byte(builder.String())
}

func deepResearchJoinObjectField(rows []map[string]any, field string) string {
	values := []string{}
	for _, row := range rows {
		if value := strings.TrimSpace(asString(row[field])); value != "" {
			values = append(values, value)
		}
	}
	if len(values) == 0 {
		return "None"
	}
	return strings.Join(values, "; ")
}

func deepResearchJoinObjectStringArrays(rows []map[string]any, field string) string {
	values := []string{}
	for _, row := range rows {
		values = append(values, deepResearchStrings(row[field])...)
	}
	if len(values) == 0 {
		return "None"
	}
	return strings.Join(deepResearchUniqueStrings(values), "; ")
}

func deepResearchInlineCodeList(values []string) string {
	if len(values) == 0 {
		return "None"
	}
	out := make([]string, 0, len(values))
	for _, value := range values {
		out = append(out, "`"+strings.ReplaceAll(value, "`", "")+"`")
	}
	return strings.Join(out, ", ")
}

func deepResearchEscapeTable(value string) string {
	return strings.ReplaceAll(strings.TrimSpace(value), "|", "\\|")
}

func deepResearchJSONUpdates(values map[string]any) ([]fileTransactionUpdate, error) {
	return deepResearchJSONAndTextUpdates(values, nil)
}

func deepResearchJSONAndTextUpdates(values map[string]any, textValues map[string][]byte) ([]fileTransactionUpdate, error) {
	paths := make([]string, 0, len(values)+len(textValues))
	for path := range values {
		paths = append(paths, path)
	}
	for path := range textValues {
		if _, collision := values[path]; collision {
			return nil, fmt.Errorf("duplicate deep-research update target %s", path)
		}
		paths = append(paths, path)
	}
	sort.Strings(paths)
	updates := make([]fileTransactionUpdate, 0, len(paths))
	for _, path := range paths {
		content, exists := textValues[path]
		if !exists {
			var err error
			content, err = deepResearchMarshal(values[path])
			if err != nil {
				return nil, err
			}
		}
		updates = append(updates, fileTransactionUpdate{Path: path, Content: append([]byte(nil), content...), Perm: 0o644})
	}
	return updates, nil
}

func deepResearchMarshal(value any) ([]byte, error) {
	raw, err := json.MarshalIndent(value, "", "  ")
	if err != nil {
		return nil, err
	}
	return append(raw, '\n'), nil
}

func deepResearchDigest(value []byte) string {
	sum := sha256.Sum256(value)
	return hex.EncodeToString(sum[:])
}

func deepResearchReadObject(path string) (map[string]any, error) {
	raw, err := deepResearchReadRegularFile(path)
	if err != nil {
		return nil, err
	}
	var payload map[string]any
	if err := json.Unmarshal(raw, &payload); err != nil || payload == nil {
		return nil, firstDeepResearchError(err, fmt.Errorf("JSON root must be an object"))
	}
	return payload, nil
}

func deepResearchReadRegularProjectFile(projectRoot, ref string) ([]byte, error) {
	ref = filepath.ToSlash(strings.TrimSpace(ref))
	if ref == "" || filepath.IsAbs(ref) || ref == ".git" || strings.HasPrefix(ref, ".git/") {
		return nil, fmt.Errorf("project file reference is invalid: %s", ref)
	}
	path, err := secureProjectPath(projectRoot, ref)
	if err != nil {
		return nil, err
	}
	return deepResearchReadRegularFile(path)
}

func deepResearchReadRegularFile(path string) ([]byte, error) {
	info, err := os.Lstat(path)
	if err != nil {
		return nil, err
	}
	if info.Mode()&os.ModeSymlink != 0 || !info.Mode().IsRegular() {
		return nil, fmt.Errorf("%s must be a regular non-symlink file", filepath.Base(path))
	}
	return os.ReadFile(path)
}

func deepResearchPathWithin(path, root string) bool {
	pathAbs, pathErr := filepath.Abs(path)
	rootAbs, rootErr := filepath.Abs(root)
	if pathErr != nil || rootErr != nil {
		return false
	}
	relative, err := filepath.Rel(rootAbs, pathAbs)
	return err == nil && relative != ".." && !strings.HasPrefix(relative, ".."+string(filepath.Separator))
}

func deepResearchPathCovered(candidate string, allowed []string) bool {
	candidate = strings.TrimSuffix(filepath.ToSlash(filepath.Clean(filepath.FromSlash(candidate))), "/")
	for _, raw := range allowed {
		path := strings.TrimSuffix(filepath.ToSlash(filepath.Clean(filepath.FromSlash(raw))), "/")
		if path == "." || candidate == path || strings.HasPrefix(candidate, path+"/") {
			return true
		}
	}
	return false
}

func deepResearchStrictStrings(value any, label string, requireNonEmpty bool) ([]string, error) {
	var rows []any
	switch typed := value.(type) {
	case []any:
		rows = typed
	case []string:
		rows = make([]any, 0, len(typed))
		for _, item := range typed {
			rows = append(rows, item)
		}
	default:
		return nil, fmt.Errorf("%s must be an array", label)
	}
	out := make([]string, 0, len(rows))
	seen := map[string]bool{}
	for index, raw := range rows {
		text, ok := raw.(string)
		text = strings.TrimSpace(text)
		if !ok || text == "" {
			return nil, fmt.Errorf("%s[%d] must be a non-empty string", label, index)
		}
		if seen[text] {
			return nil, fmt.Errorf("%s contains duplicate value %q", label, text)
		}
		seen[text] = true
		out = append(out, text)
	}
	if requireNonEmpty && len(out) == 0 {
		return nil, fmt.Errorf("%s must not be empty", label)
	}
	return out, nil
}

func deepResearchOptionalStrings(value any, label string) ([]string, error) {
	if value == nil {
		return []string{}, nil
	}
	return deepResearchStrictStrings(value, label, false)
}

func deepResearchStrings(value any) []string {
	switch rows := value.(type) {
	case []any:
		out := make([]string, 0, len(rows))
		for _, raw := range rows {
			if text, ok := raw.(string); ok && strings.TrimSpace(text) != "" {
				out = append(out, strings.TrimSpace(text))
			}
		}
		return out
	case []string:
		return deepResearchUniqueStrings(rows)
	default:
		return []string{}
	}
}

func deepResearchObjectSlice(value any) []map[string]any {
	rows, ok := value.([]any)
	if !ok {
		return []map[string]any{}
	}
	out := make([]map[string]any, 0, len(rows))
	for _, raw := range rows {
		if row, ok := raw.(map[string]any); ok {
			out = append(out, row)
		}
	}
	return out
}

func deepResearchAnySlice(value any) []any {
	switch rows := value.(type) {
	case []any:
		return append([]any(nil), rows...)
	case []string:
		out := make([]any, 0, len(rows))
		for _, row := range rows {
			out = append(out, row)
		}
		return out
	default:
		return []any{}
	}
}

func deepResearchContains(values []string, target string) bool {
	for _, value := range values {
		if value == target {
			return true
		}
	}
	return false
}

func deepResearchStringSet(values []string) map[string]bool {
	set := make(map[string]bool, len(values))
	for _, value := range values {
		set[value] = true
	}
	return set
}

func deepResearchStringSubset(subset, universe []string) bool {
	set := deepResearchStringSet(universe)
	for _, value := range subset {
		if !set[value] {
			return false
		}
	}
	return true
}

func deepResearchSameStringSet(left, right []string) bool {
	if len(left) != len(right) {
		return false
	}
	leftSet := deepResearchStringSet(left)
	if len(leftSet) != len(right) {
		return false
	}
	for _, value := range right {
		if !leftSet[value] {
			return false
		}
	}
	return true
}

func deepResearchAppendUnique(values []string, value string) []string {
	if !deepResearchContains(values, value) {
		values = append(values, value)
	}
	sort.Strings(values)
	return values
}

func deepResearchUniqueStrings(values []string) []string {
	out := []string{}
	seen := map[string]bool{}
	for _, value := range values {
		value = strings.TrimSpace(value)
		if value != "" && !seen[value] {
			seen[value] = true
			out = append(out, value)
		}
	}
	return out
}

func deepResearchSortedKeys(values map[string]bool) []string {
	keys := make([]string, 0, len(values))
	for key := range values {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	return keys
}

func deepResearchSortedMapKeys(values map[string]map[string]any) []string {
	keys := make([]string, 0, len(values))
	for key := range values {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	return keys
}

func deepResearchSortedStringMapKeys(values map[string]string) []string {
	keys := make([]string, 0, len(values))
	for key := range values {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	return keys
}

func deepResearchSortedObjectMap(values map[string]map[string]any, identityField string) []any {
	keys := make([]string, 0, len(values))
	for key := range values {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	out := make([]any, 0, len(keys))
	for _, key := range keys {
		row := values[key]
		if identityField != "" && strings.TrimSpace(asString(row[identityField])) == "" {
			row[identityField] = key
		}
		out = append(out, row)
	}
	return out
}

func deepResearchStringMap(value any) map[string]string {
	out := map[string]string{}
	switch values := value.(type) {
	case map[string]any:
		for key, raw := range values {
			if text, ok := raw.(string); ok && strings.TrimSpace(key) != "" && strings.TrimSpace(text) != "" {
				out[key] = strings.TrimSpace(text)
			}
		}
	case map[string]string:
		for key, text := range values {
			if strings.TrimSpace(key) != "" && strings.TrimSpace(text) != "" {
				out[key] = strings.TrimSpace(text)
			}
		}
	}
	return out
}

func deepResearchStringMapEqual(left, right map[string]string) bool {
	if len(left) != len(right) {
		return false
	}
	for key, value := range left {
		if right[key] != value {
			return false
		}
	}
	return true
}

func deepResearchRefsKnown(refs []string, corpus deepResearchCorpus) bool {
	for _, ref := range refs {
		if deepResearchContains(corpus.EvidenceIDs, ref) || deepResearchContains(corpus.SpikeRefs, ref) {
			continue
		}
		return false
	}
	return true
}

func deepResearchStringPointer(value string) *string {
	copy := value
	return &copy
}

func deepResearchFailure(status, summary string, err error) Envelope {
	env := NewEnvelope(status, summary)
	if err != nil {
		env.Blockers = append(env.Blockers, err.Error())
	}
	bindDeepResearchSourceReadiness(&env, err)
	return env
}

func bindDeepResearchSourceReadiness(env *Envelope, cause error) bool {
	if env == nil || cause == nil {
		return false
	}
	var readiness *deepResearchSourceReadinessError
	if !errors.As(cause, &readiness) {
		return false
	}
	env.Status = "blocked"
	env.Summary = readiness.Error()
	env.Data["error_code"] = readiness.Code
	env.Data["feature_dir"] = readiness.FeatureRef
	env.Data["source_spec_status"] = readiness.SpecStatus
	env.Data["workflow_stage"] = readiness.WorkflowStage
	env.Data["workflow_status"] = readiness.WorkflowStatus
	env.Data["owner_workflow"] = readiness.OwnerWorkflow
	env.Data["owner"] = readiness.Owner
	env.Data["human_action_required"] = readiness.HumanActionRequired
	env.Data["resolution_action"] = readiness.ResolutionAction
	env.Blockers = []any{map[string]any{
		"code": readiness.Code, "owner": readiness.Owner,
		"human_action_required": readiness.HumanActionRequired,
		"owner_workflow":        readiness.OwnerWorkflow, "details": append([]any(nil), readiness.Details...),
	}}
	if readiness.OwnerWorkflow != "" {
		env.NextArgv = []string{readiness.OwnerWorkflow}
	}
	return true
}

func firstDeepResearchError(primary, fallback error) error {
	if primary != nil {
		return primary
	}
	return fallback
}
