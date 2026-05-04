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


def test_build_testing_inventory_reports_javascript_command_tier_candidates(tmp_path):
    project = tmp_path / "web"
    project.mkdir()
    (project / "package.json").write_text(
        json.dumps(
            {
                "name": "web",
                "scripts": {
                    "test": "vitest run",
                    "test:unit": "vitest run src",
                    "test:smoke": "vitest run tests/smoke",
                    "coverage": "vitest run --coverage",
                },
                "devDependencies": {"vitest": "^3.0.0"},
            }
        ),
        encoding="utf-8",
    )

    payload = build_testing_inventory(project)
    module = payload["modules"][0]

    assert module["canonical_test_command"] == "vitest run"
    assert module["coverage_command"] == "vitest run --coverage"
    assert module["command_tiers"]["fast_smoke"] == "vitest run tests/smoke"
    assert module["command_tiers"]["focused"] == "vitest run src"
    assert module["command_tiers"]["full"] == "vitest run"


def test_build_testing_inventory_reports_python_command_tier_defaults(tmp_path):
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
    module = payload["modules"][0]

    assert module["canonical_test_command"] == "pytest"
    assert module["coverage_command"] == "pytest --cov"
    assert module["command_tiers"]["fast_smoke"] == "pytest -q"
    assert module["command_tiers"]["focused"] == "pytest"
    assert module["command_tiers"]["full"] == "pytest --cov"


def test_build_testing_inventory_reports_unittest_command_tier_defaults(tmp_path):
    project = tmp_path / "unittest-project"
    project.mkdir()
    (project / "pyproject.toml").write_text(
        "[project]\nname='demo'\nversion='0.1.0'\n",
        encoding="utf-8",
    )
    (project / "tests").mkdir()
    (project / "tests" / "test_sample.py").write_text(
        "import unittest\n\n"
        "class SampleTest(unittest.TestCase):\n"
        "    def test_ok(self):\n"
        "        self.assertTrue(True)\n",
        encoding="utf-8",
    )

    payload = build_testing_inventory(project)
    module = payload["modules"][0]

    assert module["framework"] == "unittest"
    assert module["canonical_test_command"] == "python -m unittest discover"
    assert module["coverage_command"] == "coverage run -m unittest discover"
    assert module["command_tiers"]["fast_smoke"] == "python -m unittest discover"
    assert module["command_tiers"]["focused"] == "python -m unittest discover"
    assert module["command_tiers"]["full"] == "coverage run -m unittest discover"


def test_build_testing_inventory_reports_scriptless_jest_defaults(tmp_path):
    project = tmp_path / "jest-project"
    project.mkdir()
    (project / "package.json").write_text(
        json.dumps({"name": "web", "devDependencies": {"jest": "^30.0.0"}}),
        encoding="utf-8",
    )

    payload = build_testing_inventory(project)
    module = payload["modules"][0]

    assert module["framework"] == "jest"
    assert module["canonical_test_command"] == "npm exec -- jest"
    assert module["coverage_command"] == "npm exec -- jest --coverage"
    assert module["command_tiers"]["fast_smoke"] == "npm exec -- jest"
    assert module["command_tiers"]["focused"] == "npm exec -- jest"
    assert module["command_tiers"]["full"] == "npm exec -- jest"


def test_build_testing_inventory_keeps_plain_node_test_project_non_authoritative(tmp_path):
    project = tmp_path / "node-test-project"
    project.mkdir()
    (project / "package.json").write_text(json.dumps({"name": "web", "type": "module"}), encoding="utf-8")

    payload = build_testing_inventory(project)
    module = payload["modules"][0]

    assert module["framework"] == "node-test"
    assert module["canonical_test_command"] is None
    assert module["coverage_command"] is None
    assert module["command_tiers"]["fast_smoke"] is None
    assert module["command_tiers"]["focused"] is None
    assert module["command_tiers"]["full"] is None


def test_build_testing_inventory_reports_node_test_defaults_when_test_files_exist(tmp_path):
    project = tmp_path / "node-test-project"
    project.mkdir()
    (project / "package.json").write_text(json.dumps({"name": "web", "type": "module"}), encoding="utf-8")
    (project / "tests").mkdir()
    (project / "tests" / "app.test.js").write_text("import test from 'node:test'\n", encoding="utf-8")

    payload = build_testing_inventory(project)
    module = payload["modules"][0]

    assert module["framework"] == "node-test"
    assert module["canonical_test_path"] == "tests"
    assert module["canonical_test_command"] == "node --test"
    assert module["coverage_command"] is None
    assert module["command_tiers"]["fast_smoke"] == "node --test"
    assert module["command_tiers"]["focused"] == "node --test"
    assert module["command_tiers"]["full"] == "node --test"


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


def test_build_testing_inventory_reports_bare_python_fallback_defaults(tmp_path):
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
    assert module["command_tiers"]["fast_smoke"] is None
    assert module["command_tiers"]["focused"] is None
    assert module["command_tiers"]["full"] is None
    assert module["state"] == "missing"


def test_build_testing_inventory_ignores_worktrees_manifests(tmp_path):
    project = tmp_path / "workspace-project"
    project.mkdir()
    (project / "pyproject.toml").write_text(
        "[project]\nname='demo'\nversion='0.1.0'\n"
        "[tool.pytest.ini_options]\naddopts=['-q']\n",
        encoding="utf-8",
    )
    (project / "tests").mkdir()
    (project / "tests" / "test_sample.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    nested = project / ".worktrees" / "feature-a"
    nested.mkdir(parents=True)
    (nested / "pyproject.toml").write_text(
        "[project]\nname='shadow'\nversion='0.1.0'\n"
        "[tool.pytest.ini_options]\naddopts=['-q']\n",
        encoding="utf-8",
    )
    (nested / "tests").mkdir()

    payload = build_testing_inventory(project)

    assert payload["module_count"] == 1
    assert payload["modules"][0]["module_root"] == "."


def test_build_testing_inventory_treats_rust_inline_tests_as_healthy(tmp_path):
    project = tmp_path / "rust-inline-tests"
    project.mkdir()
    (project / "Cargo.toml").write_text(
        "[package]\nname='inline-tests'\nversion='0.1.0'\nedition='2021'\n",
        encoding="utf-8",
    )
    src = project / "src"
    src.mkdir()
    (src / "lib.rs").write_text(
        "pub fn answer() -> i32 { 42 }\n\n"
        "#[cfg(test)]\n"
        "mod tests {\n"
        "    use super::*;\n\n"
        "    #[test]\n"
        "    fn returns_answer() {\n"
        "        assert_eq!(answer(), 42);\n"
        "    }\n"
        "}\n",
        encoding="utf-8",
    )

    payload = build_testing_inventory(project)

    module = payload["modules"][0]
    assert module["framework"] == "cargo-test"
    assert module["canonical_test_path"] == "src"
    assert module["state"] == "healthy"


def test_build_testing_inventory_ignores_node_modules_test_file_fallback(tmp_path):
    project = tmp_path / "js-fallback-project"
    project.mkdir()
    (project / "package.json").write_text(json.dumps({"name": "demo"}), encoding="utf-8")
    ignored = project / "node_modules" / "leftpad"
    ignored.mkdir(parents=True)
    (ignored / "fake.test.js").write_text("test('x', () => {})\n", encoding="utf-8")

    payload = build_testing_inventory(project)

    module = payload["modules"][0]
    assert module["canonical_test_path"] is None
    assert module["canonical_test_command"] is None
    assert module["command_tiers"]["focused"] is None
    assert module["state"] == "partial"


def test_build_testing_inventory_uses_maven_test_for_plain_pom_projects(tmp_path):
    project = tmp_path / "maven-project"
    project.mkdir()
    (project / "pom.xml").write_text(
        "<project><modelVersion>4.0.0</modelVersion></project>",
        encoding="utf-8",
    )

    payload = build_testing_inventory(project)

    module = payload["modules"][0]
    assert module["language"] == "java"
    assert module["framework"] == "maven-test"
    assert module["canonical_test_command"] == "mvn test"
