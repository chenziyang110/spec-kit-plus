"""SQLite-backed project cognition graph store."""

from __future__ import annotations

from contextlib import closing, contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Iterator

from .paths import cognition_db_path, cognition_dir


SCHEMA_VERSION = 1


class CognitionRuntimeMetadataError(RuntimeError):
    """Raised when query runtime metadata cannot be derived from the DB."""


def iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def connect_cognition_db(project_root: Path) -> sqlite3.Connection:
    path = cognition_db_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


@contextmanager
def cognition_transaction(project_root: Path) -> Iterator[sqlite3.Connection]:
    conn = connect_cognition_db(project_root)
    try:
        conn.execute("BEGIN IMMEDIATE")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def ensure_cognition_db(project_root: Path) -> Path:
    cognition_dir(project_root).mkdir(parents=True, exist_ok=True)
    path = cognition_db_path(project_root)
    with closing(connect_cognition_db(project_root)) as conn:
        _create_schema(conn)
        _write_metadata(conn, "schema_version", SCHEMA_VERSION)
        conn.commit()
    return path


def _write_metadata(conn: sqlite3.Connection, key: str, value: object) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO metadata(key, value_json, updated_at) VALUES (?, ?, ?)",
        (key, json.dumps(value), iso_now()),
    )


def publish_cognition_runtime_metadata(project_root: Path) -> dict[str, object]:
    """Publish query-runtime readiness metadata into the DB and status entrypoint."""

    from .paths import cognition_status_path
    from .status import read_cognition_status

    ensure_cognition_db(project_root)
    active_generation_id = get_active_generation_id(project_root)
    if not active_generation_id:
        raise CognitionRuntimeMetadataError("project-cognition.db must have an active generation before publishing runtime metadata")
    metadata: dict[str, object] = {
        "baseline_state": "ready",
        "graph_ready": True,
        "graph_store_path": ".specify/project-cognition/project-cognition.db",
        "active_generation_id": active_generation_id,
        "query_contract_version": 1,
        "update_contract_version": 1,
    }
    with closing(connect_cognition_db(project_root)) as conn:
        for key, value in metadata.items():
            _write_metadata(conn, key, value)
        conn.commit()
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")

    current = read_cognition_status(project_root)
    status_path = cognition_status_path(project_root)
    existing_payload: dict[str, object] = {}
    if status_path.exists() and status_path.is_file():
        try:
            raw_payload = json.loads(status_path.read_text(encoding="utf-8"))
            if isinstance(raw_payload, dict):
                existing_payload = dict(raw_payload)
        except json.JSONDecodeError:
            existing_payload = {}
    existing_payload.update(
        {
            "version": max(int(current.version or 1), 3),
            "baseline_state": "ready",
            "baseline_commit": current.baseline_commit,
            "baseline_branch": current.baseline_branch,
            "baseline_built_at": current.baseline_built_at,
            "last_update_id": current.last_update_id,
            "graph_ready": True,
            "graph_store_path": ".specify/project-cognition/project-cognition.db",
            "active_generation_id": active_generation_id,
            "query_contract_version": 1,
            "update_contract_version": 1,
            "stale_paths": list(current.stale_paths or []),
            "stale_reasons": list(current.stale_reasons or []),
            "freshness": current.freshness,
            "last_refresh_reason": current.last_refresh_reason,
            "last_refresh_topics": list(current.last_refresh_topics or []),
            "last_refresh_scope": current.last_refresh_scope,
            "last_refresh_basis": current.last_refresh_basis,
            "last_refresh_changed_files_basis": list(current.last_refresh_changed_files_basis or []),
            "manual_force_stale": current.manual_force_stale,
            "manual_force_stale_reasons": list(current.manual_force_stale_reasons or []),
            "dirty": current.dirty,
            "dirty_reasons": list(current.dirty_reasons or []),
            "dirty_origin_command": current.dirty_origin_command,
            "dirty_origin_feature_dir": current.dirty_origin_feature_dir,
            "dirty_origin_lane_id": current.dirty_origin_lane_id,
            "dirty_scope_paths": list(current.dirty_scope_paths or []),
        }
    )
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_text(json.dumps(existing_payload, indent=2) + "\n", encoding="utf-8")
    return metadata


def read_cognition_runtime_metadata(project_root: Path) -> dict[str, object]:
    """Read DB-published query runtime metadata."""

    db_path = cognition_db_path(project_root)
    if not db_path.exists() or not db_path.is_file() or db_path.stat().st_size == 0:
        return {}
    try:
        conn = sqlite3.connect(f"{db_path.resolve().as_uri()}?mode=ro&immutable=1", uri=True)
        conn.row_factory = sqlite3.Row
        with closing(conn):
            rows = conn.execute(
                "SELECT key, value_json FROM metadata WHERE key IN "
                "('baseline_state', 'graph_ready', 'graph_store_path', 'active_generation_id', "
                "'query_contract_version', 'update_contract_version')"
            ).fetchall()
    except sqlite3.Error:
        return {}

    metadata: dict[str, object] = {}
    for row in rows:
        key = str(row["key"])
        raw_value = str(row["value_json"])
        try:
            metadata[key] = json.loads(raw_value)
        except json.JSONDecodeError:
            metadata[key] = raw_value
    return metadata


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS metadata(
          key TEXT PRIMARY KEY,
          value_json TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS generations(
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

        CREATE TABLE IF NOT EXISTS evidence(
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

        CREATE TABLE IF NOT EXISTS observations(
          id TEXT PRIMARY KEY,
          generation_id TEXT NOT NULL REFERENCES generations(id) ON DELETE CASCADE,
          observation_type TEXT NOT NULL,
          summary TEXT NOT NULL,
          attrs_json TEXT NOT NULL DEFAULT '{}',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS observation_evidence(
          observation_id TEXT NOT NULL REFERENCES observations(id) ON DELETE CASCADE,
          evidence_id TEXT NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
          PRIMARY KEY(observation_id, evidence_id)
        );

        CREATE TABLE IF NOT EXISTS nodes(
          id TEXT PRIMARY KEY,
          generation_id TEXT NOT NULL REFERENCES generations(id) ON DELETE CASCADE,
          type TEXT NOT NULL,
          title TEXT NOT NULL,
          confidence TEXT NOT NULL,
          attrs_json TEXT NOT NULL DEFAULT '{}',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(type);
        CREATE INDEX IF NOT EXISTS idx_nodes_generation ON nodes(generation_id);

        CREATE TABLE IF NOT EXISTS node_evidence(
          node_id TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
          evidence_id TEXT NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
          PRIMARY KEY(node_id, evidence_id)
        );

        CREATE TABLE IF NOT EXISTS edges(
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
        CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id);
        CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id);
        CREATE INDEX IF NOT EXISTS idx_edges_type ON edges(type);
        CREATE INDEX IF NOT EXISTS idx_edges_generation ON edges(generation_id);

        CREATE TABLE IF NOT EXISTS edge_evidence(
          edge_id TEXT NOT NULL REFERENCES edges(id) ON DELETE CASCADE,
          evidence_id TEXT NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
          PRIMARY KEY(edge_id, evidence_id)
        );

        CREATE TABLE IF NOT EXISTS claims(
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

        CREATE TABLE IF NOT EXISTS claim_evidence(
          claim_id TEXT NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
          evidence_id TEXT NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
          PRIMARY KEY(claim_id, evidence_id)
        );

        CREATE TABLE IF NOT EXISTS conflicts(
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

        CREATE TABLE IF NOT EXISTS conflict_claims(
          conflict_id TEXT NOT NULL REFERENCES conflicts(id) ON DELETE CASCADE,
          claim_id TEXT NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
          PRIMARY KEY(conflict_id, claim_id)
        );

        CREATE TABLE IF NOT EXISTS path_index(
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

        CREATE TABLE IF NOT EXISTS symbol_index(
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

        CREATE TABLE IF NOT EXISTS alias_index(
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

        CREATE TABLE IF NOT EXISTS entrypoint_index(
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

        CREATE TABLE IF NOT EXISTS test_index(
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
        CREATE INDEX IF NOT EXISTS idx_test_capability ON test_index(capability_id);
        CREATE INDEX IF NOT EXISTS idx_test_path ON test_index(test_path);

        CREATE TABLE IF NOT EXISTS slice_members(
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

        CREATE TABLE IF NOT EXISTS query_examples(
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

        CREATE TABLE IF NOT EXISTS updates(
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
        """
    )


def get_active_generation_id(project_root: Path) -> str:
    ensure_cognition_db(project_root)
    with closing(connect_cognition_db(project_root)) as conn:
        row = conn.execute(
            "SELECT id FROM generations WHERE state = 'active' ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
    return str(row["id"]) if row else ""


def seed_active_generation(project_root: Path, *, source_commit: str = "") -> str:
    ensure_cognition_db(project_root)
    generation_id = "GEN-0001"
    now = iso_now()
    with cognition_transaction(project_root) as conn:
        conn.execute("UPDATE generations SET state = 'superseded', superseded_at = ? WHERE state = 'active'", (now,))
        conn.execute(
            "INSERT INTO generations(id, sequence, kind, state, source_commit, started_at, published_at, superseded_at, attrs_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET "
            "sequence = excluded.sequence, "
            "kind = excluded.kind, "
            "state = excluded.state, "
            "source_commit = excluded.source_commit, "
            "started_at = excluded.started_at, "
            "published_at = excluded.published_at, "
            "superseded_at = excluded.superseded_at, "
            "attrs_json = excluded.attrs_json",
            (generation_id, 1, "seed", "active", source_commit, now, now, "", "{}"),
        )
    return generation_id
