package runcontrol

const schemaVersion = 3

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
