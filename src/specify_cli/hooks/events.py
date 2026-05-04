"""Canonical hook event names for first-party workflow quality hooks."""

from __future__ import annotations


WORKFLOW_PREFLIGHT = "workflow.preflight"
WORKFLOW_STATE_VALIDATE = "workflow.state.validate"
WORKFLOW_ARTIFACTS_VALIDATE = "workflow.artifacts.validate"
WORKFLOW_GATE_VALIDATE = "workflow.gate.validate"
WORKFLOW_CHECKPOINT = "workflow.checkpoint"
WORKFLOW_CONTEXT_MONITOR = "workflow.context.monitor"
WORKFLOW_SESSION_STATE_VALIDATE = "workflow.session_state.validate"
WORKFLOW_STATUSLINE_RENDER = "workflow.statusline.render"
WORKFLOW_READ_GUARD_VALIDATE = "workflow.read_guard.validate"
WORKFLOW_PROMPT_GUARD_VALIDATE = "workflow.prompt_guard.validate"
WORKFLOW_BOUNDARY_VALIDATE = "workflow.boundary.validate"
WORKFLOW_PHASE_BOUNDARY_VALIDATE = "workflow.phase_boundary.validate"
WORKFLOW_COMMIT_VALIDATE = "workflow.commit.validate"
WORKFLOW_POLICY_EVALUATE = "workflow.policy.evaluate"
WORKFLOW_COMPACTION_BUILD = "workflow.compaction.build"
WORKFLOW_COMPACTION_READ = "workflow.compaction.read"
WORKFLOW_LEARNING_SIGNAL = "workflow.learning.signal"
WORKFLOW_LEARNING_REVIEW = "workflow.learning.review"
WORKFLOW_LEARNING_CAPTURE = "workflow.learning.capture"
WORKFLOW_LEARNING_INJECT = "workflow.learning.inject"
DELEGATION_PACKET_VALIDATE = "delegation.packet.validate"
DELEGATION_JOIN_VALIDATE = "delegation.join.validate"
PROJECT_MAP_MARK_DIRTY = "project_map.mark_dirty"  # manual dirty override/fallback
PROJECT_MAP_COMPLETE_REFRESH = "project_map.complete_refresh"  # successful-refresh finalizer


CANONICAL_HOOK_EVENTS = frozenset(
    {
        WORKFLOW_PREFLIGHT,
        WORKFLOW_STATE_VALIDATE,
        WORKFLOW_ARTIFACTS_VALIDATE,
        WORKFLOW_GATE_VALIDATE,
        WORKFLOW_CHECKPOINT,
        WORKFLOW_CONTEXT_MONITOR,
        WORKFLOW_SESSION_STATE_VALIDATE,
        WORKFLOW_STATUSLINE_RENDER,
        WORKFLOW_READ_GUARD_VALIDATE,
        WORKFLOW_PROMPT_GUARD_VALIDATE,
        WORKFLOW_BOUNDARY_VALIDATE,
        WORKFLOW_PHASE_BOUNDARY_VALIDATE,
        WORKFLOW_COMMIT_VALIDATE,
        WORKFLOW_POLICY_EVALUATE,
        WORKFLOW_COMPACTION_BUILD,
        WORKFLOW_COMPACTION_READ,
        WORKFLOW_LEARNING_SIGNAL,
        WORKFLOW_LEARNING_REVIEW,
        WORKFLOW_LEARNING_CAPTURE,
        WORKFLOW_LEARNING_INJECT,
        DELEGATION_PACKET_VALIDATE,
        DELEGATION_JOIN_VALIDATE,
        PROJECT_MAP_MARK_DIRTY,
        PROJECT_MAP_COMPLETE_REFRESH,
    }
)
