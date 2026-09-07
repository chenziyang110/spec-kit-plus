package specvalidate

import (
	"bytes"
	"encoding/json"
	"fmt"
	"reflect"
)

// DiscussionCheckpointFields is the shared producer/consumer field inventory.
func DiscussionCheckpointFields() []string {
	return []string{
		"user_goal", "turn_class", "requirements_snapshot", "implementation_target",
		"source_evidence", "source_materials", "blocking_unknowns", "soft_unknowns",
		"conflicts", "downstream_instructions", "discussion_decision_digest", "must_preserve",
		"truth_pass_status", "verified_project_facts", "evidence_checked", "advice_confidence",
		"discussion_compass_status", "next_discussion_paths", "ui_discussion_status", "design_context",
		"artifact_refs", "confirmed_decisions", "changed_recommendations", "context_boundary",
		"verified_fact_refs", "open_assumptions", "open_questions", "current_recommendation",
		"allowed_actions", "next_gate", "current_decision_frame", "topic_ownership",
	}
}

// DiscussionSemanticSnapshot excludes lifecycle-only changes, so consuming a
// handoff does not invalidate its semantic identity while a new source does.
func DiscussionSemanticSnapshot(packet map[string]any) map[string]any {
	result := map[string]any{}
	for _, key := range DiscussionCheckpointFields() {
		switch key {
		case "allowed_actions", "lifecycle_phase", "next_gate", "persistence_mode", "turn_class":
			continue
		}
		if value, exists := packet[key]; exists {
			result[key] = value
		}
	}
	result["discussion_slug"] = packet["discussion_slug"]
	return result
}

// DiscussionSnapshotDigest hashes the same canonical JSON used by checkpoints.
func DiscussionSnapshotDigest(snapshot map[string]any) (string, error) {
	var content bytes.Buffer
	encoder := json.NewEncoder(&content)
	encoder.SetEscapeHTML(false)
	if err := encoder.Encode(snapshot); err != nil {
		return "", err
	}
	return coverageDigest(bytes.TrimSpace(content.Bytes())), nil
}

func validateCurrentDiscussionSnapshot(handoff, state map[string]any) error {
	packet, ok := state["turn_packet"].(map[string]any)
	checkpoint, checkpointOK := state["latest_checkpoint"].(map[string]any)
	if !ok || !checkpointOK {
		return fmt.Errorf("Discussion current semantic checkpoint is missing")
	}
	digest, err := DiscussionSnapshotDigest(DiscussionSemanticSnapshot(packet))
	if err != nil || checkpoint["snapshot_sha256"] != digest || handoff["discussion_snapshot_digest"] != digest {
		return fmt.Errorf("Discussion handoff does not match the current semantic checkpoint; unread or changed sources must return to Discussion")
	}
	if !reflect.DeepEqual(handoff["source_materials"], packet["source_materials"]) || !reflect.DeepEqual(handoff["agent_requirement_contract"], packet["requirements_snapshot"]) {
		return fmt.Errorf("Discussion source inventory or requirements differ from current checkpoint truth")
	}
	return nil
}
