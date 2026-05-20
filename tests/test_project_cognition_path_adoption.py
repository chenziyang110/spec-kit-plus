from contextlib import closing
from pathlib import Path

from specify_cli.cognition import connect_cognition_db, ensure_cognition_db, seed_active_generation
from specify_cli.cognition.path_adoption import classify_path_coverage


def _seed_indexed_path(project_root: Path, *, indexed_path: str = "src/auth/login.ts") -> str:
    ensure_cognition_db(project_root)
    generation_id = seed_active_generation(project_root, source_commit="abc123")
    with closing(connect_cognition_db(project_root)) as conn:
        conn.execute(
            "INSERT INTO evidence(id, generation_id, source_kind, source_path, commit_sha, span, extractor, content_hash, captured_at, attrs_json) "
            "VALUES ('E-login', ?, 'file', ?, 'abc123', '1-80', 'test', 'hash-login', '2026-05-13T00:00:00Z', '{}')",
            (generation_id, indexed_path),
        )
        conn.execute(
            "INSERT INTO nodes(id, generation_id, type, title, confidence, attrs_json, created_at, updated_at) "
            "VALUES ('capability:auth.login', ?, 'capability', 'User login', 'strong', '{}', '2026-05-13T00:00:00Z', '2026-05-13T00:00:00Z')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO path_index(id, generation_id, path, node_id, relation, confidence, evidence_id, updated_at) "
            "VALUES ('P-login', ?, ?, 'capability:auth.login', 'implements', 'strong', 'E-login', '2026-05-13T00:00:00Z')",
            (generation_id, indexed_path),
        )
        conn.commit()
    return generation_id


def test_classifies_same_directory_missing_path_as_adoptable(tmp_path: Path) -> None:
    generation_id = _seed_indexed_path(tmp_path)
    with closing(connect_cognition_db(tmp_path)) as conn:
        result = classify_path_coverage(
            conn,
            generation_id,
            missing_paths=["src/auth/session.ts"],
            requested_paths=["src/auth/session.ts"],
        )

    assert result.query_coverage == "adoptable_path_gap"
    assert result.recommended_next_action == "run_map_update"
    assert [item.path for item in result.adoptable_paths] == ["src/auth/session.ts"]
    assert result.adoptable_paths[0].node_id == "capability:auth.login"
    assert result.adoptable_paths[0].nearest_indexed_sibling == "src/auth/login.ts"
    assert result.review_paths == []
    assert result.unadoptable_paths == []


def test_duplicate_missing_paths_do_not_change_adoption_classification(tmp_path: Path) -> None:
    generation_id = _seed_indexed_path(tmp_path)
    duplicate_paths = ["src/auth/session.ts", "src\\auth\\session.ts"] * 6
    with closing(connect_cognition_db(tmp_path)) as conn:
        result = classify_path_coverage(
            conn,
            generation_id,
            missing_paths=duplicate_paths,
            requested_paths=duplicate_paths,
        )

    assert result.query_coverage == "adoptable_path_gap"
    assert [item.path for item in result.adoptable_paths] == ["src/auth/session.ts"]
    assert result.recommended_next_action == "run_map_update"


def test_classifies_nearest_indexed_ancestor_within_two_levels_as_adoptable(tmp_path: Path) -> None:
    generation_id = _seed_indexed_path(tmp_path)
    with closing(connect_cognition_db(tmp_path)) as conn:
        result = classify_path_coverage(
            conn,
            generation_id,
            missing_paths=["src/auth/payments/deep/new.ts"],
            requested_paths=["src/auth/payments/deep/new.ts"],
        )

    assert result.query_coverage == "adoptable_path_gap"
    assert [item.path for item in result.adoptable_paths] == ["src/auth/payments/deep/new.ts"]
    assert result.adoptable_paths[0].nearest_indexed_sibling == "src/auth/login.ts"
    assert result.adoptable_paths[0].reason == "nearest_indexed_ancestor_within_two_levels"


def test_classifies_nearest_of_multiple_indexed_ancestors_as_adoptable(tmp_path: Path) -> None:
    generation_id = _seed_indexed_path(tmp_path)
    with closing(connect_cognition_db(tmp_path)) as conn:
        conn.execute(
            "INSERT INTO evidence(id, generation_id, source_kind, source_path, commit_sha, span, extractor, content_hash, captured_at, attrs_json) "
            "VALUES ('E-payments', ?, 'file', 'src/auth/payments/index.ts', 'abc123', '1-40', 'test', 'hash-payments', '2026-05-13T00:00:00Z', '{}')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO nodes(id, generation_id, type, title, confidence, attrs_json, created_at, updated_at) "
            "VALUES ('capability:auth.payments', ?, 'capability', 'Auth payments', 'strong', '{}', '2026-05-13T00:00:00Z', '2026-05-13T00:00:00Z')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO path_index(id, generation_id, path, node_id, relation, confidence, evidence_id, updated_at) "
            "VALUES ('P-payments', ?, 'src/auth/payments/index.ts', 'capability:auth.payments', 'implements', 'strong', 'E-payments', '2026-05-13T00:00:00Z')",
            (generation_id,),
        )
        conn.commit()

    with closing(connect_cognition_db(tmp_path)) as conn:
        result = classify_path_coverage(
            conn,
            generation_id,
            missing_paths=["src/auth/payments/deep/new.ts"],
            requested_paths=["src/auth/payments/deep/new.ts"],
        )

    assert result.query_coverage == "adoptable_path_gap"
    assert result.adoptable_paths[0].node_id == "capability:auth.payments"
    assert result.adoptable_paths[0].nearest_indexed_sibling == "src/auth/payments/index.ts"


def test_classifies_small_shared_top_level_gap_as_review(tmp_path: Path) -> None:
    generation_id = _seed_indexed_path(tmp_path)
    with closing(connect_cognition_db(tmp_path)) as conn:
        result = classify_path_coverage(
            conn,
            generation_id,
            missing_paths=["src/payments/invoice.ts"],
            requested_paths=["src/payments/invoice.ts"],
        )

    assert result.query_coverage == "uncertain_path_gap"
    assert result.recommended_next_action == "perform_minimal_live_reads"
    assert result.adoptable_paths == []
    assert result.review_paths == ["src/payments/invoice.ts"]
    assert result.unadoptable_paths == []


def test_classifies_ordinary_unknown_subproject_batch_as_review(tmp_path: Path) -> None:
    generation_id = _seed_indexed_path(tmp_path)
    missing_paths = [
        "provider-lab/web/src/App.tsx",
        "provider-lab/web/src/components/providers/ProviderList.tsx",
        "provider-lab/web/tests/provider-lab.smoke.ts",
        "provider-lab/web/tests/smoke/provider-lab.test.tsx",
        "provider-lab/RELEASE-CHECKLIST.md",
        "provider-lab/web/src/components/providers/ProviderDetail.tsx",
    ]

    with closing(connect_cognition_db(tmp_path)) as conn:
        result = classify_path_coverage(
            conn,
            generation_id,
            missing_paths=missing_paths,
            requested_paths=missing_paths,
        )

    assert result.query_coverage == "uncertain_path_gap"
    assert result.recommended_next_action == "perform_minimal_live_reads"
    assert result.adoptable_paths == []
    assert result.review_paths == missing_paths
    assert result.unadoptable_paths == []
    assert any("more than 5" in reason for reason in result.reasons)


def test_classifies_many_unrelated_missing_paths_as_review(tmp_path: Path) -> None:
    generation_id = _seed_indexed_path(tmp_path)
    missing_paths = [f"new_system_{index}/entry.py" for index in range(26)]

    with closing(connect_cognition_db(tmp_path)) as conn:
        result = classify_path_coverage(
            conn,
            generation_id,
            missing_paths=missing_paths,
            requested_paths=missing_paths,
        )

    assert result.query_coverage == "uncertain_path_gap"
    assert result.recommended_next_action == "perform_minimal_live_reads"
    assert result.adoptable_paths == []
    assert result.review_paths == missing_paths
    assert result.unadoptable_paths == []
    assert any("more than 25" in reason for reason in result.reasons)


def test_core_surface_without_indexed_sibling_requires_review(tmp_path: Path) -> None:
    generation_id = _seed_indexed_path(tmp_path)

    with closing(connect_cognition_db(tmp_path)) as conn:
        result = classify_path_coverage(
            conn,
            generation_id,
            missing_paths=["scripts/release/package.ps1"],
            requested_paths=["scripts/release/package.ps1"],
        )

    assert result.query_coverage == "uncertain_path_gap"
    assert result.recommended_next_action == "perform_minimal_live_reads"
    assert result.adoptable_paths == []
    assert result.review_paths == ["scripts/release/package.ps1"]
    assert result.unadoptable_paths == []
    assert any("core live surface" in reason for reason in result.reasons)


def test_package_manifest_without_indexed_sibling_requires_review(tmp_path: Path) -> None:
    generation_id = _seed_indexed_path(tmp_path)

    with closing(connect_cognition_db(tmp_path)) as conn:
        result = classify_path_coverage(
            conn,
            generation_id,
            missing_paths=["package.json"],
            requested_paths=["package.json"],
        )

    assert result.query_coverage == "uncertain_path_gap"
    assert result.recommended_next_action == "perform_minimal_live_reads"
    assert result.review_paths == ["package.json"]
    assert result.unadoptable_paths == []


def test_active_generation_without_indexed_paths_is_unusable(tmp_path: Path) -> None:
    ensure_cognition_db(tmp_path)
    generation_id = seed_active_generation(tmp_path, source_commit="abc123")

    with closing(connect_cognition_db(tmp_path)) as conn:
        result = classify_path_coverage(
            conn,
            generation_id,
            missing_paths=["src/auth/session.ts"],
            requested_paths=["src/auth/session.ts"],
        )

    assert result.query_coverage == "unadoptable_path_gap"
    assert result.recommended_next_action == "run_map_scan_build"
    assert result.unadoptable_paths == ["src/auth/session.ts"]
    assert result.reasons == ["active generation has no path_index rows to adopt from"]
