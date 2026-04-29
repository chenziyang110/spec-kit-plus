import json
from pathlib import Path


def test_detect_solution_metadata_reads_solution_configurations(tmp_path: Path):
    from specify_cli.codex_team.baseline_check import detect_solution_metadata

    solution = tmp_path / "Example.sln"
    solution.write_text(
        "\n".join(
            [
                "Microsoft Visual Studio Solution File, Format Version 12.00",
                "Global",
                "\tGlobalSection(SolutionConfigurationPlatforms) = preSolution",
                "\t\tDebug|x86 = Debug|x86",
                "\t\tRelease|x64 = Release|x64",
                "\tEndGlobalSection",
                "EndGlobal",
            ]
        ),
        encoding="utf-8",
    )

    metadata = detect_solution_metadata(tmp_path)

    assert metadata["has_solution"] is True
    assert str(solution) in metadata["solutions"]
    assert "Debug|x86" in metadata["configurations"]
    assert "Release|x64" in metadata["configurations"]


def test_classify_baseline_build_status_uses_cached_state_record(codex_team_project_root: Path):
    from specify_cli.codex_team.baseline_check import classify_baseline_build_status

    state_path = codex_team_project_root / ".specify" / "teams" / "state" / "baseline-build.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {
                "status": "blocked",
                "reason": "aria2/src/common.h depends on missing config.h",
                "checked_at": "2026-04-26T00:00:00Z",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    baseline = classify_baseline_build_status(codex_team_project_root)

    assert baseline["status"] == "blocked"
    assert baseline["source"] == "cached_record"
    assert "config.h" in baseline["reason"]


def test_detect_native_build_shell_reports_target_arch(monkeypatch):
    from specify_cli.codex_team.baseline_check import detect_native_build_shell

    monkeypatch.setattr("specify_cli.codex_team.baseline_check.is_native_windows", lambda: True)
    monkeypatch.setenv("VSINSTALLDIR", r"C:\VS")
    monkeypatch.setenv("VSCMD_ARG_TGT_ARCH", "x86")

    shell = detect_native_build_shell(Path.cwd())

    assert shell["ready"] is True
    assert shell["target_arch"] == "x86"
    assert shell["source"] == "vsdevcmd_env"
