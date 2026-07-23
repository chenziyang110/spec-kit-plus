package scanworkbench

import (
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strings"

	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
)

const (
	estimatedBytesPerToken       = int64(4)
	estimatedResultTokensPerPath = int64(256)
	defaultEffectiveWorkerTokens = int64(16_000)
	defaultPacketBytes           = int64(2 * 1024 * 1024)
)

type packetPlanningBudget struct {
	MaxPaths  int
	MaxBytes  int64
	MaxTokens int64
}

type packetPlan struct {
	Paths           []string
	EstimatedTokens int64
	EstimatedBytes  int64
	Oversized       bool
}

type LeaseInput struct {
	PacketID             string
	WorkerID             string
	WorkerCapacityTokens int64
}

type LeasePayload struct {
	Status                 string `json:"status"`
	PacketID               string `json:"packet_id"`
	AttemptID              string `json:"attempt_id"`
	WorkerID               string `json:"worker_id"`
	TaskPath               string `json:"task_path"`
	ResultSubmissionPath   string `json:"result_submission_path"`
	ResultHandoffPath      string `json:"result_handoff_path"`
	ResultProtocol         string `json:"result_protocol"`
	RequiredAcceptance     string `json:"required_acceptance"`
	EstimatedTokens        int64  `json:"estimated_tokens"`
	EffectiveContextBudget int64  `json:"effective_context_budget_tokens"`
	PendingPackets         int    `json:"pending_packets"`
	NextAction             string `json:"next_action"`
}

type ActiveLeaseSummary struct {
	PacketID                 string `json:"packet_id"`
	AttemptID                string `json:"attempt_id"`
	WorkerID                 string `json:"worker_id"`
	CheckpointSequence       int    `json:"checkpoint_sequence"`
	CompletedPathCount       int    `json:"completed_path_count"`
	RemainingPathCount       int    `json:"remaining_path_count"`
	EstimatedRemainingTokens int64  `json:"estimated_remaining_tokens"`
}

type CheckpointInput struct {
	PacketID   string
	AttemptID  string
	ResultPath string
}

type CheckpointPayload struct {
	Status             string `json:"status"`
	PacketID           string `json:"packet_id"`
	AttemptID          string `json:"attempt_id"`
	Sequence           int    `json:"sequence"`
	CompletedPathCount int    `json:"completed_path_count"`
	RemainingPathCount int    `json:"remaining_path_count"`
	CheckpointPath     string `json:"checkpoint_path"`
	NextAction         string `json:"next_action"`
}

type YieldInput struct {
	PacketID  string
	AttemptID string
}

type YieldPayload struct {
	Status             string `json:"status"`
	PacketID           string `json:"packet_id"`
	AttemptID          string `json:"attempt_id"`
	AcceptedPathCount  int    `json:"accepted_path_count"`
	RemainingPathCount int    `json:"remaining_path_count"`
	RemainderPacketID  string `json:"remainder_packet_id,omitempty"`
	NextAction         string `json:"next_action"`
}

type StatusPayload struct {
	Status                     string               `json:"status"`
	StageState                 string               `json:"stage_state"`
	Packets                    map[string]int       `json:"packets"`
	ActiveLeases               []ActiveLeaseSummary `json:"active_leases,omitempty"`
	EstimatedRemainingTokens   int64                `json:"estimated_remaining_tokens"`
	RecommendedParallelWorkers int                  `json:"recommended_parallel_workers"`
	CompletionAllowed          bool                 `json:"completion_allowed"`
	CompletionGate             string               `json:"completion_gate"`
	NextAction                 string               `json:"next_action"`
}

func planPackets(root string, files []string, budget packetPlanningBudget) ([]packetPlan, error) {
	plans := []packetPlan{}
	current := packetPlan{Paths: []string{}}
	flush := func() {
		if len(current.Paths) == 0 {
			return
		}
		plans = append(plans, current)
		current = packetPlan{Paths: []string{}}
	}

	for _, rel := range files {
		info, err := os.Stat(filepath.Join(root, filepath.FromSlash(rel)))
		if err != nil {
			return nil, fmt.Errorf("estimate scan path %s: %w", rel, err)
		}
		bytes := info.Size()
		tokens := estimatePathTokens(bytes)
		exceedsCurrent := len(current.Paths) > 0 && (len(current.Paths) >= budget.MaxPaths ||
			(budget.MaxBytes > 0 && current.EstimatedBytes+bytes > budget.MaxBytes) ||
			(budget.MaxTokens > 0 && current.EstimatedTokens+tokens > budget.MaxTokens))
		if exceedsCurrent {
			flush()
		}
		current.Paths = append(current.Paths, rel)
		current.EstimatedBytes += bytes
		current.EstimatedTokens += tokens
		if (budget.MaxBytes > 0 && bytes > budget.MaxBytes) || (budget.MaxTokens > 0 && tokens > budget.MaxTokens) {
			current.Oversized = true
			flush()
		}
	}
	flush()
	return plans, nil
}

func estimatePathTokens(sizeBytes int64) int64 {
	contentTokens := (sizeBytes + estimatedBytesPerToken - 1) / estimatedBytesPerToken
	if contentTokens < 1 {
		contentTokens = 1
	}
	return contentTokens + estimatedResultTokensPerPath
}

func scanGenerationID(root string, files []string) (string, error) {
	digest := sha256.New()
	for _, rel := range files {
		if _, err := io.WriteString(digest, filepath.ToSlash(rel)+"\x00"); err != nil {
			return "", err
		}
		file, err := os.Open(filepath.Join(root, filepath.FromSlash(rel)))
		if err != nil {
			return "", fmt.Errorf("hash scan generation path %s: %w", rel, err)
		}
		_, copyErr := io.Copy(digest, file)
		closeErr := file.Close()
		if copyErr != nil {
			return "", fmt.Errorf("hash scan generation path %s: %w", rel, copyErr)
		}
		if closeErr != nil {
			return "", fmt.Errorf("close scan generation path %s: %w", rel, closeErr)
		}
	}
	var nonce [16]byte
	if _, err := rand.Read(nonce[:]); err != nil {
		return "", fmt.Errorf("create scan generation nonce: %w", err)
	}
	if _, err := digest.Write(nonce[:]); err != nil {
		return "", err
	}
	return "GEN-" + hex.EncodeToString(digest.Sum(nil))[:16], nil
}

func Lease(paths rt.Paths, input LeaseInput) (LeasePayload, error) {
	if err := validateRuntimeControlDir(paths); err != nil {
		return LeasePayload{}, err
	}
	release, err := acquireWorkbenchLock(paths)
	if err != nil {
		return LeasePayload{}, err
	}
	defer release()

	workerID := strings.TrimSpace(input.WorkerID)
	if !workerIDPattern.MatchString(workerID) {
		return LeasePayload{}, fmt.Errorf("scan lease requires a safe worker_id using letters, digits, slash, dot, colon, underscore, or hyphen")
	}
	queuePath := filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json")
	var queue queueFile
	if err := readJSON(queuePath, &queue); err != nil {
		return LeasePayload{}, fmt.Errorf("read scan queue: %w", err)
	}
	if err := requireV2Workbench(queue); err != nil {
		return LeasePayload{}, err
	}
	packetIndex := -1
	wantedPacketID := strings.TrimSpace(input.PacketID)
	for index := range queue.Packets {
		packet := queue.Packets[index]
		if wantedPacketID != "" && packet.PacketID != wantedPacketID {
			continue
		}
		if packet.State == "pending" {
			packetIndex = index
			break
		}
		if wantedPacketID != "" && packet.PacketID == wantedPacketID {
			return LeasePayload{}, fmt.Errorf("packet %s state %s cannot be leased", packet.PacketID, packet.State)
		}
	}
	if packetIndex < 0 {
		if wantedPacketID != "" {
			return LeasePayload{}, fmt.Errorf("packet %s is not present or pending", wantedPacketID)
		}
		return LeasePayload{}, fmt.Errorf("scan queue has no pending packet")
	}

	packet := &queue.Packets[packetIndex]
	capacity := input.WorkerCapacityTokens
	if capacity < 0 {
		return LeasePayload{}, fmt.Errorf("worker capacity tokens must not be negative")
	}
	if capacity == 0 {
		if packet.Oversized {
			return LeasePayload{}, fmt.Errorf("packet %s exceeds the planned worker capacity (%d estimated tokens); choose a larger worker and pass --worker-capacity-tokens of at least %d", packet.PacketID, packet.EffectiveContextBudget, packet.EstimatedTokens)
		}
		capacity = packet.EffectiveContextBudget
	}
	if capacity < packet.EstimatedTokens {
		return LeasePayload{}, fmt.Errorf("packet %s needs an estimated %d tokens but worker capacity is %d; re-plan or choose a larger worker", packet.PacketID, packet.EstimatedTokens, capacity)
	}
	packet.AttemptNumber++
	packet.AttemptID = fmt.Sprintf("%s-%s-attempt-%03d", queue.GenerationID, packet.PacketID, packet.AttemptNumber)
	packet.WorkerID = workerID
	packet.EffectiveContextBudget = capacity
	packet.State = "leased"
	packet.CheckpointPath = ""
	packet.CheckpointSequence = 0
	packet.CompletedPaths = nil

	var handoffs handoffFile
	handoffPath := filepath.Join(paths.RuntimeDir, "workbench", "handoff-ledger.json")
	if err := readJSON(handoffPath, &handoffs); err != nil {
		return LeasePayload{}, err
	}
	event := map[string]any{
		"event_id":            "lease-" + packet.AttemptID,
		"packet_id":           packet.PacketID,
		"attempt_id":          packet.AttemptID,
		"worker_id":           workerID,
		"event_type":          "dispatched",
		"result_handoff_path": packet.ResultHandoffPath,
	}
	handoffs.Events, err = mergeObjectRows(handoffs.Events, []map[string]any{event}, "event_id", "handoff")
	if err != nil {
		return LeasePayload{}, err
	}
	// Materialize the retry-safe attempt surfaces before committing the queue
	// transition. If any derived write fails, the packet remains pending and a
	// retry recreates the same attempt number and handoff event id.
	if err := writeTextAtomic(packetTaskPath(paths, packet.PacketID), renderLeasedPacket(*packet)); err != nil {
		return LeasePayload{}, err
	}
	if err := writeJSONAtomic(
		filepath.Join(paths.RuntimeDir, "workbench", "pending-results", packet.PacketID+".json"),
		workerResultSkeleton(packet.PacketID, packet.AttemptID, packet.AssignedPaths),
	); err != nil {
		return LeasePayload{}, err
	}
	if err := writeJSONAtomic(handoffPath, handoffs); err != nil {
		return LeasePayload{}, err
	}
	if err := writeJSONAtomic(queuePath, queue); err != nil {
		return LeasePayload{}, err
	}

	pending := 0
	for _, row := range queue.Packets {
		if row.State == "pending" {
			pending++
		}
	}
	return LeasePayload{
		Status:                 "leased",
		PacketID:               packet.PacketID,
		AttemptID:              packet.AttemptID,
		WorkerID:               workerID,
		TaskPath:               canonicalPacketTaskPath(packet.PacketID),
		ResultSubmissionPath:   canonicalPendingResultPath(packet.PacketID),
		ResultHandoffPath:      packet.ResultHandoffPath,
		ResultProtocol:         "map_scan_result.v2",
		RequiredAcceptance:     "partial",
		EstimatedTokens:        packet.EstimatedTokens,
		EffectiveContextBudget: packet.EffectiveContextBudget,
		PendingPackets:         pending,
		NextAction:             "dispatch_worker_task_brief",
	}, nil
}

func Checkpoint(paths rt.Paths, input CheckpointInput) (CheckpointPayload, error) {
	if err := validateRuntimeControlDir(paths); err != nil {
		return CheckpointPayload{}, err
	}
	release, err := acquireWorkbenchLock(paths)
	if err != nil {
		return CheckpointPayload{}, err
	}
	defer release()

	queuePath := filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json")
	var queue queueFile
	if err := readJSON(queuePath, &queue); err != nil {
		return CheckpointPayload{}, fmt.Errorf("read scan queue: %w", err)
	}
	if err := requireV2Workbench(queue); err != nil {
		return CheckpointPayload{}, err
	}
	packetIndex, err := activePacketIndex(queue, input.PacketID, input.AttemptID)
	if err != nil {
		return CheckpointPayload{}, err
	}
	packet := queue.Packets[packetIndex]
	resultPath, err := resolveResultPath(paths, input.ResultPath)
	if err != nil {
		return CheckpointPayload{}, err
	}
	var result workerResult
	if err := readJSON(resultPath, &result); err != nil {
		return CheckpointPayload{}, fmt.Errorf("read checkpoint result: %w", err)
	}
	if result.AttemptID != packet.AttemptID {
		return CheckpointPayload{}, fmt.Errorf("packet %s checkpoint attempt_id %q does not match active attempt %s", packet.PacketID, result.AttemptID, packet.AttemptID)
	}
	if result.Sequence < 1 {
		return CheckpointPayload{}, fmt.Errorf("packet %s checkpoint sequence must be positive", packet.PacketID)
	}
	if result.Sequence == packet.CheckpointSequence {
		if packet.CheckpointPath == "" {
			return CheckpointPayload{}, fmt.Errorf("packet %s checkpoint sequence %d has no durable checkpoint", packet.PacketID, result.Sequence)
		}
		var previous workerResult
		previousPath := filepath.Join(paths.Root, filepath.FromSlash(packet.CheckpointPath))
		if err := readJSON(previousPath, &previous); err != nil {
			return CheckpointPayload{}, fmt.Errorf("read previous checkpoint: %w", err)
		}
		if !sameJSON(previous, result) {
			return CheckpointPayload{}, fmt.Errorf("packet %s checkpoint sequence %d conflicts with the durable checkpoint", packet.PacketID, result.Sequence)
		}
		return checkpointPayload(packet, result, packet.CheckpointPath), nil
	}
	if result.Sequence != packet.CheckpointSequence+1 {
		return CheckpointPayload{}, fmt.Errorf("packet %s checkpoint sequence %d must follow %d", packet.PacketID, result.Sequence, packet.CheckpointSequence)
	}
	if err := validateCheckpointResult(packet, result, allAssignedPathSet(queue)); err != nil {
		return CheckpointPayload{}, err
	}
	var previousCheckpointNodes []map[string]any
	if packet.CheckpointPath != "" {
		var previous workerResult
		previousPath := filepath.Join(paths.Root, filepath.FromSlash(packet.CheckpointPath))
		if err := readJSON(previousPath, &previous); err != nil {
			return CheckpointPayload{}, fmt.Errorf("read previous checkpoint: %w", err)
		}
		if !isSubset(normalizedSet(previous.PathsRead), normalizedSet(result.PathsRead)) {
			return CheckpointPayload{}, fmt.Errorf("packet %s cumulative checkpoint dropped previously completed paths", packet.PacketID)
		}
		previousCheckpointNodes = previous.Nodes
	}

	completedResult := checkpointCompletedResult(result)
	if err := mergeCheckpointRows(paths, queue, packet.PacketID, completedResult, previousCheckpointNodes); err != nil {
		return CheckpointPayload{}, err
	}
	checkpointRel := canonicalCheckpointPath(packet.PacketID, packet.AttemptID, result.Sequence)
	if err := writeJSONAtomic(filepath.Join(paths.Root, filepath.FromSlash(checkpointRel)), result); err != nil {
		return CheckpointPayload{}, err
	}
	queue.Packets[packetIndex].CheckpointPath = checkpointRel
	queue.Packets[packetIndex].CheckpointSequence = result.Sequence
	queue.Packets[packetIndex].CompletedPaths = append([]string{}, result.PathsRead...)
	if err := writeJSONAtomic(queuePath, queue); err != nil {
		return CheckpointPayload{}, err
	}

	packet.CheckpointPath = checkpointRel
	packet.CheckpointSequence = result.Sequence
	packet.CompletedPaths = append([]string{}, result.PathsRead...)
	return checkpointPayload(packet, result, checkpointRel), nil
}

func checkpointPayload(packet queuePacket, result workerResult, checkpointPath string) CheckpointPayload {
	remaining := len(packet.AssignedPaths) - len(normalizedSet(result.PathsRead))
	nextAction := "continue_packet"
	if remaining == 0 {
		nextAction = "accept_packet"
	}
	return CheckpointPayload{
		Status: "checkpointed", PacketID: packet.PacketID, AttemptID: packet.AttemptID,
		Sequence: result.Sequence, CompletedPathCount: len(normalizedSet(result.PathsRead)),
		RemainingPathCount: remaining, CheckpointPath: checkpointPath, NextAction: nextAction,
	}
}

func Yield(paths rt.Paths, input YieldInput) (YieldPayload, error) {
	if err := validateRuntimeControlDir(paths); err != nil {
		return YieldPayload{}, err
	}
	release, err := acquireWorkbenchLock(paths)
	if err != nil {
		return YieldPayload{}, err
	}
	defer release()
	return yieldUnlocked(paths, input)
}

func yieldUnlocked(paths rt.Paths, input YieldInput) (YieldPayload, error) {
	queuePath := filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json")
	var queue queueFile
	if err := readJSON(queuePath, &queue); err != nil {
		return YieldPayload{}, fmt.Errorf("read scan queue: %w", err)
	}
	if err := requireV2Workbench(queue); err != nil {
		return YieldPayload{}, err
	}
	packetIndex, err := activePacketIndex(queue, input.PacketID, input.AttemptID)
	if err != nil {
		return YieldPayload{}, err
	}
	packet := queue.Packets[packetIndex]
	if packet.CheckpointPath == "" {
		queue.Packets[packetIndex].State = "pending"
		queue.Packets[packetIndex].WorkerID = ""
		queue.Packets[packetIndex].AttemptID = ""
		if err := appendYieldEvent(paths, &queue, packet, "requeued", ""); err != nil {
			return YieldPayload{}, err
		}
		return YieldPayload{
			Status: "requeued", PacketID: packet.PacketID, AttemptID: input.AttemptID,
			RemainingPathCount: len(packet.AssignedPaths), NextAction: "dispatch_remaining_packets",
		}, nil
	}

	var checkpoint workerResult
	checkpointPath := filepath.Join(paths.Root, filepath.FromSlash(packet.CheckpointPath))
	if err := readJSON(checkpointPath, &checkpoint); err != nil {
		return YieldPayload{}, fmt.Errorf("read latest checkpoint: %w", err)
	}
	completed := orderedSubset(packet.AssignedPaths, normalizedSet(checkpoint.PathsRead))
	remaining := orderedDifference(packet.AssignedPaths, normalizedSet(completed))
	if len(completed) == 0 {
		return YieldPayload{}, fmt.Errorf("packet %s checkpoint has no completed paths", packet.PacketID)
	}

	acceptedResult := checkpointCompletedResult(checkpoint)
	queue.Packets[packetIndex].AssignedPaths = completed
	queue.Packets[packetIndex].State = "accepted"
	queue.Packets[packetIndex].CompletedPaths = append([]string{}, completed...)
	remainderPacketID := ""
	if len(remaining) > 0 {
		remainderPacketID = nextRemainderPacketID(queue, packet.PacketID)
		effectiveBudget := packet.EffectiveContextBudget
		if effectiveBudget == 0 {
			effectiveBudget = defaultEffectiveWorkerTokens
		}
		// The remainder is an exact subset of a packet that was already admitted
		// under its planning budget. Re-estimate it as one packet instead of
		// silently imposing today's defaults, which may be stricter than the
		// original custom byte budget.
		plan, planErr := planPackets(paths.Root, remaining, packetPlanningBudget{MaxPaths: len(remaining)})
		if planErr != nil || len(plan) != 1 {
			if planErr != nil {
				return YieldPayload{}, planErr
			}
			return YieldPayload{}, fmt.Errorf("plan yielded remainder for packet %s", packet.PacketID)
		}
		queue.Packets = append(queue.Packets, queuePacket{
			PacketID: remainderPacketID, State: "pending", AssignedPaths: remaining,
			ResultHandoffPath: canonicalWorkerResultPath(remainderPacketID), ParentPacketID: packet.PacketID,
			EstimatedTokens: plan[0].EstimatedTokens, EstimatedBytes: plan[0].EstimatedBytes,
			EffectiveContextBudget: effectiveBudget, Oversized: plan[0].EstimatedTokens > effectiveBudget,
		})
		if err := writeTextAtomic(packetTaskPath(paths, remainderPacketID), renderPacket(remainderPacketID, remaining)); err != nil {
			return YieldPayload{}, err
		}
		if err := writeJSONAtomic(
			filepath.Join(paths.RuntimeDir, "workbench", "pending-results", remainderPacketID+".json"),
			workerResultSkeleton(remainderPacketID, "", remaining),
		); err != nil {
			return YieldPayload{}, err
		}
	}
	if err := writeTextAtomic(packetTaskPath(paths, packet.PacketID), renderPacket(packet.PacketID, completed)); err != nil {
		return YieldPayload{}, err
	}
	canonicalResult := filepath.Join(paths.RuntimeDir, "workbench", "worker-results", packet.PacketID+".json")
	if err := ensureWorkerResultCompatible(canonicalResult, acceptedResult); err != nil {
		return YieldPayload{}, err
	}
	submissionValue, submissionDigest, err := readNormalizedJSONFile(checkpointPath)
	if err != nil {
		return YieldPayload{}, fmt.Errorf("hash packet %s checkpoint: %w", packet.PacketID, err)
	}
	submissionSnapshotPath := acceptanceSubmissionSnapshotPath(paths, packet.PacketID)
	if err := ensureNormalizedJSONCompatible(submissionSnapshotPath, submissionValue); err != nil {
		return YieldPayload{}, err
	}
	receipt, err := newAcceptanceReceipt(
		queue,
		packet,
		acceptanceSubmissionPath(paths, checkpointPath),
		submissionDigest,
		checkpoint,
		acceptedResult,
	)
	if err != nil {
		return YieldPayload{}, err
	}
	receiptPath := acceptanceReceiptPath(paths, packet.PacketID)
	if err := ensureAcceptanceReceiptCompatible(receiptPath, receipt); err != nil {
		return YieldPayload{}, err
	}
	var handoffs handoffFile
	handoffPath := filepath.Join(paths.RuntimeDir, "workbench", "handoff-ledger.json")
	if err := readJSON(handoffPath, &handoffs); err != nil {
		return YieldPayload{}, err
	}
	yieldEvent := map[string]any{
		"event_id": "yield-" + packet.AttemptID, "packet_id": packet.PacketID,
		"attempt_id": packet.AttemptID, "worker_id": packet.WorkerID, "event_type": "split",
	}
	if remainderPacketID != "" {
		yieldEvent["child_packet_id"] = remainderPacketID
	}
	returnEvent := map[string]any{
		"event_id": "return-" + packet.PacketID, "packet_id": packet.PacketID,
		"attempt_id": packet.AttemptID, "worker_id": packet.WorkerID, "event_type": "returned",
		"worker_result_path": canonicalWorkerResultPath(packet.PacketID),
	}
	var mergeErr error
	handoffs.Events, mergeErr = mergeObjectRows(handoffs.Events, []map[string]any{yieldEvent, returnEvent}, "event_id", "handoff")
	if mergeErr != nil {
		return YieldPayload{}, mergeErr
	}
	if err := writeJSONAtomic(submissionSnapshotPath, submissionValue); err != nil {
		return YieldPayload{}, err
	}
	if err := writeJSONAtomic(receiptPath, receipt); err != nil {
		return YieldPayload{}, err
	}
	if err := writeJSONAtomic(canonicalResult, acceptedResult); err != nil {
		return YieldPayload{}, err
	}
	if err := writeJSONAtomic(handoffPath, handoffs); err != nil {
		return YieldPayload{}, err
	}
	if err := writeJSONAtomic(queuePath, queue); err != nil {
		return YieldPayload{}, err
	}
	var ledger coverageLedgerFile
	if err := readJSON(filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json"), &ledger); err == nil {
		_ = renderHumanState(paths, queue, ledger)
	}
	nextAction := "validate_scan"
	if len(remaining) > 0 {
		nextAction = "dispatch_remaining_packets"
	}
	return YieldPayload{
		Status:             "yielded",
		PacketID:           packet.PacketID,
		AttemptID:          input.AttemptID,
		AcceptedPathCount:  len(completed),
		RemainingPathCount: len(remaining),
		RemainderPacketID:  remainderPacketID,
		NextAction:         nextAction,
	}, nil
}

func Requeue(paths rt.Paths, input YieldInput) (YieldPayload, error) {
	return Yield(paths, input)
}

func Status(paths rt.Paths) (StatusPayload, error) {
	if err := validateRuntimeControlDir(paths); err != nil {
		return StatusPayload{}, err
	}
	var queue queueFile
	if err := readJSON(filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"), &queue); err != nil {
		return StatusPayload{}, fmt.Errorf("read scan queue: %w", err)
	}
	if err := requireV2Workbench(queue); err != nil {
		return StatusPayload{}, err
	}
	counts := map[string]int{"pending": 0, "leased": 0, "accepted": 0, "blocked": 0}
	var remainingTokens int64
	activeLeases := []ActiveLeaseSummary{}
	for _, packet := range queue.Packets {
		counts[packet.State]++
		if packet.State == "accepted" {
			continue
		}
		remainingPaths := packet.AssignedPaths
		packetRemainingTokens := packet.EstimatedTokens
		if packet.State == "leased" && len(packet.CompletedPaths) > 0 {
			remainingPaths = orderedDifference(packet.AssignedPaths, normalizedSet(packet.CompletedPaths))
			packetRemainingTokens = estimateExistingPathsTokens(paths.Root, remainingPaths)
		}
		remainingTokens += packetRemainingTokens
		if packet.State == "leased" {
			activeLeases = append(activeLeases, ActiveLeaseSummary{
				PacketID: packet.PacketID, AttemptID: packet.AttemptID, WorkerID: packet.WorkerID,
				CheckpointSequence: packet.CheckpointSequence,
				CompletedPathCount: len(normalizedSet(packet.CompletedPaths)),
				RemainingPathCount: len(remainingPaths), EstimatedRemainingTokens: packetRemainingTokens,
			})
		}
	}
	nextAction := "validate_scan"
	stageState := "validation_required"
	if counts["pending"] > 0 {
		nextAction = "dispatch_pending_packets"
		stageState = "packets_pending"
	} else if counts["leased"] > 0 {
		nextAction = "await_worker_results"
		stageState = "worker_results_pending"
	} else if counts["blocked"] > 0 {
		nextAction = "resolve_blocked_packets"
		stageState = "packets_blocked"
	}
	return StatusPayload{
		Status: "ok", StageState: stageState, Packets: counts, ActiveLeases: activeLeases,
		EstimatedRemainingTokens: remainingTokens, RecommendedParallelWorkers: counts["pending"],
		CompletionAllowed: false, CompletionGate: "validate_scan", NextAction: nextAction,
	}, nil
}

func estimateExistingPathsTokens(root string, paths []string) int64 {
	var total int64
	for _, rel := range paths {
		info, err := os.Stat(filepath.Join(root, filepath.FromSlash(rel)))
		if err != nil || !info.Mode().IsRegular() {
			continue
		}
		total += estimatePathTokens(info.Size())
	}
	return total
}

func validateCheckpointResult(packet queuePacket, result workerResult, allAssignedPaths map[string]bool) error {
	if result.Protocol != "map_scan_result.v2" {
		return fmt.Errorf("packet %s checkpoint protocol %q must be map_scan_result.v2", packet.PacketID, result.Protocol)
	}
	if result.PacketID != packet.PacketID {
		return fmt.Errorf("checkpoint packet_id %q does not match %s", result.PacketID, packet.PacketID)
	}
	assigned := normalizedSet(packet.AssignedPaths)
	if !sameSet(assigned, normalizedSet(result.AssignedPaths)) {
		return fmt.Errorf("packet %s checkpoint assigned_paths must exactly match the leased packet", packet.PacketID)
	}
	completed := normalizedSet(result.PathsRead)
	if len(completed) == 0 {
		return fmt.Errorf("packet %s checkpoint must contain at least one completed path", packet.PacketID)
	}
	if !isSubset(completed, assigned) {
		return fmt.Errorf("packet %s checkpoint contains a path outside assigned_paths", packet.PacketID)
	}
	remaining := setDifference(assigned, completed)
	if !sameSet(completed, normalizedSet(result.Ledger.Done)) || !sameSet(remaining, normalizedSet(result.Ledger.Todo)) ||
		len(result.Ledger.Doing) > 0 || len(result.Ledger.Blocked) > 0 || len(result.Ledger.Overflow) > 0 {
		return fmt.Errorf("packet %s checkpoint ledger must partition assigned paths into done and todo", packet.PacketID)
	}
	if result.Acceptance != "partial" {
		return fmt.Errorf("packet %s worker-authored checkpoint acceptance must remain partial; runtime derives pass", packet.PacketID)
	}
	completedPacket := packet
	completedPacket.AssignedPaths = orderedSubset(packet.AssignedPaths, completed)
	return validateWorkerResult(completedPacket, checkpointCompletedResult(result), allAssignedPaths)
}

func checkpointCompletedResult(result workerResult) workerResult {
	completed := normalizedSet(result.PathsRead)
	result.AssignedPaths = orderedSubset(result.AssignedPaths, completed)
	result.PathsRead = append([]string{}, result.AssignedPaths...)
	result.Ledger = workerLedger{Done: append([]string{}, result.AssignedPaths...), Todo: []string{}, Doing: []string{}, Blocked: []string{}, Overflow: []string{}}
	result.Acceptance = "pass"
	return result
}

func mergeCheckpointRows(paths rt.Paths, queue queueFile, packetID string, result workerResult, previousCheckpointNodes []map[string]any) error {
	if err := ensureEvidenceCompatible(paths, packetID, result.Evidence); err != nil {
		return err
	}
	var nodes map[string][]map[string]any
	var edges map[string][]map[string]any
	var observations map[string][]map[string]any
	var claims map[string][]map[string]any
	var coverage coverageFile
	var ledger coverageLedgerFile
	for path, target := range map[string]any{
		filepath.Join(paths.RuntimeDir, "provisional", "nodes.json"):         &nodes,
		filepath.Join(paths.RuntimeDir, "provisional", "edges.json"):         &edges,
		filepath.Join(paths.RuntimeDir, "provisional", "observations.json"):  &observations,
		filepath.Join(paths.RuntimeDir, "provisional", "claims.json"):        &claims,
		filepath.Join(paths.RuntimeDir, "coverage.json"):                     &coverage,
		filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json"): &ledger,
	} {
		if err := readJSON(path, target); err != nil {
			return err
		}
	}
	var err error
	if nodes["nodes"], err = mergeCheckpointNodeRows(nodes["nodes"], result.Nodes, previousCheckpointNodes); err != nil {
		return err
	}
	if edges["edges"], err = mergeObjectRows(edges["edges"], result.Edges, "id", "edge"); err != nil {
		return err
	}
	if observations["observations"], err = mergeObjectRows(observations["observations"], result.Observations, "id", "observation"); err != nil {
		return err
	}
	if claims["claims"], err = mergeObjectRows(claims["claims"], result.Claims, "id", "claim"); err != nil {
		return err
	}
	if coverage.Rows, err = mergeObjectRows(coverage.Rows, result.Coverage, "path", "coverage"); err != nil {
		return err
	}
	ledgerRows := make([]map[string]any, 0, len(result.Coverage))
	for _, row := range result.Coverage {
		item := cloneObject(row)
		item["packet_id"] = packetID
		item["status"] = stringValue(row["outcome"])
		ledgerRows = append(ledgerRows, item)
	}
	if ledger.Rows, err = mergeObjectRows(ledger.Rows, ledgerRows, "path", "coverage ledger"); err != nil {
		return err
	}
	for path, value := range map[string]any{
		filepath.Join(paths.RuntimeDir, "evidence", packetID+".json"):        map[string]any{"rows": result.Evidence},
		filepath.Join(paths.RuntimeDir, "provisional", "nodes.json"):         nodes,
		filepath.Join(paths.RuntimeDir, "provisional", "edges.json"):         edges,
		filepath.Join(paths.RuntimeDir, "provisional", "observations.json"):  observations,
		filepath.Join(paths.RuntimeDir, "provisional", "claims.json"):        claims,
		filepath.Join(paths.RuntimeDir, "coverage.json"):                     coverage,
		filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json"): ledger,
	} {
		if err := writeJSONAtomic(path, value); err != nil {
			return err
		}
	}
	return renderHumanState(paths, queue, ledger)
}

func mergeCheckpointNodeRows(existing []map[string]any, incoming []map[string]any, previousCheckpoint []map[string]any) ([]map[string]any, error) {
	previousByID := map[string]map[string]any{}
	for _, row := range previousCheckpoint {
		identity := stringValue(row["id"])
		if identity == "" {
			return nil, fmt.Errorf("previous checkpoint node row has no id")
		}
		if previous, duplicate := previousByID[identity]; duplicate {
			if !sameJSON(previous, row) {
				return nil, fmt.Errorf("node %s conflict in previous checkpoint", identity)
			}
			continue
		}
		previousByID[identity] = row
	}

	merged := make([]map[string]any, 0, len(existing)+len(incoming))
	index := map[string]int{}
	for _, row := range existing {
		identity := stringValue(row["id"])
		if identity == "" {
			return nil, fmt.Errorf("existing node row has no id")
		}
		if position, duplicate := index[identity]; duplicate {
			if !sameJSON(merged[position], row) {
				return nil, fmt.Errorf("node %s conflict in existing rows", identity)
			}
			continue
		}
		index[identity] = len(merged)
		merged = append(merged, row)
	}

	for _, row := range incoming {
		identity := stringValue(row["id"])
		if identity == "" {
			return nil, fmt.Errorf("incoming node row has no id")
		}
		position, exists := index[identity]
		if !exists {
			index[identity] = len(merged)
			merged = append(merged, row)
			continue
		}
		if sameJSON(merged[position], row) {
			continue
		}

		previous, cumulative := previousByID[identity]
		if !cumulative || !sameJSON(merged[position], previous) {
			return nil, fmt.Errorf("node %s conflict with partially merged result", identity)
		}
		extended, err := monotonicCheckpointNodeExtension(previous, row, identity)
		if err != nil {
			return nil, err
		}
		merged[position] = extended
	}

	sortObjectRows(merged, "id")
	return merged, nil
}

func monotonicCheckpointNodeExtension(previous map[string]any, incoming map[string]any, identity string) (map[string]any, error) {
	previousStable := cloneObject(previous)
	incomingStable := cloneObject(incoming)
	delete(previousStable, "paths")
	delete(previousStable, "evidence_ids")
	delete(incomingStable, "paths")
	delete(incomingStable, "evidence_ids")
	if !sameJSON(previousStable, incomingStable) {
		return nil, fmt.Errorf("node %s changed immutable fields across cumulative checkpoints", identity)
	}

	if !isSubset(normalizedSet(stringValues(previous["paths"])), normalizedSet(stringValues(incoming["paths"]))) {
		return nil, fmt.Errorf("node %s dropped paths from the previous cumulative checkpoint", identity)
	}
	if !isSubset(exactStringSet(stringValues(previous["evidence_ids"])), exactStringSet(stringValues(incoming["evidence_ids"]))) {
		return nil, fmt.Errorf("node %s dropped evidence_ids from the previous cumulative checkpoint", identity)
	}
	return incoming, nil
}

func exactStringSet(values []string) map[string]bool {
	set := make(map[string]bool, len(values))
	for _, value := range values {
		if value = strings.TrimSpace(value); value != "" {
			set[value] = true
		}
	}
	return set
}

func activePacketIndex(queue queueFile, packetID string, attemptID string) (int, error) {
	packetID = strings.TrimSpace(packetID)
	attemptID = strings.TrimSpace(attemptID)
	for index, packet := range queue.Packets {
		if packet.PacketID != packetID {
			continue
		}
		if packet.State != "leased" {
			return -1, fmt.Errorf("packet %s state %s has no active lease", packetID, packet.State)
		}
		if attemptID == "" || packet.AttemptID != attemptID {
			return -1, fmt.Errorf("packet %s attempt_id %q does not match active attempt %s", packetID, attemptID, packet.AttemptID)
		}
		return index, nil
	}
	return -1, fmt.Errorf("packet %s is not present in scan queue", packetID)
}

func resolveResultPath(paths rt.Paths, value string) (string, error) {
	value = strings.TrimSpace(value)
	if value == "" {
		return "", fmt.Errorf("checkpoint requires result_path")
	}
	if filepath.IsAbs(value) {
		return value, nil
	}
	return filepath.Join(paths.Root, filepath.FromSlash(value)), nil
}

func allAssignedPathSet(queue queueFile) map[string]bool {
	paths := map[string]bool{}
	for _, packet := range queue.Packets {
		for path := range normalizedSet(packet.AssignedPaths) {
			paths[path] = true
		}
	}
	return paths
}

func appendYieldEvent(paths rt.Paths, queue *queueFile, packet queuePacket, state string, childPacketID string) error {
	handoffPath := filepath.Join(paths.RuntimeDir, "workbench", "handoff-ledger.json")
	var handoffs handoffFile
	if err := readJSON(handoffPath, &handoffs); err != nil {
		return err
	}
	event := map[string]any{
		"event_id":   "yield-" + packet.AttemptID,
		"packet_id":  packet.PacketID,
		"attempt_id": packet.AttemptID,
		"worker_id":  packet.WorkerID,
		"event_type": state,
	}
	if childPacketID != "" {
		event["child_packet_id"] = childPacketID
	}
	var err error
	handoffs.Events, err = mergeObjectRows(handoffs.Events, []map[string]any{event}, "event_id", "handoff")
	if err != nil {
		return err
	}
	if err := writeJSONAtomic(handoffPath, handoffs); err != nil {
		return err
	}
	return writeJSONAtomic(filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"), *queue)
}

func renderLeasedPacket(packet queuePacket) string {
	base := renderPacket(packet.PacketID, packet.AssignedPaths)
	resultPath := canonicalPendingResultPath(packet.PacketID)
	return base + fmt.Sprintf("\nActive lease:\n- worker_id: `%s`\n- attempt_id: `%s`\n- estimated_task_tokens: `%d`\n- effective_context_budget_tokens: `%d`\n- checkpoint_command: `specify-runtime cognition scan-checkpoint --packet-id %s --attempt-id %s --result %s --format json`\n- yield_command: `specify-runtime cognition scan-yield --packet-id %s --attempt-id %s --format json`\nSubmit cumulative checkpoints before the context safety threshold. The leader accepts a fully checkpointed attempt with the same packet and attempt identifiers.\n", packet.WorkerID, packet.AttemptID, packet.EstimatedTokens, packet.EffectiveContextBudget, packet.PacketID, packet.AttemptID, resultPath, packet.PacketID, packet.AttemptID)
}

func workerResultSkeleton(packetID string, attemptID string, assigned []string) map[string]any {
	return map[string]any{
		"protocol":       "map_scan_result.v2",
		"packet_id":      packetID,
		"attempt_id":     attemptID,
		"sequence":       1,
		"assigned_paths": append([]string{}, assigned...),
		"paths_read":     []string{},
		"ledger": map[string]any{
			"todo": append([]string{}, assigned...), "doing": []string{}, "done": []string{},
			"blocked": []string{}, "overflow": []string{},
		},
		"coverage": []map[string]any{}, "evidence": []map[string]any{}, "nodes": []map[string]any{},
		"edges": []map[string]any{}, "observations": []map[string]any{}, "claims": []map[string]any{},
		"confidence": "", "acceptance": "partial",
	}
}

func packetTaskPath(paths rt.Paths, packetID string) string {
	return filepath.Join(paths.RuntimeDir, "workbench", "scan-packets", packetID+".md")
}

func canonicalPacketTaskPath(packetID string) string {
	return ".specify/project-cognition/workbench/scan-packets/" + packetID + ".md"
}

func canonicalPendingResultPath(packetID string) string {
	return ".specify/project-cognition/workbench/pending-results/" + packetID + ".json"
}

func canonicalCheckpointPath(packetID string, attemptID string, sequence int) string {
	return filepath.ToSlash(filepath.Join(".specify", "project-cognition", "workbench", "checkpoints", packetID, attemptID, fmt.Sprintf("checkpoint-%04d.json", sequence)))
}

func nextRemainderPacketID(queue queueFile, parentID string) string {
	existing := map[string]bool{}
	for _, packet := range queue.Packets {
		existing[packet.PacketID] = true
	}
	for index := 1; ; index++ {
		candidate := fmt.Sprintf("%s-r%03d", parentID, index)
		if !existing[candidate] {
			return candidate
		}
	}
}

func orderedSubset(values []string, subset map[string]bool) []string {
	out := []string{}
	for _, value := range values {
		if subset[normalizePath(value)] {
			out = append(out, normalizePath(value))
		}
	}
	return out
}

func orderedDifference(values []string, excluded map[string]bool) []string {
	out := []string{}
	for _, value := range values {
		normalized := normalizePath(value)
		if !excluded[normalized] {
			out = append(out, normalized)
		}
	}
	return out
}

func setDifference(left map[string]bool, right map[string]bool) map[string]bool {
	out := map[string]bool{}
	for value := range left {
		if !right[value] {
			out[value] = true
		}
	}
	return out
}

func isSubset(left map[string]bool, right map[string]bool) bool {
	for value := range left {
		if !right[value] {
			return false
		}
	}
	return true
}

func sortedKeys(values map[string]bool) []string {
	out := make([]string, 0, len(values))
	for value := range values {
		out = append(out, value)
	}
	sort.Strings(out)
	return out
}
