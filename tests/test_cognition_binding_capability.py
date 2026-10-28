"""Strong closeout consumers must refuse a runtime with only legacy evidence."""

import json
from pathlib import Path
from types import SimpleNamespace

from specify_cli import specify_runtime


CAPABILITY = "cognition.closeout.binding.v1"


def test_old_runtime_cannot_satisfy_current_source_binding(monkeypatch):
    old = sorted(set(specify_runtime.REQUIRED_CAPABILITIES) - {CAPABILITY})
    assert {"cognition.closeout.recovery.v1", "cognition.worker-delta.v1"} <= set(old)
    monkeypatch.setattr(
        specify_runtime.subprocess, "run",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=0, stderr="", stdout=json.dumps({
                "status": "ok", "data": {
                    "protocol_version": specify_runtime.EXPECTED_RUNTIME_PROTOCOL,
                    "capability_ids": old,
                },
            }),
        ),
    )
    assert not specify_runtime.launcher_supports_required_commands(["legacy-runtime"])


def test_both_installers_refuse_weak_binding_before_publication():
    root = Path(__file__).resolve().parents[1]
    for name, publish in (
        ("install.sh", "mv -f"),
        ("install.ps1", "Move-Item -LiteralPath $candidate"),
    ):
        text = (root / "tools/specify-runtime" / name).read_text(encoding="utf-8")
        guard = text.index("Downloaded binary lacks required cognition closeout binding capability")
        assert f'"{CAPABILITY}"' in text[:guard]
        assert guard < text.index(publish)
