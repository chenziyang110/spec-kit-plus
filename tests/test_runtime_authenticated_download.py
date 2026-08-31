"""Private-release bootstrap, including credential and redirect boundaries."""

import hashlib
import io
import json
from pathlib import Path
from types import SimpleNamespace
from urllib.error import HTTPError, URLError
from urllib.request import Request

import pytest

from specify_cli import specify_runtime as runtime


@pytest.fixture(autouse=True)
def isolate_credentials(monkeypatch):
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(runtime.shutil, "which", lambda _name: None)


def test_download_recovers_with_git_credentials_after_gh_fails(monkeypatch, tmp_path, capsys):
    official = runtime.github_download_url("latest")
    monkeypatch.setattr(runtime, "cache_dir", lambda: tmp_path)
    monkeypatch.setattr(runtime, "download_urls", lambda _v: [official, "https://mirror.invalid/asset"])
    calls = []

    def fail_http(url, *_args, **_kwargs):
        calls.append("http")
        assert url == official, "authenticated recovery must precede custom mirrors"
        raise HTTPError(url, 404, "Not Found", {}, None)

    def fail_gh(*_args):
        calls.append("gh")
        raise runtime.SpecifyRuntimeError("GitHub CLI is unavailable")

    def api(version, destination):
        calls.append("api")
        assert version == "latest"
        destination.write_bytes(b"x" * 2048)
        return destination

    monkeypatch.setattr(runtime, "_download_from_url", fail_http)
    monkeypatch.setattr(runtime, "_download_with_github_cli", fail_gh)
    monkeypatch.setattr(runtime, "_download_with_github_api", api, raising=False)
    destination = tmp_path / "runtime.bin"
    assert runtime.download("latest", destination) == destination
    assert calls == ["http", "gh", "api"]
    assert "GitHub API" in capsys.readouterr().err


def test_git_credential_lookup_is_scoped_noninteractive_and_not_logged(monkeypatch, capsys):
    monkeypatch.setattr(runtime.shutil, "which", lambda name: "git" if name == "git" else None)

    def run(command, **kwargs):
        assert command == ["git", "-c", "credential.interactive=false", "-c", "core.askPass=", "credential", "fill"]
        assert kwargs["input"] == f"protocol=https\nhost=github.com\npath={runtime.REPO}.git\n\n"
        assert kwargs["env"]["GIT_TERMINAL_PROMPT"] == "0"
        assert kwargs["env"]["GCM_INTERACTIVE"] == "never"
        assert kwargs["env"]["GIT_ASKPASS"] == ""
        assert kwargs["capture_output"] is True
        assert 0 < kwargs["timeout"] <= 10
        return SimpleNamespace(returncode=0, stdout="protocol=https\nhost=github.com\nusername=test\npassword=private-test-token\n", stderr="")

    monkeypatch.setattr(runtime.subprocess, "run", run)
    assert list(runtime._github_tokens()) == ["private-test-token"]
    captured = capsys.readouterr()
    assert "private-test-token" not in captured.out + captured.err


def test_tokens_prefer_environment_but_keep_git_as_fallback(monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "environment-token")
    monkeypatch.setenv("GITHUB_TOKEN", "environment-token")
    monkeypatch.setattr(runtime.shutil, "which", lambda _name: "git")
    monkeypatch.setattr(runtime.subprocess, "run", lambda *_a, **_k: SimpleNamespace(returncode=0, stdout="password=git-token\n", stderr=""))
    assert list(runtime._github_tokens()) == ["environment-token", "git-token"]


@pytest.mark.parametrize("result", [
    SimpleNamespace(returncode=1, stdout="password=secret\n", stderr="secret"),
    SimpleNamespace(returncode=0, stdout="username=user\n", stderr=""),
    SimpleNamespace(returncode=0, stdout="password=bad token\n", stderr=""),
])
def test_unusable_credentials_are_ignored(monkeypatch, result):
    monkeypatch.setattr(runtime.shutil, "which", lambda _name: "git")
    monkeypatch.setattr(runtime.subprocess, "run", lambda *_a, **_k: result)
    assert list(runtime._github_tokens()) == []


@pytest.mark.parametrize("error", [OSError("secret"), runtime.subprocess.TimeoutExpired("secret", 10)])
def test_credential_lookup_failure_is_bounded_and_silent(monkeypatch, error, capsys):
    monkeypatch.setattr(runtime.shutil, "which", lambda _name: "git")
    def fail(*_a, **_k):
        raise error
    monkeypatch.setattr(runtime.subprocess, "run", fail)
    assert list(runtime._github_tokens()) == []
    assert "secret" not in str(capsys.readouterr())


def _mock_api(monkeypatch, *, asset_overrides=None, content=b"x" * 2048, metadata=None):
    asset = {"name": runtime.binary_filename(), "id": 123, "size": 2048,
             "digest": "sha256:" + hashlib.sha256(b"x" * 2048).hexdigest(),
             "url": "https://untrusted.invalid/do-not-use", "browser_download_url": "https://untrusted.invalid/do-not-use"}
    asset.update(asset_overrides or {})
    requests = []
    def open_request(request, *, timeout):
        requests.append(request)
        assert request.host == "api.github.com"
        assert request.get_header("Authorization") == "Bearer private-test-token"
        assert timeout > 0
        if len(requests) == 1:
            return io.BytesIO(json.dumps(metadata if metadata is not None else {"assets": [asset]}).encode())
        assert request.full_url == f"https://api.github.com/repos/{runtime.REPO}/releases/assets/123"
        assert request.get_header("Accept") == "application/octet-stream"
        return io.BytesIO(content)
    monkeypatch.setattr(runtime, "build_opener", lambda *_handlers: SimpleNamespace(open=open_request), raising=False)
    monkeypatch.setenv("GH_TOKEN", "private-test-token")
    return requests


@pytest.mark.parametrize("version,suffix", [("latest", "latest"), ("v0.6.23", "tags/v0.6.23")])
def test_api_download_uses_asset_id_size_and_digest(monkeypatch, tmp_path, version, suffix):
    requests = _mock_api(monkeypatch)
    destination = tmp_path / "runtime.bin"
    assert runtime._download_with_github_api(version, destination) == destination
    assert requests[0].full_url == f"https://api.github.com/repos/{runtime.REPO}/releases/{suffix}"
    assert destination.read_bytes() == b"x" * 2048


@pytest.mark.parametrize("overrides,content", [
    ({"size": 4096}, b"x" * 2048),
    ({"digest": "sha256:" + "0" * 64}, b"x" * 2048),
    ({"digest": "sha256:malformed"}, b"x" * 2048),
    ({"id": "../other"}, b"x" * 2048),
    ({"size": 12}, b"x" * 12),
], ids=["size-mismatch", "checksum-mismatch", "invalid-digest", "invalid-id", "too-small"])
def test_api_rejects_invalid_or_corrupt_assets(monkeypatch, tmp_path, overrides, content):
    _mock_api(monkeypatch, asset_overrides=overrides, content=content)
    destination = tmp_path / "runtime.bin"
    with pytest.raises(runtime.SpecifyRuntimeError):
        runtime._download_with_github_api("latest", destination)
    assert not destination.exists()


def test_missing_asset_is_reported_without_auth_blame(monkeypatch, tmp_path):
    _mock_api(monkeypatch, metadata={"assets": []})
    with pytest.raises(runtime.SpecifyRuntimeError, match="does not contain"):
        runtime._download_with_github_api("latest", tmp_path / "runtime.bin")


def test_api_failure_hides_tokens_and_signed_urls(monkeypatch, tmp_path):
    monkeypatch.setenv("GH_TOKEN", "private-test-token")
    def fail(*_a, **_k):
        raise URLError("private-test-token https://example.invalid/?signature=secret")
    monkeypatch.setattr(runtime, "build_opener", lambda *_a: SimpleNamespace(open=fail), raising=False)
    with pytest.raises(runtime.SpecifyRuntimeError) as exc:
        runtime._download_with_github_api("latest", tmp_path / "runtime.bin")
    assert "private-test-token" not in str(exc.value)
    assert "signature" not in str(exc.value)
    assert exc.value.__suppress_context__ is True


def test_rejected_env_token_can_fall_back_to_git_token(monkeypatch, tmp_path):
    monkeypatch.setattr(runtime, "_github_tokens", lambda: iter(["expired-token", "private-test-token"]), raising=False)
    requests = _mock_api(monkeypatch)
    opener = runtime.build_opener()
    def open_request(request, **kwargs):
        if request.get_header("Authorization") == "Bearer expired-token":
            raise HTTPError(request.full_url, 401, "Unauthorized", {}, None)
        return opener.open(request, **kwargs)
    monkeypatch.setattr(runtime, "build_opener", lambda *_a: SimpleNamespace(open=open_request))
    assert runtime._download_with_github_api("latest", tmp_path / "runtime.bin").is_file()
    assert len(requests) == 2


def test_redirect_does_not_forward_credentials():
    request = Request("https://api.github.com/repos/example/repo/releases/assets/1", headers={"Authorization": "Bearer secret"})
    redirected = runtime._GitHubAssetRedirect().redirect_request(
        request, None, 302, "Found", {}, "https://release-assets.githubusercontent.com/asset?signature=secret"
    )
    assert redirected.get_header("Authorization") is None


@pytest.mark.parametrize("url", ["http://example.invalid/asset", "ftp://example.invalid/asset", "https://user:secret@example.invalid/asset"])
def test_redirect_rejects_insecure_destinations(url):
    with pytest.raises(runtime.SpecifyRuntimeError):
        runtime._GitHubAssetRedirect().redirect_request(Request("https://api.github.com/asset"), None, 302, "Found", {}, url)
