from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _fake_runtime_toolchain(monkeypatch, tmp_path: Path) -> None:
    fake_bin = tmp_path / "fake-contract-runtime-bin"
    fake_bin.mkdir()
    binary_names = {
        "tmux": "tmux.exe",
        "node": "node.exe",
        "npm": "npm.cmd",
        "codex": "codex.exe",
        "cargo": "cargo.exe",
        "git": "git.exe",
        "psmux": "psmux.exe",
    }
    tool_paths: dict[str, str] = {}
    for tool_name, file_name in binary_names.items():
        path = fake_bin / file_name
        path.write_text("", encoding="utf-8")
        tool_paths[tool_name] = str(path)

    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: False)
    monkeypatch.setattr(
        "specify_cli.codex_team.runtime_bridge.shutil.which",
        lambda name: tool_paths.get(str(name).lower()),
    )
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.detect_available_backends", lambda: {})
