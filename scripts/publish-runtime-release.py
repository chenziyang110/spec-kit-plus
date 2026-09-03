#!/usr/bin/env python3
"""Publish public specify-runtime binary releases without exposing source history."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ALLOWED_BINARY_ASSETS = (
    "specify-runtime-linux-amd64",
    "specify-runtime-linux-arm64",
    "specify-runtime-darwin-amd64",
    "specify-runtime-darwin-arm64",
    "specify-runtime-windows-amd64.exe",
)
CHECKSUM_NAME = "SHA256SUMS"
PUBLIC_RELEASE_ASSETS = (*ALLOWED_BINARY_ASSETS, CHECKSUM_NAME)
MIN_BINARY_SIZE = 1024
GH_TIMEOUT_SECONDS = 60
# Uploading five cross-platform binaries can exceed one minute on ordinary
# residential or proxied connections. Keep that operation bounded separately
# so read/check/edit commands still fail quickly.
GH_UPLOAD_TIMEOUT_SECONDS = 600
TAG_RE = re.compile(r"^v[0-9]+(\.[0-9]+){2}([-.][0-9A-Za-z.-]+)?$")
REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
TOKEN_ENV_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")


class PublishRuntimeReleaseError(RuntimeError):
    """Raised when public runtime release publishing must fail closed."""


def release_identity_marker(tag: str, source_revision: str) -> str:
    return (
        "specify-runtime.release.v1,"
        f"version={tag},revision={source_revision},dirty=false"
    )


def validate_tag(tag: str) -> str:
    if not TAG_RE.fullmatch(tag):
        raise PublishRuntimeReleaseError(f"Invalid release tag: {tag}")
    return tag


def validate_source_revision(source_revision: str) -> str:
    normalized = source_revision.strip().lower()
    if not REVISION_RE.fullmatch(normalized):
        raise PublishRuntimeReleaseError(
            "Source revision must be a 40-character lowercase hex commit id"
        )
    return normalized


def validate_target_repo(target_repo: str) -> str:
    normalized = target_repo.strip()
    if not REPO_RE.fullmatch(normalized):
        raise PublishRuntimeReleaseError(
            f"Target repository must look like owner/name: {target_repo}"
        )
    return normalized


def validate_token_env(token_env: str) -> str:
    normalized = token_env.strip()
    if not TOKEN_ENV_RE.fullmatch(normalized):
        raise PublishRuntimeReleaseError(
            f"Token env name must be an all-caps shell identifier: {token_env}"
        )
    return normalized


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_runtime_binary(path: Path, tag: str, source_revision: str) -> None:
    if path.is_symlink():
        raise PublishRuntimeReleaseError(f"Runtime asset must not be a symlink: {path.name}")
    if not path.is_file():
        raise PublishRuntimeReleaseError(f"Missing runtime asset: {path.name}")
    if path.stat().st_size < MIN_BINARY_SIZE:
        raise PublishRuntimeReleaseError(
            f"Runtime asset is too small to be trusted: {path.name}"
        )
    raw = path.read_bytes()
    marker = release_identity_marker(tag, source_revision).encode("utf-8")
    if marker not in raw:
        raise PublishRuntimeReleaseError(
            f"Runtime asset identity mismatch for {path.name}; "
            "refusing to publish a different source revision under the same tag"
        )
    if b"specify-runtime.v1" not in raw:
        raise PublishRuntimeReleaseError(
            f"Runtime asset protocol marker missing: {path.name}"
        )


def write_sha256sums(assets_dir: Path, binaries: list[Path]) -> Path:
    checksum_path = assets_dir / CHECKSUM_NAME
    lines = [f"{sha256_file(path)}  {path.name}\n" for path in binaries]
    checksum_path.write_text("".join(lines), encoding="utf-8")
    return checksum_path


def verify_checksums(assets_dir: Path) -> None:
    checksum_path = assets_dir / CHECKSUM_NAME
    if checksum_path.is_symlink():
        raise PublishRuntimeReleaseError("Checksum asset must not be a symlink")
    try:
        lines = checksum_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise PublishRuntimeReleaseError("Unable to read SHA256SUMS") from exc
    expected_names: list[str] = []
    for line in lines:
        digest, separator, name = line.partition("  ")
        if (
            separator != "  "
            or name not in ALLOWED_BINARY_ASSETS
            or len(digest) != 64
            or any(ch not in "0123456789abcdef" for ch in digest)
        ):
            raise PublishRuntimeReleaseError("SHA256SUMS has an invalid line format")
        expected_names.append(name)
        if sha256_file(assets_dir / name) != digest:
            raise PublishRuntimeReleaseError(
                f"SHA256SUMS does not match the runtime asset: {name}"
            )
    if expected_names != list(ALLOWED_BINARY_ASSETS):
        raise PublishRuntimeReleaseError(
            "SHA256SUMS must contain exactly the five allowed runtime binaries"
        )


def prepare_local_release_assets(
    assets_dir: Path,
    tag: str,
    source_revision: str,
) -> list[Path]:
    assets_dir = assets_dir.resolve()
    entries = {path.name: path for path in assets_dir.iterdir()}
    allowed_now = set(ALLOWED_BINARY_ASSETS) | {CHECKSUM_NAME}
    extras = sorted(name for name in entries if name not in allowed_now)
    if extras:
        raise PublishRuntimeReleaseError(
            f"Unexpected asset in publish directory: {', '.join(extras)}"
        )
    missing = [name for name in ALLOWED_BINARY_ASSETS if name not in entries]
    if missing:
        raise PublishRuntimeReleaseError(
            f"Missing runtime binaries: {', '.join(missing)}"
        )
    checksum_entry = entries.get(CHECKSUM_NAME)
    if checksum_entry is not None and checksum_entry.is_symlink():
        raise PublishRuntimeReleaseError("Checksum asset must not be a symlink")
    binaries = [entries[name] for name in ALLOWED_BINARY_ASSETS]
    for path in binaries:
        verify_runtime_binary(path, tag, source_revision)
    checksum_path = write_sha256sums(assets_dir, binaries)
    verify_checksums(assets_dir)
    return binaries + [checksum_path]


def public_release_notes(tag: str, source_revision: str) -> str:
    return (
        f"Prebuilt `specify-runtime` binaries for `{tag}`.\n\n"
        "This public release intentionally contains only the five supported "
        f"platform binaries and `{CHECKSUM_NAME}`.\n"
    )


def token_from_env(token_env: str) -> str:
    token_env = validate_token_env(token_env)
    token = os.environ.get(token_env, "").strip()
    if not token:
        raise PublishRuntimeReleaseError(
            f"Missing required publishing credential in {token_env}"
        )
    return token


def run_gh(
    args: list[str],
    *,
    token: str,
    capture_output: bool = True,
    check: bool = True,
) -> str:
    env = dict(os.environ)
    env["GH_TOKEN"] = token
    env["GITHUB_TOKEN"] = ""
    env["GH_DEBUG"] = ""
    timeout = (
        GH_UPLOAD_TIMEOUT_SECONDS
        if args[:2] == ["release", "upload"]
        else GH_TIMEOUT_SECONDS
    )
    result = subprocess.run(
        ["gh", *args],
        env=env,
        capture_output=capture_output,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=timeout,
    )
    if check and result.returncode != 0:
        raise PublishRuntimeReleaseError(
            f"gh {' '.join(args[:3])} failed with exit {result.returncode}"
        )
    return result.stdout


def gh_release_view(target_repo: str, tag: str, token: str) -> dict[str, Any] | None:
    result = subprocess.run(
        ["gh", "release", "view", tag, "--repo", target_repo, "--json", "isDraft,assets"],
        env={**os.environ, "GH_TOKEN": token, "GITHUB_TOKEN": "", "GH_DEBUG": ""},
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=GH_TIMEOUT_SECONDS,
    )
    if result.returncode != 0:
        stderr = (result.stderr or "").lower()
        stdout = (result.stdout or "").lower()
        combined = f"{stdout}\n{stderr}"
        if "not found" in combined:
            return None
        raise PublishRuntimeReleaseError(
            f"gh release view could not read {target_repo}@{tag} "
            f"(exit {result.returncode})"
        )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise PublishRuntimeReleaseError("gh release view returned invalid JSON") from exc
    if not isinstance(payload, dict):
        raise PublishRuntimeReleaseError("gh release view returned invalid release metadata")
    return payload


def gh_release_download(target_repo: str, tag: str, destination: Path, token: str) -> None:
    gh_release_download_selected(
        target_repo,
        tag,
        destination,
        token,
        list(PUBLIC_RELEASE_ASSETS),
    )


def gh_release_download_selected(
    target_repo: str,
    tag: str,
    destination: Path,
    token: str,
    asset_names: list[str],
) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for asset in asset_names:
        run_gh(
            [
                "release",
                "download",
                tag,
                "--repo",
                target_repo,
                "--pattern",
                asset,
                "--dir",
                str(destination),
                "--clobber",
            ],
            token=token,
        )


def verify_downloaded_release_assets(
    assets_dir: Path,
    tag: str,
    source_revision: str,
) -> None:
    entries = sorted(path.name for path in assets_dir.iterdir())
    if entries != sorted(PUBLIC_RELEASE_ASSETS):
        raise PublishRuntimeReleaseError("Downloaded release assets do not match the public allowlist")
    for name in ALLOWED_BINARY_ASSETS:
        verify_runtime_binary(assets_dir / name, tag, source_revision)
    verify_checksums(assets_dir)


def verify_downloaded_release_subset(
    assets_dir: Path,
    tag: str,
    source_revision: str,
    asset_names: list[str],
) -> None:
    seen = sorted(path.name for path in assets_dir.iterdir())
    if seen != sorted(asset_names):
        raise PublishRuntimeReleaseError(
            "Downloaded subset assets do not match the requested remote asset set"
        )
    for name in asset_names:
        path = assets_dir / name
        if name == CHECKSUM_NAME:
            if path.is_symlink():
                raise PublishRuntimeReleaseError("Checksum asset must not be a symlink")
            continue
        verify_runtime_binary(path, tag, source_revision)


def check_public_release(
    *,
    target_repo: str,
    tag: str,
    source_revision: str,
    token: str,
) -> dict[str, Any]:
    target_repo = validate_target_repo(target_repo)
    tag = validate_tag(tag)
    source_revision = validate_source_revision(source_revision)
    payload = gh_release_view(target_repo, tag, token)
    if payload is None:
        return {
            "exists": False,
            "is_draft": False,
            "complete": False,
            "reason": "missing_release",
        }
    assets = payload.get("assets")
    if not isinstance(assets, list):
        raise PublishRuntimeReleaseError("Public release metadata is invalid")
    remote_names = sorted(
        asset.get("name")
        for asset in assets
        if isinstance(asset, dict) and isinstance(asset.get("name"), str)
    )
    allowed = set(PUBLIC_RELEASE_ASSETS)
    extras = [name for name in remote_names if name not in allowed]
    if extras:
        return {
            "exists": True,
            "is_draft": bool(payload.get("isDraft")),
            "complete": False,
            "reason": "unexpected_remote_assets",
            "extras": extras,
        }
    missing = [name for name in PUBLIC_RELEASE_ASSETS if name not in remote_names]
    for asset in assets:
        if not isinstance(asset, dict) or int(asset.get("size", 0)) <= 0:
            return {
                "exists": True,
                "is_draft": bool(payload.get("isDraft")),
                "complete": False,
                "reason": "empty_remote_asset",
            }
    if missing:
        with tempfile.TemporaryDirectory(prefix="public-runtime-release-") as tmp:
            download_dir = Path(tmp)
            present_assets = [name for name in PUBLIC_RELEASE_ASSETS if name in remote_names]
            gh_release_download_selected(
                target_repo,
                tag,
                download_dir,
                token,
                present_assets,
            )
            try:
                verify_downloaded_release_subset(
                    download_dir,
                    tag,
                    source_revision,
                    present_assets,
                )
            except PublishRuntimeReleaseError as exc:
                reason = "invalid_remote_release"
                if "different source revision" in str(exc) or "identity mismatch" in str(exc):
                    reason = "source_revision_mismatch"
                return {
                    "exists": True,
                    "is_draft": bool(payload.get("isDraft")),
                    "complete": False,
                    "reason": reason,
                    "detail": str(exc),
                }
        return {
            "exists": True,
            "is_draft": bool(payload.get("isDraft")),
            "complete": False,
            "reason": "repairable_partial_release",
            "missing": missing,
        }
    with tempfile.TemporaryDirectory(prefix="public-runtime-release-") as tmp:
        download_dir = Path(tmp)
        gh_release_download(target_repo, tag, download_dir, token)
        try:
            verify_downloaded_release_assets(download_dir, tag, source_revision)
        except PublishRuntimeReleaseError as exc:
            reason = "invalid_remote_release"
            if "different source revision" in str(exc) or "identity mismatch" in str(exc):
                reason = "source_revision_mismatch"
            return {
                "exists": True,
                "is_draft": bool(payload.get("isDraft")),
                "complete": False,
                "reason": reason,
                "detail": str(exc),
            }
    is_draft = bool(payload.get("isDraft"))
    return {
        "exists": True,
        "is_draft": is_draft,
        "complete": not is_draft,
        "reason": "draft_release" if is_draft else "complete",
    }


def ensure_public_release(
    *,
    target_repo: str,
    tag: str,
    source_revision: str,
    assets_dir: Path,
    token: str,
) -> dict[str, Any]:
    target_repo = validate_target_repo(target_repo)
    tag = validate_tag(tag)
    source_revision = validate_source_revision(source_revision)
    local_assets = prepare_local_release_assets(assets_dir, tag, source_revision)
    current = check_public_release(
        target_repo=target_repo,
        tag=tag,
        source_revision=source_revision,
        token=token,
    )
    if current["complete"]:
        return {"published": True, "state": "already-complete"}
    if current["reason"] == "unexpected_remote_assets":
        raise PublishRuntimeReleaseError(
            "Existing public release contains extra assets; refusing to publish more files"
        )
    if current["reason"] == "source_revision_mismatch":
        raise PublishRuntimeReleaseError(
            "Existing public release points to a different source revision; refusing to clobber it"
        )
    if current["reason"] in {"invalid_remote_release", "empty_remote_asset"}:
        raise PublishRuntimeReleaseError(
            f"Existing public release is not safe to repair: {current['reason']}"
        )
    notes = public_release_notes(tag, source_revision)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", delete=False, prefix="public-runtime-notes-", suffix=".md"
    ) as handle:
        handle.write(notes)
        notes_path = Path(handle.name)
    try:
        if current["exists"]:
            run_gh(
                [
                    "release",
                    "edit",
                    tag,
                    "--repo",
                    target_repo,
                    "--title",
                    f"specify-runtime {tag}",
                    "--notes-file",
                    str(notes_path),
                ],
                token=token,
            )
        else:
            run_gh(
                [
                    "release",
                    "create",
                    tag,
                    "--repo",
                    target_repo,
                    "--draft",
                    "--title",
                    f"specify-runtime {tag}",
                    "--notes-file",
                    str(notes_path),
                ],
                token=token,
            )
        run_gh(
            [
                "release",
                "upload",
                tag,
                "--repo",
                target_repo,
                *(str(path) for path in local_assets),
                "--clobber",
            ],
            token=token,
        )
        checked = check_public_release(
            target_repo=target_repo,
            tag=tag,
            source_revision=source_revision,
            token=token,
        )
        if checked["reason"] not in {"complete", "draft_release"}:
            raise PublishRuntimeReleaseError(
                f"Public release verification failed after upload: {checked['reason']}"
            )
        if checked["is_draft"]:
            run_gh(
                [
                    "release",
                    "edit",
                    tag,
                    "--repo",
                    target_repo,
                    "--draft=false",
                ],
                token=token,
            )
    finally:
        notes_path.unlink(missing_ok=True)
    return {"published": True, "state": "published"}


def write_github_output(path: str | None, values: dict[str, Any]) -> None:
    if not path:
        return
    output_path = Path(path)
    with output_path.open("a", encoding="utf-8") as handle:
        for key, value in values.items():
            if isinstance(value, bool):
                rendered = "true" if value else "false"
            else:
                rendered = str(value)
            handle.write(f"{key}={rendered}\n")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-repo", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--assets-dir", required=True)
    parser.add_argument("--token-env", required=True)
    parser.add_argument("--mode", choices=("check", "ensure-release"), required=True)
    parser.add_argument("--github-output")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        target_repo = validate_target_repo(args.target_repo)
        tag = validate_tag(args.tag)
        source_revision = validate_source_revision(args.source_revision)
        token_env = validate_token_env(args.token_env)
        token = token_from_env(token_env)
        assets_dir = Path(args.assets_dir)
        if args.mode == "check":
            result = check_public_release(
                target_repo=target_repo,
                tag=tag,
                source_revision=source_revision,
                token=token,
            )
            write_github_output(
                args.github_output,
                {"complete": result["complete"], "reason": result["reason"]},
            )
            print(json.dumps(result, sort_keys=True))
            return 0
        result = ensure_public_release(
            target_repo=target_repo,
            tag=tag,
            source_revision=source_revision,
            assets_dir=assets_dir,
            token=token,
        )
        write_github_output(args.github_output, result)
        print(json.dumps(result, sort_keys=True))
        return 0
    except PublishRuntimeReleaseError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
