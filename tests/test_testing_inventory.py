import json

from typer.testing import CliRunner

from specify_cli import app
from specify_cli.testing_inventory import build_testing_inventory


def test_build_testing_inventory_detects_python_pytest_module(tmp_path):
    project = tmp_path / "python-project"
    project.mkdir()
    (project / "pyproject.toml").write_text(
        "[project]\nname='demo'\nversion='0.1.0'\n"
        "[tool.pytest.ini_options]\naddopts=['-q']\n",
        encoding="utf-8",
    )
    (project / "tests").mkdir()
    (project / "tests" / "test_sample.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")

    payload = build_testing_inventory(project)

    assert payload["module_count"] == 1
    module = payload["modules"][0]
    assert module["language"] == "python"
    assert module["selected_skill"] == "python-testing"
    assert module["framework"] == "pytest"
    assert module["state"] == "healthy"
    assert module["canonical_test_path"] == "tests"
    assert module["module_kind"] == "root-module"


def test_build_testing_inventory_ignores_node_modules_and_detects_nested_js_module(tmp_path):
    project = tmp_path / "js-project"
    project.mkdir()
    (project / "package.json").write_text(
        json.dumps({"name": "root", "private": True, "workspaces": ["packages/*"]}),
        encoding="utf-8",
    )
    package_dir = project / "packages" / "web"
    package_dir.mkdir(parents=True)
    (package_dir / "package.json").write_text(
        json.dumps(
            {
                "name": "@demo/web",
                "scripts": {"test": "vitest run", "coverage": "vitest run --coverage"},
                "devDependencies": {"vitest": "^3.0.0"},
            }
        ),
        encoding="utf-8",
    )
    (package_dir / "tests").mkdir()
    (package_dir / "tests" / "app.test.ts").write_text("import { test, expect } from 'vitest'\n", encoding="utf-8")
    ignored = project / "node_modules" / "ignored"
    ignored.mkdir(parents=True)
    (ignored / "package.json").write_text(json.dumps({"name": "ignored"}), encoding="utf-8")

    payload = build_testing_inventory(project)

    module_paths = {module["module_root"] for module in payload["modules"]}
    assert "node_modules/ignored" not in module_paths
    assert "." in module_paths
    assert "packages/web" in module_paths

    web_module = next(module for module in payload["modules"] if module["module_root"] == "packages/web")
    assert web_module["language"] == "javascript"
    assert web_module["selected_skill"] == "js-testing"
    assert web_module["framework"] == "vitest"
    assert web_module["state"] == "healthy"


def test_testing_inventory_cli_outputs_json(tmp_path, monkeypatch):
    project = tmp_path / "inventory-cli"
    project.mkdir()
    (project / "pyproject.toml").write_text(
        "[project]\nname='demo'\nversion='0.1.0'\n"
        "[tool.pytest.ini_options]\naddopts=['-q']\n",
        encoding="utf-8",
    )
    (project / "tests").mkdir()

    monkeypatch.chdir(project)
    result = CliRunner().invoke(app, ["testing", "inventory", "--format", "json"], catch_exceptions=False)

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["project_root"] == str(project.resolve())
    assert payload["module_count"] == 1
    assert payload["modules"][0]["selected_skill"] == "python-testing"
