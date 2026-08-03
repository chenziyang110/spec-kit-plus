package runcontrol

const schemaVersion = 5

const workspaceAllocationSchemaSQL = `
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
`

const candidateIntegrationSchemaSQL = `
CREATE TABLE IF NOT EXISTS candidates (
    candidate_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL UNIQUE REFERENCES runs(run_id) ON DELETE RESTRICT,
    attempt_id TEXT NOT NULL UNIQUE REFERENCES attempts(attempt_id) ON DELETE RESTRICT,
    activity_id TEXT NOT NULL REFERENCES activities(activity_id) ON DELETE RESTRICT,
    workspace_id TEXT NOT NULL UNIQUE REFERENCES workspaces(workspace_id) ON DELETE RESTRICT,
    workspace_generation INTEGER NOT NULL CHECK (workspace_generation > 0),
    target_ref TEXT NOT NULL,
    base_commit TEXT NOT NULL,
    private_ref TEXT NOT NULL UNIQUE,
    head_commit TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('queued', 'integrating', 'integrated', 'conflicted')
    ),
    revision INTEGER NOT NULL CHECK (revision >= 1),
    created_at_ms INTEGER NOT NULL,
    updated_at_ms INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS candidates_target_queue
    ON candidates(target_ref, status, created_at_ms, candidate_id);

CREATE TABLE IF NOT EXISTS candidate_integrations (
    integration_id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL REFERENCES candidates(candidate_id) ON DELETE RESTRICT,
    target_ref TEXT NOT NULL,
    owner_epoch TEXT NOT NULL REFERENCES supervisor_instances(owner_epoch) ON DELETE RESTRICT,
    status TEXT NOT NULL CHECK (
        status IN ('prepared', 'executing', 'succeeded', 'conflicted', 'failed', 'outcome_unknown')
    ),
    target_before TEXT NOT NULL DEFAULT '',
    target_after TEXT NOT NULL DEFAULT '',
    reason TEXT NOT NULL DEFAULT '',
    revision INTEGER NOT NULL CHECK (revision >= 1),
    created_at_ms INTEGER NOT NULL,
    updated_at_ms INTEGER NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS candidate_integrations_one_live_per_target
    ON candidate_integrations(target_ref)
    WHERE status IN ('prepared', 'executing', 'outcome_unknown');

CREATE UNIQUE INDEX IF NOT EXISTS candidate_integrations_one_live_per_candidate
    ON candidate_integrations(candidate_id)
    WHERE status IN ('prepared', 'executing', 'outcome_unknown');

CREATE TABLE IF NOT EXISTS results (
    result_id TEXT PRIMARY KEY,
    integration_id TEXT NOT NULL UNIQUE REFERENCES candidate_integrations(integration_id) ON DELETE RESTRICT,
    candidate_id TEXT NOT NULL UNIQUE REFERENCES candidates(candidate_id) ON DELETE RESTRICT,
    run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE RESTRICT,
    target_ref TEXT NOT NULL,
    target_before TEXT NOT NULL,
    target_after TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('integrated', 'conflicted')),
    reason TEXT NOT NULL DEFAULT '',
    created_at_ms INTEGER NOT NULL
);
`

const schemaSQL = `
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

` + workspaceAllocationSchemaSQL + `

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

` + candidateIntegrationSchemaSQL + `

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
`
