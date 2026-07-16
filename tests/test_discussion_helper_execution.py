from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
import sys

import specify_cli


def test_discussion_helper_uses_one_utf8_python_process(
    tmp_path: Path, monkeypatch
) -> None:
    core_pack = tmp_path / "core_pack"
    shared_helper = core_pack / "scripts" / "shared" / "discussion-state.py"
    shared_helper.parent.mkdir(parents=True)
    shared_helper.write_text("# test helper\n", encoding="utf-8")

    powershell_wrapper = (
        core_pack / "scripts" / "powershell" / "discussion-state.ps1"
    )
    powershell_wrapper.parent.mkdir(parents=True)
    powershell_wrapper.write_text("# legacy wrapper\n", encoding="utf-8")

    bash_wrapper = core_pack / "scripts" / "bash" / "discussion-state.sh"
    bash_wrapper.parent.mkdir(parents=True)
    bash_wrapper.write_text("# legacy wrapper\n", encoding="utf-8")

    captured: dict[str, object] = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps({"discussions": []}),
            stderr="",
        )

    monkeypatch.setattr(specify_cli, "_locate_core_pack", lambda: core_pack)
    monkeypatch.setattr(specify_cli.subprocess, "run", fake_run)

    payload = specify_cli._run_discussion_helper("list")

    assert payload == {"discussions": []}
    command = captured["command"]
    assert isinstance(command, list)
    assert command[:3] == [sys.executable, "-X", "utf8"]
    assert Path(command[3]) == shared_helper
    assert not any(str(part).endswith((".ps1", ".sh")) for part in command)

    kwargs = captured["kwargs"]
    assert isinstance(kwargs, dict)
    env = kwargs["env"]
    assert env["PYTHONUTF8"] == "1"
    assert env["PYTHONIOENCODING"] == "utf-8"
    assert kwargs["encoding"] == "utf-8"
    assert kwargs["errors"] == "strict"
