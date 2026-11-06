#!/usr/bin/env python3
"""Run a frozen native process with external file paths resolved only in memory.

Read one bounded packet from stdin. Verify source bytes before launch and
external bytes before/after it; emit symbolic JSON and discard child output.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
from typing import Any

SCHEMA = "spec-kit-protected-process.v1"
MAX_INPUT_BYTES = 256 * 1024
_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,63}\Z")
_ENVIRONMENT = re.compile(r"[A-Z_][A-Z0-9_]*\Z")
_DIGEST = re.compile(r"[a-f0-9]{64}\Z")
_ATTEMPT = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}\Z")
_TOKEN = re.compile(r"\{\{external:([A-Za-z][A-Za-z0-9_-]{0,63})\}\}\Z")


class ProtectedProcessError(ValueError):
    def __init__(self, code: str, binding: str = "") -> None:
        super().__init__(code)
        self.code = code
        self.binding = binding


def _need(condition: bool, code: str = "invalid_packet", binding: str = "") -> None:
    if not condition:
        raise ProtectedProcessError(code, binding)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        _need(key not in result)
        result[key] = value
    return result


def _digest_file(path: Path, code: str, binding: str = "") -> str:
    try:
        with path.open("rb") as stream:
            _need(stat.S_ISREG(os.fstat(stream.fileno()).st_mode), code, binding)
            digest = hashlib.sha256()
            for chunk in iter(lambda: stream.read(128 * 1024), b""):
                digest.update(chunk)
            return digest.hexdigest()
    except ProtectedProcessError:
        raise
    except (OSError, ValueError):
        raise ProtectedProcessError(code, binding) from None


def _external_path(root: Path, environment: str, binding: str) -> Path:
    value = os.environ.get(environment)
    _need(bool(value), "external_input_missing", binding)
    try:
        supplied = Path(value)
        _need(supplied.is_absolute(), "external_input_invalid", binding)
        resolved = supplied.resolve(strict=True)
        _need(not resolved.is_relative_to(root), "external_input_inside_project", binding)
        _need(resolved.is_file(), "external_input_invalid", binding)
        return resolved
    except ProtectedProcessError:
        raise
    except (OSError, ValueError, RuntimeError):
        raise ProtectedProcessError("external_input_invalid", binding) from None


def _project_path(root: Path, name: str, *, directory: bool = False) -> Path:
    code = "cwd_invalid" if directory else "source_input_invalid"
    if directory and name == ".":
        return root
    relative = PurePosixPath(name)
    _need(
        bool(name) and len(name) <= 512 and "\\" not in name and ":" not in name
        and not relative.is_absolute() and relative.as_posix() == name
        and name != "." and ".." not in relative.parts
        and all(part.lower() != ".git" for part in relative.parts),
        code,
    )
    try:
        resolved = root.joinpath(*relative.parts).resolve(strict=True)
        _need(resolved.is_relative_to(root), code)
        _need(resolved.is_dir() if directory else resolved.is_file(), code)
        return resolved
    except ProtectedProcessError:
        raise
    except (OSError, ValueError, RuntimeError):
        raise ProtectedProcessError(code) from None


def _packet(raw: bytes) -> dict[str, Any]:
    _need(len(raw) <= MAX_INPUT_BYTES, "input_too_large")
    try:
        packet = json.loads(raw, object_pairs_hook=_unique_object)
    except ProtectedProcessError:
        raise
    except (ValueError, UnicodeError, RecursionError):
        raise ProtectedProcessError("invalid_packet") from None
    required = {"schema", "cwd", "argv", "external_inputs", "source_files"}
    identity = {"attempt_id", "definition_digest", "source_fingerprint", "external_fingerprint"}
    _need(isinstance(packet, dict) and required <= packet.keys() <= required | identity)
    _need(packet["schema"] == SCHEMA and isinstance(packet["cwd"], str))
    argv = packet["argv"]
    _need(isinstance(argv, list) and 1 <= len(argv) <= 128)
    _need(all(isinstance(arg, str) and len(arg) <= 8192 and not any(c in arg for c in "\x00\r\n") for arg in argv))
    _need(bool(argv[0].strip()) and _TOKEN.fullmatch(argv[0]) is None)
    for key in identity & packet.keys():
        value = packet[key]
        pattern = _ATTEMPT if key == "attempt_id" else _DIGEST
        _need(isinstance(value, str) and pattern.fullmatch(value) is not None)
    bindings = packet["external_inputs"]
    sources = packet["source_files"]
    _need(isinstance(bindings, dict) and 1 <= len(bindings) <= 32)
    _need(isinstance(sources, dict) and 1 <= len(sources) <= 192)
    for name, definition in bindings.items():
        _need(isinstance(name, str) and _NAME.fullmatch(name) is not None)
        _need(isinstance(definition, dict) and set(definition) == {"environment", "sha256"})
        _need(isinstance(definition["environment"], str) and _ENVIRONMENT.fullmatch(definition["environment"]) is not None)
        _need(isinstance(definition["sha256"], str) and _DIGEST.fullmatch(definition["sha256"]) is not None)
    for name, digest in sources.items():
        _need(isinstance(name, str) and isinstance(digest, str) and _DIGEST.fullmatch(digest) is not None)
    for arg in argv:
        token = _TOKEN.fullmatch(arg)
        if token:
            _need(token[1] in bindings, "unknown_external_binding")
        else:
            _need("{{external:" not in arg, "invalid_external_placeholder")
    return packet


def _external_fingerprint(bindings: dict[str, Any], paths: dict[str, Path]) -> str:
    digest = hashlib.sha256()
    for name in sorted(bindings):
        location = str(paths[name])
        if os.name == "nt":
            location = location.lower()
        path_digest = hashlib.sha256(location.encode("utf-8")).hexdigest()
        record = [name, bindings[name]["environment"], bindings[name]["sha256"], path_digest]
        digest.update((json.dumps(record, separators=(",", ":"), ensure_ascii=True) + "\n").encode("ascii"))
    return digest.hexdigest()


def _run(packet: dict[str, Any], result: dict[str, Any]) -> int:
    root = Path.cwd().resolve(strict=True)
    cwd = _project_path(root, packet["cwd"], directory=True)
    bindings = packet["external_inputs"]
    resolved: dict[str, Path] = {}
    for name, definition in bindings.items():
        path = _external_path(root, definition["environment"], name)
        _need(_digest_file(path, "external_input_invalid", name) == definition["sha256"], "external_input_hash_mismatch", name)
        resolved[name] = path
    if "external_fingerprint" in packet:
        _need(_external_fingerprint(bindings, resolved) == packet["external_fingerprint"], "external_fingerprint_mismatch")
    for name, digest in packet["source_files"].items():
        _need(_digest_file(_project_path(root, name), "source_input_invalid") == digest, "source_hash_mismatch")
    # Do not let an accidentally literal protected path enter the receipt.
    for name, path in resolved.items():
        original = os.environ[bindings[name]["environment"]]
        _need(all(original not in arg and str(path) not in arg for arg in packet["argv"]), "literal_external_input", name)
    argv = [str(resolved[token[1]]) if (token := _TOKEN.fullmatch(arg)) else arg for arg in packet["argv"]]
    result["argv"] = packet["argv"]
    used = {token[1] for arg in packet["argv"] if (token := _TOKEN.fullmatch(arg))}
    result["used_bindings"] = [{"name": name, "sha256": bindings[name]["sha256"]} for name in sorted(used)]
    for name in ("attempt_id", "definition_digest", "source_fingerprint", "external_fingerprint"):
        if name in packet:
            result[name] = packet[name]
    try:
        completed = subprocess.run(
            argv, cwd=cwd, stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=False,
        )
    except (OSError, ValueError):
        raise ProtectedProcessError("process_launch_failed") from None
    result["exit_code"] = completed.returncode
    result["outcome"] = "passed" if completed.returncode == 0 else "failed"
    after: dict[str, Path] = {}
    for name, definition in bindings.items():
        try:
            path = _external_path(root, definition["environment"], name)
            unchanged = path == resolved[name] and _digest_file(path, "external_input_changed", name) == definition["sha256"]
        except ProtectedProcessError:
            unchanged = False
        if not unchanged:
            result["outcome"] = "failed"
            result["error"] = {"code": "external_input_changed", "binding": name}
            return 1
        after[name] = path
    if "external_fingerprint" in packet and _external_fingerprint(bindings, after) != packet["external_fingerprint"]:
        result["outcome"] = "failed"
        result["error"] = {"code": "external_fingerprint_mismatch"}
        return 1
    if completed.returncode != 0:
        result["error"] = {"code": "process_failed"}
        return 1
    return 0


def main() -> int:
    result: dict[str, Any] = {"schema": SCHEMA, "outcome": "blocked", "exit_code": None, "argv": [], "used_bindings": []}
    try:
        _need(sys.argv[1:] == ["--input-json", "-"], "invalid_cli")
        packet = _packet(sys.stdin.buffer.read(MAX_INPUT_BYTES + 1))
        code = _run(packet, result)
    except ProtectedProcessError as error:
        result["error"] = {"code": error.code}
        if error.binding:
            result["error"]["binding"] = error.binding
        code = 2
    except KeyboardInterrupt:
        result["outcome"] = "interrupted"
        result["error"] = {"code": "process_interrupted"}
        code = 130
    except Exception:
        result["outcome"] = "blocked" if result["exit_code"] is None else "failed"
        result["error"] = {"code": "protected_process_error"}
        code = 2
    sys.stdout.write(json.dumps(result, separators=(",", ":")) + "\n")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
