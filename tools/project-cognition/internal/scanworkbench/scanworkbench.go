package scanworkbench

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"sync"
	"time"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/scanartifacts"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/scanset"
)

const defaultPacketSize = 25

const (
	workbenchLockRetryInterval = 25 * time.Millisecond
	workbenchLockWait          = 30 * time.Second
	workbenchLockHeartbeat     = 20 * time.Second
	workbenchLockStaleAfter    = 2 * time.Minute
)

var packetIDPattern = regexp.MustCompile(`^[A-Za-z0-9][A-Za-z0-9._-]*$`)

type PrepareInput struct {
	ScanSetPath string
	PacketSize  int
	Force       bool
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
	ResultPath string
}

type AcceptPayload struct {
	Status            string `json:"status"`
	PacketID          string `json:"packet_id"`
	AcceptedPathCount int    `json:"accepted_path_count"`
	PendingPackets    int    `json:"pending_packets"`
	WorkerResultPath  string `json:"worker_result_path"`
	NextAction        string `json:"next_action"`
}

type scanSetFile struct {
	Files []string `json:"files"`
}

type queueFile struct {
	Packets []queuePacket `json:"packets"`
}

type queuePacket struct {
	PacketID          string   `json:"packet_id"`
	State             string   `json:"state"`
	AssignedPaths     []string `json:"assigned_paths"`
	ResultHandoffPath string   `json:"result_handoff_path"`
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
	PacketID      string           `json:"packet_id"`
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

// Prepare converts the runtime-produced scan set into a deterministic,
// exhaustive packet queue. Every path is concrete and assigned exactly once.
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
	packetSize := input.PacketSize
	if packetSize == 0 {
		packetSize = defaultPacketSize
	}
	if packetSize < 1 || packetSize > 150 {
		return PreparePayload{}, fmt.Errorf("packet size must be between 1 and 150")
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

	if err := resetWorkbench(paths); err != nil {
		return PreparePayload{}, err
	}
	if err := writePreparedStatus(paths); err != nil {
		return PreparePayload{}, err
	}

	packetIDs := make([]string, 0, (len(files)+packetSize-1)/packetSize)
	queue := queueFile{Packets: []queuePacket{}}
	handoffs := handoffFile{Events: []map[string]any{}}
	for start := 0; start < len(files); start += packetSize {
		end := start + packetSize
		if end > len(files) {
			end = len(files)
		}
		packetID := fmt.Sprintf("lane-%03d", len(packetIDs)+1)
		assigned := append([]string{}, files[start:end]...)
		resultPath := canonicalWorkerResultPath(packetID)
		packetIDs = append(packetIDs, packetID)
		queue.Packets = append(queue.Packets, queuePacket{
			PacketID:          packetID,
			State:             "pending",
			AssignedPaths:     assigned,
			ResultHandoffPath: resultPath,
		})
		handoffs.Events = append(handoffs.Events, map[string]any{
			"event_id":            "dispatch-" + packetID,
			"packet_id":           packetID,
			"event_type":          "dispatched",
			"result_handoff_path": resultPath,
		})
		if err := writeTextAtomic(
			filepath.Join(paths.RuntimeDir, "workbench", "scan-packets", packetID+".md"),
			renderPacket(packetID, assigned),
		); err != nil {
			return PreparePayload{}, err
		}
	}

	workbench := filepath.Join(paths.RuntimeDir, "workbench")
	writes := []struct {
		path  string
		value any
	}{
		{filepath.Join(workbench, "repository-universe.json"), repositoryUniverse(files)},
		{filepath.Join(workbench, "scan-targets.json"), scanTargets(files)},
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
	if packet.State != "pending" && packet.State != "accepted" {
		return AcceptPayload{}, fmt.Errorf("packet %s state %s is not acceptable", packetID, packet.State)
	}

	resultPath := strings.TrimSpace(input.ResultPath)
	if resultPath == "" {
		resultPath = filepath.Join(paths.RuntimeDir, "workbench", "pending-results", packetID+".json")
	} else if !filepath.IsAbs(resultPath) {
		resultPath = filepath.Join(paths.Root, filepath.FromSlash(resultPath))
	}
	var result workerResult
	if err := readJSON(resultPath, &result); err != nil {
		return AcceptPayload{}, fmt.Errorf("read worker result: %w", err)
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
	if packet.State == "accepted" {
		return acceptAlreadyCommitted(paths, queue, packet, result)
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

	var err error
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

func validateScanSetPaths(root string, raw []string) ([]string, error) {
	seen := map[string]bool{}
	files := make([]string, 0, len(raw))
	for _, item := range raw {
		path := normalizePath(item)
		if !scanartifacts.ValidConcreteRepositoryPath(path) {
			return nil, fmt.Errorf("scan set path %q is not a concrete repository file", item)
		}
		if path == ".specify" || strings.HasPrefix(path, ".specify/") {
			return nil, fmt.Errorf("scan set path %q enters project cognition control state", item)
		}
		if err := validateRepositoryFile(root, path); err != nil {
			return nil, err
		}
		if !seen[path] {
			seen[path] = true
			files = append(files, path)
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

func acceptAlreadyCommitted(paths rt.Paths, queue queueFile, packet queuePacket, incoming workerResult) (AcceptPayload, error) {
	canonicalPath := filepath.Join(paths.RuntimeDir, "workbench", "worker-results", packet.PacketID+".json")
	var canonical workerResult
	if err := readJSON(canonicalPath, &canonical); err != nil {
		return AcceptPayload{}, fmt.Errorf("accepted packet %s canonical result: %w", packet.PacketID, err)
	}
	if !sameJSON(canonical, incoming) {
		return AcceptPayload{}, fmt.Errorf("accepted packet %s result conflict", packet.PacketID)
	}

	// An accepted queue is canonical. Repair human-readable mirrors when
	// possible, but never turn an idempotent accepted retry into a failure.
	var ledger coverageLedgerFile
	if err := readJSON(filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json"), &ledger); err == nil {
		_ = renderHumanState(paths, queue, ledger)
	}
	return acceptedPayload(queue, packet), nil
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
		filepath.Join(paths.RuntimeDir, "workbench", "pending-results"),
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

func repositoryUniverse(files []string) map[string]any {
	candidates := make([]map[string]any, 0, len(files))
	dispositions := map[string]string{}
	criticality := map[string]string{}
	reasons := map[string]string{}
	decisionSource := map[string]string{}
	for _, path := range files {
		candidates = append(candidates, map[string]any{
			"path":          path,
			"disposition":   "deep_read",
			"criticality":   "important",
			"value_tier":    "P1",
			"scan_decision": "scan",
			"path_kind":     pathKind(path),
		})
		dispositions[path] = "deep_read"
		criticality[path] = "important"
		reasons[path] = "canonical_scan_set"
		decisionSource[path] = "project-cognition scan-prepare"
	}
	return map[string]any{
		"schema_version":         1,
		"candidate_universe":     candidates,
		"included_paths":         files,
		"excluded_paths":         []string{},
		"ambiguous_paths":        []string{},
		"dispositions":           dispositions,
		"criticality":            criticality,
		"classification_reasons": reasons,
		"decision_source":        decisionSource,
	}
}

func scanTargets(files []string) map[string]any {
	valueTier := map[string]string{}
	decision := map[string]string{}
	for _, path := range files {
		valueTier[path] = "P1"
		decision[path] = "scan"
	}
	return map[string]any{
		"selected_paths":       files,
		"sampled_paths":        []string{},
		"inventory_only_paths": []string{},
		"excluded_paths":       []string{},
		"blocked_paths":        []string{},
		"value_tier":           valueTier,
		"scan_decision":        decision,
	}
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
	skeleton := map[string]any{
		"packet_id":      packetID,
		"assigned_paths": paths,
		"paths_read":     paths,
		"ledger": map[string]any{
			"todo": []string{}, "doing": []string{}, "done": paths,
			"blocked": []string{}, "overflow": []string{},
		},
		"coverage": []map[string]any{{"path": "<assigned-path>", "outcome": "read", "evidence_ids": []string{"E-001"}}},
		"evidence": []map[string]any{{"id": "E-001", "source_path": "<assigned-path>", "span": "<line-range>"}},
		"nodes": []map[string]any{{
			"id": "N-001", "type": "file", "title": "<title>",
			"paths": []string{"<assigned-path>"}, "evidence_ids": []string{"E-001"},
		}},
		"edges": []map[string]any{}, "observations": []map[string]any{}, "claims": []map[string]any{},
		"confidence": "high", "acceptance": "pass",
	}
	skeletonJSON, _ := json.MarshalIndent(skeleton, "", "  ")
	builder.WriteString("```json\n")
	builder.Write(skeletonJSON)
	builder.WriteString("\n```\n\n")
	builder.WriteString("Every pass result must mark every assigned path read or deep_read with matching evidence and nodes[].paths. For a relationship proven by an assigned file but targeting another scan packet, one edge endpoint may be that other file's concrete repository path; at least one endpoint must remain packet-local. Do not read an unassigned target merely to strengthen the edge. Do not write product files or canonical cognition ledgers.\n")
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
	lower := strings.ToLower(path)
	base := strings.ToLower(filepath.Base(path))
	switch {
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
