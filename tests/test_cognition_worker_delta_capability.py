"""New worker contracts must reject a runtime that silently drops their fields."""

import json
from pathlib import Path
from types import SimpleNamespace

from specify_cli import specify_runtime


def test_runtime_with_recovery_but_without_worker_delta_contract_is_rejected(monkeypatch):
    capability = "cognition.worker-delta.v1"
    assert capability in specify_runtime.REQUIRED_CAPABILITIES
    old = sorted(set(specify_runtime.REQUIRED_CAPABILITIES) - {capability})
    assert "cognition.closeout.recovery.v1" in old
    monkeypatch.setattr(
        specify_runtime.subprocess, "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=0, stderr="", stdout=json.dumps({
            "status": "ok", "data": {
                "protocol_version": specify_runtime.EXPECTED_RUNTIME_PROTOCOL,
                "capability_ids": old,
            },
        })),
    )
    assert not specify_runtime.launcher_supports_required_commands(["old-runtime"])


def test_both_installers_check_worker_delta_before_publishing_binary():
    root = Path(__file__).resolve().parents[1]
    for name, publish in (("install.sh", "mv -f"), ("install.ps1", "Move-Item -LiteralPath $candidate")):
        text = (root / "tools/specify-runtime" / name).read_text(encoding="utf-8")
        guard = text.index("Downloaded binary lacks required worker cognition delta capability")
        assert '"cognition.worker-delta.v1"' in text[:guard]
        assert guard < text.index(publish)
