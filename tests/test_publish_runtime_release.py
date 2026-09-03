import hashlib
import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "publish-runtime-release.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("publish_runtime_release", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_runtime(path: Path, marker: str) -> None:
    payload = (b"x" * 2048) + b"\x00" + marker.encode("utf-8") + b"\x00specify-runtime.v1\x00"
    path.write_bytes(payload)


def test_release_helper_allows_a_bounded_full_asset_upload_window() -> None:
    module = _load_module()

    assert module.GH_TIMEOUT_SECONDS == 60
    assert 300 <= module.GH_UPLOAD_TIMEOUT_SECONDS <= 900


def test_validate_local_assets_generates_sha256sums_and_rejects_extras(tmp_path: Path):
    module = _load_module()
    revision = "a" * 40
    marker = module.release_identity_marker("v1.2.3", revision)
    for name in module.ALLOWED_BINARY_ASSETS:
        _write_runtime(tmp_path / name, marker)
    (tmp_path / "extra.txt").write_text("unexpected\n", encoding="utf-8")

    with pytest.raises(module.PublishRuntimeReleaseError, match="Unexpected asset"):
        module.prepare_local_release_assets(tmp_path, "v1.2.3", revision)

    (tmp_path / "extra.txt").unlink()
    assets = module.prepare_local_release_assets(tmp_path, "v1.2.3", revision)
    assert [path.name for path in assets] == list(module.PUBLIC_RELEASE_ASSETS)
    sums = (tmp_path / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    assert len(sums) == len(module.ALLOWED_BINARY_ASSETS)
    assert sums[0].endswith(f"  {module.ALLOWED_BINARY_ASSETS[0]}")


def test_prepare_local_assets_rejects_symlinks(tmp_path: Path):
    module = _load_module()
    revision = "b" * 40
    marker = module.release_identity_marker("v1.2.3", revision)
    for name in module.ALLOWED_BINARY_ASSETS[:-1]:
        _write_runtime(tmp_path / name, marker)
    outside = tmp_path / "outside"
    outside.mkdir()
    target = outside / "actual.exe"
    _write_runtime(target, marker)
    link = tmp_path / module.ALLOWED_BINARY_ASSETS[-1]
    try:
        link.symlink_to(target)
    except OSError as exc:
        pytest.skip(f"symlinks unavailable: {exc}")

    with pytest.raises(module.PublishRuntimeReleaseError, match="symlink"):
        module.prepare_local_release_assets(tmp_path, "v1.2.3", revision)


def test_public_release_notes_are_fixed_and_do_not_embed_changelog():
    module = _load_module()
    source_revision = "c" * 40
    notes = module.public_release_notes("v1.2.3", source_revision)
    assert "SHA256SUMS" in notes
    assert source_revision not in notes
    assert "What's Changed" not in notes
    assert "feat:" not in notes
    assert "fix:" not in notes


def test_release_check_reports_false_for_extra_remote_assets(monkeypatch, tmp_path: Path):
    module = _load_module()
    marker = module.release_identity_marker("v1.2.3", "d" * 40)
    for name in module.ALLOWED_BINARY_ASSETS:
        _write_runtime(tmp_path / name, marker)
    module.write_sha256sums(tmp_path, [tmp_path / name for name in module.ALLOWED_BINARY_ASSETS])

    monkeypatch.setattr(
        module,
        "gh_release_view",
        lambda *_args, **_kwargs: {
            "isDraft": False,
            "assets": [
                {"name": name, "size": 2048} for name in (*module.PUBLIC_RELEASE_ASSETS, "extra.txt")
            ],
        },
    )
    monkeypatch.setattr(
        module,
        "gh_release_download",
        lambda *_args, **_kwargs: None,
    )

    result = module.check_public_release(
        target_repo="owner/repo",
        tag="v1.2.3",
        source_revision="d" * 40,
        token="secret",
    )
    assert result["complete"] is False
    assert result["reason"] == "unexpected_remote_assets"


def test_release_check_raises_on_auth_or_access_failures(monkeypatch):
    module = _load_module()

    def fail(*_args, **_kwargs):
        raise module.PublishRuntimeReleaseError(
            "gh release view could not read owner/repo@v1.2.3 (exit 1)"
        )

    monkeypatch.setattr(module, "gh_release_view", fail)
    with pytest.raises(module.PublishRuntimeReleaseError, match="could not read"):
        module.check_public_release(
            target_repo="owner/repo",
            tag="v1.2.3",
            source_revision="d" * 40,
            token="secret",
        )


def test_release_check_reports_repairable_partial_release(monkeypatch, tmp_path: Path):
    module = _load_module()
    revision = "e" * 40
    marker = module.release_identity_marker("v1.2.3", revision)
    present = list(module.ALLOWED_BINARY_ASSETS[:2])
    for name in present:
        _write_runtime(tmp_path / name, marker)
    monkeypatch.setattr(
        module,
        "gh_release_view",
        lambda *_args, **_kwargs: {
            "isDraft": False,
            "assets": [{"name": name, "size": 2048} for name in present],
        },
    )
    seen_downloads: list[list[str]] = []

    def fake_download(_repo, _tag, destination, _token, asset_names):
        seen_downloads.append(list(asset_names))
        for name in asset_names:
            _write_runtime(destination / name, marker)

    monkeypatch.setattr(module, "gh_release_download_selected", fake_download)
    result = module.check_public_release(
        target_repo="owner/repo",
        tag="v1.2.3",
        source_revision=revision,
        token="secret",
    )
    assert result["complete"] is False
    assert result["reason"] == "repairable_partial_release"
    assert seen_downloads == [present]


def test_release_check_partial_release_fails_closed_on_revision_mismatch(
    monkeypatch, tmp_path: Path
):
    module = _load_module()
    good_revision = "f" * 40
    bad_marker = module.release_identity_marker("v1.2.3", "0" * 40)
    present = list(module.ALLOWED_BINARY_ASSETS[:2])
    monkeypatch.setattr(
        module,
        "gh_release_view",
        lambda *_args, **_kwargs: {
            "isDraft": False,
            "assets": [{"name": name, "size": 2048} for name in present],
        },
    )

    def fake_download(_repo, _tag, destination, _token, asset_names):
        for name in asset_names:
            _write_runtime(destination / name, bad_marker)

    monkeypatch.setattr(module, "gh_release_download_selected", fake_download)
    result = module.check_public_release(
        target_repo="owner/repo",
        tag="v1.2.3",
        source_revision=good_revision,
        token="secret",
    )
    assert result["complete"] is False
    assert result["reason"] == "source_revision_mismatch"


def test_ensure_release_fails_closed_on_remote_revision_mismatch(monkeypatch, tmp_path: Path):
    module = _load_module()
    marker = module.release_identity_marker("v1.2.3", "e" * 40)
    for name in module.ALLOWED_BINARY_ASSETS:
        _write_runtime(tmp_path / name, marker)

    monkeypatch.setattr(
        module,
        "prepare_local_release_assets",
        lambda *_args, **_kwargs: [tmp_path / name for name in module.PUBLIC_RELEASE_ASSETS],
    )
    monkeypatch.setattr(
        module,
        "check_public_release",
        lambda *_args, **_kwargs: {
            "exists": True,
            "is_draft": False,
            "complete": False,
            "reason": "source_revision_mismatch",
        },
    )

    with pytest.raises(module.PublishRuntimeReleaseError, match="source revision"):
        module.ensure_public_release(
            target_repo="owner/repo",
            tag="v1.2.3",
            source_revision="e" * 40,
            assets_dir=tmp_path,
            token="secret",
        )


def test_ensure_release_uses_draft_upload_verify_publish(monkeypatch, tmp_path: Path):
    module = _load_module()
    revision = "f" * 40
    marker = module.release_identity_marker("v1.2.3", revision)
    for name in module.ALLOWED_BINARY_ASSETS:
        _write_runtime(tmp_path / name, marker)
    commands: list[list[str]] = []
    states = iter(
        [
            {"exists": False, "is_draft": False, "complete": False, "reason": "missing_release"},
            {"exists": True, "is_draft": True, "complete": False, "reason": "draft_release"},
        ]
    )

    monkeypatch.setattr(
        module,
        "check_public_release",
        lambda *_args, **_kwargs: next(states),
    )

    def fake_run_gh(args, *, token, capture_output=True, check=True):
        assert token == "secret"
        commands.append(args)
        return ""

    monkeypatch.setattr(module, "run_gh", fake_run_gh)

    result = module.ensure_public_release(
        target_repo="owner/repo",
        tag="v1.2.3",
        source_revision=revision,
        assets_dir=tmp_path,
        token="secret",
    )

    assert result["published"] is True
    create, upload, publish = commands
    assert create[:4] == ["release", "create", "v1.2.3", "--repo"]
    assert upload[:4] == ["release", "upload", "v1.2.3", "--repo"]
    assert upload[-1] == "--clobber"
    uploaded_names = {Path(path).name for path in upload[5:-1]}
    assert uploaded_names == set(module.PUBLIC_RELEASE_ASSETS)
    assert publish == [
        "release",
        "edit",
        "v1.2.3",
        "--repo",
        "owner/repo",
        "--draft=false",
    ]


def test_release_check_treats_verified_draft_as_incomplete(monkeypatch, tmp_path: Path):
    module = _load_module()
    marker = module.release_identity_marker("v1.2.3", "a" * 40)
    for name in module.ALLOWED_BINARY_ASSETS:
        _write_runtime(tmp_path / name, marker)
    module.write_sha256sums(
        tmp_path, [tmp_path / name for name in module.ALLOWED_BINARY_ASSETS]
    )
    monkeypatch.setattr(
        module,
        "gh_release_view",
        lambda *_args, **_kwargs: {
            "isDraft": True,
            "assets": [
                {"name": name, "size": 2048} for name in module.PUBLIC_RELEASE_ASSETS
            ],
        },
    )
    def download(_repo, _tag, destination, _token):
        for name in module.PUBLIC_RELEASE_ASSETS:
            (destination / name).write_bytes((tmp_path / name).read_bytes())

    monkeypatch.setattr(module, "gh_release_download", download)

    result = module.check_public_release(
        target_repo="owner/repo",
        tag="v1.2.3",
        source_revision="a" * 40,
        token="secret",
    )
    assert result["complete"] is False
    assert result["reason"] == "draft_release"


def test_main_rejects_invalid_inputs(monkeypatch, capsys):
    module = _load_module()
    monkeypatch.setenv("PUBLIC_RELEASES_TOKEN", "secret")
    exit_code = module.main(
        [
            "--target-repo",
            "owner",
            "--tag",
            "1.2.3",
            "--source-revision",
            "xyz",
            "--assets-dir",
            str(ROOT),
            "--token-env",
            "bad-name",
            "--mode",
            "check",
        ]
    )
    assert exit_code == 1
    assert "Target repository must look like owner/name" in capsys.readouterr().err


def test_cli_requires_configured_public_token(monkeypatch, capsys):
    module = _load_module()
    monkeypatch.delenv("PUBLIC_RELEASES_TOKEN", raising=False)

    exit_code = module.main(
        [
            "--target-repo",
            "owner/repo",
            "--tag",
            "v1.2.3",
            "--source-revision",
            "a" * 40,
            "--assets-dir",
            str(ROOT),
            "--token-env",
            "PUBLIC_RELEASES_TOKEN",
            "--mode",
            "check",
        ]
    )
    assert exit_code == 1
    assert "PUBLIC_RELEASES_TOKEN" in capsys.readouterr().err
