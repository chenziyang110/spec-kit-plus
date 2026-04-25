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


def test_build_testing_inventory_classifies_gradle_java_vs_kotlin(tmp_path):
    java_project = tmp_path / "java-gradle"
    java_project.mkdir()
    (java_project / "build.gradle").write_text(
        "plugins { id 'java' }\nrepositories { mavenCentral() }\n",
        encoding="utf-8",
    )
    (java_project / "src" / "test" / "java").mkdir(parents=True)

    kotlin_project = tmp_path / "kotlin-gradle"
    kotlin_project.mkdir()
    (kotlin_project / "build.gradle.kts").write_text(
        "plugins { kotlin(\"jvm\") version \"2.1.0\" }\nrepositories { mavenCentral() }\n",
        encoding="utf-8",
    )
    (kotlin_project / "src" / "main" / "kotlin").mkdir(parents=True)

    java_payload = build_testing_inventory(java_project)
    kotlin_payload = build_testing_inventory(kotlin_project)

    java_module = java_payload["modules"][0]
    kotlin_module = kotlin_payload["modules"][0]

    assert java_module["language"] == "java"
    assert java_module["selected_skill"] == "java-testing"
    assert java_module["framework"] in {"junit", "gradle-test"}

    assert kotlin_module["language"] == "kotlin"
    assert kotlin_module["selected_skill"] == "kotlin-testing"
    assert kotlin_module["framework"] in {"kotest", "junit5", "gradle-test"}


def test_build_testing_inventory_classifies_cmake_c_project_as_c(tmp_path):
    project = tmp_path / "c-project"
    project.mkdir()
    (project / "CMakeLists.txt").write_text(
        "cmake_minimum_required(VERSION 3.20)\n"
        "project(example LANGUAGES C)\n"
        "add_library(example src/example.c)\n",
        encoding="utf-8",
    )
    (project / "src").mkdir()
    (project / "src" / "example.c").write_text("int meaning(void) { return 42; }\n", encoding="utf-8")

    payload = build_testing_inventory(project)

    module = payload["modules"][0]
    assert module["language"] == "c"
    assert module["selected_skill"] == "c-testing"
    assert module["framework"] in {"ctest", "cmake-test", "cmocka", "unity"}


def test_build_testing_inventory_marks_bare_python_repo_as_missing(tmp_path):
    project = tmp_path / "bare-python"
    project.mkdir()
    (project / "pyproject.toml").write_text(
        "[project]\nname='demo'\nversion='0.1.0'\n",
        encoding="utf-8",
    )

    payload = build_testing_inventory(project)

    module = payload["modules"][0]
    assert module["language"] == "python"
    assert module["selected_skill"] == "python-testing"
    assert module["framework"] == "unknown"
    assert module["canonical_test_command"] is None
    assert module["coverage_command"] is None
    assert module["state"] == "missing"
