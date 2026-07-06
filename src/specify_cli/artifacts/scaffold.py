"""Create fixed workflow artifact scaffolds from registered templates."""

from __future__ import annotations

import errno
import json
import os
from collections.abc import Mapping
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
    rendered = _render_template(template, values)

    target.parent.mkdir(parents=True, exist_ok=True)
    _reject_symlink_escape(root, target, allowed_roots)
    _write_create_only(target, rendered)

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


def _render_template(template: Path, variables: Mapping[str, Any]) -> str:
    if template.suffix == ".json":
        payload = json.loads(template.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ArtifactScaffoldError("invalid_template: JSON scaffold must be an object")
        for key, value in variables.items():
            if key in payload:
                payload[key] = value
        return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"

    rendered = template.read_text(encoding="utf-8")
    for key in ("id", "slug", "title", "trigger"):
        value = _sanitize_markdown_yaml_scalar(key, variables.get(key, ""))
        rendered = rendered.replace("{{" + key + "}}", value)
    return rendered


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


def _write_create_only(target: Path, content: str) -> None:
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

    if target.exists() or target.is_symlink():
        raise ArtifactScaffoldError("blocked_existing_file: target already exists")

    try:
        with target.open("x", encoding="utf-8", newline="") as handle:
            handle.write(content)
    except FileExistsError as exc:
        raise ArtifactScaffoldError("blocked_existing_file: target already exists") from exc
    except OSError as exc:
        if exc.errno in {errno.ELOOP}:
            raise ArtifactScaffoldError("unsafe_path: target path uses unsafe symlink") from exc
        raise


def _reject_unsafe_status(variables: Mapping[str, Any]) -> None:
    unsafe_values = {
        "approved",
        "confirmed",
        "ready",
        "true",
        "user-confirmed",
        "user_confirmed",
    }

    for key, value in variables.items():
        normalized_key = str(key).lower().replace("-", "_")
        if not _is_readiness_sensitive_key(normalized_key):
            continue
        if value is True:
            raise ArtifactScaffoldError(
                "unsafe_status: scaffold variables cannot assert readiness"
            )
        if isinstance(value, str) and value.strip().lower() in unsafe_values:
            raise ArtifactScaffoldError(
                "unsafe_status: scaffold variables cannot assert readiness"
            )


def _is_readiness_sensitive_key(key: str) -> bool:
    return (
        key == "status"
        or "ready" in key
        or "approved" in key
        or "confirmed" in key
        or key.endswith("_status")
    )
