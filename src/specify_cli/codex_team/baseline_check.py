"""Baseline build and native shell readiness helpers for Codex team runtime."""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any

from .state_paths import codex_team_state_root


SOLUTION_CONFIGURATION_RE = re.compile(r"^\s*(?P<name>[^=\s][^=]+?)\s*=")


def is_wsl() -> bool:
    return bool(
        os.environ.get("WSL_INTEROP")
        or os.environ.get("WSL_DISTRO_NAME")
        or "microsoft" in os.uname().release.lower() if hasattr(os, "uname") else False
    )


def is_msys_or_git_bash() -> bool:
    return bool(os.environ.get("MSYSTEM"))


def is_native_windows() -> bool:
    return sys.platform == "win32" and not is_wsl() and not is_msys_or_git_bash()


def _baseline_record_path(project_root: Path) -> Path:
    return codex_team_state_root(project_root) / "baseline-build.json"


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def detect_solution_metadata(project_root: Path) -> dict[str, object]:
    solutions = sorted(path.resolve() for path in project_root.rglob("*.sln"))
    configurations: list[str] = []

    for solution in solutions:
        try:
            in_config_section = False
            for line in solution.read_text(encoding="utf-8", errors="ignore").splitlines():
                if "GlobalSection(SolutionConfigurationPlatforms)" in line:
                    in_config_section = True
                    continue
                if in_config_section and "EndGlobalSection" in line:
                    in_config_section = False
                    continue
                if not in_config_section:
                    continue
                match = SOLUTION_CONFIGURATION_RE.match(line)
                if match:
                    configurations.append(match.group("name").strip())
        except OSError:
            continue

    unique_configurations = sorted(dict.fromkeys(configurations))
    return {
        "has_solution": bool(solutions),
        "solutions": [str(path) for path in solutions],
        "primary_solution": str(solutions[0]) if solutions else "",
        "solution_count": len(solutions),
        "configurations": unique_configurations,
    }


def detect_native_build_shell(project_root: Path) -> dict[str, object]:
    del project_root
    if not is_native_windows():
        return {
            "ready": True,
            "source": "non_native",
            "target_arch": "",
            "vs_install_dir": "",
            "vc_install_dir": "",
            "visual_studio_version": "",
        }

    vs_install_dir = os.environ.get("VSINSTALLDIR", "").strip()
    vc_install_dir = os.environ.get("VCINSTALLDIR", "").strip()
    visual_studio_version = os.environ.get("VisualStudioVersion", "").strip() or os.environ.get("VSCMD_VER", "").strip()
    target_arch = (
        os.environ.get("VSCMD_ARG_TGT_ARCH", "").strip()
        or os.environ.get("Platform", "").strip()
        or os.environ.get("PLATFORM", "").strip()
    )
    ready = bool(vs_install_dir or vc_install_dir or visual_studio_version)
    source = "vsdevcmd_env" if ready else "missing"
    return {
        "ready": ready,
        "source": source,
        "target_arch": target_arch,
        "vs_install_dir": vs_install_dir,
        "vc_install_dir": vc_install_dir,
        "visual_studio_version": visual_studio_version,
    }


def classify_baseline_build_status(project_root: Path) -> dict[str, object]:
    cached = _read_json(_baseline_record_path(project_root))
    if cached is not None:
        cached_status = str(cached.get("status", "")).strip().lower()
        if cached_status in {"clean", "blocked", "unknown"}:
            return {
                "status": cached_status,
                "source": "cached_record",
                "reason": str(cached.get("reason", "")).strip(),
                "checked_at": str(cached.get("checked_at", "")).strip(),
                "details": cached,
            }

    solution = detect_solution_metadata(project_root)
    native_shell = detect_native_build_shell(project_root)
    msbuild_path = shutil.which("msbuild") or shutil.which("MSBuild.exe") or ""

    if not solution["has_solution"]:
        return {
            "status": "unknown",
            "source": "inspection",
            "reason": "No solution or known native build surface was detected.",
            "checked_at": "",
            "details": {
                "solution": solution,
                "native_build_shell": native_shell,
                "msbuild_path": msbuild_path,
            },
        }

    if is_native_windows() and not native_shell["ready"]:
        return {
            "status": "unknown",
            "source": "inspection",
            "reason": "A native Windows build shell is not initialized for this session.",
            "checked_at": "",
            "details": {
                "solution": solution,
                "native_build_shell": native_shell,
                "msbuild_path": msbuild_path,
            },
        }

    if is_native_windows() and not msbuild_path:
        return {
            "status": "unknown",
            "source": "inspection",
            "reason": "MSBuild is unavailable in the current shell.",
            "checked_at": "",
            "details": {
                "solution": solution,
                "native_build_shell": native_shell,
                "msbuild_path": msbuild_path,
            },
        }

    return {
        "status": "unknown",
        "source": "inspection",
        "reason": "Build surface detected but no cached baseline build assessment is recorded yet.",
        "checked_at": "",
        "details": {
            "solution": solution,
            "native_build_shell": native_shell,
            "msbuild_path": msbuild_path,
        },
    }
