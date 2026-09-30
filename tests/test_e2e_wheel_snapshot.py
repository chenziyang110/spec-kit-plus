"""Snapshot/freshness regressions using the original synthetic wheel fixtures.

Real file mutations are synchronized at verifier boundaries, not with sleeps.
These tests do not claim a real package installation or cloud execution.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import zipfile

import pytest

from tests.test_e2e_wheel_verifier import PROBE, probe, source as source, verifier, wheel_for


def observed_stat(value, **changes):
    fields = ("st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns", "st_ctime_ns")
    return SimpleNamespace(**({field: getattr(value, field) for field in fields} | changes))


def test_stable_path_and_descriptor_metadata_need_not_match(source, tmp_path, monkeypatch):
    wheel = wheel_for(tmp_path, verifier.source_assets(source))
    original = os.fstat

    def descriptor_observation(fd):
        value = original(fd)
        # Windows can expose different timestamp semantics/precision through
        # the path and descriptor APIs for the same unchanged file.
        return observed_stat(value, st_ctime_ns=value.st_ctime_ns + 100,
                             st_mtime_ns=value.st_mtime_ns + 200,
                             st_mode=value.st_mode ^ 0o200)

    monkeypatch.setattr(verifier.os, "fstat", descriptor_observation)
    report = verifier.verify_wheel(wheel, source)
    assert report["claim"] == "wheel_e2e_assets_verified"
    assert report["wheel_sha256"] == hashlib.sha256(wheel.read_bytes()).hexdigest()


@pytest.mark.parametrize("api", ["path", "descriptor"])
@pytest.mark.parametrize("field", ["st_size", "st_mtime_ns", "st_ctime_ns", "st_mode", "st_ino", "st_dev"])
def test_each_snapshot_rejects_its_own_metadata_drift(source, tmp_path, monkeypatch, api, field):
    wheel = wheel_for(tmp_path, verifier.source_assets(source))
    original_record = verifier.read_record
    original_path_stat = Path.stat
    original_fstat = os.fstat
    after_inventory = []
    observed = []

    def read_record(archive):
        result = original_record(archive)
        after_inventory.append(True)
        return result

    def change(value):
        observed.append(field)
        return observed_stat(value, **{field: getattr(value, field) + 1})

    def path_observation(path, *args, **kwargs):
        value = original_path_stat(path, *args, **kwargs)
        return change(value) if api == "path" and path == wheel and after_inventory else value

    def descriptor_observation(fd):
        value = original_fstat(fd)
        return change(value) if api == "descriptor" and after_inventory else value

    monkeypatch.setattr(verifier, "read_record", read_record)
    monkeypatch.setattr(Path, "stat", path_observation)
    monkeypatch.setattr(verifier.os, "fstat", descriptor_observation)
    with pytest.raises(verifier.WheelError, match="wheel changed"):
        verifier.verify_wheel(wheel, source)
    assert after_inventory == [True]
    assert observed, f"{api} drift was not exercised"


def test_same_byte_wheel_replacement_between_path_snapshot_and_open_is_rejected(source, tmp_path, monkeypatch):
    wheel = wheel_for(tmp_path, verifier.source_assets(source))
    replacement = tmp_path / "replacement.whl"
    replacement.write_bytes(wheel.read_bytes())
    metadata = wheel.stat()
    os.utime(replacement, ns=(metadata.st_atime_ns, metadata.st_mtime_ns))
    assert not os.path.samestat(metadata, replacement.stat())
    original_open = os.open
    injected = []

    def replace_at_open(path, flags, *args, **kwargs):
        if Path(path) == wheel and not injected:
            injected.append(True)
            replacement.replace(wheel)
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(verifier.os, "open", replace_at_open)
    with pytest.raises(verifier.WheelError, match="wheel changed"):
        verifier.verify_wheel(wheel, source)
    assert injected == [True]


@pytest.mark.parametrize("mutation", ["replace", "rewrite-same-size", "append", "delete"])
def test_wheel_change_after_archive_reads_never_closes_verification(source, tmp_path, monkeypatch, mutation):
    import os
    wheel = wheel_for(tmp_path, verifier.source_assets(source))
    original = wheel.read_bytes()
    metadata = wheel.stat()
    exit_archive = zipfile.ZipFile.__exit__
    injected = []

    def change_after_reads(archive, *args):
        exit_archive(archive, *args)
        injected.append(mutation)
        if mutation == "replace":
            replacement = tmp_path / "foreign.whl"
            replacement.write_bytes(b"Unverified replacement, not an archive")
            replacement.replace(wheel)
        elif mutation == "rewrite-same-size":
            wheel.write_bytes(bytes([original[0] ^ 1]) + original[1:])
            os.utime(wheel, ns=(metadata.st_atime_ns, metadata.st_mtime_ns))
        elif mutation == "append":
            with wheel.open("ab") as handle:
                handle.write(b"unverified new bytes")
        else:
            wheel.unlink()

    monkeypatch.setattr(zipfile.ZipFile, "__exit__", change_after_reads)
    # Windows can deny replacement/deletion of an open descriptor. That also
    # aborts this verification; it must not be mislabeled as a validated swap.
    with pytest.raises((verifier.WheelError, OSError)):
        verifier.verify_wheel(wheel, source)
    assert injected == [mutation]


@pytest.mark.parametrize("mutation", ["modify", "remove", "add-reference"])
def test_source_changes_after_inventory_never_close_verification(source, tmp_path, monkeypatch, mutation):
    wheel = wheel_for(tmp_path, verifier.source_assets(source))
    original = verifier.read_record
    injected = []

    def change_after_inventory(archive):
        result = original(archive)
        injected.append(mutation)
        target = source / "templates/commands/e2e.md"
        if mutation == "modify":
            target.write_bytes(b"Changed after the initial source inventory")
        elif mutation == "remove":
            target.unlink()
        else:
            target = source / "templates/advanced-skills/spx-e2e/new-reference.md"
            target.write_bytes(b"A newly required reference must not be omitted")
        return result

    monkeypatch.setattr(verifier, "read_record", change_after_inventory)
    with pytest.raises(verifier.WheelError, match="source"):
        verifier.verify_wheel(wheel, source)
    assert injected == [mutation]


def test_wheel_hash_never_reopens_the_path_after_validation(source, tmp_path, monkeypatch):
    wheel = wheel_for(tmp_path, verifier.source_assets(source))
    wanted = hashlib.sha256(wheel.read_bytes()).hexdigest()
    original = Path.read_bytes

    def reject_wheel_path_read(path):
        if path == wheel:
            raise AssertionError("The report must hash the validated descriptor, not reopen the wheel")
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", reject_wheel_path_read)
    assert verifier.verify_wheel(wheel, source)["wheel_sha256"] == wanted


def test_stream_hash_is_bounded_and_rewinds():
    payload = b"hash-me\x00\xff" * 50000

    class BoundedStream(io.BytesIO):
        def read(self, size=-1):
            assert 0 < size <= 65536, "Unbounded archive read"
            return super().read(size)

    stream = BoundedStream(payload)
    stream.seek(7)
    assert verifier._stream_sha256(stream) == hashlib.sha256(payload).hexdigest()
    assert stream.tell() == 0


def test_nonregular_wheel_is_rejected_before_open(source, tmp_path):
    with pytest.raises(verifier.WheelError, match="regular file"):
        verifier.verify_wheel(tmp_path, source)


@pytest.mark.parametrize("expected", ["", "0" * 63, "0" * 65, "A" * 64, "g" * 64])
def test_probe_rejects_malformed_archive_binding_before_reading(tmp_path, expected):
    with pytest.raises(RuntimeError, match="64 lowercase"):
        probe.freeze_wheel_hash(tmp_path / "missing.whl", expected)


def test_probe_rejects_replacement_between_archive_check_and_install(tmp_path):
    wheel = tmp_path / "synthetic.whl"
    wheel.write_bytes(b"original verified input")
    expected = probe.freeze_wheel_hash(wheel)
    wheel.write_bytes(b"replacement input")
    with pytest.raises(RuntimeError, match="source/archive verification"):
        probe.freeze_wheel_hash(wheel, expected)


def test_probe_preserves_matching_external_archive_binding(tmp_path):
    wheel = tmp_path / "synthetic.whl"
    wheel.write_bytes(b"synthetic wheel bytes")
    expected = hashlib.sha256(wheel.read_bytes()).hexdigest()
    assert probe.freeze_wheel_hash(wheel, expected) == expected


def test_probe_console_logs_are_utf8_without_inheriting_python_paths(tmp_path, monkeypatch):
    monkeypatch.setenv("PYTHONPATH", str(tmp_path / "foreign-package"))
    monkeypatch.setenv("PYTHONIOENCODING", "ascii")
    env = probe.clean_environment(tmp_path, tmp_path / "runtime")
    assert "PYTHONPATH" not in env
    result = subprocess.run(
        [sys.executable, "-c", "print('\u4e2d\u6587 \u2192 E2E')"],
        env=env, capture_output=True, encoding="utf-8", timeout=20,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "\u4e2d\u6587 \u2192 E2E"


@pytest.mark.parametrize("mutation", ["none", "diagnostic", "extra-preserved", "missing-preserved", "no-partial"])
def test_probe_partial_repair_accepts_only_the_intentional_edit(mutation):
    helper = ".specify/scripts/shared/e2e_scenarios.py"
    text = "PARTIAL Runtime-owned files repaired where safe\nFiles preserved without overwrite\n- " + helper + "\n\n"
    if mutation == "diagnostic":
        text += "Remaining diagnostics\n- unbound-runtime: launcher remains broken\n"
    elif mutation == "extra-preserved":
        text += "- .specify/project-launcher.cmd\n"
    elif mutation == "missing-preserved":
        text = text.replace("- " + helper, "")
    elif mutation == "no-partial":
        text = text.replace("PARTIAL", "OK")
    text += "Human repair tutorial\nKeep the intentional user edit.\n"
    if mutation == "none":
        probe.verify_expected_partial_repair(text, {helper})
    else:
        with pytest.raises(RuntimeError):
            probe.verify_expected_partial_repair(text, {helper})


@pytest.mark.parametrize("mutation", ["none", "wheel", "installed", "missing-installed"])
def test_probe_rechecks_original_installed_assets_at_closeout(tmp_path, mutation):
    package = tmp_path / "site-packages/specify_cli"
    package.mkdir(parents=True)
    wheel = tmp_path / "synthetic.whl"
    wheel.write_bytes(b"synthetic, not an installed product")
    wheel_hash = probe.freeze_wheel_hash(wheel)
    assets = {"specify_cli/__init__.py": b"# original fixture entrypoint\n"}
    asset = package / "__init__.py"
    asset.write_bytes(assets["specify_cli/__init__.py"])
    probe.verify_asset_snapshot(wheel, wheel_hash, package, assets)
    if mutation == "none":
        return
    if mutation == "wheel":
        wheel.write_bytes(b"changed archive")
    elif mutation == "installed":
        asset.write_bytes(b"# changed entrypoint\n")
    else:
        asset.unlink()
    with pytest.raises(RuntimeError, match="changed during"):
        probe.verify_asset_snapshot(wheel, wheel_hash, package, assets)


@pytest.mark.parametrize("optimized", [False, True])
def test_probe_cli_archive_mismatch_fails_before_package_import(tmp_path, optimized):
    wheel, runtime = tmp_path / "synthetic.whl", tmp_path / "runtime-placeholder"
    wheel.write_bytes(b"not an installed product")
    runtime.write_bytes(b"Never executed by this mismatch guard")
    output = tmp_path / "new evidence"
    argv = [sys.executable, "-I"] + (["-O"] if optimized else [])
    argv += [str(PROBE), "--wheel", str(wheel), "--runtime", str(runtime),
             "--output", str(output), "--expected-revision", "fixture",
             "--expected-wheel-sha256", "0" * 64]
    result = subprocess.run(argv, text=True, capture_output=True, timeout=20)
    assert result.returncode == 1
    assert "source/archive verification" in result.stderr
    assert json.loads((output / "error.json").read_text())["claim"] == "failed"
    assert not (output / "result.json").exists()
    assert not (output / "commands.json").exists()


def test_replacement_by_nonregular_file_is_rejected_before_reading(source, tmp_path, monkeypatch):
    import os
    wheel = wheel_for(tmp_path, verifier.source_assets(source))
    original_open = os.open
    injected = []

    def replace_at_open(path, flags, *args, **kwargs):
        if Path(path) == wheel and not injected:
            injected.append(True)
            wheel.unlink()
            if hasattr(os, "mkfifo"):
                # Fail before open, rather than hanging, if nonblocking support
                # is ever removed from the verifier's POSIX open contract.
                assert flags & os.O_NONBLOCK
                os.mkfifo(wheel)
            else:
                wheel.mkdir()
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(verifier.os, "open", replace_at_open)
    with pytest.raises((verifier.WheelError, OSError)):
        verifier.verify_wheel(wheel, source)
    assert injected == [True]
