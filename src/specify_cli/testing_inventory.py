"""Repository testing inventory helpers for the sp-test workflow."""

from __future__ import annotations

import json
import os
import re
import tomllib
from pathlib import Path
from typing import Any


IGNORE_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".specify",
    ".planning",
    ".venv",
    "venv",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    "node_modules",
    "vendor",
    "dist",
    "build",
    "target",
    ".gradle",
    ".idea",
    ".vscode",
    "zig-cache",
}

MANIFEST_FILES = {
    "pyproject.toml": "python",
    "package.json": "javascript",
    "go.mod": "go",
    "Cargo.toml": "rust",
    "composer.json": "php",
    "Gemfile": "ruby",
    "pubspec.yaml": "dart",
    "Package.swift": "swift",
    "pom.xml": "java",
}
SPECIAL_MANIFEST_NAMES = {
    "build.gradle",
    "build.gradle.kts",
    "CMakeLists.txt",
}

LANGUAGE_SKILL_MAP = {
    "python": "python-testing",
    "javascript": "js-testing",
    "go": "go-testing",
    "rust": "rust-testing",
    "php": "php-testing",
    "ruby": "ruby-testing",
    "dart": "dart-testing",
    "swift": "swift-testing",
    "java": "java-testing",
    "kotlin": "kotlin-testing",
    "cpp": "cpp-testing",
    "csharp": "cs-testing",
    "c": "c-testing",
    "zig": "zig-testing",
}

COMMON_TEST_DIRS = (
    "tests",
    "test",
    "spec",
    "__tests__",
    "src/test",
    "src/test/java",
    "src/test/kotlin",
)


def _iter_manifest_paths(project_root: Path) -> list[Path]:
    manifests: list[Path] = []
    for root, dirs, files in os.walk(project_root):
        dirs[:] = [name for name in dirs if name not in IGNORE_DIRS]
        root_path = Path(root)
        for file_name in files:
            if file_name in MANIFEST_FILES or file_name in SPECIAL_MANIFEST_NAMES:
                manifests.append(root_path / file_name)
                continue
            if file_name.endswith(".csproj"):
                manifests.append(root_path / file_name)
            elif file_name == "build.zig":
                manifests.append(root_path / file_name)
    return sorted(set(manifests))


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _load_toml(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as fh:
            data = tomllib.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def _detect_language(manifest_path: Path) -> str:
    if manifest_path.suffix == ".csproj":
        return "csharp"
    if manifest_path.name == "build.zig":
        return "zig"
    if manifest_path.name in {"build.gradle", "build.gradle.kts"}:
        gradle_text = _read_text(manifest_path).lower()
        module_root = manifest_path.parent
        if (
            "org.jetbrains.kotlin" in gradle_text
            or "kotlin(" in gradle_text
            or "kotlin-android" in gradle_text
            or (module_root / "src" / "main" / "kotlin").exists()
            or (module_root / "src" / "test" / "kotlin").exists()
        ):
            return "kotlin"
        return "java"
    if manifest_path.name == "CMakeLists.txt":
        cmake_text = _read_text(manifest_path).lower()
        module_root = manifest_path.parent
        if re.search(r"\blanguages\s+[^)\n]*\bcxx\b", cmake_text) or "enable_language(cxx" in cmake_text:
            return "cpp"
        if re.search(r"\blanguages\s+[^)\n]*\bc\b", cmake_text) or "enable_language(c)" in cmake_text:
            return "c"
        cpp_suffixes = {".cpp", ".cxx", ".cc", ".hpp", ".hxx", ".hh"}
        c_suffixes = {".c", ".h"}
        has_cpp = False
        has_c = False
        for root, dirs, files in os.walk(module_root):
            dirs[:] = [name for name in dirs if name not in IGNORE_DIRS]
            for file_name in files:
                suffix = Path(file_name).suffix.lower()
                if suffix in cpp_suffixes:
                    has_cpp = True
                elif suffix in c_suffixes:
                    has_c = True
            if has_cpp:
                break
        if has_cpp:
            return "cpp"
        if has_c:
            return "c"
        return "cpp"
    return MANIFEST_FILES.get(manifest_path.name, "unknown")


def _module_kind(project_root: Path, manifest_path: Path, language: str) -> tuple[str, str]:
    module_root = manifest_path.parent
    rel = module_root.relative_to(project_root)
    if rel == Path("."):
        if language == "javascript":
            package_json = _load_json(manifest_path)
            if package_json.get("workspaces"):
                return "workspace-root", "package.json defines workspaces"
        return "root-module", "manifest is at repository root"
    return "nested-module", "manifest is in a nested project path"


def _detect_test_path(module_root: Path, language: str) -> str | None:
    for rel in COMMON_TEST_DIRS:
        candidate = module_root / rel
        if candidate.exists():
            return candidate.relative_to(module_root).as_posix()

    if language == "javascript":
        matches = list(module_root.rglob("*.test.*")) + list(module_root.rglob("*.spec.*"))
        if matches:
            return matches[0].parent.relative_to(module_root).as_posix() or "."
    return None


def _package_scripts(package_json: dict[str, Any]) -> dict[str, str]:
    scripts = package_json.get("scripts")
    if not isinstance(scripts, dict):
        return {}
    return {str(k): str(v) for k, v in scripts.items()}


def _detect_framework(module_root: Path, manifest_path: Path, language: str) -> tuple[str, str]:
    if language == "python":
        if (module_root / "pytest.ini").exists():
            return "pytest", "high"
        data = _load_toml(manifest_path)
        if isinstance(data.get("tool", {}), dict) and "pytest" in data.get("tool", {}):
            return "pytest", "high"
        if "pytest.ini_options" in data.get("tool", {}).get("pytest", {}):
            return "pytest", "high"
        if (module_root / "conftest.py").exists():
            return "pytest", "medium"
        test_path = _detect_test_path(module_root, language)
        if test_path:
            return "unittest", "medium"
        return "unknown", "low"

    if language == "javascript":
        package_json = _load_json(manifest_path)
        scripts = _package_scripts(package_json)
        dev_deps = {
            **(package_json.get("dependencies") or {}),
            **(package_json.get("devDependencies") or {}),
        }
        if (module_root / "vitest.config.ts").exists() or any("vitest" in v for v in scripts.values()) or "vitest" in dev_deps:
            return "vitest", "high"
        if any("jest" in v for v in scripts.values()) or "jest" in dev_deps:
            return "jest", "high"
        return "node-test", "low"

    if language == "go":
        return "go-test", "high"

    if language == "rust":
        if (module_root / ".config" / "nextest.toml").exists():
            return "cargo-nextest", "high"
        return "cargo-test", "high"

    if language == "php":
        composer = _load_json(manifest_path)
        deps = {
            **(composer.get("require") or {}),
            **(composer.get("require-dev") or {}),
        }
        if "pestphp/pest" in deps:
            return "pest", "high"
        if (module_root / "phpunit.xml").exists() or any("phpunit" in dep for dep in deps):
            return "phpunit", "high"
        return "php-test", "low"

    if language == "ruby":
        gemfile = _read_text(manifest_path)
        if "rspec" in gemfile.lower() or (module_root / "spec").exists():
            return "rspec", "high"
        return "minitest", "low"

    if language == "dart":
        pubspec = _read_text(manifest_path)
        if "flutter_test" in pubspec:
            return "flutter_test", "high"
        return "dart-test", "medium"

    if language == "swift":
        package_swift = _read_text(manifest_path)
        if re.search(r"\bTesting\b", package_swift):
            return "swift-testing", "medium"
        return "xctest", "medium"

    if language == "java":
        text = _read_text(manifest_path)
        return ("junit", "high") if "junit" in text.lower() else ("gradle-test", "low")

    if language == "kotlin":
        text = _read_text(manifest_path)
        if "kotest" in text.lower():
            return "kotest", "high"
        if "junit" in text.lower():
            return "junit5", "medium"
        return "gradle-test", "low"

    if language in {"cpp", "c"}:
        text = _read_text(manifest_path).lower()
        if "gtest" in text or "googletest" in text:
            return "gtest", "high"
        if "catch2" in text:
            return "catch2", "high"
        if "ctest" in text:
            return "ctest", "medium"
        if "cmocka" in text:
            return "cmocka", "medium"
        if "unity" in text:
            return "unity", "medium"
        return "cmake-test", "low"

    if language == "csharp":
        text = _read_text(manifest_path).lower()
        if "xunit" in text:
            return "xunit", "high"
        if "nunit" in text:
            return "nunit", "high"
        if "mstest" in text:
            return "mstest", "high"
        return "dotnet-test", "low"

    if language == "zig":
        return "zig-test", "high"

    return "unknown", "low"


def _canonical_commands(module_root: Path, manifest_path: Path, language: str, framework: str) -> tuple[str | None, str | None]:
    if language == "python":
        if framework == "pytest":
            return "pytest", "pytest --cov"
        if framework == "unittest":
            return "python -m unittest discover", "coverage run -m unittest discover"
        return None, None

    if language == "javascript":
        package_json = _load_json(manifest_path)
        scripts = _package_scripts(package_json)
        test_command = scripts.get("test") or ("vitest run" if framework == "vitest" else None)
        coverage_command = scripts.get("coverage") or scripts.get("test:coverage")
        if not coverage_command and framework == "vitest":
            coverage_command = "vitest run --coverage"
        elif not coverage_command and framework == "jest":
            coverage_command = "jest --coverage"
        return test_command, coverage_command

    if language == "go":
        return "go test ./...", "go test -coverprofile=coverage.out ./..."
    if language == "rust":
        return ("cargo nextest run" if framework == "cargo-nextest" else "cargo test"), "cargo llvm-cov"
    if language == "php":
        return ("vendor/bin/pest" if framework == "pest" else "vendor/bin/phpunit"), (
            "./vendor/bin/pest --coverage" if framework == "pest" else "vendor/bin/phpunit --coverage-html coverage"
        )
    if language == "ruby":
        return ("bundle exec rspec" if framework == "rspec" else "bundle exec ruby -Itest"), "bundle exec rspec"
    if language == "dart":
        return ("flutter test" if framework == "flutter_test" else "dart test"), (
            "flutter test --coverage" if framework == "flutter_test" else "dart test"
        )
    if language == "swift":
        return "swift test", "swift test --enable-code-coverage"
    if language == "java":
        return ("./gradlew test" if "gradle" in manifest_path.name else "mvn test"), None
    if language == "kotlin":
        return "./gradlew test", "./gradlew test koverHtmlReport"
    if language in {"cpp", "c"}:
        return "ctest", "ctest"
    if language == "csharp":
        return "dotnet test", 'dotnet test --collect:"XPlat Code Coverage"'
    if language == "zig":
        return "zig test", "zig test"
    return None, None


def _module_state(framework: str, test_path: str | None, test_command: str | None, coverage_command: str | None) -> str:
    if framework == "unknown" and not test_path and not test_command and not coverage_command:
        return "missing"
    if framework == "unknown":
        return "gap"
    if test_path and test_command:
        return "healthy" if coverage_command else "partial"
    if framework != "unknown" or test_path or test_command:
        return "partial"
    return "missing"


def _module_name(module_root: Path, manifest_path: Path, language: str) -> str:
    if language == "javascript":
        package_json = _load_json(manifest_path)
        if isinstance(package_json.get("name"), str) and package_json["name"].strip():
            return package_json["name"].strip()
    if language == "python":
        pyproject = _load_toml(manifest_path)
        if isinstance(pyproject.get("project", {}).get("name"), str):
            return str(pyproject["project"]["name"]).strip()
    return module_root.name or "."


def build_testing_inventory(project_root: Path) -> dict[str, Any]:
    project_root = project_root.resolve()
    modules: list[dict[str, Any]] = []
    seen_roots: set[Path] = set()

    for manifest_path in _iter_manifest_paths(project_root):
        module_root = manifest_path.parent.resolve()
        if module_root in seen_roots:
            continue
        seen_roots.add(module_root)

        language = _detect_language(manifest_path)
        module_kind, classification_reason = _module_kind(project_root, manifest_path, language)
        framework, framework_confidence = _detect_framework(module_root, manifest_path, language)
        test_path = _detect_test_path(module_root, language)
        test_command, coverage_command = _canonical_commands(module_root, manifest_path, language, framework)
        state = _module_state(framework, test_path, test_command, coverage_command)

        modules.append(
            {
                "module_name": _module_name(module_root, manifest_path, language),
                "module_root": module_root.relative_to(project_root).as_posix() or ".",
                "module_kind": module_kind,
                "language": language,
                "manifest_path": manifest_path.relative_to(project_root).as_posix(),
                "selected_skill": LANGUAGE_SKILL_MAP.get(language),
                "framework": framework,
                "framework_confidence": framework_confidence,
                "canonical_test_path": test_path,
                "canonical_test_command": test_command,
                "coverage_command": coverage_command,
                "state": state,
                "classification_reason": classification_reason,
            }
        )

    return {
        "project_root": str(project_root),
        "module_count": len(modules),
        "languages": sorted({module["language"] for module in modules}),
        "modules": sorted(modules, key=lambda module: module["module_root"]),
    }
