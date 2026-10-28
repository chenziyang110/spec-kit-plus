#!/usr/bin/env python3
"""Run actual init/upgrade/repair from a wheel-installed, isolated interpreter.

Launch with the fresh virtualenv's Python -I. Only disposable projects beneath
--output are written. This never installs dependencies, publishes, or changes
repository source. An existing output directory is rejected to keep old evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import sysconfig
import zipfile

HELPERS = ("e2e_scenarios.py", "e2e_coverage.py", "e2e_runner.py", "e2e_pytest_reporter.py", "e2e_assets.py")
MAP_COMPANIONS = {"sp-map-scan", "sp-map-build", "sp-map-update"}
TOKENS = ("{{spec-kit-include:", "{{project-cognition-workflow}}", "{{specify-subcmd:",
          "SPECIFY_RUNTIME_LAUNCHER_UNAVAILABLE")


def require(ok: bool, message: str) -> None:
    if not ok:
        raise RuntimeError(message)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze_wheel_hash(wheel: Path, expected: str | None = None) -> str:
    """Optionally bind the probe to the preceding source/archive check."""
    if expected is not None:
        require(len(expected) == 64 and all(c in "0123456789abcdef" for c in expected),
                "expected wheel SHA-256 must be 64 lowercase hexadecimal characters")
    actual = digest(wheel)
    require(expected is None or actual == expected,
            "wheel differs from the source/archive verification report")
    return actual


def verify_asset_snapshot(wheel: Path, wheel_hash: str, package: Path,
                          assets: dict[str, bytes]) -> None:
    """Check observed input stability; this is not an atomic snapshot."""
    require(digest(wheel) == wheel_hash, "wheel changed during installation verification")
    for name, expected in assets.items():
        actual = package.parent / name
        require(actual.is_file() and actual.read_bytes() == expected,
                f"installed assets changed during verification: {name}")


def installed_assets(wheel: Path) -> tuple[Path, dict[str, bytes]]:
    """Refuse editable/source imports even when their version strings match."""
    require(sys.flags.isolated == 1, "launch the wheel interpreter with -I")
    require(sys.prefix != sys.base_prefix, "a fresh virtualenv is required")
    distribution = importlib.metadata.distribution("specify-cli")
    direct = json.loads(distribution.read_text("direct_url.json") or "{}")
    require(not direct.get("dir_info", {}).get("editable", False), "editable install is not wheel evidence")
    import specify_cli
    package = Path(specify_cli.__file__).resolve().parent
    allowed = {Path(sysconfig.get_path(key)).resolve() / "specify_cli" for key in ("purelib", "platlib")}
    require(package in allowed, "specify_cli was imported outside this virtualenv's site-packages")
    required = ["specify_cli/__init__.py", "specify_cli/specify_runtime.py",
                "specify_cli/execution/packet_schema.py", "specify_cli/execution/packet_validator.py",
                "specify_cli/core_pack/tools/specify-runtime/e2e_workflow.go",
                "specify_cli/core_pack/tools/specify-runtime/e2e_contract.go"]
    required += [f"specify_cli/core_pack/scripts/shared/{name}" for name in HELPERS]
    required += ["specify_cli/core_pack/commands/e2e.md",
                 "specify_cli/core_pack/advanced-skills/spx-e2e/SKILL.md",
                 "specify_cli/core_pack/advanced-skills/spx-e2e/references/scenario-design.md",
                 "specify_cli/core_pack/advanced-skills/_shared/surface-map.json"]
    with zipfile.ZipFile(wheel) as archive:
        require(len(archive.namelist()) == len(set(archive.namelist())), "duplicate ZIP member")
        assets = {name: archive.read(name) for name in required}
    for name, expected in assets.items():
        actual = package.parent / name
        require(actual.is_file() and actual.read_bytes() == expected, f"installed/wheel mismatch: {name}")
    return package, assets


def clean_environment(output: Path, runtime: Path) -> dict[str, str]:
    env = {key: value for key, value in os.environ.items()
           if not key.startswith(("PYTHON", "SPECIFY_RUNTIME", "SPECIFY_PROJECT_LAUNCHER"))}
    env.update({
        "VIRTUAL_ENV": sys.prefix,
        "PATH": sysconfig.get_path("scripts") + os.pathsep + env.get("PATH", ""),
        "SPECIFY_RUNTIME_BIN": str(runtime),
        # The repository's own local-build test fixture permits dirty builds;
        # this is not permission to publish one or accept a foreign runtime.
        "SPECIFY_RUNTIME_ALLOW_DIRTY": "1",
        "SPECIFY_RUNTIME_CACHE_DIR": str(output / "runtime-cache"),
        "SPECIFY_PROJECT_LAUNCHER_STATE_DIR": str(output / "launcher-state"),
        "CLAUDE_CONFIG_DIR": str(output / "claude-config"),
        "NO_COLOR": "1", "COLUMNS": "240", "CI": "true",
        # The console entrypoint writes raw bytes to redirected log handles.
        # Bind its encoding to the UTF-8 evidence readers on every host locale.
        "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8",
    })
    return env


def verify_expected_partial_repair(text: str, preserved: set[str]) -> None:
    """Accept only the intentional user-edit boundary, with no repair issues."""
    require("PARTIAL" in text, "repair did not report its preservation boundary")
    require("Remaining diagnostics" not in text, "repair left unresolved diagnostics")
    marker = "Files preserved without overwrite\n"
    require(marker in text, "repair did not identify preserved files")
    section = text.split(marker, 1)[1].split("Human repair tutorial", 1)[0]
    actual = {line[2:].strip() for line in section.splitlines() if line.startswith("- ")}
    require(actual == preserved, "repair preserved unexpected files")


def run_probe(wheel: Path, runtime: Path, output: Path, expected_revision: str,
              expected_wheel_sha256: str | None = None) -> dict:
    require(runtime.is_file(), "missing locally built runtime")
    wheel_hash = freeze_wheel_hash(wheel, expected_wheel_sha256)
    package, assets = installed_assets(wheel)
    verify_asset_snapshot(wheel, wheel_hash, package, assets)
    from specify_cli.integrations.manifest import IntegrationManifest
    from specify_cli.specify_runtime import project_runtime_launcher_arg
    runtime_hash = digest(runtime)
    env = clean_environment(output, runtime)
    commands = []
    executable = Path(sysconfig.get_path("scripts")) / ("specify.exe" if os.name == "nt" else "specify")
    require(executable.is_file(), "wheel console entrypoint is missing")
    cli = [str(executable)]

    def run(argv: list[str], project: Path, label: str, expected_exit: int = 0) -> str:
        index = len(commands) + 1
        stdout = output / f"{index:02d}-{label}.stdout.txt"
        stderr = output / f"{index:02d}-{label}.stderr.txt"
        record = {"argv": argv, "project": project.name, "stdout": stdout.name, "stderr": stderr.name}
        commands.append(record)
        try:
            with stdout.open("x", encoding="utf-8") as out, stderr.open("x", encoding="utf-8") as err:
                process = subprocess.run(argv, cwd=project, env=env, stdin=subprocess.DEVNULL,
                                         stdout=out, stderr=err, timeout=180, check=False)
            record["exit_code"] = process.returncode
            require(process.returncode == expected_exit,
                    f"{label}: unexpected exit code; inspect {stderr.name} and {stdout.name}")
            return stdout.read_text(encoding="utf-8")
        except subprocess.TimeoutExpired:
            record["timeout"] = True
            raise
        finally:
            (output / "commands.json").write_text(json.dumps(commands, indent=2) + "\n", encoding="utf-8")

    def initialize(project: Path, profile: str, script_type: str) -> None:
        text = run(cli + ["init", "--here", "--force", "--ai", "codex", "--workflow-profile", profile,
                          "--script", script_type, "--no-git", "--ignore-agent-tools"], project, "init-" + profile)
        require(("$sp-e2e" if profile == "classic" else "$spx-e2e") in text, "missing native E2E init hint")

    def verify(project: Path, profiles: set[str], edits: dict[str, bytes]) -> None:
        core = IntegrationManifest.load("speckit", project)
        agent = IntegrationManifest.load("codex", project)
        for name in HELPERS:
            relative = f".specify/scripts/shared/{name}"
            path = project / relative
            wanted = edits.get(relative, assets[f"specify_cli/core_pack/scripts/shared/{name}"])
            require(path.is_file() and path.read_bytes() == wanted, f"helper missing/changed: {relative}")
            require(relative in core.files, f"helper missing from core manifest: {relative}")
        for profile in profiles:
            prefix = "sp" if profile == "classic" else "spx"
            relative = f".codex/skills/{prefix}-e2e/SKILL.md"
            skill = project / relative
            require(skill.is_file() and relative in agent.files, f"missing tracked skill: {relative}")
            if relative in edits:
                require(skill.read_bytes() == edits[relative], "user-modified skill was overwritten")
            text = skill.read_text(encoding="utf-8")
            require("--require-v2" in text and not any(token in text for token in TOKENS), "unusable generated E2E skill")
            import yaml
            metadata = yaml.safe_load((skill.parent / "agents/openai.yaml").read_text(encoding="utf-8"))
            require(metadata["policy"]["allow_implicit_invocation"] is False, "implicit E2E invocation enabled")
            if profile == "advanced":
                reference = skill.parent / "references/scenario-design.md"
                require(reference.is_file() and reference.relative_to(project).as_posix() in agent.files,
                        "missing tracked Advanced scenario-design reference")
        skills = project / ".codex/skills"
        if profiles == {"advanced"}:
            require({p.parent.name for p in skills.glob("sp-*/SKILL.md")} == MAP_COMPANIONS, "Classic profile leakage")
            require(not (skills / "spec-kit-project-cognition-gate").exists(), "Classic passive bundle leaked")
        if profiles == {"classic"}:
            require(not list(skills.glob("spx-*/SKILL.md")), "Advanced profile leakage")
        pinned = project / ".specify/bin" / ("specify-runtime.exe" if os.name == "nt" else "specify-runtime")
        require(pinned.is_file() and digest(pinned) == runtime_hash, "runtime was not pinned from this source build")
        config = json.loads((project / ".specify/config.json").read_text(encoding="utf-8"))
        require(config["runtime_launcher"]["argv"] == [project_runtime_launcher_arg()], "runtime launcher is not project-local")
        version = json.loads(run([str(pinned), "version", "--format", "json"], project, "runtime-version"))
        require(version["status"] == "ok" and version["data"]["source_revision"] == expected_revision,
                "pinned runtime source revision differs from this build")
        capabilities = ["e2e." + action for action in (
            "init", "status", "compact", "task-show", "scope-add", "task-start", "task-submit", "review-start",
            "review-submit", "task-accept", "reopen", "close",
        )]
        ensured = json.loads(run([str(pinned), "api", "ensure", "--capabilities", ",".join(capabilities),
                                  "--format", "json"], project, "e2e-runtime-capabilities"))
        require(ensured["status"] == "ok" and set(ensured["data"]["present"]) == set(capabilities)
                and ensured["data"]["missing"] == [], "installed runtime lacks the E2E handoff owner")
        learning = json.loads(run([str(pinned), "learning", "start", "--command", "sp-e2e", "--format", "json"],
                                  project, "learning-e2e"))
        require(learning["status"] == "ok", "current runtime rejects E2E learning identity")
        catalog = json.loads(run([sys.executable, "-I", str(project / ".specify/scripts/shared/e2e_scenarios.py"), "catalog"],
                                 project, "scenario-catalog"))
        require(len(catalog["dimensions"]) >= 14, "installed scenario helper is incomplete")
        for name in ("e2e_coverage.py", "e2e_runner.py", "e2e_assets.py"):
            run([sys.executable, "-E", "-s", str(project / ".specify/scripts/shared" / name), "--help"], project, name)
        for asset in ("strength", "bundle", "crosswalk"):
            schema = json.loads(run([sys.executable, "-E", "-s", str(project / ".specify/scripts/shared/e2e_assets.py"), "schema", asset], project, asset + "-schema"))
            require(schema["claim"] == "schemas_only", f"installed {asset} helper is not executable")
        if edits:
            require(".specify/scripts/shared/e2e_scenarios.py" in core.check_modified(), "user edit lost its manifest boundary")

    completed = []
    for script_type in ("sh", "ps"):
        for first, second in (("classic", "advanced"), ("advanced", "classic")):
            project = output / f"project {script_type} {first}"
            project.mkdir()
            initialize(project, first, script_type)
            verify(project, {first}, {})
            prefix = "sp" if first == "classic" else "spx"
            edits = {}
            for relative, note in ((f".codex/skills/{prefix}-e2e/SKILL.md", b"\n<!-- user E2E note -->\n"),
                                   (".specify/scripts/shared/e2e_scenarios.py", b"\n# user E2E note\n")):
                path = project / relative
                edits[relative] = path.read_bytes() + note
                path.write_bytes(edits[relative])
            initialize(project, second, script_type)
            verify(project, {first, second}, edits)
            second_prefix = "sp" if second == "classic" else "spx"
            # Remove only an unmodified file in this probe-owned disposable project.
            missing = project / f".codex/skills/{second_prefix}-e2e/SKILL.md"
            missing.unlink()
            # The helper was deliberately edited above. Repair must preserve it
            # and return the documented partial status, without other issues.
            repair_text = run(cli + ["integration", "repair"], project, "repair", expected_exit=10)
            verify_expected_partial_repair(repair_text, {".specify/scripts/shared/e2e_scenarios.py"})
            verify(project, {first, second}, edits)
            completed.append({"script_type": script_type, "order": [first, second], "repair": "verified"})
    verify_asset_snapshot(wheel, wheel_hash, package, assets)
    return {"claim": "installed_e2e_wheel_verified", "wheel_sha256": wheel_hash,
            "runtime_sha256": runtime_hash, "source_revision": expected_revision,
            "package_root": str(package), "python": sys.version, "cases": completed,
            "qualification": "Wheel/init/upgrade/repair verification only; not native shell execution, GUI perception or product acceptance."}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("wheel", "runtime", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--expected-revision", required=True)
    parser.add_argument("--expected-wheel-sha256",
                        help="wheel_sha256 from the preceding source/archive verification report")
    args = parser.parse_args(argv)
    output = args.output.resolve()
    require(not output.is_relative_to(Path(__file__).resolve().parents[2]), "probe output must be outside the source checkout")
    output.mkdir(parents=True, exist_ok=False)
    try:
        result = run_probe(args.wheel.resolve(), args.runtime.resolve(), output, args.expected_revision,
                           args.expected_wheel_sha256)
    except (OSError, ValueError, RuntimeError, KeyError, ImportError, subprocess.SubprocessError, zipfile.BadZipFile) as exc:
        (output / "error.json").write_text(json.dumps({"claim": "failed", "error": str(exc)}, indent=2) + "\n", encoding="utf-8")
        print(str(exc), file=sys.stderr)
        return 1
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
