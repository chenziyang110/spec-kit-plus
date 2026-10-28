from types import SimpleNamespace
import json
from pathlib import Path

from specify_cli import specify_runtime


def test_old_runtime_with_apply_replay_but_without_receipt_guard_is_rejected(monkeypatch):
    capability = "cognition.closeout.recovery.v1"
    assert capability in specify_runtime.REQUIRED_CAPABILITIES
    old = sorted(set(specify_runtime.REQUIRED_CAPABILITIES) - {capability})
    assert {"cognition.closeout.apply", "cognition.closeout.replay"} <= set(old)
    monkeypatch.setattr(
        specify_runtime.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=0,
            stdout=json.dumps({"status": "ok", "data": {
                "protocol_version": specify_runtime.EXPECTED_RUNTIME_PROTOCOL,
                "capability_ids": old,
            }}),
            stderr="",
        ),
    )
    assert not specify_runtime.launcher_supports_required_commands(["old-runtime"])


def test_installers_refuse_missing_recovery_guard_before_replacing_binary():
    root = Path(__file__).resolve().parents[1]
    for name, publish in (("install.sh", "mv -f"), ("install.ps1", "Move-Item -LiteralPath $candidate")):
        text = (root / "tools" / "specify-runtime" / name).read_text(encoding="utf-8")
        guard = text.index("Downloaded binary lacks required cognition closeout recovery capability")
        assert '"cognition.closeout.recovery.v1"' in text[:guard]
        assert guard < text.index(publish)
