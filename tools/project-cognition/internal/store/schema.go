package store

const SchemaVersion = 5

const schemaSQL = `
CREATE TABLE IF NOT EXISTS metadata (
	key TEXT PRIMARY KEY,
	value_json TEXT NOT NULL,
	updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS generations (
	id TEXT PRIMARY KEY,
	sequence INTEGER NOT NULL,
	kind TEXT NOT NULL,
	state TEXT NOT NULL,
	source_commit TEXT NOT NULL,
	started_at TEXT NOT NULL,
	published_at TEXT NOT NULL,
	superseded_at TEXT NOT NULL,
	attrs_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_generations_state ON generations(state);

CREATE TABLE IF NOT EXISTS evidence (
	id TEXT PRIMARY KEY,
	generation_id TEXT NOT NULL REFERENCES generations(id) ON DELETE CASCADE,
	source_kind TEXT NOT NULL,
	source_path TEXT NOT NULL,
	commit_sha TEXT NOT NULL,
	span TEXT NOT NULL,
	extractor TEXT NOT NULL,
	content_hash TEXT NOT NULL,
	captured_at TEXT NOT NULL,
	attrs_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_evidence_source_path ON evidence(source_path);
CREATE INDEX IF NOT EXISTS idx_evidence_source_hash ON evidence(source_path, content_hash);
CREATE INDEX IF NOT EXISTS idx_evidence_commit ON evidence(commit_sha);

CREATE TABLE IF NOT EXISTS observations (
	id TEXT PRIMARY KEY,
	generation_id TEXT NOT NULL REFERENCES generations(id) ON DELETE CASCADE,
	observation_type TEXT NOT NULL,
	summary TEXT NOT NULL,
	attrs_json TEXT NOT NULL DEFAULT '{}',
	created_at TEXT NOT NULL,
	updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS observation_evidence (
	observation_id TEXT NOT NULL REFERENCES observations(id) ON DELETE CASCADE,
	evidence_id TEXT NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
	PRIMARY KEY(observation_id, evidence_id)
);

CREATE TABLE IF NOT EXISTS nodes (
	id TEXT PRIMARY KEY,
	generation_id TEXT NOT NULL REFERENCES generations(id) ON DELETE CASCADE,
	type TEXT NOT NULL,
	title TEXT NOT NULL,
	confidence TEXT NOT NULL,
	attrs_json TEXT NOT NULL DEFAULT '{}',
	created_at TEXT NOT NULL,
	updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_nodes_generation ON nodes(generation_id);
CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(type);

CREATE TABLE IF NOT EXISTS node_evidence (
	node_id TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
	evidence_id TEXT NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
	PRIMARY KEY(node_id, evidence_id)
);

CREATE TABLE IF NOT EXISTS edges (
	id TEXT PRIMARY KEY,
	generation_id TEXT NOT NULL REFERENCES generations(id) ON DELETE CASCADE,
	type TEXT NOT NULL,
	source_id TEXT NOT NULL,
	target_id TEXT NOT NULL,
	confidence TEXT NOT NULL,
	attrs_json TEXT NOT NULL DEFAULT '{}',
	created_at TEXT NOT NULL,
	updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_edges_generation ON edges(generation_id);
CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id);
CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id);
CREATE INDEX IF NOT EXISTS idx_edges_type ON edges(type);

CREATE TABLE IF NOT EXISTS edge_evidence (
	edge_id TEXT NOT NULL REFERENCES edges(id) ON DELETE CASCADE,
	evidence_id TEXT NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
	PRIMARY KEY(edge_id, evidence_id)
);

CREATE TABLE IF NOT EXISTS path_index (
	id TEXT PRIMARY KEY,
	generation_id TEXT NOT NULL REFERENCES generations(id) ON DELETE CASCADE,
	path TEXT NOT NULL,
	node_id TEXT NOT NULL,
	relation TEXT NOT NULL,
	confidence TEXT NOT NULL,
	evidence_id TEXT NOT NULL,
	updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_path_index_path ON path_index(path);
CREATE INDEX IF NOT EXISTS idx_path_index_node ON path_index(node_id);
CREATE INDEX IF NOT EXISTS idx_path_index_generation_path ON path_index(generation_id, path);

CREATE TABLE IF NOT EXISTS alias_index (
	id TEXT PRIMARY KEY,
	generation_id TEXT NOT NULL REFERENCES generations(id) ON DELETE CASCADE,
	alias TEXT NOT NULL,
	normalized_alias TEXT NOT NULL,
	target_type TEXT NOT NULL,
	target_id TEXT NOT NULL,
	language TEXT NOT NULL,
	source TEXT NOT NULL,
	confidence TEXT NOT NULL,
	evidence_id TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_alias_normalized ON alias_index(normalized_alias);
CREATE INDEX IF NOT EXISTS idx_alias_target ON alias_index(target_id);
CREATE INDEX IF NOT EXISTS idx_alias_generation_normalized ON alias_index(generation_id, normalized_alias);
CREATE UNIQUE INDEX IF NOT EXISTS idx_alias_identity ON alias_index(generation_id, target_type, target_id, normalized_alias, source);

CREATE TABLE IF NOT EXISTS updates (
	id TEXT PRIMARY KEY,
	generation_id TEXT NOT NULL REFERENCES generations(id) ON DELETE CASCADE,
	trigger TEXT NOT NULL,
	changed_paths_json TEXT NOT NULL,
	affected_nodes_json TEXT NOT NULL,
	affected_claims_json TEXT NOT NULL,
	affected_slices_json TEXT NOT NULL,
	result_state TEXT NOT NULL,
	completed_at TEXT NOT NULL,
	attrs_json TEXT NOT NULL DEFAULT '{}'
);
`

const schemaV5ClaimSQL = `
CREATE TABLE IF NOT EXISTS claims (
	id TEXT PRIMARY KEY,
	generation_id TEXT NOT NULL REFERENCES generations(id) ON DELETE CASCADE,
	node_id TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
	graph_claim_type TEXT NOT NULL,
	summary TEXT NOT NULL,
	state TEXT NOT NULL,
	prior_state TEXT NOT NULL,
	freshness TEXT NOT NULL,
	state_reason TEXT NOT NULL,
	revision INTEGER NOT NULL DEFAULT 1,
	attrs_json TEXT NOT NULL DEFAULT '{}',
	created_at TEXT NOT NULL,
	updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_claims_generation ON claims(generation_id);
CREATE INDEX IF NOT EXISTS idx_claims_node ON claims(node_id);
CREATE INDEX IF NOT EXISTS idx_claims_state ON claims(state, freshness);

CREATE TABLE IF NOT EXISTS claim_evidence (
	claim_id TEXT NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
	evidence_id TEXT NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
	role TEXT NOT NULL,
	reconciliation_id TEXT NOT NULL DEFAULT '',
	basis_state TEXT NOT NULL DEFAULT 'current',
	PRIMARY KEY(claim_id, evidence_id, role)
);
CREATE INDEX IF NOT EXISTS idx_claim_evidence_evidence ON claim_evidence(evidence_id);
CREATE INDEX IF NOT EXISTS idx_claim_evidence_current ON claim_evidence(claim_id, basis_state);

CREATE TABLE IF NOT EXISTS claim_verifications (
	id TEXT PRIMARY KEY,
	claim_id TEXT NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
	generation_id TEXT NOT NULL REFERENCES generations(id) ON DELETE CASCADE,
	result TEXT NOT NULL,
	command TEXT NOT NULL,
	evidence_id TEXT NOT NULL,
	observed_at TEXT NOT NULL,
	attrs_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_claim_verifications_claim ON claim_verifications(claim_id, observed_at);

CREATE TABLE IF NOT EXISTS claim_transitions (
	id TEXT PRIMARY KEY,
	claim_id TEXT NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
	generation_id TEXT NOT NULL REFERENCES generations(id) ON DELETE CASCADE,
	from_state TEXT NOT NULL,
	to_state TEXT NOT NULL,
	reason TEXT NOT NULL,
	evidence_id TEXT NOT NULL,
	occurred_at TEXT NOT NULL,
	attrs_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_claim_transitions_claim ON claim_transitions(claim_id, occurred_at);

CREATE TABLE IF NOT EXISTS claim_reconciliations (
	id TEXT PRIMARY KEY,
	generation_id TEXT NOT NULL REFERENCES generations(id) ON DELETE CASCADE,
	workflow TEXT NOT NULL,
	observed_at TEXT NOT NULL,
	packet_hash TEXT NOT NULL,
	result_state TEXT NOT NULL,
	attrs_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_claim_reconciliations_generation ON claim_reconciliations(generation_id, observed_at);
`

func RequiredTables() []string {
	return []string{
		"metadata",
		"generations",
		"evidence",
		"observations",
		"observation_evidence",
		"nodes",
		"node_evidence",
		"edges",
		"edge_evidence",
		"path_index",
		"alias_index",
		"claims",
		"claim_evidence",
		"claim_verifications",
		"claim_transitions",
		"claim_reconciliations",
		"updates",
	}
}

func RequiredTableColumns() map[string][]string {
	return map[string][]string{
		"metadata": {
			"key", "value_json", "updated_at",
		},
		"generations": {
			"id", "sequence", "kind", "state", "source_commit", "started_at", "published_at", "superseded_at", "attrs_json",
		},
		"evidence": {
			"id", "generation_id", "source_kind", "source_path", "commit_sha", "span", "extractor", "content_hash", "captured_at", "attrs_json",
		},
		"observations": {
			"id", "generation_id", "observation_type", "summary", "attrs_json", "created_at", "updated_at",
		},
		"observation_evidence": {
			"observation_id", "evidence_id",
		},
		"nodes": {
			"id", "generation_id", "type", "title", "confidence", "attrs_json", "created_at", "updated_at",
		},
		"node_evidence": {
			"node_id", "evidence_id",
		},
		"edges": {
			"id", "generation_id", "type", "source_id", "target_id", "confidence", "attrs_json", "created_at", "updated_at",
		},
		"edge_evidence": {
			"edge_id", "evidence_id",
		},
		"path_index": {
			"id", "generation_id", "path", "node_id", "relation", "confidence", "evidence_id", "updated_at",
		},
		"alias_index": {
			"id", "generation_id", "alias", "normalized_alias", "target_type", "target_id", "language", "source", "confidence", "evidence_id",
		},
		"claims": {
			"id", "generation_id", "node_id", "graph_claim_type", "summary", "state", "prior_state", "freshness", "state_reason", "revision", "attrs_json", "created_at", "updated_at",
		},
		"claim_evidence": {
			"claim_id", "evidence_id", "role", "reconciliation_id", "basis_state",
		},
		"claim_verifications": {
			"id", "claim_id", "generation_id", "result", "command", "evidence_id", "observed_at", "attrs_json",
		},
		"claim_transitions": {
			"id", "claim_id", "generation_id", "from_state", "to_state", "reason", "evidence_id", "occurred_at", "attrs_json",
		},
		"claim_reconciliations": {
			"id", "generation_id", "workflow", "observed_at", "packet_hash", "result_state", "attrs_json",
		},
		"updates": {
			"id", "generation_id", "trigger", "changed_paths_json", "affected_nodes_json", "affected_claims_json", "affected_slices_json", "result_state", "completed_at", "attrs_json",
		},
	}
}
