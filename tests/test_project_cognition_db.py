from contextlib import closing
import sqlite3
from pathlib import Path

from specify_cli.cognition import (
    CognitionStatus,
    cognition_db_path,
    connect_cognition_db,
    ensure_cognition_db,
    get_active_generation_id,
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
            query_contract_version=1,
            update_contract_version=1,
        ),
    )

    status = read_cognition_status(tmp_path)

    assert status.graph_ready is True
    assert status.graph_store_path == ".specify/project-cognition/project-cognition.db"
    assert status.active_generation_id == "GEN-0001"
    assert status.query_contract_version == 1
    assert status.update_contract_version == 1
