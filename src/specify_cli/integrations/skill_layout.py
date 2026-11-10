"""Ownership checks and migration for project skill destinations."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from hashlib import sha256
import os
from pathlib import Path
import stat
import tempfile

from ..atomic_io import (
    atomic_write_bytes,
    interprocess_lock,
    read_local_state_bytes,
    safe_local_state_path,
)
from .manifest import (
    IntegrationManifest,
    ManifestConflictError,
    _locked_manifest_revision,
    _manifest_revision,
    _matches_recorded_hash,
    _other_manifest_assets,
    _sha256,
)


@contextmanager
def skill_layout_lock(project_root: Path) -> Iterator[None]:
    """Serialize cooperating layout writers for this project across agents."""
    root = safe_local_state_path(project_root)
    path = safe_local_state_path(root / ".specify/runtime/skill-layout.lock", root=root)
    with interprocess_lock(path):
        yield


def _path_key(path: Path) -> str:
    return os.path.normcase(os.fspath(path))


def _directory(path: Path, root: Path) -> bool:
    safe_local_state_path(path, root=root)
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return False
    if not stat.S_ISDIR(metadata.st_mode):
        raise ValueError(f"Skill directory conflicts with an existing file: {path.relative_to(root)}")
    return True


def _planned_directories(
    root: Path, skills_dir: Path, planned_roots: Iterable[str | Path],
) -> list[Path]:
    if ".." in skills_dir.parts:
        raise ValueError("Skill destination must be a canonical project path")
    directory = safe_local_state_path(skills_dir, root=root)
    if directory == root:
        raise ValueError("Skill destination must be below the project root")
    _directory(directory, root)
    directories = set()
    for item in planned_roots:
        candidate = Path(item)
        if not candidate.is_absolute():
            candidate = directory / candidate
        if (
            candidate.parent != directory
            or candidate.name in {"", ".", ".."}
            or ":" in candidate.name
        ):
            raise ValueError(f"Skill directory must be a direct child of the destination: {item}")
        directories.add(candidate)
    return sorted(directories)


def _manifest_assets(manifest: IntegrationManifest, root: Path) -> dict[str, str]:
    if manifest.project_root != root:
        raise ValueError("Skill manifest belongs to another project")
    path = manifest._observe_manifest()
    if _manifest_revision(path, root) != manifest._observed_revision:
        raise ManifestConflictError("Skill manifest changed; reload it before continuing")
    return {_path_key(root / relative): digest for relative, digest in manifest.files.items()}


def _check_owned_tree(path: Path, root: Path, owners: list[dict[str, str]]) -> None:
    for child in sorted(path.iterdir()):
        safe_local_state_path(child, root=root)
        metadata = child.lstat()
        key = _path_key(child)
        expected = [owner[key] for owner in owners if key in owner]
        if stat.S_ISDIR(metadata.st_mode) and not expected:
            _check_owned_tree(child, root, owners)
            continue
        relative = child.relative_to(root)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise ValueError(f"Skill layout requires a regular, unlinked file: {relative}")
        if not expected:
            raise ValueError(f"Skill layout would overwrite an untracked file: {relative}")
        if any(not _matches_recorded_hash(child, digest) for digest in set(expected)):
            raise ValueError(f"Skill layout would overwrite a modified file: {relative}")


def preflight_skill_install(
    project_root: Path,
    manifest: IntegrationManifest,
    skills_dir: Path,
    planned_roots: Iterable[str | Path],
    *,
    replacing_manifest: IntegrationManifest | None = None,
) -> None:
    """Check each planned skill and all of its sidecars before installation.

    Peer claims also reserve missing paths. A switch may explicitly supply the
    outgoing manifest, whose files still have to match their recorded hashes.
    This is a read-only observation. Layout writers should hold the project
    lock around preflight and the ensuing writes.
    """
    root = safe_local_state_path(project_root)
    directories = _planned_directories(root, skills_dir, planned_roots)
    if not directories:
        return
    owners = [_manifest_assets(manifest, root)]
    if replacing_manifest is not None:
        owners.append(_manifest_assets(replacing_manifest, root))
    peers = _other_manifest_assets(
        root,
        manifest.manifest_path,
        replacing_manifest=replacing_manifest.manifest_path if replacing_manifest else None,
    )
    for directory in directories:
        directory_alias = Path(os.fspath(directory).casefold())
        for peer in peers:
            claimed = Path(peer)
            # Case-only aliases can identify the same asset on macOS and Windows.
            claim_alias = Path(os.fspath(claimed).casefold())
            directory_alias = Path(os.fspath(directory).casefold())
            if claim_alias.is_relative_to(directory_alias) or directory_alias.is_relative_to(claim_alias):
                relative = claimed.relative_to(root)
                raise ValueError(f"Skill layout conflicts with another integration's file: {relative}")
        if _directory(directory, root):
            _check_owned_tree(directory, root, owners)


@dataclass(frozen=True)
class _SkillFile:
    record: str
    source: Path
    target: Path
    content: bytes
    digest: str
    metadata: os.stat_result


def _migration_files(
    root: Path, manifest: IntegrationManifest, source: Path, target: Path,
    *, flat_project_skills: bool,
) -> list[_SkillFile]:
    inventory = []
    for relative, expected in sorted(manifest.files.items()):
        path = root / relative
        if not path.is_relative_to(source):
            continue
        inside = path.relative_to(source)
        if len(inside.parts) < 2 or any(part in {"..", "."} or ":" in part for part in inside.parts):
            raise ValueError(f"Invalid tracked skill path: {relative}")
        inventory.append((relative, path, target / inside, inside.parts[0], expected))
    names = {name for _, _, _, name, _ in inventory}
    if flat_project_skills:
        names.update(f"{name}.md" for name in tuple(names) if name != "references")
    preflight_skill_install(root, manifest, source, names)
    preflight_skill_install(root, manifest, target, names)

    assets = []
    for relative, path, destination, _, expected in inventory:
        if destination.exists():
            raise ValueError(f"Skill migration destination already exists: {destination.relative_to(root)}")
        try:
            metadata = safe_local_state_path(path, root=root).lstat()
        except FileNotFoundError as exc:
            raise ValueError(f"Repair the missing skill file before migration: {path.relative_to(root)}") from exc
        if os.name == "nt" and not metadata.st_mode & stat.S_IWRITE:
            raise ValueError(f"Skill migration cannot move a read-only file: {path.relative_to(root)}")
        content = read_local_state_bytes(path, root=root)
        digest = sha256(content).hexdigest()
        if digest != expected and (
            not _matches_recorded_hash(path, expected) or _sha256(path) != digest
        ):
            raise ValueError(f"Skill migration found a modified file: {path.relative_to(root)}")
        assets.append(_SkillFile(relative, path, destination, content, digest, metadata))
    return assets


def _create_parents(path: Path, root: Path, created: list[Path]) -> None:
    missing = []
    while not _directory(path, root):
        missing.append(path)
        path = path.parent
    for directory in reversed(missing):
        safe_local_state_path(directory, root=root)
        try:
            directory.mkdir()
        except FileExistsError:
            _directory(directory, root)
        else:
            created.append(directory)


def _publish_exclusive(stage: Path, destination: Path) -> None:
    if os.name == "nt":
        # On Windows a rename fails when the destination is already present.
        stage.rename(destination)
    else:
        os.link(stage, destination)


def _publish_new_file(
    path: Path,
    asset: _SkillFile,
    root: Path,
    created: list[Path],
    published: dict[Path, os.stat_result],
) -> None:
    """Stage a complete file and publish without replacing an existing path."""
    _create_parents(path.parent, root, created)
    safe_local_state_path(path, root=root)
    stage = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent, prefix=".specify-layout-", delete=False,
        ) as handle:
            stage = Path(handle.name)
            handle.write(asset.content)
            handle.flush()
            os.fsync(handle.fileno())
        stage.chmod(stat.S_IMODE(asset.metadata.st_mode))
        identity = stage.lstat()
        safe_local_state_path(path, root=root)
        published[path] = identity
        _publish_exclusive(stage, path)
    except BaseException as error:
        if stage is not None:
            try:
                stage.unlink(missing_ok=True)
            except OSError as exc:
                error.add_note(f"Could not remove temporary skill file {stage}: {exc}")
        raise
    else:
        if stage is not None:
            stage.unlink(missing_ok=True)


def _check_unchanged(
    path: Path,
    root: Path,
    identity: os.stat_result,
    digest: str,
    *,
    require_unlinked: bool = True,
) -> Path:
    target = safe_local_state_path(path, root=root)
    metadata = target.lstat()
    if (
        not os.path.samestat(identity, metadata)
        or (require_unlinked and metadata.st_nlink != 1)
        or (os.name != "nt" and metadata.st_mode != identity.st_mode)
        or _sha256(target) != digest
        or not os.path.samestat(identity, target.lstat())
    ):
        raise ValueError(f"Skill file changed during migration: {path.relative_to(root)}")
    return target


def _remove_empty(path: Path, root: Path) -> None:
    try:
        safe_local_state_path(path, root=root).rmdir()
    except (OSError, ValueError):
        pass


def migrate_skill_layout(
    project_root: Path,
    manifest: IntegrationManifest,
    source_skills_dir: Path,
    target_skills_dir: Path,
    *,
    layout: str,
    flat_project_skills: bool = False,
) -> list[Path]:
    """Move the active integration's unchanged skill inventory and save its layout.

    Copy first, then remove the old copies and publish the manifest under its
    existing revision lock. A failed migration restores the old files and
    manifest, and rolls back only destination files it still identifies as its
    own. External writers can still prevent restoration.
    """
    if layout not in ("native", "shared"):
        raise ValueError(f"Invalid skill layout: {layout!r}")
    root = safe_local_state_path(project_root)
    if manifest.project_root != root:
        raise ValueError("Skill manifest belongs to another project")
    source = safe_local_state_path(source_skills_dir, root=root)
    target = safe_local_state_path(target_skills_dir, root=root)
    if source.is_relative_to(target) or target.is_relative_to(source):
        raise ValueError("Skill migration requires distinct, non-overlapping directories")

    with skill_layout_lock(root):
        manifest_path = manifest._observe_manifest()
        revision = manifest._observed_revision
        with _locked_manifest_revision(manifest_path, root, manifest.key, revision):
            if manifest.skill_layout == layout:
                return []
            old_bytes = read_local_state_bytes(manifest_path, root=root)
            if sha256(old_bytes).hexdigest() != revision:
                raise ManifestConflictError("Skill manifest changed before migration")
            assets = _migration_files(
                root, manifest, source, target, flat_project_skills=flat_project_skills,
            )
            if not assets:
                raise ValueError("No manifest-owned skills found in the source layout")
            return _move_files_and_save(root, manifest, assets, layout, old_bytes)


def _move_files_and_save(
    root: Path,
    manifest: IntegrationManifest,
    assets: list[_SkillFile],
    layout: str,
    old_bytes: bytes,
) -> list[Path]:
    old_files = manifest.files
    old_layout = manifest.skill_layout
    old_revision = manifest._observed_revision
    old_installed_at = manifest._installed_at
    candidate = None
    created: list[Path] = []
    published: dict[Path, os.stat_result] = {}
    removed: list[_SkillFile] = []
    try:
        for asset in assets:
            _publish_new_file(asset.target, asset, root, created, published)
        for asset in assets:
            _check_unchanged(asset.target, root, published[asset.target], asset.digest)
            source = _check_unchanged(asset.source, root, asset.metadata, asset.digest)
            removed.append(asset)
            source.unlink()
            del manifest._files[asset.record]
            manifest._files[asset.target.relative_to(root).as_posix()] = asset.digest
        manifest.skill_layout = layout
        content, installed_at, candidate = manifest._prepare_save(manifest.manifest_path)
        if _manifest_revision(manifest.manifest_path, root) != old_revision:
            raise ManifestConflictError("Skill manifest changed during migration")
        manifest._save_locked(manifest.manifest_path, content, installed_at, candidate)
    except BaseException as error:
        _rollback(
            root, manifest, assets, removed, published, created, old_bytes, candidate, error,
        )
        manifest._files = old_files
        manifest.skill_layout = old_layout
        manifest._observed_revision = old_revision
        manifest._installed_at = old_installed_at
        manifest._published_revision = None
        raise

    parents = {asset.source.parent for asset in assets}
    for directory in sorted(parents, key=lambda path: len(path.parts), reverse=True):
        _remove_empty(directory, root)
    return list(published)


def _rollback(
    root: Path,
    manifest: IntegrationManifest,
    assets: list[_SkillFile],
    removed: list[_SkillFile],
    published: dict[Path, os.stat_result],
    created: list[Path],
    old_bytes: bytes,
    candidate: str | None,
    error: BaseException,
) -> None:
    for asset in removed:
        try:
            _check_unchanged(asset.source, root, asset.metadata, asset.digest)
        except FileNotFoundError:
            try:
                _publish_new_file(asset.source, asset, root, [], {})
            except (OSError, ValueError) as exc:
                error.add_note(f"Could not restore skill {asset.source.relative_to(root)}: {exc}")
                published.pop(asset.target, None)
        except (OSError, ValueError) as exc:
            error.add_note(f"Could not restore skill {asset.source.relative_to(root)}: {exc}")
            # Keep the corresponding target as the remaining recovery copy.
            published.pop(asset.target, None)
    for asset in reversed(assets):
        if asset.target in published:
            try:
                _check_unchanged(
                    asset.target, root, published[asset.target], asset.digest, require_unlinked=False,
                ).unlink()
            except FileNotFoundError:
                pass
            except (OSError, ValueError) as exc:
                error.add_note(f"Could not remove new skill {asset.target.relative_to(root)}: {exc}")
    for directory in reversed(created):
        _remove_empty(directory, root)
    if candidate is not None:
        try:
            current = _manifest_revision(manifest.manifest_path, root)
            if current == candidate:
                atomic_write_bytes(manifest.manifest_path, old_bytes)
            elif current != manifest._observed_revision:
                error.add_note("The skill manifest was changed externally and was preserved")
        except (OSError, ValueError) as exc:
            error.add_note(f"Could not restore the skill manifest: {exc}")
