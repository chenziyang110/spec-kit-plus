from __future__ import annotations

import json
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "templates" / "ui-professional-skills"
CATALOG = PACK / "catalog.json"
ROUTER = PACK / "router.md"
ROUTE_SCRIPT = PACK / "route.py"


def _load_route_module():
    spec = importlib.util.spec_from_file_location("ui_professional_route", ROUTE_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _catalog() -> dict[str, object]:
    payload = json.loads(_read(CATALOG))
    assert isinstance(payload, dict)
    return payload


def _assert_component_adoption_plan_row(
    row: dict[str, object], *, resource_id: str, action: str
) -> None:
    assert row["resource_id"] == resource_id
    assert row["action"] == action
    assert isinstance(row["package"], str)
    assert isinstance(row["version"], str)
    assert isinstance(row["license"], str)
    assert isinstance(row["source_ref"], str)
    component_refs = row["component_refs"]
    assert isinstance(component_refs, list)
    assert component_refs
    assert all(isinstance(item, str) and item for item in component_refs)
    reason_codes = row["reason_codes"]
    assert isinstance(reason_codes, list)
    assert reason_codes
    assert all(isinstance(item, str) and item for item in reason_codes)
    selection_basis_refs = row["selection_basis_refs"]
    assert isinstance(selection_basis_refs, list)
    assert selection_basis_refs
    assert all(isinstance(item, str) and item for item in selection_basis_refs)


def _route(
    query: str,
    *,
    style_authority: str | None = None,
    project_root: Path | None = None,
    catalog_path: Path | None = None,
) -> dict[str, object]:
    argv = [sys.executable, str(ROUTE_SCRIPT), "--query", query]
    if style_authority is not None:
        argv.extend(["--style-authority", style_authority])
    if project_root is not None:
        argv.extend(["--project-root", str(project_root)])
    if catalog_path is not None:
        argv.extend(["--catalog", str(catalog_path)])
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


def test_catalog_collects_mature_web_ui_resources_and_agent_materials() -> None:
    catalog = _catalog()

    resources = catalog["mature_web_ui_resources"]
    assert isinstance(resources, list)
    resource_ids = [resource["id"] for resource in resources if isinstance(resource, dict)]
    assert len(resource_ids) == len(set(resource_ids))
    resource_id_set = set(resource_ids)
    for required in (
        "shadcn-ui",
        "radix-primitives",
        "base-ui",
        "material-ui",
        "ant-design",
        "mantine",
        "chakra-ui",
        "headless-ui",
        "shadcn-agent-skill",
    ):
        assert required in resource_ids

    for resource in resources:
        assert resource["category"] in {
            "component-library",
            "headless-primitive",
            "design-system",
            "agent-resource",
        }
        assert resource["official_url"].startswith("https://")
        assert resource["maturity"] in {"default", "mature", "enterprise", "specialized"}
        assert resource["ecosystems"]
        assert resource["capabilities"]
        assert resource["use_when"]
        assert resource["guardrails"]
        assert set(resource.get("agent_resource_ids", [])).issubset(resource_id_set)


def test_catalog_defines_deterministic_asset_scan_scoring_and_smoothness_checks() -> None:
    catalog = _catalog()
    routing = catalog["mature_web_ui_routing"]

    assert routing["asset_scan"]["manifest_files"] == ["package.json"]
    assert "src/components/ui" in routing["asset_scan"]["component_roots"]
    assert routing["selection_scoring"]["installed"] > routing["selection_scoring"]["ecosystem"]
    assert routing["selection_scoring"]["ecosystem"] > routing["selection_scoring"]["maturity"]["enterprise"]
    assert routing["resource_package_markers"]["material-ui"] == ["@mui/material"]

    checks = routing["smoothness_acceptance_checks"]
    check_ids = {check["id"] for check in checks}
    assert {
        "focus-continuity",
        "selection-scroll-continuity",
        "pending-cancel-feedback",
        "duplicate-activation",
        "reduced-motion",
        "layout-stability",
        "large-data-performance",
        "editing-input-continuity",
        "interruption-safe-motion",
    } <= check_ids


def test_router_scans_live_ui_assets_and_prefers_the_installed_primary_system(
    tmp_path: Path,
) -> None:
    project = tmp_path / "react-app"
    (project / "src" / "components" / "ui").mkdir(parents=True)
    (project / "src" / "app").mkdir(parents=True)
    (project / "package.json").write_text(
        json.dumps(
            {
                "dependencies": {
                    "react": "^19.0.0",
                    "next": "^15.0.0",
                    "@mui/material": "^7.0.0",
                }
            }
        ),
        encoding="utf-8",
    )
    (project / "pnpm-lock.yaml").write_text("lockfileVersion: '9.0'\n", encoding="utf-8")
    (project / "tailwind.config.ts").write_text("export default {}\n", encoding="utf-8")
    (project / "src" / "app" / "page.tsx").write_text(
        "export default function Page() { return null }\n",
        encoding="utf-8",
    )

    payload = _route(
        "React Web 管理后台，需要成熟组件和无障碍表格",
        style_authority="inherit-existing",
        project_root=project,
    )

    inventory = payload["web_ui_asset_inventory"]
    assert inventory == {
        "status": "scanned",
        "manifest_refs": ["package.json"],
        "lockfile_refs": ["pnpm-lock.yaml"],
        "framework_ids": ["react"],
        "installed_resources": [
            {"resource_id": "material-ui", "version": "^7.0.0"}
        ],
        "component_roots": ["src/components/ui"],
        "token_refs": ["tailwind.config.ts"],
        "theme_refs": [],
        "surface_refs": ["src/app/page.tsx"],
    }
    selection = payload["mature_web_ui_selection"]
    assert selection["status"] == "provisional"
    assert selection["primary_resource_id"] == "material-ui"
    assert selection["candidates"][0]["resource_id"] == "material-ui"
    assert "installed" in selection["candidates"][0]["reason_codes"]
    assert "dependency-add-authorization-required" in selection["confirmation_codes"]
    adoption_plan = selection["component_adoption_plan"]
    assert [row["resource_id"] for row in adoption_plan] == ["material-ui", "ag-grid"]
    material_ui = adoption_plan[0]
    _assert_component_adoption_plan_row(
        material_ui,
        resource_id="material-ui",
        action="reuse",
    )
    assert material_ui["package"] == "@mui/material"
    assert material_ui["version"] == "^7.0.0"
    assert material_ui["permission_gate"] == "not-required"
    assert material_ui["permission_status"] == "authorized"
    ag_grid = adoption_plan[1]
    _assert_component_adoption_plan_row(
        ag_grid,
        resource_id="ag-grid",
        action="add",
    )
    assert ag_grid["permission_gate"] == "required"
    assert ag_grid["permission_status"] == "not-authorized"
    assert payload["professional_skill_route"]["status"] == "unresolved"
    assert payload["professional_skill_route"]["web_ui_asset_inventory"] == inventory
    assert payload["professional_skill_route"]["mature_web_ui_selection"] == selection


def test_router_library_api_exercises_deterministic_adoption_and_native_boundaries(
    tmp_path: Path,
) -> None:
    module = _load_route_module()
    project = tmp_path / "react-app"
    component_root = project / "src" / "components" / "ui"
    component_root.mkdir(parents=True)
    (component_root / "Grid.tsx").write_text(
        "export function Grid() { return null }\n", encoding="utf-8"
    )
    (project / "package.json").write_text(
        json.dumps(
            {
                "dependencies": {
                    "react": "^19.0.0",
                    "@mui/material": "^7.0.0",
                }
            }
        ),
        encoding="utf-8",
    )

    web = module.route(
        _catalog(),
        "React 数据工作台，需要十万行表格、富文本编辑和可中断动效",
        style_authority="inherit-existing",
        project_root=project,
    )
    adoption = web["mature_web_ui_selection"]["component_adoption_plan"]
    assert adoption[0]["resource_id"] == "local-components"
    assert any(row["action"] == "reuse" for row in adoption)
    assert any(row["action"] == "add" for row in adoption)
    assert web["smoothness_performance_budgets"]["inp_ms"] == 200

    native = module.route(_catalog(), "iOS SwiftUI 组件设计")
    assert native["mature_web_ui_selection"]["component_adoption_plan"] == []
    assert native["smoothness_performance_budgets"] == {}


def test_router_requires_confirmation_for_multiple_installed_primary_systems(
    tmp_path: Path,
) -> None:
    project = tmp_path / "react-app"
    project.mkdir()
    (project / "package.json").write_text(
        json.dumps(
            {
                "dependencies": {
                    "react": "^19.0.0",
                    "@mui/material": "^7.0.0",
                    "@chakra-ui/react": "^3.0.0",
                }
            }
        ),
        encoding="utf-8",
    )

    payload = _route(
        "React Web 管理后台，需要成熟组件",
        style_authority="inherit-existing",
        project_root=project,
    )

    selection = payload["mature_web_ui_selection"]
    assert selection["status"] == "provisional"
    assert "multiple-installed-primary-systems" in selection["confirmation_codes"]
    assert payload["professional_skill_route"]["status"] == "unresolved"


def test_router_asset_scan_rejects_catalog_paths_outside_the_project_root(
    tmp_path: Path,
) -> None:
    project = tmp_path / "react-app"
    project.mkdir()
    outside_token = tmp_path / "outside-tokens.css"
    outside_token.write_text(":root {}\n", encoding="utf-8")
    (project / "package.json").write_text(
        json.dumps({"dependencies": {"react": "^19.0.0"}}),
        encoding="utf-8",
    )
    catalog = _catalog()
    routing = catalog["mature_web_ui_routing"]
    assert isinstance(routing, dict)
    asset_scan = routing["asset_scan"]
    assert isinstance(asset_scan, dict)
    asset_scan["token_files"] = ["../outside-tokens.css", str(outside_token)]
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(json.dumps(catalog), encoding="utf-8")

    payload = _route(
        "React Web 管理后台",
        project_root=project,
        catalog_path=catalog_path,
    )

    assert payload["web_ui_asset_inventory"]["token_refs"] == []


def test_router_explains_selection_and_routes_smoothness_acceptance_ids() -> None:
    payload = _route(
        "React 数据工作台，需要十万行虚拟表格、富文本编辑和可中断流畅动效"
    )

    selection = payload["mature_web_ui_selection"]
    assert selection["status"] == "provisional"
    assert selection["primary_resource_id"] == "material-ui"
    assert len(selection["supporting_resource_ids"]) <= 3
    assert {"ag-grid", "apache-echarts", "tiptap", "motion"}.intersection(
        selection["supporting_resource_ids"]
    )
    assert all(
        candidate["reason_codes"] and isinstance(candidate["score"], int)
        for candidate in selection["candidates"]
    )
    assert "asset-inventory-not-scanned" in selection["confirmation_codes"]

    acceptance_ids = payload["smoothness_acceptance_ids"]
    assert {
        "focus-continuity",
        "selection-scroll-continuity",
        "pending-cancel-feedback",
        "duplicate-activation",
        "reduced-motion",
        "layout-stability",
        "large-data-performance",
        "editing-input-continuity",
        "interruption-safe-motion",
    } <= set(acceptance_ids)
    persisted = payload["professional_skill_route"]
    assert persisted["smoothness_acceptance_ids"] == acceptance_ids
    budgets = payload["smoothness_performance_budgets"]
    assert budgets == {
        "inp_ms": 200,
        "long_task_ms": 50,
        "cls": 0.1,
        "animation_dropped_frame_pct": 5,
        "bundle_delta_kb": 30,
    }
    assert persisted["smoothness_performance_budgets"] == budgets


def test_router_component_adoption_plan_marks_selected_uninstalled_support_as_add_with_permission_gate() -> None:
    payload = _route(
        "React 数据工作台，需要十万行虚拟表格、富文本编辑和可中断流畅动效"
    )

    selection = payload["mature_web_ui_selection"]
    adoption_plan = selection["component_adoption_plan"]
    assert [row["resource_id"] for row in adoption_plan] == [
        selection["primary_resource_id"],
        *selection["supporting_resource_ids"],
    ]
    for row in adoption_plan[1:]:
        _assert_component_adoption_plan_row(
            row,
            resource_id=str(row["resource_id"]),
            action="add",
        )
        assert row["permission_gate"] == "required"
        assert row["permission_status"] == "not-authorized"


def test_router_component_adoption_plan_creates_local_reuse_rows_for_unmapped_live_component_roots(
    tmp_path: Path,
) -> None:
    project = tmp_path / "react-app"
    (project / "src" / "components" / "ui").mkdir(parents=True)
    (project / "src" / "app").mkdir(parents=True)
    (project / "package.json").write_text(
        json.dumps({"dependencies": {"react": "^19.0.0"}}),
        encoding="utf-8",
    )
    (project / "src" / "app" / "page.tsx").write_text(
        "export default function Page() { return null }\n",
        encoding="utf-8",
    )
    (project / "src" / "components" / "ui" / "CommandPalette.tsx").write_text(
        "export function CommandPalette() { return null }\n",
        encoding="utf-8",
    )

    payload = _route(
        "React Web 应用，优先使用成熟组件库，组件状态要丝滑流畅",
        style_authority="inherit-existing",
        project_root=project,
    )

    adoption_plan = payload["mature_web_ui_selection"]["component_adoption_plan"]
    local_rows = [row for row in adoption_plan if row["resource_id"] == "local-components"]
    assert len(local_rows) == 1
    local_row = local_rows[0]
    _assert_component_adoption_plan_row(
        local_row,
        resource_id="local-components",
        action="reuse",
    )
    assert local_row["permission_gate"] == "not-required"
    assert local_row["permission_status"] == "authorized"
    assert "requires-mapping" in local_row["reason_codes"]
    assert local_row["component_refs"] == ["src/components/ui/CommandPalette.tsx"]


def test_router_surfaces_mature_web_ui_resources_for_component_library_work() -> None:
    payload = _route("React Web 应用，优先使用成熟组件库，组件状态要丝滑流畅")

    resource_ids = payload["mature_web_ui_resource_ids"]
    assert resource_ids[:3] == ["shadcn-ui", "radix-primitives", "base-ui"]
    assert "material-ui" in resource_ids
    assert "ant-design" in resource_ids
    assert "shadcn-agent-skill" in resource_ids
    assert payload["professional_skill_route"]["mature_web_ui_resource_ids"] == resource_ids


def test_router_narrows_component_resources_by_framework_and_capability() -> None:
    vue = _route("Vue Web 管理后台，优先成熟组件库和无障碍交互")
    vue_ids = vue["mature_web_ui_resource_ids"]
    assert "primevue" in vue_ids
    assert "vuetify" in vue_ids
    assert "headless-ui" in vue_ids
    assert "material-ui" not in vue_ids

    svelte = _route("SvelteKit Web 应用，需要成熟组件和可访问浮层")
    svelte_ids = svelte["mature_web_ui_resource_ids"]
    assert "bits-ui" in svelte_ids
    assert "web-awesome" in svelte_ids
    assert "material-ui" not in svelte_ids

    data_workspace = _route(
        "React 数据工作台，需要十万行虚拟表格、可访问图表和流畅动效"
    )
    data_ids = data_workspace["mature_web_ui_resource_ids"]
    assert "ag-grid" in data_ids
    assert "tanstack-table" in data_ids
    assert "apache-echarts" in data_ids
    assert "motion" in data_ids


def test_router_keeps_web_resources_out_of_native_platform_routes() -> None:
    for query in (
        "React Native mobile app component library",
        "iOS SwiftUI 组件设计",
        "Android Jetpack Compose design system",
        "Flutter desktop app component toolkit",
    ):
        payload = _route(query)
        assert payload["mature_web_ui_resource_ids"] == [], query
        assert payload["mature_web_ui_selection"]["component_adoption_plan"] == [], query
        assert payload["professional_skill_route"]["mature_web_ui_resource_ids"] == [], query
        assert payload["professional_skill_route"]["status"] == "resolved", query


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
        "mature_web_ui_resources",
        "prefer mature components",
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
        mature_status = payload["mature_web_ui_selection"]["status"]
        expected_status = (
            "unresolved"
            if mature_status in {"provisional", "unresolved"}
            else "resolved"
        )
        assert persisted["status"] == expected_status
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
        assert "component_adoption_plan" in lowered or "component adoption" in lowered
        assert "official-resource refresh" in lowered
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
    for content in (brief, classic_change, advanced_change):
        assert "professional_skill_route:" in content
        assert "domain_skill_id:" in content
        assert "style_skill_id:" in content
        assert "specialist_skill_ids:" in content
        assert "mature_web_ui_resource_ids:" in content
        assert "web_ui_asset_inventory:" in content
        assert "mature_web_ui_selection:" in content
        assert "component_adoption_plan:" in content
        assert "official_resource_refresh:" in content
        assert "smoothness_acceptance_ids:" in content
        assert "smoothness_performance_budgets:" in content
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
    assert (installed / "refresh.py").is_file()
    assert (installed / "web-component-selection.md").is_file()
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
