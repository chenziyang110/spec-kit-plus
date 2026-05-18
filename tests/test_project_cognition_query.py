from contextlib import closing
from pathlib import Path

import pytest

from specify_cli.cognition import (
    connect_cognition_db,
    ensure_cognition_db,
    project_cognition_lexicon,
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
        conn.execute("INSERT INTO node_evidence(node_id, evidence_id) VALUES ('capability:auth.login', 'E-login')")
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
            "INSERT INTO entrypoint_index(id, generation_id, entrypoint_key, entrypoint_type, node_id, capability_id, path, evidence_id, confidence) "
            "VALUES ('EP-login', ?, 'auth.login', 'handler', 'capability:auth.login', 'capability:auth.login', 'src/auth/login.ts', 'E-login', 'strong')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO test_index(id, generation_id, test_path, test_name, node_id, capability_id, verification_node_id, evidence_id, confidence) "
            "VALUES ('T-login', ?, 'tests/auth/test_login.py', 'test_login_accepts_valid_credentials', 'capability:auth.login', 'capability:auth.login', 'verification:auth.login', 'E-login', 'strong')",
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
        conn.execute(
            "INSERT INTO query_examples(id, generation_id, query_text, intent, expected_target_type, expected_target_id, language, source, created_at) "
            "VALUES ('Q-login-debug', ?, 'debug failed login', 'debug', 'capability', 'capability:auth.login', 'en', 'test', '2026-05-13T00:00:00Z')",
            (generation_id,),
        )
        conn.commit()
    return generation_id


def _seed_api_version_graph(project_root: Path) -> str:
    ensure_cognition_db(project_root)
    generation_id = seed_active_generation(project_root, source_commit="abc123")
    with closing(connect_cognition_db(project_root)) as conn:
        conn.execute(
            "INSERT INTO evidence(id, generation_id, source_kind, source_path, commit_sha, span, extractor, content_hash, captured_at, attrs_json) "
            "VALUES ('E-api', ?, 'file', 'apps/relay-server/src/handlers/routes.ts', 'abc123', '1-120', 'test', 'hash-api', '2026-05-13T00:00:00Z', '{}')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO nodes(id, generation_id, type, title, confidence, attrs_json, created_at, updated_at) "
            "VALUES ('node-rest-api', ?, 'capability', 'REST API versioning', 'strong', '{}', '2026-05-13T00:00:00Z', '2026-05-13T00:00:00Z')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO alias_index(id, generation_id, alias, normalized_alias, target_type, target_id, language, source, confidence, evidence_id) "
            "VALUES ('A-api-version', ?, 'api version', 'api version', 'capability', 'node-rest-api', 'en', 'evidence', 'strong', 'E-api')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO alias_index(id, generation_id, alias, normalized_alias, target_type, target_id, language, source, confidence, evidence_id) "
            "VALUES ('A-rest-api', ?, 'REST API', 'rest api', 'capability', 'node-rest-api', 'en', 'evidence', 'strong', 'E-api')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO path_index(id, generation_id, path, node_id, relation, confidence, evidence_id, updated_at) "
            "VALUES ('P-api', ?, 'apps/relay-server/src/handlers/routes.ts', 'node-rest-api', 'implements', 'strong', 'E-api', '2026-05-13T00:00:00Z')",
            (generation_id,),
        )
        conn.execute(
            "INSERT INTO symbol_index(id, generation_id, symbol_name, normalized_symbol, node_id, path, relation, evidence_id, confidence) "
            "VALUES ('S-api-handler', ?, 'createV2Handler', 'createv2handler', 'node-rest-api', 'apps/relay-server/src/handlers/routes.ts', 'implements', 'E-api', 'strong')",
            (generation_id,),
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


def test_query_normalizes_project_absolute_paths_before_path_index_lookup(tmp_path: Path) -> None:
    _seed_login_graph(tmp_path)
    absolute_path = tmp_path / "src" / "auth" / "login.ts"

    result = query_project_cognition(tmp_path, intent="implement", query_text="", paths=[str(absolute_path)])

    assert result["readiness"] == "ready"
    assert result["query_plan"]["paths"] == ["src/auth/login.ts"]
    assert result["affected_nodes"] == ["capability:auth.login"]
    assert result["minimal_live_reads"] == ["src/auth/login.ts"]
    assert result["missing_coverage"] == []


def test_query_reports_needs_update_when_path_is_missing_from_index(tmp_path: Path) -> None:
    _seed_login_graph(tmp_path)

    result = query_project_cognition(tmp_path, intent="debug", query_text="", paths=["src/auth/missing.ts"])

    assert result["readiness"] == "needs_rebuild"
    assert result["recommended_next_action"] == "run_map_scan_build"
    assert result["missing_coverage"] == ["path not covered by project cognition index: src/auth/missing.ts"]


def test_query_reports_needs_update_when_path_is_missing_even_with_query_candidate(tmp_path: Path) -> None:
    _seed_login_graph(tmp_path)

    result = query_project_cognition(tmp_path, intent="debug", query_text="login", paths=["src/auth/missing.ts"])

    assert result["readiness"] == "needs_rebuild"
    assert result["recommended_next_action"] == "run_map_scan_build"
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


def test_lexicon_returns_map_terms_for_agent_query_planning(tmp_path: Path) -> None:
    _seed_api_version_graph(tmp_path)

    result = project_cognition_lexicon(tmp_path, intent="plan", query_text="v1 v2接口很乱啊，能不能统一用最新的")

    assert result["readiness"] == "ready"
    assert result["intent"] == "plan"
    assert result["query"] == "v1 v2接口很乱啊，能不能统一用最新的"
    assert result["terms"][0]["node_id"] == "node-rest-api"
    assert result["terms"][0]["title"] == "REST API versioning"
    assert "api version" in result["terms"][0]["aliases"]
    assert "REST API" in result["terms"][0]["aliases"]
    assert "apps/relay-server/src/handlers/routes.ts" in result["terms"][0]["paths"]
    assert "createV2Handler" in result["terms"][0]["symbols"]
    assert "api" in result["available_terms"]
    assert result["query_planning_contract"]["agent_responsibility"] == "translate raw user intent using this lexicon"


def test_lexicon_default_returns_complete_keyword_mapping(tmp_path: Path) -> None:
    generation_id = _seed_api_version_graph(tmp_path)
    with closing(connect_cognition_db(tmp_path)) as conn:
        for index in range(25):
            node_id = f"node-filler-{index:02d}"
            conn.execute(
                "INSERT INTO nodes(id, generation_id, type, title, confidence, attrs_json, created_at, updated_at) "
                "VALUES (?, ?, 'capability', ?, 'medium', '{}', '2026-05-13T00:00:00Z', '2026-05-13T00:00:00Z')",
                (node_id, generation_id, f"Filler capability {index:02d}"),
            )
            conn.execute(
                "INSERT INTO alias_index(id, generation_id, alias, normalized_alias, target_type, target_id, language, source, confidence, evidence_id) "
                "VALUES (?, ?, ?, ?, 'capability', ?, 'en', 'evidence', 'medium', 'E-api')",
                (f"A-filler-{index:02d}", generation_id, f"filler-{index:02d}", f"filler-{index:02d}", node_id),
            )
        conn.commit()

    result = project_cognition_lexicon(tmp_path, intent="plan", query_text="接口版本太乱了，统一用最新的")

    term_ids = {term["node_id"] for term in result["terms"]}
    assert "node-rest-api" in term_ids
    assert len(term_ids) == 26


def test_query_consumes_agent_expanded_queries(tmp_path: Path) -> None:
    _seed_api_version_graph(tmp_path)

    result = query_project_cognition(
        tmp_path,
        intent="plan",
        query_text="v1 v2接口很乱啊，能不能统一用最新的",
        expanded_queries=["api version", "REST API version consolidation", "latest interface"],
        paths=["apps\\relay-server\\src\\handlers\\routes.ts"],
    )

    assert result["readiness"] == "ready"
    assert result["capability_candidates"][0]["node_id"] == "node-rest-api"
    assert "expanded_query:api version" in result["capability_candidates"][0]["matched_by"]
    assert result["query_plan"]["raw_query"] == "v1 v2接口很乱啊，能不能统一用最新的"
    assert "api version" in result["query_plan"]["expanded_queries"]
    assert result["query_plan"]["paths"] == ["apps/relay-server/src/handlers/routes.ts"]
    assert result["minimal_live_reads"] == ["apps/relay-server/src/handlers/routes.ts"]


def test_query_echoes_selected_and_rejected_concepts_in_query_plan(tmp_path: Path) -> None:
    _seed_login_graph(tmp_path)

    result = query_project_cognition(
        tmp_path,
        intent="debug",
        query_text="login",
        selected_concepts=["capability:auth.login"],
        rejected_concepts=["capability:admin.sso_login"],
        selection_reason="user selected the login capability from lexicon candidates",
    )

    assert result["readiness"] == "ready"
    assert result["selected_concepts"] == ["capability:auth.login"]
    assert result["rejected_concepts"] == ["capability:admin.sso_login"]
    assert result["selection_reason"] == "user selected the login capability from lexicon candidates"
    assert result["query_plan"]["selected_concepts"] == ["capability:auth.login"]
    assert result["query_plan"]["rejected_concepts"] == ["capability:admin.sso_login"]
    assert result["query_plan"]["selection_reason"] == "user selected the login capability from lexicon candidates"


def test_query_unknown_selected_concept_routes_review_or_update(tmp_path: Path) -> None:
    _seed_login_graph(tmp_path)

    review = query_project_cognition(
        tmp_path,
        intent="debug",
        query_text="",
        selected_concepts=["capability:auth.missing"],
    )
    needs_update = query_project_cognition(
        tmp_path,
        intent="debug",
        query_text="",
        selected_concepts=["capability:auth.missing"],
        paths=["src/auth/missing.ts"],
    )

    assert review["readiness"] == "review"
    assert review["recommended_next_action"] == "perform_minimal_live_reads"
    assert "selected concept not covered by active generation: capability:auth.missing" in review["missing_coverage"]
    assert needs_update["readiness"] == "needs_rebuild"
    assert needs_update["recommended_next_action"] == "run_map_scan_build"
    assert "selected concept not covered by active generation: capability:auth.missing" in needs_update["missing_coverage"]


def test_query_selected_and_rejected_conflict_is_ambiguous_without_affected_nodes(tmp_path: Path) -> None:
    _seed_login_graph(tmp_path)

    result = query_project_cognition(
        tmp_path,
        intent="debug",
        query_text="login",
        selected_concepts=["capability:auth.login"],
        rejected_concepts=["capability:auth.login"],
    )

    assert result["readiness"] == "ambiguous"
    assert result["recommended_next_action"] == "ask_user_to_select_candidate"
    assert "concept selected and rejected: capability:auth.login" in result["missing_coverage"]
    assert result["affected_nodes"] == []
    assert result["route_pack"]["items"] == []


def test_query_selected_concept_without_route_evidence_returns_review(tmp_path: Path) -> None:
    ensure_cognition_db(tmp_path)
    generation_id = seed_active_generation(tmp_path, source_commit="abc123")
    with closing(connect_cognition_db(tmp_path)) as conn:
        conn.execute(
            "INSERT INTO nodes(id, generation_id, type, title, confidence, attrs_json, created_at, updated_at) "
            "VALUES ('capability:route.missing', ?, 'capability', 'Missing route', 'strong', '{}', '2026-05-13T00:00:00Z', '2026-05-13T00:00:00Z')",
            (generation_id,),
        )
        conn.commit()

    result = query_project_cognition(
        tmp_path,
        intent="implement",
        query_text="missing route",
        selected_concepts=["capability:route.missing"],
    )

    assert result["readiness"] == "review"
    assert result["recommended_next_action"] == "perform_minimal_live_reads"
    assert result["route_pack"]["items"] == []
    assert "route_pack has no evidence-backed route items for affected nodes" in result["missing_coverage"]


def test_query_rejected_concept_suppresses_alias_and_path_candidates(tmp_path: Path) -> None:
    _seed_login_graph(tmp_path)

    result = query_project_cognition(
        tmp_path,
        intent="debug",
        query_text="login",
        paths=["src/auth/login.ts"],
        rejected_concepts=["capability:auth.login"],
    )

    assert result["readiness"] == "review"
    assert result["capability_candidates"] == []
    assert result["affected_nodes"] == []
    assert result["minimal_live_reads"] == []
    assert result["route_pack"]["items"] == []


def test_lexicon_exposes_concept_candidates_with_examples_and_evidence(tmp_path: Path) -> None:
    _seed_login_graph(tmp_path)

    result = project_cognition_lexicon(tmp_path, intent="debug", query_text="login")

    candidate = next(item for item in result["concept_candidates"] if item["concept_id"] == "capability:auth.login")
    assert candidate["label"] == "User login"
    assert candidate["kind"] == "capability"
    assert candidate["domain"]
    assert "login" in candidate["matched_terms"]
    assert candidate["target_type"] == "capability"
    assert "login" in candidate["aliases"]
    assert "debug failed login" in candidate["colloquial_matches"]
    assert "debug failed login" in candidate["query_examples"]
    assert candidate["target_nodes"] == ["capability:auth.login"]
    assert "symbol:AuthService.login" in candidate["related_concepts"]
    assert candidate["disambiguation_hint"]
    assert candidate["evidence_ids"] == ["E-login"]
    assert candidate["agent_responsibility"] == "select concept_id values for query_plan selected_concepts or rejected_concepts"


def test_query_route_pack_uses_object_route_items(tmp_path: Path) -> None:
    _seed_login_graph(tmp_path)

    result = query_project_cognition(tmp_path, intent="debug", query_text="login")

    route_pack = result["route_pack"]
    assert route_pack["minimal_live_reads"] == result["minimal_live_reads"]
    assert route_pack["why_these_reads"]
    assert "owner_files" in route_pack
    assert "entry_files" in route_pack
    assert "tests" in route_pack
    assert route_pack["entry_files"]
    assert route_pack["tests"]
    item = route_pack["items"][0]
    assert item["path"] == "src/auth/login.ts"
    assert item["relation"] == "implements"
    assert item["reason"]
    assert item["evidence_ids"] == ["E-login"]
    assert item["confidence"] == "strong"
    assert item["node_id"] == "capability:auth.login"


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
