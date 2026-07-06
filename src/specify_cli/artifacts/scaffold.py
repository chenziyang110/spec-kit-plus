"""Create fixed workflow artifact scaffolds from registered templates."""

from __future__ import annotations

import errno
import json
import os
import stat
from collections.abc import Mapping, Sequence
from pathlib import Path
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any

from .registry import ArtifactKind, get_artifact_kind


class ArtifactScaffoldError(ValueError):
    """Raised when artifact scaffold generation fails."""


def scaffold_artifact(
    project_root: Path,
    *,
    kind: str,
    out_path: str,
    variables: dict[str, Any] | None = None,
) -> dict[str, Any]:
    artifact_kind = _get_artifact_kind(kind)
    values = variables or {}
    _reject_unsafe_status(values)

    relative_path = _normalize_output_path(out_path)
    if not _matches_any_allowed_path(relative_path, artifact_kind.allowed_output_paths):
        raise ArtifactScaffoldError("unsafe_path: output path is not allowed for kind")

    root = project_root.resolve()
    target = root / Path(*relative_path.parts)
    allowed_roots = _allowed_kind_roots(root, artifact_kind, relative_path)
    _reject_symlink_escape(root, target, allowed_roots)

    if target.exists() or target.is_symlink():
        raise ArtifactScaffoldError("blocked_existing_file: target already exists")

    template = _locate_template(root, artifact_kind.source_template)
    rendered = _render_template(template, values, artifact_kind)

    _reject_unsafe_existing_components(root, target)
    target.parent.mkdir(parents=True, exist_ok=True)
    _reject_symlink_escape(root, target, allowed_roots)
    _write_create_only(root, target, rendered, allowed_roots)
    _reject_written_path_escape(root, target, allowed_roots)

    audit = artifact_kind.audit_record()
    return {
        "status": "created",
        "kind": artifact_kind.kind,
        "path": relative_path.as_posix(),
        "estimated_token_savings": audit["estimated_token_savings"],
        "agent_fill_required": list(artifact_kind.agent_fill_required),
        "fill_targets": artifact_kind.fill_targets,
    }


def _get_artifact_kind(kind: str) -> ArtifactKind:
    try:
        return get_artifact_kind(kind)
    except ValueError as exc:
        raise ArtifactScaffoldError(str(exc)) from exc


def _normalize_output_path(out_path: str) -> PurePosixPath:
    if not out_path or "\\" in out_path:
        raise ArtifactScaffoldError("unsafe_path: output path must be relative POSIX")
    if Path(out_path).is_absolute() or PureWindowsPath(out_path).is_absolute():
        raise ArtifactScaffoldError("unsafe_path: output path must be relative")

    relative_path = PurePosixPath(out_path)
    if relative_path.is_absolute() or any(
        part in {"", ".."} for part in relative_path.parts
    ):
        raise ArtifactScaffoldError("unsafe_path: output path contains unsafe segments")
    if str(relative_path) in {"", "."}:
        raise ArtifactScaffoldError("unsafe_path: output path is empty")

    return relative_path


def _matches_any_allowed_path(
    relative_path: PurePosixPath, patterns: tuple[str, ...]
) -> bool:
    return any(
        _path_matches_pattern(relative_path, PurePosixPath(pattern))
        for pattern in patterns
    )


def _path_matches_pattern(relative_path: PurePosixPath, pattern: PurePosixPath) -> bool:
    path_parts = relative_path.parts
    pattern_parts = pattern.parts
    if len(path_parts) != len(pattern_parts):
        return False

    return all(
        pattern_part == "*" or pattern_part == path_part
        for path_part, pattern_part in zip(path_parts, pattern_parts)
    )


def _allowed_kind_roots(
    project_root: Path,
    artifact_kind: ArtifactKind,
    relative_path: PurePosixPath,
) -> list[Path]:
    roots: list[Path] = []
    for pattern in artifact_kind.allowed_output_paths:
        pattern_parts = PurePosixPath(pattern).parts
        prefix_parts: list[str] = []
        for part in pattern_parts:
            if part == "*":
                break
            prefix_parts.append(part)
        if prefix_parts and _path_matches_pattern(relative_path, PurePosixPath(pattern)):
            roots.append((project_root / Path(*prefix_parts)).resolve(strict=False))

    return roots


def _reject_symlink_escape(
    project_root: Path, target: Path, allowed_roots: list[Path]
) -> None:
    parent = target.parent
    existing_parent = parent
    while not existing_parent.exists() and existing_parent != project_root:
        existing_parent = existing_parent.parent

    resolved_parent = existing_parent.resolve()
    if not _is_relative_to(resolved_parent, project_root):
        raise ArtifactScaffoldError("unsafe_path: output path escapes project root")

    if allowed_roots and not any(
        _is_relative_to(resolved_parent, allowed_root)
        or _is_relative_to(allowed_root, resolved_parent)
        for allowed_root in allowed_roots
    ):
        raise ArtifactScaffoldError("unsafe_path: output path escapes allowed kind root")


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _locate_template(project_root: Path, source_template: str) -> Path:
    package_root = Path(__file__).resolve().parent.parent
    candidates = (
        project_root / ".specify" / source_template,
        package_root / "core_pack" / source_template,
        package_root.parent.parent / source_template,
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate

    raise ArtifactScaffoldError(f"missing_template: {source_template}")


def _render_template(
    template: Path, variables: Mapping[str, Any], artifact_kind: ArtifactKind
) -> str:
    if template.suffix == ".json":
        payload = json.loads(template.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ArtifactScaffoldError("invalid_template: JSON scaffold must be an object")
        allowed_json_keys = _json_fill_target_keys(artifact_kind)
        for key, value in variables.items():
            _reject_unsafe_status_value(key, value)
            if key not in allowed_json_keys:
                if key in payload:
                    raise ArtifactScaffoldError(
                        f"unsafe_variable: {key} is not a declared JSON fill target"
                    )
                continue
            payload[key] = value
        return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"

    rendered = template.read_text(encoding="utf-8")
    for key in ("id", "slug", "title", "trigger"):
        value = _sanitize_markdown_yaml_scalar(key, variables.get(key, ""))
        rendered = rendered.replace("{{" + key + "}}", value)
    return rendered


def _json_fill_target_keys(artifact_kind: ArtifactKind) -> set[str]:
    keys: set[str] = set()
    for target in artifact_kind.fill_targets.values():
        if target.get("type") != "json_pointer":
            continue
        pointer = target.get("pointer", "")
        if not pointer.startswith("/") or "/" in pointer[1:]:
            continue
        key = pointer[1:]
        if key:
            keys.add(key)
    return keys


def _sanitize_markdown_yaml_scalar(key: str, value: Any) -> str:
    text = "" if value is None else str(value)
    if (
        "\r" in text
        or "\n" in text
        or "---" in text
        or "..." in text
        or any(ord(char) < 32 or ord(char) == 127 for char in text)
    ):
        raise ArtifactScaffoldError(f"unsafe_variable: {key} contains unsafe content")

    return text.replace("\\", "\\\\").replace('"', '\\"')


def _write_create_only(
    project_root: Path, target: Path, content: str, allowed_roots: list[Path]
) -> None:
    _reject_unsafe_existing_components(project_root, target)
    _reject_symlink_escape(project_root, target, allowed_roots)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    if os.name != "nt" and nofollow:
        fd: int | None = None
        try:
            fd = os.open(target, flags | nofollow)
            buffer = memoryview(content.encode("utf-8"))
            while buffer:
                written = os.write(fd, buffer)
                if written == 0:
                    raise OSError("failed to write scaffold content")
                buffer = buffer[written:]
        except FileExistsError as exc:
            raise ArtifactScaffoldError("blocked_existing_file: target already exists") from exc
        except OSError as exc:
            if exc.errno in {errno.ELOOP}:
                raise ArtifactScaffoldError(
                    "unsafe_path: target path uses unsafe symlink"
                ) from exc
            raise
        finally:
            if fd is not None:
                os.close(fd)
        return

    directory_handles = _hold_windows_directory_handles(project_root, target)
    try:
        _reject_unsafe_existing_components(project_root, target)
        _reject_symlink_escape(project_root, target, allowed_roots)
        if target.exists() or target.is_symlink():
            raise ArtifactScaffoldError("blocked_existing_file: target already exists")

        with target.open("x", encoding="utf-8", newline="") as handle:
            _reject_unsafe_existing_components(project_root, target)
            _reject_symlink_escape(project_root, target, allowed_roots)
            handle.write(content)
    except FileExistsError as exc:
        raise ArtifactScaffoldError("blocked_existing_file: target already exists") from exc
    except OSError as exc:
        if exc.errno in {errno.ELOOP}:
            raise ArtifactScaffoldError("unsafe_path: target path uses unsafe symlink") from exc
        raise
    finally:
        _close_windows_directory_handles(directory_handles)


def _reject_written_path_escape(
    project_root: Path, target: Path, allowed_roots: list[Path]
) -> None:
    try:
        resolved_target = target.resolve(strict=True)
    except FileNotFoundError as exc:
        raise ArtifactScaffoldError("unsafe_path: target disappeared after write") from exc

    if not _is_relative_to(resolved_target, project_root):
        raise ArtifactScaffoldError("unsafe_path: output path escapes project root")
    if allowed_roots and not any(
        _is_relative_to(resolved_target, allowed_root) for allowed_root in allowed_roots
    ):
        raise ArtifactScaffoldError("unsafe_path: output path escapes allowed kind root")


def _reject_unsafe_existing_components(project_root: Path, target: Path) -> None:
    root = project_root.resolve()
    current = root
    parent = target.parent

    try:
        relative_parts = parent.relative_to(root).parts
    except ValueError as exc:
        raise ArtifactScaffoldError("unsafe_path: output path escapes project root") from exc

    for part in relative_parts:
        current = current / part
        if not current.exists() and not current.is_symlink():
            return
        if _is_reparse_like_path(current):
            raise ArtifactScaffoldError(
                "unsafe_path: output path uses unsafe symlink or reparse point"
            )


def _is_reparse_like_path(path: Path) -> bool:
    try:
        if path.is_symlink():
            return True
        attrs = path.lstat().st_file_attributes
    except AttributeError:
        return False
    except OSError:
        return True

    return bool(attrs & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x0400))


def _hold_windows_directory_handles(project_root: Path, target: Path) -> list[int]:
    if os.name != "nt":
        return []

    import ctypes
    from ctypes import wintypes

    create_file = ctypes.windll.kernel32.CreateFileW
    create_file.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    create_file.restype = wintypes.HANDLE

    handles: list[int] = []
    current = project_root.resolve()
    parent = target.parent
    try:
        relative_parts = parent.relative_to(current).parts
    except ValueError as exc:
        raise ArtifactScaffoldError("unsafe_path: output path escapes project root") from exc

    paths = [current]
    paths.extend(
        current.joinpath(*relative_parts[:index])
        for index in range(1, len(relative_parts) + 1)
    )

    try:
        for path in paths:
            if _is_reparse_like_path(path):
                raise ArtifactScaffoldError(
                    "unsafe_path: output path uses unsafe symlink or reparse point"
                )
            handle = create_file(
                str(path),
                0,
                0x00000001 | 0x00000002,
                None,
                3,
                0x02000000,
                None,
            )
            if handle == wintypes.HANDLE(-1).value:
                raise ctypes.WinError()
            handles.append(int(handle))
            if _is_reparse_like_path(path):
                raise ArtifactScaffoldError(
                    "unsafe_path: output path uses unsafe symlink or reparse point"
                )
    except Exception:
        _close_windows_directory_handles(handles)
        raise

    return handles


def _close_windows_directory_handles(handles: list[int]) -> None:
    if not handles:
        return

    import ctypes
    from ctypes import wintypes

    close_handle = ctypes.windll.kernel32.CloseHandle
    close_handle.argtypes = [wintypes.HANDLE]
    close_handle.restype = wintypes.BOOL
    for handle in reversed(handles):
        close_handle(wintypes.HANDLE(handle))


def _reject_unsafe_status(variables: Mapping[str, Any]) -> None:
    for key, value in variables.items():
        _reject_unsafe_status_value(key, value)


def _reject_unsafe_status_value(key: object, value: Any) -> None:
    unsafe_values = {
        "approved",
        "confirmed",
        "ready",
        "true",
        "user-confirmed",
        "user_confirmed",
    }

    normalized_key = str(key).lower().replace("-", "_")
    if _is_readiness_sensitive_key(normalized_key):
        if value is True:
            raise ArtifactScaffoldError(
                "unsafe_status: scaffold variables cannot assert readiness"
            )
        if isinstance(value, str) and value.strip().lower() in unsafe_values:
            raise ArtifactScaffoldError(
                "unsafe_status: scaffold variables cannot assert readiness"
            )
        if isinstance(value, Mapping):
            ready_value = value.get("ready")
            if ready_value is True or (
                isinstance(ready_value, str)
                and ready_value.strip().lower() in unsafe_values
            ):
                raise ArtifactScaffoldError(
                    "unsafe_status: scaffold variables cannot assert readiness"
                )

    if isinstance(value, Mapping):
        for nested_key, nested_value in value.items():
            _reject_unsafe_status_value(nested_key, nested_value)
    elif _is_nonstring_sequence(value):
        for item in value:
            _reject_unsafe_status_value(key, item)


def _is_nonstring_sequence(value: object) -> bool:
    return isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray)
    )


def _is_readiness_sensitive_key(key: str) -> bool:
    return (
        key == "status"
        or "ready" in key
        or "approved" in key
        or "confirmed" in key
        or key.endswith("_status")
    )
