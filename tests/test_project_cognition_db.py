from contextlib import closing
import json
import sqlite3
from pathlib import Path

import pytest

from specify_cli.cognition import (
    apply_cognition_update,
    CognitionStatus,
    CognitionRuntimeMetadataError,
    cognition_db_path,
    cognition_status_path,
    connect_cognition_db,
    ensure_cognition_db,
    get_active_generation_id,
    publish_cognition_runtime_metadata,
    read_cognition_status,
    seed_active_generation,
    write_cognition_status,
)


def test_cognition_db_path_lives_under_project_cognition(tmp_path: Path) -> None:
    assert cognition_db_path(tmp_path) == tmp_path / ".specify" / "project-cognition" / "project-cognition.db"


def test_ensure_cognition_db_creates_schema_and_active_generation(tmp_path: Path) -> None:
    db_path = ensure_cognition_db(tmp_path)

    assert db_path == cognition_db_path(tmp_path)
    assert db_path.exists()

    with closing(connect_cognition_db(tmp_path)) as conn:
        table_names = {
            row["name"]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'virtual')")
        }

    assert "generations" in table_names
    assert "nodes" in table_names
    assert "edges" in table_names
    assert "claims" in table_names
    assert "path_index" in table_names
    assert "alias_index" in table_names
    assert "claim_fts" in table_names
    assert "observation_fts" in table_names
    assert "alias_fts" in table_names
    assert get_active_generation_id(tmp_path) == ""


def test_seed_active_generation_is_query_visible(tmp_path: Path) -> None:
    ensure_cognition_db(tmp_path)
    generation_id = seed_active_generation(tmp_path, source_commit="abc123")

    assert generation_id
    assert get_active_generation_id(tmp_path) == generation_id

    with closing(connect_cognition_db(tmp_path)) as conn:
        row = conn.execute(
            "SELECT state, source_commit FROM generations WHERE id = ?",
            (generation_id,),
        ).fetchone()

    assert dict(row) == {"state": "active", "source_commit": "abc123"}


def test_reseeding_active_generation_preserves_existing_graph_rows(tmp_path: Path) -> None:
    ensure_cognition_db(tmp_path)
    generation_id = seed_active_generation(tmp_path, source_commit="abc123")

    with closing(connect_cognition_db(tmp_path)) as conn:
        conn.execute(
            "INSERT INTO nodes(id, generation_id, type, title, confidence, attrs_json, created_at, updated_at) "
            "VALUES ('NODE-1', ?, 'capability', 'Login', 'high', '{}', '2026-05-13T00:00:00Z', '2026-05-13T00:00:00Z')",
            (generation_id,),
        )
        conn.commit()

    assert seed_active_generation(tmp_path, source_commit="def456") == generation_id

    with closing(connect_cognition_db(tmp_path)) as conn:
        row = conn.execute(
            "SELECT generation_id, title FROM nodes WHERE id = 'NODE-1'",
        ).fetchone()

    assert dict(row) == {"generation_id": generation_id, "title": "Login"}


def test_staging_generation_is_not_active(tmp_path: Path) -> None:
    ensure_cognition_db(tmp_path)

    with closing(connect_cognition_db(tmp_path)) as conn:
        conn.execute(
            "INSERT INTO generations(id, sequence, kind, state, source_commit, started_at, published_at, superseded_at, attrs_json) "
            "VALUES ('GEN-STAGING', 1, 'scan', 'staging', 'abc123', '2026-05-13T00:00:00Z', '', '', '{}')"
        )
        conn.commit()

    assert get_active_generation_id(tmp_path) == ""


def test_connection_uses_row_factory_and_foreign_keys(tmp_path: Path) -> None:
    ensure_cognition_db(tmp_path)

    with closing(connect_cognition_db(tmp_path)) as conn:
        row = conn.execute("PRAGMA foreign_keys").fetchone()
        assert isinstance(row, sqlite3.Row)
        assert row[0] == 1


def test_cognition_status_round_trips_database_runtime_fields(tmp_path: Path) -> None:
    write_cognition_status(
        tmp_path,
        CognitionStatus(
            graph_ready=True,
            graph_store_path=".specify/project-cognition/project-cognition.db",
            active_generation_id="GEN-0001",
            query_contract_version=2,
            update_contract_version=1,
        ),
    )

    status = read_cognition_status(tmp_path)

    assert status.graph_ready is True
    assert status.graph_store_path == ".specify/project-cognition/project-cognition.db"
    assert status.active_generation_id == "GEN-0001"
    assert status.query_contract_version == 2
    assert status.update_contract_version == 1


def test_cognition_status_tolerates_malformed_database_contract_versions(tmp_path: Path) -> None:
    path = cognition_status_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        '{"query_contract_version": "unknown", "update_contract_version": {}}\n',
        encoding="utf-8",
    )

    status = read_cognition_status(tmp_path)

    assert status.query_contract_version == 0
    assert status.update_contract_version == 0


def test_publish_cognition_runtime_metadata_writes_db_and_status_runtime_fields(tmp_path: Path) -> None:
    generation_id = seed_active_generation(tmp_path, source_commit="abc123")

    publish_cognition_runtime_metadata(tmp_path)

    status = read_cognition_status(tmp_path)
    assert status.baseline_state == "ready"
    assert status.graph_ready is True
    assert status.graph_store_path == ".specify/project-cognition/project-cognition.db"
    assert status.active_generation_id == generation_id
    assert status.query_contract_version == 2
    assert status.update_contract_version == 1

    with closing(connect_cognition_db(tmp_path)) as conn:
        rows = conn.execute(
            "SELECT key, value_json FROM metadata WHERE key IN "
            "('baseline_state', 'graph_ready', 'graph_store_path', 'active_generation_id', "
            "'query_contract_version', 'update_contract_version')"
        ).fetchall()

    metadata = {str(row["key"]): row["value_json"] for row in rows}
    assert metadata == {
        "baseline_state": '"ready"',
        "graph_ready": "true",
        "graph_store_path": '".specify/project-cognition/project-cognition.db"',
        "active_generation_id": '"GEN-0001"',
        "query_contract_version": "2",
        "update_contract_version": "1",
    }


def test_publish_cognition_runtime_metadata_preserves_extra_status_fields(tmp_path: Path) -> None:
    seed_active_generation(tmp_path, source_commit="abc123")
    status_path = cognition_status_path(tmp_path)
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_text(
        json.dumps(
            {
                "version": 3,
                "minimal_baseline": True,
                "custom_marker": "keep-me",
                "freshness": "fresh",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    publish_cognition_runtime_metadata(tmp_path)

    payload = json.loads(status_path.read_text(encoding="utf-8"))
    assert payload["minimal_baseline"] is True
    assert payload["custom_marker"] == "keep-me"
    assert payload["baseline_state"] == "ready"
    assert payload["graph_ready"] is True


def test_publish_cognition_runtime_metadata_blocks_without_active_generation(tmp_path: Path) -> None:
    ensure_cognition_db(tmp_path)

    with pytest.raises(CognitionRuntimeMetadataError, match="active generation"):
        publish_cognition_runtime_metadata(tmp_path)

    status = read_cognition_status(tmp_path)
    assert status.graph_ready is False
    assert status.baseline_state == "missing"


def test_publish_cognition_runtime_metadata_checkpoints_wal_sidecar(tmp_path: Path) -> None:
    seed_active_generation(tmp_path, source_commit="abc123")
    db_path = cognition_db_path(tmp_path)
    wal_path = db_path.with_name(f"{db_path.name}-wal")

    publish_cognition_runtime_metadata(tmp_path)

    assert not wal_path.exists() or wal_path.stat().st_size == 0


def test_read_cognition_runtime_metadata_does_not_create_wal_sidecars(tmp_path: Path) -> None:
    generation_id = seed_active_generation(tmp_path, source_commit="abc123")
    publish_cognition_runtime_metadata(tmp_path)
    db_path = cognition_db_path(tmp_path)
    wal_path = db_path.with_name(f"{db_path.name}-wal")
    shm_path = db_path.with_name(f"{db_path.name}-shm")
    wal_path.unlink(missing_ok=True)
    shm_path.unlink(missing_ok=True)

    from specify_cli.cognition import read_cognition_runtime_metadata

    metadata = read_cognition_runtime_metadata(tmp_path)

    assert metadata["active_generation_id"] == generation_id
    assert not wal_path.exists()
    assert not shm_path.exists()


def test_apply_cognition_update_records_affected_path_update(tmp_path: Path) -> None:
    ensure_cognition_db(tmp_path)
    generation_id = seed_active_generation(tmp_path, source_commit="abc123")
    with closing(connect_cognition_db(tmp_path)) as conn:
        conn.execute(
            "INSERT INTO evidence(id, generation_id, source_kind, source_path, commit_sha, span, extractor, content_hash, captured_at, attrs_json) "
            "VALUES ('E-update', ?, 'file', 'src/auth/login.ts', 'abc123', '1-80', 'test', 'old', '2026-05-13T00:00:00Z', '{}')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO nodes(id, generation_id, type, title, confidence, attrs_json, created_at, updated_at) "
            "VALUES ('capability:auth.login', ?, 'capability', 'User login', 'strong', '{}', '2026-05-13T00:00:00Z', '2026-05-13T00:00:00Z')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO path_index(id, generation_id, path, node_id, relation, confidence, evidence_id, updated_at) "
            "VALUES ('P-update', ?, 'src/auth/login.ts', 'capability:auth.login', 'implements', 'strong', 'E-update', '2026-05-13T00:00:00Z')",
            (generation_id,),
        )
        conn.commit()

    result = apply_cognition_update(tmp_path, changed_paths=["src\\auth\\login.ts"], reason="unit-test")

    assert result["readiness"] == "ready"
    assert result["recommended_next_action"] == "retry_current_workflow"
    assert result["affected_nodes"] == ["capability:auth.login"]
    assert result["changed_paths"] == ["src/auth/login.ts"]
    assert result["update_id"]
    status = read_cognition_status(tmp_path)
    assert status.last_update_id == result["update_id"]
    assert status.last_refresh_reason == "unit-test"
    assert status.last_refresh_scope == "partial"
    assert status.last_refresh_basis == "project-cognition update"
    assert status.last_refresh_changed_files_basis == ["src/auth/login.ts"]
    with closing(connect_cognition_db(tmp_path)) as conn:
        updates = conn.execute(
            "SELECT id, trigger, changed_paths_json, affected_nodes_json, result_state FROM updates"
        ).fetchall()
    assert len(updates) == 1
    assert updates[0]["id"] == result["update_id"]
    assert updates[0]["trigger"] == "unit-test"
    assert updates[0]["changed_paths_json"] == '["src/auth/login.ts"]'
    assert updates[0]["affected_nodes_json"] == '["capability:auth.login"]'
    assert updates[0]["result_state"] == "ready"
    with closing(connect_cognition_db(tmp_path)) as conn:
        update_row = conn.execute("SELECT attrs_json FROM updates WHERE id = ?", (result["update_id"],)).fetchone()
    attrs = json.loads(update_row["attrs_json"])
    assert attrs["publishing_model"] == "patch-in-active-generation"
    assert attrs["patched_retrieval_signals"] == ["src/auth/login.ts"]
    assert attrs["invalidated_retrieval_signals"] == []
    assert attrs["affected_route_records"] == ["P-update"]


def test_apply_cognition_update_records_duplicate_covered_path_once(tmp_path: Path) -> None:
    ensure_cognition_db(tmp_path)
    generation_id = seed_active_generation(tmp_path, source_commit="abc123")
    with closing(connect_cognition_db(tmp_path)) as conn:
        conn.execute(
            "INSERT INTO evidence(id, generation_id, source_kind, source_path, commit_sha, span, extractor, content_hash, captured_at, attrs_json) "
            "VALUES ('E-update', ?, 'file', 'src/auth/login.ts', 'abc123', '1-80', 'test', 'old', '2026-05-13T00:00:00Z', '{}')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO nodes(id, generation_id, type, title, confidence, attrs_json, created_at, updated_at) "
            "VALUES ('capability:auth.login', ?, 'capability', 'User login', 'strong', '{}', '2026-05-13T00:00:00Z', '2026-05-13T00:00:00Z')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO path_index(id, generation_id, path, node_id, relation, confidence, evidence_id, updated_at) "
            "VALUES ('P-update', ?, 'src/auth/login.ts', 'capability:auth.login', 'implements', 'strong', 'E-update', '2026-05-13T00:00:00Z')",
            (generation_id,),
        )
        conn.commit()

    result = apply_cognition_update(
        tmp_path,
        changed_paths=["src/auth/login.ts", "src\\auth\\login.ts"],
        reason="unit-test",
    )

    assert result["readiness"] == "ready"
    assert result["changed_paths"] == ["src/auth/login.ts"]
    with closing(connect_cognition_db(tmp_path)) as conn:
        updates = conn.execute("SELECT changed_paths_json FROM updates").fetchall()
    assert len(updates) == 1
    assert updates[0]["changed_paths_json"] == '["src/auth/login.ts"]'


def test_apply_cognition_update_records_partial_refresh_when_path_missing(tmp_path: Path) -> None:
    ensure_cognition_db(tmp_path)
    seed_active_generation(tmp_path, source_commit="abc123")

    result = apply_cognition_update(tmp_path, changed_paths=["src/auth/missing.ts"], reason="unit-test")

    assert result["readiness"] == "partial_refresh"
    assert result["recommended_next_action"] == "review_missing_coverage"
    assert result["update_id"]
    assert result["affected_nodes"] == []
    assert result["missing_coverage"] == ["path not covered by project cognition index: src/auth/missing.ts"]
    assert result["known_unknowns"] == ["path not covered by project cognition index: src/auth/missing.ts"]
    assert result["minimal_live_reads"] == ["src/auth/missing.ts"]
    with closing(connect_cognition_db(tmp_path)) as conn:
        updates = conn.execute("SELECT id, result_state, attrs_json FROM updates").fetchall()
    assert len(updates) == 1
    assert updates[0]["id"] == result["update_id"]
    assert updates[0]["result_state"] == "partial_refresh"
    attrs = json.loads(updates[0]["attrs_json"])
    assert attrs["known_unknowns"] == ["path not covered by project cognition index: src/auth/missing.ts"]
    assert attrs["minimal_live_reads"] == ["src/auth/missing.ts"]
    assert attrs["confidence"] == "partial"


def test_apply_cognition_update_reports_duplicate_missing_path_once(tmp_path: Path) -> None:
    ensure_cognition_db(tmp_path)
    seed_active_generation(tmp_path, source_commit="abc123")

    result = apply_cognition_update(
        tmp_path,
        changed_paths=["src/missing.ts", "src\\missing.ts"],
        reason="unit-test",
    )

    assert result["readiness"] == "partial_refresh"
    assert result["update_id"]
    assert result["changed_paths"] == ["src/missing.ts"]
    assert result["missing_coverage"] == ["path not covered by project cognition index: src/missing.ts"]
    with closing(connect_cognition_db(tmp_path)) as conn:
        updates = conn.execute("SELECT id FROM updates").fetchall()
    assert len(updates) == 1


def test_apply_cognition_update_records_proven_nodes_when_any_path_missing(tmp_path: Path) -> None:
    ensure_cognition_db(tmp_path)
    generation_id = seed_active_generation(tmp_path, source_commit="abc123")
    with closing(connect_cognition_db(tmp_path)) as conn:
        conn.execute(
            "INSERT INTO evidence(id, generation_id, source_kind, source_path, commit_sha, span, extractor, content_hash, captured_at, attrs_json) "
            "VALUES ('E-update', ?, 'file', 'src/auth/login.ts', 'abc123', '1-80', 'test', 'old', '2026-05-13T00:00:00Z', '{}')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO nodes(id, generation_id, type, title, confidence, attrs_json, created_at, updated_at) "
            "VALUES ('capability:auth.login', ?, 'capability', 'User login', 'strong', '{}', '2026-05-13T00:00:00Z', '2026-05-13T00:00:00Z')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO path_index(id, generation_id, path, node_id, relation, confidence, evidence_id, updated_at) "
            "VALUES ('P-update', ?, 'src/auth/login.ts', 'capability:auth.login', 'implements', 'strong', 'E-update', '2026-05-13T00:00:00Z')",
            (generation_id,),
        )
        conn.commit()

    result = apply_cognition_update(
        tmp_path,
        changed_paths=["src/auth/login.ts", "src/auth/missing.ts"],
        reason="unit-test",
    )

    assert result["readiness"] == "partial_refresh"
    assert result["recommended_next_action"] == "review_missing_coverage"
    assert result["affected_nodes"] == ["capability:auth.login"]
    assert result["missing_coverage"] == ["path not covered by project cognition index: src/auth/missing.ts"]
    assert result["minimal_live_reads"] == ["src/auth/missing.ts"]
    with closing(connect_cognition_db(tmp_path)) as conn:
        updates = conn.execute("SELECT id, affected_nodes_json, result_state FROM updates").fetchall()
    assert len(updates) == 1
    assert updates[0]["id"] == result["update_id"]
    assert updates[0]["affected_nodes_json"] == '["capability:auth.login"]'
    assert updates[0]["result_state"] == "partial_refresh"


def test_apply_cognition_update_without_active_generation_includes_empty_update_id(tmp_path: Path) -> None:
    ensure_cognition_db(tmp_path)

    result = apply_cognition_update(tmp_path, changed_paths=["src/auth/login.ts"], reason="unit-test")

    assert result["readiness"] == "needs_rebuild"
    assert result["recommended_next_action"] == "run_map_scan_build"
    assert result["update_id"] == ""
