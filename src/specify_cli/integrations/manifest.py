"""Hash-tracked installation manifest for integrations.

Each installed integration records the files it created together with
their SHA-256 hashes.  On uninstall only files whose hash still matches
the recorded value are removed — modified files are left in place and
reported to the caller.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
import codecs
import errno
import hashlib
import json
import os
import stat
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..atomic_io import (
    _open_regular_state_file,
    atomic_write_bytes,
    atomic_write_text,
    interprocess_lock,
    read_local_state_bytes,
    safe_local_state_path,
)

_TRANSIENT_FILE_ACCESS_ERRNOS = frozenset(
    {errno.EACCES, errno.EBUSY, errno.EINVAL, errno.EPERM}
)
_TRANSIENT_FILE_ACCESS_WINERRORS = frozenset({32, 33})
_FILE_WRITE_RETRY_DELAYS_SECONDS = (0.05, 0.1, 0.2, 0.4)


def _write_bytes_with_retry(path: Path, content: bytes) -> None:
    """Publish an independent file, with bounded retries for watcher conflicts.

    Revalidate on every attempt through the atomic writer. New files retain
    normal creation permissions (0666 filtered by umask); existing modes survive.
    A late sync error may follow replacement, so retries do not imply rollback.
    """

    for attempt in range(len(_FILE_WRITE_RETRY_DELAYS_SECONDS) + 1):
        try:
            atomic_write_bytes(path, content, new_file_mode=0o666)
            return
        except OSError as exc:
            transient = (
                exc.errno in _TRANSIENT_FILE_ACCESS_ERRNOS
                or getattr(exc, "winerror", None)
                in _TRANSIENT_FILE_ACCESS_WINERRORS
            )
            if not transient or attempt == len(_FILE_WRITE_RETRY_DELAYS_SECONDS):
                raise
            time.sleep(_FILE_WRITE_RETRY_DELAYS_SECONDS[attempt])


def _hash_regular_file(path: Path) -> str:
    """Hash one safely opened regular file in bounded chunks, rejecting changes."""

    target = safe_local_state_path(path)
    h = hashlib.sha256()
    with _open_regular_state_file(target) as fh:
        before = os.fstat(fh.fileno())
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
        safe_local_state_path(target)
        opened, current = os.fstat(fh.fileno()), target.lstat()
        for observed in (opened, current):
            if not os.path.samestat(before, observed) or (
                before.st_mode, before.st_size, before.st_mtime_ns, before.st_ctime_ns
            ) != (
                observed.st_mode, observed.st_size, observed.st_mtime_ns, observed.st_ctime_ns
            ):
                raise ValueError(f"Manifest file changed while hashing: {target}")
    return h.hexdigest()


def _sha256(path: Path) -> str:
    """Hash an existing asset through the common bounded file reader."""

    return _hash_regular_file(path)


def _matches_recorded_hash(path: Path, expected_hash: str) -> bool:
    """Compare digests with bounded buffers, retaining legacy EOL tolerance.

    Exact matches (including arbitrary binary files) need only one raw pass.
    Only a mismatch containing CR/LF needs a second, UTF-8-validated pass over
    the same descriptor. A CR at a chunk edge is held until the next chunk;
    partial Unicode sequences are validated by the incremental decoder.

    Recheck observed identity/metadata after reading and compare raw digests
    across passes. These checks are not an atomic snapshot or compare-and-delete.
    """

    target = safe_local_state_path(path)
    with _open_regular_state_file(target) as handle:
        before = os.fstat(handle.fileno())

        def ensure_unchanged() -> None:
            safe_local_state_path(target)
            for observed in (os.fstat(handle.fileno()), target.lstat()):
                if not os.path.samestat(before, observed) or (
                    before.st_mode, before.st_size, before.st_mtime_ns, before.st_ctime_ns
                ) != (
                    observed.st_mode, observed.st_size,
                    observed.st_mtime_ns, observed.st_ctime_ns
                ):
                    raise ValueError(f"Manifest file changed while hashing: {target}")

        raw_hash = hashlib.sha256()
        has_eol = False
        for chunk in iter(lambda: handle.read(65536), b""):
            raw_hash.update(chunk)
            has_eol = has_eol or b"\r" in chunk or b"\n" in chunk
        original_digest = raw_hash.hexdigest()
        ensure_unchanged()
        if original_digest == expected_hash:
            return True
        if not has_eol:
            return False

        # Rewind the checked descriptor, not the pathname. Keep only bounded
        # chunks and digest state rather than full Unicode and EOL variants.
        handle.seek(0)
        decoder = codecs.getincrementaldecoder("utf-8")(errors="strict")
        replay_hash = hashlib.sha256()
        lf_hash, crlf_hash = hashlib.sha256(), hashlib.sha256()
        pending_cr = False
        try:
            for chunk in iter(lambda: handle.read(65536), b""):
                replay_hash.update(chunk)
                decoder.decode(chunk, final=False)
                if pending_cr:
                    chunk = b"\r" + chunk
                pending_cr = chunk.endswith(b"\r")
                if pending_cr:
                    chunk = chunk[:-1]
                logical = chunk.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
                lf_hash.update(logical)
                crlf_hash.update(logical.replace(b"\n", b"\r\n"))
            # A truncated trailing multibyte sequence must not pass the fallback.
            decoder.decode(b"", final=True)
        except UnicodeDecodeError:
            return False
        if pending_cr:
            lf_hash.update(b"\n")
            crlf_hash.update(b"\r\n")
        ensure_unchanged()
        if replay_hash.hexdigest() != original_digest:
            raise ValueError(f"Manifest file changed between hash passes: {target}")
        return expected_hash in (lf_hash.hexdigest(), crlf_hash.hexdigest())


def _is_link_or_junction(path: Path) -> bool:
    """Return whether *path* is a link-like redirect without following it."""

    if path.is_symlink():
        return True
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return False
    except OSError:
        return True
    if stat.S_ISLNK(metadata.st_mode):
        return True
    is_junction = getattr(path, "is_junction", None)
    if callable(is_junction) and bool(is_junction()):
        return True
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return bool(getattr(metadata, "st_file_attributes", 0) & reparse_flag)


def _validate_rel_path(rel: Path, root: Path) -> Path:
    """Validate a lexical file record before resolving away redirects or ``..``.

    Even traversal that would end inside the project is not a canonical record.
    The shared owner checks all existing components without following links.
    """
    if rel.is_absolute() or rel.drive:
        raise ValueError(f"Absolute paths are not allowed in manifests: {rel}")
    if rel == Path(".") or ".." in rel.parts or "\0" in str(rel):
        raise ValueError(f"Unsafe manifest path (empty or outside traversal): {rel}")
    return safe_local_state_path(root / rel, root=root)


def _is_manifest_control_path(path: Path, root: Path) -> bool:
    """Recognize reserved metadata/coordination paths for every integration.

    Asset records never confer ownership of another manifest or live lock.
    Match the existing control-file layout, not an agent allowlist, so dotted
    profile keys and future integrations receive the same protection. Ordinary
    similarly named assets outside these exact directories remain supported.
    """

    parts = path.relative_to(root).parts
    if len(parts) != 3:
        return False
    # Reserve case variants on every host; spelling alone must not turn
    # metadata into an ordinary asset. No path is resolved or followed here.
    directory = tuple(part.casefold() for part in parts[:2])
    name = parts[2].casefold()
    if directory == (".specify", "integrations"):
        return name.endswith(".manifest.json")
    if directory == (".specify", "runtime"):
        return name == "launcher-config.lock" or (
            name.startswith("manifest-") and name.endswith(".lock")
        )
    return False


def _other_manifest_assets(root: Path, own_manifest: Path) -> set[str]:
    """Read peer ownership once before cleanup; unreadable peers stop deletion.

    Only the validated ``files`` mapping confers ownership. A peer's claim is
    retained even when its recorded digest differs: ``force`` on one integration
    does not authorize removing another integration's asset. No persistent index
    or schema is introduced. Revalidate each parsed revision and the discovered
    peer set before returning ownership, so a change noticed during the scan
    cannot authorize the first deletion. This is not an atomic snapshot or a
    lock against later installs, peer saves or external edits.
    """

    directory = safe_local_state_path(
        root / ".specify" / "integrations", root=root,
    )
    try:
        directory.lstat()
    except FileNotFoundError:
        return set()
    assets: set[str] = set()
    suffix = ".manifest.json"
    own_name = os.path.normcase(os.fspath(own_manifest))

    def peer_paths() -> list[Path]:
        # Recheck the directory itself before each enumeration. Ignore ordinary
        # notes, but do not lose a newly published or removed peer manifest.
        safe_local_state_path(directory, root=root)
        return sorted(
            (path for path in directory.iterdir()
             if path.name.casefold().endswith(suffix)
             and os.path.normcase(os.fspath(path)) != own_name),
            key=lambda item: item.name,
        )

    peers = peer_paths()
    revisions: list[tuple[Path, str | None]] = []
    for path in peers:
        # Loading owns JSON, field, link and regular-file validation. Do not
        # silently ignore a malformed/disappearing peer and infer sole ownership.
        safe_local_state_path(path, root=root)
        key = path.name[:-len(suffix)]
        peer = IntegrationManifest.load(key, root)
        if os.path.normcase(os.fspath(peer.manifest_path)) != os.path.normcase(os.fspath(path)):
            raise ValueError("Noncanonical peer manifest name; inspect before cleanup")
        # load() binds this digest to the exact bytes parsed, not a later read.
        revisions.append((path, peer._observed_revision))
        for relative in peer.files:
            rel = Path(relative)
            if (
                rel.is_absolute() or rel.drive or rel == Path(".")
                or ".." in rel.parts or "\0" in relative
            ):
                continue
            assets.add(os.path.normcase(os.fspath(root / rel)))

    # Validate only after every peer has been parsed: an earlier peer can change
    # while a later one is read. The shared hash reader uses bounded buffers.
    # Both callers finish this scan before any asset or metadata removal.
    for path, expected in revisions:
        if _manifest_revision(path, root) != expected:
            raise ValueError("Peer manifest changed during ownership scan; retry cleanup")
    if peer_paths() != peers:
        raise ValueError("Peer manifest set changed during ownership scan; retry cleanup")
    return assets


def _prune_empty_parents(path: Path, root: Path) -> None:
    """Prune only lexical project parents, never through a redirected directory."""

    parent = path.parent
    while parent != root:
        try:
            safe_local_state_path(parent, root=root)
            parent.rmdir()
        except (OSError, ValueError):
            break
        parent = parent.parent


def _unlink_manifest_file(
    path: Path, root: Path, expected_hash: str | None, *, force: bool = False,
) -> bool:
    """Unlink the observed file, preserving redirects and changed observations.

    Only force may unlink a final symlink itself; it never authorizes a linked
    parent or other reparse point. A missing path raises FileNotFoundError so
    callers retain their existing missing-entry semantics. These rechecks are
    not a hostile-writer sandbox or an atomic compare-and-delete operation.
    """

    safe_local_state_path(path.parent, root=root)
    before = path.lstat()
    if _is_link_or_junction(path):
        if not (force and stat.S_ISLNK(before.st_mode)):
            return False
    elif not stat.S_ISREG(before.st_mode):
        return False
    elif not force and expected_hash is not None:
        if not _matches_recorded_hash(path, expected_hash):
            return False

    # Hashing can take time. Refuse an observed replacement or in-place edit,
    # and inspect the parent again before any destructive operation.
    safe_local_state_path(path.parent, root=root)
    current = path.lstat()
    if not os.path.samestat(before, current) or (
        before.st_mode, before.st_size, before.st_mtime_ns, before.st_ctime_ns
    ) != (
        current.st_mode, current.st_size, current.st_mtime_ns, current.st_ctime_ns
    ):
        return False
    path.unlink()
    _prune_empty_parents(path, root)
    return True


def _validate_manifest_data(data: Any, path: Path) -> dict[str, str]:
    """Validate before publication; legacy omitted metadata remains supported."""

    if not isinstance(data, dict):
        raise ValueError(
            f"Integration manifest at {path} must be a JSON object, "
            f"got {type(data).__name__}"
        )
    files = data.get("files", {})
    if not isinstance(files, dict) or not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in files.items()
    ):
        raise ValueError(
            f"Integration manifest 'files' at {path} must be a "
            "mapping of string paths to string hashes"
        )
    for field in ("integration", "version", "installed_at"):
        if not isinstance(data.get(field, ""), str):
            raise ValueError(f"Integration manifest '{field}' at {path} must be a string")
    try:
        # Validate all JSON values, including extensions, without rounding
        # integers or accepting non-finite numbers and surrogate escapes.
        json.dumps(data, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, RecursionError) as exc:
        raise ValueError(f"Integration manifest at {path} contains invalid JSON values") from exc
    return files


class ManifestConflictError(RuntimeError):
    """The observed manifest changed; reload before saving or cleaning assets."""


def _manifest_revision(path: Path, root: Path) -> str | None:
    """Identify exact metadata bytes without allocating another full JSON copy.

    Only an initially missing path is an absent revision. Reuse the asset hash
    reader's descriptor and post-read identity checks; disappearance after the
    initial observation is an incomplete read, never permission to recreate state.
    JSON parsing still belongs to load(), and revisions never normalize EOLs.
    """

    target = safe_local_state_path(path, root=root)
    try:
        target.lstat()
    except FileNotFoundError:
        return None
    try:
        return _hash_regular_file(target)
    except FileNotFoundError as exc:
        raise ValueError(f"Integration manifest changed while reading: {target}") from exc


@contextmanager
def _locked_manifest_revision(
    path: Path, root: Path, key: str, expected_revision: str | None,
) -> Iterator[Path]:
    """Serialize cooperating saves and cleanup against one observation.

    Keep the lock inode after release. record_file also participates; direct
    asset writers and external editors do not follow this manifest-level protocol.
    """

    lock = safe_local_state_path(
        root / ".specify" / "runtime" / f"manifest-{key}.lock", root=root,
    )
    with interprocess_lock(lock):
        if _manifest_revision(path, root) != expected_revision:
            raise ManifestConflictError(
                "Integration manifest changed since it was observed; reload "
                "the latest manifest and reconcile pending changes before continuing. "
                "Previously written assets have not been rolled back."
            )
        yield lock


class IntegrationManifest:
    """Tracks files installed by a single integration.

    Parameters:
        key:          Integration identifier (e.g. ``"copilot"``).
        project_root: Absolute path to the project directory.
        version:      CLI version string recorded in the manifest.
    """

    def __init__(self, key: str, project_root: Path, version: str = "") -> None:
        self.key = key
        self.project_root = project_root.resolve()
        self.version = version
        self._files: dict[str, str] = {}  # rel_path → sha256 hex
        self._installed_at: str = ""
        # Unknown top-level JSON fields are opaque metadata, not asset authority.
        self._extra_metadata: dict[str, Any] = {}
        # Construction stays side-effect free. Loading or the first record/save
        # binds the exact manifest revision used by this in-memory operation.
        self._observed_path: Path | None = None
        self._observed_revision: str | None = None
        # A load proves visible bytes, not that this instance completed a durable
        # publication. Its first save must still run the normal sync path.
        self._published_revision: str | None = None

    # -- Manifest file location -------------------------------------------

    @property
    def manifest_path(self) -> Path:
        """Path to the on-disk manifest JSON for a single integration key."""
        if (
            not isinstance(self.key, str) or not self.key or self.key in {".", ".."}
            or any(character in self.key for character in ("/", "\\", ":", "\0"))
        ):
            raise ValueError(f"Unsafe integration key: {self.key!r}")
        return self.project_root / ".specify" / "integrations" / f"{self.key}.manifest.json"

    def _observe_manifest(self) -> Path:
        """Capture once, before recording side effects; never adopt a newer revision."""

        path = safe_local_state_path(self.manifest_path, root=self.project_root)
        if self._observed_path is None:
            revision = _manifest_revision(path, self.project_root)
            self._observed_revision = revision
            self._observed_path = path
        elif self._observed_path != path:
            raise ManifestConflictError(
                "Manifest target changed after observation; create a new instance "
                "for a different integration or project."
            )
        return path

    # -- Recording files --------------------------------------------------

    def record_file(self, rel_path: str | Path, content: bytes | str) -> Path:
        """Publish one asset only while the observed manifest is current.

        Reject unsafe paths and content before creating state. Hold the existing
        per-project/key guard through publication, retries and the pending hash
        update so a stale writer cannot overwrite files before save reports a
        conflict. No integration manifest or coordination lock is an asset target.

        This does not save JSON or hold the guard through a later save. External
        edits and writers outside this API are not serialized, and a conflict
        detected after publication does not restore the previous asset bytes.
        """
        rel = Path(rel_path)
        abs_path = _validate_rel_path(rel, self.project_root)
        if isinstance(content, str):
            content = content.encode("utf-8")
        elif not isinstance(content, bytes):
            # Freeze mutable buffers before waiting/retrying so publication and
            # the pending hash always describe the same bytes.
            content = memoryview(content).tobytes()
        manifest = self.manifest_path
        if _is_manifest_control_path(abs_path, self.project_root):
            raise ValueError(f"Manifest control file cannot be written as an asset: {rel}")
        self._observe_manifest()
        with _locked_manifest_revision(
            manifest, self.project_root, self.key, self._observed_revision,
        ):
            _write_bytes_with_retry(abs_path, content)
            # Cooperating saves/cleanup are excluded. Do not adopt an external
            # metadata revision or certify a new record against an obsolete one.
            if _manifest_revision(manifest, self.project_root) != self._observed_revision:
                raise ManifestConflictError(
                    "Integration manifest changed during asset publication; reload "
                    "and inspect the installed file. Published bytes were not rolled back."
                )
            normalized = abs_path.relative_to(self.project_root).as_posix()
            self._files[normalized] = hashlib.sha256(content).hexdigest()
        return abs_path

    def record_existing(self, rel_path: str | Path) -> None:
        """Adopt an existing asset only against the observed manifest revision.

        Check before the potentially large file read and again before updating
        pending records. Hash/path/access errors or detected revision changes
        leave the previous record intact; no file, directory or lock is created.

        This read-only operation may run inside the installer's existing guard,
        so it does not acquire that non-reentrant OS lock itself. Observations
        are not an atomic snapshot, and this method does not save the manifest.
        """
        rel = Path(rel_path)
        abs_path = _validate_rel_path(rel, self.project_root)
        if _is_manifest_control_path(abs_path, self.project_root):
            raise ValueError(f"Manifest control file cannot be recorded as an asset: {rel}")
        normalized = abs_path.relative_to(self.project_root).as_posix()
        manifest = self._observe_manifest()
        if _manifest_revision(manifest, self.project_root) != self._observed_revision:
            raise ManifestConflictError(
                "Integration manifest changed since it was observed; reload "
                "and reconcile pending records before adopting an existing asset."
            )
        digest = _sha256(abs_path)
        self._observe_manifest()  # A changed project/key must not retarget adoption.
        if _manifest_revision(manifest, self.project_root) != self._observed_revision:
            raise ManifestConflictError(
                "Integration manifest changed during asset hashing; reload "
                "and inspect the existing file before adopting its digest."
            )
        self._files[normalized] = digest

    # -- Querying ---------------------------------------------------------

    @property
    def files(self) -> dict[str, str]:
        """Return a copy of the ``{rel_path: sha256}`` mapping."""
        return dict(self._files)

    def check_modified(self) -> list[str]:
        """Report changed or uninspectable tracked files; missing files stay absent."""
        modified: list[str] = []
        for rel, expected_hash in self._files.items():
            rel_path = Path(rel)
            if (
                rel_path.is_absolute() or rel_path.drive or rel_path == Path(".")
                or ".." in rel_path.parts or "\0" in rel
            ):
                continue
            abs_path = self.project_root / rel_path
            if _is_manifest_control_path(abs_path, self.project_root):
                # A historical control-file record is unsafe to treat as an
                # unmodified asset, even when its stored digest still matches.
                modified.append(rel)
                continue
            try:
                safe_local_state_path(abs_path, root=self.project_root)
                if not stat.S_ISREG(abs_path.lstat().st_mode):
                    modified.append(rel)
                elif not _matches_recorded_hash(abs_path, expected_hash):
                    modified.append(rel)
            except FileNotFoundError:
                continue
            except (OSError, ValueError):
                modified.append(rel)
        return modified

    def remove_file_if_unmodified(self, rel_path: str | Path) -> bool:
        """Remove one tracked asset only while the observed manifest is current.

        Share the save/uninstall guard through hashing, deletion and the pending
        record update. A stale observation raises ManifestConflictError rather
        than being mistaken for a modified-file skip. Unknown paths remain no-ops;
        missing assets are forgotten, while changed or unsafe assets stay tracked.

        Assets claimed by another saved manifest are preserved and remain tracked.
        Unreadable peer manifests stop cleanup rather than imply sole ownership.
        All integration manifests and coordination locks are control files, never
        single-file cleanup targets. This does not save JSON implicitly or hold the guard until a later
        save. An external edit detected after unlink cannot undo that unlink.
        """
        rel = Path(rel_path)
        if (
            rel.is_absolute() or rel.drive or rel == Path(".")
            or ".." in rel.parts or "\0" in str(rel)
        ):
            raise ValueError(f"Unsafe manifest path: {rel}")
        normalized = rel.as_posix()
        expected_hash = self._files.get(normalized)
        if expected_hash is None:
            return False
        manifest = self.manifest_path  # Validate the key before guard side effects.
        abs_path = self.project_root / rel
        try:
            self._observe_manifest()
            with _locked_manifest_revision(
                manifest, self.project_root, self.key, self._observed_revision,
            ):
                if _is_manifest_control_path(abs_path, self.project_root):
                    return False
                # Retain the original per-component redirect checks as well as
                # the shared reader's checks; perform them while holding the guard.
                component = self.project_root
                for part in rel.parts:
                    component /= part
                    if _is_link_or_junction(component):
                        return False
                shared = _other_manifest_assets(self.project_root, manifest)
                if os.path.normcase(os.fspath(abs_path)) in shared:
                    return False
                try:
                    deleted = _unlink_manifest_file(
                        abs_path, self.project_root, expected_hash,
                    )
                except FileNotFoundError:
                    deleted = True
                # Cooperating metadata operations are locked out. Do not adopt
                # an external editor's revision or discard a pending record if
                # the metadata changed during this operation.
                if _manifest_revision(manifest, self.project_root) != self._observed_revision:
                    raise ManifestConflictError(
                        "Integration manifest changed during single-file cleanup; reload "
                        "and inspect the remaining files. Earlier removals were not rolled back."
                    )
                if deleted:
                    self._files.pop(normalized, None)
                return deleted
        except (OSError, ValueError):
            return False

    # -- Uninstall --------------------------------------------------------

    def uninstall(
        self,
        project_root: Path | None = None,
        *,
        force: bool = False,
    ) -> tuple[list[Path], list[Path]]:
        """Remove tracked files only while the observed manifest is still current.

        A stale instance raises ManifestConflictError before deleting any assets,
        including with force=True. Saves and uninstalls use the same per-key lock;
        force permits modified files or a final symlink, never bypassing revision
        checks, parent-path checks or other integrations' control-file ownership.

        The explicit root override remains a one-call cleanup scope: its manifest
        revision is captured before waiting and does not retarget this instance.
        Assets claimed by other saved manifests are skipped even with force.
        If a peer cannot be inspected, preserve this manifest and its assets for
        retry. Peer ownership is read once, not locked against concurrent installs.
        A file inspection/deletion error keeps an existing manifest unchanged for
        a fresh-instance retry and reports its path as skipped. Expected skips
        (user edits or shared ownership) retain normal completed-uninstall behavior.
        Unsafe/unreadable state is returned as skipped. External edits during the
        operation can still leave partial asset cleanup; there is no rollback.
        """
        own_manifest = self.manifest_path  # Validate the key before side effects.
        root = Path(os.path.abspath(os.fspath(project_root or self.project_root)))
        manifest = root / own_manifest.relative_to(self.project_root)
        if self._observed_path is not None and self._observed_path != own_manifest:
            raise ManifestConflictError(
                "Manifest target changed after observation; create a new instance "
                "for a different integration or project."
            )
        removed: list[Path] = []
        skipped: list[Path] = []
        candidates: list[tuple[Path, str]] = []
        for rel, expected_hash in self._files.items():
            rel_path = Path(rel)
            if (
                rel_path.is_absolute() or rel_path.drive or rel_path == Path(".")
                or ".." in rel_path.parts or "\0" in rel
            ):
                continue
            candidates.append((root / rel_path, expected_hash))

        try:
            safe_local_state_path(manifest, root=root)
            if root == self.project_root:
                self._observe_manifest()
                expected_revision = self._observed_revision
            else:
                expected_revision = _manifest_revision(manifest, root)
            with _locked_manifest_revision(
                manifest, root, self.key, expected_revision,
            ):
                # Resolve every peer before removing the first asset. Unknown
                # ownership must not result in partially deleting this install.
                shared = _other_manifest_assets(root, manifest)
                asset_cleanup_failed = False
                for path, expected_hash in candidates:
                    if path != manifest and _is_manifest_control_path(path, root):
                        # Records cannot authorize deletion of another owner's
                        # metadata or lock. Keep live lock inodes intact even
                        # with force; our own metadata is handled only below.
                        skipped.append(path)
                        continue
                    if path == manifest:
                        # Metadata is cleaned once, under its exact revision,
                        # never by the tracked-file force/EOL-tolerance rules.
                        continue
                    if os.path.normcase(os.fspath(path)) in shared:
                        skipped.append(path)
                        continue
                    try:
                        deleted = _unlink_manifest_file(path, root, expected_hash, force=force)
                    except FileNotFoundError:
                        continue
                    except (OSError, ValueError):
                        # An I/O/inspection failure is not an intentional user
                        # modification skip. Keep saved ownership so a new
                        # process can reload and retry after the cause is fixed.
                        asset_cleanup_failed = True
                        deleted = False
                    (removed if deleted else skipped).append(path)

                # Cooperating saves are excluded by the lock. Also refuse an
                # observed external metadata change during asset hashing/deletion.
                if _manifest_revision(manifest, root) != expected_revision:
                    raise ManifestConflictError(
                        "Integration manifest changed during uninstall; reload and "
                        "inspect the remaining files. Earlier removals were not rolled back."
                    )
                if asset_cleanup_failed and expected_revision is not None:
                    # Do not rewrite metadata to drop already removed paths:
                    # missing assets are already tolerated on a later retry.
                    # Preserve exact bytes, extension fields, modes and revision.
                    skipped.append(manifest)
                    return removed, skipped
                try:
                    if not _unlink_manifest_file(manifest, root, None):
                        skipped.append(manifest)
                except FileNotFoundError:
                    pass
                except (OSError, ValueError):
                    skipped.append(manifest)
        except (OSError, ValueError):
            # Failed guard acquisition cannot authorize asset deletion. If an
            # I/O error occurred later, keep the removals already performed visible.
            for path, _ in candidates:
                if path not in removed and path not in skipped:
                    skipped.append(path)
            if manifest not in skipped:
                skipped.append(manifest)

        return removed, skipped

    # -- Persistence ------------------------------------------------------

    def save(self) -> Path:
        """Publish complete manifest JSON; update the timestamp only on success.

        Cooperating saves serialize their revision check and replacement. A stale
        instance raises ManifestConflictError without rewriting the latest JSON;
        callers must reload and deliberately reconcile, not retry blindly. Asset
        writes through record_file, whole uninstall and single-file cleanup use
        this lock. Direct asset writers and external editors do not participate.
        Repeated exact matches after this instance's successful publication are
        not rewritten after the locked revision check, preserving file identity
        and timestamps. A loaded instance still publishes once. Hardlinked metadata is
        still replaced independently. This is a metadata save, not an asset
        integrity check or an atomic snapshot against external editors.
        An error after replacement (such as directory fsync) does not roll it back.
        """
        path = safe_local_state_path(self.manifest_path, root=self.project_root)
        data: dict[str, Any] = {
            "integration": self.key,
            "version": self.version,
            "installed_at": self._installed_at,
            "files": self._files,
        }
        data.update(self._extra_metadata)
        _validate_manifest_data(data, path)
        installed_at = self._installed_at or datetime.now(timezone.utc).isoformat()
        data["installed_at"] = installed_at
        # Keep the existing escaped-ASCII JSON formatting for downstream readers.
        content = json.dumps(data, indent=2, allow_nan=False) + "\n"
        revision = hashlib.sha256(content.encode("utf-8")).hexdigest()
        self._observe_manifest()
        with _locked_manifest_revision(
            path, self.project_root, self.key, self._observed_revision,
        ):
            unchanged = False
            if revision == self._observed_revision == self._published_revision:
                metadata = path.lstat()
                # Do not retain a shared inode merely because its bytes match:
                # the existing publication contract detaches hardlinked backups.
                unchanged = stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1
            if unchanged:
                # Check again before certifying a no-op. An external edit noticed
                # here is a conflict, never a reason to overwrite newer content.
                if _manifest_revision(path, self.project_root) != revision:
                    raise ManifestConflictError(
                        "Integration manifest changed during unchanged save; "
                        "reload and reconcile before continuing."
                    )
            else:
                # Any publication attempt can replace the inode before reporting
                # an error (for example, a directory sync failure). An earlier
                # success for identical bytes cannot certify that new inode.
                # Invalidate before the attempt, including interrupted writes;
                # only a fully successful publication below restores the marker.
                self._published_revision = None
                # Match ordinary creation permissions and preserve existing modes.
                atomic_write_text(path, content, new_file_mode=0o666)
            self._installed_at = installed_at
            self._observed_revision = revision
            self._published_revision = revision
        return path

    @classmethod
    def load(cls, key: str, project_root: Path) -> IntegrationManifest:
        """Load regular, non-link manifest JSON without changing installed state.

        Unknown top-level fields round-trip as opaque metadata; only ``files``
        grants tracked-asset ownership. Known fields use this instance's values.
        Raises FileNotFoundError when absent and ValueError for unsafe paths or
        malformed/ambiguous JSON. Access errors propagate to the caller.
        """
        inst = cls(key, project_root)
        path = inst.manifest_path

        def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
            result: dict[str, Any] = {}
            for name, value in pairs:
                if name in result:
                    raise ValueError("duplicate manifest key")
                result[name] = value
            return result

        raw = read_local_state_bytes(path, root=inst.project_root)
        try:
            data = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object)
        except (ValueError, RecursionError) as exc:
            raise ValueError(
                f"Integration manifest at {path} contains invalid JSON"
            ) from exc

        files = _validate_manifest_data(data, path)
        stored_key = data.get("integration", "")
        if stored_key and stored_key != key:
            raise ValueError(
                f"Manifest at {path} belongs to integration {stored_key!r}, "
                f"not {key!r}"
            )

        inst.version = data.get("version", "")
        inst._installed_at = data.get("installed_at", "")
        inst._files = files
        inst._extra_metadata = {
            name: value for name, value in data.items()
            if name not in {"integration", "version", "installed_at", "files"}
        }
        # Bind to the bytes actually parsed, not a second read of a newer file.
        inst._observed_path = safe_local_state_path(path, root=inst.project_root)
        inst._observed_revision = hashlib.sha256(raw).hexdigest()
        return inst
