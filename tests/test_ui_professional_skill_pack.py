from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "templates" / "ui-professional-skills"
CATALOG = PACK / "catalog.json"
ROUTER = PACK / "router.md"
ROUTE_SCRIPT = PACK / "route.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _catalog() -> dict[str, object]:
    payload = json.loads(_read(CATALOG))
    assert isinstance(payload, dict)
    return payload


def _route(
    query: str,
    *,
    style_authority: str | None = None,
) -> dict[str, object]:
    argv = [sys.executable, str(ROUTE_SCRIPT), "--query", query]
    if style_authority is not None:
        argv.extend(["--style-authority", style_authority])
    completed = subprocess.run(
        argv,
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    payload = json.loads(completed.stdout)
    assert isinstance(payload, dict)
    return payload


def test_ui_professional_catalog_is_bounded_and_all_references_exist() -> None:
    catalog = _catalog()

    assert catalog["schema_version"] == 1
    assert catalog["catalog_id"] == "spec-kit-ui-professional-v1"
    routing = catalog["routing"]
    assert isinstance(routing, dict)
    assert routing == {
        "domain_limit": 1,
        "style_limit": 1,
        "specialist_limit": 2,
        "fallback_domain": "domain-general-interface",
        "ambiguity_policy": "ask-one-high-impact-question",
    }

    sources = catalog["sources"]
    assert isinstance(sources, list)
    source_ids = {
        source["id"]
        for source in sources
        if isinstance(source, dict) and isinstance(source.get("id"), str)
    }
    for required in (
        "anthropic-frontend-design",
        "openai-skill-creator",
        "ui-ux-pro-max",
        "impeccable",
        "taste-skill",
        "emil-design-engineering",
        "vercel-web-guidelines",
    ):
        assert required in source_ids

    skills = catalog["skills"]
    assert isinstance(skills, list)
    ids = [skill["id"] for skill in skills if isinstance(skill, dict)]
    assert len(ids) == len(set(ids))

    by_kind: dict[str, list[dict[str, object]]] = {
        "domain": [],
        "style": [],
        "specialist": [],
    }
    for raw_skill in skills:
        assert isinstance(raw_skill, dict)
        kind = raw_skill["kind"]
        assert kind in by_kind
        by_kind[kind].append(raw_skill)
        assert raw_skill["source_ids"]
        assert set(raw_skill["source_ids"]).issubset(source_ids)
        triggers = raw_skill["triggers"]
        assert isinstance(triggers, dict)
        assert triggers["phrases"]
        assert any(
            any("\u4e00" <= char <= "\u9fff" for char in phrase)
            for phrase in triggers["phrases"]
        )
        reference = ROOT / "templates" / raw_skill["ref"]
        assert reference.is_file(), (raw_skill["id"], reference)
        slug = raw_skill["id"].removeprefix(f"{kind}-")
        expected_ref = (
            f"design-library/{slug}.md"
            if kind == "style"
            else f"ui-professional-skills/{kind}s/{slug}.md"
        )
        assert raw_skill["ref"] == expected_ref

    assert len(by_kind["domain"]) >= 8
    assert len(by_kind["style"]) >= 8
    assert len(by_kind["specialist"]) >= 6
    assert routing["fallback_domain"] in ids


def test_router_uses_sparse_progressive_disclosure_and_one_question() -> None:
    content = _read(ROUTER).lower()

    for phrase in (
        "read `catalog.json` first",
        "exactly one domain",
        "zero or one style",
        "zero to two specialists",
        "do not load every",
        "one high-impact question",
        "resume the pinned route",
        "image-primary",
        "html-primary",
        "professional_skill_route",
        "approved references",
    ):
        assert phrase in content


def test_router_matches_representative_gui_requests() -> None:
    data_ops = _route("B2B SaaS 数据后台，实时指标、告警、趋势图和筛选器")
    assert data_ops["selection"]["domain_skill_id"] == "domain-data-operations"
    assert "specialist-data-visualization" in data_ops["selection"]["specialist_skill_ids"]

    commerce = _route("奢侈品电商首页，商品故事、购物车和购买转化")
    assert commerce["selection"]["domain_skill_id"] == "domain-commerce-service"
    assert commerce["selection"]["style_skill_id"] in {
        "style-commerce-tactile",
        "style-soft-premium-calm",
    }
    assert "specialist-forms-conversion" in commerce["selection"]["specialist_skill_ids"]

    editorial = _route("新闻杂志阅读网站，长篇内容、专题和作者页面")
    assert editorial["selection"]["domain_skill_id"] == "domain-content-editorial"
    assert editorial["selection"]["style_skill_id"] == "style-marketing-editorial-asymmetric"

    assistant = _route("AI 聊天助手工作台，流式回复、引用和工具调用")
    assert assistant["selection"]["domain_skill_id"] == "domain-product-workspace"
    assert "specialist-conversational-ai" in assistant["selection"]["specialist_skill_ids"]

    for payload in (data_ops, commerce, editorial, assistant):
        selection = payload["selection"]
        assert isinstance(selection, dict)
        assert len(selection["specialist_skill_ids"]) <= 2
        assert payload["load_refs"]
        assert len(payload["load_refs"]) <= 4
        persisted = payload["professional_skill_route"]
        assert persisted["status"] == "resolved"
        assert persisted["domain_skill_id"] == selection["domain_skill_id"]
        assert persisted["style_skill_id"] == selection["style_skill_id"]
        assert persisted["specialist_skill_ids"] == selection["specialist_skill_ids"]
        assert persisted["loaded_refs"] == payload["load_refs"]


def test_router_reports_material_ambiguity_instead_of_loading_both_styles() -> None:
    payload = _route("品牌官网，要极简高端，也要粗野实验感")

    assert payload["question_required"] is True
    assert payload["ambiguities"]
    assert payload["selection"]["style_skill_id"] is None
    assert len(payload["load_refs"]) == 1
    persisted = payload["professional_skill_route"]
    assert persisted["status"] == "question-required"
    assert persisted["unresolved_candidates"]


def test_router_keeps_local_existing_ui_authoritative_over_style_matches() -> None:
    payload = _route(
        "奢侈品电商订单详情页，做成高端编辑感并强化转化",
        style_authority="inherit-existing",
    )

    assert payload["style_authority"] == "inherit-existing"
    assert payload["selection"]["domain_skill_id"] == "domain-commerce-service"
    assert payload["selection"]["style_skill_id"] is None
    assert all(
        not str(reference).startswith("design-library/")
        for reference in payload["load_refs"]
    )
    assert payload["professional_skill_route"]["style_skill_id"] is None


def test_design_workflows_route_to_the_shared_professional_pack() -> None:
    classic = _read(ROOT / "templates" / "command-partials" / "design" / "shell.md")
    passive = _read(
        ROOT / "templates" / "passive-skills" / "spec-kit-ui-design" / "SKILL.md"
    )
    advanced = _read(
        ROOT / "templates" / "advanced-skills" / "spx-design" / "SKILL.md"
    )
    advanced_gate = _read(
        ROOT / "templates" / "advanced-skills" / "_shared" / "ui-quality-gate.md"
    )

    for content in (classic, passive, advanced, advanced_gate):
        lowered = content.lower()
        assert "ui-professional-skills/router.md" in lowered
        assert "professional_skill_route" in lowered
        assert "domain_skill_id" in lowered
        assert "style_skill_id" in lowered
        assert "specialist_skill_ids" in lowered
        assert "load only" in lowered or "only load" in lowered


def test_design_artifacts_persist_the_resolved_professional_route() -> None:
    brief = _read(ROOT / "templates" / "design-brief-template.md")
    classic_change = _read(ROOT / "templates" / "design-change-template.md")
    advanced_change = _read(
        ROOT
        / "templates"
        / "advanced-skills"
        / "spx-design"
        / "assets"
        / "design-change.md"
    )
    legacy = _read(ROOT / "templates" / "design-template.md")

    for content in (brief, classic_change, advanced_change, legacy):
        assert "professional_skill_route:" in content
        assert "domain_skill_id:" in content
        assert "style_skill_id:" in content
        assert "specialist_skill_ids:" in content
        assert "matched_signals:" in content
        assert "loaded_refs:" in content

    scaffold = _read(ROOT / "tools" / "specify-runtime" / "artifact_scaffold.go")
    start = scaffold.index('"design-brief"')
    end = scaffold.index('"design-review"', start)
    assert '"professional_skill_route"' in scaffold[start:end]


def test_ui_professional_pack_is_bundled_for_source_and_wheel_installs() -> None:
    pyproject = _read(ROOT / "pyproject.toml")
    assert (
        '"templates/ui-professional-skills" = '
        '"specify_cli/core_pack/templates/ui-professional-skills"'
    ) in pyproject

    for path in (
        ROOT / "README.md",
        ROOT / "PROJECT-HANDBOOK.md",
        ROOT / "templates" / "project-handbook-template.md",
        ROOT / "AGENTS.md",
    ):
        content = _read(path).lower()
        assert "ui professional skill" in content or "ui 专业技能" in content, path
        assert "progressive disclosure" in content or "渐进" in content, path


def test_shared_infra_install_copies_the_runnable_professional_pack(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from specify_cli import _install_shared_infra

    monkeypatch.setattr(
        "specify_cli.launcher.write_project_specify_launcher_config",
        lambda *args, **kwargs: None,
    )
    project = tmp_path / "project"
    project.mkdir()

    assert _install_shared_infra(project, "ps") is True
    installed = project / ".specify" / "templates" / "ui-professional-skills"
    assert (installed / "catalog.json").is_file()
    assert (installed / "router.md").is_file()
    assert (installed / "domains" / "product-workspace.md").is_file()

    completed = subprocess.run(
        [
            sys.executable,
            str(installed / "route.py"),
            "--query",
            "桌面端专业工作台和组件库",
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    payload = json.loads(completed.stdout)
    assert payload["selection"]["domain_skill_id"] == "domain-product-workspace"
    assert "specialist-design-system" in payload["selection"]["specialist_skill_ids"]
