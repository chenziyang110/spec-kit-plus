from contextlib import closing
from pathlib import Path

import pytest

from specify_cli.cognition import (
    connect_cognition_db,
    ensure_cognition_db,
    query_project_cognition,
    seed_active_generation,
)


def _seed_login_graph(project_root: Path) -> str:
    ensure_cognition_db(project_root)
    generation_id = seed_active_generation(project_root, source_commit="abc123")
    with closing(connect_cognition_db(project_root)) as conn:
        conn.execute(
            "INSERT INTO evidence(id, generation_id, source_kind, source_path, commit_sha, span, extractor, content_hash, captured_at, attrs_json) "
            "VALUES ('E-login', ?, 'file', 'src/auth/login.ts', 'abc123', '1-80', 'test', 'hash-login', '2026-05-13T00:00:00Z', '{}')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO nodes(id, generation_id, type, title, confidence, attrs_json, created_at, updated_at) "
            "VALUES ('capability:auth.login', ?, 'capability', 'User login', 'strong', '{}', '2026-05-13T00:00:00Z', '2026-05-13T00:00:00Z')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO nodes(id, generation_id, type, title, confidence, attrs_json, created_at, updated_at) "
            "VALUES ('symbol:AuthService.login', ?, 'symbol', 'AuthService.login', 'strong', '{}', '2026-05-13T00:00:00Z', '2026-05-13T00:00:00Z')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO alias_index(id, generation_id, alias, normalized_alias, target_type, target_id, language, source, confidence, evidence_id) "
            "VALUES ('A-login', ?, 'login', 'login', 'capability', 'capability:auth.login', 'en', 'evidence', 'strong', 'E-login')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO alias_index(id, generation_id, alias, normalized_alias, target_type, target_id, language, source, confidence, evidence_id) "
            "VALUES ('A-login-zh', ?, '登录', '登录', 'capability', 'capability:auth.login', 'zh', 'evidence', 'strong', 'E-login')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO alias_index(id, generation_id, alias, normalized_alias, target_type, target_id, language, source, confidence, evidence_id) "
            "VALUES ('A-valid-password', ?, '正确密码登录失败', '正确密码登录失败', 'symptom', 'symptom:valid_credentials_rejected', 'zh', 'evidence', 'strong', 'E-login')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO path_index(id, generation_id, path, node_id, relation, confidence, evidence_id, updated_at) "
            "VALUES ('P-login', ?, 'src/auth/login.ts', 'capability:auth.login', 'implements', 'strong', 'E-login', '2026-05-13T00:00:00Z')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO symbol_index(id, generation_id, symbol_name, normalized_symbol, node_id, path, relation, evidence_id, confidence) "
            "VALUES ('S-auth-service', ?, 'AuthService.login', 'authservice.login', 'symbol:AuthService.login', 'src/auth/login.ts', 'implements', 'E-login', 'strong')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO edges(id, generation_id, type, source_id, target_id, confidence, attrs_json, created_at, updated_at) "
            "VALUES ('edge:login-service', ?, 'implements', 'capability:auth.login', 'symbol:AuthService.login', 'strong', '{}', '2026-05-13T00:00:00Z', '2026-05-13T00:00:00Z')",
            (generation_id,),
        )
        conn.execute("INSERT INTO edge_evidence(edge_id, evidence_id) VALUES ('edge:login-service', 'E-login')")
        conn.execute(
            "INSERT INTO claims(id, generation_id, subject_ref, predicate, object_ref, object_value, truth_layer, confidence, status, last_validated_at, attrs_json) "
            "VALUES ('claim:login-implementation', ?, 'capability:auth.login', 'implemented_by', 'symbol:AuthService.login', '', 'implementation_reality', 'strong', 'active', '2026-05-13T00:00:00Z', '{}')",
            (generation_id,),
        )
        conn.execute("INSERT INTO claim_evidence(claim_id, evidence_id) VALUES ('claim:login-implementation', 'E-login')")
        conn.execute(
            "INSERT INTO claim_fts(claim_id, subject_ref, predicate, object_text, content) "
            "VALUES ('claim:login-implementation', 'capability:auth.login', 'implemented_by', 'AuthService.login', 'login AuthService valid password')"
        )
        conn.commit()
    return generation_id


def test_query_resolves_login_by_alias_with_evidence_trace(tmp_path: Path) -> None:
    _seed_login_graph(tmp_path)

    result = query_project_cognition(tmp_path, intent="debug", query_text="正确密码登录失败", paths=[])

    assert result["readiness"] == "ready"
    assert result["capability_candidates"][0]["node_id"] == "capability:auth.login"
    assert "alias:登录" in result["capability_candidates"][0]["matched_by"]
    assert result["capability_candidates"][0]["evidence_ids"] == ["E-login"]
    assert "src/auth/login.ts" in result["minimal_live_reads"]


def test_query_resolves_by_path_when_paths_are_known(tmp_path: Path) -> None:
    _seed_login_graph(tmp_path)

    result = query_project_cognition(tmp_path, intent="implement", query_text="", paths=["src/auth/login.ts"])

    assert result["readiness"] == "ready"
    assert result["affected_nodes"] == ["capability:auth.login"]
    assert result["minimal_live_reads"] == ["src/auth/login.ts"]


def test_query_reports_needs_update_when_path_is_missing_from_index(tmp_path: Path) -> None:
    _seed_login_graph(tmp_path)

    result = query_project_cognition(tmp_path, intent="debug", query_text="", paths=["src/auth/missing.ts"])

    assert result["readiness"] == "needs_update"
    assert result["recommended_next_action"] == "run_map_update"
    assert result["missing_coverage"] == ["path not covered by project cognition index: src/auth/missing.ts"]


def test_query_reports_needs_update_when_path_is_missing_even_with_query_candidate(tmp_path: Path) -> None:
    _seed_login_graph(tmp_path)

    result = query_project_cognition(tmp_path, intent="debug", query_text="login", paths=["src/auth/missing.ts"])

    assert result["readiness"] == "needs_update"
    assert result["recommended_next_action"] == "run_map_update"
    assert result["missing_coverage"] == ["path not covered by project cognition index: src/auth/missing.ts"]


def test_query_returns_review_when_text_misses_but_runtime_has_baseline(tmp_path: Path) -> None:
    _seed_login_graph(tmp_path)

    result = query_project_cognition(tmp_path, intent="plan", query_text="接口版本混乱", paths=[])

    assert result["readiness"] == "review"
    assert result["recommended_next_action"] == "perform_minimal_live_reads"
    assert result["minimal_live_reads"] == ["src/auth/login.ts"]
    assert result["missing_coverage"] == [
        "query did not match project cognition aliases or claims; use minimal live reads or ask a clarifying question"
    ]


@pytest.mark.parametrize(
    "query_text",
    [
        "AuthService.login",
        "foo-bar",
        "capability:auth.login",
        "src/auth/login.ts",
        "login:",
        "login - password",
    ],
)
def test_query_tolerates_punctuation_heavy_fts_input(tmp_path: Path, query_text: str) -> None:
    _seed_login_graph(tmp_path)

    result = query_project_cognition(tmp_path, intent="debug", query_text=query_text, paths=[])

    assert result["readiness"] in {"ready", "review"}


def test_query_reports_ambiguous_when_candidates_are_close(tmp_path: Path) -> None:
    generation_id = _seed_login_graph(tmp_path)
    with closing(connect_cognition_db(tmp_path)) as conn:
        conn.execute(
            "INSERT INTO nodes(id, generation_id, type, title, confidence, attrs_json, created_at, updated_at) "
            "VALUES ('capability:admin.sso_login', ?, 'capability', 'Admin SSO login', 'strong', '{}', '2026-05-13T00:00:00Z', '2026-05-13T00:00:00Z')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO alias_index(id, generation_id, alias, normalized_alias, target_type, target_id, language, source, confidence, evidence_id) "
            "VALUES ('A-admin-login', ?, 'login', 'login', 'capability', 'capability:admin.sso_login', 'en', 'evidence', 'strong', 'E-login')",
            (generation_id,),
        )
        conn.commit()

    result = query_project_cognition(tmp_path, intent="debug", query_text="login", paths=[])

    assert result["readiness"] == "ambiguous"
    assert result["recommended_next_action"] == "ask_user_to_select_candidate"
    assert {item["node_id"] for item in result["capability_candidates"]} == {
        "capability:auth.login",
        "capability:admin.sso_login",
    }
