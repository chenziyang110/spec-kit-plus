package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"regexp"
	"runtime"
	"sort"
	"strconv"
	"strings"
	"time"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/filelock"
)

const (
	testDesignStateSchema        = "spec-kit-test-design-state-v1"
	testDesignGapsSchema         = "spec-kit-test-design-gaps-v1"
	testDesignHandoffSchema      = "spec-kit-test-design-handoff-v1"
	testDesignPublicationFile    = "test-design-publication.json"
	testDesignPublicationV1      = "spec-kit-test-design-publication-v1"
	testDesignProjectionV1       = "spec-kit-test-design-projection-v1"
	testDesignLaneProtocol       = "test_design_lane_result.v1"
	testDesignLaneManifestFormat = "test-design-lane-manifest"
)

var (
	testDesignLaneIDPattern       = regexp.MustCompile(`^(LANE|AUDIT)-[0-9]{3,}$`)
	testDesignAttemptIDPattern    = regexp.MustCompile(`^ATTEMPT-[0-9]{3,}$`)
	testDesignWorkerIDPattern     = regexp.MustCompile(`^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$`)
	testDesignObligationPattern   = regexp.MustCompile(`^TO-[0-9]{3,}$`)
	testDesignCapabilityPattern   = regexp.MustCompile(`^CAP-[0-9]{3,}$`)
	testDesignScenarioPattern     = regexp.MustCompile(`^SCN-[0-9]{3,}$`)
	testDesignCasePattern         = regexp.MustCompile(`^TC-[0-9]{3,}$`)
	testDesignCoveragePattern     = regexp.MustCompile(`^COV-[0-9]{3,}$`)
	testDesignDataPattern         = regexp.MustCompile(`^TD-[0-9]{3,}$`)
	testDesignGapPattern          = regexp.MustCompile(`^GAP-[0-9]{3,}$`)
	testDesignSHA256Pattern       = regexp.MustCompile(`^[0-9a-f]{64}$`)
	testDesignEvidenceRefPattern  = regexp.MustCompile(`^\.specify/evidence/records/evd-[0-9a-f]{24}\.json$`)
	testDesignAuditCheckIDPattern = regexp.MustCompile(`^[a-z][a-z0-9_-]+$`)
)

var testDesignAuditCoreCheckIDs = []string{
	"obligation_accounting",
	"traceability",
	"oracle_quality",
	"harness_feasibility",
	"data_readiness",
	"evidence_freshness",
	"risk_dimensions",
	"contradictions",
}

type testDesignService struct {
	projectRoot string
}

type testDesignState struct {
	SchemaVersion string                `json:"schema_version"`
	Revision      int                   `json:"revision"`
	Scope         string                `json:"scope"`
	Mode          string                `json:"mode"`
	FeatureDir    *string               `json:"feature_dir"`
	ArtifactRoot  string                `json:"artifact_root"`
	Status        string                `json:"status"`
	Phase         string                `json:"phase"`
	ClaimStatus   string                `json:"claim_status"`
	Source        testDesignStateSource `json:"source"`
	Lanes         testDesignStateLanes  `json:"lanes"`
	Audit         testDesignStateAudit  `json:"audit"`
	Blockers      []any                 `json:"blockers"`
}

type testDesignStateSource struct {
	Query          string   `json:"query"`
	SourceRefs     []string `json:"source_refs"`
	IncludedPaths  []string `json:"included_paths"`
	ExcludedPaths  []string `json:"excluded_paths"`
	RiskDimensions []string `json:"risk_dimensions"`
	Fingerprint    string   `json:"fingerprint"`
}

type testDesignStateLanes struct {
	ManifestRef        string   `json:"manifest_ref"`
	AcceptedResultRefs []string `json:"accepted_result_refs"`
}

type testDesignStateAudit struct {
	Status    string  `json:"status"`
	LaneID    *string `json:"lane_id"`
	ResultRef *string `json:"result_ref"`
}

type testDesignLaneManifest struct {
	Version                  int               `json:"version"`
	Artifact                 string            `json:"artifact"`
	GenerationID             string            `json:"generation_id"`
	Status                   string            `json:"status"`
	LeaderID                 string            `json:"leader_id"`
	AuditSequence            int               `json:"audit_sequence,omitempty"`
	SynthesisOwnerID         string            `json:"synthesis_owner_id,omitempty"`
	SynthesisArtifactDigests map[string]string `json:"synthesis_artifact_digests,omitempty"`
	Lanes                    []testDesignLane  `json:"lanes"`
}

type testDesignLane struct {
	LaneID             string                `json:"lane_id"`
	Kind               string                `json:"kind"`
	Title              string                `json:"title"`
	State              string                `json:"state"`
	ObligationIDs      []string              `json:"obligation_ids"`
	ReadPaths          []string              `json:"read_paths"`
	Questions          []string              `json:"questions"`
	WorkerID           string                `json:"worker_id,omitempty"`
	AttemptID          string                `json:"attempt_id,omitempty"`
	AttemptNumber      int                   `json:"attempt_number"`
	CheckpointSequence int                   `json:"checkpoint_sequence"`
	CheckpointRef      string                `json:"checkpoint_ref,omitempty"`
	ResultRef          string                `json:"result_ref,omitempty"`
	ResultSHA256       string                `json:"result_sha256,omitempty"`
	SourceFingerprint  string                `json:"source_fingerprint,omitempty"`
	ArtifactDigests    map[string]string     `json:"artifact_digests,omitempty"`
	YieldHistory       []testDesignLaneYield `json:"yield_history,omitempty"`
}

type testDesignLaneYield struct {
	AttemptID     string `json:"attempt_id"`
	WorkerID      string `json:"worker_id"`
	Reason        string `json:"reason"`
	CheckpointRef string `json:"checkpoint_ref,omitempty"`
}

type testDesignBundle struct {
	Universe       map[string]any
	Catalog        map[string]any
	DataManifest   map[string]any
	CoverageMatrix map[string]any
	Gaps           map[string]any
}

type testDesignPublishedHandoff struct {
	Ref               string
	SHA256            string
	SourceFingerprint string
	StateRevision     int
	ArtifactDigests   map[string]string
	TestCaseRefs      []string
	TestDataRefs      []string
}

type testDesignPublicationBinding struct {
	Ref               string
	SHA256            string
	Scope             string
	ArtifactRoot      string
	FeatureDir        *string
	SourceFingerprint string
	StateRevision     int
	ClaimStatus       string
	ArtifactDigests   map[string]string
	ObligationRefs    []string
	TestCaseRefs      []string
	TestDataRefs      []string
	CoverageRefs      []string
	GapRefs           []string
}

type testDesignPublicationSnapshot struct {
	State       testDesignState
	Bundle      testDesignBundle
	Publication map[string]any
}

func runTestDesign(args []string, stdout io.Writer) int {
	if len(args) == 0 {
		return writeEnvelope(stdout, testDesignFailure("usage-error", "missing test-design subcommand", nil))
	}
	if args[0] == "--help" || args[0] == "-h" || args[0] == "help" {
		return writeTestDesignHelp(stdout)
	}
	if err := testDesignValidateOptions(args); err != nil {
		return writeEnvelope(stdout, testDesignFailure("usage-error", "test-design command options are invalid", err))
	}
	projectRoot := optionValue(args, "--project-root", ".")
	service := testDesignService{projectRoot: projectRoot}
	var env Envelope
	switch args[0] {
	case "init":
		env = service.initialize(args[1:])
	case "status":
		env = service.status(args[1:])
	case "universe-build":
		env = service.universeBuild(args[1:])
	case "lane-prepare":
		env = service.lanePrepare(args[1:])
	case "lane-lease":
		env = service.laneLease(args[1:])
	case "lane-checkpoint":
		env = service.laneCheckpoint(args[1:])
	case "lane-yield":
		env = service.laneYield(args[1:])
	case "lane-accept":
		env = service.laneAccept(args[1:])
	case "gap-reconcile":
		env = service.gapReconcile(args[1:])
	case "synthesize":
		env = service.synthesize(args[1:])
	case "audit-prepare":
		env = service.auditPrepare(args[1:])
	case "validate":
		env = service.validate(args[1:])
	case "publish":
		env = service.publish(args[1:])
	case "projection-build":
		env = service.projectionBuild(args[1:])
	case "projection-verify":
		env = service.projectionVerify(args[1:])
	case "handoff":
		env = service.handoff(args[1:])
	default:
		env = testDesignFailure("usage-error", fmt.Sprintf("unknown test-design subcommand %q", args[0]), nil)
	}
	return writeEnvelope(stdout, env)
}

func testDesignValidateOptions(args []string) error {
	if len(args) == 0 {
		return fmt.Errorf("missing test-design subcommand")
	}
	common := []string{"--project-root", "--format"}
	perCommand := map[string][]string{
		"init":              {"--scope", "--feature-dir", "--mode", "--input-json", "--expected-revision", "--leader-id"},
		"status":            {"--feature-dir"},
		"universe-build":    {"--feature-dir", "--expected-revision"},
		"lane-prepare":      {"--feature-dir", "--input-json", "--expected-revision"},
		"lane-lease":        {"--feature-dir", "--worker-id", "--expected-revision"},
		"lane-checkpoint":   {"--feature-dir", "--lane-id", "--attempt-id", "--result-json", "--expected-revision"},
		"lane-yield":        {"--feature-dir", "--lane-id", "--attempt-id", "--reason"},
		"lane-accept":       {"--feature-dir", "--lane-id", "--attempt-id", "--expected-revision"},
		"gap-reconcile":     {"--feature-dir", "--leader-id", "--input-json", "--expected-revision"},
		"synthesize":        {"--feature-dir", "--leader-id", "--expected-revision"},
		"audit-prepare":     {"--feature-dir", "--expected-revision"},
		"validate":          {"--feature-dir", "--expected-revision"},
		"publish":           {"--feature-dir", "--expected-revision"},
		"projection-build":  {"--feature-dir", "--consumer", "--basis-ref", "--obligation-ids"},
		"projection-verify": {"--feature-dir", "--projection-ref", "--expected-sha256"},
		"handoff":           {"--feature-dir", "--expected-revision"},
	}
	commandOptions, ok := perCommand[args[0]]
	if !ok {
		return nil
	}
	allowed := map[string]bool{}
	for _, name := range append(common, commandOptions...) {
		allowed[name] = true
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

func writeTestDesignHelp(stdout io.Writer) int {
	_, _ = fmt.Fprintln(stdout, "Usage: specify-runtime test-design <subcommand> [options]")
	_, _ = fmt.Fprintln(stdout, "Subcommands: init, status, universe-build, lane-prepare, lane-lease, lane-checkpoint, lane-yield, lane-accept, gap-reconcile, synthesize, audit-prepare, validate, publish, projection-build, projection-verify, handoff")
	return 0
}

func (service testDesignService) initialize(args []string) Envelope {
	leaderID := strings.TrimSpace(optionValue(args, "--leader-id", ""))
	if !testDesignWorkerIDPattern.MatchString(leaderID) {
		return testDesignFailure("usage-error", "test-design init requires a valid --leader-id", nil)
	}
	scope := strings.ToLower(strings.TrimSpace(optionValue(args, "--scope", "")))
	featureArg := strings.TrimSpace(optionValue(args, "--feature-dir", ""))
	if scope == "" {
		if featureArg != "" {
			scope = "feature"
		} else {
			scope = "project"
		}
	}
	if scope != "feature" && scope != "project" {
		return testDesignFailure("usage-error", "test-design init --scope must be feature or project", nil)
	}
	if scope == "feature" && featureArg == "" {
		return testDesignFailure("usage-error", "feature-scoped test design requires --feature-dir", nil)
	}
	if scope == "project" && featureArg != "" {
		return testDesignFailure("usage-error", "project-scoped test design must not set --feature-dir", nil)
	}
	root, rootRef, featureRef, err := service.resolveRoot(featureArg)
	if err != nil {
		return testDesignFailure("usage-error", "test-design root is invalid", err)
	}
	input, err := service.inputObject(args, "--input-json", "test-design init")
	if err != nil {
		return testDesignFailure("usage-error", "test-design init input is invalid", err)
	}
	query := strings.TrimSpace(asString(input["query"]))
	if query == "" {
		return testDesignFailure("invalid", "test-design init requires a non-empty query", nil)
	}
	sourceRefs, err := service.normalizedPathList(input["source_refs"], "source_refs", false)
	if err != nil || len(sourceRefs) == 0 {
		return testDesignFailure("invalid", "test-design init source_refs are invalid", firstTestDesignError(err, errors.New("source_refs must not be empty")))
	}
	includedPaths, err := service.normalizedPathList(input["included_paths"], "included_paths", true)
	if err != nil || len(includedPaths) == 0 {
		return testDesignFailure("invalid", "test-design init included_paths are invalid", firstTestDesignError(err, errors.New("included_paths must not be empty")))
	}
	excludedPaths, err := service.normalizedPathList(input["excluded_paths"], "excluded_paths", true)
	if err != nil {
		return testDesignFailure("invalid", "test-design init excluded_paths are invalid", err)
	}
	riskDimensions, err := testDesignStrictStrings(input["risk_dimensions"], "risk_dimensions", true)
	if err != nil || len(riskDimensions) == 0 {
		return testDesignFailure("invalid", "test-design init risk_dimensions are invalid", firstTestDesignError(err, errors.New("risk_dimensions must not be empty")))
	}
	for _, ref := range sourceRefs {
		if testDesignPathCovered(ref, excludedPaths) {
			return testDesignFailure("invalid", "test-design source is excluded from the frozen boundary", fmt.Errorf("source_ref %s is excluded", ref))
		}
		path, resolveErr := testDesignResolveProjectPath(service.projectRoot, ref)
		if resolveErr != nil {
			return testDesignFailure("invalid", "test-design source path is invalid", resolveErr)
		}
		info, statErr := os.Stat(path)
		if statErr != nil || !info.Mode().IsRegular() {
			if statErr == nil {
				statErr = fmt.Errorf("source_ref must name a regular file")
			}
			return testDesignFailure("invalid", "test-design source cannot be frozen", fmt.Errorf("%s: %w", ref, statErr))
		}
	}
	mode := strings.ToLower(strings.TrimSpace(optionValue(args, "--mode", "")))
	if mode == "" {
		if scope == "project" {
			mode = "project-baseline"
		} else {
			mode = "feature"
		}
	}
	if !testDesignContains([]string{"project-baseline", "feature", "incremental-update", "audit"}, mode) {
		return testDesignFailure("usage-error", "test-design init --mode is invalid", fmt.Errorf("unsupported mode %q", mode))
	}
	if (mode == "project-baseline" && scope != "project") || (mode == "feature" && scope != "feature") {
		return testDesignFailure("usage-error", "test-design init mode does not match scope", fmt.Errorf("mode %s cannot initialize scope %s", mode, scope))
	}
	sourceFingerprint, err := service.sourceFingerprint(sourceRefs, includedPaths, excludedPaths, riskDimensions, rootRef)
	if err != nil {
		return testDesignFailure("error", "cannot fingerprint test-design sources", err)
	}
	var featureDir *string
	if featureRef != "" {
		featureDir = &featureRef
	}
	state := testDesignState{
		SchemaVersion: testDesignStateSchema,
		Revision:      1,
		Scope:         scope,
		Mode:          mode,
		FeatureDir:    featureDir,
		ArtifactRoot:  rootRef,
		Status:        "active",
		Phase:         "scoped",
		ClaimStatus:   "pending",
		Source: testDesignStateSource{
			Query:          query,
			SourceRefs:     sourceRefs,
			IncludedPaths:  includedPaths,
			ExcludedPaths:  excludedPaths,
			RiskDimensions: riskDimensions,
			Fingerprint:    sourceFingerprint,
		},
		Lanes: testDesignStateLanes{
			ManifestRef:        "lane-manifest.json",
			AcceptedResultRefs: []string{},
		},
		Audit: testDesignStateAudit{
			Status:    "pending",
			LaneID:    nil,
			ResultRef: nil,
		},
		Blockers: []any{},
	}
	manifest := testDesignLaneManifest{
		Version:      1,
		Artifact:     testDesignLaneManifestFormat,
		GenerationID: "tdg-" + sourceFingerprint[:16],
		Status:       "idle",
		LeaderID:     leaderID,
		Lanes:        []testDesignLane{},
	}
	return service.withMutationLock(root, func() Envelope {
		statePath := filepath.Join(root, "test-state.json")
		_, statErr := os.Stat(statePath)
		exists := statErr == nil
		if statErr != nil && !errors.Is(statErr, os.ErrNotExist) {
			return testDesignFailure("error", "cannot inspect test-design workspace", statErr)
		}
		if mode == "incremental-update" || mode == "audit" {
			if !exists {
				return testDesignFailure("blocked", "test-design update mode requires an existing matching workspace", fmt.Errorf("initialize the root with project-baseline or feature mode first"))
			}
			if !hasFlag(args, "--expected-revision") {
				return testDesignFailure("blocked", "test-design update mode requires --expected-revision", fmt.Errorf("read the current revision with test-design status and retry with CAS"))
			}
			previous, readErr := testDesignReadState(root)
			if readErr != nil {
				return testDesignFailure("blocked", "existing test-design state is invalid", readErr)
			}
			if revisionErr := testDesignCheckExpectedRevision(args, previous); revisionErr != nil {
				return testDesignFailure("blocked", "test-design revision changed", revisionErr)
			}
			if matchErr := testDesignStateMatchesRoot(previous, scope, featureRef, rootRef); matchErr != nil {
				return testDesignFailure("blocked", "test-design update root does not match existing state", matchErr)
			}
			if mode == "audit" && !testDesignSameBoundary(previous.Source, state.Source) {
				return testDesignFailure("blocked", "test-design audit mode cannot change the frozen boundary", fmt.Errorf("source_refs, included_paths, excluded_paths, and risk_dimensions must match the existing state"))
			}
			if _, bundleErr := testDesignReadBundle(root); bundleErr != nil {
				return testDesignFailure("blocked", "existing canonical test-design artifacts are unavailable", bundleErr)
			}
			state.Revision = previous.Revision + 1
			manifest.GenerationID = "tdg-" + sourceFingerprint[:16]
			archivePath, archiveErr := service.archiveHandoff(root, previous.Revision)
			if archiveErr != nil {
				return testDesignFailure("error", "cannot invalidate previous test-design handoff", archiveErr)
			}
			updates, updateErr := testDesignFileUpdates(map[string]any{
				statePath: state,
				filepath.Join(root, "lane-manifest.json"): manifest,
			})
			if updateErr != nil {
				_ = service.restoreArchivedHandoff(root, archivePath)
				return testDesignFailure("error", "cannot render test-design update state", updateErr)
			}
			if _, transactionErr := applyFileTransaction(service.projectRoot, "test-design.reinitialize", updates); transactionErr != nil {
				_ = service.restoreArchivedHandoff(root, archivePath)
				return testDesignFailure("error", "cannot reset test-design workflow generation", transactionErr)
			}
			env := NewEnvelope("ok", "test-design workspace generation reset")
			env.Data = testDesignStateData(state, rootRef)
			env.Data["preserved_stable_ids"] = true
			env.NextArgv = service.commandArgv(state, "universe-build")
			return env
		}
		if exists {
			return testDesignFailure("blocked", "test-design workspace already exists", fmt.Errorf("resume it with test-design status or use incremental-update/audit with --expected-revision"))
		}
		universe, loadErr := service.loadCanonicalTemplate("test-universe.json")
		if loadErr != nil {
			return testDesignFailure("blocked", "test-design template is unavailable", loadErr)
		}
		catalog, loadErr := service.loadCanonicalTemplate("test-catalog.json")
		if loadErr != nil {
			return testDesignFailure("blocked", "test-design template is unavailable", loadErr)
		}
		dataManifest, loadErr := service.loadCanonicalTemplate("test-data-manifest.json")
		if loadErr != nil {
			return testDesignFailure("blocked", "test-design template is unavailable", loadErr)
		}
		coverage, loadErr := service.loadCanonicalTemplate("coverage-matrix.json")
		if loadErr != nil {
			return testDesignFailure("blocked", "test-design template is unavailable", loadErr)
		}
		if scope == "project" {
			universe["feature_ref"] = nil
		} else {
			universe["feature_ref"] = featureRef
		}
		if _, ok := universe["obligations"]; !ok {
			universe["obligations"] = []any{}
		}
		gaps := map[string]any{"schema_version": testDesignGapsSchema, "status": "open", "gaps": []any{}}
		updates, updateErr := testDesignFileUpdates(map[string]any{
			filepath.Join(root, "test-state.json"):         state,
			filepath.Join(root, "test-universe.json"):      universe,
			filepath.Join(root, "test-catalog.json"):       catalog,
			filepath.Join(root, "test-data-manifest.json"): dataManifest,
			filepath.Join(root, "coverage-matrix.json"):    coverage,
			filepath.Join(root, "test-gaps.json"):          gaps,
			filepath.Join(root, "lane-manifest.json"):      manifest,
		})
		if updateErr != nil {
			return testDesignFailure("error", "cannot render test-design workspace", updateErr)
		}
		if _, transactionErr := applyFileTransaction(service.projectRoot, "test-design.init", updates); transactionErr != nil {
			return testDesignFailure("error", "cannot initialize test-design workspace", transactionErr)
		}
		env := NewEnvelope("ok", "test-design workspace initialized")
		env.Data = testDesignStateData(state, rootRef)
		env.NextArgv = service.commandArgv(state, "universe-build")
		return env
	})
}

func (service testDesignService) status(args []string) Envelope {
	root, rootRef, _, err := service.resolveRoot(optionValue(args, "--feature-dir", ""))
	if err != nil {
		return testDesignFailure("usage-error", "test-design root is invalid", err)
	}
	state, err := testDesignReadState(root)
	if err != nil {
		return testDesignFailure("blocked", "test-design state is unavailable", err)
	}
	manifest, err := testDesignReadManifest(root)
	if err != nil {
		return testDesignFailure("blocked", "test-design lane manifest is unavailable", err)
	}
	env := NewEnvelope("ok", "test-design status")
	env.Data = testDesignStateData(state, rootRef)
	env.Data["lanes"] = testDesignLaneCounts(manifest)
	env.Data["active_leases"] = testDesignActiveLeases(manifest)
	if freshnessErr := service.requireFreshSources(state); freshnessErr != nil {
		env.Status = "blocked"
		env.Summary = "test-design sources are stale"
		env.Blockers = append(env.Blockers, freshnessErr.Error())
		env.Data["source_freshness"] = "stale"
	} else {
		env.Data["source_freshness"] = "current"
	}
	if _, handoffErr := os.Stat(filepath.Join(root, "handoff-to-tasks.json")); handoffErr == nil {
		binding, verifyErr := service.verifyPublishedHandoff(root)
		if verifyErr != nil {
			env.Data["handoff_freshness"] = "stale"
			env.Data["handoff_error"] = verifyErr.Error()
		} else {
			env.Data["handoff_freshness"] = "current"
			env.Data["handoff_sha256"] = binding.SHA256
		}
	} else if state.Phase == "handed-off" {
		env.Data["handoff_freshness"] = "missing"
	} else {
		env.Data["handoff_freshness"] = "not-published"
	}
	if _, publicationErr := os.Lstat(filepath.Join(root, testDesignPublicationFile)); publicationErr == nil {
		binding, verifyErr := service.verifyPublication(root)
		if verifyErr != nil {
			env.Data["publication_freshness"] = "stale"
			env.Data["publication_error"] = verifyErr.Error()
		} else {
			env.Data["publication_freshness"] = "current"
			env.Data["publication_sha256"] = binding.SHA256
		}
	} else if state.Phase == "handed-off" {
		env.Data["publication_freshness"] = "missing"
	} else {
		env.Data["publication_freshness"] = "not-published"
	}
	next := testDesignNextSubcommand(state, manifest)
	env.Data["next_action"] = next
	if next != "" {
		env.NextArgv = service.commandArgv(state, next)
	}
	return env
}

func (service testDesignService) universeBuild(args []string) Envelope {
	root, rootRef, _, err := service.resolveRoot(optionValue(args, "--feature-dir", ""))
	if err != nil {
		return testDesignFailure("usage-error", "test-design root is invalid", err)
	}
	return service.withMutationLock(root, func() Envelope {
		state, readErr := testDesignReadState(root)
		if readErr != nil {
			return testDesignFailure("blocked", "test-design state is unavailable", readErr)
		}
		if revisionErr := testDesignCheckExpectedRevision(args, state); revisionErr != nil {
			return testDesignFailure("blocked", "test-design revision changed", revisionErr)
		}
		if state.Phase != "scoped" && state.Phase != "universe-ready" {
			return testDesignFailure("blocked", "test-design universe cannot be rebuilt at the current phase", fmt.Errorf("current phase is %s", state.Phase))
		}
		if freshnessErr := service.requireFreshSources(state); freshnessErr != nil {
			return service.persistStaleState(root, rootRef, state, freshnessErr)
		}
		bundle, bundleErr := testDesignReadBundle(root)
		if bundleErr != nil {
			return testDesignFailure("invalid", "test-design bundle cannot be read", bundleErr)
		}
		if validationErr := testDesignValidateBundle(bundle); validationErr != nil {
			return testDesignFailure("invalid", "test-design universe is invalid", validationErr)
		}
		if evidenceErr := service.validateBundleEvidence(bundle); evidenceErr != nil {
			return testDesignFailure("invalid", "test-design universe evidence is invalid", evidenceErr)
		}
		digests, digestErr := testDesignBundleDigests(root)
		if digestErr != nil {
			return testDesignFailure("error", "cannot fingerprint test-design artifacts", digestErr)
		}
		state.Phase = "universe-ready"
		state.Status = "active"
		state.ClaimStatus = "pending"
		state.Revision++
		if writeErr := service.writeState(root, state, "test-design.universe-build"); writeErr != nil {
			return testDesignFailure("error", "cannot persist test-design state", writeErr)
		}
		env := NewEnvelope("ok", "test-design universe frozen")
		env.Data = testDesignStateData(state, rootRef)
		env.Data["artifact_digests"] = digests
		env.NextArgv = service.commandArgv(state, "lane-prepare")
		return env
	})
}

func (service testDesignService) lanePrepare(args []string) Envelope {
	root, rootRef, _, err := service.resolveRoot(optionValue(args, "--feature-dir", ""))
	if err != nil {
		return testDesignFailure("usage-error", "test-design root is invalid", err)
	}
	input, err := service.inputObject(args, "--input-json", "test-design lane-prepare")
	if err != nil {
		return testDesignFailure("usage-error", "test-design lane input is invalid", err)
	}
	rawLanes, ok := input["lanes"].([]any)
	if !ok || len(rawLanes) == 0 {
		return testDesignFailure("invalid", "test-design lane-prepare requires a non-empty lanes array", nil)
	}
	return service.withMutationLock(root, func() Envelope {
		state, readErr := testDesignReadState(root)
		if readErr != nil {
			return testDesignFailure("blocked", "test-design state is unavailable", readErr)
		}
		if revisionErr := testDesignCheckExpectedRevision(args, state); revisionErr != nil {
			return testDesignFailure("blocked", "test-design revision changed", revisionErr)
		}
		if state.Phase != "universe-ready" && state.Phase != "discovery" {
			return testDesignFailure("blocked", "discovery lanes require a frozen universe", fmt.Errorf("current phase is %s", state.Phase))
		}
		manifest, manifestErr := testDesignReadManifest(root)
		if manifestErr != nil {
			return testDesignFailure("blocked", "test-design lane manifest is unavailable", manifestErr)
		}
		bundle, bundleErr := testDesignReadBundle(root)
		if bundleErr != nil {
			return testDesignFailure("blocked", "test-design universe is unavailable", bundleErr)
		}
		obligations, obligationErr := testDesignIndexRows(bundle.Universe["obligations"], "obligation_id", "test-universe obligations")
		if obligationErr != nil || len(obligations) == 0 {
			return testDesignFailure("blocked", "test-design obligations are unavailable", firstTestDesignError(obligationErr, errors.New("obligations must not be empty")))
		}
		seen := map[string]bool{}
		for _, lane := range manifest.Lanes {
			seen[lane.LaneID] = true
		}
		prepared := make([]string, 0, len(rawLanes))
		for index, raw := range rawLanes {
			row, rowOK := raw.(map[string]any)
			if !rowOK {
				return testDesignFailure("invalid", "test-design lane is invalid", fmt.Errorf("lanes[%d] must be an object", index))
			}
			lane, laneErr := service.parseDiscoveryLane(row, state)
			if laneErr != nil {
				return testDesignFailure("invalid", "test-design lane is invalid", fmt.Errorf("lanes[%d]: %w", index, laneErr))
			}
			if seen[lane.LaneID] {
				return testDesignFailure("invalid", "test-design lane id is duplicated", fmt.Errorf("lane %s already exists", lane.LaneID))
			}
			for _, obligationID := range lane.ObligationIDs {
				if _, ok := obligations[obligationID]; !ok {
					return testDesignFailure("invalid", "test-design lane references an unknown obligation", fmt.Errorf("lane %s references %s", lane.LaneID, obligationID))
				}
			}
			seen[lane.LaneID] = true
			manifest.Lanes = append(manifest.Lanes, lane)
			prepared = append(prepared, lane.LaneID)
		}
		manifest.Status = "active"
		state.Phase = "discovery"
		state.Status = "active"
		state.Revision++
		if writeErr := service.writeStateAndManifest(root, state, manifest, "test-design.lane-prepare"); writeErr != nil {
			return testDesignFailure("error", "cannot prepare test-design lanes", writeErr)
		}
		env := NewEnvelope("ok", "test-design discovery lanes prepared")
		env.Data = testDesignStateData(state, rootRef)
		env.Data["lane_ids"] = prepared
		env.Data["lanes"] = testDesignLaneCounts(manifest)
		env.NextArgv = service.commandArgv(state, "lane-lease")
		return env
	})
}

func (service testDesignService) laneLease(args []string) Envelope {
	root, rootRef, _, err := service.resolveRoot(optionValue(args, "--feature-dir", ""))
	if err != nil {
		return testDesignFailure("usage-error", "test-design root is invalid", err)
	}
	workerID := strings.TrimSpace(optionValue(args, "--worker-id", ""))
	if !testDesignWorkerIDPattern.MatchString(workerID) {
		return testDesignFailure("usage-error", "test-design lane-lease requires a valid --worker-id", nil)
	}
	return service.withMutationLock(root, func() Envelope {
		state, readErr := testDesignReadState(root)
		if readErr != nil {
			return testDesignFailure("blocked", "test-design state is unavailable", readErr)
		}
		if revisionErr := testDesignCheckExpectedRevision(args, state); revisionErr != nil {
			return testDesignFailure("blocked", "test-design revision changed", revisionErr)
		}
		manifest, manifestErr := testDesignReadManifest(root)
		if manifestErr != nil {
			return testDesignFailure("blocked", "test-design lane manifest is unavailable", manifestErr)
		}
		laneIndex := -1
		identityConflict := ""
		for index := range manifest.Lanes {
			candidate := manifest.Lanes[index]
			if candidate.State != "pending" {
				continue
			}
			if candidate.Kind == "audit" {
				if manifest.SynthesisOwnerID == "" {
					identityConflict = "audit cannot be leased before the synthesis owner is recorded"
					continue
				}
				if testDesignAuditWorkerConflict(manifest, workerID) {
					identityConflict = fmt.Sprintf("audit worker %s overlaps the leader, synthesis owner, or an accepted discovery worker", workerID)
					continue
				}
			}
			if candidate.Kind == "discovery" && workerID == manifest.LeaderID {
				identityConflict = fmt.Sprintf("discovery worker %s is the generation leader and is not an independent subagent", workerID)
				continue
			}
			laneIndex = index
			break
		}
		if laneIndex < 0 {
			if identityConflict != "" {
				return testDesignFailure("blocked", "test-design lane requires an independent worker", errors.New(identityConflict))
			}
			return testDesignFailure("blocked", "no pending test-design lane is available", fmt.Errorf("inspect test-design status for active leases or validation readiness"))
		}
		lane := manifest.Lanes[laneIndex]
		lane.State = "leased"
		lane.WorkerID = workerID
		lane.AttemptID = testDesignNextAttemptID(manifest)
		lane.AttemptNumber++
		manifest.Lanes[laneIndex] = lane
		state.Revision++
		if writeErr := service.writeStateAndManifest(root, state, manifest, "test-design.lane-lease"); writeErr != nil {
			return testDesignFailure("error", "cannot lease test-design lane", writeErr)
		}
		checkpointPrefix := service.commandArgv(state, "lane-checkpoint")
		checkpointPrefix = append(checkpointPrefix, "--lane-id", lane.LaneID, "--attempt-id", lane.AttemptID, "--result-json")
		yieldPrefix := service.commandArgv(state, "lane-yield")
		yieldPrefix = append(yieldPrefix, "--lane-id", lane.LaneID, "--attempt-id", lane.AttemptID, "--reason")
		env := NewEnvelope("ok", "test-design lane leased")
		env.Data = testDesignStateData(state, rootRef)
		env.Data["lane_id"] = lane.LaneID
		env.Data["attempt_id"] = lane.AttemptID
		env.Data["worker_id"] = lane.WorkerID
		env.Data["result_protocol"] = testDesignLaneProtocol
		env.Data["required_acceptance"] = "partial"
		env.Data["result_submission_mode"] = "inline_json"
		env.Data["checkpoint_argv_prefix"] = checkpointPrefix
		env.Data["yield_argv_prefix"] = yieldPrefix
		env.Data["packet"] = testDesignLanePacket(lane)
		env.Data["lanes"] = testDesignLaneCounts(manifest)
		return env
	})
}

func (service testDesignService) laneCheckpoint(args []string) Envelope {
	root, rootRef, _, err := service.resolveRoot(optionValue(args, "--feature-dir", ""))
	if err != nil {
		return testDesignFailure("usage-error", "test-design root is invalid", err)
	}
	laneID := strings.TrimSpace(optionValue(args, "--lane-id", ""))
	attemptID := strings.TrimSpace(optionValue(args, "--attempt-id", ""))
	if !testDesignLaneIDPattern.MatchString(laneID) || !testDesignAttemptIDPattern.MatchString(attemptID) {
		return testDesignFailure("usage-error", "test-design lane-checkpoint requires --lane-id and --attempt-id", nil)
	}
	result, err := service.inputObject(args, "--result-json", "test-design lane-checkpoint")
	if err != nil {
		return testDesignFailure("usage-error", "test-design lane result is invalid", err)
	}
	return service.withMutationLock(root, func() Envelope {
		state, readErr := testDesignReadState(root)
		if readErr != nil {
			return testDesignFailure("blocked", "test-design state is unavailable", readErr)
		}
		if revisionErr := testDesignCheckExpectedRevision(args, state); revisionErr != nil {
			return testDesignFailure("blocked", "test-design revision changed", revisionErr)
		}
		manifest, manifestErr := testDesignReadManifest(root)
		if manifestErr != nil {
			return testDesignFailure("blocked", "test-design lane manifest is unavailable", manifestErr)
		}
		laneIndex := testDesignFindLane(manifest, laneID)
		if laneIndex < 0 {
			return testDesignFailure("invalid", "test-design lane does not exist", fmt.Errorf("unknown lane %s", laneID))
		}
		lane := manifest.Lanes[laneIndex]
		if lane.State != "leased" || lane.AttemptID != attemptID {
			return testDesignFailure("blocked", "test-design lane attempt is not active", fmt.Errorf("lane %s is %s with attempt %s", laneID, lane.State, lane.AttemptID))
		}
		if lane.Kind == "discovery" && lane.WorkerID == manifest.LeaderID {
			return testDesignFailure("blocked", "test-design discovery must be performed by an independent subagent", fmt.Errorf("worker %s is the generation leader", lane.WorkerID))
		}
		if validationErr := service.validateLaneResult(result, lane); validationErr != nil {
			return testDesignFailure("invalid", "test-design lane checkpoint is invalid", validationErr)
		}
		if lane.Kind == "audit" {
			if gapErr := service.validateAuditGapAccounting(root, result, lane); gapErr != nil {
				return testDesignFailure("invalid", "test-design audit gap accounting is invalid", gapErr)
			}
		}
		checkpointRaw, marshalErr := testDesignMarshal(result)
		if marshalErr != nil {
			return testDesignFailure("error", "cannot render test-design checkpoint", marshalErr)
		}
		checkpointDigest := testDesignDigest(checkpointRaw)
		lane.CheckpointSequence++
		checkpointRef := filepath.ToSlash(filepath.Join("lane-results", "checkpoints", fmt.Sprintf("%s-%s-%04d-%s.json", lane.LaneID, lane.AttemptID, lane.CheckpointSequence, checkpointDigest[:12])))
		lane.CheckpointRef = checkpointRef
		manifest.Lanes[laneIndex] = lane
		state.Revision++
		updates, updateErr := testDesignFileUpdates(map[string]any{
			filepath.Join(root, "test-state.json"):                 state,
			filepath.Join(root, "lane-manifest.json"):              manifest,
			filepath.Join(root, filepath.FromSlash(checkpointRef)): result,
		})
		if updateErr != nil {
			return testDesignFailure("error", "cannot render test-design checkpoint", updateErr)
		}
		if _, transactionErr := applyFileTransaction(service.projectRoot, "test-design.lane-checkpoint", updates); transactionErr != nil {
			return testDesignFailure("error", "cannot persist test-design checkpoint", transactionErr)
		}
		env := NewEnvelope("ok", "test-design lane checkpoint persisted")
		env.Data = testDesignStateData(state, rootRef)
		env.Data["lane_id"] = lane.LaneID
		env.Data["attempt_id"] = lane.AttemptID
		env.Data["sequence"] = lane.CheckpointSequence
		env.Data["checkpoint_ref"] = checkpointRef
		env.NextArgv = append(service.commandArgv(state, "lane-accept"), "--lane-id", lane.LaneID, "--attempt-id", lane.AttemptID)
		return env
	})
}

func (service testDesignService) laneYield(args []string) Envelope {
	root, rootRef, _, err := service.resolveRoot(optionValue(args, "--feature-dir", ""))
	if err != nil {
		return testDesignFailure("usage-error", "test-design root is invalid", err)
	}
	laneID := strings.TrimSpace(optionValue(args, "--lane-id", ""))
	attemptID := strings.TrimSpace(optionValue(args, "--attempt-id", ""))
	reason := strings.TrimSpace(optionValue(args, "--reason", ""))
	if !testDesignLaneIDPattern.MatchString(laneID) || !testDesignAttemptIDPattern.MatchString(attemptID) {
		return testDesignFailure("usage-error", "test-design lane-yield requires --lane-id and --attempt-id", nil)
	}
	if reason == "" {
		return testDesignFailure("usage-error", "test-design lane-yield requires a non-empty --reason", nil)
	}
	return service.withMutationLock(root, func() Envelope {
		state, readErr := testDesignReadState(root)
		if readErr != nil {
			return testDesignFailure("blocked", "test-design state is unavailable", readErr)
		}
		manifest, manifestErr := testDesignReadManifest(root)
		if manifestErr != nil {
			return testDesignFailure("blocked", "test-design lane manifest is unavailable", manifestErr)
		}
		laneIndex := testDesignFindLane(manifest, laneID)
		if laneIndex < 0 {
			return testDesignFailure("invalid", "test-design lane does not exist", fmt.Errorf("unknown lane %s", laneID))
		}
		lane := manifest.Lanes[laneIndex]
		if lane.State != "leased" || lane.AttemptID != attemptID {
			return testDesignFailure("blocked", "test-design lane attempt is not active", nil)
		}
		lane.YieldHistory = append(lane.YieldHistory, testDesignLaneYield{
			AttemptID:     lane.AttemptID,
			WorkerID:      lane.WorkerID,
			Reason:        reason,
			CheckpointRef: lane.CheckpointRef,
		})
		lane.State = "pending"
		lane.WorkerID = ""
		lane.AttemptID = ""
		manifest.Lanes[laneIndex] = lane
		state.Revision++
		if writeErr := service.writeStateAndManifest(root, state, manifest, "test-design.lane-yield"); writeErr != nil {
			return testDesignFailure("error", "cannot yield test-design lane", writeErr)
		}
		env := NewEnvelope("ok", "test-design lane yielded")
		env.Data = testDesignStateData(state, rootRef)
		env.Data["lane_id"] = laneID
		env.Data["checkpoint_ref"] = lane.CheckpointRef
		env.Data["reason"] = reason
		env.NextArgv = service.commandArgv(state, "lane-lease")
		return env
	})
}

func (service testDesignService) laneAccept(args []string) Envelope {
	root, rootRef, _, err := service.resolveRoot(optionValue(args, "--feature-dir", ""))
	if err != nil {
		return testDesignFailure("usage-error", "test-design root is invalid", err)
	}
	laneID := strings.TrimSpace(optionValue(args, "--lane-id", ""))
	attemptID := strings.TrimSpace(optionValue(args, "--attempt-id", ""))
	if !testDesignLaneIDPattern.MatchString(laneID) || !testDesignAttemptIDPattern.MatchString(attemptID) {
		return testDesignFailure("usage-error", "test-design lane-accept requires --lane-id and --attempt-id", nil)
	}
	return service.withMutationLock(root, func() Envelope {
		state, readErr := testDesignReadState(root)
		if readErr != nil {
			return testDesignFailure("blocked", "test-design state is unavailable", readErr)
		}
		if revisionErr := testDesignCheckExpectedRevision(args, state); revisionErr != nil {
			return testDesignFailure("blocked", "test-design revision changed", revisionErr)
		}
		manifest, manifestErr := testDesignReadManifest(root)
		if manifestErr != nil {
			return testDesignFailure("blocked", "test-design lane manifest is unavailable", manifestErr)
		}
		laneIndex := testDesignFindLane(manifest, laneID)
		if laneIndex < 0 {
			return testDesignFailure("invalid", "test-design lane does not exist", fmt.Errorf("unknown lane %s", laneID))
		}
		lane := manifest.Lanes[laneIndex]
		if lane.State == "accepted" && lane.AttemptID == attemptID {
			env := NewEnvelope("ok", "test-design lane was already accepted")
			env.Data = testDesignStateData(state, rootRef)
			env.Data["lane_id"] = laneID
			env.Data["result_ref"] = lane.ResultRef
			return env
		}
		if lane.State != "leased" || lane.AttemptID != attemptID {
			return testDesignFailure("blocked", "test-design lane attempt is not active", nil)
		}
		if lane.Kind == "discovery" && lane.WorkerID == manifest.LeaderID {
			return testDesignFailure("blocked", "test-design discovery worker is not independent", fmt.Errorf("worker %s is the generation leader", lane.WorkerID))
		}
		if lane.CheckpointRef == "" {
			return testDesignFailure("blocked", "test-design lane has no checkpoint to accept", nil)
		}
		checkpoint, checkpointErr := testDesignReadObject(filepath.Join(root, filepath.FromSlash(lane.CheckpointRef)))
		if checkpointErr != nil {
			return testDesignFailure("blocked", "test-design checkpoint cannot be read", checkpointErr)
		}
		if validationErr := service.validateLaneResult(checkpoint, lane); validationErr != nil {
			return testDesignFailure("invalid", "test-design checkpoint is no longer valid", validationErr)
		}
		if lane.Kind == "audit" {
			if gapErr := service.validateAuditGapAccounting(root, checkpoint, lane); gapErr != nil {
				return testDesignFailure("invalid", "test-design audit gap accounting is invalid", gapErr)
			}
		}
		if strings.ToLower(strings.TrimSpace(asString(checkpoint["status"]))) != "success" {
			return testDesignFailure("blocked", "test-design lane result is not ready for acceptance", fmt.Errorf("worker status must be success; use lane-yield to continue"))
		}
		if lane.Kind == "audit" {
			if testDesignAuditWorkerConflict(manifest, lane.WorkerID) {
				return testDesignFailure("blocked", "test-design audit worker is not independent", fmt.Errorf("worker %s overlaps the leader, synthesis owner, or an accepted discovery worker", lane.WorkerID))
			}
			if freshnessErr := service.requireFreshSources(state); freshnessErr != nil {
				return service.persistStaleState(root, rootRef, state, freshnessErr)
			}
			currentDigests, digestErr := testDesignBundleDigests(root)
			if digestErr != nil {
				return testDesignFailure("error", "cannot fingerprint audited artifacts", digestErr)
			}
			if !testDesignSameDigests(currentDigests, lane.ArtifactDigests) {
				return testDesignFailure("blocked", "test-design audit packet is stale", fmt.Errorf("canonical artifact digests changed after audit preparation"))
			}
		}
		resultRaw, marshalErr := testDesignMarshal(checkpoint)
		if marshalErr != nil {
			return testDesignFailure("error", "cannot render accepted test-design result", marshalErr)
		}
		resultDigest := testDesignDigest(resultRaw)
		resultRef := filepath.ToSlash(filepath.Join("lane-results", fmt.Sprintf("%s-%s.json", lane.LaneID, resultDigest[:12])))
		lane.State = "accepted"
		lane.ResultRef = resultRef
		lane.ResultSHA256 = resultDigest
		manifest.Lanes[laneIndex] = lane
		if testDesignAllLanesAccepted(manifest) {
			manifest.Status = "accepted"
		}
		state.Lanes.AcceptedResultRefs = testDesignAppendUnique(state.Lanes.AcceptedResultRefs, resultRef)
		if lane.Kind == "audit" {
			state.Audit.Status = "accepted"
			state.Audit.LaneID = testDesignStringPointer(lane.LaneID)
			state.Audit.ResultRef = testDesignStringPointer(resultRef)
		}
		state.Revision++
		updates, updateErr := testDesignFileUpdates(map[string]any{
			filepath.Join(root, "test-state.json"):             state,
			filepath.Join(root, "lane-manifest.json"):          manifest,
			filepath.Join(root, filepath.FromSlash(resultRef)): checkpoint,
		})
		if updateErr != nil {
			return testDesignFailure("error", "cannot render test-design acceptance", updateErr)
		}
		if _, transactionErr := applyFileTransaction(service.projectRoot, "test-design.lane-accept", updates); transactionErr != nil {
			return testDesignFailure("error", "cannot accept test-design lane", transactionErr)
		}
		env := NewEnvelope("ok", "test-design lane accepted")
		env.Data = testDesignStateData(state, rootRef)
		env.Data["lane_id"] = laneID
		env.Data["attempt_id"] = attemptID
		env.Data["result_ref"] = resultRef
		env.Data["result_sha256"] = lane.ResultSHA256
		env.Data["lanes"] = testDesignLaneCounts(manifest)
		return env
	})
}

func (service testDesignService) gapReconcile(args []string) Envelope {
	leaderID := strings.TrimSpace(optionValue(args, "--leader-id", ""))
	if !testDesignWorkerIDPattern.MatchString(leaderID) {
		return testDesignFailure("usage-error", "test-design gap-reconcile requires a valid --leader-id", nil)
	}
	if !hasFlag(args, "--expected-revision") {
		return testDesignFailure("usage-error", "test-design gap-reconcile requires --expected-revision", nil)
	}
	root, rootRef, _, err := service.resolveRoot(optionValue(args, "--feature-dir", ""))
	if err != nil {
		return testDesignFailure("usage-error", "test-design root is invalid", err)
	}
	input, err := service.inputObject(args, "--input-json", "test-design gap-reconcile")
	if err != nil {
		return testDesignFailure("usage-error", "test-design gap reconciliation input is invalid", err)
	}
	rawGaps, ok := input["gaps"].([]any)
	if !ok || len(rawGaps) == 0 || len(input) != 1 {
		return testDesignFailure("invalid", "test-design gap-reconcile input must contain only a non-empty gaps array", nil)
	}
	return service.withMutationLock(root, func() Envelope {
		state, readErr := testDesignReadState(root)
		if readErr != nil {
			return testDesignFailure("blocked", "test-design state is unavailable", readErr)
		}
		if revisionErr := testDesignCheckExpectedRevision(args, state); revisionErr != nil {
			return testDesignFailure("blocked", "test-design revision changed", revisionErr)
		}
		if state.Phase != "discovery" && state.Phase != "audit" {
			return testDesignFailure("blocked", "test-design gaps can only be reconciled after discovery or an accepted audit", fmt.Errorf("current phase is %s", state.Phase))
		}
		manifest, manifestErr := testDesignReadManifest(root)
		if manifestErr != nil {
			return testDesignFailure("blocked", "test-design lane manifest is unavailable", manifestErr)
		}
		if manifest.LeaderID == "" || manifest.LeaderID != leaderID {
			return testDesignFailure("blocked", "test-design gap reconciliation leader does not own this generation", fmt.Errorf("expected leader_id %s", manifest.LeaderID))
		}
		if independenceErr := testDesignValidateWorkerIndependence(manifest); independenceErr != nil {
			return testDesignFailure("blocked", "test-design discovery worker independence is not proven", independenceErr)
		}
		if !testDesignKindLanesAccepted(manifest, "discovery", true) {
			return testDesignFailure("blocked", "test-design gap reconciliation requires accepted discovery lanes", nil)
		}
		if state.Phase == "audit" && (state.Audit.Status != "accepted" || state.Audit.ResultRef == nil || strings.TrimSpace(*state.Audit.ResultRef) == "") {
			return testDesignFailure("blocked", "test-design audit repair requires an accepted audit result", nil)
		}
		if freshnessErr := service.requireFreshSources(state); freshnessErr != nil {
			return service.persistStaleState(root, rootRef, state, freshnessErr)
		}
		bundle, bundleErr := testDesignReadBundle(root)
		if bundleErr != nil {
			return testDesignFailure("invalid", "test-design bundle cannot be read", bundleErr)
		}
		proposalKinds := map[string]bool{"discovery": true}
		if state.Phase == "audit" {
			proposalKinds["audit"] = true
		}
		proposalIDs, proposalErr := service.acceptedGapProposalIDs(root, manifest, proposalKinds)
		if proposalErr != nil {
			return testDesignFailure("blocked", "accepted discovery gap proposals are invalid", proposalErr)
		}
		incomingPayload := map[string]any{"schema_version": testDesignGapsSchema, "status": "qualified", "gaps": rawGaps}
		incoming, validationErr := testDesignValidateGaps(incomingPayload)
		if validationErr != nil {
			return testDesignFailure("invalid", "test-design gap proposal is invalid", validationErr)
		}
		for gapID := range incoming {
			if !proposalIDs[gapID] {
				return testDesignFailure("invalid", "test-design gap was not proposed by an accepted discovery worker", fmt.Errorf("unproposed gap %s", gapID))
			}
		}
		existing, indexErr := testDesignIndexRows(bundle.Gaps["gaps"], "gap_id", "test-gaps gaps")
		if indexErr != nil {
			return testDesignFailure("invalid", "existing test-design gaps are invalid", indexErr)
		}
		for gapID, gap := range incoming {
			existing[gapID] = gap
		}
		bundle.Gaps["gaps"] = testDesignSortedObjectRows(existing)
		bundle.Gaps["status"] = testDesignGapCollectionStatus(existing)
		if reconcileErr := testDesignReconcileGapLinks(&bundle, existing); reconcileErr != nil {
			return testDesignFailure("invalid", "test-design gap links cannot be reconciled", reconcileErr)
		}
		if validationErr := testDesignValidateBundle(bundle); validationErr != nil {
			return testDesignFailure("invalid", "reconciled test-design bundle is invalid", validationErr)
		}
		if evidenceErr := service.validateBundleEvidence(bundle); evidenceErr != nil {
			return testDesignFailure("invalid", "reconciled test-design evidence is invalid", evidenceErr)
		}
		state.Status = "active"
		// Preserve audit phase so the repaired bundle must be explicitly
		// re-synthesized before a fresh audit wave can be prepared.
		state.ClaimStatus = "pending"
		state.Revision++
		updates, updateErr := testDesignFileUpdates(map[string]any{
			filepath.Join(root, "test-state.json"):      state,
			filepath.Join(root, "test-universe.json"):   bundle.Universe,
			filepath.Join(root, "coverage-matrix.json"): bundle.CoverageMatrix,
			filepath.Join(root, "test-gaps.json"):       bundle.Gaps,
		})
		if updateErr != nil {
			return testDesignFailure("error", "cannot render reconciled test-design gaps", updateErr)
		}
		if _, transactionErr := applyFileTransaction(service.projectRoot, "test-design.gap-reconcile", updates); transactionErr != nil {
			return testDesignFailure("error", "cannot persist reconciled test-design gaps", transactionErr)
		}
		env := NewEnvelope("ok", "test-design gaps reconciled")
		env.Data = testDesignStateData(state, rootRef)
		env.Data["gap_ids"] = testDesignSortedMapKeys(incoming)
		env.Data["gap_status"] = bundle.Gaps["status"]
		env.NextArgv = append(service.commandArgv(state, "synthesize"), "--leader-id", leaderID)
		return env
	})
}

func (service testDesignService) synthesize(args []string) Envelope {
	leaderID := strings.TrimSpace(optionValue(args, "--leader-id", ""))
	if !testDesignWorkerIDPattern.MatchString(leaderID) {
		return testDesignFailure("usage-error", "test-design synthesize requires a valid --leader-id", nil)
	}
	root, rootRef, _, err := service.resolveRoot(optionValue(args, "--feature-dir", ""))
	if err != nil {
		return testDesignFailure("usage-error", "test-design root is invalid", err)
	}
	return service.withMutationLock(root, func() Envelope {
		state, readErr := testDesignReadState(root)
		if readErr != nil {
			return testDesignFailure("blocked", "test-design state is unavailable", readErr)
		}
		if revisionErr := testDesignCheckExpectedRevision(args, state); revisionErr != nil {
			return testDesignFailure("blocked", "test-design revision changed", revisionErr)
		}
		manifest, manifestErr := testDesignReadManifest(root)
		if manifestErr != nil {
			return testDesignFailure("blocked", "test-design lane manifest is unavailable", manifestErr)
		}
		if manifest.LeaderID == "" || manifest.LeaderID != leaderID {
			return testDesignFailure("blocked", "test-design synthesis leader does not own this generation", fmt.Errorf("expected leader_id %s", manifest.LeaderID))
		}
		if state.Phase != "discovery" && state.Phase != "audit" {
			return testDesignFailure("blocked", "test-design synthesis is not allowed from the current phase", fmt.Errorf("current phase is %s; use CAS init to begin a new generation after validation or handoff", state.Phase))
		}
		if independenceErr := testDesignValidateWorkerIndependence(manifest); independenceErr != nil {
			return testDesignFailure("blocked", "test-design discovery worker independence is not proven", independenceErr)
		}
		if !testDesignKindLanesAccepted(manifest, "discovery", true) {
			return testDesignFailure("blocked", "test-design discovery lanes are incomplete", fmt.Errorf("every discovery lane must be runtime-accepted before synthesis"))
		}
		repairWave := state.Phase == "audit"
		if repairWave && (state.Audit.Status != "accepted" || state.Audit.ResultRef == nil || strings.TrimSpace(*state.Audit.ResultRef) == "") {
			return testDesignFailure("blocked", "test-design audit repair cannot be synthesized before the audit result is accepted", nil)
		}
		if freshnessErr := service.requireFreshSources(state); freshnessErr != nil {
			return service.persistStaleState(root, rootRef, state, freshnessErr)
		}
		bundle, bundleErr := testDesignReadBundle(root)
		if bundleErr != nil {
			return testDesignFailure("invalid", "test-design bundle cannot be read", bundleErr)
		}
		if validationErr := testDesignValidateBundle(bundle); validationErr != nil {
			return testDesignFailure("invalid", "test-design synthesis bundle is invalid", validationErr)
		}
		if evidenceErr := service.validateBundleEvidence(bundle); evidenceErr != nil {
			return testDesignFailure("invalid", "test-design synthesis evidence is invalid", evidenceErr)
		}
		if laneCoverageErr := testDesignValidateLaneObligationCoverage(manifest, bundle); laneCoverageErr != nil {
			return testDesignFailure("blocked", "test-design discovery lanes do not account for the frozen obligations", laneCoverageErr)
		}
		if joinErr := service.validateAcceptedProposals(root, manifest, bundle); joinErr != nil {
			return testDesignFailure("blocked", "test-design synthesis has unjoined worker proposals", joinErr)
		}
		digests, digestErr := testDesignBundleDigests(root)
		if digestErr != nil {
			return testDesignFailure("error", "cannot fingerprint synthesized artifacts", digestErr)
		}
		state.Phase = "synthesis"
		state.Status = "active"
		state.ClaimStatus = "pending"
		if repairWave {
			auditRefs := map[string]bool{}
			retained := make([]testDesignLane, 0, len(manifest.Lanes))
			for _, lane := range manifest.Lanes {
				if lane.Kind == "audit" {
					if lane.ResultRef != "" {
						auditRefs[lane.ResultRef] = true
					}
					continue
				}
				retained = append(retained, lane)
			}
			manifest.Lanes = retained
			acceptedRefs := make([]string, 0, len(state.Lanes.AcceptedResultRefs))
			for _, ref := range state.Lanes.AcceptedResultRefs {
				if !auditRefs[ref] {
					acceptedRefs = append(acceptedRefs, ref)
				}
			}
			state.Lanes.AcceptedResultRefs = acceptedRefs
			state.Audit = testDesignStateAudit{Status: "pending"}
		}
		manifest.SynthesisArtifactDigests = testDesignCloneDigests(digests)
		manifest.SynthesisOwnerID = leaderID
		state.Revision++
		if writeErr := service.writeStateAndManifest(root, state, manifest, "test-design.synthesize"); writeErr != nil {
			return testDesignFailure("error", "cannot persist synthesis state", writeErr)
		}
		env := NewEnvelope("ok", "test-design synthesis accepted")
		env.Data = testDesignStateData(state, rootRef)
		env.Data["artifact_digests"] = digests
		env.NextArgv = service.commandArgv(state, "audit-prepare")
		return env
	})
}

func (service testDesignService) auditPrepare(args []string) Envelope {
	root, rootRef, _, err := service.resolveRoot(optionValue(args, "--feature-dir", ""))
	if err != nil {
		return testDesignFailure("usage-error", "test-design root is invalid", err)
	}
	return service.withMutationLock(root, func() Envelope {
		state, readErr := testDesignReadState(root)
		if readErr != nil {
			return testDesignFailure("blocked", "test-design state is unavailable", readErr)
		}
		if revisionErr := testDesignCheckExpectedRevision(args, state); revisionErr != nil {
			return testDesignFailure("blocked", "test-design revision changed", revisionErr)
		}
		if state.Phase != "synthesis" {
			return testDesignFailure("blocked", "test-design audit requires accepted synthesis", fmt.Errorf("current phase is %s", state.Phase))
		}
		if freshnessErr := service.requireFreshSources(state); freshnessErr != nil {
			return service.persistStaleState(root, rootRef, state, freshnessErr)
		}
		digests, digestErr := testDesignBundleDigests(root)
		if digestErr != nil {
			return testDesignFailure("error", "cannot fingerprint audit inputs", digestErr)
		}
		manifest, manifestErr := testDesignReadManifest(root)
		if manifestErr != nil {
			return testDesignFailure("blocked", "test-design lane manifest is unavailable", manifestErr)
		}
		if !testDesignSameDigests(digests, manifest.SynthesisArtifactDigests) {
			return testDesignFailure("blocked", "test-design synthesis changed before audit", fmt.Errorf("rerun synthesize against the current artifacts"))
		}
		auditNumber := manifest.AuditSequence + 1
		for _, lane := range manifest.Lanes {
			if lane.Kind == "audit" {
				var candidate int
				if _, scanErr := fmt.Sscanf(lane.LaneID, "AUDIT-%d", &candidate); scanErr == nil && candidate >= auditNumber {
					auditNumber = candidate + 1
				}
			}
		}
		auditID := fmt.Sprintf("AUDIT-%03d", auditNumber)
		manifest.AuditSequence = auditNumber
		bundle, bundleErr := testDesignReadBundle(root)
		if bundleErr != nil {
			return testDesignFailure("invalid", "test-design audit inputs cannot be read", bundleErr)
		}
		if manifest.SynthesisOwnerID == "" || manifest.SynthesisOwnerID != manifest.LeaderID {
			return testDesignFailure("blocked", "test-design audit requires an explicit synthesis owner", fmt.Errorf("rerun synthesize with the generation leader"))
		}
		obligationIDs := testDesignUniverseObligationRefs(bundle.Universe)
		if len(obligationIDs) == 0 {
			return testDesignFailure("blocked", "test-design audit has no frozen obligations", nil)
		}
		auditReadPaths := []string{
			filepath.ToSlash(filepath.Join(rootRef, "test-universe.json")),
			filepath.ToSlash(filepath.Join(rootRef, "test-catalog.json")),
			filepath.ToSlash(filepath.Join(rootRef, "test-data-manifest.json")),
			filepath.ToSlash(filepath.Join(rootRef, "coverage-matrix.json")),
			filepath.ToSlash(filepath.Join(rootRef, "test-gaps.json")),
		}
		manifest.Lanes = append(manifest.Lanes, testDesignLane{
			LaneID:            auditID,
			Kind:              "audit",
			Title:             "Independent completeness and freshness audit",
			State:             "pending",
			ObligationIDs:     obligationIDs,
			ReadPaths:         auditReadPaths,
			Questions:         []string{"Find unaccounted obligations, circular oracles, stale evidence, unsafe data, unresolved contradictions, and unsupported completeness claims."},
			SourceFingerprint: state.Source.Fingerprint,
			ArtifactDigests:   testDesignCloneDigests(digests),
		})
		manifest.Status = "active"
		state.Phase = "audit"
		state.Status = "active"
		state.Audit.Status = "prepared"
		state.Audit.LaneID = testDesignStringPointer(auditID)
		state.Audit.ResultRef = nil
		state.Revision++
		if writeErr := service.writeStateAndManifest(root, state, manifest, "test-design.audit-prepare"); writeErr != nil {
			return testDesignFailure("error", "cannot prepare test-design audit", writeErr)
		}
		env := NewEnvelope("ok", "independent test-design audit prepared")
		env.Data = testDesignStateData(state, rootRef)
		env.Data["lane_id"] = auditID
		env.Data["artifact_digests"] = digests
		env.NextArgv = service.commandArgv(state, "lane-lease")
		return env
	})
}

func (service testDesignService) validate(args []string) Envelope {
	root, rootRef, _, err := service.resolveRoot(optionValue(args, "--feature-dir", ""))
	if err != nil {
		return testDesignFailure("usage-error", "test-design root is invalid", err)
	}
	return service.withMutationLock(root, func() Envelope {
		state, readErr := testDesignReadState(root)
		if readErr != nil {
			return testDesignFailure("blocked", "test-design state is unavailable", readErr)
		}
		if revisionErr := testDesignCheckExpectedRevision(args, state); revisionErr != nil {
			return testDesignFailure("blocked", "test-design revision changed", revisionErr)
		}
		if state.Phase != "audit" || state.Audit.Status != "accepted" || state.Audit.ResultRef == nil || strings.TrimSpace(*state.Audit.ResultRef) == "" {
			return testDesignFailure("blocked", "test-design validation requires the current accepted audit wave", fmt.Errorf("current phase/audit status is %s/%s", state.Phase, state.Audit.Status))
		}
		if freshnessErr := service.requireFreshSources(state); freshnessErr != nil {
			return service.persistStaleState(root, rootRef, state, freshnessErr)
		}
		bundle, bundleErr := testDesignReadBundle(root)
		if bundleErr != nil {
			return testDesignFailure("invalid", "test-design bundle cannot be read", bundleErr)
		}
		if validationErr := testDesignValidateBundle(bundle); validationErr != nil {
			return testDesignFailure("invalid", "test-design bundle validation failed", validationErr)
		}
		if evidenceErr := service.validateBundleEvidence(bundle); evidenceErr != nil {
			return testDesignFailure("invalid", "test-design bundle evidence validation failed", evidenceErr)
		}
		digests, digestErr := testDesignBundleDigests(root)
		if digestErr != nil {
			return testDesignFailure("error", "cannot fingerprint validated artifacts", digestErr)
		}
		manifest, manifestErr := testDesignReadManifest(root)
		if manifestErr != nil {
			return testDesignFailure("blocked", "test-design lane manifest is unavailable", manifestErr)
		}
		if !testDesignKindLanesAccepted(manifest, "discovery", true) || !testDesignKindLanesAccepted(manifest, "audit", true) {
			return testDesignFailure("blocked", "test-design validation requires accepted discovery and audit lanes", nil)
		}
		if _, bindingErr := testDesignValidateStateAuditBinding(state, manifest); bindingErr != nil {
			return testDesignFailure("blocked", "test-design state is not bound to the accepted audit lane", bindingErr)
		}
		if auditErr := service.validateAuditResults(root, manifest, state.Source.Fingerprint, digests); auditErr != nil {
			return testDesignFailure("blocked", "test-design independent audit is unresolved", auditErr)
		}
		claimStatus := testDesignClassifyClaim(bundle)
		state.Phase = "validated"
		state.ClaimStatus = claimStatus
		state.Revision++
		if claimStatus == "blocked" {
			state.Status = "blocked"
		} else {
			state.Status = "ready"
		}
		if writeErr := service.writeState(root, state, "test-design.validate"); writeErr != nil {
			return testDesignFailure("error", "cannot persist test-design validation", writeErr)
		}
		status := "ok"
		if claimStatus == "blocked" {
			status = "blocked"
		}
		env := NewEnvelope(status, "test-design validation complete")
		env.Data = testDesignStateData(state, rootRef)
		env.Data["claim_status"] = claimStatus
		env.Data["artifact_digests"] = digests
		if status == "ok" {
			nextCommand := "handoff"
			if state.Scope == "project" {
				nextCommand = "publish"
			}
			env.NextArgv = service.commandArgv(state, nextCommand)
		}
		return env
	})
}

func (service testDesignService) publish(args []string) Envelope {
	if strings.TrimSpace(optionValue(args, "--expected-revision", "")) == "" {
		return testDesignFailure("usage-error", "test-design publish requires --expected-revision", nil)
	}
	root, rootRef, _, err := service.resolveRoot(optionValue(args, "--feature-dir", ""))
	if err != nil {
		return testDesignFailure("usage-error", "test-design root is invalid", err)
	}
	return service.withMutationLock(root, func() Envelope {
		state, readErr := testDesignReadState(root)
		if readErr != nil {
			return testDesignFailure("blocked", "test-design state is unavailable", readErr)
		}
		if revisionErr := testDesignCheckExpectedRevision(args, state); revisionErr != nil {
			return testDesignFailure("blocked", "test-design revision changed", revisionErr)
		}
		if state.Phase != "validated" && state.Phase != "handed-off" {
			return testDesignFailure("blocked", "test-design publish requires a validated bundle", fmt.Errorf("current phase is %s", state.Phase))
		}
		publicationPath, pathErr := service.containedArtifactPath(root, testDesignPublicationFile)
		if pathErr != nil {
			return testDesignFailure("blocked", "test-design publication path is unsafe", pathErr)
		}
		if _, statErr := os.Lstat(publicationPath); statErr == nil {
			if binding, verifyErr := service.verifyPublication(root); verifyErr == nil {
				return testDesignPublicationEnvelope(binding, state, rootRef, "test-design publication already current")
			}
		} else if !errors.Is(statErr, os.ErrNotExist) {
			return testDesignFailure("blocked", "test-design publication cannot be inspected", statErr)
		}
		snapshot, snapshotErr := service.preparePublicationSnapshot(root, state)
		if snapshotErr != nil {
			return testDesignFailure("blocked", "test-design publication inputs are stale or invalid", snapshotErr)
		}
		updates, updateErr := testDesignFileUpdates(map[string]any{publicationPath: snapshot.Publication})
		if updateErr != nil {
			return testDesignFailure("error", "cannot render test-design publication", updateErr)
		}
		if _, transactionErr := applyFileTransaction(service.projectRoot, "test-design.publish", updates); transactionErr != nil {
			return testDesignFailure("error", "cannot publish test-design bundle", transactionErr)
		}
		binding, verifyErr := service.verifyPublication(root)
		if verifyErr != nil {
			return testDesignFailure("error", "published test-design bundle failed verification", verifyErr)
		}
		return testDesignPublicationEnvelope(binding, snapshot.State, rootRef, "test-design publication created")
	})
}

func testDesignPublicationEnvelope(binding testDesignPublicationBinding, state testDesignState, rootRef, summary string) Envelope {
	env := NewEnvelope("ok", summary)
	env.Data = testDesignStateData(state, rootRef)
	env.Data["publication_ref"] = binding.Ref
	env.Data["publication_sha256"] = binding.SHA256
	env.Data["test_execution_status"] = "not_executed_by_test_design"
	return env
}

func (service testDesignService) preparePublicationSnapshot(root string, state testDesignState) (testDesignPublicationSnapshot, error) {
	var snapshot testDesignPublicationSnapshot
	if state.Phase != "validated" && state.Phase != "handed-off" {
		return snapshot, fmt.Errorf("current phase %s is not eligible for publication", state.Phase)
	}
	if state.ClaimStatus != "complete_against_frozen_scope" && state.ClaimStatus != "qualified_with_declared_gaps" {
		return snapshot, fmt.Errorf("claim_status %s is not eligible for publication", state.ClaimStatus)
	}
	if err := service.requireFreshSources(state); err != nil {
		return snapshot, fmt.Errorf("test-design sources are stale: %w", err)
	}
	bundle, err := testDesignReadBundle(root)
	if err != nil {
		return snapshot, err
	}
	if err := testDesignValidateBundle(bundle); err != nil {
		return snapshot, err
	}
	if err := service.validateBundleEvidence(bundle); err != nil {
		return snapshot, err
	}
	if classified := testDesignClassifyClaim(bundle); classified == "blocked" || classified != state.ClaimStatus {
		return snapshot, fmt.Errorf("claim no longer matches the current bundle: %s", classified)
	}
	digests, err := testDesignBundleDigests(root)
	if err != nil {
		return snapshot, err
	}
	manifest, err := testDesignReadManifest(root)
	if err != nil {
		return snapshot, err
	}
	if _, err := testDesignValidateStateAuditBinding(state, manifest); err != nil {
		return snapshot, err
	}
	if err := service.validateAuditResults(root, manifest, state.Source.Fingerprint, digests); err != nil {
		return snapshot, err
	}
	if state.Audit.Status != "accepted" || state.Audit.ResultRef == nil || strings.TrimSpace(*state.Audit.ResultRef) == "" {
		return snapshot, fmt.Errorf("test-design state has no accepted audit result")
	}
	stateRaw, err := testDesignMarshal(state)
	if err != nil {
		return snapshot, err
	}
	statePath, err := service.containedArtifactPath(root, "test-state.json")
	if err != nil {
		return snapshot, err
	}
	onDiskStateRaw, err := testDesignReadRegularFile(statePath)
	if err != nil {
		return snapshot, err
	}
	if !bytes.Equal(onDiskStateRaw, stateRaw) {
		return snapshot, fmt.Errorf("test-state.json is non-canonical or changed outside the runtime")
	}
	auditResultPath, err := service.containedArtifactPath(root, *state.Audit.ResultRef)
	if err != nil {
		return snapshot, err
	}
	auditRaw, err := testDesignReadRegularFile(auditResultPath)
	if err != nil {
		return snapshot, err
	}
	artifactDigests := map[string]any{
		"state":           testDesignDigest(stateRaw),
		"universe":        digests["test-universe.json"],
		"catalog":         digests["test-catalog.json"],
		"data_manifest":   digests["test-data-manifest.json"],
		"coverage_matrix": digests["coverage-matrix.json"],
		"gaps":            digests["test-gaps.json"],
		"audit_result":    testDesignDigest(auditRaw),
	}
	publicationID := "tdpub-" + canonicalJSONSHA256(map[string]any{
		"scope": state.Scope, "artifact_root": state.ArtifactRoot, "source_fingerprint": state.Source.Fingerprint,
		"state_revision": state.Revision, "claim_status": state.ClaimStatus, "artifact_digests": artifactDigests,
	})[:24]
	publication := map[string]any{
		"schema_version":     testDesignPublicationV1,
		"publication_id":     publicationID,
		"scope":              state.Scope,
		"artifact_root":      state.ArtifactRoot,
		"source_fingerprint": state.Source.Fingerprint,
		"state_revision":     state.Revision,
		"claim_status":       state.ClaimStatus,
		"artifact_refs": map[string]any{
			"state": "test-state.json", "universe": "test-universe.json", "catalog": "test-catalog.json",
			"data_manifest": "test-data-manifest.json", "coverage_matrix": "coverage-matrix.json", "gaps": "test-gaps.json",
			"audit_result": *state.Audit.ResultRef,
		},
		"artifact_digests":      artifactDigests,
		"obligation_refs":       testDesignObligationPointers(bundle.Universe),
		"test_case_refs":        testDesignCatalogPointers(bundle.Catalog),
		"test_data_refs":        testDesignDataPointers(bundle.DataManifest),
		"coverage_refs":         testDesignCoveragePointers(bundle.CoverageMatrix),
		"gap_ref":               "test-gaps.json",
		"gap_refs":              testDesignGapPointers(bundle.Gaps),
		"audit_result_ref":      *state.Audit.ResultRef,
		"forbidden_claims":      testDesignPublicationForbiddenClaims(),
		"test_execution_status": "not_executed_by_test_design",
	}
	return testDesignPublicationSnapshot{State: state, Bundle: bundle, Publication: publication}, nil
}

func testDesignPublicationForbiddenClaims() []string {
	return []string{"tests_executed", "tests_passed", "behavior_fixed", "implementation_complete", "release_safe", "absolute_complete"}
}

func (service testDesignService) verifyPublication(root string) (testDesignPublicationBinding, error) {
	var binding testDesignPublicationBinding
	publicationPath, err := service.containedArtifactPath(root, testDesignPublicationFile)
	if err != nil {
		return binding, err
	}
	publicationRaw, err := testDesignReadRegularFile(publicationPath)
	if err != nil {
		return binding, err
	}
	publication, err := testDesignReadObject(publicationPath)
	if err != nil {
		return binding, err
	}
	state, err := testDesignReadState(root)
	if err != nil {
		return binding, err
	}
	snapshot, err := service.preparePublicationSnapshot(root, state)
	if err != nil {
		return binding, err
	}
	expectedRaw, err := testDesignMarshal(snapshot.Publication)
	if err != nil {
		return binding, err
	}
	if !bytes.Equal(publicationRaw, expectedRaw) {
		return binding, fmt.Errorf("%s is stale, non-canonical, or contains copied truth", testDesignPublicationFile)
	}
	if strings.TrimSpace(asString(publication["schema_version"])) != testDesignPublicationV1 {
		return binding, fmt.Errorf("%s has an unsupported schema", testDesignPublicationFile)
	}
	artifactDigests, err := testDesignPublicationDigestStrings(publication["artifact_digests"])
	if err != nil {
		return binding, err
	}
	binding = testDesignPublicationBinding{
		Ref:               filepath.ToSlash(filepath.Join(state.ArtifactRoot, testDesignPublicationFile)),
		SHA256:            testDesignDigest(publicationRaw),
		Scope:             state.Scope,
		ArtifactRoot:      state.ArtifactRoot,
		FeatureDir:        state.FeatureDir,
		SourceFingerprint: state.Source.Fingerprint,
		StateRevision:     state.Revision,
		ClaimStatus:       state.ClaimStatus,
		ArtifactDigests:   artifactDigests,
		ObligationRefs:    testDesignStrings(publication["obligation_refs"]),
		TestCaseRefs:      testDesignStrings(publication["test_case_refs"]),
		TestDataRefs:      testDesignStrings(publication["test_data_refs"]),
		CoverageRefs:      testDesignStrings(publication["coverage_refs"]),
		GapRefs:           testDesignStrings(publication["gap_refs"]),
	}
	return binding, nil
}

func testDesignPublicationDigestStrings(value any) (map[string]string, error) {
	raw, ok := value.(map[string]any)
	expected := []string{"state", "universe", "catalog", "data_manifest", "coverage_matrix", "gaps", "audit_result"}
	if !ok || len(raw) != len(expected) {
		return nil, fmt.Errorf("publication artifact_digests must contain exactly seven entries")
	}
	result := map[string]string{}
	for _, key := range expected {
		digest := strings.TrimSpace(asString(raw[key]))
		if !testDesignSHA256Pattern.MatchString(digest) {
			return nil, fmt.Errorf("publication artifact digest %s is invalid", key)
		}
		result[key] = digest
	}
	return result, nil
}

func (service testDesignService) handoff(args []string) Envelope {
	root, rootRef, _, err := service.resolveRoot(optionValue(args, "--feature-dir", ""))
	if err != nil {
		return testDesignFailure("usage-error", "test-design root is invalid", err)
	}
	return service.withMutationLock(root, func() Envelope {
		state, readErr := testDesignReadState(root)
		if readErr != nil {
			return testDesignFailure("blocked", "test-design state is unavailable", readErr)
		}
		if revisionErr := testDesignCheckExpectedRevision(args, state); revisionErr != nil {
			return testDesignFailure("blocked", "test-design revision changed", revisionErr)
		}
		if state.Scope != "feature" || state.FeatureDir == nil || strings.TrimSpace(*state.FeatureDir) == "" {
			return testDesignFailure("blocked", "test-design handoff to tasks requires feature scope", fmt.Errorf("current scope is %s", state.Scope))
		}
		if state.Phase == "handed-off" {
			binding, verifyErr := service.verifyPublishedHandoff(root)
			if verifyErr != nil {
				return testDesignFailure("blocked", "existing test-design handoff is stale or invalid", verifyErr)
			}
			return testDesignLegacyHandoffEnvelope(binding, state, rootRef, "test-design handoff already published")
		}
		if state.Phase != "validated" {
			return testDesignFailure("blocked", "test-design handoff requires a validated bundle", fmt.Errorf("current phase is %s", state.Phase))
		}
		snapshot, snapshotErr := service.preparePublicationSnapshot(root, state)
		if snapshotErr != nil {
			return testDesignFailure("blocked", "test-design handoff inputs are stale or invalid", snapshotErr)
		}
		state.Phase = "handed-off"
		state.Status = "complete"
		state.Revision++
		stateRaw, stateMarshalErr := testDesignMarshal(state)
		if stateMarshalErr != nil {
			return testDesignFailure("error", "cannot render final test-design state", stateMarshalErr)
		}
		digestStrings, digestErr := testDesignPublicationDigestStrings(snapshot.Publication["artifact_digests"])
		if digestErr != nil {
			return testDesignFailure("error", "cannot fingerprint test-design handoff inputs", digestErr)
		}
		artifactDigests := map[string]any{}
		for key, digest := range digestStrings {
			artifactDigests[key] = digest
		}
		digestStrings["state"] = testDesignDigest(stateRaw)
		artifactDigests["state"] = digestStrings["state"]
		handoff := map[string]any{
			"schema_version":     testDesignHandoffSchema,
			"source_fingerprint": state.Source.Fingerprint,
			"state_revision":     state.Revision,
			"claim_status":       state.ClaimStatus,
			"artifact_refs": map[string]any{
				"state":           "test-state.json",
				"universe":        "test-universe.json",
				"catalog":         "test-catalog.json",
				"data_manifest":   "test-data-manifest.json",
				"coverage_matrix": "coverage-matrix.json",
			},
			"artifact_digests": artifactDigests,
			"test_case_refs":   testDesignCatalogPointers(snapshot.Bundle.Catalog),
			"test_data_refs":   testDesignDataPointers(snapshot.Bundle.DataManifest),
			"gap_ref":          "test-gaps.json",
			"audit_result_ref": *state.Audit.ResultRef,
			"next_command":     "/sp.tasks",
		}
		handoffRaw, marshalErr := testDesignMarshal(handoff)
		if marshalErr != nil {
			return testDesignFailure("error", "cannot render test-design handoff", marshalErr)
		}
		handoffPath, pathErr := service.containedArtifactPath(root, "handoff-to-tasks.json")
		if pathErr != nil {
			return testDesignFailure("blocked", "test-design handoff path is unsafe", pathErr)
		}
		statePath, pathErr := service.containedArtifactPath(root, "test-state.json")
		if pathErr != nil {
			return testDesignFailure("blocked", "test-design state path is unsafe", pathErr)
		}
		updates, updateErr := testDesignFileUpdates(map[string]any{handoffPath: handoff, statePath: state})
		if updateErr != nil {
			return testDesignFailure("error", "cannot render test-design handoff transaction", updateErr)
		}
		if _, transactionErr := applyFileTransaction(service.projectRoot, "test-design.handoff", updates); transactionErr != nil {
			return testDesignFailure("error", "cannot publish test-design handoff", transactionErr)
		}
		binding := testDesignPublishedHandoff{
			Ref:               filepath.ToSlash(filepath.Join(rootRef, "handoff-to-tasks.json")),
			SHA256:            testDesignDigest(handoffRaw),
			SourceFingerprint: state.Source.Fingerprint,
			StateRevision:     state.Revision,
			ArtifactDigests:   digestStrings,
			TestCaseRefs:      testDesignCatalogPointers(snapshot.Bundle.Catalog),
			TestDataRefs:      testDesignDataPointers(snapshot.Bundle.DataManifest),
		}
		return testDesignLegacyHandoffEnvelope(binding, state, rootRef, "test-design handoff published")
	})
}

func testDesignLegacyHandoffEnvelope(binding testDesignPublishedHandoff, state testDesignState, rootRef, summary string) Envelope {
	env := NewEnvelope("ok", summary)
	env.Data = testDesignStateData(state, rootRef)
	env.Data["handoff_ref"] = filepath.ToSlash(filepath.Join(rootRef, "handoff-to-tasks.json"))
	env.Data["handoff_sha256"] = binding.SHA256
	env.Data["next_command"] = "/sp.tasks"
	env.NextArgv = []string{"/sp.tasks"}
	return env
}

func (service testDesignService) projectionBuild(args []string) Envelope {
	root, _, _, err := service.resolveRoot(optionValue(args, "--feature-dir", ""))
	if err != nil {
		return testDesignFailure("usage-error", "test-design root is invalid", err)
	}
	return service.withMutationLock(root, func() Envelope {
		consumer := strings.ToLower(strings.TrimSpace(optionValue(args, "--consumer", "")))
		binding, verifyErr := service.verifyPublication(root)
		if verifyErr != nil {
			return testDesignFailure("blocked", "test-design publication is stale or unavailable", verifyErr)
		}
		if consumerErr := testDesignValidateProjectionConsumer(consumer, binding.Scope); consumerErr != nil {
			return testDesignFailure("blocked", "test-design projection consumer is not eligible", consumerErr)
		}
		basisRef, basisRaw, basisErr := service.readProjectionBasis(optionValue(args, "--basis-ref", ""))
		if basisErr != nil {
			return testDesignFailure("blocked", "test-design projection basis is unavailable", basisErr)
		}
		if basisContractErr := testDesignValidateProjectionBasis(binding, consumer, basisRef); basisContractErr != nil {
			return testDesignFailure("blocked", "test-design projection basis is incompatible", basisContractErr)
		}
		bundle, bundleErr := testDesignReadBundle(root)
		if bundleErr != nil {
			return testDesignFailure("blocked", "test-design projection bundle is unavailable", bundleErr)
		}
		selectedIDs, selectionErr := testDesignProjectionObligationIDs(bundle.Universe, optionValue(args, "--obligation-ids", ""), hasFlag(args, "--obligation-ids"))
		if selectionErr != nil {
			return testDesignFailure("invalid", "test-design projection obligation selection is invalid", selectionErr)
		}
		selection, selectionErr := testDesignBuildProjectionSelection(bundle, selectedIDs, consumer)
		if selectionErr != nil {
			return testDesignFailure("invalid", "test-design projection closure is invalid", selectionErr)
		}
		payload := testDesignProjectionPayload(binding, consumer, basisRef, testDesignDigest(basisRaw), selection)
		payloadRaw, marshalErr := testDesignMarshal(payload)
		if marshalErr != nil {
			return testDesignFailure("error", "cannot render test-design projection", marshalErr)
		}
		projectionSHA := testDesignDigest(payloadRaw)
		projectionID := strings.TrimSpace(asString(payload["projection_id"]))
		projectionName := projectionID + ".json"
		projectionPath, pathErr := service.containedArtifactPath(root, filepath.ToSlash(filepath.Join("projections", projectionName)))
		if pathErr != nil {
			return testDesignFailure("blocked", "test-design projection path is unsafe", pathErr)
		}
		existingRaw, readErr := testDesignReadRegularFile(projectionPath)
		needsWrite := readErr == nil && !bytes.Equal(existingRaw, payloadRaw)
		if errors.Is(readErr, os.ErrNotExist) {
			needsWrite = true
		} else if readErr != nil {
			return testDesignFailure("blocked", "test-design projection cannot be inspected", readErr)
		}
		if needsWrite {
			if _, transactionErr := applyFileTransaction(service.projectRoot, "test-design.projection-build", []fileTransactionUpdate{{
				Path: projectionPath, Content: payloadRaw, Perm: 0o644,
			}}); transactionErr != nil {
				return testDesignFailure("error", "cannot publish test-design projection", transactionErr)
			}
		}
		env := NewEnvelope("ok", "test-design projection built")
		env.Data = map[string]any{
			"consumer": consumer, "projection_id": projectionID,
			"projection_ref":    filepath.ToSlash(filepath.Join(binding.ArtifactRoot, "projections", projectionName)),
			"projection_sha256": projectionSHA, "publication_ref": binding.Ref, "publication_sha256": binding.SHA256,
			"basis_ref": basisRef, "basis_sha256": testDesignDigest(basisRaw),
		}
		return env
	})
}

func (service testDesignService) projectionVerify(args []string) Envelope {
	root, _, _, err := service.resolveRoot(optionValue(args, "--feature-dir", ""))
	if err != nil {
		return testDesignFailure("usage-error", "test-design root is invalid", err)
	}
	expectedSHA := strings.ToLower(strings.TrimSpace(optionValue(args, "--expected-sha256", "")))
	if !testDesignSHA256Pattern.MatchString(expectedSHA) {
		return testDesignFailure("usage-error", "projection-verify requires --expected-sha256", fmt.Errorf("expected digest must be 64 lowercase hexadecimal characters"))
	}
	projectionRef := strings.TrimSpace(optionValue(args, "--projection-ref", ""))
	if projectionRef == "" {
		return testDesignFailure("usage-error", "projection-verify requires --projection-ref", nil)
	}
	projectionPath, normalizedRef, projectionRaw, readErr := service.readProjectRegularFile(projectionRef)
	if readErr != nil {
		return testDesignFailure("blocked", "test-design projection is unavailable", readErr)
	}
	rootAbs, err := filepath.Abs(root)
	if err != nil {
		return testDesignFailure("blocked", "test-design projection root is invalid", err)
	}
	projectionRel, err := filepath.Rel(rootAbs, projectionPath)
	if err != nil || projectionRel == ".." || strings.HasPrefix(projectionRel, ".."+string(filepath.Separator)) || !strings.HasPrefix(filepath.ToSlash(projectionRel), "projections/") {
		return testDesignFailure("blocked", "test-design projection escapes its publication root", fmt.Errorf("projection_ref must identify a file under the selected test-design projections directory"))
	}
	actualSHA := testDesignDigest(projectionRaw)
	if actualSHA != expectedSHA {
		return testDesignFailure("blocked", "test-design projection digest is stale", fmt.Errorf("expected %s but found %s", expectedSHA, actualSHA))
	}
	projection, decodeErr := testDesignReadObject(projectionPath)
	if decodeErr != nil {
		return testDesignFailure("blocked", "test-design projection is malformed", decodeErr)
	}
	consumer := strings.ToLower(strings.TrimSpace(asString(projection["consumer"])))
	binding, publicationErr := service.verifyPublication(root)
	if publicationErr != nil {
		return testDesignFailure("blocked", "test-design publication is stale or invalid", publicationErr)
	}
	if consumerErr := testDesignValidateProjectionConsumer(consumer, binding.Scope); consumerErr != nil {
		return testDesignFailure("blocked", "test-design projection consumer is not eligible", consumerErr)
	}
	basisRef := strings.TrimSpace(asString(projection["basis_ref"]))
	normalizedBasisRef, basisRaw, basisErr := service.readProjectionBasis(basisRef)
	if basisErr != nil {
		return testDesignFailure("blocked", "test-design projection basis is unavailable", basisErr)
	}
	if basisContractErr := testDesignValidateProjectionBasis(binding, consumer, normalizedBasisRef); basisContractErr != nil {
		return testDesignFailure("blocked", "test-design projection basis is incompatible", basisContractErr)
	}
	if normalizedBasisRef != basisRef || testDesignDigest(basisRaw) != strings.TrimSpace(asString(projection["basis_sha256"])) {
		return testDesignFailure("blocked", "test-design projection basis is stale", nil)
	}
	selection, ok := projection["selection"].(map[string]any)
	if !ok {
		return testDesignFailure("blocked", "test-design projection selection is malformed", nil)
	}
	selectedIDs, selectionErr := testDesignProjectionIDsFromPointers(selection)
	if selectionErr != nil {
		return testDesignFailure("blocked", "test-design projection selection is malformed", selectionErr)
	}
	bundle, bundleErr := testDesignReadBundle(root)
	if bundleErr != nil {
		return testDesignFailure("blocked", "test-design projection bundle is unavailable", bundleErr)
	}
	expectedSelection, selectionErr := testDesignBuildProjectionSelection(bundle, selectedIDs, consumer)
	if selectionErr != nil {
		return testDesignFailure("blocked", "test-design projection selection is stale", selectionErr)
	}
	expectedPayload := testDesignProjectionPayload(binding, consumer, normalizedBasisRef, testDesignDigest(basisRaw), expectedSelection)
	expectedRaw, marshalErr := testDesignMarshal(expectedPayload)
	if marshalErr != nil {
		return testDesignFailure("error", "cannot verify test-design projection", marshalErr)
	}
	if !bytes.Equal(projectionRaw, expectedRaw) {
		return testDesignFailure("blocked", "test-design projection is stale, non-canonical, or contains copied truth", nil)
	}
	expectedName := strings.TrimSpace(asString(expectedPayload["projection_id"])) + ".json"
	expectedRef := filepath.ToSlash(filepath.Join(binding.ArtifactRoot, "projections", expectedName))
	if normalizedRef != expectedRef {
		return testDesignFailure("blocked", "test-design projection ref does not match its canonical consumer slot", fmt.Errorf("expected %s", expectedRef))
	}
	env := NewEnvelope("ok", "test-design projection is valid and fresh")
	env.Data = map[string]any{
		"valid": true, "fresh": true, "consumer": consumer,
		"projection_ref": normalizedRef, "projection_sha256": actualSHA,
		"publication_ref": binding.Ref, "publication_sha256": binding.SHA256,
		"basis_ref": normalizedBasisRef, "basis_sha256": testDesignDigest(basisRaw),
	}
	return env
}

func testDesignValidateProjectionConsumer(consumer, scope string) error {
	switch consumer {
	case "implement":
		return fmt.Errorf("Implement consumes the Tasks-bound task packet; no independent test-design projection is supported")
	case "plan", "quick":
		return nil
	case "tasks", "review":
		if scope != "feature" {
			return fmt.Errorf("%s projection requires feature scope", consumer)
		}
		return nil
	default:
		return fmt.Errorf("consumer must be plan, quick, tasks, or review")
	}
}

func testDesignValidateProjectionBasis(binding testDesignPublicationBinding, consumer, basisRef string) error {
	basisRef = filepath.ToSlash(filepath.Clean(filepath.FromSlash(strings.TrimSpace(basisRef))))
	if basisRef == "." || basisRef == "" {
		return fmt.Errorf("consumer basis must be a project-relative file")
	}
	if consumer == "quick" {
		parts := strings.Split(basisRef, "/")
		if len(parts) != 4 || parts[0] != ".planning" || parts[1] != "quick" || strings.TrimSpace(parts[2]) == "" || parts[2] == "." || parts[2] == ".." || parts[3] != "confirmation.json" {
			return fmt.Errorf("Quick projection basis must be .planning/quick/<id>/confirmation.json")
		}
		return nil
	}
	if binding.Scope != "feature" {
		return nil
	}
	if binding.FeatureDir == nil || strings.TrimSpace(*binding.FeatureDir) == "" {
		return fmt.Errorf("feature publication has no feature directory binding")
	}
	featureDir := strings.TrimSuffix(filepath.ToSlash(filepath.Clean(filepath.FromSlash(*binding.FeatureDir))), "/")
	switch consumer {
	case "plan":
		if basisRef != featureDir+"/spec-contract.json" {
			return fmt.Errorf("Plan projection basis must be the selected feature spec-contract.json")
		}
	case "tasks":
		if basisRef != featureDir+"/plan-contract.json" && basisRef != featureDir+"/plan/plan-contract.json" {
			return fmt.Errorf("Tasks projection basis must be the selected feature plan-contract.json")
		}
	case "review":
		if basisRef != featureDir+"/implementation-handoff.json" {
			return fmt.Errorf("Review projection basis must be the selected feature implementation-handoff.json")
		}
	}
	return nil
}

func (service testDesignService) readProjectionBasis(ref string) (string, []byte, error) {
	_, normalized, raw, err := service.readProjectRegularFile(ref)
	return normalized, raw, err
}

func (service testDesignService) readProjectRegularFile(ref string) (string, string, []byte, error) {
	ref = strings.TrimSpace(ref)
	if ref == "" || filepath.IsAbs(ref) {
		return "", "", nil, fmt.Errorf("project-relative file ref is required")
	}
	projectRoot, err := filepath.Abs(service.projectRoot)
	if err != nil {
		return "", "", nil, err
	}
	projectRoot, err = filepath.EvalSymlinks(projectRoot)
	if err != nil {
		return "", "", nil, err
	}
	path, err := testDesignResolveProjectPath(projectRoot, ref)
	if err != nil {
		return "", "", nil, err
	}
	normalized, err := filepath.Rel(projectRoot, path)
	if err != nil || normalized == ".." || strings.HasPrefix(normalized, ".."+string(filepath.Separator)) {
		return "", "", nil, fmt.Errorf("file ref escapes the project root")
	}
	raw, err := testDesignReadRegularFile(path)
	if err != nil {
		return "", "", nil, err
	}
	return path, filepath.ToSlash(normalized), raw, nil
}

func testDesignProjectionObligationIDs(universe map[string]any, raw string, explicitlySet bool) ([]string, error) {
	all := testDesignUniverseObligationRefs(universe)
	if len(all) == 0 {
		return nil, fmt.Errorf("published test-design universe has no obligations")
	}
	if !explicitlySet {
		return all, nil
	}
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return nil, fmt.Errorf("--obligation-ids must contain at least one TO-* id")
	}
	allowed := map[string]bool{}
	for _, id := range all {
		allowed[id] = true
	}
	seen := map[string]bool{}
	for _, part := range strings.Split(raw, ",") {
		id := strings.TrimSpace(part)
		if !testDesignObligationPattern.MatchString(id) || !allowed[id] {
			return nil, fmt.Errorf("unknown or invalid obligation id %q", id)
		}
		if seen[id] {
			return nil, fmt.Errorf("duplicate obligation id %s", id)
		}
		seen[id] = true
	}
	return testDesignSortedKeys(seen), nil
}

func testDesignBuildProjectionSelection(bundle testDesignBundle, selectedIDs []string, consumer string) (map[string]any, error) {
	allIDs := testDesignUniverseObligationRefs(bundle.Universe)
	if consumer == "tasks" && !testDesignSameStringSet(selectedIDs, allIDs) {
		return nil, fmt.Errorf("Tasks projection must preserve the full frozen obligation denominator")
	}
	obligations, err := testDesignIndexRows(bundle.Universe["obligations"], "obligation_id", "test-universe obligations")
	if err != nil {
		return nil, err
	}
	cases, err := testDesignIndexRows(bundle.Catalog["cases"], "test_case_id", "test-catalog cases")
	if err != nil {
		return nil, err
	}
	datasets, err := testDesignIndexRows(bundle.DataManifest["datasets"], "test_data_id", "test-data-manifest datasets")
	if err != nil {
		return nil, err
	}
	coverage, err := testDesignIndexRows(bundle.CoverageMatrix["rows"], "coverage_id", "coverage-matrix rows")
	if err != nil {
		return nil, err
	}
	gaps, err := testDesignIndexRows(bundle.Gaps["gaps"], "gap_id", "test-gaps gaps")
	if err != nil {
		return nil, err
	}
	selected := map[string]bool{}
	caseIDs := map[string]bool{}
	dataIDs := map[string]bool{}
	coverageIDs := map[string]bool{}
	gapIDs := map[string]bool{}
	for _, obligationID := range selectedIDs {
		obligation, ok := obligations[obligationID]
		if !ok {
			return nil, fmt.Errorf("selected obligation %s is absent from the universe", obligationID)
		}
		selected[obligationID] = true
		for _, id := range testDesignStrings(obligation["test_case_ids"]) {
			caseIDs[id] = true
		}
		for _, id := range testDesignStrings(obligation["gap_refs"]) {
			gapIDs[id] = true
		}
	}
	for coverageID, row := range coverage {
		if !selected[strings.TrimSpace(asString(row["obligation_ref"]))] {
			continue
		}
		coverageIDs[coverageID] = true
		if caseID := strings.TrimSpace(asString(row["test_case_ref"])); caseID != "" {
			caseIDs[caseID] = true
		}
		for _, id := range testDesignStrings(row["test_data_refs"]) {
			dataIDs[id] = true
		}
		for _, id := range testDesignStrings(row["gap_refs"]) {
			gapIDs[id] = true
		}
	}
	for caseID := range caseIDs {
		candidate, ok := cases[caseID]
		if !ok {
			return nil, fmt.Errorf("selected closure references missing test case %s", caseID)
		}
		for _, id := range testDesignStrings(candidate["test_data_refs"]) {
			dataIDs[id] = true
		}
	}
	for dataID := range dataIDs {
		if _, ok := datasets[dataID]; !ok {
			return nil, fmt.Errorf("selected closure references missing test data %s", dataID)
		}
	}
	for gapID := range gapIDs {
		if _, ok := gaps[gapID]; !ok {
			return nil, fmt.Errorf("selected closure references missing gap %s", gapID)
		}
	}
	return map[string]any{
		"obligation_refs": testDesignPointerList("test-universe.json#/obligations/", testDesignSortedKeys(selected)),
		"test_case_refs":  testDesignPointerList("test-catalog.json#/cases/", testDesignSortedKeys(caseIDs)),
		"test_data_refs":  testDesignPointerList("test-data-manifest.json#/datasets/", testDesignSortedKeys(dataIDs)),
		"coverage_refs":   testDesignPointerList("coverage-matrix.json#/rows/", testDesignSortedKeys(coverageIDs)),
		"gap_refs":        testDesignPointerList("test-gaps.json#/gaps/", testDesignSortedKeys(gapIDs)),
	}, nil
}

func testDesignProjectionPayload(binding testDesignPublicationBinding, consumer, basisRef, basisSHA string, selection map[string]any) map[string]any {
	selectionSHA := canonicalJSONSHA256(selection)
	projectionID := "tdproj-" + canonicalJSONSHA256(map[string]any{
		"consumer": consumer, "basis_ref": basisRef, "selection_sha256": selectionSHA,
	})[:24]
	return map[string]any{
		"schema_version": testDesignProjectionV1, "projection_id": projectionID,
		"publication_ref": binding.Ref, "publication_sha256": binding.SHA256,
		"consumer": consumer, "basis_ref": basisRef, "basis_sha256": basisSHA,
		"scope": binding.Scope, "artifact_root": binding.ArtifactRoot,
		"source_fingerprint": binding.SourceFingerprint, "state_revision": binding.StateRevision, "claim_status": binding.ClaimStatus,
		"selection": selection, "selection_sha256": selectionSHA,
		"forbidden_claims": testDesignPublicationForbiddenClaims(), "test_execution_status": "not_executed_by_test_design",
	}
}

func testDesignProjectionIDsFromPointers(selection map[string]any) ([]string, error) {
	expected := map[string]string{
		"obligation_refs": "test-universe.json#/obligations/", "test_case_refs": "test-catalog.json#/cases/",
		"test_data_refs": "test-data-manifest.json#/datasets/", "coverage_refs": "coverage-matrix.json#/rows/", "gap_refs": "test-gaps.json#/gaps/",
	}
	if len(selection) != len(expected) {
		return nil, fmt.Errorf("selection must contain exactly the five pointer arrays")
	}
	for field, prefix := range expected {
		refs, err := testDesignRequireStringList(selection, field, "projection selection", field == "obligation_refs")
		if err != nil {
			return nil, err
		}
		seen := map[string]bool{}
		for _, ref := range refs {
			if !strings.HasPrefix(ref, prefix) || strings.TrimPrefix(ref, prefix) == "" {
				return nil, fmt.Errorf("selection %s contains non-canonical pointer %s", field, ref)
			}
			if seen[ref] {
				return nil, fmt.Errorf("selection %s contains duplicate pointer %s", field, ref)
			}
			seen[ref] = true
		}
	}
	obligationRefs, _ := testDesignRequireStringList(selection, "obligation_refs", "projection selection", true)
	ids := make([]string, 0, len(obligationRefs))
	for _, ref := range obligationRefs {
		id := strings.TrimPrefix(ref, "test-universe.json#/obligations/")
		if !testDesignObligationPattern.MatchString(id) {
			return nil, fmt.Errorf("selection contains invalid obligation pointer %s", ref)
		}
		ids = append(ids, id)
	}
	sort.Strings(ids)
	return ids, nil
}

func testDesignPointerList(prefix string, ids []string) []string {
	result := make([]string, 0, len(ids))
	for _, id := range ids {
		result = append(result, prefix+id)
	}
	return result
}

func (service testDesignService) verifyPublishedHandoff(root string) (testDesignPublishedHandoff, error) {
	return service.verifyPublishedHandoffWithSourcePolicy(root, true)
}

func (service testDesignService) verifyPublishedHandoffIntegrity(root string) (testDesignPublishedHandoff, error) {
	return service.verifyPublishedHandoffWithSourcePolicy(root, false)
}

func (service testDesignService) verifyPublishedHandoffWithSourcePolicy(root string, requireLiveSourceFreshness bool) (testDesignPublishedHandoff, error) {
	var binding testDesignPublishedHandoff
	handoffPath := filepath.Join(root, "handoff-to-tasks.json")
	info, err := os.Lstat(handoffPath)
	if err != nil {
		return binding, err
	}
	if !info.Mode().IsRegular() || info.Mode()&os.ModeSymlink != 0 {
		return binding, fmt.Errorf("handoff-to-tasks.json must be a regular non-symlink file")
	}
	handoffRaw, err := testDesignReadRegularFile(handoffPath)
	if err != nil {
		return binding, err
	}
	handoff, err := testDesignReadObject(handoffPath)
	if err != nil {
		return binding, err
	}
	if len(handoff) != 11 || strings.TrimSpace(asString(handoff["schema_version"])) != testDesignHandoffSchema || strings.TrimSpace(asString(handoff["next_command"])) != "/sp.tasks" {
		return binding, fmt.Errorf("handoff-to-tasks.json has an unsupported canonical contract")
	}
	statePath := filepath.Join(root, "test-state.json")
	stateRaw, err := testDesignReadRegularFile(statePath)
	if err != nil {
		return binding, err
	}
	state, err := testDesignReadState(root)
	if err != nil {
		return binding, err
	}
	if state.Phase != "handed-off" || state.Status != "complete" {
		return binding, fmt.Errorf("test-design state is not handed-off and complete")
	}
	if state.ClaimStatus != "complete_against_frozen_scope" && state.ClaimStatus != "qualified_with_declared_gaps" {
		return binding, fmt.Errorf("test-design claim %s is not consumable", state.ClaimStatus)
	}
	if intFromAny(handoff["state_revision"]) != state.Revision {
		return binding, fmt.Errorf("test-design handoff state_revision is stale")
	}
	if strings.TrimSpace(asString(handoff["source_fingerprint"])) != state.Source.Fingerprint || strings.TrimSpace(asString(handoff["claim_status"])) != state.ClaimStatus {
		return binding, fmt.Errorf("test-design handoff source or claim does not match state")
	}
	if requireLiveSourceFreshness {
		if freshnessErr := service.requireFreshSources(state); freshnessErr != nil {
			return binding, fmt.Errorf("test-design sources are stale: %w", freshnessErr)
		}
	}
	projectRoot, err := filepath.Abs(service.projectRoot)
	if err != nil {
		return binding, err
	}
	artifactRoot, err := filepath.Abs(root)
	if err != nil {
		return binding, err
	}
	artifactRel, err := filepath.Rel(projectRoot, artifactRoot)
	if err != nil || filepath.ToSlash(artifactRel) != state.ArtifactRoot {
		return binding, fmt.Errorf("test-design artifact root does not match state")
	}
	bundle, err := testDesignReadBundle(root)
	if err != nil {
		return binding, err
	}
	if err := testDesignValidateBundle(bundle); err != nil {
		return binding, err
	}
	if err := service.validateBundleEvidence(bundle); err != nil {
		return binding, err
	}
	classified := testDesignClassifyClaim(bundle)
	if classified == "blocked" || classified != state.ClaimStatus {
		return binding, fmt.Errorf("test-design claim no longer matches the current bundle: %s", classified)
	}
	manifest, err := testDesignReadManifest(root)
	if err != nil {
		return binding, err
	}
	if _, err := testDesignValidateStateAuditBinding(state, manifest); err != nil {
		return binding, err
	}
	digests, err := testDesignBundleDigests(root)
	if err != nil {
		return binding, err
	}
	if err := service.validateAuditResults(root, manifest, state.Source.Fingerprint, digests); err != nil {
		return binding, err
	}
	if state.Audit.Status != "accepted" || state.Audit.ResultRef == nil || strings.TrimSpace(*state.Audit.ResultRef) == "" {
		return binding, fmt.Errorf("test-design state has no accepted audit result")
	}
	auditResultPath, err := service.containedArtifactPath(root, *state.Audit.ResultRef)
	if err != nil {
		return binding, err
	}
	auditRaw, err := testDesignReadRegularFile(auditResultPath)
	if err != nil {
		return binding, err
	}
	refs, ok := handoff["artifact_refs"].(map[string]any)
	if !ok || len(refs) != 5 {
		return binding, fmt.Errorf("test-design handoff artifact_refs is invalid")
	}
	expectedRefs := map[string]string{
		"state": "test-state.json", "universe": "test-universe.json", "catalog": "test-catalog.json",
		"data_manifest": "test-data-manifest.json", "coverage_matrix": "coverage-matrix.json",
	}
	for key, expected := range expectedRefs {
		if strings.TrimSpace(asString(refs[key])) != expected {
			return binding, fmt.Errorf("test-design handoff artifact ref %s is invalid", key)
		}
	}
	if strings.TrimSpace(asString(handoff["gap_ref"])) != "test-gaps.json" || strings.TrimSpace(asString(handoff["audit_result_ref"])) != *state.Audit.ResultRef {
		return binding, fmt.Errorf("test-design gap or audit reference is stale")
	}
	expectedDigests := map[string]string{
		"state":           testDesignDigest(stateRaw),
		"universe":        digests["test-universe.json"],
		"catalog":         digests["test-catalog.json"],
		"data_manifest":   digests["test-data-manifest.json"],
		"coverage_matrix": digests["coverage-matrix.json"],
		"gaps":            digests["test-gaps.json"],
		"audit_result":    testDesignDigest(auditRaw),
	}
	rawDigests, ok := handoff["artifact_digests"].(map[string]any)
	if !ok || len(rawDigests) != len(expectedDigests) {
		return binding, fmt.Errorf("test-design handoff artifact_digests is invalid")
	}
	for key, expected := range expectedDigests {
		actual := strings.TrimSpace(asString(rawDigests[key]))
		if !testDesignSHA256Pattern.MatchString(actual) || actual != expected {
			return binding, fmt.Errorf("test-design handoff digest %s is stale", key)
		}
	}
	caseRefs, err := testDesignRequireStringList(handoff, "test_case_refs", "test-design handoff", true)
	if err != nil || !testDesignSameStringSet(caseRefs, testDesignCatalogPointers(bundle.Catalog)) {
		return binding, firstTestDesignError(err, fmt.Errorf("test-design handoff test_case_refs do not match the catalog"))
	}
	dataRefs, err := testDesignRequireStringList(handoff, "test_data_refs", "test-design handoff", false)
	if err != nil || !testDesignSameStringSet(dataRefs, testDesignDataPointers(bundle.DataManifest)) {
		return binding, firstTestDesignError(err, fmt.Errorf("test-design handoff test_data_refs do not match the data manifest"))
	}
	binding = testDesignPublishedHandoff{
		Ref:               filepath.ToSlash(filepath.Join(filepath.Base(root), "handoff-to-tasks.json")),
		SHA256:            testDesignDigest(handoffRaw),
		SourceFingerprint: state.Source.Fingerprint,
		StateRevision:     state.Revision,
		ArtifactDigests:   expectedDigests,
		TestCaseRefs:      caseRefs,
		TestDataRefs:      dataRefs,
	}
	return binding, nil
}

func (service testDesignService) containedArtifactPath(root, ref string) (string, error) {
	projectRoot, err := filepath.Abs(service.projectRoot)
	if err != nil {
		return "", err
	}
	projectRoot, err = filepath.EvalSymlinks(projectRoot)
	if err != nil {
		return "", err
	}
	rootAbs, err := filepath.Abs(root)
	if err != nil {
		return "", err
	}
	rootRelative, err := filepath.Rel(projectRoot, rootAbs)
	if err != nil || rootRelative == ".." || strings.HasPrefix(rootRelative, ".."+string(filepath.Separator)) {
		return "", fmt.Errorf("test-design artifact root escapes the project root")
	}
	securedRoot, err := testDesignSecureProjectPath(projectRoot, filepath.ToSlash(rootRelative))
	if err != nil {
		return "", err
	}
	cleanRef := strings.TrimSpace(ref)
	if cleanRef == "" || filepath.IsAbs(cleanRef) {
		return "", fmt.Errorf("test-design artifact ref must be project-relative")
	}
	projectRef := filepath.ToSlash(filepath.Join(rootRelative, filepath.FromSlash(cleanRef)))
	candidate, err := testDesignSecureProjectPath(projectRoot, projectRef)
	if err != nil {
		return "", err
	}
	relative, err := filepath.Rel(securedRoot, candidate)
	if err != nil || relative == ".." || strings.HasPrefix(relative, ".."+string(filepath.Separator)) {
		return "", fmt.Errorf("test-design artifact ref escapes its root: %s", ref)
	}
	return candidate, nil
}

func testDesignResolveProjectPath(projectRoot, value string) (string, error) {
	value = strings.TrimSpace(value)
	if value == "" {
		return "", fmt.Errorf("path is required")
	}
	root, err := filepath.Abs(projectRoot)
	if err != nil {
		return "", err
	}
	root, err = filepath.EvalSymlinks(root)
	if err != nil {
		return "", err
	}
	absolute := value
	if !filepath.IsAbs(absolute) {
		absolute = filepath.Join(root, filepath.FromSlash(value))
	}
	absolute, err = filepath.Abs(absolute)
	if err != nil {
		return "", err
	}
	relative, err := filepath.Rel(root, absolute)
	if err != nil || relative == ".." || strings.HasPrefix(relative, ".."+string(filepath.Separator)) {
		return "", fmt.Errorf("path must stay inside the project root")
	}
	return testDesignSecureProjectPath(root, filepath.ToSlash(relative))
}

func testDesignSecureProjectPath(projectRoot, relative string) (string, error) {
	target, err := secureProjectPath(projectRoot, relative)
	if err != nil {
		return "", err
	}
	root, err := filepath.Abs(projectRoot)
	if err != nil {
		return "", err
	}
	root, err = filepath.EvalSymlinks(root)
	if err != nil {
		return "", err
	}
	relativeToRoot, err := filepath.Rel(root, target)
	if err != nil || relativeToRoot == ".." || strings.HasPrefix(relativeToRoot, ".."+string(filepath.Separator)) {
		return "", fmt.Errorf("path must stay inside the project root")
	}
	current := root
	for _, component := range strings.Split(relativeToRoot, string(filepath.Separator)) {
		if component == "" || component == "." {
			continue
		}
		current = filepath.Join(current, component)
		info, statErr := os.Lstat(current)
		if errors.Is(statErr, os.ErrNotExist) {
			break
		}
		if statErr != nil {
			return "", statErr
		}
		if info.Mode()&os.ModeSymlink != 0 {
			return "", fmt.Errorf("project path crosses symlink or junction %q", current)
		}
		resolved, resolveErr := filepath.EvalSymlinks(current)
		if resolveErr != nil {
			return "", resolveErr
		}
		resolved, resolveErr = filepath.Abs(resolved)
		if resolveErr != nil {
			return "", resolveErr
		}
		currentAbs, currentErr := filepath.Abs(current)
		if currentErr != nil {
			return "", currentErr
		}
		same := filepath.Clean(resolved) == filepath.Clean(currentAbs)
		if runtime.GOOS == "windows" {
			same = strings.EqualFold(filepath.Clean(resolved), filepath.Clean(currentAbs))
		}
		if !same {
			return "", fmt.Errorf("project path crosses reparse point %q", current)
		}
	}
	return target, nil
}

func (service testDesignService) resolveRoot(featureArg string) (string, string, string, error) {
	projectRoot, err := filepath.Abs(service.projectRoot)
	if err != nil {
		return "", "", "", err
	}
	featureArg = strings.TrimSpace(featureArg)
	if featureArg == "" {
		root, err := testDesignResolveProjectPath(projectRoot, ".specify/test-design")
		return root, ".specify/test-design", "", err
	}
	featurePath, err := testDesignResolveProjectPath(projectRoot, featureArg)
	if err != nil {
		return "", "", "", err
	}
	info, err := os.Stat(featurePath)
	if err != nil {
		return "", "", "", fmt.Errorf("feature directory is unavailable: %w", err)
	}
	if !info.IsDir() {
		return "", "", "", fmt.Errorf("feature directory must be a directory")
	}
	featureRel, err := filepath.Rel(projectRoot, featurePath)
	if err != nil {
		return "", "", "", err
	}
	featureRef := filepath.ToSlash(featureRel)
	root, err := testDesignResolveProjectPath(projectRoot, filepath.Join(featureRef, "test-design"))
	if err != nil {
		return "", "", "", err
	}
	return root, filepath.ToSlash(filepath.Join(featureRef, "test-design")), featureRef, nil
}

func testDesignStateMatchesRoot(state testDesignState, scope, featureRef, rootRef string) error {
	if state.Scope != scope || state.ArtifactRoot != rootRef {
		return fmt.Errorf("existing scope/root is %s/%s, requested %s/%s", state.Scope, state.ArtifactRoot, scope, rootRef)
	}
	if scope == "project" {
		if state.FeatureDir != nil {
			return fmt.Errorf("project-scoped state must not name feature_dir")
		}
		return nil
	}
	if state.FeatureDir == nil || *state.FeatureDir != featureRef {
		return fmt.Errorf("existing feature_dir does not match %s", featureRef)
	}
	return nil
}

func testDesignSameBoundary(left, right testDesignStateSource) bool {
	return testDesignSameStringSet(left.SourceRefs, right.SourceRefs) &&
		testDesignSameStringSet(left.IncludedPaths, right.IncludedPaths) &&
		testDesignSameStringSet(left.ExcludedPaths, right.ExcludedPaths) &&
		testDesignSameStringSet(left.RiskDimensions, right.RiskDimensions)
}

func (service testDesignService) archiveHandoff(root string, revision int) (string, error) {
	source, err := service.containedArtifactPath(root, "handoff-to-tasks.json")
	if err != nil {
		return "", err
	}
	info, err := os.Lstat(source)
	if errors.Is(err, os.ErrNotExist) {
		return "", nil
	}
	if err != nil {
		return "", err
	}
	if !info.Mode().IsRegular() || info.Mode()&os.ModeSymlink != 0 {
		return "", fmt.Errorf("handoff-to-tasks.json must be a regular non-symlink file")
	}
	raw, err := os.ReadFile(source)
	if err != nil {
		return "", err
	}
	archiveDir, err := service.containedArtifactPath(root, "handoff-history")
	if err != nil {
		return "", err
	}
	if err := os.MkdirAll(archiveDir, 0o755); err != nil {
		return "", err
	}
	// Re-resolve after creation so a raced symlink/junction cannot become the
	// destination of the following rename.
	archiveDir, err = service.containedArtifactPath(root, "handoff-history")
	if err != nil {
		return "", err
	}
	archiveName := fmt.Sprintf("handoff-r%06d-%s.json", revision, testDesignDigest(raw)[:12])
	archivePath, err := service.containedArtifactPath(root, filepath.ToSlash(filepath.Join("handoff-history", archiveName)))
	if err != nil {
		return "", err
	}
	if _, err := os.Lstat(archivePath); err == nil {
		return "", fmt.Errorf("handoff archive already exists: %s", filepath.Base(archivePath))
	} else if !errors.Is(err, os.ErrNotExist) {
		return "", err
	}
	if err := os.Rename(source, archivePath); err != nil {
		return "", err
	}
	return archivePath, nil
}

func (service testDesignService) restoreArchivedHandoff(root, archivePath string) error {
	if archivePath == "" {
		return nil
	}
	rootAbs, err := filepath.Abs(root)
	if err != nil {
		return err
	}
	archiveAbs, err := filepath.Abs(archivePath)
	if err != nil {
		return err
	}
	archiveRef, err := filepath.Rel(rootAbs, archiveAbs)
	if err != nil || archiveRef == ".." || strings.HasPrefix(archiveRef, ".."+string(filepath.Separator)) {
		return fmt.Errorf("handoff archive escapes test-design root")
	}
	securedArchive, err := service.containedArtifactPath(root, filepath.ToSlash(archiveRef))
	if err != nil {
		return err
	}
	archiveInfo, err := os.Lstat(securedArchive)
	if err != nil {
		return err
	}
	if !archiveInfo.Mode().IsRegular() || archiveInfo.Mode()&os.ModeSymlink != 0 {
		return fmt.Errorf("handoff archive must be a regular non-symlink file")
	}
	destination, err := service.containedArtifactPath(root, "handoff-to-tasks.json")
	if err != nil {
		return err
	}
	return os.Rename(securedArchive, destination)
}

func (service testDesignService) withMutationLock(root string, action func() Envelope) Envelope {
	projectRoot, err := filepath.Abs(service.projectRoot)
	if err != nil {
		return testDesignFailure("error", "cannot resolve project root", err)
	}
	lockDir, err := testDesignSecureProjectPath(projectRoot, ".specify/runtime/test-design/locks")
	if err != nil {
		return testDesignFailure("error", "cannot resolve test-design lock directory", err)
	}
	if err := os.MkdirAll(lockDir, 0o755); err != nil {
		return testDesignFailure("error", "cannot create test-design lock directory", err)
	}
	lockDir, err = testDesignSecureProjectPath(projectRoot, ".specify/runtime/test-design/locks")
	if err != nil {
		return testDesignFailure("error", "test-design lock directory is unsafe", err)
	}
	lockName := testDesignDigest([]byte(filepath.Clean(root)))[:24] + ".lock"
	lockPath, err := testDesignSecureProjectPath(projectRoot, filepath.ToSlash(filepath.Join(".specify", "runtime", "test-design", "locks", lockName)))
	if err != nil {
		return testDesignFailure("error", "test-design lock path is unsafe", err)
	}
	release, err := filelock.Acquire(lockPath)
	if err != nil {
		return testDesignFailure("blocked", "cannot acquire test-design workflow lock", err)
	}
	defer release()
	return action()
}

func (service testDesignService) inputObject(args []string, flag, label string) (map[string]any, error) {
	if !hasFlag(args, flag) || strings.TrimSpace(optionValue(args, flag, "")) == "" {
		return nil, fmt.Errorf("%s requires %s", label, flag)
	}
	raw, err := resolveAgentJSONInputBytes(optionValue(args, flag, ""), service.projectRoot, label)
	if err != nil {
		return nil, err
	}
	var payload map[string]any
	if err := json.Unmarshal(raw, &payload); err != nil {
		return nil, fmt.Errorf("%s must contain a JSON object: %w", flag, err)
	}
	if payload == nil {
		return nil, fmt.Errorf("%s must contain a JSON object", flag)
	}
	return payload, nil
}

func (service testDesignService) loadCanonicalTemplate(name string) (map[string]any, error) {
	projectRoot, err := filepath.Abs(service.projectRoot)
	if err != nil {
		return nil, err
	}
	path, err := testDesignResolveProjectPath(projectRoot, filepath.Join(".specify", "templates", "artifacts", name))
	if err != nil {
		return nil, err
	}
	return testDesignReadObject(path)
}

func (service testDesignService) normalizedPathList(value any, label string, allowDot bool) ([]string, error) {
	values, err := testDesignStrictStrings(value, label, false)
	if err != nil {
		return nil, err
	}
	out := make([]string, 0, len(values))
	seen := map[string]bool{}
	for _, value := range values {
		path, err := service.normalizedProjectPath(value, allowDot)
		if err != nil {
			return nil, fmt.Errorf("%s contains invalid path %q: %w", label, value, err)
		}
		if !seen[path] {
			seen[path] = true
			out = append(out, path)
		}
	}
	sort.Strings(out)
	return out, nil
}

func (service testDesignService) normalizedProjectPath(value string, allowDot bool) (string, error) {
	path, err := testDesignResolveProjectPath(service.projectRoot, value)
	if err != nil {
		return "", err
	}
	root, err := filepath.Abs(service.projectRoot)
	if err != nil {
		return "", err
	}
	relative, err := filepath.Rel(root, path)
	if err != nil {
		return "", err
	}
	relative = filepath.ToSlash(relative)
	if relative == "." && !allowDot {
		return "", fmt.Errorf("project root is not a valid file reference")
	}
	if relative == ".git" || strings.HasPrefix(relative, ".git/") {
		return "", fmt.Errorf(".git is outside the test-design evidence boundary")
	}
	return relative, nil
}

func (service testDesignService) sourceFingerprint(sourceRefs, includedPaths, excludedPaths, risks []string, artifactRoot string) (string, error) {
	type sourceDigest struct {
		Ref    string `json:"ref"`
		SHA256 string `json:"sha256"`
	}
	root, err := filepath.Abs(service.projectRoot)
	if err != nil {
		return "", err
	}
	root, err = filepath.EvalSymlinks(root)
	if err != nil {
		return "", err
	}
	files := map[string]string{}
	addFile := func(ref string) error {
		ref = filepath.ToSlash(filepath.Clean(filepath.FromSlash(ref)))
		if testDesignFingerprintPathExcluded(ref, excludedPaths, artifactRoot) {
			return nil
		}
		path, err := testDesignSecureProjectPath(root, ref)
		if err != nil {
			return err
		}
		info, err := os.Lstat(path)
		if err != nil {
			return err
		}
		if info.Mode()&os.ModeSymlink != 0 || !info.Mode().IsRegular() {
			return fmt.Errorf("fingerprinted path must be a regular non-symlink file: %s", ref)
		}
		raw, err := os.ReadFile(path)
		if err != nil {
			return err
		}
		files[ref] = testDesignDigest(raw)
		return nil
	}
	for _, ref := range sourceRefs {
		if testDesignFingerprintPathExcluded(ref, excludedPaths, artifactRoot) {
			return "", fmt.Errorf("source_ref %s is excluded from the fingerprint boundary", ref)
		}
		if err := addFile(ref); err != nil {
			return "", fmt.Errorf("fingerprint source %s: %w", ref, err)
		}
	}
	for _, included := range includedPaths {
		path, err := testDesignSecureProjectPath(root, included)
		if err != nil {
			return "", fmt.Errorf("fingerprint included path %s: %w", included, err)
		}
		info, err := os.Lstat(path)
		if err != nil {
			return "", fmt.Errorf("fingerprint included path %s: %w", included, err)
		}
		if info.Mode()&os.ModeSymlink != 0 {
			return "", fmt.Errorf("included path must not be a symlink or junction: %s", included)
		}
		if info.Mode().IsRegular() {
			if err := addFile(included); err != nil {
				return "", err
			}
			continue
		}
		if !info.IsDir() {
			return "", fmt.Errorf("included path must be a directory or regular file: %s", included)
		}
		walkErr := filepath.WalkDir(path, func(candidate string, entry os.DirEntry, walkErr error) error {
			if walkErr != nil {
				return walkErr
			}
			relative, relErr := filepath.Rel(root, candidate)
			if relErr != nil || relative == ".." || strings.HasPrefix(relative, ".."+string(filepath.Separator)) {
				return fmt.Errorf("included path escaped project root: %s", candidate)
			}
			relative = filepath.ToSlash(relative)
			if testDesignFingerprintPathExcluded(relative, excludedPaths, artifactRoot) {
				if entry.IsDir() {
					return filepath.SkipDir
				}
				return nil
			}
			if _, secureErr := testDesignSecureProjectPath(root, relative); secureErr != nil {
				return secureErr
			}
			entryInfo, infoErr := entry.Info()
			if infoErr != nil {
				return infoErr
			}
			if entryInfo.Mode()&os.ModeSymlink != 0 {
				return fmt.Errorf("included path contains symlink or junction: %s", relative)
			}
			if entry.IsDir() {
				return nil
			}
			if !entryInfo.Mode().IsRegular() {
				return fmt.Errorf("included path contains non-regular file: %s", relative)
			}
			return addFile(relative)
		})
		if walkErr != nil {
			return "", fmt.Errorf("fingerprint included path %s: %w", included, walkErr)
		}
	}
	sources := make([]sourceDigest, 0, len(files))
	for ref, digest := range files {
		sources = append(sources, sourceDigest{Ref: ref, SHA256: digest})
	}
	sort.Slice(sources, func(i, j int) bool { return sources[i].Ref < sources[j].Ref })
	payload := map[string]any{
		"sources":         sources,
		"source_refs":     append([]string(nil), sourceRefs...),
		"included_paths":  append([]string(nil), includedPaths...),
		"excluded_paths":  append([]string(nil), excludedPaths...),
		"risk_dimensions": append([]string(nil), risks...),
		"artifact_root":   artifactRoot,
	}
	raw, err := json.Marshal(payload)
	if err != nil {
		return "", err
	}
	return testDesignDigest(raw), nil
}

func testDesignFingerprintPathExcluded(ref string, excludedPaths []string, artifactRoot string) bool {
	ref = strings.TrimPrefix(filepath.ToSlash(filepath.Clean(filepath.FromSlash(ref))), "./")
	if ref == ".git" || strings.HasPrefix(ref, ".git/") ||
		ref == ".specify/runtime" || strings.HasPrefix(ref, ".specify/runtime/") ||
		ref == ".specify/evidence" || strings.HasPrefix(ref, ".specify/evidence/") {
		return true
	}
	if strings.TrimSpace(artifactRoot) != "" && testDesignPathCovered(ref, []string{artifactRoot}) {
		return true
	}
	return testDesignPathCovered(ref, excludedPaths)
}

func (service testDesignService) requireFreshSources(state testDesignState) error {
	current, err := service.sourceFingerprint(state.Source.SourceRefs, state.Source.IncludedPaths, state.Source.ExcludedPaths, state.Source.RiskDimensions, state.ArtifactRoot)
	if err != nil {
		return err
	}
	if current != state.Source.Fingerprint {
		return fmt.Errorf("source fingerprint changed from %s to %s", state.Source.Fingerprint, current)
	}
	return nil
}

func (service testDesignService) persistStaleState(root, rootRef string, state testDesignState, cause error) Envelope {
	state.Status = "blocked"
	state.ClaimStatus = "stale"
	state.Blockers = []any{map[string]any{
		"category":     "source_freshness",
		"owner":        "test-design leader",
		"exact_cause":  cause.Error(),
		"next_action":  "rerun test-design init or rebuild the affected universe",
		"resume_point": "test-design universe-build",
	}}
	state.Revision++
	if err := service.writeState(root, state, "test-design.mark-stale"); err != nil {
		return testDesignFailure("error", "cannot persist stale test-design state", err)
	}
	env := testDesignFailure("blocked", "test-design sources are stale", cause)
	env.Data = testDesignStateData(state, rootRef)
	return env
}

func (service testDesignService) parseDiscoveryLane(row map[string]any, state testDesignState) (testDesignLane, error) {
	laneID := strings.ToUpper(strings.TrimSpace(asString(row["lane_id"])))
	if !testDesignLaneIDPattern.MatchString(laneID) {
		return testDesignLane{}, fmt.Errorf("lane_id is invalid")
	}
	kind := strings.ToLower(strings.TrimSpace(asString(row["kind"])))
	if kind == "" {
		kind = "discovery"
	}
	if kind != "discovery" {
		return testDesignLane{}, fmt.Errorf("lane-prepare accepts discovery lanes only; audit lanes are runtime-owned")
	}
	title := strings.TrimSpace(asString(row["title"]))
	if title == "" {
		return testDesignLane{}, fmt.Errorf("title is required")
	}
	obligations, err := testDesignStrictStrings(row["obligation_ids"], "obligation_ids", true)
	if err != nil || len(obligations) == 0 {
		return testDesignLane{}, firstTestDesignError(err, errors.New("obligation_ids must not be empty"))
	}
	for _, obligationID := range obligations {
		if !testDesignObligationPattern.MatchString(obligationID) {
			return testDesignLane{}, fmt.Errorf("obligation_id %s is invalid", obligationID)
		}
	}
	readPaths, err := service.normalizedPathList(row["read_paths"], "read_paths", true)
	if err != nil || len(readPaths) == 0 {
		return testDesignLane{}, firstTestDesignError(err, errors.New("read_paths must not be empty"))
	}
	for _, path := range readPaths {
		if testDesignPathCovered(path, state.Source.ExcludedPaths) {
			return testDesignLane{}, fmt.Errorf("read path %s is excluded", path)
		}
		if !testDesignPathCovered(path, state.Source.IncludedPaths) && !testDesignPathCovered(path, state.Source.SourceRefs) {
			return testDesignLane{}, fmt.Errorf("read path %s is outside the frozen boundary", path)
		}
	}
	questions, err := testDesignStrictStrings(row["questions"], "questions", true)
	if err != nil || len(questions) == 0 {
		return testDesignLane{}, firstTestDesignError(err, errors.New("questions must not be empty"))
	}
	return testDesignLane{
		LaneID:        laneID,
		Kind:          kind,
		Title:         title,
		State:         "pending",
		ObligationIDs: obligations,
		ReadPaths:     readPaths,
		Questions:     questions,
	}, nil
}

func (service testDesignService) validateLaneResult(result map[string]any, lane testDesignLane) error {
	allowed := map[string]bool{
		"lane_id": true, "attempt_id": true, "status": true, "inspected_paths": true,
		"evidence_refs": true, "obligation_results": true, "checks": true,
		"candidate_cases": true, "data_requirements": true, "contradictions": true,
		"unknowns": true, "gaps": true, "findings": true, "summary": true,
	}
	for key := range result {
		if !allowed[key] {
			return fmt.Errorf("result contains unsupported field %s", key)
		}
	}
	for _, key := range []string{
		"lane_id", "attempt_id", "status", "inspected_paths", "evidence_refs",
		"obligation_results", "checks", "candidate_cases", "data_requirements",
		"contradictions", "unknowns", "gaps", "summary",
	} {
		if _, ok := result[key]; !ok {
			return fmt.Errorf("result is missing required field %s", key)
		}
	}
	if strings.TrimSpace(asString(result["lane_id"])) != lane.LaneID {
		return fmt.Errorf("result lane_id must equal %s", lane.LaneID)
	}
	if strings.TrimSpace(asString(result["attempt_id"])) != lane.AttemptID {
		return fmt.Errorf("result attempt_id must equal the active attempt")
	}
	status := strings.ToLower(strings.TrimSpace(asString(result["status"])))
	if status != "success" && status != "partial" && status != "blocked" && status != "failed" {
		return fmt.Errorf("result status must be success, partial, blocked, or failed")
	}
	inspected, err := service.normalizedPathList(result["inspected_paths"], "inspected_paths", true)
	if err != nil {
		return err
	}
	if len(inspected) != len(testDesignArray(result["inspected_paths"])) {
		return fmt.Errorf("result inspected_paths must contain unique paths")
	}
	for _, path := range inspected {
		if !testDesignPathCovered(path, lane.ReadPaths) {
			return fmt.Errorf("inspected path %s is outside lane %s read_paths", path, lane.LaneID)
		}
	}
	evidence, err := testDesignStrictStrings(result["evidence_refs"], "evidence_refs", false)
	if err != nil || len(evidence) != len(testDesignArray(result["evidence_refs"])) {
		return firstTestDesignError(err, fmt.Errorf("result evidence_refs must contain unique non-empty strings"))
	}
	if err := service.verifyEvidenceRefs(evidence); err != nil {
		return fmt.Errorf("result evidence_refs are not verifiable: %w", err)
	}
	for _, key := range []string{"candidate_cases", "data_requirements", "contradictions", "unknowns", "gaps"} {
		if err := testDesignValidateObjectArray(result[key], key, true); err != nil {
			return err
		}
	}
	obligationRows, err := service.validateLaneObligationResults(result["obligation_results"], lane)
	if err != nil {
		return err
	}
	proposedGaps := map[string]bool{}
	for index, gap := range testDesignObjects(result["gaps"]) {
		gapID := strings.TrimSpace(asString(gap["gap_id"]))
		if !testDesignGapPattern.MatchString(gapID) || proposedGaps[gapID] {
			return fmt.Errorf("result gaps[%d] must declare a unique canonical gap_id", index)
		}
		proposedGaps[gapID] = true
	}
	for obligationID, row := range obligationRows {
		for _, gapID := range testDesignStrings(row["gap_refs"]) {
			if lane.Kind != "audit" && !proposedGaps[gapID] {
				return fmt.Errorf("%s accounts through gap %s but result gaps does not propose it", obligationID, gapID)
			}
		}
	}
	if err := service.validateLaneChecks(result["checks"], lane); err != nil {
		return err
	}
	if findings, exists := result["findings"]; exists {
		if err := testDesignValidateObjectArray(findings, "findings", true); err != nil {
			return err
		}
	}
	if status == "success" || status == "partial" {
		if len(inspected) == 0 || len(evidence) == 0 || len(obligationRows) == 0 {
			return fmt.Errorf("success/partial results require inspected_paths, verified evidence_refs, and obligation_results")
		}
		accounted := map[string]bool{}
		for obligationID := range obligationRows {
			accounted[obligationID] = true
		}
		assigned := map[string]bool{}
		for _, obligationID := range lane.ObligationIDs {
			assigned[obligationID] = true
		}
		if !testDesignSameStringSet(testDesignSortedKeys(accounted), testDesignSortedKeys(assigned)) {
			return fmt.Errorf("result obligation_results must account for exactly the assigned obligation set")
		}
	}
	if lane.Kind == "audit" {
		if _, exists := result["findings"]; !exists {
			return fmt.Errorf("audit result must declare findings")
		}
		if !testDesignSameStringSet(inspected, lane.ReadPaths) {
			return fmt.Errorf("audit inspected_paths must cover every canonical audit input")
		}
	}
	if strings.TrimSpace(asString(result["summary"])) == "" {
		return fmt.Errorf("result summary is required")
	}
	return nil
}

func (service testDesignService) validateLaneObligationResults(value any, lane testDesignLane) (map[string]map[string]any, error) {
	rows, ok := value.([]any)
	if !ok {
		return nil, fmt.Errorf("result obligation_results must be an array")
	}
	out := map[string]map[string]any{}
	for index, raw := range rows {
		row, ok := raw.(map[string]any)
		if !ok {
			return nil, fmt.Errorf("result obligation_results[%d] must be an object", index)
		}
		if len(row) != 5 {
			return nil, fmt.Errorf("result obligation_results[%d] must use the canonical fields", index)
		}
		for key := range row {
			if !testDesignContains([]string{"obligation_id", "status", "evidence_refs", "gap_refs", "summary"}, key) {
				return nil, fmt.Errorf("result obligation_results[%d] contains unsupported field %s", index, key)
			}
		}
		obligationID := strings.TrimSpace(asString(row["obligation_id"]))
		if !testDesignObligationPattern.MatchString(obligationID) || !testDesignContains(lane.ObligationIDs, obligationID) {
			return nil, fmt.Errorf("result obligation_results[%d] references unassigned obligation %s", index, obligationID)
		}
		if _, exists := out[obligationID]; exists {
			return nil, fmt.Errorf("result obligation_results duplicates %s", obligationID)
		}
		status := strings.ToLower(strings.TrimSpace(asString(row["status"])))
		if !testDesignContains([]string{"covered", "gap", "unknown", "not_applicable"}, status) {
			return nil, fmt.Errorf("result obligation_results[%d] status is invalid", index)
		}
		evidenceRefs, err := testDesignRequireStringList(row, "evidence_refs", obligationID, false)
		if err != nil {
			return nil, err
		}
		if err := service.verifyEvidenceRefs(evidenceRefs); err != nil {
			return nil, fmt.Errorf("%s evidence_refs are not verifiable: %w", obligationID, err)
		}
		gapRefs, err := testDesignRequireStringList(row, "gap_refs", obligationID, false)
		if err != nil {
			return nil, err
		}
		for _, gapID := range gapRefs {
			if !testDesignGapPattern.MatchString(gapID) {
				return nil, fmt.Errorf("%s gap_ref %s is invalid", obligationID, gapID)
			}
		}
		if (status == "covered" || status == "not_applicable") && (len(evidenceRefs) == 0 || len(gapRefs) != 0) {
			return nil, fmt.Errorf("%s %s accounting requires verified evidence and no gaps", obligationID, status)
		}
		if (status == "gap" || status == "unknown") && len(gapRefs) == 0 {
			return nil, fmt.Errorf("%s %s accounting requires gap_refs", obligationID, status)
		}
		if strings.TrimSpace(asString(row["summary"])) == "" {
			return nil, fmt.Errorf("%s obligation result summary is required", obligationID)
		}
		out[obligationID] = row
	}
	return out, nil
}

func (service testDesignService) validateLaneChecks(value any, lane testDesignLane) error {
	rows, ok := value.([]any)
	if !ok {
		return fmt.Errorf("result checks must be an array")
	}
	seen := map[string]bool{}
	for index, raw := range rows {
		row, ok := raw.(map[string]any)
		if !ok {
			return fmt.Errorf("result checks[%d] must be an object", index)
		}
		if len(row) != 6 {
			return fmt.Errorf("result checks[%d] must use the canonical fields", index)
		}
		for key := range row {
			if !testDesignContains([]string{"check_id", "status", "evidence_refs", "affected_obligation_refs", "finding_refs", "summary"}, key) {
				return fmt.Errorf("result checks[%d] contains unsupported field %s", index, key)
			}
		}
		checkID := strings.TrimSpace(asString(row["check_id"]))
		if !testDesignAuditCheckIDPattern.MatchString(checkID) || seen[checkID] {
			return fmt.Errorf("result checks[%d] check_id is invalid or duplicated", index)
		}
		seen[checkID] = true
		if err := testDesignRequireEnum(row, "status", checkID, []string{"passed", "finding", "blocked", "not_applicable"}); err != nil {
			return err
		}
		checkStatus := strings.ToLower(strings.TrimSpace(asString(row["status"])))
		evidenceRefs, err := testDesignRequireStringList(row, "evidence_refs", checkID, false)
		if err != nil {
			return err
		}
		if err := service.verifyEvidenceRefs(evidenceRefs); err != nil {
			return fmt.Errorf("audit check %s evidence is not verifiable: %w", checkID, err)
		}
		affected, err := testDesignRequireStringList(row, "affected_obligation_refs", checkID, false)
		if err != nil {
			return err
		}
		for _, obligationID := range affected {
			if !testDesignContains(lane.ObligationIDs, obligationID) {
				return fmt.Errorf("audit check %s references unassigned obligation %s", checkID, obligationID)
			}
		}
		findingRefs, err := testDesignRequireStringList(row, "finding_refs", checkID, false)
		if err != nil {
			return err
		}
		if checkStatus == "passed" && len(evidenceRefs) == 0 {
			return fmt.Errorf("audit check %s passed status requires verified evidence", checkID)
		}
		if testDesignContains([]string{"finding", "blocked"}, checkStatus) && len(findingRefs) == 0 {
			return fmt.Errorf("audit check %s status %s requires finding_refs", checkID, checkStatus)
		}
		if strings.TrimSpace(asString(row["summary"])) == "" {
			return fmt.Errorf("audit check %s summary is required", checkID)
		}
	}
	if lane.Kind == "audit" {
		required := map[string]bool{}
		for _, checkID := range testDesignAuditCoreCheckIDs {
			required[checkID] = true
		}
		if !testDesignSameStringSet(testDesignSortedKeys(seen), testDesignSortedKeys(required)) {
			return fmt.Errorf("audit checks must contain exactly the runtime core check IDs")
		}
	}
	return nil
}

func (service testDesignService) verifyEvidenceRefs(refs []string) error {
	evidence := evidenceService{projectRoot: service.projectRoot}
	for _, ref := range refs {
		ref = filepath.ToSlash(strings.TrimSpace(ref))
		if !testDesignEvidenceRefPattern.MatchString(ref) {
			return fmt.Errorf("evidence ref %q is not a canonical evidence record_ref", ref)
		}
		recordPath, err := testDesignSecureProjectPath(service.projectRoot, ref)
		if err != nil {
			return fmt.Errorf("evidence record %s is unsafe: %w", ref, err)
		}
		if _, err := testDesignReadRegularFile(recordPath); err != nil {
			return fmt.Errorf("evidence record %s is unavailable: %w", ref, err)
		}
		record, err := evidence.readRecord(ref)
		if err != nil {
			return fmt.Errorf("read evidence record %s: %w", ref, err)
		}
		expectedID := strings.TrimSuffix(filepath.Base(ref), filepath.Ext(ref))
		if record.SchemaVersion != evidenceSchemaVersion || record.RecordRef != ref || record.EvidenceID != expectedID {
			return fmt.Errorf("evidence record %s identity is forged", ref)
		}
		if record.Status != "ready" {
			return fmt.Errorf("evidence record %s is not registered and ready", ref)
		}
		if record.Scope != "test-design" {
			return fmt.Errorf("evidence record %s has incompatible scope %q", ref, record.Scope)
		}
		if strings.TrimSpace(record.Source) == "" || strings.TrimSpace(record.Provenance) == "" || strings.TrimSpace(record.CreatedAt) == "" {
			return fmt.Errorf("evidence record %s is missing source, provenance, or created_at metadata", ref)
		}
		if _, err := time.Parse(time.RFC3339, record.CreatedAt); err != nil {
			return fmt.Errorf("evidence record %s created_at is invalid", ref)
		}
		recomputedID := newEvidenceID(record.CreatedAt, evidenceCommonInput{
			Scope: record.Scope, Source: record.Source, Provenance: record.Provenance,
			TaskID: record.TaskID, ScenarioID: record.ScenarioID, MIME: record.MIME,
		})
		if recomputedID != record.EvidenceID {
			return fmt.Errorf("evidence record %s metadata does not match its evidence_id", ref)
		}
		if !testDesignSHA256Pattern.MatchString(record.SHA256) || record.Size < 0 {
			return fmt.Errorf("evidence record %s has invalid content metadata", ref)
		}
		expectedObjectRef := filepath.ToSlash(filepath.Join(".specify", "evidence", "objects", "sha256", record.SHA256[:2], record.SHA256))
		if record.ObjectRef != expectedObjectRef {
			return fmt.Errorf("evidence record %s object_ref is forged", ref)
		}
		objectPath, err := testDesignSecureProjectPath(service.projectRoot, record.ObjectRef)
		if err != nil {
			return fmt.Errorf("evidence object for %s is unsafe: %w", ref, err)
		}
		if _, err := testDesignReadRegularFile(objectPath); err != nil {
			return fmt.Errorf("evidence object for %s is unavailable: %w", ref, err)
		}
		verified := evidence.verify(ref)
		if verified.Status != "ok" {
			return fmt.Errorf("evidence record %s failed content verification: %s", ref, verified.Summary)
		}
	}
	return nil
}

func (service testDesignService) validateBundleEvidence(bundle testDesignBundle) error {
	for _, row := range testDesignObjects(bundle.CoverageMatrix["rows"]) {
		coverageID := strings.TrimSpace(asString(row["coverage_id"]))
		refs, err := testDesignRequireStringList(row, "evidence_refs", coverageID, false)
		if err != nil {
			return err
		}
		if err := service.verifyEvidenceRefs(refs); err != nil {
			return fmt.Errorf("%s evidence is invalid: %w", coverageID, err)
		}
	}
	for _, row := range testDesignObjects(bundle.DataManifest["datasets"]) {
		if strings.ToLower(strings.TrimSpace(asString(row["disposition"]))) != "search" || strings.ToLower(strings.TrimSpace(asString(row["readiness"]))) != "ready" {
			continue
		}
		dataID := strings.TrimSpace(asString(row["test_data_id"]))
		refs, err := testDesignRequireStringList(row, "provenance_refs", dataID, true)
		if err != nil {
			return err
		}
		canonical := make([]string, 0, len(refs))
		for _, ref := range refs {
			if testDesignEvidenceRefPattern.MatchString(filepath.ToSlash(ref)) {
				canonical = append(canonical, ref)
			}
		}
		if len(canonical) == 0 {
			return fmt.Errorf("%s has no canonical provenance evidence", dataID)
		}
		if err := service.verifyEvidenceRefs(canonical); err != nil {
			return fmt.Errorf("%s provenance evidence is invalid: %w", dataID, err)
		}
	}
	return nil
}

func (service testDesignService) writeStateAndManifest(root string, state testDesignState, manifest testDesignLaneManifest, kind string) error {
	updates, err := testDesignFileUpdates(map[string]any{
		filepath.Join(root, "test-state.json"):    state,
		filepath.Join(root, "lane-manifest.json"): manifest,
	})
	if err != nil {
		return err
	}
	_, err = applyFileTransaction(service.projectRoot, kind, updates)
	return err
}

func (service testDesignService) commandArgv(state testDesignState, subcommand string) []string {
	argv := []string{"specify-runtime", "test-design", subcommand}
	if state.Scope == "feature" && state.FeatureDir != nil && strings.TrimSpace(*state.FeatureDir) != "" {
		argv = append(argv, "--feature-dir", *state.FeatureDir)
	}
	if subcommand == "publish" {
		argv = append(argv, "--expected-revision", strconv.Itoa(state.Revision))
	}
	argv = append(argv, "--format", "json")
	return argv
}

func testDesignReadState(root string) (testDesignState, error) {
	var state testDesignState
	raw, err := testDesignReadRegularFile(filepath.Join(root, "test-state.json"))
	if err != nil {
		return state, err
	}
	if err := json.Unmarshal(raw, &state); err != nil {
		return state, err
	}
	if state.SchemaVersion != testDesignStateSchema || state.Revision < 1 {
		return state, fmt.Errorf("test-state.json has an unsupported runtime contract")
	}
	if state.ArtifactRoot == "" || state.Source.Fingerprint == "" || state.Lanes.ManifestRef == "" {
		return state, fmt.Errorf("test-state.json is missing canonical runtime fields")
	}
	if state.Lanes.AcceptedResultRefs == nil {
		state.Lanes.AcceptedResultRefs = []string{}
	}
	if state.Blockers == nil {
		state.Blockers = []any{}
	}
	return state, nil
}

func (service testDesignService) writeState(root string, state testDesignState, kind string) error {
	updates, err := testDesignFileUpdates(map[string]any{
		filepath.Join(root, "test-state.json"): state,
	})
	if err != nil {
		return err
	}
	_, err = applyFileTransaction(service.projectRoot, kind, updates)
	return err
}

func testDesignReadManifest(root string) (testDesignLaneManifest, error) {
	var manifest testDesignLaneManifest
	raw, err := testDesignReadRegularFile(filepath.Join(root, "lane-manifest.json"))
	if err != nil {
		return manifest, err
	}
	if err := json.Unmarshal(raw, &manifest); err != nil {
		return manifest, err
	}
	if manifest.Version != 1 || manifest.Artifact != testDesignLaneManifestFormat {
		return manifest, fmt.Errorf("lane-manifest.json has an unsupported runtime contract")
	}
	if !testDesignWorkerIDPattern.MatchString(manifest.LeaderID) {
		return manifest, fmt.Errorf("lane-manifest.json is missing a valid leader identity")
	}
	if manifest.Lanes == nil {
		manifest.Lanes = []testDesignLane{}
	}
	return manifest, nil
}

func testDesignReadBundle(root string) (testDesignBundle, error) {
	var bundle testDesignBundle
	var err error
	if bundle.Universe, err = testDesignReadObject(filepath.Join(root, "test-universe.json")); err != nil {
		return bundle, fmt.Errorf("test-universe.json: %w", err)
	}
	if bundle.Catalog, err = testDesignReadObject(filepath.Join(root, "test-catalog.json")); err != nil {
		return bundle, fmt.Errorf("test-catalog.json: %w", err)
	}
	if bundle.DataManifest, err = testDesignReadObject(filepath.Join(root, "test-data-manifest.json")); err != nil {
		return bundle, fmt.Errorf("test-data-manifest.json: %w", err)
	}
	if bundle.CoverageMatrix, err = testDesignReadObject(filepath.Join(root, "coverage-matrix.json")); err != nil {
		return bundle, fmt.Errorf("coverage-matrix.json: %w", err)
	}
	if bundle.Gaps, err = testDesignReadObject(filepath.Join(root, "test-gaps.json")); err != nil {
		return bundle, fmt.Errorf("test-gaps.json: %w", err)
	}
	return bundle, nil
}

func testDesignReadObject(path string) (map[string]any, error) {
	raw, err := testDesignReadRegularFile(path)
	if err != nil {
		return nil, err
	}
	var payload map[string]any
	if err := json.Unmarshal(raw, &payload); err != nil {
		return nil, err
	}
	if payload == nil {
		return nil, fmt.Errorf("JSON root must be an object")
	}
	return payload, nil
}

func testDesignReadRegularFile(path string) ([]byte, error) {
	info, err := os.Lstat(path)
	if err != nil {
		return nil, err
	}
	if info.Mode()&os.ModeSymlink != 0 || !info.Mode().IsRegular() {
		return nil, fmt.Errorf("%s must be a regular non-symlink file", filepath.Base(path))
	}
	return os.ReadFile(path)
}

func testDesignValidateBundle(bundle testDesignBundle) error {
	for _, artifact := range []struct {
		name    string
		payload map[string]any
	}{
		{"test-universe", bundle.Universe},
		{"test-catalog", bundle.Catalog},
		{"test-data-manifest", bundle.DataManifest},
		{"coverage-matrix", bundle.CoverageMatrix},
	} {
		if number, ok := artifact.payload["version"].(float64); !ok || number != 1 {
			return fmt.Errorf("%s version discriminator is invalid", artifact.name)
		}
		if strings.TrimSpace(asString(artifact.payload["artifact"])) != artifact.name {
			return fmt.Errorf("%s artifact discriminator is invalid", artifact.name)
		}
	}
	gapRows, err := testDesignValidateGaps(bundle.Gaps)
	if err != nil {
		return err
	}
	obligations, err := testDesignIndexRows(bundle.Universe["obligations"], "obligation_id", "test-universe obligations")
	if err != nil {
		return err
	}
	capabilities, err := testDesignIndexRows(bundle.Universe["capabilities"], "capability_id", "test-universe capabilities")
	if err != nil {
		return err
	}
	scenarios, err := testDesignIndexRows(bundle.Universe["scenarios"], "scenario_id", "test-universe scenarios")
	if err != nil {
		return err
	}
	universeCases, err := testDesignIndexRows(bundle.Universe["test_cases"], "test_case_id", "test-universe test_cases")
	if err != nil {
		return err
	}
	catalogCases, err := testDesignIndexRows(bundle.Catalog["cases"], "test_case_id", "test-catalog cases")
	if err != nil {
		return err
	}
	datasets, err := testDesignIndexRows(bundle.DataManifest["datasets"], "test_data_id", "test-data-manifest datasets")
	if err != nil {
		return err
	}
	coverageRows, err := testDesignIndexRows(bundle.CoverageMatrix["rows"], "coverage_id", "coverage-matrix rows")
	if err != nil {
		return err
	}
	if len(obligations) == 0 || len(capabilities) == 0 || len(scenarios) == 0 || len(universeCases) == 0 || len(coverageRows) == 0 {
		return fmt.Errorf("test universe must contain obligations, capabilities, scenarios, cases, and coverage rows")
	}
	if !testDesignSameKeys(universeCases, catalogCases) {
		return fmt.Errorf("test-universe and test-catalog must declare the same test_case_id set")
	}
	for obligationID, obligation := range obligations {
		if !testDesignObligationPattern.MatchString(obligationID) {
			return fmt.Errorf("obligation_id %s is invalid", obligationID)
		}
		if err := testDesignRequireNonEmptyStrings(obligation, obligationID, []string{"title", "rationale"}); err != nil {
			return err
		}
		for _, field := range []string{"source_refs", "required_evidence_classes", "invalidation_triggers"} {
			if _, err := testDesignRequireStringList(obligation, field, obligationID, true); err != nil {
				return err
			}
		}
		for _, evidenceClass := range testDesignStrings(obligation["required_evidence_classes"]) {
			if !testDesignContains([]string{"unit", "contract", "integration", "workflow", "system", "visual", "human", "performance", "security", "runtime-diagnostics", "primary-source"}, evidenceClass) {
				return fmt.Errorf("%s required_evidence_classes contains invalid value %s", obligationID, evidenceClass)
			}
		}
		capabilityRefs, err := testDesignRequireStringList(obligation, "capability_refs", obligationID, false)
		if err != nil {
			return err
		}
		scenarioRefs, err := testDesignRequireStringList(obligation, "scenario_refs", obligationID, false)
		if err != nil {
			return err
		}
		caseRefs, err := testDesignRequireStringList(obligation, "test_case_ids", obligationID, false)
		if err != nil {
			return err
		}
		gapRefs, err := testDesignRequireStringList(obligation, "gap_refs", obligationID, false)
		if err != nil {
			return err
		}
		if err := testDesignRequireEnum(obligation, "dimension", obligationID, []string{"functional", "positive", "negative", "boundary", "state", "permission", "concurrency", "timing", "failure", "recovery", "compatibility", "migration", "security", "privacy", "accessibility", "internationalization", "performance", "resilience", "observability", "operations", "policy"}); err != nil {
			return err
		}
		if err := testDesignRequireEnum(obligation, "risk_tier", obligationID, []string{"critical", "high", "medium", "low"}); err != nil {
			return err
		}
		applicability := strings.ToLower(strings.TrimSpace(asString(obligation["applicability"])))
		if !testDesignContains([]string{"applicable", "not_applicable", "excluded", "deferred", "blocked"}, applicability) {
			return fmt.Errorf("%s applicability is invalid", obligationID)
		}
		if applicability == "applicable" && len(caseRefs) == 0 {
			return fmt.Errorf("%s is applicable and must declare at least one test case", obligationID)
		}
		if testDesignContains([]string{"excluded", "deferred", "blocked"}, applicability) && len(gapRefs) == 0 {
			return fmt.Errorf("%s is %s and must declare at least one gap", obligationID, applicability)
		}
		for _, capabilityID := range capabilityRefs {
			capability, ok := capabilities[capabilityID]
			if !ok || !testDesignContains(testDesignStrings(capability["obligation_ids"]), obligationID) {
				return fmt.Errorf("%s and %s are missing a bidirectional obligation/capability link", obligationID, capabilityID)
			}
		}
		for _, scenarioID := range scenarioRefs {
			scenario, ok := scenarios[scenarioID]
			if !ok || !testDesignContains(testDesignStrings(scenario["obligation_refs"]), obligationID) {
				return fmt.Errorf("%s and %s are missing a bidirectional obligation/scenario link", obligationID, scenarioID)
			}
		}
		for _, caseID := range caseRefs {
			candidate, ok := universeCases[caseID]
			if !ok || !testDesignContains(testDesignStrings(candidate["obligation_refs"]), obligationID) {
				return fmt.Errorf("%s and %s are missing a bidirectional obligation/case link", obligationID, caseID)
			}
		}
		matchingDisposition := false
		for _, gapID := range gapRefs {
			gap, ok := gapRows[gapID]
			if !ok {
				return fmt.Errorf("%s references missing gap %s", obligationID, gapID)
			}
			if !testDesignContains(testDesignStrings(gap["affected_obligation_refs"]), obligationID) {
				return fmt.Errorf("%s and %s are missing a bidirectional obligation/gap link", obligationID, gapID)
			}
			if strings.ToLower(strings.TrimSpace(asString(gap["disposition"]))) == applicability {
				matchingDisposition = true
			}
		}
		if testDesignContains([]string{"excluded", "deferred", "blocked"}, applicability) && !matchingDisposition {
			return fmt.Errorf("%s applicability %s has no matching gap disposition", obligationID, applicability)
		}
	}
	for capabilityID, capability := range capabilities {
		if !testDesignCapabilityPattern.MatchString(capabilityID) {
			return fmt.Errorf("capability_id %s is invalid", capabilityID)
		}
		if err := testDesignRequireNonEmptyStrings(capability, capabilityID, []string{"title"}); err != nil {
			return err
		}
		requirements, err := testDesignStrictStrings(capability["requirement_refs"], capabilityID+" requirement_refs", true)
		if err != nil || len(requirements) == 0 {
			return firstTestDesignError(err, fmt.Errorf("%s must declare requirement_refs", capabilityID))
		}
		obligationIDs, err := testDesignRequireStringList(capability, "obligation_ids", capabilityID, true)
		if err != nil {
			return err
		}
		for _, obligationID := range obligationIDs {
			obligation, ok := obligations[obligationID]
			if !ok || !testDesignContains(testDesignStrings(obligation["capability_refs"]), capabilityID) {
				return fmt.Errorf("%s references missing or non-reciprocal obligation %s", capabilityID, obligationID)
			}
		}
		if _, err := testDesignRequireStringList(capability, "test_case_ids", capabilityID, true); err != nil {
			return err
		}
		if _, err := testDesignRequireStringList(capability, "scenario_ids", capabilityID, true); err != nil {
			return err
		}
		for _, scenarioID := range testDesignStrings(capability["scenario_ids"]) {
			scenario, ok := scenarios[scenarioID]
			if !ok || !testDesignContains(testDesignStrings(scenario["capability_refs"]), capabilityID) {
				return fmt.Errorf("%s and %s are missing a bidirectional capability/scenario link", capabilityID, scenarioID)
			}
		}
		for _, caseID := range testDesignStrings(capability["test_case_ids"]) {
			candidate, ok := universeCases[caseID]
			if !ok || !testDesignContains(testDesignStrings(candidate["capability_refs"]), capabilityID) {
				return fmt.Errorf("%s and %s are missing a bidirectional capability/case link", capabilityID, caseID)
			}
		}
	}
	for scenarioID, scenario := range scenarios {
		if !testDesignScenarioPattern.MatchString(scenarioID) {
			return fmt.Errorf("scenario_id %s is invalid", scenarioID)
		}
		if err := testDesignRequireNonEmptyStrings(scenario, scenarioID, []string{"title"}); err != nil {
			return err
		}
		if _, err := testDesignRequireStringList(scenario, "capability_refs", scenarioID, true); err != nil {
			return err
		}
		if _, err := testDesignRequireStringList(scenario, "test_case_ids", scenarioID, true); err != nil {
			return err
		}
		if err := testDesignValidateScenarioCoverageShape(scenarioID, scenario); err != nil {
			return err
		}
		for _, coverageID := range testDesignScenarioCoverageRefs(scenario) {
			coverage, ok := coverageRows[coverageID]
			if !ok || strings.TrimSpace(asString(coverage["scenario_ref"])) != scenarioID {
				return fmt.Errorf("%s references missing or non-reciprocal coverage %s", scenarioID, coverageID)
			}
		}
		obligationRefs, err := testDesignRequireStringList(scenario, "obligation_refs", scenarioID, true)
		if err != nil {
			return err
		}
		for _, obligationID := range obligationRefs {
			obligation, ok := obligations[obligationID]
			if !ok || !testDesignContains(testDesignStrings(obligation["scenario_refs"]), scenarioID) {
				return fmt.Errorf("%s references missing or non-reciprocal obligation %s", scenarioID, obligationID)
			}
		}
		for _, capabilityID := range testDesignStrings(scenario["capability_refs"]) {
			capability, ok := capabilities[capabilityID]
			if !ok || !testDesignContains(testDesignStrings(capability["scenario_ids"]), scenarioID) {
				return fmt.Errorf("%s references missing capability %s", scenarioID, capabilityID)
			}
		}
		for _, caseID := range testDesignStrings(scenario["test_case_ids"]) {
			candidate, ok := universeCases[caseID]
			if !ok || !testDesignContains(testDesignStrings(candidate["scenario_refs"]), scenarioID) {
				return fmt.Errorf("%s references missing test case %s", scenarioID, caseID)
			}
		}
	}
	for caseID, universeCase := range universeCases {
		if !testDesignCasePattern.MatchString(caseID) {
			return fmt.Errorf("test_case_id %s is invalid", caseID)
		}
		catalogCase := catalogCases[caseID]
		if err := testDesignRequireNonEmptyStrings(universeCase, caseID+" universe", []string{"title"}); err != nil {
			return err
		}
		if err := testDesignRequireEnum(universeCase, "kind", caseID+" universe", []string{"unit", "integration", "workflow", "review", "acceptance", "research-proof"}); err != nil {
			return err
		}
		for _, field := range []string{"capability_refs", "scenario_refs", "coverage_refs"} {
			if _, err := testDesignRequireStringList(universeCase, field, caseID+" universe", true); err != nil {
				return err
			}
		}
		if _, err := testDesignRequireStringList(universeCase, "data_refs", caseID+" universe", false); err != nil {
			return err
		}
		if err := testDesignValidateProfessionalCase(caseID, catalogCase); err != nil {
			return err
		}
		universeObligations, err := testDesignRequireStringList(universeCase, "obligation_refs", caseID+" universe", true)
		if err != nil {
			return err
		}
		catalogObligations, err := testDesignRequireStringList(catalogCase, "obligation_refs", caseID+" catalog", true)
		if err != nil {
			return err
		}
		if !testDesignSameStringSet(universeObligations, catalogObligations) ||
			!testDesignSameStringSet(testDesignStrings(universeCase["capability_refs"]), testDesignStrings(catalogCase["capability_refs"])) ||
			!testDesignSameStringSet(testDesignStrings(universeCase["scenario_refs"]), testDesignStrings(catalogCase["scenario_refs"])) ||
			!testDesignSameStringSet(testDesignStrings(universeCase["data_refs"]), testDesignStrings(catalogCase["test_data_refs"])) {
			return fmt.Errorf("%s references differ between test-universe and test-catalog", caseID)
		}
		for _, obligationID := range catalogObligations {
			obligation, ok := obligations[obligationID]
			if !ok || !testDesignContains(testDesignStrings(obligation["test_case_ids"]), caseID) {
				return fmt.Errorf("%s references missing or non-reciprocal obligation %s", caseID, obligationID)
			}
		}
		for _, capabilityID := range testDesignStrings(catalogCase["capability_refs"]) {
			capability, ok := capabilities[capabilityID]
			if !ok || !testDesignContains(testDesignStrings(capability["test_case_ids"]), caseID) {
				return fmt.Errorf("%s references missing or non-reciprocal capability %s", caseID, capabilityID)
			}
		}
		for _, scenarioID := range testDesignStrings(catalogCase["scenario_refs"]) {
			scenario, ok := scenarios[scenarioID]
			if !ok || !testDesignContains(testDesignStrings(scenario["test_case_ids"]), caseID) {
				return fmt.Errorf("%s references missing or non-reciprocal scenario %s", caseID, scenarioID)
			}
		}
		for _, coverageID := range testDesignStrings(universeCase["coverage_refs"]) {
			coverage, ok := coverageRows[coverageID]
			if !ok || strings.TrimSpace(asString(coverage["test_case_ref"])) != caseID {
				return fmt.Errorf("%s references missing or non-reciprocal coverage %s", caseID, coverageID)
			}
		}
		for _, dataID := range testDesignStrings(catalogCase["test_data_refs"]) {
			dataset, ok := datasets[dataID]
			if !ok || !testDesignContains(testDesignStrings(dataset["applicable_test_case_ids"]), caseID) {
				return fmt.Errorf("%s references missing or non-reciprocal dataset %s", caseID, dataID)
			}
		}
	}
	coverageByObligation := map[string]bool{}
	for coverageID, row := range coverageRows {
		if !testDesignCoveragePattern.MatchString(coverageID) {
			return fmt.Errorf("coverage_id %s is invalid", coverageID)
		}
		if err := testDesignRequireNonEmptyStrings(row, coverageID, []string{"requirement_ref", "obligation_ref", "capability_ref", "scenario_ref", "test_case_ref"}); err != nil {
			return err
		}
		for _, field := range []string{"test_data_refs", "evidence_refs", "acceptance_refs", "gap_refs"} {
			if _, err := testDesignRequireStringList(row, field, coverageID, false); err != nil {
				return err
			}
		}
		if err := testDesignRequireEnum(row, "status", coverageID, []string{"covered", "partial", "missing", "waived", "gap", "blocked", "deferred", "excluded", "not_applicable"}); err != nil {
			return err
		}
		caseID := strings.TrimSpace(asString(row["test_case_ref"]))
		capabilityID := strings.TrimSpace(asString(row["capability_ref"]))
		scenarioID := strings.TrimSpace(asString(row["scenario_ref"]))
		obligationID := strings.TrimSpace(asString(row["obligation_ref"]))
		catalogCase, caseOK := catalogCases[caseID]
		universeCase := universeCases[caseID]
		capability, capabilityOK := capabilities[capabilityID]
		scenario, scenarioOK := scenarios[scenarioID]
		obligation, obligationOK := obligations[obligationID]
		if !caseOK || !capabilityOK || !scenarioOK || !obligationOK {
			return fmt.Errorf("%s references a missing obligation, case, capability, or scenario", coverageID)
		}
		if !testDesignContains(testDesignStrings(catalogCase["obligation_refs"]), obligationID) ||
			!testDesignContains(testDesignStrings(universeCase["obligation_refs"]), obligationID) ||
			!testDesignContains(testDesignStrings(capability["obligation_ids"]), obligationID) ||
			!testDesignContains(testDesignStrings(scenario["obligation_refs"]), obligationID) ||
			!testDesignContains(testDesignStrings(obligation["test_case_ids"]), caseID) ||
			!testDesignContains(testDesignStrings(obligation["capability_refs"]), capabilityID) ||
			!testDesignContains(testDesignStrings(obligation["scenario_refs"]), scenarioID) ||
			!testDesignContains(testDesignStrings(catalogCase["capability_refs"]), capabilityID) ||
			!testDesignContains(testDesignStrings(catalogCase["scenario_refs"]), scenarioID) ||
			!testDesignContains(testDesignStrings(scenario["capability_refs"]), capabilityID) {
			return fmt.Errorf("%s is not bidirectionally linked", coverageID)
		}
		if !testDesignContains(testDesignStrings(universeCase["coverage_refs"]), coverageID) || !testDesignContains(testDesignScenarioCoverageRefs(scenario), coverageID) {
			return fmt.Errorf("%s is not referenced by its universe case and scenario", coverageID)
		}
		coverageByObligation[obligationID] = true
		requirement := strings.TrimSpace(asString(row["requirement_ref"]))
		if !testDesignContains(testDesignStrings(capability["requirement_refs"]), requirement) || !testDesignContains(testDesignStrings(catalogCase["requirement_refs"]), requirement) {
			return fmt.Errorf("%s requirement_ref is not declared by its capability and case", coverageID)
		}
		for _, dataID := range testDesignStrings(row["test_data_refs"]) {
			dataset, ok := datasets[dataID]
			if !ok {
				return fmt.Errorf("%s references missing dataset %s", coverageID, dataID)
			}
			if !testDesignContains(testDesignStrings(dataset["applicable_test_case_ids"]), caseID) || !testDesignContains(testDesignStrings(dataset["applicable_scenario_ids"]), scenarioID) {
				return fmt.Errorf("%s references non-reciprocal dataset %s", coverageID, dataID)
			}
		}
		if strings.ToLower(strings.TrimSpace(asString(row["status"]))) == "covered" && len(testDesignStrings(row["evidence_refs"])) == 0 && len(testDesignStrings(row["acceptance_refs"])) == 0 {
			return fmt.Errorf("%s cannot be covered without evidence_refs or acceptance_refs", coverageID)
		}
		coverageStatus := strings.ToLower(strings.TrimSpace(asString(row["status"])))
		gapRefs := testDesignStrings(row["gap_refs"])
		applicability := strings.ToLower(strings.TrimSpace(asString(obligation["applicability"])))
		switch applicability {
		case "not_applicable":
			if coverageStatus != "not_applicable" {
				return fmt.Errorf("%s status %s is incompatible with not_applicable obligation %s", coverageID, coverageStatus, obligationID)
			}
		case "excluded", "deferred":
			if coverageStatus != applicability {
				return fmt.Errorf("%s status %s must match obligation %s applicability %s", coverageID, coverageStatus, obligationID, applicability)
			}
		case "blocked":
			if coverageStatus != "blocked" {
				return fmt.Errorf("%s status %s must be blocked for obligation %s", coverageID, coverageStatus, obligationID)
			}
		case "applicable":
			if testDesignContains([]string{"not_applicable", "excluded", "deferred"}, coverageStatus) {
				return fmt.Errorf("%s status %s is incompatible with applicable obligation %s", coverageID, coverageStatus, obligationID)
			}
		}
		if coverageStatus == "covered" && len(gapRefs) != 0 {
			return fmt.Errorf("%s covered row must not declare gap_refs", coverageID)
		}
		if coverageStatus == "not_applicable" && len(gapRefs) != 0 {
			return fmt.Errorf("%s not_applicable row must not declare gap_refs", coverageID)
		}
		if testDesignContains([]string{"partial", "missing", "waived", "gap", "blocked", "deferred", "excluded"}, coverageStatus) && len(gapRefs) == 0 {
			return fmt.Errorf("%s status %s requires gap_refs", coverageID, coverageStatus)
		}
		activeGapCount := 0
		for _, gapID := range gapRefs {
			gap, ok := gapRows[gapID]
			if !ok {
				return fmt.Errorf("%s references missing gap %s", coverageID, gapID)
			}
			if !testDesignContains(testDesignStrings(obligation["gap_refs"]), gapID) {
				return fmt.Errorf("%s gap %s is not declared by obligation %s", coverageID, gapID, obligationID)
			}
			if !testDesignContains(testDesignStrings(gap["coverage_refs"]), coverageID) {
				return fmt.Errorf("%s and %s are missing a bidirectional coverage/gap link", coverageID, gapID)
			}
			disposition := strings.ToLower(strings.TrimSpace(asString(gap["disposition"])))
			if disposition == "resolved" {
				continue
			}
			activeGapCount++
			matches := false
			switch coverageStatus {
			case "partial", "missing", "gap":
				matches = disposition == "open"
			case "waived", "deferred", "excluded":
				matches = disposition == coverageStatus
			case "blocked":
				matches = disposition == "blocked" || (strings.ToLower(strings.TrimSpace(asString(gap["severity"]))) == "blocking" && disposition == "open")
			}
			if !matches {
				return fmt.Errorf("%s status %s is inconsistent with active gap %s disposition %s", coverageID, coverageStatus, gapID, disposition)
			}
		}
		if len(gapRefs) > 0 && activeGapCount == 0 {
			return fmt.Errorf("%s non-covered status has no active gap", coverageID)
		}
	}
	for obligationID, obligation := range obligations {
		if strings.ToLower(strings.TrimSpace(asString(obligation["applicability"]))) == "applicable" && !coverageByObligation[obligationID] {
			return fmt.Errorf("applicable obligation %s is absent from the coverage matrix", obligationID)
		}
	}
	for dataID, dataset := range datasets {
		if !testDesignDataPattern.MatchString(dataID) {
			return fmt.Errorf("test_data_id %s is invalid", dataID)
		}
		if err := testDesignValidateDataset(dataID, dataset); err != nil {
			return err
		}
		if boolValue(dataset["contains_pii"]) && strings.ToLower(strings.TrimSpace(asString(dataset["sensitivity"]))) != "restricted" {
			return fmt.Errorf("%s contains PII and must be restricted", dataID)
		}
		if disposition := strings.ToLower(strings.TrimSpace(asString(dataset["disposition"]))); disposition != "" && !testDesignContains([]string{"reuse", "generate", "search", "request", "block", "defer"}, disposition) {
			return fmt.Errorf("%s has unsupported disposition %s", dataID, disposition)
		}
		for _, caseID := range testDesignStrings(dataset["applicable_test_case_ids"]) {
			catalogCase, ok := catalogCases[caseID]
			if !ok {
				return fmt.Errorf("%s references missing test case %s", dataID, caseID)
			}
			if !testDesignContains(testDesignStrings(catalogCase["test_data_refs"]), dataID) {
				return fmt.Errorf("%s and %s are missing a bidirectional data/case link", dataID, caseID)
			}
		}
		for _, scenarioID := range testDesignStrings(dataset["applicable_scenario_ids"]) {
			if _, ok := scenarios[scenarioID]; !ok {
				return fmt.Errorf("%s references missing scenario %s", dataID, scenarioID)
			}
		}
	}
	for gapID, gap := range gapRows {
		for _, obligationID := range testDesignStrings(gap["affected_obligation_refs"]) {
			obligation, ok := obligations[obligationID]
			if !ok {
				return fmt.Errorf("%s references missing obligation %s", gapID, obligationID)
			}
			if !testDesignContains(testDesignStrings(obligation["gap_refs"]), gapID) {
				return fmt.Errorf("%s and %s are missing a bidirectional gap/obligation link", gapID, obligationID)
			}
		}
		for _, coverageID := range testDesignStrings(gap["coverage_refs"]) {
			coverage, ok := coverageRows[coverageID]
			if !ok {
				return fmt.Errorf("%s references missing coverage row %s", gapID, coverageID)
			}
			if !testDesignContains(testDesignStrings(coverage["gap_refs"]), gapID) {
				return fmt.Errorf("%s and %s are missing a bidirectional gap/coverage link", gapID, coverageID)
			}
		}
		for _, caseID := range testDesignStrings(gap["affected_test_case_refs"]) {
			if _, ok := catalogCases[caseID]; !ok {
				return fmt.Errorf("%s references missing test case %s", gapID, caseID)
			}
		}
		for _, dataID := range testDesignStrings(gap["affected_test_data_refs"]) {
			if _, ok := datasets[dataID]; !ok {
				return fmt.Errorf("%s references missing test data %s", gapID, dataID)
			}
		}
	}
	for dataID, dataset := range datasets {
		readiness := strings.ToLower(strings.TrimSpace(asString(dataset["readiness"])))
		if testDesignContains([]string{"deferred", "evidence-needed", "human-input-required", "blocked"}, readiness) && !testDesignHasActiveGapReference(gapRows, "affected_test_data_refs", dataID) {
			return fmt.Errorf("%s readiness %s requires an active bidirectional data gap", dataID, readiness)
		}
	}
	for caseID, candidate := range catalogCases {
		deferred := false
		if variants, ok := candidate["variants"].(map[string]any); ok {
			for _, value := range variants {
				if strings.ToLower(strings.TrimSpace(asString(value))) == "deferred" {
					deferred = true
					break
				}
			}
		}
		if deferred && !testDesignHasActiveGapReference(gapRows, "affected_test_case_refs", caseID) {
			return fmt.Errorf("%s deferred variant requires an active bidirectional case gap", caseID)
		}
	}
	if testDesignClassifyClaim(bundle) == "qualified_with_declared_gaps" && !testDesignHasAnyActiveGap(gapRows) {
		return fmt.Errorf("qualified test-design claim requires at least one active canonical gap")
	}
	return nil
}

func testDesignHasActiveGapReference(gaps map[string]map[string]any, field, ref string) bool {
	for _, gap := range gaps {
		if strings.ToLower(strings.TrimSpace(asString(gap["disposition"]))) != "resolved" && testDesignContains(testDesignStrings(gap[field]), ref) {
			return true
		}
	}
	return false
}

func testDesignHasAnyActiveGap(gaps map[string]map[string]any) bool {
	for _, gap := range gaps {
		if strings.ToLower(strings.TrimSpace(asString(gap["disposition"]))) != "resolved" {
			return true
		}
	}
	return false
}

func testDesignValidateGaps(payload map[string]any) (map[string]map[string]any, error) {
	if strings.TrimSpace(asString(payload["schema_version"])) != testDesignGapsSchema {
		return nil, fmt.Errorf("test-gaps schema_version is invalid")
	}
	if status := strings.ToLower(strings.TrimSpace(asString(payload["status"]))); !testDesignContains([]string{"open", "qualified", "blocked", "clear"}, status) {
		return nil, fmt.Errorf("test-gaps status is invalid")
	}
	gaps, err := testDesignIndexRows(payload["gaps"], "gap_id", "test-gaps gaps")
	if err != nil {
		return nil, err
	}
	for gapID, gap := range gaps {
		if !testDesignGapPattern.MatchString(gapID) {
			return nil, fmt.Errorf("gap_id %s is invalid", gapID)
		}
		allowed := map[string]bool{
			"gap_id": true, "category": true, "severity": true, "disposition": true,
			"source_refs": true, "affected_obligation_refs": true, "coverage_refs": true,
			"affected_test_case_refs": true, "affected_test_data_refs": true,
			"owner": true, "residual_risk": true, "next_action": true, "unblock_criteria": true,
		}
		if len(gap) != len(allowed) {
			return nil, fmt.Errorf("%s must use exactly the canonical gap fields", gapID)
		}
		for key := range gap {
			if !allowed[key] {
				return nil, fmt.Errorf("%s contains unsupported field %s", gapID, key)
			}
		}
		if err := testDesignRequireEnum(gap, "category", gapID, []string{"coverage", "oracle", "harness", "data", "evidence", "scope", "audit"}); err != nil {
			return nil, err
		}
		if err := testDesignRequireEnum(gap, "severity", gapID, []string{"blocking", "high", "medium", "low"}); err != nil {
			return nil, err
		}
		if err := testDesignRequireEnum(gap, "disposition", gapID, []string{"open", "deferred", "waived", "excluded", "resolved", "blocked"}); err != nil {
			return nil, err
		}
		if err := testDesignRequireNonEmptyStrings(gap, gapID, []string{"owner", "residual_risk", "next_action", "unblock_criteria"}); err != nil {
			return nil, err
		}
		if _, err := testDesignRequireStringList(gap, "affected_obligation_refs", gapID, true); err != nil {
			return nil, err
		}
		for _, field := range []string{"source_refs", "coverage_refs", "affected_test_case_refs", "affected_test_data_refs"} {
			if _, err := testDesignRequireStringList(gap, field, gapID, false); err != nil {
				return nil, err
			}
		}
	}
	return gaps, nil
}

func testDesignValidateProfessionalCase(caseID string, row map[string]any) error {
	if err := testDesignRequireNonEmptyStrings(row, caseID, []string{
		"title", "objective", "cleanup_reset", "idempotency", "side_effect_boundary",
		"freshness_rule", "residual_risk",
	}); err != nil {
		return err
	}
	for field, values := range map[string][]string{
		"status":              {"proposed", "approved", "implemented", "retired"},
		"stage":               {"unit", "integration", "workflow", "review", "acceptance", "research-proof"},
		"priority":            {"p0", "p1", "p2"},
		"automation_target":   {"automated", "manual", "hybrid", "research"},
		"owner_stage":         {"tasks", "implement", "review", "accept", "deep-research"},
		"verification_method": {"command-check", "rule-check", "manual-observation", "visual-compare", "runtime-diagnostics"},
	} {
		if err := testDesignRequireEnum(row, field, caseID, values); err != nil {
			return err
		}
	}
	for _, field := range []string{
		"risk_tags", "requirement_refs", "obligation_refs", "capability_refs", "scenario_refs",
		"environment", "entrypoint_refs", "preconditions", "roles_permissions", "configuration",
		"steps", "expected_results", "pass_criteria", "evidence_requirements", "invalidation_triggers",
	} {
		if _, err := testDesignRequireStringList(row, field, caseID, true); err != nil {
			return err
		}
	}
	if len(testDesignStrings(row["steps"])) != len(testDesignStrings(row["expected_results"])) {
		return fmt.Errorf("%s steps and expected_results must have equal length", caseID)
	}
	for _, field := range []string{"test_data_refs", "flake_risks"} {
		if _, err := testDesignRequireStringList(row, field, caseID, false); err != nil {
			return err
		}
	}
	variants, ok := row["variants"].(map[string]any)
	if !ok {
		return fmt.Errorf("%s variants must be an object", caseID)
	}
	variantFields := []string{"positive", "negative", "boundary", "state", "permission", "concurrency", "timing", "recovery", "compatibility"}
	if len(variants) != len(variantFields) {
		return fmt.Errorf("%s variants must declare exactly the professional variant matrix", caseID)
	}
	for _, field := range variantFields {
		if err := testDesignRequireEnum(variants, field, caseID+" variants", []string{"covered", "not_applicable", "deferred"}); err != nil {
			return err
		}
	}
	return nil
}

func testDesignValidateDataset(dataID string, row map[string]any) error {
	if err := testDesignRequireNonEmptyStrings(row, dataID, []string{"name"}); err != nil {
		return err
	}
	for field, values := range map[string][]string{
		"kind":        {"fixture", "seed", "synthetic", "golden", "replay", "reference"},
		"sensitivity": {"public", "internal", "sanitized", "restricted"},
		"source":      {"generated", "curated", "captured", "imported", "reused", "human-provided"},
		"disposition": {"reuse", "generate", "search", "request", "block", "defer"},
		"readiness":   {"ready", "recipe-ready", "evidence-needed", "human-input-required", "blocked", "deferred"},
	} {
		if err := testDesignRequireEnum(row, field, dataID, values); err != nil {
			return err
		}
	}
	if _, ok := row["contains_pii"].(bool); !ok {
		return fmt.Errorf("%s contains_pii must be boolean", dataID)
	}
	provenance, err := testDesignRequireStringList(row, "provenance_refs", dataID, false)
	if err != nil {
		return err
	}
	for _, field := range []string{"applicable_test_case_ids", "applicable_scenario_ids"} {
		if _, err := testDesignRequireStringList(row, field, dataID, true); err != nil {
			return err
		}
	}
	hygiene, ok := row["hygiene"].(map[string]any)
	if !ok {
		return fmt.Errorf("%s hygiene must be an object", dataID)
	}
	if err := testDesignRequireNonEmptyStrings(hygiene, dataID+" hygiene", []string{"classification_reason"}); err != nil {
		return err
	}
	if err := testDesignRequireEnum(hygiene, "sanitization_status", dataID+" hygiene", []string{"not_required", "sanitized", "restricted-access", "pending", "blocked"}); err != nil {
		return err
	}
	if err := testDesignRequireEnum(hygiene, "retention_policy", dataID+" hygiene", []string{"ephemeral", "release-bound", "long-lived", "manual-review"}); err != nil {
		return err
	}
	disposition := strings.ToLower(strings.TrimSpace(asString(row["disposition"])))
	readiness := strings.ToLower(strings.TrimSpace(asString(row["readiness"])))
	sanitization := strings.ToLower(strings.TrimSpace(asString(hygiene["sanitization_status"])))
	if testDesignContains([]string{"ready", "recipe-ready"}, readiness) && testDesignContains([]string{"pending", "blocked"}, sanitization) {
		return fmt.Errorf("%s readiness %s is incompatible with hygiene sanitization_status %s", dataID, readiness, sanitization)
	}
	standardStrings := []string{"format", "volume", "license", "usage_limits", "snapshot_binding", "refresh_policy", "cleanup_reset", "oracle_binding", "residual_risk"}
	standardArrays := []string{"constraints", "allowed_usage", "limitations"}
	if testDesignContains([]string{"generate", "reuse", "search"}, disposition) {
		if err := testDesignRequireNonEmptyStrings(row, dataID, standardStrings); err != nil {
			return err
		}
		for _, field := range standardArrays {
			requireNonEmpty := field == "allowed_usage"
			if _, err := testDesignRequireStringList(row, field, dataID, requireNonEmpty); err != nil {
				return err
			}
		}
	}
	switch disposition {
	case "generate":
		if err := testDesignRequireNonEmptyStrings(row, dataID, []string{"fixed_seed", "distribution", "checksum", "generation_recipe"}); err != nil {
			return err
		}
		if _, err := testDesignRequireStringList(row, "edge_partitions", dataID, true); err != nil {
			return err
		}
		if !testDesignContains([]string{"ready", "recipe-ready"}, readiness) {
			return fmt.Errorf("%s generate disposition has incompatible readiness %s", dataID, readiness)
		}
	case "reuse":
		if len(provenance) == 0 || readiness != "ready" {
			return fmt.Errorf("%s reuse disposition requires provenance and ready status", dataID)
		}
		if err := testDesignRequireNonEmptyStrings(row, dataID, []string{"checksum"}); err != nil {
			return err
		}
	case "search":
		if !testDesignContains([]string{"ready", "evidence-needed"}, readiness) {
			return fmt.Errorf("%s search disposition has incompatible readiness %s", dataID, readiness)
		}
		if readiness == "ready" {
			checksum := strings.TrimSpace(asString(row["checksum"]))
			if !strings.HasPrefix(checksum, "sha256:") || !testDesignSHA256Pattern.MatchString(strings.TrimPrefix(checksum, "sha256:")) {
				return fmt.Errorf("%s search-ready dataset requires checksum sha256:<64hex>", dataID)
			}
			canonicalEvidence := 0
			for _, ref := range provenance {
				if testDesignEvidenceRefPattern.MatchString(filepath.ToSlash(ref)) {
					canonicalEvidence++
				}
			}
			if canonicalEvidence == 0 {
				return fmt.Errorf("%s search-ready dataset requires canonical evidence provenance", dataID)
			}
		}
	case "request":
		if readiness != "human-input-required" {
			return fmt.Errorf("%s request disposition must be human-input-required", dataID)
		}
		if err := testDesignRequireNonEmptyStrings(row, dataID, []string{"request_instructions", "unblock_criteria", "residual_risk"}); err != nil {
			return err
		}
		if _, err := testDesignRequireStringList(row, "limitations", dataID, false); err != nil {
			return err
		}
	case "block", "defer":
		expected := "blocked"
		if disposition == "defer" {
			expected = "deferred"
		}
		if readiness != expected {
			return fmt.Errorf("%s %s disposition must have %s readiness", dataID, disposition, expected)
		}
		if err := testDesignRequireNonEmptyStrings(row, dataID, []string{"blocker_reason", "unblock_criteria", "residual_risk"}); err != nil {
			return err
		}
		if _, err := testDesignRequireStringList(row, "limitations", dataID, false); err != nil {
			return err
		}
	}
	return nil
}

func testDesignRequireNonEmptyStrings(row map[string]any, label string, fields []string) error {
	for _, field := range fields {
		if strings.TrimSpace(asString(row[field])) == "" {
			return fmt.Errorf("%s %s must be a non-empty string", label, field)
		}
	}
	return nil
}

func testDesignRequireStringList(row map[string]any, field, label string, requireNonEmpty bool) ([]string, error) {
	raw, ok := row[field].([]any)
	if !ok {
		return nil, fmt.Errorf("%s %s must be an array", label, field)
	}
	values, err := testDesignStrictStrings(raw, label+" "+field, requireNonEmpty)
	if err != nil {
		return nil, err
	}
	if len(values) != len(raw) {
		return nil, fmt.Errorf("%s %s must contain unique values", label, field)
	}
	return values, nil
}

func testDesignRequireEnum(row map[string]any, field, label string, allowed []string) error {
	value := strings.ToLower(strings.TrimSpace(asString(row[field])))
	if !testDesignContains(allowed, value) {
		return fmt.Errorf("%s %s is invalid", label, field)
	}
	return nil
}

func testDesignScenarioCoverageRefs(row map[string]any) []string {
	refs := testDesignStrings(row["coverage_refs"])
	if ref := strings.TrimSpace(asString(row["coverage_ref"])); ref != "" {
		refs = testDesignAppendUnique(refs, ref)
	}
	return refs
}

func testDesignValidateScenarioCoverageShape(scenarioID string, row map[string]any) error {
	_, hasSingle := row["coverage_ref"]
	_, hasMany := row["coverage_refs"]
	if hasSingle == hasMany {
		return fmt.Errorf("%s must declare exactly one of coverage_ref or coverage_refs", scenarioID)
	}
	if hasSingle {
		if strings.TrimSpace(asString(row["coverage_ref"])) == "" {
			return fmt.Errorf("%s coverage_ref must be non-empty", scenarioID)
		}
		return nil
	}
	_, err := testDesignRequireStringList(row, "coverage_refs", scenarioID, true)
	return err
}

func (service testDesignService) validateAcceptedProposals(root string, manifest testDesignLaneManifest, bundle testDesignBundle) error {
	cases, _ := testDesignIndexRows(bundle.Catalog["cases"], "test_case_id", "catalog cases")
	datasets, _ := testDesignIndexRows(bundle.DataManifest["datasets"], "test_data_id", "datasets")
	gapRows, _ := testDesignIndexRows(bundle.Gaps["gaps"], "gap_id", "gaps")
	for _, lane := range manifest.Lanes {
		if lane.Kind != "discovery" || lane.State != "accepted" {
			continue
		}
		resultPath, err := service.containedArtifactPath(root, lane.ResultRef)
		if err != nil {
			return fmt.Errorf("resolve accepted result for %s: %w", lane.LaneID, err)
		}
		resultRaw, err := testDesignReadRegularFile(resultPath)
		if err != nil || testDesignDigest(resultRaw) != lane.ResultSHA256 {
			return fmt.Errorf("accepted result for %s is missing or changed", lane.LaneID)
		}
		var result map[string]any
		if err := json.Unmarshal(resultRaw, &result); err != nil {
			return fmt.Errorf("read accepted result for %s: %w", lane.LaneID, err)
		}
		if err := service.validateLaneResult(result, lane); err != nil {
			return fmt.Errorf("accepted result for %s is invalid: %w", lane.LaneID, err)
		}
		for _, raw := range testDesignObjects(result["candidate_cases"]) {
			caseID := strings.TrimSpace(asString(raw["test_case_id"]))
			if caseID != "" {
				if _, ok := cases[caseID]; !ok {
					return fmt.Errorf("%s candidate %s is absent from test-catalog", lane.LaneID, caseID)
				}
			}
		}
		for _, raw := range testDesignObjects(result["data_requirements"]) {
			dataID := strings.TrimSpace(asString(raw["test_data_id"]))
			if dataID != "" {
				if _, ok := datasets[dataID]; !ok {
					return fmt.Errorf("%s data requirement %s is absent from test-data-manifest", lane.LaneID, dataID)
				}
			}
		}
		if len(testDesignArray(result["contradictions"]))+len(testDesignArray(result["unknowns"]))+len(testDesignArray(result["gaps"])) > 0 && len(gapRows) == 0 {
			return fmt.Errorf("%s has unresolved findings that are absent from test-gaps", lane.LaneID)
		}
	}
	return nil
}

func (service testDesignService) acceptedGapProposalIDs(root string, manifest testDesignLaneManifest, allowedKinds map[string]bool) (map[string]bool, error) {
	proposals := map[string]bool{}
	for _, lane := range manifest.Lanes {
		if !allowedKinds[lane.Kind] || lane.State != "accepted" || lane.ResultRef == "" {
			continue
		}
		resultPath, err := service.containedArtifactPath(root, lane.ResultRef)
		if err != nil {
			return nil, err
		}
		raw, err := testDesignReadRegularFile(resultPath)
		if err != nil || testDesignDigest(raw) != lane.ResultSHA256 {
			return nil, fmt.Errorf("accepted result for %s is missing or changed", lane.LaneID)
		}
		var result map[string]any
		if err := json.Unmarshal(raw, &result); err != nil {
			return nil, err
		}
		if err := service.validateLaneResult(result, lane); err != nil {
			return nil, fmt.Errorf("accepted result for %s is invalid: %w", lane.LaneID, err)
		}
		for _, gap := range testDesignObjects(result["gaps"]) {
			if gapID := strings.TrimSpace(asString(gap["gap_id"])); testDesignGapPattern.MatchString(gapID) {
				proposals[gapID] = true
			}
		}
	}
	return proposals, nil
}

func testDesignReconcileGapLinks(bundle *testDesignBundle, gaps map[string]map[string]any) error {
	obligations, err := testDesignIndexRows(bundle.Universe["obligations"], "obligation_id", "test-universe obligations")
	if err != nil {
		return err
	}
	coverageRows, err := testDesignIndexRows(bundle.CoverageMatrix["rows"], "coverage_id", "coverage-matrix rows")
	if err != nil {
		return err
	}
	for _, obligation := range obligations {
		obligation["gap_refs"] = []any{}
	}
	for _, coverage := range coverageRows {
		coverage["gap_refs"] = []any{}
	}
	for gapID, gap := range gaps {
		for _, obligationID := range testDesignStrings(gap["affected_obligation_refs"]) {
			obligation, ok := obligations[obligationID]
			if !ok {
				return fmt.Errorf("%s references unknown obligation %s", gapID, obligationID)
			}
			obligation["gap_refs"] = testDesignStringsToAny(testDesignAppendUnique(testDesignStrings(obligation["gap_refs"]), gapID))
		}
		for _, coverageID := range testDesignStrings(gap["coverage_refs"]) {
			coverage, ok := coverageRows[coverageID]
			if !ok {
				return fmt.Errorf("%s references unknown coverage row %s", gapID, coverageID)
			}
			coverage["gap_refs"] = testDesignStringsToAny(testDesignAppendUnique(testDesignStrings(coverage["gap_refs"]), gapID))
		}
	}
	for _, obligation := range obligations {
		refs := testDesignStrings(obligation["gap_refs"])
		sort.Strings(refs)
		obligation["gap_refs"] = testDesignStringsToAny(refs)
		terminal := ""
		for _, gapID := range refs {
			disposition := strings.ToLower(strings.TrimSpace(asString(gaps[gapID]["disposition"])))
			switch disposition {
			case "blocked":
				terminal = "blocked"
			case "deferred":
				if terminal != "blocked" {
					terminal = "deferred"
				}
			case "excluded":
				if terminal == "" {
					terminal = "excluded"
				}
			}
		}
		if terminal != "" {
			obligation["applicability"] = terminal
		} else if testDesignContains([]string{"excluded", "deferred", "blocked"}, strings.ToLower(strings.TrimSpace(asString(obligation["applicability"])))) {
			if len(testDesignStrings(obligation["test_case_ids"])) > 0 {
				obligation["applicability"] = "applicable"
			} else {
				obligation["applicability"] = "not_applicable"
			}
		}
	}
	for _, coverage := range coverageRows {
		refs := testDesignStrings(coverage["gap_refs"])
		sort.Strings(refs)
		coverage["gap_refs"] = testDesignStringsToAny(refs)
		if len(refs) == 0 {
			continue
		}
		blocked := false
		status := "partial"
		for _, gapID := range refs {
			gap := gaps[gapID]
			severity := strings.ToLower(strings.TrimSpace(asString(gap["severity"])))
			disposition := strings.ToLower(strings.TrimSpace(asString(gap["disposition"])))
			if severity == "blocking" && !testDesignContains([]string{"resolved", "waived", "excluded"}, disposition) {
				blocked = true
			}
			switch disposition {
			case "blocked":
				blocked = true
			case "deferred":
				if status != "blocked" {
					status = "deferred"
				}
			case "excluded":
				if status == "partial" {
					status = "excluded"
				}
			case "waived":
				if status == "partial" {
					status = "waived"
				}
			}
		}
		if blocked {
			coverage["status"] = "blocked"
		} else {
			coverage["status"] = status
		}
	}
	bundle.Universe["obligations"] = testDesignSortedObjectRows(obligations)
	bundle.CoverageMatrix["rows"] = testDesignSortedObjectRows(coverageRows)
	return nil
}

func testDesignGapCollectionStatus(gaps map[string]map[string]any) string {
	status := "clear"
	for _, gap := range gaps {
		disposition := strings.ToLower(strings.TrimSpace(asString(gap["disposition"])))
		severity := strings.ToLower(strings.TrimSpace(asString(gap["severity"])))
		if severity == "blocking" && !testDesignContains([]string{"resolved", "waived", "excluded"}, disposition) {
			return "blocked"
		}
		if disposition != "resolved" {
			status = "qualified"
		}
	}
	return status
}

func testDesignSortedObjectRows(values map[string]map[string]any) []any {
	keys := testDesignSortedMapKeys(values)
	rows := make([]any, 0, len(keys))
	for _, key := range keys {
		rows = append(rows, values[key])
	}
	return rows
}

func testDesignSortedMapKeys(values map[string]map[string]any) []string {
	keys := make([]string, 0, len(values))
	for key := range values {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	return keys
}

func testDesignStringsToAny(values []string) []any {
	out := make([]any, len(values))
	for index, value := range values {
		out[index] = value
	}
	return out
}

func testDesignValidateLaneObligationCoverage(manifest testDesignLaneManifest, bundle testDesignBundle) error {
	assigned := map[string]bool{}
	for _, lane := range manifest.Lanes {
		if lane.Kind != "discovery" {
			continue
		}
		for _, obligationID := range lane.ObligationIDs {
			assigned[obligationID] = true
		}
	}
	for _, obligation := range testDesignObjects(bundle.Universe["obligations"]) {
		if strings.ToLower(strings.TrimSpace(asString(obligation["applicability"]))) != "applicable" {
			continue
		}
		obligationID := strings.TrimSpace(asString(obligation["obligation_id"]))
		if obligationID != "" && !assigned[obligationID] {
			return fmt.Errorf("applicable obligation %s has no discovery lane", obligationID)
		}
	}
	return nil
}

func (service testDesignService) validateAuditGapAccounting(root string, result map[string]any, lane testDesignLane) error {
	gapPath, err := service.containedArtifactPath(root, "test-gaps.json")
	if err != nil {
		return err
	}
	canonicalGaps, err := testDesignReadObject(gapPath)
	if err != nil {
		return err
	}
	gapRows, err := testDesignIndexRows(canonicalGaps["gaps"], "gap_id", "test-gaps gaps")
	if err != nil {
		return err
	}
	proposed := map[string]bool{}
	for _, gap := range testDesignObjects(result["gaps"]) {
		proposed[strings.TrimSpace(asString(gap["gap_id"]))] = true
	}
	usedProposals := map[string]bool{}
	for _, row := range testDesignObjects(result["obligation_results"]) {
		obligationID := strings.TrimSpace(asString(row["obligation_id"]))
		for _, gapID := range testDesignStrings(row["gap_refs"]) {
			if proposed[gapID] {
				usedProposals[gapID] = true
				continue
			}
			canonical, ok := gapRows[gapID]
			if !ok || strings.ToLower(strings.TrimSpace(asString(canonical["disposition"]))) == "resolved" {
				return fmt.Errorf("%s references missing or inactive canonical gap %s", obligationID, gapID)
			}
			if !testDesignContains(testDesignStrings(canonical["affected_obligation_refs"]), obligationID) {
				return fmt.Errorf("canonical gap %s does not account for obligation %s", gapID, obligationID)
			}
		}
	}
	for gapID := range proposed {
		if !usedProposals[gapID] {
			return fmt.Errorf("new audit gap %s is not used by obligation accounting", gapID)
		}
	}
	return nil
}

func testDesignValidateStateAuditBinding(state testDesignState, manifest testDesignLaneManifest) (testDesignLane, error) {
	var zero testDesignLane
	if state.Audit.Status != "accepted" || state.Audit.LaneID == nil || state.Audit.ResultRef == nil {
		return zero, fmt.Errorf("state has no accepted audit lane/result binding")
	}
	laneID := strings.TrimSpace(*state.Audit.LaneID)
	resultRef := strings.TrimSpace(*state.Audit.ResultRef)
	acceptedAuditCount := 0
	matchCount := 0
	matched := zero
	for _, lane := range manifest.Lanes {
		if lane.Kind != "audit" || lane.State != "accepted" {
			continue
		}
		acceptedAuditCount++
		if lane.LaneID == laneID {
			matchCount++
			matched = lane
		}
	}
	if acceptedAuditCount != 1 || matchCount != 1 {
		return zero, fmt.Errorf("state audit lane %s must match the manifest's sole accepted audit lane", laneID)
	}
	if matched.ResultRef == "" || matched.ResultRef != resultRef || !testDesignSHA256Pattern.MatchString(matched.ResultSHA256) {
		return zero, fmt.Errorf("state audit result_ref does not match the accepted audit result identity")
	}
	return matched, nil
}

func (service testDesignService) validateAuditResults(root string, manifest testDesignLaneManifest, sourceFingerprint string, digests map[string]string) error {
	if err := testDesignValidateWorkerIndependence(manifest); err != nil {
		return err
	}
	for _, lane := range manifest.Lanes {
		if lane.Kind != "audit" {
			continue
		}
		if lane.State != "accepted" || lane.ResultRef == "" {
			return fmt.Errorf("audit lane %s is not accepted", lane.LaneID)
		}
		if testDesignAuditWorkerConflict(manifest, lane.WorkerID) {
			return fmt.Errorf("audit lane %s worker is not independent", lane.LaneID)
		}
		if lane.SourceFingerprint != sourceFingerprint || !testDesignSameDigests(lane.ArtifactDigests, digests) {
			return fmt.Errorf("audit lane %s is stale", lane.LaneID)
		}
		resultPath, err := service.containedArtifactPath(root, lane.ResultRef)
		if err != nil {
			return err
		}
		resultRaw, err := testDesignReadRegularFile(resultPath)
		if err != nil {
			return err
		}
		if testDesignDigest(resultRaw) != lane.ResultSHA256 {
			return fmt.Errorf("audit lane %s result digest changed", lane.LaneID)
		}
		var result map[string]any
		if err := json.Unmarshal(resultRaw, &result); err != nil {
			return err
		}
		if err := service.validateLaneResult(result, lane); err != nil {
			return fmt.Errorf("audit lane %s result is invalid: %w", lane.LaneID, err)
		}
		if err := service.validateAuditGapAccounting(root, result, lane); err != nil {
			return fmt.Errorf("audit lane %s gap accounting is invalid: %w", lane.LaneID, err)
		}
		if len(testDesignArray(result["contradictions"])) > 0 || len(testDesignArray(result["unknowns"])) > 0 {
			return fmt.Errorf("audit lane %s returned unresolved contradictions or unknowns", lane.LaneID)
		}
		if len(testDesignObjects(result["gaps"])) > 0 {
			return fmt.Errorf("audit lane %s contains newly proposed unresolved gaps that require reconciliation and a fresh audit wave", lane.LaneID)
		}
		for _, finding := range testDesignObjects(result["findings"]) {
			status := strings.ToLower(strings.TrimSpace(asString(finding["status"])))
			if status == "" || status == "open" || status == "blocked" || status == "unresolved" {
				return fmt.Errorf("audit lane %s contains unresolved finding", lane.LaneID)
			}
		}
		for _, check := range testDesignObjects(result["checks"]) {
			status := strings.ToLower(strings.TrimSpace(asString(check["status"])))
			if status == "finding" || status == "blocked" {
				return fmt.Errorf("audit lane %s contains unresolved check %s", lane.LaneID, asString(check["check_id"]))
			}
		}
	}
	return nil
}

func testDesignClassifyClaim(bundle testDesignBundle) string {
	claim := "complete_against_frozen_scope"
	for _, obligation := range testDesignObjects(bundle.Universe["obligations"]) {
		switch strings.ToLower(strings.TrimSpace(asString(obligation["applicability"]))) {
		case "blocked":
			return "blocked"
		case "excluded", "deferred":
			claim = "qualified_with_declared_gaps"
		}
	}
	for _, row := range testDesignObjects(bundle.CoverageMatrix["rows"]) {
		switch strings.ToLower(strings.TrimSpace(asString(row["status"]))) {
		case "blocked", "missing", "gap":
			return "blocked"
		case "partial", "waived", "deferred", "excluded":
			claim = "qualified_with_declared_gaps"
		}
	}
	for _, gap := range testDesignObjects(bundle.Gaps["gaps"]) {
		disposition := strings.ToLower(strings.TrimSpace(asString(gap["disposition"])))
		severity := strings.ToLower(strings.TrimSpace(asString(gap["severity"])))
		if severity == "blocking" && !testDesignContains([]string{"resolved", "waived", "excluded"}, disposition) {
			return "blocked"
		}
		if disposition != "resolved" {
			claim = "qualified_with_declared_gaps"
		}
	}
	if strings.ToLower(strings.TrimSpace(asString(bundle.Gaps["status"]))) == "blocked" {
		return "blocked"
	}
	for _, dataset := range testDesignObjects(bundle.DataManifest["datasets"]) {
		switch strings.ToLower(strings.TrimSpace(asString(dataset["readiness"]))) {
		case "blocked", "human-input-required", "evidence-needed":
			return "blocked"
		case "deferred":
			claim = "qualified_with_declared_gaps"
		}
	}
	for _, candidate := range testDesignObjects(bundle.Catalog["cases"]) {
		if variants, ok := candidate["variants"].(map[string]any); ok {
			for _, value := range variants {
				if strings.ToLower(strings.TrimSpace(asString(value))) == "deferred" {
					claim = "qualified_with_declared_gaps"
				}
			}
		}
	}
	return claim
}

func testDesignBundleDigests(root string) (map[string]string, error) {
	digests := map[string]string{}
	for _, name := range []string{"test-universe.json", "test-catalog.json", "test-data-manifest.json", "coverage-matrix.json", "test-gaps.json"} {
		raw, err := testDesignReadRegularFile(filepath.Join(root, name))
		if err != nil {
			return nil, fmt.Errorf("read %s: %w", name, err)
		}
		digests[name] = testDesignDigest(raw)
	}
	return digests, nil
}

func testDesignFileUpdates(values map[string]any) ([]fileTransactionUpdate, error) {
	paths := make([]string, 0, len(values))
	for path := range values {
		paths = append(paths, path)
	}
	sort.Strings(paths)
	updates := make([]fileTransactionUpdate, 0, len(paths))
	for _, path := range paths {
		raw, err := testDesignMarshal(values[path])
		if err != nil {
			return nil, err
		}
		updates = append(updates, fileTransactionUpdate{Path: path, Content: raw, Perm: 0o644})
	}
	return updates, nil
}

func testDesignMarshal(value any) ([]byte, error) {
	raw, err := json.MarshalIndent(value, "", "  ")
	if err != nil {
		return nil, err
	}
	return append(raw, '\n'), nil
}

func testDesignDigest(value []byte) string {
	sum := sha256.Sum256(value)
	return hex.EncodeToString(sum[:])
}

func testDesignCheckExpectedRevision(args []string, state testDesignState) error {
	raw := strings.TrimSpace(optionValue(args, "--expected-revision", ""))
	if raw == "" {
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

func testDesignStrictStrings(value any, label string, requireNonEmpty bool) ([]string, error) {
	rows, ok := value.([]any)
	if !ok {
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
		if !seen[text] {
			seen[text] = true
			out = append(out, text)
		}
	}
	if requireNonEmpty && len(out) == 0 {
		return nil, fmt.Errorf("%s must not be empty", label)
	}
	return out, nil
}

func testDesignStrings(value any) []string {
	rows, _ := value.([]any)
	out := make([]string, 0, len(rows))
	for _, raw := range rows {
		if text, ok := raw.(string); ok && strings.TrimSpace(text) != "" {
			out = append(out, strings.TrimSpace(text))
		}
	}
	return out
}

func testDesignArray(value any) []any {
	rows, _ := value.([]any)
	return rows
}

func testDesignValidateObjectArray(value any, label string, required bool) error {
	rows, ok := value.([]any)
	if !ok {
		if !required && value == nil {
			return nil
		}
		return fmt.Errorf("result %s must be an array", label)
	}
	for index, raw := range rows {
		if _, ok := raw.(map[string]any); !ok {
			return fmt.Errorf("result %s[%d] must be an object", label, index)
		}
	}
	return nil
}

func testDesignObjects(value any) []map[string]any {
	rows, _ := value.([]any)
	out := make([]map[string]any, 0, len(rows))
	for _, raw := range rows {
		if row, ok := raw.(map[string]any); ok {
			out = append(out, row)
		}
	}
	return out
}

func testDesignIndexRows(value any, idKey, label string) (map[string]map[string]any, error) {
	rows, ok := value.([]any)
	if !ok {
		return nil, fmt.Errorf("%s must be an array", label)
	}
	out := map[string]map[string]any{}
	for index, raw := range rows {
		row, ok := raw.(map[string]any)
		if !ok {
			return nil, fmt.Errorf("%s[%d] must be an object", label, index)
		}
		id := strings.TrimSpace(asString(row[idKey]))
		if id == "" {
			return nil, fmt.Errorf("%s[%d].%s must be non-empty", label, index, idKey)
		}
		if _, exists := out[id]; exists {
			return nil, fmt.Errorf("%s contains duplicate %s %s", label, idKey, id)
		}
		out[id] = row
	}
	return out, nil
}

func testDesignSameKeys(left, right map[string]map[string]any) bool {
	if len(left) != len(right) {
		return false
	}
	for key := range left {
		if _, ok := right[key]; !ok {
			return false
		}
	}
	return true
}

func testDesignSameStringSet(left, right []string) bool {
	if len(left) != len(right) {
		return false
	}
	seen := map[string]bool{}
	for _, value := range left {
		seen[value] = true
	}
	for _, value := range right {
		if !seen[value] {
			return false
		}
	}
	return true
}

func testDesignContains(values []string, want string) bool {
	for _, value := range values {
		if value == want {
			return true
		}
	}
	return false
}

func testDesignPathCovered(candidate string, scopes []string) bool {
	candidate = strings.TrimSuffix(filepath.ToSlash(filepath.Clean(filepath.FromSlash(candidate))), "/")
	for _, raw := range scopes {
		scope := strings.TrimSuffix(filepath.ToSlash(filepath.Clean(filepath.FromSlash(raw))), "/")
		if scope == "." || candidate == scope || strings.HasPrefix(candidate, scope+"/") {
			return true
		}
	}
	return false
}

func testDesignFindLane(manifest testDesignLaneManifest, laneID string) int {
	for index := range manifest.Lanes {
		if manifest.Lanes[index].LaneID == laneID {
			return index
		}
	}
	return -1
}

func testDesignAuditWorkerConflict(manifest testDesignLaneManifest, workerID string) bool {
	if workerID == "" || workerID == manifest.LeaderID || workerID == manifest.SynthesisOwnerID {
		return true
	}
	for _, lane := range manifest.Lanes {
		if lane.Kind == "discovery" && lane.State == "accepted" && lane.WorkerID == workerID {
			return true
		}
	}
	return false
}

func testDesignValidateWorkerIndependence(manifest testDesignLaneManifest) error {
	if !testDesignWorkerIDPattern.MatchString(manifest.LeaderID) {
		return fmt.Errorf("generation leader_id is missing or invalid")
	}
	acceptedDiscovery := 0
	for _, lane := range manifest.Lanes {
		if lane.Kind != "discovery" || lane.State != "accepted" {
			continue
		}
		acceptedDiscovery++
		if !testDesignWorkerIDPattern.MatchString(lane.WorkerID) {
			return fmt.Errorf("accepted discovery lane %s has no valid worker identity", lane.LaneID)
		}
		if lane.WorkerID == manifest.LeaderID {
			return fmt.Errorf("accepted discovery lane %s was performed by the generation leader", lane.LaneID)
		}
	}
	if acceptedDiscovery == 0 {
		return fmt.Errorf("no accepted independent discovery lane exists")
	}
	return nil
}

func testDesignNextAttemptID(manifest testDesignLaneManifest) string {
	next := 1
	for _, lane := range manifest.Lanes {
		next += lane.AttemptNumber
	}
	return fmt.Sprintf("ATTEMPT-%03d", next)
}

func testDesignLaneCounts(manifest testDesignLaneManifest) map[string]int {
	counts := map[string]int{"pending": 0, "leased": 0, "accepted": 0, "blocked": 0}
	for _, lane := range manifest.Lanes {
		counts[lane.State]++
	}
	return counts
}

func testDesignActiveLeases(manifest testDesignLaneManifest) []any {
	leases := []any{}
	for _, lane := range manifest.Lanes {
		if lane.State == "leased" {
			leases = append(leases, map[string]any{
				"lane_id": lane.LaneID, "attempt_id": lane.AttemptID, "worker_id": lane.WorkerID,
				"checkpoint_sequence": lane.CheckpointSequence, "checkpoint_ref": lane.CheckpointRef,
			})
		}
	}
	return leases
}

func testDesignLanePacket(lane testDesignLane) map[string]any {
	return map[string]any{
		"lane_id": lane.LaneID, "kind": lane.Kind, "title": lane.Title,
		"obligation_ids": lane.ObligationIDs, "read_paths": lane.ReadPaths, "questions": lane.Questions,
		"attempt_id": lane.AttemptID, "prior_checkpoint_ref": nullableTestDesignString(lane.CheckpointRef),
		"source_fingerprint": nullableTestDesignString(lane.SourceFingerprint), "artifact_digests": lane.ArtifactDigests,
		"stop_conditions": []string{"Do not inspect unassigned paths.", "Checkpoint and yield when evidence is insufficient or the packet exceeds capacity.", "Do not edit canonical test-design artifacts or declare global completeness."},
	}
}

func testDesignAllLanesAccepted(manifest testDesignLaneManifest) bool {
	return len(manifest.Lanes) > 0 && testDesignKindLanesAccepted(manifest, "", false)
}

func testDesignKindLanesAccepted(manifest testDesignLaneManifest, kind string, requireOne bool) bool {
	count := 0
	for _, lane := range manifest.Lanes {
		if kind != "" && lane.Kind != kind {
			continue
		}
		count++
		if lane.State != "accepted" {
			return false
		}
	}
	return count > 0 || !requireOne
}

func testDesignStateData(state testDesignState, rootRef string) map[string]any {
	featureDir := any(nil)
	if state.FeatureDir != nil {
		featureDir = *state.FeatureDir
	}
	return map[string]any{
		"artifact_root":      rootRef,
		"scope":              state.Scope,
		"mode":               state.Mode,
		"feature_dir":        featureDir,
		"revision":           state.Revision,
		"phase":              state.Phase,
		"status":             state.Status,
		"claim_status":       state.ClaimStatus,
		"source_fingerprint": state.Source.Fingerprint,
	}
}

func testDesignNextSubcommand(state testDesignState, manifest testDesignLaneManifest) string {
	counts := testDesignLaneCounts(manifest)
	if counts["pending"] > 0 {
		return "lane-lease"
	}
	if counts["leased"] > 0 {
		return "status"
	}
	switch state.Phase {
	case "scoped":
		return "universe-build"
	case "universe-ready":
		return "lane-prepare"
	case "discovery":
		return "synthesize"
	case "synthesis":
		return "audit-prepare"
	case "audit":
		return "validate"
	case "validated":
		if state.Scope == "project" {
			return "publish"
		}
		return "handoff"
	case "handed-off":
		return "publish"
	default:
		return ""
	}
}

func testDesignCoverageObligationRefs(coverage map[string]any) []string {
	seen := map[string]bool{}
	for _, row := range testDesignObjects(coverage["rows"]) {
		if value := strings.TrimSpace(asString(row["obligation_ref"])); value != "" {
			seen[value] = true
		}
	}
	return testDesignSortedKeys(seen)
}

func testDesignUniverseObligationRefs(universe map[string]any) []string {
	seen := map[string]bool{}
	for _, row := range testDesignObjects(universe["obligations"]) {
		if value := strings.TrimSpace(asString(row["obligation_id"])); value != "" {
			seen[value] = true
		}
	}
	return testDesignSortedKeys(seen)
}

func testDesignObligationPointers(universe map[string]any) []string {
	return testDesignPointerList("test-universe.json#/obligations/", testDesignUniverseObligationRefs(universe))
}

func testDesignCatalogPointers(catalog map[string]any) []string {
	seen := map[string]bool{}
	for _, row := range testDesignObjects(catalog["cases"]) {
		if id := strings.TrimSpace(asString(row["test_case_id"])); id != "" {
			seen["test-catalog.json#/cases/"+id] = true
		}
	}
	return testDesignSortedKeys(seen)
}

func testDesignDataPointers(manifest map[string]any) []string {
	seen := map[string]bool{}
	for _, row := range testDesignObjects(manifest["datasets"]) {
		if id := strings.TrimSpace(asString(row["test_data_id"])); id != "" {
			seen["test-data-manifest.json#/datasets/"+id] = true
		}
	}
	return testDesignSortedKeys(seen)
}

func testDesignCoveragePointers(matrix map[string]any) []string {
	seen := map[string]bool{}
	for _, row := range testDesignObjects(matrix["rows"]) {
		if id := strings.TrimSpace(asString(row["coverage_id"])); id != "" {
			seen["coverage-matrix.json#/rows/"+id] = true
		}
	}
	return testDesignSortedKeys(seen)
}

func testDesignGapPointers(gaps map[string]any) []string {
	seen := map[string]bool{}
	for _, row := range testDesignObjects(gaps["gaps"]) {
		if id := strings.TrimSpace(asString(row["gap_id"])); id != "" {
			seen["test-gaps.json#/gaps/"+id] = true
		}
	}
	return testDesignSortedKeys(seen)
}

func testDesignSortedKeys(values map[string]bool) []string {
	out := make([]string, 0, len(values))
	for value := range values {
		out = append(out, value)
	}
	sort.Strings(out)
	return out
}

func testDesignAppendUnique(values []string, value string) []string {
	if testDesignContains(values, value) {
		return values
	}
	return append(values, value)
}

func testDesignStringPointer(value string) *string {
	value = strings.TrimSpace(value)
	if value == "" {
		return nil
	}
	return &value
}

func testDesignCloneDigests(values map[string]string) map[string]string {
	out := make(map[string]string, len(values))
	for key, value := range values {
		out[key] = value
	}
	return out
}

func testDesignSameDigests(left, right map[string]string) bool {
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

func testDesignFailure(status, summary string, err error) Envelope {
	env := NewEnvelope(status, summary)
	if err != nil {
		env.Blockers = append(env.Blockers, err.Error())
	}
	return env
}

func firstTestDesignError(primary, fallback error) error {
	if primary != nil {
		return primary
	}
	return fallback
}

func nullableTestDesignString(value string) any {
	if strings.TrimSpace(value) == "" {
		return nil
	}
	return value
}
