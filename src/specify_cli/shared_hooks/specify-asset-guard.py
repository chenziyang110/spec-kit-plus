"""Small native-hook adapter for the project-local Go asset checker.

Policy and validation belong to specify-runtime. This adapter keeps only a
discardable, session-scoped observation of writes; it never creates workflow
state, changes assets, or grants ownership/readiness. Read-only tools do nothing.
"""

from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import stat
import subprocess
import tempfile
import time
from typing import Any


CACHE_ROOT = ".specify/runtime/asset-observations"
MAX_PATHS = 2048
MAX_STATE_BYTES = 1024 * 1024
MAX_FINGERPRINT_BYTES = 32 * 1024 * 1024
MAX_SCAN_BYTES = 64 * 1024 * 1024
MAX_GIT_VISIBLE_PATHS = 100000
MAX_GIT_ATTRIBUTE_BYTES = 16 * 1024 * 1024
COMMAND_TIMEOUT = 3.0
WRITE_TOOLS = frozenset({"write", "edit", "multiedit", "write_file", "edit_file", "multi_edit", "replace"})
SHELL_TOOLS = frozenset({"bash", "powershell", "run_shell_command", "run-shell-command"})


def _unavailable(reason: str) -> dict[str, Any]:
    return {"status": "unavailable", "message": "Asset verification is unavailable: " + reason + ". Preserve existing files, use project conventions, and do not claim this check passed."}


def _message(payload: dict[str, Any]) -> str:
    parts: list[str] = []
    for item in payload.get("items", []):
        if isinstance(item, dict):
            parts.append(f"{item.get('path', '')}: {item.get('message', item.get('code', 'asset policy violation'))}")
    for key in ("blockers", "errors"):
        value = payload.get(key, [])
        if isinstance(value, list):
            parts.extend(str(item) for item in value[:3])
    if not parts:
        parts.append(str(payload.get("message") or payload.get("summary") or "asset validation did not pass"))
    return " | ".join(" ".join(part.split())[:300] for part in parts[:5])


def _runtime_argv(root: Path) -> list[str] | None:
    try:
        config = json.loads((root / ".specify/config.json").read_text(encoding="utf-8"))
        argv = config.get("runtime_launcher", {}).get("argv")
    except (OSError, ValueError, AttributeError):
        argv = None
    if isinstance(argv, list) and argv and all(isinstance(part, str) and part for part in argv):
        executable = Path(argv[0])
        if not executable.is_absolute():
            # A bare command is a global PATH lookup, not a project pin.
            if len(executable.parts) == 1:
                return None
            executable = root / executable
        if executable.is_file():
            return [str(executable), *argv[1:]]
        return None
    executable = root / ".specify/bin" / ("specify-runtime.exe" if os.name == "nt" else "specify-runtime")
    return [str(executable)] if executable.is_file() else None


def check_paths(root: Path, paths: list[str], *, path_only: bool, deleted_paths: list[str] | None = None) -> dict[str, Any]:
    """Delegate exact paths to Go; absent/old runtime never means passed."""
    deleted_paths = deleted_paths or []
    if not paths and not deleted_paths:
        return {}
    argv = _runtime_argv(root)
    if argv is None:
        return _unavailable("the pinned project runtime is missing")
    if len(paths) + len(deleted_paths) > MAX_PATHS:
        return _unavailable("the changed path set exceeds the bounded hook budget; check explicit task batches")
    command = [*argv, "assets", "check", "--format", "json"]
    if path_only:
        command.append("--path-only")
    for path in sorted(set(paths)):
        command.extend(["--path", path])
    for path in sorted(set(deleted_paths)):
        command.extend(["--deleted-path", path])
    # Discovery and validation are separate processes; preserve the existing
    # per-command cap while bounding the complete pair, including startup.
    deadline = time.monotonic() + 2 * COMMAND_TIMEOUT
    try:
        ensured = subprocess.run(
            [*argv, "api", "ensure", "--capabilities", "assets.check", "--format", "json"],
            cwd=root, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=COMMAND_TIMEOUT, check=False,
        )
        discovery = json.loads(ensured.stdout)
        data = discovery.get("data") if isinstance(discovery, dict) else None
        if not (
            ensured.returncode == 0 and isinstance(discovery, dict) and discovery.get("status") == "ok"
            and isinstance(data, dict)
            and data.get("requested") == ["assets.check"]
            and data.get("present") == ["assets.check"]
            and data.get("missing") == []
        ):
            return _unavailable("the pinned runtime does not advertise the required assets.check capability")
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return _unavailable("the runtime check exceeded its bounded hook deadline")
        result = subprocess.run(command, cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=min(COMMAND_TIMEOUT, remaining), check=False)
        payload = json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        return _unavailable("the runtime check exceeded its bounded hook deadline")
    except (OSError, ValueError):
        return _unavailable("the runtime returned no valid asset-check result")
    if not isinstance(payload, dict):
        return _unavailable("the runtime returned an invalid asset-check result")
    status = str(payload.get("status", ""))
    data = payload.get("data")
    if status == "ok" and result.returncode == 0 and isinstance(data, dict):
        reported_deleted = data.get("deleted_paths")
        if (
            type(data.get("checked")) is int
            and data["checked"] == len(set(paths))
            and data.get("path_only") is path_only
            and data.get("scope") == ("paths" if path_only else "worktree")
            and type(data.get("violation_count")) is int
            and data["violation_count"] == 0
            and isinstance(reported_deleted, list)
            and all(isinstance(path, str) for path in reported_deleted)
            and set(reported_deleted) == set(deleted_paths)
        ):
            return {"status": "ok", "path_only": path_only}
    if status == "blocked" and result.returncode in {0, 10}:
        return {"status": "blocked", "message": "Asset check: " + _message(payload), "path_only": path_only}
    return _unavailable("the runtime did not return a compatible assets.check result: " + _message(payload))


def _relative(root: Path, raw: str) -> str:
    # Keep lexical paths: Go must see and reject symlink/traversal attempts.
    path = Path(raw)
    if path.is_absolute():
        try:
            path = path.relative_to(root)
        except ValueError:
            return raw
    return path.as_posix()


def _write_paths(root: Path, tool_input: dict[str, Any]) -> list[str]:
    paths: list[str] = []
    for entry in [tool_input, *tool_input.get("edits", [])] if isinstance(tool_input.get("edits", []), list) else [tool_input]:
        if not isinstance(entry, dict):
            continue
        for key in ("file_path", "path", "absolute_path"):
            value = entry.get(key)
            if isinstance(value, str) and value:
                paths.append(_relative(root, value))
                break
    return sorted(set(paths))


def _obviously_read_only(command: str) -> bool:
    """Recognize a small read-only shell subset; never parse shell output."""
    if not command.strip() or re.search(r"[<>(){}`]|\n", command):
        return not command.strip()
    for segment in re.split(r"\s*(?:&&|\|\||[;&|])\s*", command):
        try:
            args = shlex.split(segment)
        except ValueError:
            return False
        if not args:
            continue
        name = Path(args[0]).name.lower()
        if name in {"pwd", "ls", "cat", "head", "tail", "wc", "stat", "file", "rg", "grep", "get-content", "get-childitem", "get-location", "get-item", "test-path", "select-string", "measure-object"}:
            if any(arg.startswith(("--pre", "--hostname-bin")) for arg in args[1:]):
                return False
            if name == "file" and any(arg == "--compile" or (arg.startswith("-") and not arg.startswith("--") and "C" in arg) for arg in args[1:]):
                return False
            continue
        if name == "sed" and len(args) >= 3 and args[1] == "-n" and re.fullmatch(r"[0-9]+(?:,[0-9]+)?p", args[2]) and not any(arg.startswith("-") for arg in args[3:]):
            continue
        # Status/diff/show/log can execute configured fsmonitor, clean/process
        # filters, textconv or external diff programs in the user's shell.
        # Our own safe Git queries cannot constrain those program effects.
        if name in {"git", "git.exe"} and len(args) > 1 and args[1] in {"ls-files", "rev-parse", "ls-tree", "check-ignore"}:
            if not any(arg.startswith(("--output", "--ext-diff", "--textconv")) for arg in args[2:]):
                continue
        return False
    return True


def _git(root: Path, args: list[str]) -> bytes | None:
    # Never accidentally observe a parent repository for an isolated generated
    # project. Both ordinary clones and linked worktrees have this entry.
    if not (root / ".git").exists():
        return None
    env = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
    command = ["git", "--no-optional-locks", "--no-pager", "-c", "core.fsmonitor=false"]
    if args and args[0] == "diff":
        args = ["diff", "--no-ext-diff", "--no-textconv", "--ignore-submodules=all", *args[1:]]
    elif args and args[0] == "status":
        args = ["status", "--ignore-submodules=all", *args[1:]]
    deadline = time.monotonic() + COMMAND_TIMEOUT

    def run(arguments: list[str], *, input: bytes | None = None):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise subprocess.TimeoutExpired(command, COMMAND_TIMEOUT)
        return subprocess.run(
            [*command, *arguments], cwd=root, env=env, input=input,
            capture_output=True, timeout=remaining, check=False,
        )

    try:
        verified = run(["rev-parse", "--show-toplevel"])
        if verified.returncode != 0 or len(verified.stdout) > MAX_STATE_BYTES:
            return None
        actual_root = Path(os.fsdecode(verified.stdout).rstrip("\r\n")).resolve()
        if actual_root != root.resolve():
            return None
        if args and args[0] in {"status", "diff"}:
            # Index flags can hide a changed worktree file from both queries.
            # Keep explicit target checking available without changing flags.
            if not _worktree_index_observation_is_safe(run):
                return None
            # Even name-only worktree queries can execute external clean or
            # process filters. Fall back to exact task paths without invoking
            # those programs or weakening a required filter's configuration.
            if not _worktree_filter_observation_is_safe(run):
                return None
        result = run(args)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0 or len(result.stdout) > MAX_STATE_BYTES:
        return None
    return result.stdout


def _worktree_index_observation_is_safe(run) -> bool:
    inventory = run(["ls-files", "-v", "-z"])
    raw = inventory.stdout
    if inventory.returncode != 0 or len(raw) > MAX_GIT_ATTRIBUTE_BYTES:
        return False
    if not raw:
        return True
    if not raw.endswith(b"\0"):
        return False
    records = raw[:-1].split(b"\0")
    if len(records) > MAX_GIT_VISIBLE_PATHS:
        return False
    return all(
        len(record) >= 3 and record[1:2] == b" "
        and record[0:1] != b"S" and not b"a" <= record[0:1] <= b"z"
        for record in records
    )


def _worktree_filter_observation_is_safe(run) -> bool:
    filters = run(["config", "--null", "--name-only", "--get-regexp", r"^filter\..*\.(clean|process)$"])
    if filters.returncode == 1 and not filters.stdout:
        return True
    if filters.returncode != 0 or len(filters.stdout) > MAX_STATE_BYTES or not filters.stdout.endswith(b"\0"):
        return False
    drivers = set()
    for name in filters.stdout[:-1].split(b"\0"):
        match = re.fullmatch(rb"filter\.(.+)\.(?:clean|process)", name)
        if match is None:
            return False
        drivers.add(match.group(1))
    visible = run(["ls-files", "--cached", "--others", "--exclude-standard", "-z"])
    if visible.returncode != 0 or len(visible.stdout) > MAX_GIT_ATTRIBUTE_BYTES:
        return False
    if not visible.stdout:
        return True
    if not visible.stdout.endswith(b"\0"):
        return False
    paths = sorted(set(visible.stdout[:-1].split(b"\0")))
    if not all(paths) or len(paths) > MAX_GIT_VISIBLE_PATHS:
        return False
    attributes = run(["check-attr", "-z", "--stdin", "filter"], input=b"\0".join(paths) + b"\0")
    if attributes.returncode != 0 or len(attributes.stdout) > MAX_GIT_ATTRIBUTE_BYTES or not attributes.stdout.endswith(b"\0"):
        return False
    fields = attributes.stdout[:-1].split(b"\0")
    if len(fields) != 3 * len(paths):
        return False
    path_set = set(paths)
    observed = set()
    for index in range(0, len(fields), 3):
        path, attribute, value = fields[index:index + 3]
        if path not in path_set or path in observed or attribute != b"filter" or value in drivers:
            return False
        observed.add(path)
    return observed == path_set


def _status_paths(root: Path) -> list[str] | None:
    raw = _git(root, ["status", "--porcelain=v1", "-z", "--untracked-files=all"])
    if raw is None:
        return None
    fields = raw.decode("utf-8", errors="surrogateescape").split("\0")
    paths: list[str] = []
    index = 0
    while index < len(fields):
        field = fields[index]
        index += 1
        if not field:
            continue
        paths.append(field[3:])
        if "R" in field[:2] or "C" in field[:2]:
            if index < len(fields) and fields[index]:
                paths.append(fields[index])
                index += 1
    paths = sorted({path for path in paths if path and not path.startswith(CACHE_ROOT + "/")})
    return paths if len(paths) <= MAX_PATHS else None


def _fingerprint(root: Path, relative: str, budget: list[int] | None = None) -> str:
    path = root / relative
    try:
        # Dirty deltas can include untrusted paths. Never follow a parent link
        # outside the observed project merely to compare disposable metadata.
        parent = root
        for part in Path(relative).parts[:-1]:
            parent /= part
            if _is_link(parent.lstat()):
                return "unknown"
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode):
            return "link:" + hashlib.sha256(os.readlink(path).encode()).hexdigest()
        if _is_link(info) or not stat.S_ISREG(info.st_mode):
            return "non-regular"
        if info.st_size > MAX_FINGERPRINT_BYTES or (budget is not None and info.st_size > budget[0]):
            return "unknown"
        if budget is not None:
            budget[0] -= info.st_size
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            opened = os.fstat(stream.fileno())
            if not os.path.samestat(info, opened):
                return "unknown"
            remaining = info.st_size
            while remaining:
                chunk = stream.read(min(65536, remaining))
                if not chunk:
                    return "unknown"
                digest.update(chunk)
                remaining -= len(chunk)
            after = os.fstat(stream.fileno())
            if stream.read(1) or any(getattr(opened, field) != getattr(after, field) for field in ("st_size", "st_mtime_ns", "st_ctime_ns", "st_mode")):
                return "unknown"
            if not os.path.samestat(after, path.lstat()):
                return "unknown"
        return f"{stat.S_IMODE(info.st_mode)}:{digest.hexdigest()}"
    except FileNotFoundError:
        return "missing"
    except (OSError, ValueError):
        return "unknown"


def _cache_path(root: Path, payload: dict[str, Any], integration: str) -> Path | None:
    identity = payload.get("session_id") or payload.get("sessionId") or payload.get("transcript_path") or payload.get("transcriptPath")
    if not isinstance(identity, str) or not identity:
        return None
    key = hashlib.sha256((str(root) + "\0" + integration + "\0" + identity).encode()).hexdigest()[:32]
    return root / CACHE_ROOT / (key + ".json")


def _safe_cache_parent(root: Path, path: Path, *, create: bool) -> bool:
    current = root
    for part in path.parent.relative_to(root).parts:
        current = current / part
        try:
            if create:
                current.mkdir(exist_ok=True)
            info = current.lstat()
            if _is_link(info) or not stat.S_ISDIR(info.st_mode):
                return False
        except OSError:
            return False
    return True


def _is_link(info: os.stat_result) -> bool:
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    )


def _read_state(path: Path) -> dict[str, Any] | None:
    try:
        info = path.lstat()
        if _is_link(info) or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > MAX_STATE_BYTES:
            return None
        state = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(state, dict) or type(state.get("schema_version")) is not int or state["schema_version"] != 1:
            return None
        head = state.get("head")
        if not isinstance(head, str) or (head and not re.fullmatch(r"[0-9a-f]{40,64}", head)):
            return None
        if any(type(state.get(key)) is not bool for key in ("shell", "git_available")):
            return None
        touched = state.get("touched")
        if not isinstance(touched, list) or len(touched) > MAX_PATHS or not all(isinstance(name, str) and _safe_relative(name) for name in touched):
            return None
        for key in ("baseline", "initial"):
            values = state.get(key)
            if not isinstance(values, dict) or len(values) > MAX_PATHS or not all(isinstance(name, str) and _safe_relative(name) and _valid_fingerprint(value) for name, value in values.items()):
                return None
        if set(state["initial"]) != set(touched) or len(set(touched)) != len(touched):
            return None
        return state
    except (OSError, ValueError):
        pass
    return None


def _valid_fingerprint(value: Any) -> bool:
    return isinstance(value, str) and (
        value in {"missing", "unknown", "non-regular"}
        or bool(re.fullmatch(r"(?:link|[0-9]{1,4}):[0-9a-f]{64}", value))
    )


def _safe_relative(name: str) -> bool:
    path = Path(name)
    return bool(name) and not path.is_absolute() and not path.drive and ".." not in path.parts


@contextmanager
def _state_lock(path: Path):
    lock = path.with_suffix(".lock")
    deadline = time.monotonic() + 0.5
    acquired = False
    while time.monotonic() < deadline:
        try:
            lock.mkdir()
            acquired = True
            break
        except FileExistsError:
            time.sleep(0.02)
        except OSError:
            break
    try:
        yield acquired
    finally:
        if acquired:
            try:
                lock.rmdir()
            except OSError:
                pass


def _save_state(path: Path, state: dict[str, Any]) -> None:
    raw = json.dumps(state, ensure_ascii=True, separators=(",", ":"))
    if len(raw.encode()) > MAX_STATE_BYTES:
        raise ValueError("session observation exceeds its bounded budget")
    if path.exists() and _read_state(path) is None:
        raise ValueError("session observation is invalid or unsafe")
    descriptor, temporary = tempfile.mkstemp(prefix=".asset-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(raw)
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def _observe(root: Path, payload: dict[str, Any], integration: str, paths: list[str], shell: bool) -> dict[str, Any]:
    if not all(_safe_relative(name) for name in paths):
        return _unavailable("the requested target is outside this project's observation scope")
    path = _cache_path(root, payload, integration)
    if path is None:
        return _unavailable("the native event has no session identity; check the task's final exact changed paths")
    if not _safe_cache_parent(root, path, create=True):
        return _unavailable("the disposable observation directory is unsafe or unwritable")
    with _state_lock(path) as locked:
        if not locked:
            return _unavailable("another event is updating this session observation")
        state = _read_state(path)
        if state is None:
            if path.exists() or path.is_symlink():
                return _unavailable("the existing disposable observation is invalid or unsafe")
            current = _status_paths(root)
            head = _git(root, ["rev-parse", "--verify", "HEAD"])
            budget = [MAX_SCAN_BYTES]
            state = {"schema_version": 1, "head": head.decode().strip() if head else "", "baseline": {name: _fingerprint(root, name, budget) for name in current or []}, "git_available": current is not None, "touched": [], "initial": {}, "shell": False}
        touched = sorted(set(state.get("touched", [])) | set(paths))
        if len(touched) > MAX_PATHS:
            return _unavailable("the task's explicit output set exceeds the bounded hook budget")
        state["touched"] = touched
        initial = state.setdefault("initial", {})
        budget = [MAX_SCAN_BYTES]
        for name in paths:
            if name not in initial:
                initial[name] = _fingerprint(root, name, budget)
        state["shell"] = bool(state.get("shell")) or shell
        try:
            _save_state(path, state)
        except (OSError, ValueError) as exc:
            return _unavailable(str(exc))
    return {}


def before_tool(root: Path, payload: dict[str, Any], integration: str, *, owner_paths: set[str] | None = None) -> dict[str, Any]:
    root = root.resolve()
    name = str(payload.get("tool_name") or payload.get("toolName") or "").lower()
    tool_input = payload.get("tool_input") or payload.get("toolInput") or {}
    if not isinstance(tool_input, dict):
        return {}
    if name in WRITE_TOOLS:
        paths = _write_paths(root, tool_input)
        if not paths:
            return _unavailable("this file tool did not provide an exact target path")
        # Only the existing host workflow gate can supply these exact repair
        # paths. They are never read from tool payloads or project policy.
        owned = {_relative(root, path) for path in owner_paths or set()}
        paths = [path for path in paths if path not in owned]
        if not paths:
            return {}
        result = check_paths(root, paths, path_only=True)
        if result.get("status") == "blocked":
            return result
        observation = _observe(root, payload, integration, paths, False)
        return result if result.get("status") == "unavailable" else observation
    if name in SHELL_TOOLS:
        command = str(tool_input.get("command") or "")
        if not _obviously_read_only(command):
            return _observe(root, payload, integration, [], True)
    return {}


def finish_turn(root: Path, payload: dict[str, Any], integration: str) -> dict[str, Any]:
    root = root.resolve()
    path = _cache_path(root, payload, integration)
    if path is None or not _safe_cache_parent(root, path, create=False):
        return {}
    if not path.exists() and not path.is_symlink():
        return {}
    result: dict[str, Any] = {}
    with _state_lock(path) as locked:
        if not locked:
            return _unavailable("another event is updating this session observation")
        state = _read_state(path)
        if state is None:
            return _unavailable("the disposable observation is invalid or unsafe")
        touched = {name for name in state.get("touched", []) if isinstance(name, str)}
        changed = set(touched)
        candidates: set[str] = set()
        baseline = state.get("baseline", {})
        current = _status_paths(root)
        if state["shell"] and (not state["git_available"] or not state["head"]):
            result = _unavailable("the shell task has no complete starting Git baseline; check its exact output paths")
        if current is not None:
            # Starting dirty/untracked paths can disappear from both status
            # and the HEAD diff when deleted or restored by this task. Compare
            # them too so deletion/reverse-reference checks retain that scope.
            candidates = set(current) | set(baseline)
            head = state.get("head")
            if isinstance(head, str) and re.fullmatch(r"[0-9a-f]{40,64}", head):
                diff = _git(root, ["diff", "--name-only", "-z", head, "--"])
                if diff is None:
                    result = _unavailable("the task's original Git baseline is unavailable")
                else:
                    candidates.update(name for name in diff.decode("utf-8", errors="surrogateescape").split("\0") if name)
            if len(candidates) > MAX_PATHS:
                result = _unavailable("the changed path set exceeds the bounded hook budget")
            else:
                budget = [MAX_SCAN_BYTES]
                for name in candidates:
                    if name.startswith(CACHE_ROOT + "/"):
                        continue
                    fingerprint = _fingerprint(root, name, budget)
                    if name not in baseline or fingerprint == "unknown" or fingerprint != baseline[name]:
                        changed.add(name)
        elif state.get("shell"):
            result = _unavailable("Git cannot identify files created by shell tools; check the task's exact output paths")
        # Deletions are explicit so a misspelled path cannot masquerade as an
        # authorized delete. Go owns bounded reverse-reference validation.
        retained = sorted(name for name in changed if (root / name).exists() or (root / name).is_symlink())
        initial = state.get("initial", {})
        deleted = sorted(name for name in changed - set(retained) if initial.get(name) not in {None, "missing"} or (name in candidates and baseline.get(name) != "missing"))
        checked = check_paths(root, retained, path_only=False, deleted_paths=deleted)
        if checked.get("status") in {"blocked", "unavailable"}:
            result = checked
        if result.get("status") == "blocked":
            inferred = set(retained + deleted) - touched
            if inferred:
                result["message"] += " Some paths were discovered from the Git delta; establish their task/worker ownership before changing another actor's files."
        else:
            # Clean and unavailable observations are disposable. Unavailable is
            # reported explicitly; deleting this cache never changes readiness.
            path.unlink()
    try:
        path.parent.rmdir()
    except OSError:
        pass
    return result
