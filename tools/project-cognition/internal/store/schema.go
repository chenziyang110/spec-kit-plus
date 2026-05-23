package store

const SchemaVersion = 1

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

CREATE TABLE IF NOT EXISTS claims (
	id TEXT PRIMARY KEY,
	generation_id TEXT NOT NULL REFERENCES generations(id) ON DELETE CASCADE,
	subject_ref TEXT NOT NULL,
	predicate TEXT NOT NULL,
	object_ref TEXT NOT NULL,
	object_value TEXT NOT NULL,
	truth_layer TEXT NOT NULL,
	confidence TEXT NOT NULL,
	status TEXT NOT NULL,
	last_validated_at TEXT NOT NULL,
	attrs_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_claims_subject ON claims(subject_ref);
CREATE INDEX IF NOT EXISTS idx_claims_predicate ON claims(predicate);
CREATE INDEX IF NOT EXISTS idx_claims_status ON claims(status);

CREATE TABLE IF NOT EXISTS claim_evidence (
	claim_id TEXT NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
	evidence_id TEXT NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
	PRIMARY KEY(claim_id, evidence_id)
);

CREATE TABLE IF NOT EXISTS conflicts (
	id TEXT PRIMARY KEY,
	generation_id TEXT NOT NULL REFERENCES generations(id) ON DELETE CASCADE,
	subject_ref TEXT NOT NULL,
	conflict_type TEXT NOT NULL,
	impact_scope TEXT NOT NULL,
	agent_behavior_rule TEXT NOT NULL,
	resolution_status TEXT NOT NULL,
	attrs_json TEXT NOT NULL DEFAULT '{}',
	updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_conflicts_subject ON conflicts(subject_ref);
CREATE INDEX IF NOT EXISTS idx_conflicts_status ON conflicts(resolution_status);

CREATE TABLE IF NOT EXISTS conflict_claims (
	conflict_id TEXT NOT NULL REFERENCES conflicts(id) ON DELETE CASCADE,
	claim_id TEXT NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
	PRIMARY KEY(conflict_id, claim_id)
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

CREATE TABLE IF NOT EXISTS symbol_index (
	id TEXT PRIMARY KEY,
	generation_id TEXT NOT NULL REFERENCES generations(id) ON DELETE CASCADE,
	symbol_name TEXT NOT NULL,
	normalized_symbol TEXT NOT NULL,
	node_id TEXT NOT NULL,
	path TEXT NOT NULL,
	relation TEXT NOT NULL,
	evidence_id TEXT NOT NULL,
	confidence TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_symbol_normalized ON symbol_index(normalized_symbol);
CREATE INDEX IF NOT EXISTS idx_symbol_generation_normalized ON symbol_index(generation_id, normalized_symbol);

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

CREATE TABLE IF NOT EXISTS entrypoint_index (
	id TEXT PRIMARY KEY,
	generation_id TEXT NOT NULL REFERENCES generations(id) ON DELETE CASCADE,
	entrypoint_key TEXT NOT NULL,
	entrypoint_type TEXT NOT NULL,
	node_id TEXT NOT NULL,
	capability_id TEXT NOT NULL,
	path TEXT NOT NULL,
	evidence_id TEXT NOT NULL,
	confidence TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_entrypoint_key ON entrypoint_index(entrypoint_key);
CREATE INDEX IF NOT EXISTS idx_entrypoint_capability ON entrypoint_index(capability_id);

CREATE TABLE IF NOT EXISTS test_index (
	id TEXT PRIMARY KEY,
	generation_id TEXT NOT NULL REFERENCES generations(id) ON DELETE CASCADE,
	test_path TEXT NOT NULL,
	test_name TEXT NOT NULL,
	node_id TEXT NOT NULL,
	capability_id TEXT NOT NULL,
	verification_node_id TEXT NOT NULL,
	evidence_id TEXT NOT NULL,
	confidence TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_test_path ON test_index(test_path);
CREATE INDEX IF NOT EXISTS idx_test_capability ON test_index(capability_id);

CREATE TABLE IF NOT EXISTS slice_members (
	id TEXT PRIMARY KEY,
	generation_id TEXT NOT NULL REFERENCES generations(id) ON DELETE CASCADE,
	slice_id TEXT NOT NULL,
	object_type TEXT NOT NULL,
	object_id TEXT NOT NULL,
	rank INTEGER NOT NULL,
	reason TEXT NOT NULL,
	updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_slice_members_slice ON slice_members(slice_id);
CREATE INDEX IF NOT EXISTS idx_slice_members_generation_slice ON slice_members(generation_id, slice_id);

CREATE TABLE IF NOT EXISTS query_examples (
	id TEXT PRIMARY KEY,
	generation_id TEXT NOT NULL REFERENCES generations(id) ON DELETE CASCADE,
	query_text TEXT NOT NULL,
	intent TEXT NOT NULL,
	expected_target_type TEXT NOT NULL,
	expected_target_id TEXT NOT NULL,
	language TEXT NOT NULL,
	source TEXT NOT NULL,
	created_at TEXT NOT NULL
);

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

CREATE VIRTUAL TABLE IF NOT EXISTS claim_fts USING fts5(claim_id, subject_ref, predicate, object_text, content);
CREATE VIRTUAL TABLE IF NOT EXISTS observation_fts USING fts5(observation_id, observation_type, summary, content);
CREATE VIRTUAL TABLE IF NOT EXISTS alias_fts USING fts5(alias_id, alias, normalized_alias, target_id, content);
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
		"claims",
		"claim_evidence",
		"conflicts",
		"conflict_claims",
		"path_index",
		"symbol_index",
		"alias_index",
		"entrypoint_index",
		"test_index",
		"slice_members",
		"query_examples",
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
		"claims": {
			"id", "generation_id", "subject_ref", "predicate", "object_ref", "object_value", "truth_layer", "confidence", "status", "last_validated_at", "attrs_json",
		},
		"claim_evidence": {
			"claim_id", "evidence_id",
		},
		"conflicts": {
			"id", "generation_id", "subject_ref", "conflict_type", "impact_scope", "agent_behavior_rule", "resolution_status", "attrs_json", "updated_at",
		},
		"conflict_claims": {
			"conflict_id", "claim_id",
		},
		"path_index": {
			"id", "generation_id", "path", "node_id", "relation", "confidence", "evidence_id", "updated_at",
		},
		"symbol_index": {
			"id", "generation_id", "symbol_name", "normalized_symbol", "node_id", "path", "relation", "evidence_id", "confidence",
		},
		"alias_index": {
			"id", "generation_id", "alias", "normalized_alias", "target_type", "target_id", "language", "source", "confidence", "evidence_id",
		},
		"entrypoint_index": {
			"id", "generation_id", "entrypoint_key", "entrypoint_type", "node_id", "capability_id", "path", "evidence_id", "confidence",
		},
		"test_index": {
			"id", "generation_id", "test_path", "test_name", "node_id", "capability_id", "verification_node_id", "evidence_id", "confidence",
		},
		"slice_members": {
			"id", "generation_id", "slice_id", "object_type", "object_id", "rank", "reason", "updated_at",
		},
		"query_examples": {
			"id", "generation_id", "query_text", "intent", "expected_target_type", "expected_target_id", "language", "source", "created_at",
		},
		"updates": {
			"id", "generation_id", "trigger", "changed_paths_json", "affected_nodes_json", "affected_claims_json", "affected_slices_json", "result_state", "completed_at", "attrs_json",
		},
	}
}
