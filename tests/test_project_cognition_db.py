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
from specify_cli.cognition.path_adoption import AUTO_ADOPT_LIMIT


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
    assert status.dirty_reasons == []
    assert status.dirty_origin_command == ""
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


def test_apply_cognition_update_reports_and_skips_cognitionignored_paths(tmp_path: Path) -> None:
    ensure_cognition_db(tmp_path)
    generation_id = seed_active_generation(tmp_path, source_commit="abc123")
    (tmp_path / ".cognitionignore").write_text("vendor/\n", encoding="utf-8")
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
        changed_paths=["src/auth/login.ts", "vendor/reference.ts"],
        reason="unit-test",
    )

    assert result["readiness"] == "ready"
    assert result["changed_paths"] == ["src/auth/login.ts"]
    assert result["ignored_paths"] == ["vendor/reference.ts"]
    assert result["minimal_live_reads"] == []
    with closing(connect_cognition_db(tmp_path)) as conn:
        update_row = conn.execute("SELECT changed_paths_json, attrs_json FROM updates").fetchone()
    assert update_row["changed_paths_json"] == '["src/auth/login.ts"]'
    attrs = json.loads(update_row["attrs_json"])
    assert attrs["ignored_paths"] == ["vendor/reference.ts"]


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


def test_apply_cognition_update_adopts_same_directory_missing_path(tmp_path: Path) -> None:
    ensure_cognition_db(tmp_path)
    generation_id = seed_active_generation(tmp_path, source_commit="abc123")
    source_path = tmp_path / "src" / "auth" / "session.ts"
    source_path.parent.mkdir(parents=True)
    source_path.write_text("export const session = true\n", encoding="utf-8")
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

    result = apply_cognition_update(tmp_path, changed_paths=["src/auth/session.ts"], reason="unit-test")

    assert result["readiness"] == "ready"
    assert result["recommended_next_action"] == "retry_current_workflow"
    assert result["affected_nodes"] == ["capability:auth.login"]
    assert result["adopted_paths"] == ["src/auth/session.ts"]
    assert result["review_paths"] == []
    assert result["unadoptable_paths"] == []
    assert result["missing_coverage"] == []
    assert result["known_unknowns"] == []
    assert result["minimal_live_reads"] == []
    with closing(connect_cognition_db(tmp_path)) as conn:
        row = conn.execute(
            "SELECT path, node_id, relation, confidence, evidence_id FROM path_index WHERE path = 'src/auth/session.ts'"
        ).fetchone()
        evidence = conn.execute(
            "SELECT source_kind, source_path, extractor, attrs_json FROM evidence WHERE id = ?",
            (row["evidence_id"],),
        ).fetchone()
        update_row = conn.execute("SELECT result_state, attrs_json FROM updates").fetchone()
    assert row["path"] == "src/auth/session.ts"
    assert row["node_id"] == "capability:auth.login"
    assert row["relation"] == "provisional_path"
    assert row["confidence"] == "weak"
    assert evidence["source_kind"] == "path_adoption"
    assert evidence["source_path"] == "src/auth/session.ts"
    assert evidence["extractor"] == "map-update-adoption"
    evidence_attrs = json.loads(evidence["attrs_json"])
    assert evidence_attrs["adoption_status"] == "provisional"
    assert evidence_attrs["adoption_reason"] == "same_directory_indexed_sibling"
    assert evidence_attrs["nearest_indexed_sibling"] == "src/auth/login.ts"
    assert evidence_attrs["update_id"] == result["update_id"]
    assert update_row["result_state"] == "ready"
    attrs = json.loads(update_row["attrs_json"])
    assert attrs["path_adoption"]["query_coverage"] == "adoptable_path_gap"
    assert attrs["path_adoption"]["adopted_paths"] == ["src/auth/session.ts"]
    assert attrs["path_adoption"]["review_paths"] == []
    assert attrs["path_adoption"]["unadoptable_paths"] == []
    assert attrs["adopted_paths"] == ["src/auth/session.ts"]
    assert attrs["known_unknowns"] == []
    assert attrs["minimal_live_reads"] == []
    assert attrs["confidence"] == "weak"
    status = read_cognition_status(tmp_path)
    assert status.freshness == "fresh"
    assert status.stale_paths == []
    assert status.stale_reasons == []
    assert status.dirty_reasons == []
    assert status.dirty_origin_command == ""


def test_successful_cognition_update_preserves_prior_path_index_rebuild_block(tmp_path: Path) -> None:
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

    missing_result = apply_cognition_update(
        tmp_path,
        changed_paths=["scripts/release/package.ps1"],
        reason="missing-path",
    )
    ready_result = apply_cognition_update(
        tmp_path,
        changed_paths=["src/auth/login.ts"],
        reason="covered-path",
    )

    assert missing_result["readiness"] == "needs_rebuild"
    assert ready_result["readiness"] == "ready"
    status = read_cognition_status(tmp_path)
    assert status.last_update_id == ready_result["update_id"]
    assert status.baseline_state == "blocked"
    assert status.freshness == "stale"
    assert status.stale_paths == ["scripts/release/package.ps1"]
    assert status.stale_reasons == [
        "path not safely adoptable by project cognition index: scripts/release/package.ps1"
    ]
    assert status.dirty_reasons == [
        "path not safely adoptable by project cognition index: scripts/release/package.ps1"
    ]
    assert status.dirty_origin_command == "sp-map-update"


def test_apply_cognition_update_returns_review_for_small_uncertain_gap(tmp_path: Path) -> None:
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
        changed_paths=["docs/future/idea.md"],
        reason="unit-test",
    )

    assert result["readiness"] == "review"
    assert result["recommended_next_action"] == "perform_minimal_live_reads"
    assert result["adopted_paths"] == []
    assert result["review_paths"] == ["docs/future/idea.md"]
    assert result["unadoptable_paths"] == []
    assert result["minimal_live_reads"] == ["docs/future/idea.md"]
    assert result["missing_coverage"] == [
        "path requires minimal live read before adoption: docs/future/idea.md"
    ]
    assert result["known_unknowns"] == [
        "path requires minimal live read before adoption: docs/future/idea.md"
    ]
    with closing(connect_cognition_db(tmp_path)) as conn:
        row = conn.execute("SELECT path FROM path_index WHERE path = 'docs/future/idea.md'").fetchone()
        update_row = conn.execute("SELECT result_state, attrs_json FROM updates").fetchone()
    assert row is None
    assert update_row["result_state"] == "review"
    attrs = json.loads(update_row["attrs_json"])
    assert attrs["path_adoption"]["query_coverage"] == "uncertain_path_gap"
    assert attrs["known_unknowns"] == [
        "path requires minimal live read before adoption: docs/future/idea.md"
    ]
    assert attrs["minimal_live_reads"] == ["docs/future/idea.md"]
    assert attrs["confidence"] == "weak"
    status = read_cognition_status(tmp_path)
    assert status.freshness == "possibly_stale"
    assert status.stale_paths == ["docs/future/idea.md"]
    assert status.stale_reasons == [
        "path requires minimal live read before adoption: docs/future/idea.md"
    ]
    assert status.dirty_reasons == []
    assert status.dirty_origin_command == ""


def test_review_update_preserves_prior_unadoptable_rebuild_block(tmp_path: Path) -> None:
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

    rebuild_result = apply_cognition_update(
        tmp_path,
        changed_paths=["scripts/release/package.ps1"],
        reason="core-surface",
    )
    review_result = apply_cognition_update(
        tmp_path,
        changed_paths=["docs/future/idea.md"],
        reason="review-gap",
    )

    assert rebuild_result["readiness"] == "needs_rebuild"
    assert review_result["readiness"] == "review"
    assert review_result["review_paths"] == ["docs/future/idea.md"]
    status = read_cognition_status(tmp_path)
    assert status.last_update_id == review_result["update_id"]
    assert status.baseline_state == "blocked"
    assert status.freshness == "stale"
    assert status.stale_paths == ["scripts/release/package.ps1"]
    assert status.stale_reasons == [
        "path not safely adoptable by project cognition index: scripts/release/package.ps1"
    ]
    assert status.dirty_reasons == [
        "path not safely adoptable by project cognition index: scripts/release/package.ps1"
    ]
    assert status.dirty_origin_command == "sp-map-update"


def test_apply_cognition_update_does_not_adopt_over_limit_review_paths(tmp_path: Path) -> None:
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
    missing_paths = [
        f"src/auth/session-{index}.ts"
        for index in range(AUTO_ADOPT_LIMIT + 1)
    ]

    result = apply_cognition_update(tmp_path, changed_paths=missing_paths, reason="unit-test")

    assert result["readiness"] == "review"
    assert result["recommended_next_action"] == "perform_minimal_live_reads"
    assert result["adopted_paths"] == []
    assert result["review_paths"] == missing_paths
    assert result["minimal_live_reads"] == sorted(missing_paths)
    assert result["missing_coverage"] == [
        f"path requires minimal live read before adoption: {path}"
        for path in missing_paths
    ]
    with closing(connect_cognition_db(tmp_path)) as conn:
        rows = conn.execute(
            "SELECT path FROM path_index WHERE path IN ({})".format(
                ",".join("?" for _ in missing_paths)
            ),
            missing_paths,
        ).fetchall()
        adoption_evidence = conn.execute(
            "SELECT id FROM evidence WHERE source_kind = 'path_adoption'"
        ).fetchall()
        update_row = conn.execute("SELECT result_state, attrs_json FROM updates").fetchone()
    assert rows == []
    assert adoption_evidence == []
    assert update_row["result_state"] == "review"
    attrs = json.loads(update_row["attrs_json"])
    assert attrs["path_adoption"]["query_coverage"] == "uncertain_path_gap"
    assert attrs["path_adoption"]["adopted_paths"] == []
    assert attrs["path_adoption"]["review_paths"] == missing_paths
    assert attrs["confidence"] == "weak"


def test_apply_cognition_update_routes_unadoptable_core_surface_to_rebuild(tmp_path: Path) -> None:
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
        changed_paths=["scripts/release/package.ps1"],
        reason="unit-test",
    )

    assert result["readiness"] == "needs_rebuild"
    assert result["recommended_next_action"] == "run_map_scan_build"
    assert result["adopted_paths"] == []
    assert result["review_paths"] == []
    assert result["unadoptable_paths"] == ["scripts/release/package.ps1"]
    assert result["minimal_live_reads"] == ["scripts/release/package.ps1"]
    assert result["missing_coverage"] == [
        "path not safely adoptable by project cognition index: scripts/release/package.ps1"
    ]
    assert result["known_unknowns"] == [
        "path not safely adoptable by project cognition index: scripts/release/package.ps1"
    ]
    with closing(connect_cognition_db(tmp_path)) as conn:
        row = conn.execute("SELECT path FROM path_index WHERE path = 'scripts/release/package.ps1'").fetchone()
        update_row = conn.execute("SELECT result_state, attrs_json FROM updates").fetchone()
    assert row is None
    assert update_row["result_state"] == "needs_rebuild"
    attrs = json.loads(update_row["attrs_json"])
    assert attrs["path_adoption"]["query_coverage"] == "unadoptable_path_gap"
    assert attrs["known_unknowns"] == [
        "path not safely adoptable by project cognition index: scripts/release/package.ps1"
    ]
    assert attrs["confidence"] == "strong"
    status = read_cognition_status(tmp_path)
    assert status.baseline_state == "blocked"
    assert status.freshness == "stale"
    assert status.stale_paths == ["scripts/release/package.ps1"]
    assert status.stale_reasons == [
        "path not safely adoptable by project cognition index: scripts/release/package.ps1"
    ]
    assert status.dirty_reasons == [
        "path not safely adoptable by project cognition index: scripts/release/package.ps1"
    ]
    assert status.dirty_origin_command == "sp-map-update"


def test_apply_cognition_update_without_active_generation_includes_empty_update_id(tmp_path: Path) -> None:
    ensure_cognition_db(tmp_path)

    result = apply_cognition_update(tmp_path, changed_paths=["src/auth/login.ts"], reason="unit-test")

    assert result["readiness"] == "needs_rebuild"
    assert result["recommended_next_action"] == "run_map_scan_build"
    assert result["update_id"] == ""
