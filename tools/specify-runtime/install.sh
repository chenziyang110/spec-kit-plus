#!/usr/bin/env bash
set -euo pipefail

repo="${SPECIFY_RUNTIME_REPO:-chenziyang110/spec-kit-plus}"
version="${SPECIFY_RUNTIME_VERSION:-latest}"
binary="specify-runtime"

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
if [[ "$handshake" != *'"protocol_version":"specify-runtime.v1"'* || "$handshake" != *'"artifact.catalog"'* || "$handshake" != *'"artifact.prepare"'* || "$handshake" != *'"artifact.scaffold"'* || "$handshake" != *'"artifact.show"'* || "$handshake" != *'"artifact.submit"'* || "$handshake" != *'"validate.spec"'* || "$handshake" != *'"workflow.start"'* || "$handshake" != *'"workflow.status"'* || "$handshake" != *'"workflow.transition"'* ]]; then
  echo "Downloaded binary failed the specify-runtime API handshake" >&2
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
