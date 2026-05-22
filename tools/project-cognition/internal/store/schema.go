package store

const SchemaVersion = 1

const schemaSQL = `
CREATE TABLE IF NOT EXISTS metadata (
	key TEXT PRIMARY KEY,
	value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS nodes (
	id TEXT PRIMARY KEY,
	type TEXT NOT NULL,
	title TEXT NOT NULL,
	path TEXT,
	data TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS edges (
	id TEXT PRIMARY KEY,
	source TEXT NOT NULL,
	target TEXT NOT NULL,
	type TEXT NOT NULL,
	data TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS claims (
	id TEXT PRIMARY KEY,
	node_id TEXT,
	text TEXT NOT NULL,
	evidence_id TEXT,
	data TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS conflicts (
	id TEXT PRIMARY KEY,
	description TEXT NOT NULL,
	data TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS updates (
	id TEXT PRIMARY KEY,
	reason TEXT,
	changed_paths TEXT NOT NULL,
	created_at TEXT NOT NULL
);
`
