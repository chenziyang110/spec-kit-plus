package scanworkbench

import (
	"bytes"
	"crypto/sha256"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"sync"
	"time"

	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/scanartifacts"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/scanset"
)

const (
	defaultPacketSize           = 25
	workbenchProtocolV2         = "map_scan_workbench.v2"
	acceptanceReceiptProtocolV1 = "map_scan_acceptance.v1"
)

const (
	workbenchLockRetryInterval = 25 * time.Millisecond
	workbenchLockWait          = 30 * time.Second
	workbenchLockHeartbeat     = 20 * time.Second
	workbenchLockStaleAfter    = 2 * time.Minute
)

var packetIDPattern = regexp.MustCompile(`^[A-Za-z0-9][A-Za-z0-9._-]*$`)
var workerIDPattern = regexp.MustCompile(`^[A-Za-z0-9/][A-Za-z0-9._:/-]{0,127}$`)

type PrepareInput struct {
	ScanSetPath        string
	PacketSize         int
	MaxPaths           int
	MaxBytes           int64
	WorkerBudgetTokens int64
	Force              bool
}

type PreparePayload struct {
	Status        string   `json:"status"`
	PathCount     int      `json:"path_count"`
	PacketCount   int      `json:"packet_count"`
	PacketIDs     []string `json:"packet_ids"`
	ScanSetPath   string   `json:"scan_set_path"`
	WorkbenchPath string   `json:"workbench_path"`
	NextAction    string   `json:"next_action"`
}

type AcceptInput struct {
	PacketID   string
	AttemptID  string
	ResultPath string
}

type AcceptPayload struct {
	Status            string `json:"status"`
	PacketID          string `json:"packet_id"`
	AcceptedPathCount int    `json:"accepted_path_count"`
	PendingPackets    int    `json:"pending_packets"`
	WorkerResultPath  string `json:"worker_result_path"`
	CompletionAllowed bool   `json:"completion_allowed"`
	CompletionGate    string `json:"completion_gate"`
	NextAction        string `json:"next_action"`
}

type scanSetFile struct {
	Files []string `json:"files"`
}

type pathClassification struct {
	Path                 string
	PathKind             string
	Extension            string
	SizeBytes            int64
	DirectoryFamily      string
	GitTracked           bool
	ValueTier            string
	ScanDecision         string
	Disposition          string
	Criticality          string
	ClassificationReason string
	DecisionSource       string
}

type queueFile struct {
	Protocol     string        `json:"protocol,omitempty"`
	GenerationID string        `json:"generation_id,omitempty"`
	ScanSetPath  string        `json:"scan_set_path,omitempty"`
	Packets      []queuePacket `json:"packets"`
}

type queuePacket struct {
	PacketID               string   `json:"packet_id"`
	State                  string   `json:"state"`
	AssignedPaths          []string `json:"assigned_paths"`
	ResultHandoffPath      string   `json:"result_handoff_path"`
	ParentPacketID         string   `json:"parent_packet_id,omitempty"`
	WorkerID               string   `json:"worker_id,omitempty"`
	AttemptID              string   `json:"attempt_id,omitempty"`
	AttemptNumber          int      `json:"attempt_number,omitempty"`
	CheckpointPath         string   `json:"checkpoint_path,omitempty"`
	CheckpointSequence     int      `json:"checkpoint_sequence,omitempty"`
	CompletedPaths         []string `json:"completed_paths,omitempty"`
	EstimatedTokens        int64    `json:"estimated_tokens"`
	EstimatedBytes         int64    `json:"estimated_bytes"`
	EffectiveContextBudget int64    `json:"effective_context_budget_tokens"`
	Oversized              bool     `json:"oversized,omitempty"`
}

type handoffFile struct {
	Events []map[string]any `json:"events"`
}

type coverageFile struct {
	Rows []map[string]any `json:"rows"`
}

type coverageLedgerFile struct {
	Rows     []map[string]any `json:"rows"`
	OpenGaps []map[string]any `json:"open_gaps"`
}

type workerLedger struct {
	Todo     []string `json:"todo"`
	Doing    []string `json:"doing"`
	Done     []string `json:"done"`
	Blocked  []string `json:"blocked"`
	Overflow []string `json:"overflow"`
}

type workerResult struct {
	Protocol      string           `json:"protocol,omitempty"`
	PacketID      string           `json:"packet_id"`
	AttemptID     string           `json:"attempt_id,omitempty"`
	Sequence      int              `json:"sequence,omitempty"`
	FamilyID      string           `json:"family_id,omitempty"`
	AssignedPaths []string         `json:"assigned_paths"`
	PathsRead     []string         `json:"paths_read"`
	Ledger        workerLedger     `json:"ledger"`
	Coverage      []map[string]any `json:"coverage"`
	Evidence      []map[string]any `json:"evidence"`
	Nodes         []map[string]any `json:"nodes"`
	Edges         []map[string]any `json:"edges"`
	Observations  []map[string]any `json:"observations"`
	Claims        []map[string]any `json:"claims,omitempty"`
	Confidence    string           `json:"confidence"`
	Acceptance    string           `json:"acceptance"`
}

type acceptanceReceipt struct {
	Protocol              string `json:"protocol"`
	WorkbenchGenerationID string `json:"workbench_generation_id"`
	PacketID              string `json:"packet_id"`
	AttemptID             string `json:"attempt_id"`
	Sequence              int    `json:"sequence"`
	SourceResultPath      string `json:"source_result_path"`
	SubmissionPath        string `json:"submission_path"`
	SubmissionSHA256      string `json:"submission_sha256"`
	CanonicalResultPath   string `json:"canonical_result_path"`
	CanonicalResultSHA256 string `json:"canonical_result_sha256"`
	AcceptedPathCount     int    `json:"accepted_path_count"`
}

// Prepare converts the runtime-produced scan set into deterministic boundary,
// target, and queue projections. Every dispatch-eligible path is concrete and
// assigned exactly once; inventory-only paths remain boundary accounting.
func Prepare(paths rt.Paths, input PrepareInput) (PreparePayload, error) {
	if err := validateRuntimeControlDir(paths); err != nil {
		return PreparePayload{}, err
	}
	release, err := acquireWorkbenchLock(paths)
	if err != nil {
		return PreparePayload{}, err
	}
	defer release()
	return prepareUnlocked(paths, input)
}

func prepareUnlocked(paths rt.Paths, input PrepareInput) (PreparePayload, error) {
	scanSetPath := strings.TrimSpace(input.ScanSetPath)
	if scanSetPath == "" {
		scanSetPath = scanset.DefaultOutputPath
	}
	maxPaths := input.MaxPaths
	if maxPaths == 0 {
		maxPaths = input.PacketSize
	}
	if maxPaths == 0 {
		maxPaths = defaultPacketSize
	}
	if maxPaths < 1 || maxPaths > 150 {
		return PreparePayload{}, fmt.Errorf("packet size must be between 1 and 150")
	}
	if input.WorkerBudgetTokens < 0 {
		return PreparePayload{}, fmt.Errorf("worker token budget must not be negative")
	}
	if input.MaxBytes < 0 {
		return PreparePayload{}, fmt.Errorf("packet byte budget must not be negative")
	}
	workerBudgetTokens := input.WorkerBudgetTokens
	if workerBudgetTokens == 0 {
		workerBudgetTokens = defaultEffectiveWorkerTokens
	}
	maxBytes := input.MaxBytes
	if maxBytes == 0 {
		maxBytes = defaultPacketBytes
	}

	absScanSet, relScanSet, err := resolveRepositoryFile(paths.Root, scanSetPath)
	if err != nil {
		return PreparePayload{}, fmt.Errorf("resolve scan set: %w", err)
	}
	var scanSet scanSetFile
	if err := readJSON(absScanSet, &scanSet); err != nil {
		return PreparePayload{}, fmt.Errorf("read canonical scan set: %w", err)
	}
	files, err := validateScanSetPaths(paths.Root, scanSet.Files)
	if err != nil {
		return PreparePayload{}, err
	}
	if len(files) == 0 {
		return PreparePayload{}, fmt.Errorf("canonical scan set contains no files")
	}
	if err := requireWorkbenchReplacementAllowed(paths, input.Force); err != nil {
		return PreparePayload{}, err
	}

	classifications, err := classifyRepositoryPaths(paths.Root, files)
	if err != nil {
		return PreparePayload{}, err
	}
	packetPaths := scanPacketPaths(classifications)
	if len(packetPaths) == 0 {
		return PreparePayload{}, fmt.Errorf("canonical scan set contains no scan-eligible files after value classification")
	}
	plans, err := planPackets(paths.Root, packetPaths, packetPlanningBudget{
		MaxPaths: maxPaths, MaxBytes: maxBytes, MaxTokens: workerBudgetTokens,
	})
	if err != nil {
		return PreparePayload{}, err
	}
	generationID, err := scanGenerationID(paths.Root, files)
	if err != nil {
		return PreparePayload{}, err
	}

	if err := resetWorkbench(paths); err != nil {
		return PreparePayload{}, err
	}
	if err := writePreparedStatus(paths); err != nil {
		return PreparePayload{}, err
	}

	packetIDs := make([]string, 0, len(plans))
	queue := queueFile{
		Protocol: workbenchProtocolV2, GenerationID: generationID,
		ScanSetPath: filepath.ToSlash(relScanSet), Packets: []queuePacket{},
	}
	handoffs := handoffFile{Events: []map[string]any{}}
	for _, plan := range plans {
		packetID := fmt.Sprintf("lane-%03d", len(packetIDs)+1)
		assigned := append([]string{}, plan.Paths...)
		resultPath := canonicalWorkerResultPath(packetID)
		packetIDs = append(packetIDs, packetID)
		queue.Packets = append(queue.Packets, queuePacket{
			PacketID:               packetID,
			State:                  "pending",
			AssignedPaths:          assigned,
			ResultHandoffPath:      resultPath,
			EstimatedTokens:        plan.EstimatedTokens,
			EstimatedBytes:         plan.EstimatedBytes,
			EffectiveContextBudget: workerBudgetTokens,
			Oversized:              plan.Oversized,
		})
		handoffs.Events = append(handoffs.Events, map[string]any{
			"event_id":            "dispatch-" + packetID,
			"packet_id":           packetID,
			"event_type":          "prepared",
			"result_handoff_path": resultPath,
		})
		if err := writeTextAtomic(
			filepath.Join(paths.RuntimeDir, "workbench", "scan-packets", packetID+".md"),
			renderPacket(packetID, assigned),
		); err != nil {
			return PreparePayload{}, err
		}
		if err := writeJSONAtomic(
			filepath.Join(paths.RuntimeDir, "workbench", "pending-results", packetID+".json"),
			workerResultSkeleton(packetID, "", assigned),
		); err != nil {
			return PreparePayload{}, err
		}
	}

	workbench := filepath.Join(paths.RuntimeDir, "workbench")
	writes := []struct {
		path  string
		value any
	}{
		{filepath.Join(workbench, "repository-universe.json"), repositoryUniverse(classifications)},
		{filepath.Join(workbench, "scan-targets.json"), scanTargets(classifications)},
		{filepath.Join(workbench, "scan-queue.json"), queue},
		{filepath.Join(workbench, "handoff-ledger.json"), handoffs},
		{filepath.Join(workbench, "coverage-ledger.json"), coverageLedgerFile{Rows: []map[string]any{}, OpenGaps: []map[string]any{}}},
		{filepath.Join(workbench, "capability-ledger.json"), map[string]any{"rows": []map[string]any{}}},
		{filepath.Join(workbench, "control-ledger.json"), map[string]any{"rows": []map[string]any{}}},
		{filepath.Join(paths.RuntimeDir, "coverage.json"), coverageFile{Rows: []map[string]any{}}},
		{filepath.Join(paths.RuntimeDir, "provisional", "nodes.json"), map[string]any{"nodes": []map[string]any{}}},
		{filepath.Join(paths.RuntimeDir, "provisional", "edges.json"), map[string]any{"edges": []map[string]any{}}},
		{filepath.Join(paths.RuntimeDir, "provisional", "observations.json"), map[string]any{"observations": []map[string]any{}}},
		{filepath.Join(paths.RuntimeDir, "provisional", "claims.json"), map[string]any{"claims": []map[string]any{}}},
	}
	for _, item := range writes {
		if err := writeJSONAtomic(item.path, item.value); err != nil {
			return PreparePayload{}, err
		}
	}
	if err := renderHumanState(paths, queue, coverageLedgerFile{Rows: []map[string]any{}, OpenGaps: []map[string]any{}}); err != nil {
		return PreparePayload{}, err
	}

	return PreparePayload{
		Status:        "prepared",
		PathCount:     len(files),
		PacketCount:   len(packetIDs),
		PacketIDs:     packetIDs,
		ScanSetPath:   filepath.ToSlash(relScanSet),
		WorkbenchPath: ".specify/project-cognition/workbench",
		NextAction:    "dispatch_scan_packets",
	}, nil
}

// Accept validates one packet-local result before merging any of its evidence
// into the canonical scan package. A result can only describe its assigned paths.
func Accept(paths rt.Paths, input AcceptInput) (AcceptPayload, error) {
	if err := validateRuntimeControlDir(paths); err != nil {
		return AcceptPayload{}, err
	}
	release, err := acquireWorkbenchLock(paths)
	if err != nil {
		return AcceptPayload{}, err
	}
	defer release()
	return acceptUnlocked(paths, input)
}

func acceptUnlocked(paths rt.Paths, input AcceptInput) (AcceptPayload, error) {
	packetID := strings.TrimSpace(input.PacketID)
	if !packetIDPattern.MatchString(packetID) {
		return AcceptPayload{}, fmt.Errorf("invalid packet id %q", input.PacketID)
	}
	queuePath := filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json")
	var queue queueFile
	if err := readJSON(queuePath, &queue); err != nil {
		return AcceptPayload{}, fmt.Errorf("read scan queue: %w", err)
	}
	isV2, err := classifyWorkbenchProtocol(queue)
	if err != nil {
		return AcceptPayload{}, err
	}
	packetIndex := -1
	for i := range queue.Packets {
		if queue.Packets[i].PacketID == packetID {
			packetIndex = i
			break
		}
	}
	if packetIndex < 0 {
		return AcceptPayload{}, fmt.Errorf("packet %s is not present in scan-queue.json", packetID)
	}
	packet := queue.Packets[packetIndex]
	if isV2 && packet.State == "pending" {
		return AcceptPayload{}, fmt.Errorf("packet %s must be claimed with scan-lease before scan-accept", packetID)
	}
	if packet.State != "pending" && packet.State != "leased" && packet.State != "accepted" {
		return AcceptPayload{}, fmt.Errorf("packet %s state %s is not acceptable", packetID, packet.State)
	}
	if packet.State == "leased" {
		attemptID := strings.TrimSpace(input.AttemptID)
		if attemptID == "" || attemptID != packet.AttemptID {
			return AcceptPayload{}, fmt.Errorf("packet %s requires active attempt_id %s", packetID, packet.AttemptID)
		}
	}

	resultPath := strings.TrimSpace(input.ResultPath)
	if resultPath == "" {
		if packet.CheckpointPath != "" {
			resultPath = filepath.Join(paths.Root, filepath.FromSlash(packet.CheckpointPath))
		} else {
			resultPath = filepath.Join(paths.RuntimeDir, "workbench", "pending-results", packetID+".json")
		}
	} else if !filepath.IsAbs(resultPath) {
		resultPath = filepath.Join(paths.Root, filepath.FromSlash(resultPath))
	}
	var result workerResult
	if err := readJSON(resultPath, &result); err != nil {
		return AcceptPayload{}, fmt.Errorf("read worker result: %w", err)
	}
	submittedResult := result
	submissionValue, submissionDigest, err := readNormalizedJSONFile(resultPath)
	if err != nil {
		return AcceptPayload{}, fmt.Errorf("hash worker result: %w", err)
	}
	if isV2 {
		if result.Protocol != "map_scan_result.v2" {
			return AcceptPayload{}, fmt.Errorf("packet %s result protocol %q must be map_scan_result.v2", packetID, result.Protocol)
		}
		if strings.TrimSpace(result.AttemptID) == "" || result.Sequence < 1 {
			return AcceptPayload{}, fmt.Errorf("packet %s v2 result requires attempt_id and positive sequence", packetID)
		}
		if result.Acceptance != "partial" {
			return AcceptPayload{}, fmt.Errorf("packet %s worker-authored acceptance must remain partial; scan-accept derives pass after runtime validation", packetID)
		}
		result.Acceptance = "pass"
	}
	if packet.State == "leased" && result.AttemptID != packet.AttemptID {
		return AcceptPayload{}, fmt.Errorf("packet %s worker result attempt_id %q does not match active attempt %s", packetID, result.AttemptID, packet.AttemptID)
	}
	allAssignedPaths := map[string]bool{}
	for _, queuedPacket := range queue.Packets {
		for path := range normalizedSet(queuedPacket.AssignedPaths) {
			allAssignedPaths[path] = true
		}
	}
	if err := validateWorkerResult(packet, result, allAssignedPaths); err != nil {
		return AcceptPayload{}, err
	}
	submissionPath := acceptanceSubmissionPath(paths, resultPath)
	if packet.State == "accepted" {
		return acceptAlreadyCommitted(
			paths,
			queue,
			packet,
			submissionPath,
			submissionValue,
			submissionDigest,
			submittedResult,
			result,
		)
	}
	if err := ensureEvidenceCompatible(paths, packetID, result.Evidence); err != nil {
		return AcceptPayload{}, err
	}

	var nodes map[string][]map[string]any
	var edges map[string][]map[string]any
	var observations map[string][]map[string]any
	var claims map[string][]map[string]any
	var coverage coverageFile
	var coverageLedger coverageLedgerFile
	var handoffs handoffFile
	if err := readJSON(filepath.Join(paths.RuntimeDir, "provisional", "nodes.json"), &nodes); err != nil {
		return AcceptPayload{}, err
	}
	if err := readJSON(filepath.Join(paths.RuntimeDir, "provisional", "edges.json"), &edges); err != nil {
		return AcceptPayload{}, err
	}
	if err := readJSON(filepath.Join(paths.RuntimeDir, "provisional", "observations.json"), &observations); err != nil {
		return AcceptPayload{}, err
	}
	if err := readJSON(filepath.Join(paths.RuntimeDir, "provisional", "claims.json"), &claims); err != nil {
		return AcceptPayload{}, err
	}
	if err := readJSON(filepath.Join(paths.RuntimeDir, "coverage.json"), &coverage); err != nil {
		return AcceptPayload{}, err
	}
	if err := readJSON(filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json"), &coverageLedger); err != nil {
		return AcceptPayload{}, err
	}
	if err := readJSON(filepath.Join(paths.RuntimeDir, "workbench", "handoff-ledger.json"), &handoffs); err != nil {
		return AcceptPayload{}, err
	}
	canonicalResult := filepath.Join(paths.RuntimeDir, "workbench", "worker-results", packetID+".json")
	if err := ensureWorkerResultCompatible(canonicalResult, result); err != nil {
		return AcceptPayload{}, err
	}
	submissionSnapshotPath := acceptanceSubmissionSnapshotPath(paths, packetID)
	if isV2 {
		if err := ensureNormalizedJSONCompatible(submissionSnapshotPath, submissionValue); err != nil {
			return AcceptPayload{}, err
		}
	}
	var receipt acceptanceReceipt
	if isV2 {
		receipt, err = newAcceptanceReceipt(
			queue,
			packet,
			submissionPath,
			submissionDigest,
			submittedResult,
			result,
		)
		if err != nil {
			return AcceptPayload{}, err
		}
		if err := ensureAcceptanceReceiptCompatible(
			acceptanceReceiptPath(paths, packetID),
			receipt,
		); err != nil {
			return AcceptPayload{}, err
		}
	}

	if nodes["nodes"], err = mergeObjectRows(nodes["nodes"], result.Nodes, "id", "node"); err != nil {
		return AcceptPayload{}, err
	}
	if edges["edges"], err = mergeObjectRows(edges["edges"], result.Edges, "id", "edge"); err != nil {
		return AcceptPayload{}, err
	}
	if observations["observations"], err = mergeObjectRows(observations["observations"], result.Observations, "id", "observation"); err != nil {
		return AcceptPayload{}, err
	}
	if claims["claims"], err = mergeObjectRows(claims["claims"], result.Claims, "id", "claim"); err != nil {
		return AcceptPayload{}, err
	}
	if coverage.Rows, err = mergeObjectRows(coverage.Rows, result.Coverage, "path", "coverage"); err != nil {
		return AcceptPayload{}, err
	}
	ledgerRows := make([]map[string]any, 0, len(result.Coverage))
	for _, row := range result.Coverage {
		ledgerRow := cloneObject(row)
		ledgerRow["packet_id"] = packetID
		ledgerRow["status"] = stringValue(row["outcome"])
		ledgerRows = append(ledgerRows, ledgerRow)
	}
	if coverageLedger.Rows, err = mergeObjectRows(coverageLedger.Rows, ledgerRows, "path", "coverage ledger"); err != nil {
		return AcceptPayload{}, err
	}
	queue.Packets[packetIndex].State = "accepted"
	returnEvent := map[string]any{
		"event_id":           "return-" + packetID,
		"packet_id":          packetID,
		"event_type":         "returned",
		"worker_result_path": canonicalWorkerResultPath(packetID),
	}
	if packet.AttemptID != "" {
		returnEvent["attempt_id"] = packet.AttemptID
		returnEvent["worker_id"] = packet.WorkerID
	}
	if handoffs.Events, err = mergeObjectRows(handoffs.Events, []map[string]any{returnEvent}, "event_id", "handoff"); err != nil {
		return AcceptPayload{}, err
	}

	// Every write before the queue commit is idempotently mergeable. This makes
	// an interrupted accept retryable without duplicating packet-local rows.
	writes := []struct {
		path  string
		value any
	}{
		{filepath.Join(paths.RuntimeDir, "evidence", packetID+".json"), map[string]any{"rows": result.Evidence}},
		{filepath.Join(paths.RuntimeDir, "provisional", "nodes.json"), nodes},
		{filepath.Join(paths.RuntimeDir, "provisional", "edges.json"), edges},
		{filepath.Join(paths.RuntimeDir, "provisional", "observations.json"), observations},
		{filepath.Join(paths.RuntimeDir, "provisional", "claims.json"), claims},
		{filepath.Join(paths.RuntimeDir, "coverage.json"), coverage},
		{canonicalResult, result},
		{filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json"), coverageLedger},
		{filepath.Join(paths.RuntimeDir, "workbench", "handoff-ledger.json"), handoffs},
	}
	if isV2 {
		writes = append(
			writes,
			struct {
				path  string
				value any
			}{submissionSnapshotPath, submissionValue},
			struct {
				path  string
				value any
			}{acceptanceReceiptPath(paths, packetID), receipt},
		)
	}
	for _, item := range writes {
		if err := writeJSONAtomic(item.path, item.value); err != nil {
			return AcceptPayload{}, err
		}
	}
	if err := writeJSONAtomic(queuePath, queue); err != nil {
		return AcceptPayload{}, err
	}
	// The queue is canonical. Commit it before derived Markdown so a crash can
	// never advertise acceptance that the machine-readable state has not made.
	// A retry of an accepted packet repairs these mirrors best-effort.
	if err := renderHumanState(paths, queue, coverageLedger); err != nil {
		return AcceptPayload{}, fmt.Errorf("packet %s accepted but render human state: %w", packetID, err)
	}

	return acceptedPayload(queue, packet), nil
}

func classifyWorkbenchProtocol(queue queueFile) (bool, error) {
	protocol := strings.TrimSpace(queue.Protocol)
	generationID := strings.TrimSpace(queue.GenerationID)
	scanSetPath := strings.TrimSpace(queue.ScanSetPath)
	if protocol == "" && generationID == "" && scanSetPath == "" {
		if queueHasV2Footprints(queue.Packets) {
			return false, fmt.Errorf("v2 workbench identity is missing; restore or recreate the scan workbench")
		}
		return false, nil
	}
	if protocol != workbenchProtocolV2 {
		return false, fmt.Errorf("scan workbench protocol %q is incompatible with %s", protocol, workbenchProtocolV2)
	}
	if generationID == "" || scanSetPath == "" {
		return false, fmt.Errorf("v2 scan workbench requires generation_id and scan_set_path")
	}
	return true, nil
}

func queueHasV2Footprints(packets []queuePacket) bool {
	for _, packet := range packets {
		if packet.ParentPacketID != "" || packet.WorkerID != "" || packet.AttemptID != "" ||
			packet.AttemptNumber != 0 || packet.CheckpointPath != "" || packet.CheckpointSequence != 0 ||
			len(packet.CompletedPaths) != 0 || packet.EstimatedTokens != 0 || packet.EstimatedBytes != 0 ||
			packet.EffectiveContextBudget != 0 || packet.Oversized {
			return true
		}
	}
	return false
}

func requireV2Workbench(queue queueFile) error {
	isV2, err := classifyWorkbenchProtocol(queue)
	if err != nil {
		return err
	}
	if !isV2 {
		return fmt.Errorf("resumable scan command requires a v2 workbench queue")
	}
	return nil
}

func validateScanSetPaths(root string, raw []string) ([]string, error) {
	seen := map[string]bool{}
	physical := []struct {
		path string
		info os.FileInfo
	}{}
	files := make([]string, 0, len(raw))
	for _, item := range raw {
		path := normalizePath(item)
		cleaned := filepath.ToSlash(filepath.Clean(filepath.FromSlash(path)))
		if cleaned != path {
			return nil, fmt.Errorf("scan set path %q is not in canonical repository form %q", item, cleaned)
		}
		if strings.ContainsAny(path, "`\r\n") {
			return nil, fmt.Errorf("scan set path %q contains task brief control characters", item)
		}
		if !scanartifacts.ValidConcreteRepositoryPath(path) {
			return nil, fmt.Errorf("scan set path %q is not a concrete repository file", item)
		}
		if path == ".specify" || strings.HasPrefix(path, ".specify/") {
			return nil, fmt.Errorf("scan set path %q enters project cognition control state", item)
		}
		if err := validateRepositoryFile(root, path); err != nil {
			return nil, err
		}
		info, err := os.Stat(filepath.Join(root, filepath.FromSlash(path)))
		if err != nil {
			return nil, err
		}
		for _, prior := range physical {
			if os.SameFile(prior.info, info) && prior.path != path {
				return nil, fmt.Errorf("scan set paths %q and %q refer to the same repository file", prior.path, path)
			}
		}
		if !seen[path] {
			seen[path] = true
			files = append(files, path)
			physical = append(physical, struct {
				path string
				info os.FileInfo
			}{path: path, info: info})
		}
	}
	sort.Strings(files)
	return files, nil
}

func validateRepositoryFile(root string, rel string) error {
	abs := filepath.Join(root, filepath.FromSlash(rel))
	info, err := os.Stat(abs)
	if err != nil {
		return fmt.Errorf("scan set path %s: %w", rel, err)
	}
	if !info.Mode().IsRegular() {
		return fmt.Errorf("scan set path %s is not a regular file", rel)
	}
	resolved, err := filepath.EvalSymlinks(abs)
	if err != nil {
		return fmt.Errorf("resolve scan set path %s: %w", rel, err)
	}
	inside, err := filepath.Rel(root, resolved)
	if err != nil || inside == ".." || strings.HasPrefix(inside, ".."+string(os.PathSeparator)) || filepath.IsAbs(inside) {
		return fmt.Errorf("scan set path %s resolves outside the repository", rel)
	}
	return nil
}

func validateWorkerResult(packet queuePacket, result workerResult, allAssignedPaths map[string]bool) error {
	if result.PacketID != packet.PacketID {
		return fmt.Errorf("worker result packet_id %q does not match %s", result.PacketID, packet.PacketID)
	}
	if result.Acceptance != "pass" {
		return fmt.Errorf("packet %s acceptance must be pass before scan-accept", packet.PacketID)
	}
	if strings.TrimSpace(result.Confidence) == "" {
		return fmt.Errorf("packet %s pass result requires confidence", packet.PacketID)
	}
	assigned := normalizedSet(packet.AssignedPaths)
	if !sameSet(assigned, normalizedSet(result.AssignedPaths)) {
		return fmt.Errorf("packet %s assigned_paths must exactly match the prepared packet", packet.PacketID)
	}
	if !sameSet(assigned, normalizedSet(result.PathsRead)) {
		return fmt.Errorf("packet %s paths_read must account for every assigned path", packet.PacketID)
	}
	if len(result.Ledger.Todo) > 0 || len(result.Ledger.Doing) > 0 || len(result.Ledger.Blocked) > 0 || len(result.Ledger.Overflow) > 0 ||
		!sameSet(assigned, normalizedSet(result.Ledger.Done)) {
		return fmt.Errorf("packet %s pass ledger must place every assigned path in done and leave no unresolved state", packet.PacketID)
	}

	evidenceByID := map[string]string{}
	for i, row := range result.Evidence {
		id := stringValue(row["id"])
		path := normalizePath(stringValue(row["source_path"]))
		if id == "" || path == "" {
			return fmt.Errorf("packet %s evidence[%d] requires id and source_path", packet.PacketID, i)
		}
		if !assigned[path] {
			return fmt.Errorf("packet %s evidence path %s is outside assigned_paths", packet.PacketID, path)
		}
		if _, duplicate := evidenceByID[id]; duplicate {
			return fmt.Errorf("packet %s repeats evidence id %s", packet.PacketID, id)
		}
		evidenceByID[id] = path
	}
	if len(evidenceByID) == 0 {
		return fmt.Errorf("packet %s requires packet-local evidence", packet.PacketID)
	}

	coverageByPath := map[string]bool{}
	for i, row := range result.Coverage {
		path := normalizePath(stringValue(row["path"]))
		outcome := stringValue(row["outcome"])
		if !assigned[path] {
			return fmt.Errorf("packet %s coverage[%d] path %s is outside assigned_paths", packet.PacketID, i, path)
		}
		if coverageByPath[path] {
			return fmt.Errorf("packet %s repeats coverage path %s", packet.PacketID, path)
		}
		if outcome != "read" && outcome != "deep_read" {
			return fmt.Errorf("packet %s pass coverage for %s must be read or deep_read", packet.PacketID, path)
		}
		refs := stringValues(row["evidence_ids"])
		if !referencesMatchingEvidencePath(refs, path, evidenceByID) {
			return fmt.Errorf("packet %s coverage for %s lacks matching packet-local evidence", packet.PacketID, path)
		}
		coverageByPath[path] = true
	}
	if !sameSet(assigned, coverageByPath) {
		return fmt.Errorf("packet %s coverage must account for every assigned path", packet.PacketID)
	}

	nodeIDs := map[string]bool{}
	nodePaths := map[string]bool{}
	for i, row := range result.Nodes {
		id := stringValue(row["id"])
		if id == "" || stringValue(row["type"]) == "" || stringValue(row["title"]) == "" {
			return fmt.Errorf("packet %s nodes[%d] requires id, type, and title", packet.PacketID, i)
		}
		if nodeIDs[id] {
			return fmt.Errorf("packet %s repeats node id %s", packet.PacketID, id)
		}
		nodeIDs[id] = true
		paths := normalizedSet(stringValues(row["paths"]))
		if len(paths) == 0 {
			return fmt.Errorf("packet %s node %s requires concrete paths for path_index", packet.PacketID, id)
		}
		for path := range paths {
			if !assigned[path] {
				return fmt.Errorf("packet %s node %s path %s is outside assigned_paths", packet.PacketID, id, path)
			}
			nodePaths[path] = true
		}
		if err := requireEvidenceRefs(packet.PacketID, "node "+id, stringValues(row["evidence_ids"]), evidenceByID); err != nil {
			return err
		}
	}
	if !sameSet(assigned, nodePaths) {
		return fmt.Errorf("packet %s nodes[].paths must cover every assigned path for path_index", packet.PacketID)
	}

	if err := validatePacketLocalGraphRows(
		packet.PacketID,
		result,
		nodeIDs,
		evidenceByID,
		assigned,
		allAssignedPaths,
	); err != nil {
		return err
	}
	return nil
}

func validatePacketLocalGraphRows(
	packetID string,
	result workerResult,
	nodeIDs map[string]bool,
	evidence map[string]string,
	assignedPaths map[string]bool,
	allAssignedPaths map[string]bool,
) error {
	seen := map[string]bool{}
	for i, row := range result.Edges {
		id := stringValue(row["id"])
		source := stringValue(row["source_id"])
		target := stringValue(row["target_id"])
		if id == "" || source == "" || target == "" {
			return fmt.Errorf("packet %s edges[%d] requires id, source_id, and target_id", packetID, i)
		}
		if seen[id] {
			return fmt.Errorf("packet %s repeats edge id %s", packetID, id)
		}
		seen[id] = true
		sourceValid := validEdgeEndpoint(source, nodeIDs, allAssignedPaths)
		targetValid := validEdgeEndpoint(target, nodeIDs, allAssignedPaths)
		if !sourceValid || !targetValid {
			return fmt.Errorf("packet %s edge %s endpoints must name a packet node or canonical scan-set path", packetID, id)
		}
		if !localEdgeEndpoint(source, nodeIDs, assignedPaths) && !localEdgeEndpoint(target, nodeIDs, assignedPaths) {
			return fmt.Errorf("packet %s edge %s must have at least one packet-local endpoint", packetID, id)
		}
		if err := requireEvidenceRefs(packetID, "edge "+id, stringValues(row["evidence_ids"]), evidence); err != nil {
			return err
		}
	}
	seen = map[string]bool{}
	for i, row := range result.Observations {
		id := stringValue(row["id"])
		if id == "" {
			return fmt.Errorf("packet %s observations[%d] requires id", packetID, i)
		}
		if seen[id] {
			return fmt.Errorf("packet %s repeats observation id %s", packetID, id)
		}
		seen[id] = true
		if err := requireEvidenceRefs(packetID, "observation "+id, stringValues(row["evidence_ids"]), evidence); err != nil {
			return err
		}
	}
	seen = map[string]bool{}
	for i, row := range result.Claims {
		id := stringValue(row["id"])
		nodeID := stringValue(row["node_id"])
		if id == "" || nodeID == "" {
			return fmt.Errorf("packet %s claims[%d] requires id and node_id", packetID, i)
		}
		if seen[id] {
			return fmt.Errorf("packet %s repeats claim id %s", packetID, id)
		}
		seen[id] = true
		if !nodeIDs[nodeID] {
			return fmt.Errorf("packet %s claim %s must stay within packet-local nodes", packetID, id)
		}
		refs := append(stringValues(row["supporting_evidence_ids"]), stringValues(row["contradicting_evidence_ids"])...)
		if err := requireEvidenceRefs(packetID, "claim "+id, refs, evidence); err != nil {
			return err
		}
	}
	return nil
}

func validEdgeEndpoint(endpoint string, nodeIDs map[string]bool, allAssignedPaths map[string]bool) bool {
	return nodeIDs[endpoint] || allAssignedPaths[normalizePath(endpoint)]
}

func localEdgeEndpoint(endpoint string, nodeIDs map[string]bool, assignedPaths map[string]bool) bool {
	return nodeIDs[endpoint] || assignedPaths[normalizePath(endpoint)]
}

func requireEvidenceRefs(packetID string, owner string, refs []string, evidence map[string]string) error {
	if len(refs) == 0 {
		return fmt.Errorf("packet %s %s requires packet-local evidence_ids", packetID, owner)
	}
	for _, ref := range refs {
		if _, ok := evidence[ref]; !ok {
			return fmt.Errorf("packet %s %s references evidence %s outside the packet", packetID, owner, ref)
		}
	}
	return nil
}

func referencesMatchingEvidencePath(refs []string, path string, evidence map[string]string) bool {
	for _, ref := range refs {
		if evidence[ref] == path {
			return true
		}
	}
	return false
}

func acceptAlreadyCommitted(
	paths rt.Paths,
	queue queueFile,
	packet queuePacket,
	submissionPath string,
	submissionValue any,
	submissionDigest string,
	submitted workerResult,
	incoming workerResult,
) (AcceptPayload, error) {
	canonicalPath := filepath.Join(paths.RuntimeDir, "workbench", "worker-results", packet.PacketID+".json")
	var canonical workerResult
	if err := readJSON(canonicalPath, &canonical); err != nil {
		return AcceptPayload{}, fmt.Errorf("accepted packet %s canonical result: %w", packet.PacketID, err)
	}
	if !sameJSON(canonical, incoming) {
		return AcceptPayload{}, fmt.Errorf("accepted packet %s result conflict", packet.PacketID)
	}
	if queue.Protocol == workbenchProtocolV2 {
		submissionSnapshotPath := acceptanceSubmissionSnapshotPath(paths, packet.PacketID)
		if err := ensureNormalizedJSONCompatible(submissionSnapshotPath, submissionValue); err != nil {
			return AcceptPayload{}, err
		}
		receipt, err := newAcceptanceReceipt(
			queue,
			packet,
			submissionPath,
			submissionDigest,
			submitted,
			canonical,
		)
		if err != nil {
			return AcceptPayload{}, err
		}
		receiptPath := acceptanceReceiptPath(paths, packet.PacketID)
		if err := ensureAcceptanceReceiptCompatible(receiptPath, receipt); err != nil {
			return AcceptPayload{}, err
		}
		if err := writeJSONAtomic(submissionSnapshotPath, submissionValue); err != nil {
			return AcceptPayload{}, err
		}
		if err := writeJSONAtomic(receiptPath, receipt); err != nil {
			return AcceptPayload{}, err
		}
	}

	// An accepted queue is canonical. Repair human-readable mirrors when
	// possible, but never turn an idempotent accepted retry into a failure.
	var ledger coverageLedgerFile
	if err := readJSON(filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json"), &ledger); err == nil {
		_ = renderHumanState(paths, queue, ledger)
	}
	return acceptedPayload(queue, packet), nil
}

func newAcceptanceReceipt(
	queue queueFile,
	packet queuePacket,
	submissionPath string,
	submissionDigest string,
	submitted workerResult,
	canonical workerResult,
) (acceptanceReceipt, error) {
	canonicalDigest, err := normalizedJSONDigest(canonical)
	if err != nil {
		return acceptanceReceipt{}, fmt.Errorf("hash packet %s canonical result: %w", packet.PacketID, err)
	}
	return acceptanceReceipt{
		Protocol:              acceptanceReceiptProtocolV1,
		WorkbenchGenerationID: queue.GenerationID,
		PacketID:              packet.PacketID,
		AttemptID:             submitted.AttemptID,
		Sequence:              submitted.Sequence,
		SourceResultPath:      submissionPath,
		SubmissionPath:        canonicalAcceptedSubmissionPath(packet.PacketID),
		SubmissionSHA256:      submissionDigest,
		CanonicalResultPath:   canonicalWorkerResultPath(packet.PacketID),
		CanonicalResultSHA256: canonicalDigest,
		AcceptedPathCount:     len(normalizedSet(canonical.AssignedPaths)),
	}, nil
}

func ensureAcceptanceReceiptCompatible(path string, incoming acceptanceReceipt) error {
	var existing acceptanceReceipt
	if err := readJSON(path, &existing); err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return nil
		}
		return fmt.Errorf("read acceptance receipt: %w", err)
	}
	if !sameJSON(existing, incoming) {
		return fmt.Errorf("packet %s acceptance receipt conflict", incoming.PacketID)
	}
	return nil
}

func acceptanceReceiptPath(paths rt.Paths, packetID string) string {
	return filepath.Join(paths.RuntimeDir, "workbench", "acceptance-receipts", packetID+".json")
}

func acceptanceSubmissionSnapshotPath(paths rt.Paths, packetID string) string {
	return filepath.Join(paths.RuntimeDir, "workbench", "accepted-submissions", packetID+".json")
}

func canonicalAcceptedSubmissionPath(packetID string) string {
	return ".specify/project-cognition/workbench/accepted-submissions/" + packetID + ".json"
}

func acceptanceSubmissionPath(paths rt.Paths, resultPath string) string {
	absoluteRoot, rootErr := filepath.Abs(paths.Root)
	absoluteResult, resultErr := filepath.Abs(resultPath)
	if rootErr != nil || resultErr != nil {
		return "external-result"
	}
	relative, err := filepath.Rel(absoluteRoot, absoluteResult)
	if err != nil || relative == ".." || strings.HasPrefix(relative, ".."+string(os.PathSeparator)) || filepath.IsAbs(relative) {
		return "external-result"
	}
	return filepath.ToSlash(relative)
}

func normalizedJSONDigest(value any) (string, error) {
	encoded, err := json.Marshal(value)
	if err != nil {
		return "", err
	}
	var normalized any
	if err := json.Unmarshal(encoded, &normalized); err != nil {
		return "", err
	}
	encoded, err = json.Marshal(normalized)
	if err != nil {
		return "", err
	}
	sum := sha256.Sum256(encoded)
	return fmt.Sprintf("%x", sum[:]), nil
}

func readNormalizedJSONFile(path string) (any, string, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, "", err
	}
	var value any
	if err := json.Unmarshal(data, &value); err != nil {
		return nil, "", err
	}
	digest, err := normalizedJSONDigest(value)
	if err != nil {
		return nil, "", err
	}
	return value, digest, nil
}

func ensureNormalizedJSONCompatible(path string, incoming any) error {
	_, existingDigest, err := readNormalizedJSONFile(path)
	if err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return nil
		}
		return err
	}
	incomingDigest, err := normalizedJSONDigest(incoming)
	if err != nil {
		return err
	}
	if existingDigest != incomingDigest {
		return fmt.Errorf("accepted submission snapshot conflict at %s", path)
	}
	return nil
}

func acceptedPayload(queue queueFile, packet queuePacket) AcceptPayload {
	pending := 0
	for _, row := range queue.Packets {
		if row.State != "accepted" {
			pending++
		}
	}
	nextAction := "validate_scan"
	if pending > 0 {
		nextAction = "dispatch_remaining_packets"
	}
	return AcceptPayload{
		Status:            "accepted",
		PacketID:          packet.PacketID,
		AcceptedPathCount: len(packet.AssignedPaths),
		PendingPackets:    pending,
		WorkerResultPath:  canonicalWorkerResultPath(packet.PacketID),
		CompletionAllowed: false,
		CompletionGate:    "validate_scan",
		NextAction:        nextAction,
	}
}

func ensureEvidenceCompatible(paths rt.Paths, packetID string, incoming []map[string]any) error {
	incomingByID := map[string]map[string]any{}
	for _, row := range incoming {
		incomingByID[stringValue(row["id"])] = row
	}
	evidenceDir := filepath.Join(paths.RuntimeDir, "evidence")
	entries, err := os.ReadDir(evidenceDir)
	if err != nil {
		return err
	}
	currentName := packetID + ".json"
	for _, entry := range entries {
		if entry.IsDir() || filepath.Ext(entry.Name()) != ".json" {
			continue
		}
		var payload map[string][]map[string]any
		if err := readJSON(filepath.Join(evidenceDir, entry.Name()), &payload); err != nil {
			return err
		}
		seen := map[string]map[string]any{}
		for _, row := range payload["rows"] {
			id := stringValue(row["id"])
			incomingRow, belongsToPacket := incomingByID[id]
			if entry.Name() != currentName {
				if belongsToPacket {
					return fmt.Errorf("evidence %s conflict: already belongs to %s", id, entry.Name())
				}
				continue
			}
			if !belongsToPacket || !sameJSON(row, incomingRow) {
				return fmt.Errorf("evidence %s conflict in %s", id, currentName)
			}
			if previous, duplicate := seen[id]; duplicate && !sameJSON(previous, row) {
				return fmt.Errorf("evidence %s has conflicting duplicate rows", id)
			}
			seen[id] = row
		}
	}
	return nil
}

func ensureWorkerResultCompatible(path string, incoming workerResult) error {
	var existing workerResult
	if err := readJSON(path, &existing); err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return nil
		}
		return err
	}
	if !sameJSON(existing, incoming) {
		return fmt.Errorf("worker result conflict for %s", filepath.Base(path))
	}
	return nil
}

func mergeObjectRows(existing []map[string]any, incoming []map[string]any, key string, label string) ([]map[string]any, error) {
	merged := make([]map[string]any, 0, len(existing)+len(incoming))
	index := map[string]int{}
	for _, row := range existing {
		identity := stringValue(row[key])
		if identity == "" {
			return nil, fmt.Errorf("existing %s row has no %s", label, key)
		}
		if position, duplicate := index[identity]; duplicate {
			if !sameJSON(merged[position], row) {
				return nil, fmt.Errorf("%s %s conflict in existing rows", label, identity)
			}
			continue
		}
		index[identity] = len(merged)
		merged = append(merged, row)
	}
	for _, row := range incoming {
		identity := stringValue(row[key])
		if position, exists := index[identity]; exists {
			if !sameJSON(merged[position], row) {
				return nil, fmt.Errorf("%s %s conflict with partially merged result", label, identity)
			}
			continue
		}
		index[identity] = len(merged)
		merged = append(merged, row)
	}
	sortObjectRows(merged, key)
	return merged, nil
}

func sameJSON(left any, right any) bool {
	leftJSON, leftErr := json.Marshal(left)
	rightJSON, rightErr := json.Marshal(right)
	return leftErr == nil && rightErr == nil && bytes.Equal(leftJSON, rightJSON)
}

func requireWorkbenchReplacementAllowed(paths rt.Paths, force bool) error {
	workbench := filepath.Join(paths.RuntimeDir, "workbench")
	if _, err := os.Lstat(workbench); err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return nil
		}
		return fmt.Errorf("inspect existing scan workbench: %w", err)
	}
	if !force {
		return fmt.Errorf("scan workbench already exists; rerun scan-prepare with --force to discard it")
	}
	return nil
}

func validateRuntimeControlDir(paths rt.Paths) error {
	root, err := filepath.Abs(paths.Root)
	if err != nil {
		return fmt.Errorf("resolve repository root: %w", err)
	}
	runtimeDir, err := filepath.Abs(paths.RuntimeDir)
	if err != nil {
		return fmt.Errorf("resolve project cognition runtime directory: %w", err)
	}
	rel, err := filepath.Rel(root, runtimeDir)
	if err != nil || rel == ".." || strings.HasPrefix(rel, ".."+string(os.PathSeparator)) || filepath.IsAbs(rel) {
		return fmt.Errorf("project cognition runtime directory is outside the repository")
	}

	current := root
	deepestExisting := root
	for _, component := range strings.Split(rel, string(os.PathSeparator)) {
		if component == "" || component == "." {
			continue
		}
		current = filepath.Join(current, component)
		info, statErr := os.Lstat(current)
		if errors.Is(statErr, os.ErrNotExist) {
			break
		}
		if statErr != nil {
			return fmt.Errorf("inspect project cognition control path %s: %w", current, statErr)
		}
		if info.Mode()&os.ModeSymlink != 0 {
			return fmt.Errorf("project cognition control path must not contain symbolic links: %s", current)
		}
		deepestExisting = current
	}

	resolvedRoot, err := filepath.EvalSymlinks(root)
	if err != nil {
		return fmt.Errorf("resolve repository root links: %w", err)
	}
	resolvedExisting, err := filepath.EvalSymlinks(deepestExisting)
	if err != nil {
		return fmt.Errorf("resolve project cognition control path links: %w", err)
	}
	existingRel, err := filepath.Rel(resolvedRoot, resolvedExisting)
	if err != nil || existingRel == ".." || strings.HasPrefix(existingRel, ".."+string(os.PathSeparator)) || filepath.IsAbs(existingRel) {
		return fmt.Errorf("project cognition control path resolves outside the repository")
	}
	if _, err := os.Lstat(runtimeDir); err == nil {
		resolvedRuntime, resolveErr := filepath.EvalSymlinks(runtimeDir)
		if resolveErr != nil {
			return fmt.Errorf("resolve project cognition runtime links: %w", resolveErr)
		}
		resolvedRel, relErr := filepath.Rel(resolvedRoot, resolvedRuntime)
		if relErr != nil || resolvedRel == ".." || strings.HasPrefix(resolvedRel, ".."+string(os.PathSeparator)) || filepath.IsAbs(resolvedRel) {
			return fmt.Errorf("project cognition runtime directory resolves outside the repository")
		}
	} else if !errors.Is(err, os.ErrNotExist) {
		return fmt.Errorf("inspect project cognition runtime directory: %w", err)
	}
	if _, err := os.Lstat(runtimeDir); err == nil {
		if err := filepath.WalkDir(runtimeDir, func(path string, entry os.DirEntry, walkErr error) error {
			if walkErr != nil {
				return walkErr
			}
			if entry.Type()&os.ModeSymlink != 0 {
				return fmt.Errorf("project cognition control path must not contain symbolic links: %s", path)
			}
			return nil
		}); err != nil {
			return err
		}
	}
	return nil
}

func acquireWorkbenchLock(paths rt.Paths) (func(), error) {
	lockPath := filepath.Join(paths.RuntimeDir, ".scan-workbench.lock")
	ownerPath := filepath.Join(lockPath, "owner")
	ownerToken := fmt.Sprintf("%d-%d", os.Getpid(), time.Now().UnixNano())
	if err := os.MkdirAll(paths.RuntimeDir, 0o755); err != nil {
		return nil, fmt.Errorf("create project cognition runtime directory: %w", err)
	}
	deadline := time.Now().Add(workbenchLockWait)
	for {
		if err := os.Mkdir(lockPath, 0o700); err == nil {
			if err := os.WriteFile(ownerPath, []byte(ownerToken), 0o600); err != nil {
				_ = os.RemoveAll(lockPath)
				return nil, fmt.Errorf("record scan workbench lock owner: %w", err)
			}
			stop := make(chan struct{})
			done := make(chan struct{})
			go func() {
				defer close(done)
				ticker := time.NewTicker(workbenchLockHeartbeat)
				defer ticker.Stop()
				for {
					select {
					case <-ticker.C:
						if !lockOwnedBy(ownerPath, ownerToken) {
							return
						}
						now := time.Now()
						_ = os.Chtimes(lockPath, now, now)
					case <-stop:
						return
					}
				}
			}()
			var releaseOnce sync.Once
			return func() {
				releaseOnce.Do(func() {
					close(stop)
					<-done
					if lockOwnedBy(ownerPath, ownerToken) {
						_ = os.RemoveAll(lockPath)
					}
				})
			}, nil
		} else if !errors.Is(err, os.ErrExist) {
			return nil, fmt.Errorf("acquire scan workbench lock: %w", err)
		}

		info, err := os.Lstat(lockPath)
		if err == nil && info.IsDir() && time.Since(info.ModTime()) > workbenchLockStaleAfter {
			if removeErr := os.RemoveAll(lockPath); removeErr == nil || errors.Is(removeErr, os.ErrNotExist) {
				continue
			}
		}
		if time.Now().After(deadline) {
			return nil, fmt.Errorf("timed out waiting for another scan workbench operation")
		}
		time.Sleep(workbenchLockRetryInterval)
	}
}

func lockOwnedBy(ownerPath, ownerToken string) bool {
	data, err := os.ReadFile(ownerPath)
	return err == nil && string(data) == ownerToken
}

func resetWorkbench(paths rt.Paths) error {
	if err := os.Remove(filepath.Join(paths.RuntimeDir, "scan-receipt.json")); err != nil && !errors.Is(err, os.ErrNotExist) {
		return fmt.Errorf("remove stale scan receipt: %w", err)
	}
	for _, path := range []string{
		filepath.Join(paths.RuntimeDir, "evidence"),
		filepath.Join(paths.RuntimeDir, "provisional"),
		filepath.Join(paths.RuntimeDir, "workbench"),
	} {
		if err := os.RemoveAll(path); err != nil {
			return fmt.Errorf("reset scan state %s: %w", path, err)
		}
	}
	for _, path := range []string{
		filepath.Join(paths.RuntimeDir, "evidence"),
		filepath.Join(paths.RuntimeDir, "provisional"),
		filepath.Join(paths.RuntimeDir, "workbench", "scan-packets"),
		filepath.Join(paths.RuntimeDir, "workbench", "worker-results"),
		filepath.Join(paths.RuntimeDir, "workbench", "acceptance-receipts"),
		filepath.Join(paths.RuntimeDir, "workbench", "accepted-submissions"),
		filepath.Join(paths.RuntimeDir, "workbench", "pending-results"),
		filepath.Join(paths.RuntimeDir, "workbench", "checkpoints"),
	} {
		if err := os.MkdirAll(path, 0o755); err != nil {
			return fmt.Errorf("create scan state %s: %w", path, err)
		}
	}
	return nil
}

func writePreparedStatus(paths rt.Paths) error {
	status, err := rt.ReadStatus(paths)
	if errors.Is(err, rt.ErrUnsupportedLegacy) {
		return fmt.Errorf("unsupported legacy status must be removed or repaired before scan-prepare")
	}
	if err != nil {
		return err
	}
	status.Status = "scanning"
	status.Freshness = rt.StaleFreshness
	status.Readiness = rt.NeedsRebuildReadiness
	status.RecommendedNextAction = "complete_scan_packets"
	status.GraphReady = false
	status.BaselineKind = rt.BaselineKindBrownfieldFull
	return rt.WriteStatus(paths, status)
}

func repositoryUniverse(classifications []pathClassification) map[string]any {
	candidates := make([]map[string]any, 0, len(classifications))
	includedPaths := make([]string, 0, len(classifications))
	excludedPaths := []string{}
	ambiguousPaths := []string{}
	dispositions := map[string]string{}
	criticality := map[string]string{}
	valueTier := map[string]string{}
	scanDecision := map[string]string{}
	pathKinds := map[string]string{}
	reasons := map[string]string{}
	decisionSource := map[string]string{}
	for _, classification := range classifications {
		path := classification.Path
		candidates = append(candidates, map[string]any{
			"path":                   path,
			"path_kind":              classification.PathKind,
			"extension":              classification.Extension,
			"size_bytes":             classification.SizeBytes,
			"directory_family":       classification.DirectoryFamily,
			"git_tracked":            classification.GitTracked,
			"ignored_by_cognition":   false,
			"matched_ignore_rule":    nil,
			"value_tier":             classification.ValueTier,
			"scan_decision":          classification.ScanDecision,
			"disposition":            classification.Disposition,
			"criticality":            classification.Criticality,
			"classification_reasons": classification.ClassificationReason,
			"decision_source":        classification.DecisionSource,
		})
		switch classification.Disposition {
		case "excluded":
			excludedPaths = append(excludedPaths, path)
		case "blocked":
			ambiguousPaths = append(ambiguousPaths, path)
		default:
			includedPaths = append(includedPaths, path)
		}
		dispositions[path] = classification.Disposition
		criticality[path] = classification.Criticality
		valueTier[path] = classification.ValueTier
		scanDecision[path] = classification.ScanDecision
		pathKinds[path] = classification.PathKind
		reasons[path] = classification.ClassificationReason
		decisionSource[path] = classification.DecisionSource
	}
	return map[string]any{
		"schema_version":         2,
		"candidate_universe":     candidates,
		"included_paths":         includedPaths,
		"excluded_paths":         excludedPaths,
		"ambiguous_paths":        ambiguousPaths,
		"dispositions":           dispositions,
		"criticality":            criticality,
		"value_tier":             valueTier,
		"scan_decision":          scanDecision,
		"path_kind":              pathKinds,
		"classification_reasons": reasons,
		"decision_source":        decisionSource,
	}
}

func scanTargets(classifications []pathClassification) map[string]any {
	selectedPaths := []string{}
	sampledPaths := []string{}
	inventoryOnlyPaths := []string{}
	excludedPaths := []string{}
	blockedPaths := []string{}
	valueTier := map[string]string{}
	decision := map[string]string{}
	dispositions := map[string]string{}
	criticality := map[string]string{}
	reasons := map[string]string{}
	for _, classification := range classifications {
		path := classification.Path
		switch classification.ScanDecision {
		case "scan":
			selectedPaths = append(selectedPaths, path)
		case "sample":
			selectedPaths = append(selectedPaths, path)
			sampledPaths = append(sampledPaths, path)
		case "inventory_only":
			inventoryOnlyPaths = append(inventoryOnlyPaths, path)
		case "exclude":
			excludedPaths = append(excludedPaths, path)
		case "blocked":
			blockedPaths = append(blockedPaths, path)
		}
		valueTier[path] = classification.ValueTier
		decision[path] = classification.ScanDecision
		dispositions[path] = classification.Disposition
		criticality[path] = classification.Criticality
		reasons[path] = classification.ClassificationReason
	}
	return map[string]any{
		"schema_version":         2,
		"selection_policy":       "value_weighted",
		"selected_paths":         selectedPaths,
		"sampled_paths":          sampledPaths,
		"inventory_only_paths":   inventoryOnlyPaths,
		"excluded_paths":         excludedPaths,
		"blocked_paths":          blockedPaths,
		"value_tier":             valueTier,
		"scan_decision":          decision,
		"disposition":            dispositions,
		"criticality":            criticality,
		"classification_reasons": reasons,
	}
}

func classifyRepositoryPaths(root string, files []string) ([]pathClassification, error) {
	tracked := gitTrackedPaths(root)
	classifications := make([]pathClassification, 0, len(files))
	for _, path := range files {
		info, err := os.Stat(filepath.Join(root, filepath.FromSlash(path)))
		if err != nil {
			return nil, fmt.Errorf("classify scan path %s: %w", path, err)
		}
		kind := pathKind(path)
		tier, reason := classifyValueTier(path, kind)
		disposition, decision, criticality := classificationPolicy(tier)
		classifications = append(classifications, pathClassification{
			Path:                 path,
			PathKind:             kind,
			Extension:            strings.TrimPrefix(strings.ToLower(filepath.Ext(path)), "."),
			SizeBytes:            info.Size(),
			DirectoryFamily:      directoryFamily(path),
			GitTracked:           tracked[path],
			ValueTier:            tier,
			ScanDecision:         decision,
			Disposition:          disposition,
			Criticality:          criticality,
			ClassificationReason: reason,
			DecisionSource:       "specify-runtime cognition scan-prepare",
		})
	}
	return classifications, nil
}

func scanPacketPaths(classifications []pathClassification) []string {
	paths := make([]string, 0, len(classifications))
	for _, classification := range classifications {
		if classification.ScanDecision == "scan" || classification.ScanDecision == "sample" {
			paths = append(paths, classification.Path)
		}
	}
	return paths
}

func classifyValueTier(path string, kind string) (string, string) {
	lower := strings.ToLower(filepath.ToSlash(path))
	base := strings.ToLower(filepath.Base(lower))
	switch kind {
	case "vendor", "build_output", "generated", "asset", "lockfile":
		return "P3", "generated_vendor_asset_or_low_signal"
	case "test":
		if highRiskValidationPath(lower) {
			return "P1", "critical_integration_or_security_verification"
		}
		return "P2", "test_or_verification_example"
	case "doc":
		if !strings.Contains(lower, "/") && base == "readme.md" {
			return "P1", "root_behavioral_documentation"
		}
		return "P2", "secondary_documentation_or_usage"
	case "config", "script", "template":
		return "P1", "configuration_build_release_or_template"
	}
	if highValueSourcePath(lower, base) {
		return "P0", "runtime_entrypoint_or_critical_surface"
	}
	return "P1", "project_source_or_runtime_support"
}

func classificationPolicy(valueTier string) (string, string, string) {
	switch valueTier {
	case "P0":
		return "deep_read", "scan", "critical"
	case "P1":
		return "deep_read", "scan", "important"
	case "P2":
		return "sampled", "sample", "low_risk"
	default:
		return "inventory_only", "inventory_only", "low_risk"
	}
}

func highRiskValidationPath(path string) bool {
	return matchesPathSegment(path, "auth", "security", "payment", "payments", "integration", "e2e", "contract", "smoke") ||
		strings.Contains(path, "_integration_test.") ||
		strings.Contains(path, ".integration.") ||
		strings.Contains(path, ".e2e.") ||
		strings.Contains(path, ".contract.")
}

func highValueSourcePath(lower string, base string) bool {
	if matchesPathSegment(lower, "cmd", "api", "routes", "router", "controllers", "handlers", "auth", "security", "payment", "payments", "services", "workflow", "workflows", "state", "states") {
		return true
	}
	name := strings.TrimSuffix(base, filepath.Ext(base))
	switch name {
	case "main", "index", "app", "server", "router", "routes", "service":
		return true
	default:
		return false
	}
}

func matchesPathSegment(path string, values ...string) bool {
	segments := strings.Split(strings.Trim(path, "/"), "/")
	for _, segment := range segments {
		for _, value := range values {
			if segment == value {
				return true
			}
		}
	}
	return false
}

func directoryFamily(path string) string {
	normalized := strings.Trim(filepath.ToSlash(path), "/")
	if normalized == "" {
		return "."
	}
	if index := strings.Index(normalized, "/"); index >= 0 {
		return normalized[:index]
	}
	return "."
}

func gitTrackedPaths(root string) map[string]bool {
	tracked := map[string]bool{}
	cmd := exec.Command("git", "ls-files", "-z", "--")
	cmd.Dir = root
	data, err := cmd.Output()
	if err != nil {
		return tracked
	}
	for _, path := range strings.Split(string(data), "\x00") {
		path = filepath.ToSlash(strings.TrimSpace(path))
		if path != "" {
			tracked[path] = true
		}
	}
	return tracked
}

func renderPacket(packetID string, paths []string) string {
	var builder strings.Builder
	builder.WriteString("---\npacket_id: ")
	builder.WriteString(packetID)
	builder.WriteString("\nmode: read_only\nresult_submission_path: .specify/project-cognition/workbench/pending-results/")
	builder.WriteString(packetID)
	builder.WriteString(".json\nresult_handoff_path: ")
	builder.WriteString(canonicalWorkerResultPath(packetID))
	builder.WriteString("\n---\n\n# MapScanPacket\n\nRead only these concrete assigned paths:\n")
	for _, path := range paths {
		builder.WriteString("- `")
		builder.WriteString(path)
		builder.WriteString("`\n")
	}
	builder.WriteString("\nReturn one packet-local JSON object using this exact shape (repeat rows as needed):\n\n")
	skeleton := workerResultSkeleton(packetID, "<active-attempt-id>", paths)
	skeletonJSON, _ := json.MarshalIndent(skeleton, "", "  ")
	builder.WriteString("```json\n")
	builder.Write(skeletonJSON)
	builder.WriteString("\n```\n\n")
	builder.WriteString("Treat this as a cumulative checkpoint skeleton. Move only concretely completed paths from ledger.todo to ledger.done, add matching paths_read, coverage, evidence, and nodes[].paths, increment sequence, and keep acceptance=partial even when every assigned path is complete; scan-accept derives pass only after runtime validation. Submit checkpoints through specify-runtime cognition scan-checkpoint; finish with scan-accept or yield remaining work with scan-yield. For a relationship proven by an assigned file but targeting another scan packet, one edge endpoint may be that other file's concrete repository path; at least one endpoint must remain packet-local. Do not read an unassigned target merely to strengthen the edge. Do not write product files or canonical cognition ledgers.\n")
	return builder.String()
}

func renderHumanState(paths rt.Paths, queue queueFile, ledger coverageLedgerFile) error {
	accepted := 0
	for _, row := range queue.Packets {
		if row.State == "accepted" {
			accepted++
		}
	}
	mapState := fmt.Sprintf("# Project Cognition Scan State\n\n- packets: %d\n- accepted: %d\n- pending: %d\n", len(queue.Packets), accepted, len(queue.Packets)-accepted)
	if err := writeTextAtomic(filepath.Join(paths.RuntimeDir, "workbench", "map-state.md"), mapState); err != nil {
		return err
	}
	mapScan := fmt.Sprintf("# Project Cognition Scan\n\nDeterministic packet scan with %d packets.\n", len(queue.Packets))
	if err := writeTextAtomic(filepath.Join(paths.RuntimeDir, "workbench", "map-scan.md"), mapScan); err != nil {
		return err
	}
	coverage := fmt.Sprintf("# Coverage Ledger\n\n- covered paths: %d\n- open gaps: %d\n", len(ledger.Rows), len(ledger.OpenGaps))
	return writeTextAtomic(filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.md"), coverage)
}

func pathKind(path string) string {
	lower := strings.ToLower(filepath.ToSlash(path))
	base := strings.ToLower(filepath.Base(path))
	switch {
	case matchesPathSegment(lower, "vendor", "third_party", "node_modules"):
		return "vendor"
	case matchesPathSegment(lower, "dist", "coverage", ".next", ".nuxt", ".output", "__pycache__"):
		return "build_output"
	case matchesPathSegment(lower, "generated", "gen") || strings.Contains(base, ".generated.") || strings.HasPrefix(base, "generated_"):
		return "generated"
	case isLockfile(base):
		return "lockfile"
	case isAssetFile(lower):
		return "asset"
	case matchesPathSegment(lower, "templates", "template") || strings.HasSuffix(lower, ".tmpl") || strings.HasSuffix(lower, ".tpl"):
		return "template"
	case strings.Contains(lower, "/test/") || strings.Contains(lower, "/tests/") || strings.Contains(base, "test"):
		return "test"
	case base == "readme.md" || strings.HasSuffix(lower, ".md"):
		return "doc"
	case base == "go.mod" || base == "package.json" || strings.HasSuffix(lower, ".toml") || strings.HasSuffix(lower, ".yaml") || strings.HasSuffix(lower, ".yml"):
		return "config"
	case strings.HasSuffix(lower, ".sh") || strings.HasSuffix(lower, ".ps1"):
		return "script"
	default:
		return "source"
	}
}

func isLockfile(base string) bool {
	switch base {
	case "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "go.sum", "cargo.lock", "poetry.lock", "uv.lock", "composer.lock", "gemfile.lock":
		return true
	default:
		return false
	}
}

func isAssetFile(path string) bool {
	switch strings.ToLower(filepath.Ext(path)) {
	case ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".svg", ".woff", ".woff2", ".ttf", ".otf", ".mp3", ".mp4", ".mov", ".pdf":
		return true
	default:
		return false
	}
}

func resolveRepositoryFile(root string, raw string) (string, string, error) {
	path := filepath.Clean(filepath.FromSlash(raw))
	if !filepath.IsAbs(path) {
		path = filepath.Join(root, path)
	}
	abs, err := filepath.Abs(path)
	if err != nil {
		return "", "", err
	}
	rel, err := filepath.Rel(root, abs)
	if err != nil || rel == ".." || strings.HasPrefix(rel, ".."+string(os.PathSeparator)) || filepath.IsAbs(rel) {
		return "", "", fmt.Errorf("path is outside repository")
	}
	return abs, filepath.ToSlash(rel), nil
}

func readJSON(path string, out any) error {
	data, err := os.ReadFile(path)
	if err != nil {
		return err
	}
	if err := json.Unmarshal(data, out); err != nil {
		return fmt.Errorf("parse %s: %w", path, err)
	}
	return nil
}

func writeJSONAtomic(path string, value any) error {
	data, err := json.MarshalIndent(value, "", "  ")
	if err != nil {
		return err
	}
	return writeBytesAtomic(path, append(data, '\n'))
}

func writeTextAtomic(path string, value string) error {
	return writeBytesAtomic(path, []byte(value))
}

func writeBytesAtomic(path string, data []byte) error {
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	tmp, err := os.CreateTemp(filepath.Dir(path), ".scan-workbench-*.tmp")
	if err != nil {
		return err
	}
	tmpPath := tmp.Name()
	defer os.Remove(tmpPath)
	if _, err := tmp.Write(data); err != nil {
		_ = tmp.Close()
		return err
	}
	if err := tmp.Close(); err != nil {
		return err
	}
	if err := os.Chmod(tmpPath, 0o644); err != nil {
		return err
	}
	return os.Rename(tmpPath, path)
}

func canonicalWorkerResultPath(packetID string) string {
	return ".specify/project-cognition/workbench/worker-results/" + packetID + ".json"
}

func normalizePath(value string) string {
	return filepath.ToSlash(strings.TrimSpace(value))
}

func normalizedSet(values []string) map[string]bool {
	set := map[string]bool{}
	for _, value := range values {
		path := normalizePath(value)
		if path != "" {
			set[path] = true
		}
	}
	return set
}

func sameSet(left map[string]bool, right map[string]bool) bool {
	if len(left) != len(right) {
		return false
	}
	for value := range left {
		if !right[value] {
			return false
		}
	}
	return true
}

func stringValue(value any) string {
	text, _ := value.(string)
	return strings.TrimSpace(text)
}

func stringValues(value any) []string {
	values := []string{}
	switch typed := value.(type) {
	case []any:
		for _, item := range typed {
			if text := stringValue(item); text != "" {
				values = append(values, text)
			}
		}
	case []string:
		for _, item := range typed {
			if text := strings.TrimSpace(item); text != "" {
				values = append(values, text)
			}
		}
	}
	return values
}

func cloneObject(value map[string]any) map[string]any {
	clone := make(map[string]any, len(value))
	for key, item := range value {
		clone[key] = item
	}
	return clone
}

func sortObjectRows(rows []map[string]any, key string) {
	sort.SliceStable(rows, func(i int, j int) bool {
		return stringValue(rows[i][key]) < stringValue(rows[j][key])
	})
}
