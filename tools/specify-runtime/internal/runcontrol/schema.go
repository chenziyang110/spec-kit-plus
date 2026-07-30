package runcontrol

const schemaVersion = 1

const schemaSQL = `
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS supervisor_instances (
    owner_epoch TEXT PRIMARY KEY,
    status TEXT NOT NULL,
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
    intent_sha256 TEXT NOT NULL,
    status TEXT NOT NULL,
    revision INTEGER NOT NULL CHECK (revision >= 1),
    current_fence INTEGER NOT NULL DEFAULT 0 CHECK (current_fence >= 0),
    created_at_ms INTEGER NOT NULL,
    updated_at_ms INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS attempts (
    attempt_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE RESTRICT,
    status TEXT NOT NULL,
    adapter_id TEXT NOT NULL,
    execution_mode TEXT NOT NULL,
    owner_epoch TEXT NOT NULL REFERENCES supervisor_instances(owner_epoch) ON DELETE RESTRICT,
    fence INTEGER NOT NULL CHECK (fence > 0),
    lease_until_ms INTEGER NOT NULL,
    heartbeat_at_ms INTEGER NOT NULL,
    revision INTEGER NOT NULL CHECK (revision >= 1),
    created_at_ms INTEGER NOT NULL,
    updated_at_ms INTEGER NOT NULL
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
    idempotency_key TEXT NOT NULL UNIQUE,
    request_sha256 TEXT NOT NULL,
    status TEXT NOT NULL,
    revision INTEGER NOT NULL CHECK (revision >= 1),
    created_at_ms INTEGER NOT NULL,
    updated_at_ms INTEGER NOT NULL
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
