-- Historical schema through v13, captured before source retirement.
-- Version markers let migration tests reconstruct supported older stores.
-- Keep this fixture independent from the production shared-board schema.

-- schema-version: 3
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS supervisor_instances (
    owner_epoch TEXT PRIMARY KEY,
    status TEXT NOT NULL CHECK (status IN ('active', 'stopped', 'superseded')),
    started_at_ms INTEGER NOT NULL,
    heartbeat_at_ms INTEGER NOT NULL,
    stopped_at_ms INTEGER
);

CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    subject_type TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    target_ref TEXT NOT NULL,
    intent_sha256 TEXT NOT NULL CHECK (
        length(intent_sha256) = 64 AND intent_sha256 NOT GLOB '*[^0-9a-f]*'
    ),
    owner_epoch TEXT NOT NULL REFERENCES supervisor_instances(owner_epoch) ON DELETE RESTRICT,
    status TEXT NOT NULL CHECK (
        status IN ('queued', 'allocating', 'ready', 'active', 'parked', 'interrupted', 'sealed', 'cancelled', 'failed')
    ),
    revision INTEGER NOT NULL CHECK (revision >= 1),
    current_fence INTEGER NOT NULL DEFAULT 0 CHECK (current_fence >= 0),
    created_at_ms INTEGER NOT NULL,
    updated_at_ms INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS activities (
    activity_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE RESTRICT,
    kind TEXT NOT NULL,
    ordinal INTEGER NOT NULL CHECK (ordinal > 0),
    input_sha256 TEXT NOT NULL DEFAULT '' CHECK (
        input_sha256 = '' OR (length(input_sha256) = 64 AND input_sha256 NOT GLOB '*[^0-9a-f]*')
    ),
    status TEXT NOT NULL CHECK (
        status IN ('planned', 'ready', 'active', 'blocked', 'interrupted', 'succeeded', 'cancelled', 'failed')
    ),
    revision INTEGER NOT NULL CHECK (revision >= 1),
    created_at_ms INTEGER NOT NULL,
    updated_at_ms INTEGER NOT NULL,
    UNIQUE (activity_id, run_id),
    UNIQUE (run_id, ordinal)
);

CREATE UNIQUE INDEX IF NOT EXISTS activities_one_open_per_run
    ON activities(run_id)
    WHERE status IN ('planned', 'ready', 'active', 'blocked', 'interrupted');

CREATE TABLE IF NOT EXISTS workspaces (
    workspace_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE RESTRICT,
    generation INTEGER NOT NULL CHECK (generation > 0),
    kind TEXT NOT NULL CHECK (kind IN ('git_worktree')),
    root_path TEXT NOT NULL,
    repo_common_dir TEXT NOT NULL,
    base_ref TEXT NOT NULL,
    base_commit TEXT NOT NULL,
    private_ref TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('allocating', 'ready', 'in_use', 'quarantined', 'sealed', 'released', 'failed')
    ),
    revision INTEGER NOT NULL CHECK (revision >= 1),
    created_at_ms INTEGER NOT NULL,
    updated_at_ms INTEGER NOT NULL,
    UNIQUE (workspace_id, run_id),
    UNIQUE (run_id, generation)
);

CREATE UNIQUE INDEX IF NOT EXISTS workspaces_one_usable_per_run
    ON workspaces(run_id)
    WHERE status IN ('allocating', 'ready', 'in_use');







CREATE TABLE IF NOT EXISTS attempts (
    attempt_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE RESTRICT,
    activity_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    workspace_generation INTEGER NOT NULL CHECK (workspace_generation > 0),
    status TEXT NOT NULL CHECK (
        status IN ('issued', 'active', 'sealing', 'finished', 'revoked', 'lost', 'failed')
    ),
    adapter_id TEXT NOT NULL,
    execution_mode TEXT NOT NULL CHECK (
        execution_mode IN ('managed', 'manual_attach', 'prompt_only')
    ),
    owner_epoch TEXT NOT NULL REFERENCES supervisor_instances(owner_epoch) ON DELETE RESTRICT,
    fence INTEGER NOT NULL CHECK (fence > 0),
    lease_until_ms INTEGER NOT NULL,
    heartbeat_at_ms INTEGER NOT NULL,
    revision INTEGER NOT NULL CHECK (revision >= 1),
    created_at_ms INTEGER NOT NULL,
    updated_at_ms INTEGER NOT NULL,
    UNIQUE (run_id, fence),
    UNIQUE (attempt_id, run_id, activity_id, workspace_id),
    FOREIGN KEY (activity_id, run_id) REFERENCES activities(activity_id, run_id) ON DELETE RESTRICT,
    FOREIGN KEY (workspace_id, run_id) REFERENCES workspaces(workspace_id, run_id) ON DELETE RESTRICT
);

CREATE UNIQUE INDEX IF NOT EXISTS attempts_one_live_per_run
    ON attempts(run_id)
    WHERE status IN ('issued', 'active', 'sealing');

CREATE INDEX IF NOT EXISTS attempts_lease_lookup
    ON attempts(status, lease_until_ms);















CREATE TABLE IF NOT EXISTS operations (
    operation_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    aggregate_type TEXT NOT NULL,
    aggregate_id TEXT NOT NULL,
    run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE RESTRICT,
    attempt_id TEXT NOT NULL,
    activity_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    owner_epoch TEXT NOT NULL REFERENCES supervisor_instances(owner_epoch) ON DELETE RESTRICT,
    fence INTEGER NOT NULL CHECK (fence > 0),
    run_revision INTEGER NOT NULL CHECK (run_revision >= 1),
    idempotency_key TEXT NOT NULL UNIQUE,
    request_sha256 TEXT NOT NULL CHECK (
        length(request_sha256) = 64 AND request_sha256 NOT GLOB '*[^0-9a-f]*'
    ),
    status TEXT NOT NULL CHECK (
        status IN ('prepared', 'executing', 'succeeded', 'failed', 'outcome_unknown')
    ),
    revision INTEGER NOT NULL CHECK (revision >= 1),
    created_at_ms INTEGER NOT NULL,
    updated_at_ms INTEGER NOT NULL,
    FOREIGN KEY (attempt_id, run_id, activity_id, workspace_id)
        REFERENCES attempts(attempt_id, run_id, activity_id, workspace_id) ON DELETE RESTRICT
);

CREATE UNIQUE INDEX IF NOT EXISTS operations_one_live_attempt_launch
    ON operations(attempt_id)
    WHERE kind = 'attempt.launch'
      AND status IN ('prepared', 'executing', 'succeeded', 'outcome_unknown');

CREATE TABLE IF NOT EXISTS events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    aggregate_type TEXT NOT NULL,
    aggregate_id TEXT NOT NULL,
    aggregate_revision INTEGER NOT NULL CHECK (aggregate_revision >= 1),
    event_type TEXT NOT NULL,
    reason TEXT NOT NULL DEFAULT '',
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at_ms INTEGER NOT NULL,
    UNIQUE (aggregate_type, aggregate_id, aggregate_revision)
);

CREATE INDEX IF NOT EXISTS events_aggregate_order
    ON events(aggregate_type, aggregate_id, aggregate_revision);

-- schema-version: 4
CREATE TABLE IF NOT EXISTS workspace_allocations (
    allocation_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE RESTRICT,
    workspace_id TEXT NOT NULL,
    workspace_generation INTEGER NOT NULL CHECK (workspace_generation > 0),
    owner_epoch TEXT NOT NULL REFERENCES supervisor_instances(owner_epoch) ON DELETE RESTRICT,
    run_revision INTEGER NOT NULL CHECK (run_revision >= 1),
    workspace_revision INTEGER NOT NULL CHECK (workspace_revision >= 1),
    idempotency_key TEXT NOT NULL UNIQUE,
    request_sha256 TEXT NOT NULL CHECK (
        length(request_sha256) = 64 AND request_sha256 NOT GLOB '*[^0-9a-f]*'
    ),
    status TEXT NOT NULL CHECK (
        status IN ('prepared', 'executing', 'succeeded', 'failed', 'outcome_unknown')
    ),
    reason TEXT NOT NULL DEFAULT '',
    revision INTEGER NOT NULL CHECK (revision >= 1),
    created_at_ms INTEGER NOT NULL,
    updated_at_ms INTEGER NOT NULL,
    UNIQUE (workspace_id),
    UNIQUE (allocation_id, run_id, workspace_id),
    FOREIGN KEY (workspace_id, run_id) REFERENCES workspaces(workspace_id, run_id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS workspace_allocations_recovery
    ON workspace_allocations(owner_epoch, status, run_id);

-- schema-version: 6
CREATE TABLE IF NOT EXISTS snapshots (
    snapshot_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL UNIQUE,
    attempt_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    workspace_generation INTEGER NOT NULL CHECK (workspace_generation > 0),
    target_ref TEXT NOT NULL,
    source_root TEXT NOT NULL,
    workspace_root TEXT NOT NULL,
    repo_common_dir TEXT NOT NULL,
    private_ref TEXT NOT NULL,
    base_commit TEXT NOT NULL,
    base_tree TEXT NOT NULL,
    overlay_manifest_sha256 TEXT NOT NULL CHECK (
        length(overlay_manifest_sha256) = 64 AND overlay_manifest_sha256 NOT GLOB '*[^0-9a-f]*'
    ),
    input_manifest_sha256 TEXT NOT NULL CHECK (
        length(input_manifest_sha256) = 64 AND input_manifest_sha256 NOT GLOB '*[^0-9a-f]*'
    ),
    default_delivery_policy TEXT NOT NULL CHECK (default_delivery_policy IN ('context_only', 'restorable')),
    entry_count INTEGER NOT NULL CHECK (entry_count >= 0),
    created_at_ms INTEGER NOT NULL,
    updated_at_ms INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS snapshot_entries (
    entry_id TEXT PRIMARY KEY,
    snapshot_id TEXT NOT NULL REFERENCES snapshots(snapshot_id) ON DELETE CASCADE,
    ordinal INTEGER NOT NULL CHECK (ordinal > 0),
    relative_path TEXT NOT NULL,
    provenance TEXT NOT NULL CHECK (provenance IN ('staged', 'unstaged', 'untracked')),
    kind TEXT NOT NULL CHECK (kind IN ('file', 'deleted')),
    file_mode INTEGER NOT NULL CHECK (file_mode >= 0),
    blob_sha256 TEXT NOT NULL CHECK (
        blob_sha256 = '' OR (length(blob_sha256) = 64 AND blob_sha256 NOT GLOB '*[^0-9a-f]*')
    ),
    object_path TEXT NOT NULL,
    size_bytes INTEGER NOT NULL CHECK (size_bytes >= 0),
    delivery_policy TEXT NOT NULL CHECK (delivery_policy IN ('context_only', 'restorable')),
    created_at_ms INTEGER NOT NULL,
    UNIQUE (snapshot_id, ordinal),
    UNIQUE (snapshot_id, provenance, relative_path)
);

CREATE INDEX IF NOT EXISTS snapshot_entries_snapshot_order
    ON snapshot_entries(snapshot_id, ordinal);
CREATE TABLE IF NOT EXISTS resource_claims (
    claim_id TEXT PRIMARY KEY,
    resource_type TEXT NOT NULL,
    resource_key TEXT NOT NULL,
    run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE RESTRICT,
    attempt_id TEXT NOT NULL REFERENCES attempts(attempt_id) ON DELETE RESTRICT,
    activity_id TEXT NOT NULL REFERENCES activities(activity_id) ON DELETE RESTRICT,
    workspace_id TEXT NOT NULL REFERENCES workspaces(workspace_id) ON DELETE RESTRICT,
    owner_epoch TEXT NOT NULL REFERENCES supervisor_instances(owner_epoch) ON DELETE RESTRICT,
    fence INTEGER NOT NULL CHECK (fence > 0),
    mode TEXT NOT NULL CHECK (mode IN ('shared', 'exclusive')),
    status TEXT NOT NULL CHECK (status IN ('active', 'released')),
    reason TEXT NOT NULL DEFAULT '',
    binding_json TEXT NOT NULL DEFAULT '{}',
    revision INTEGER NOT NULL CHECK (revision >= 1),
    created_at_ms INTEGER NOT NULL,
    updated_at_ms INTEGER NOT NULL,
    lease_until_ms INTEGER NOT NULL,
    released_at_ms INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS resource_claims_attempt_lookup
    ON resource_claims(attempt_id, status, resource_type, resource_key, created_at_ms, claim_id);

CREATE INDEX IF NOT EXISTS resource_claims_resource_lookup
    ON resource_claims(resource_type, resource_key, status, mode, created_at_ms, claim_id);

-- schema-version: 7
CREATE TABLE IF NOT EXISTS run_results (
    result_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE RESTRICT,
    result_revision INTEGER NOT NULL CHECK (result_revision > 0),
    attempt_id TEXT NOT NULL UNIQUE REFERENCES attempts(attempt_id) ON DELETE RESTRICT,
    activity_id TEXT NOT NULL REFERENCES activities(activity_id) ON DELETE RESTRICT,
    workspace_id TEXT NOT NULL REFERENCES workspaces(workspace_id) ON DELETE RESTRICT,
    workspace_generation INTEGER NOT NULL CHECK (workspace_generation > 0),
    fence INTEGER NOT NULL CHECK (fence > 0),
    snapshot_id TEXT NOT NULL REFERENCES snapshots(snapshot_id) ON DELETE RESTRICT,
    target_ref TEXT NOT NULL,
    base_commit_oid TEXT NOT NULL,
    result_tree_oid TEXT NOT NULL,
    result_commit_oid TEXT NOT NULL,
    hidden_ref TEXT NOT NULL UNIQUE,
    manifest_sha256 TEXT NOT NULL CHECK (
        length(manifest_sha256) = 64 AND manifest_sha256 NOT GLOB '*[^0-9a-f]*'
    ),
    workspace_attestation_sha256 TEXT NOT NULL CHECK (
        length(workspace_attestation_sha256) = 64 AND workspace_attestation_sha256 NOT GLOB '*[^0-9a-f]*'
    ),
    resource_attestation_sha256 TEXT NOT NULL CHECK (
        length(resource_attestation_sha256) = 64 AND resource_attestation_sha256 NOT GLOB '*[^0-9a-f]*'
    ),
    eligibility TEXT NOT NULL CHECK (
        eligibility IN ('ready', 'blocked', 'failed', 'overlay_dependent', 'requires_effect_approval')
    ),
    validation_evidence_json TEXT NOT NULL DEFAULT '[]',
    worker_result_digests_json TEXT NOT NULL DEFAULT '[]',
    external_effects_json TEXT NOT NULL DEFAULT '[]',
    created_at_ms INTEGER NOT NULL,
    UNIQUE (run_id, result_revision)
);

CREATE INDEX IF NOT EXISTS run_results_run_history
    ON run_results(run_id, result_revision, created_at_ms);

CREATE INDEX IF NOT EXISTS run_results_ready_queue
    ON run_results(target_ref, eligibility, created_at_ms, result_id);

CREATE TABLE IF NOT EXISTS run_result_paths (
    result_id TEXT NOT NULL REFERENCES run_results(result_id) ON DELETE RESTRICT,
    ordinal INTEGER NOT NULL CHECK (ordinal > 0),
    relative_path TEXT NOT NULL,
    PRIMARY KEY (result_id, ordinal),
    UNIQUE (result_id, relative_path)
);

CREATE TABLE IF NOT EXISTS run_reopen_intents (
    run_id TEXT PRIMARY KEY REFERENCES runs(run_id) ON DELETE RESTRICT,
    basis_result_id TEXT NOT NULL REFERENCES run_results(result_id) ON DELETE RESTRICT,
    new_result_id TEXT REFERENCES run_results(result_id) ON DELETE RESTRICT,
    reason TEXT NOT NULL,
    created_at_ms INTEGER NOT NULL,
    consumed_at_ms INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS result_supersessions (
    old_result_id TEXT PRIMARY KEY REFERENCES run_results(result_id) ON DELETE RESTRICT,
    new_result_id TEXT NOT NULL UNIQUE REFERENCES run_results(result_id) ON DELETE RESTRICT,
    run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE RESTRICT,
    reason TEXT NOT NULL,
    created_at_ms INTEGER NOT NULL
);

-- schema-version: 8
CREATE TABLE IF NOT EXISTS result_dependencies (
    dependency_id TEXT PRIMARY KEY,
    result_id TEXT NOT NULL REFERENCES run_results(result_id) ON DELETE RESTRICT,
    depends_on_result_id TEXT NOT NULL REFERENCES run_results(result_id) ON DELETE RESTRICT,
    kind TEXT NOT NULL CHECK (kind IN ('requires', 'after', 'conflicts_with')),
    reason TEXT NOT NULL,
    created_at_ms INTEGER NOT NULL,
    UNIQUE (result_id, depends_on_result_id, kind),
    CHECK (result_id <> depends_on_result_id)
);

CREATE INDEX IF NOT EXISTS result_dependencies_result
    ON result_dependencies(result_id, kind, depends_on_result_id);

CREATE TABLE IF NOT EXISTS candidate_builds (
    build_id TEXT PRIMARY KEY,
    target_ref TEXT NOT NULL,
    expected_target_oid TEXT NOT NULL,
    requested_results_sha256 TEXT NOT NULL CHECK (
        length(requested_results_sha256) = 64 AND requested_results_sha256 NOT GLOB '*[^0-9a-f]*'
    ),
    workspace_root TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('prepared', 'executing', 'succeeded', 'conflicted', 'stale', 'failed')),
    reason TEXT NOT NULL DEFAULT '',
    created_at_ms INTEGER NOT NULL,
    updated_at_ms INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS frozen_candidates (
    candidate_id TEXT PRIMARY KEY,
    build_id TEXT NOT NULL UNIQUE REFERENCES candidate_builds(build_id) ON DELETE RESTRICT,
    target_ref TEXT NOT NULL,
    expected_target_oid TEXT NOT NULL,
    tree_oid TEXT NOT NULL,
    commit_oid TEXT NOT NULL,
    hidden_ref TEXT NOT NULL UNIQUE,
    manifest_sha256 TEXT NOT NULL CHECK (
        length(manifest_sha256) = 64 AND manifest_sha256 NOT GLOB '*[^0-9a-f]*'
    ),
    status TEXT NOT NULL CHECK (status IN ('succeeded', 'stale')),
    created_at_ms INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS frozen_candidate_members (
    candidate_id TEXT NOT NULL REFERENCES frozen_candidates(candidate_id) ON DELETE RESTRICT,
    ordinal INTEGER NOT NULL CHECK (ordinal > 0),
    result_id TEXT NOT NULL REFERENCES run_results(result_id) ON DELETE RESTRICT,
    result_manifest_sha256 TEXT NOT NULL,
    PRIMARY KEY (candidate_id, ordinal),
    UNIQUE (candidate_id, result_id)
);

-- schema-version: 9
CREATE TABLE IF NOT EXISTS candidate_reviews (
    review_id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL REFERENCES frozen_candidates(candidate_id) ON DELETE RESTRICT,
    candidate_manifest_sha256 TEXT NOT NULL,
    candidate_tree_oid TEXT NOT NULL,
    candidate_commit_oid TEXT NOT NULL,
    reviewer TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('passed', 'failed')),
    evidence_digest TEXT NOT NULL CHECK (
        length(evidence_digest) = 64 AND evidence_digest NOT GLOB '*[^0-9a-f]*'
    ),
    review_digest TEXT NOT NULL UNIQUE CHECK (
        length(review_digest) = 64 AND review_digest NOT GLOB '*[^0-9a-f]*'
    ),
    evidence_json TEXT NOT NULL,
    created_at_ms INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS candidate_reviews_latest
    ON candidate_reviews(candidate_id, created_at_ms, review_id);

CREATE TABLE IF NOT EXISTS candidate_acceptances (
    acceptance_id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL REFERENCES frozen_candidates(candidate_id) ON DELETE RESTRICT,
    review_id TEXT NOT NULL REFERENCES candidate_reviews(review_id) ON DELETE RESTRICT,
    review_digest TEXT NOT NULL,
    evidence_digest TEXT NOT NULL,
    decision TEXT NOT NULL CHECK (decision IN ('accepted', 'rejected')),
    actor TEXT NOT NULL,
    acceptance_digest TEXT NOT NULL UNIQUE CHECK (
        length(acceptance_digest) = 64 AND acceptance_digest NOT GLOB '*[^0-9a-f]*'
    ),
    created_at_ms INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS candidate_acceptances_latest
    ON candidate_acceptances(candidate_id, created_at_ms, acceptance_id);

CREATE TABLE IF NOT EXISTS candidate_publications (
    publication_id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL REFERENCES frozen_candidates(candidate_id) ON DELETE RESTRICT,
    acceptance_id TEXT NOT NULL REFERENCES candidate_acceptances(acceptance_id) ON DELETE RESTRICT,
    target_ref TEXT NOT NULL,
    target_before TEXT NOT NULL,
    target_after TEXT NOT NULL,
    expected_index_tree_oid TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('prepared', 'executing', 'succeeded', 'stale', 'outcome_unknown')),
    publication_digest TEXT NOT NULL UNIQUE CHECK (
        length(publication_digest) = 64 AND publication_digest NOT GLOB '*[^0-9a-f]*'
    ),
    reason TEXT NOT NULL DEFAULT '',
    created_at_ms INTEGER NOT NULL,
    updated_at_ms INTEGER NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS candidate_publications_one_success
    ON candidate_publications(candidate_id) WHERE status = 'succeeded';

CREATE TABLE IF NOT EXISTS candidate_syncs (
    sync_id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL REFERENCES frozen_candidates(candidate_id) ON DELETE RESTRICT,
    publication_id TEXT NOT NULL REFERENCES candidate_publications(publication_id) ON DELETE RESTRICT,
    worktree_root TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('succeeded')),
    sync_digest TEXT NOT NULL UNIQUE,
    created_at_ms INTEGER NOT NULL,
    UNIQUE (publication_id, worktree_root)
);

-- schema-version: 10
CREATE TABLE IF NOT EXISTS adapter_capabilities (
    adapter_id TEXT PRIMARY KEY,
    launch_mode TEXT NOT NULL CHECK (launch_mode IN ('managed', 'manual_attach', 'prompt_only')),
    enforces_cwd INTEGER NOT NULL CHECK (enforces_cwd IN (0, 1)),
    enforces_workspace_root INTEGER NOT NULL CHECK (enforces_workspace_root IN (0, 1)),
    enforces_writable_roots INTEGER NOT NULL CHECK (enforces_writable_roots IN (0, 1)),
    controls_process_tree INTEGER NOT NULL CHECK (controls_process_tree IN (0, 1)),
    supports_heartbeat INTEGER NOT NULL CHECK (supports_heartbeat IN (0, 1)),
    supports_cancellation INTEGER NOT NULL CHECK (supports_cancellation IN (0, 1)),
    supports_structured_result INTEGER NOT NULL CHECK (supports_structured_result IN (0, 1)),
    capability_digest TEXT NOT NULL UNIQUE CHECK (
        length(capability_digest) = 64 AND capability_digest NOT GLOB '*[^0-9a-f]*'
    ),
    created_at_ms INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS workspace_attestations (
    attestation_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL UNIQUE REFERENCES workspaces(workspace_id) ON DELETE RESTRICT,
    run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE RESTRICT,
    workspace_generation INTEGER NOT NULL CHECK (workspace_generation > 0),
    canonical_root TEXT NOT NULL,
    repo_common_dir TEXT NOT NULL,
    git_admin_dir TEXT NOT NULL,
    base_ref TEXT NOT NULL,
    base_commit_oid TEXT NOT NULL,
    private_ref TEXT NOT NULL,
    snapshot_id TEXT NOT NULL REFERENCES snapshots(snapshot_id) ON DELETE RESTRICT,
    overlay_manifest_sha256 TEXT NOT NULL,
    writable_roots_json TEXT NOT NULL,
    attestation_digest TEXT NOT NULL UNIQUE CHECK (
        length(attestation_digest) = 64 AND attestation_digest NOT GLOB '*[^0-9a-f]*'
    ),
    created_at_ms INTEGER NOT NULL
);

-- schema-version: 11
CREATE TABLE IF NOT EXISTS workspace_routes (
    workspace_id TEXT PRIMARY KEY REFERENCES workspaces(workspace_id) ON DELETE RESTRICT,
    mode TEXT NOT NULL CHECK (mode IN ('primary', 'isolated')),
    source_run_id TEXT REFERENCES runs(run_id) ON DELETE RESTRICT,
    created_at_ms INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS workspace_routes_source_run
    ON workspace_routes(source_run_id, mode, workspace_id);

CREATE TABLE IF NOT EXISTS primary_workspace_slots (
    slot_id INTEGER PRIMARY KEY CHECK (slot_id = 1),
    run_id TEXT NOT NULL UNIQUE REFERENCES runs(run_id) ON DELETE RESTRICT,
    owner_epoch TEXT NOT NULL REFERENCES supervisor_instances(owner_epoch) ON DELETE RESTRICT,
    root_path TEXT NOT NULL,
    acquired_at_ms INTEGER NOT NULL
);

-- schema-version: 12
CREATE TABLE IF NOT EXISTS work_items (
    work_id TEXT PRIMARY KEY,
    parent_work_id TEXT NOT NULL DEFAULT '',
    run_id TEXT NOT NULL DEFAULT '',
    task_ref TEXT NOT NULL DEFAULT '',
    summary TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    adapter_id TEXT NOT NULL,
    workspace_root TEXT NOT NULL,
    base_commit TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL CHECK (
        status IN ('active', 'blocked', 'interrupted', 'completed', 'abandoned')
    ),
    next_action TEXT NOT NULL DEFAULT '',
    last_reason TEXT NOT NULL DEFAULT '',
    fence INTEGER NOT NULL CHECK (fence > 0),
    revision INTEGER NOT NULL CHECK (revision > 0),
    lease_until_ms INTEGER NOT NULL,
    heartbeat_at_ms INTEGER NOT NULL,
    recovery_hold INTEGER NOT NULL DEFAULT 0 CHECK (recovery_hold IN (0, 1)),
    observed_paths_json TEXT NOT NULL DEFAULT '[]',
    created_at_ms INTEGER NOT NULL,
    updated_at_ms INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS work_items_status_lease
    ON work_items(status, lease_until_ms, updated_at_ms, work_id);

CREATE TABLE IF NOT EXISTS write_intents (
    intent_id TEXT PRIMARY KEY,
    work_id TEXT NOT NULL REFERENCES work_items(work_id) ON DELETE RESTRICT,
    path TEXT NOT NULL,
    path_key TEXT NOT NULL,
    operation TEXT NOT NULL CHECK (operation IN ('create', 'modify', 'delete', 'rename')),
    reason TEXT NOT NULL DEFAULT '',
    confidence TEXT NOT NULL CHECK (confidence IN ('candidate', 'confirmed')),
    status TEXT NOT NULL CHECK (status IN ('active', 'recovery', 'released')),
    revision INTEGER NOT NULL CHECK (revision > 0),
    created_at_ms INTEGER NOT NULL,
    updated_at_ms INTEGER NOT NULL,
    released_at_ms INTEGER NOT NULL DEFAULT 0,
    UNIQUE (work_id, path_key)
);

CREATE INDEX IF NOT EXISTS write_intents_conflict_lookup
    ON write_intents(confidence, status, path_key, work_id);

CREATE INDEX IF NOT EXISTS write_intents_work_history
    ON write_intents(work_id, created_at_ms, intent_id);

-- schema-version: 13
CREATE TABLE IF NOT EXISTS execution_activities (
    activity_id TEXT PRIMARY KEY,
    work_id TEXT NOT NULL UNIQUE REFERENCES work_items(work_id) ON DELETE RESTRICT,
    workflow TEXT NOT NULL CHECK (workflow IN ('fast', 'debug', 'implement', 'quick')),
    subject_id TEXT NOT NULL,
    item_id TEXT NOT NULL DEFAULT '',
    task_ref TEXT NOT NULL,
    source_ref TEXT NOT NULL DEFAULT '',
    title TEXT NOT NULL,
    phase TEXT NOT NULL CHECK (
        phase IN ('announced', 'selected', 'claimed', 'executing', 'validating',
                  'blocked', 'interrupted', 'completed', 'abandoned')
    ),
    baseline_json TEXT NOT NULL DEFAULT '{}',
    guarded_overview_revision INTEGER NOT NULL DEFAULT 0 CHECK (guarded_overview_revision >= 0),
    guarded_overview_sha256 TEXT NOT NULL DEFAULT '' CHECK (
        guarded_overview_sha256 = '' OR (
            length(guarded_overview_sha256) = 64 AND
            guarded_overview_sha256 NOT GLOB '*[^0-9a-f]*'
        )
    ),
    validation_json TEXT NOT NULL DEFAULT '[]',
    completion_sha256 TEXT NOT NULL DEFAULT '' CHECK (
        completion_sha256 = '' OR (
            length(completion_sha256) = 64 AND
            completion_sha256 NOT GLOB '*[^0-9a-f]*'
        )
    ),
    revision INTEGER NOT NULL CHECK (revision > 0),
    completed_at_ms INTEGER NOT NULL DEFAULT 0,
    created_at_ms INTEGER NOT NULL,
    updated_at_ms INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS execution_activities_open_lookup
    ON execution_activities(phase, workflow, subject_id, item_id, updated_at_ms, activity_id);

CREATE INDEX IF NOT EXISTS execution_activities_task_lookup
    ON execution_activities(task_ref, phase, activity_id);

CREATE TABLE IF NOT EXISTS execution_resource_intents (
    resource_intent_id TEXT PRIMARY KEY,
    activity_id TEXT NOT NULL REFERENCES execution_activities(activity_id) ON DELETE RESTRICT,
    work_id TEXT NOT NULL REFERENCES work_items(work_id) ON DELETE RESTRICT,
    resource_type TEXT NOT NULL,
    resource_key TEXT NOT NULL,
    resource_key_normalized TEXT NOT NULL,
    mode TEXT NOT NULL CHECK (mode IN ('shared', 'exclusive')),
    confidence TEXT NOT NULL CHECK (confidence IN ('candidate', 'confirmed')),
    status TEXT NOT NULL CHECK (status IN ('active', 'recovery', 'released')),
    reason TEXT NOT NULL DEFAULT '',
    revision INTEGER NOT NULL CHECK (revision > 0),
    created_at_ms INTEGER NOT NULL,
    updated_at_ms INTEGER NOT NULL,
    released_at_ms INTEGER NOT NULL DEFAULT 0,
    UNIQUE (activity_id, resource_type, resource_key_normalized)
);

CREATE INDEX IF NOT EXISTS execution_resource_conflict_lookup
    ON execution_resource_intents(
        resource_type, resource_key_normalized, confidence, status, mode, activity_id
    );

CREATE INDEX IF NOT EXISTS execution_resource_activity_history
    ON execution_resource_intents(activity_id, created_at_ms, resource_intent_id);
