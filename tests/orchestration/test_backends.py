"""Tests for backend descriptor discovery."""

from specify_cli.orchestration.backends import detect
from specify_cli.orchestration.backends.base import BackendDescriptor
from specify_cli.orchestration.backends.detect import detect_available_backends


def test_detect_available_backends_includes_expected_entries(monkeypatch):
    binaries = {
        "tmux": "/usr/bin/tmux",
        "psmux": None,
    }

    monkeypatch.setattr(
        "specify_cli.orchestration.backends.detect.shutil.which",
        lambda name: binaries.get(name),
    )

    backends = detect_available_backends()

    assert set(backends) >= {"tmux", "psmux", "process"}
    assert backends["tmux"].name == "tmux"
    assert backends["tmux"].available is True
    assert backends["tmux"].binary == "/usr/bin/tmux"
    assert backends["psmux"].name == "psmux"
    assert backends["psmux"].available is False
    assert backends["process"].name == "process"
    assert backends["process"].available is True


def test_detect_available_backends_process_is_always_available(monkeypatch):
    monkeypatch.setattr("specify_cli.orchestration.backends.detect.shutil.which", lambda _: None)

    backends = detect_available_backends()

    assert backends["process"].available is True


def test_detect_available_backends_uses_process_backend_descriptor(monkeypatch):
    expected = BackendDescriptor(
        name="process",
        available=True,
        interactive=False,
        reason="process-descriptor-from-backend",
    )

    monkeypatch.setattr("specify_cli.orchestration.backends.detect.shutil.which", lambda _: None)
    class _FakeProcessBackend:
        def describe(self):
            return expected

    monkeypatch.setattr(detect, "ProcessBackend", _FakeProcessBackend, raising=False)

    backends = detect_available_backends()

    assert backends["process"] is expected
