#!/usr/bin/env bash
set -euo pipefail

repo="${SPECIFY_RUNTIME_REPO:-chenziyang110/spec-kit-plus}"
version="${SPECIFY_RUNTIME_VERSION:-latest}"
binary="specify-runtime"

if [[ "$version" != "latest" && ! "$version" =~ ^v[0-9]+(\.[0-9]+){2}([.-][0-9A-Za-z.-]+)?$ ]]; then
  echo "SPECIFY_RUNTIME_VERSION must be latest or a concrete release tag such as v0.6.6" >&2
  exit 1
fi

case "$(uname -s | tr '[:upper:]' '[:lower:]')" in
  linux) os="linux" ;;
  darwin) os="darwin" ;;
  mingw*|msys*|cygwin*)
    echo "On Windows, use tools/specify-runtime/install.ps1" >&2
    exit 1
    ;;
  *) echo "Unsupported OS: $(uname -s)" >&2; exit 1 ;;
esac

case "$(uname -m)" in
  x86_64|amd64) arch="amd64" ;;
  arm64|aarch64) arch="arm64" ;;
  *) echo "Unsupported architecture: $(uname -m)" >&2; exit 1 ;;
esac

asset="${binary}-${os}-${arch}"
if [[ "$version" == "latest" ]]; then
  url="https://github.com/${repo}/releases/latest/download/${asset}"
else
  url="https://github.com/${repo}/releases/download/${version}/${asset}"
fi

if [[ -n "${SPECIFY_RUNTIME_INSTALL_DIR:-}" ]]; then
  install_dir="$SPECIFY_RUNTIME_INSTALL_DIR"
elif [[ -w /usr/local/bin ]]; then
  install_dir="/usr/local/bin"
else
  install_dir="${HOME}/.local/bin"
fi

mkdir -p "$install_dir"
target="${install_dir}/${binary}"
candidate="$(mktemp "${install_dir}/.${binary}.XXXXXX")"
trap 'rm -f "$candidate"' EXIT

echo "==> Downloading ${asset}"
if command -v curl >/dev/null 2>&1; then
  curl -fsSL --retry 3 "$url" -o "$candidate"
elif command -v wget >/dev/null 2>&1; then
  wget -q --tries=3 "$url" -O "$candidate"
else
  echo "curl or wget is required" >&2
  exit 1
fi
chmod 0755 "$candidate"

handshake="$("$candidate" api handshake --format json)"
if [[ "$handshake" != *'"protocol_version":"specify-runtime.v1"'* || "$handshake" != *'"artifact.catalog"'* || "$handshake" != *'"artifact.checklist"'* || "$handshake" != *'"artifact.delete"'* || "$handshake" != *'"artifact.list"'* || "$handshake" != *'"artifact.patch"'* || "$handshake" != *'"artifact.prepare"'* || "$handshake" != *'"artifact.restore"'* || "$handshake" != *'"artifact.scaffold"'* || "$handshake" != *'"artifact.show"'* || "$handshake" != *'"artifact.submit"'* || "$handshake" != *'"cognition.archive-incompatible-store"'* || "$handshake" != *'"cognition.run"'* || "$handshake" != *'"cognition.scan-packet"'* || "$handshake" != *'"implement.task-reopen"'* || "$handshake" != *'"validate.spec"'* || "$handshake" != *'"workflow.show"'* || "$handshake" != *'"workflow.enter"'* || "$handshake" != *'"workflow.next"'* || "$handshake" != *'"workflow.complete-stage"'* || "$handshake" != *'"workflow.transition"'* || "$handshake" != *'"workflow.reopen"'* || "$handshake" != *'"workflow.block"'* || "$handshake" != *'"workflow.resolve"'* || "$handshake" != *'"workflow.closeout"'* ]]; then
  echo "Downloaded binary failed the specify-runtime API handshake" >&2
  exit 1
fi
version_info="$("$candidate" version --format json)"
release_cli_version="$(printf '%s' "$version_info" | sed -n 's/.*"cli_version":"\([^"]*\)".*/\1/p')"
handshake_cli_version="$(printf '%s' "$handshake" | sed -n 's/.*"cli_version":"\([^"]*\)".*/\1/p')"
source_revision="$(printf '%s' "$version_info" | sed -n 's/.*"source_revision":"\([^"]*\)".*/\1/p')"
handshake_source_revision="$(printf '%s' "$handshake" | sed -n 's/.*"source_revision":"\([^"]*\)".*/\1/p')"
release_dirty="$(printf '%s' "$version_info" | sed -n 's/.*"dirty":\([^,}]*\).*/\1/p' | tr -d '[:space:]')"
handshake_dirty="$(printf '%s' "$handshake" | sed -n 's/.*"dirty":\([^,}]*\).*/\1/p' | tr -d '[:space:]')"
if [[ "$version" == "latest" ]]; then
  if [[ ! "$release_cli_version" =~ ^v[0-9]+(\.[0-9]+){2}([.-][0-9A-Za-z.-]+)?$ ]]; then
    echo "Downloaded latest binary has no concrete release version: ${release_cli_version:-missing}" >&2
    exit 1
  fi
elif [[ "$release_cli_version" != "$version" ]]; then
  echo "Downloaded binary version ${release_cli_version:-missing} does not match requested ${version}" >&2
  exit 1
fi
if [[ "$handshake_cli_version" != "$release_cli_version" ]]; then
  echo "Downloaded binary reports inconsistent version identity" >&2
  exit 1
fi
if [[ "$handshake_source_revision" != "$source_revision" || "$handshake_dirty" != "$release_dirty" ]]; then
  echo "Downloaded binary reports inconsistent release provenance" >&2
  exit 1
fi
if [[ ! "$source_revision" =~ ^[0-9a-fA-F]{40}([0-9a-fA-F]{24})?$ || "$release_dirty" != "false" ]]; then
  echo "Downloaded binary has invalid release provenance" >&2
  exit 1
fi
cognition_help="$("$candidate" cognition --help 2>&1)"
for command in status query scan-prepare update; do
  if [[ "$cognition_help" != *"$command"* ]]; then
    echo "Downloaded binary is missing cognition command: ${command}" >&2
    exit 1
  fi
done

mv -f "$candidate" "$target"
echo "==> Installed ${target}"
case ":$PATH:" in
  *":$install_dir:"*) ;;
  *) echo "Add ${install_dir} to PATH to use specify-runtime." ;;
esac
