"""Generated material-reading contracts require a runtime that implements them."""

from pathlib import Path

import pytest

from specify_cli import specify_runtime as runtime


CAPABILITIES = ("discussion.import-material", "discussion.read-material")
ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("missing", CAPABILITIES)
def test_runtime_without_material_reading_is_not_compatible(monkeypatch, missing):
    assert missing in runtime.REQUIRED_CAPABILITIES
    monkeypatch.setattr(
        runtime,
        "_runtime_handshake",
        lambda *_args, **_kwargs: {
            "protocol_version": runtime.EXPECTED_RUNTIME_PROTOCOL,
            "capability_ids": [cap for cap in runtime.REQUIRED_CAPABILITIES if cap != missing],
        },
    )

    assert not runtime.launcher_supports_required_commands(["specify-runtime"])


@pytest.mark.parametrize("script", ("install.sh", "install.ps1"))
def test_standalone_installers_reject_material_reading_gaps(script):
    source = (ROOT / "tools" / "specify-runtime" / script).read_text(encoding="utf-8")
    guard = source.split("Downloaded binary failed the specify-runtime API handshake")[0]
    guard = guard.replace(r"\.", ".")

    for capability in CAPABILITIES:
        assert f'"{capability}"' in guard
