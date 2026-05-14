from __future__ import annotations

from contextlib import closing
import json
from pathlib import Path

from specify_cli.cognition import (
    CognitionStatus,
    connect_cognition_db,
    ensure_cognition_db,
    seed_active_generation,
    validate_build_acceptance,
    validate_scan_acceptance,
    write_cognition_status,
)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def _write_complete_scan_package(project_root: Path) -> None:
    run_dir = project_root / ".specify" / "project-cognition"
    _write_json(run_dir / "status.json", {"version": 3, "graph_ready": False})
    evidence_dir = run_dir / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "E-001.json").write_text('{"id": "E-001"}\n', encoding="utf-8")
    _write_json(run_dir / "provisional" / "nodes.json", {"nodes": [{"id": "capability:auth.login"}]})
    _write_json(run_dir / "provisional" / "edges.json", {"edges": []})
    _write_json(run_dir / "provisional" / "observations.json", {"observations": [{"id": "OBS-001"}]})
    _write_json(run_dir / "coverage.json", {"rows": [{"path": "src/auth/login.ts", "criticality": "critical"}]})
    _write_json(
        run_dir / "workbench" / "coverage-ledger.json",
        {
            "rows": [
                {
                    "path": "src/auth/login.ts",
                    "criticality": "critical",
                    "coverage_state": "covered",
                }
            ],
            "open_gaps": [],
        },
    )
    packets_dir = run_dir / "workbench" / "scan-packets"
    packets_dir.mkdir(parents=True, exist_ok=True)
    (packets_dir / "core.md").write_text("# Core scan packet\n", encoding="utf-8")


def _seed_query_ready_runtime(project_root: Path) -> str:
    generation_id = seed_active_generation(project_root, source_commit="abc123")
    with closing(connect_cognition_db(project_root)) as conn:
        conn.execute(
            "INSERT INTO evidence(id, generation_id, source_kind, source_path, commit_sha, span, extractor, content_hash, captured_at, attrs_json) "
            "VALUES ('E-login', ?, 'file', 'src/auth/login.ts', 'abc123', '1-80', 'test', 'hash-login', '2026-05-14T00:00:00Z', '{}')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO nodes(id, generation_id, type, title, confidence, attrs_json, created_at, updated_at) "
            "VALUES ('capability:auth.login', ?, 'capability', 'User login', 'strong', '{}', '2026-05-14T00:00:00Z', '2026-05-14T00:00:00Z')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO path_index(id, generation_id, path, node_id, relation, confidence, evidence_id, updated_at) "
            "VALUES ('P-login', ?, 'src/auth/login.ts', 'capability:auth.login', 'implements', 'strong', 'E-login', '2026-05-14T00:00:00Z')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO alias_index(id, generation_id, alias, normalized_alias, target_type, target_id, language, source, confidence, evidence_id) "
            "VALUES ('A-login', ?, 'login', 'login', 'capability', 'capability:auth.login', 'en', 'evidence', 'strong', 'E-login')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO claims(id, generation_id, subject_ref, predicate, object_ref, object_value, truth_layer, confidence, status, last_validated_at, attrs_json) "
            "VALUES ('claim:login', ?, 'capability:auth.login', 'implemented_by', 'src/auth/login.ts', '', 'implementation_reality', 'strong', 'active', '2026-05-14T00:00:00Z', '{}')",
            (generation_id,),
        )
        conn.commit()
    write_cognition_status(
        project_root,
        CognitionStatus(
            version=3,
            baseline_state="ready",
            graph_ready=True,
            graph_store_path=".specify/project-cognition/project-cognition.db",
            active_generation_id=generation_id,
            query_contract_version=1,
            update_contract_version=1,
            freshness="fresh",
        ),
    )
    return generation_id


def _seed_runtime_without_claims(project_root: Path) -> str:
    generation_id = seed_active_generation(project_root, source_commit="abc123")
    with closing(connect_cognition_db(project_root)) as conn:
        conn.execute(
            "INSERT INTO evidence(id, generation_id, source_kind, source_path, commit_sha, span, extractor, content_hash, captured_at, attrs_json) "
            "VALUES ('E-login', ?, 'file', 'src/auth/login.ts', 'abc123', '1-80', 'test', 'hash-login', '2026-05-14T00:00:00Z', '{}')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO nodes(id, generation_id, type, title, confidence, attrs_json, created_at, updated_at) "
            "VALUES ('capability:auth.login', ?, 'capability', 'User login', 'strong', '{}', '2026-05-14T00:00:00Z', '2026-05-14T00:00:00Z')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO path_index(id, generation_id, path, node_id, relation, confidence, evidence_id, updated_at) "
            "VALUES ('P-login', ?, 'src/auth/login.ts', 'capability:auth.login', 'implements', 'strong', 'E-login', '2026-05-14T00:00:00Z')",
            (generation_id,),
        )
        conn.commit()
    write_cognition_status(
        project_root,
        CognitionStatus(
            version=3,
            baseline_state="ready",
            graph_ready=True,
            graph_store_path=".specify/project-cognition/project-cognition.db",
            active_generation_id=generation_id,
            query_contract_version=1,
            update_contract_version=1,
            freshness="fresh",
        ),
    )
    return generation_id


def test_validate_scan_blocks_when_required_artifacts_are_missing(tmp_path: Path) -> None:
    result = validate_scan_acceptance(tmp_path)

    assert result["status"] == "blocked"
    assert result["gate"] == "scan"
    assert result["readiness"] == "blocked"
    assert any("status.json" in message for message in result["errors"])
    assert any("coverage-ledger.json" in message for message in result["errors"])


def test_validate_scan_accepts_complete_scan_package(tmp_path: Path) -> None:
    _write_complete_scan_package(tmp_path)

    result = validate_scan_acceptance(tmp_path)

    assert result["status"] == "ok"
    assert result["readiness"] == "scan_ready"
    assert result["errors"] == []
    assert ".specify/project-cognition/workbench/coverage-ledger.json" in result["checked_paths"]


def test_validate_scan_warns_for_non_critical_open_gaps(tmp_path: Path) -> None:
    _write_complete_scan_package(tmp_path)
    _write_json(
        tmp_path / ".specify" / "project-cognition" / "workbench" / "coverage-ledger.json",
        {
            "rows": [
                {
                    "path": "src/auth/login.ts",
                    "criticality": "critical",
                    "coverage_state": "covered",
                }
            ],
            "open_gaps": [
                {
                    "criticality": "low-risk",
                    "owner": "map-scan",
                    "reason": "deferred sample",
                    "revisit_condition": "when sample path changes",
                }
            ],
        },
    )

    result = validate_scan_acceptance(tmp_path)

    assert result["status"] == "ok"
    assert any(
        "open gap" in message or "non-critical" in message
        for message in result["warnings"]
    )


def test_validate_scan_blocks_empty_coverage_rows(tmp_path: Path) -> None:
    _write_complete_scan_package(tmp_path)
    _write_json(tmp_path / ".specify" / "project-cognition" / "coverage.json", {"rows": []})

    result = validate_scan_acceptance(tmp_path)

    assert result["status"] == "blocked"
    assert any("coverage.json" in message and "rows" in message for message in result["errors"])


def test_validate_scan_blocks_empty_ledger_rows(tmp_path: Path) -> None:
    _write_complete_scan_package(tmp_path)
    _write_json(
        tmp_path / ".specify" / "project-cognition" / "workbench" / "coverage-ledger.json",
        {"rows": [], "open_gaps": []},
    )

    result = validate_scan_acceptance(tmp_path)

    assert result["status"] == "blocked"
    assert any("coverage-ledger.json" in message and "rows" in message for message in result["errors"])


def test_validate_scan_blocks_malformed_open_gaps(tmp_path: Path) -> None:
    _write_complete_scan_package(tmp_path)
    _write_json(
        tmp_path / ".specify" / "project-cognition" / "workbench" / "coverage-ledger.json",
        {
            "rows": [
                {
                    "path": "src/auth/login.ts",
                    "criticality": "critical",
                    "coverage_state": "covered",
                }
            ],
            "open_gaps": [{"criticality": "unknown", "reason": "cannot classify"}],
        },
    )

    result = validate_scan_acceptance(tmp_path)

    assert result["status"] == "blocked"
    assert any("open gap" in message and "criticality" in message for message in result["errors"])


def test_validate_scan_blocks_noncritical_open_gap_without_metadata(tmp_path: Path) -> None:
    _write_complete_scan_package(tmp_path)
    _write_json(
        tmp_path / ".specify" / "project-cognition" / "workbench" / "coverage-ledger.json",
        {
            "rows": [
                {
                    "path": "src/auth/login.ts",
                    "criticality": "critical",
                    "coverage_state": "covered",
                }
            ],
            "open_gaps": [{"criticality": "important", "reason": "deferred sample"}],
        },
    )

    result = validate_scan_acceptance(tmp_path)

    assert result["status"] == "blocked"
    assert any("open gap" in message and "owner" in message for message in result["errors"])


def test_validate_scan_blocks_for_critical_open_gaps(tmp_path: Path) -> None:
    _write_complete_scan_package(tmp_path)
    _write_json(
        tmp_path / ".specify" / "project-cognition" / "workbench" / "coverage-ledger.json",
        {
            "rows": [
                {
                    "path": "src/auth/login.ts",
                    "criticality": "critical",
                    "coverage_state": "covered",
                }
            ],
            "open_gaps": [{"criticality": "critical", "reason": "required source missing"}],
        },
    )

    result = validate_scan_acceptance(tmp_path)

    assert result["status"] == "blocked"
    assert any("critical" in message and "open gap" in message for message in result["errors"])


def test_validate_build_blocks_when_db_is_missing(tmp_path: Path) -> None:
    write_cognition_status(tmp_path, CognitionStatus(version=3, graph_ready=True))

    result = validate_build_acceptance(tmp_path)

    assert result["status"] == "blocked"
    assert any("project-cognition.db" in message and "must exist" in message for message in result["errors"])


def test_validate_build_blocks_when_db_has_no_active_generation(tmp_path: Path) -> None:
    ensure_cognition_db(tmp_path)
    write_cognition_status(tmp_path, CognitionStatus(version=3, graph_ready=True))

    result = validate_build_acceptance(tmp_path)

    assert result["status"] == "blocked"
    assert any("active generation" in message for message in result["errors"])


def test_validate_build_blocks_when_status_generation_conflicts_with_db(tmp_path: Path) -> None:
    _seed_query_ready_runtime(tmp_path)
    write_cognition_status(
        tmp_path,
        CognitionStatus(
            version=3,
            graph_ready=True,
            graph_store_path=".specify/project-cognition/project-cognition.db",
            active_generation_id="GEN-WRONG",
        ),
    )

    result = validate_build_acceptance(tmp_path)

    assert result["status"] == "blocked"
    assert any("active_generation_id" in message and "does not match" in message for message in result["errors"])


def test_validate_build_accepts_query_ready_runtime(tmp_path: Path) -> None:
    _seed_query_ready_runtime(tmp_path)

    result = validate_build_acceptance(tmp_path)

    assert result["status"] == "ok"
    assert result["readiness"] == "query_ready"
    assert result["errors"] == []
    assert result["details"]["active_generation_id"] == "GEN-0001"


def test_validate_build_blocks_when_active_generation_has_no_claims(tmp_path: Path) -> None:
    _seed_runtime_without_claims(tmp_path)

    result = validate_build_acceptance(tmp_path)

    assert result["status"] == "blocked"
    assert any("claim" in message or "minimal-baseline" in message for message in result["errors"])


def test_validate_build_does_not_create_wal_sidecars(tmp_path: Path) -> None:
    _seed_query_ready_runtime(tmp_path)
    db_path = tmp_path / ".specify" / "project-cognition" / "project-cognition.db"
    wal_path = db_path.with_name(f"{db_path.name}-wal")
    shm_path = db_path.with_name(f"{db_path.name}-shm")
    wal_path.unlink(missing_ok=True)
    shm_path.unlink(missing_ok=True)

    result = validate_build_acceptance(tmp_path)

    assert result["status"] == "ok"
    assert not wal_path.exists()
    assert not shm_path.exists()
