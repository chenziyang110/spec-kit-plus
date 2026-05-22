#!/usr/bin/env bash
set -euo pipefail

REPO="${PROJECT_COGNITION_REPO:-chenziyang110/spec-kit-plus}"
VERSION="${PROJECT_COGNITION_VERSION:-latest}"
INSTALL_DIR="${PROJECT_COGNITION_INSTALL_DIR:-$HOME/.specify/bin}"

case "$(uname -s)" in
  Linux) os="linux" ;;
  Darwin) os="darwin" ;;
  *) echo "Unsupported OS: $(uname -s)" >&2; exit 1 ;;
esac

case "$(uname -m)" in
  x86_64|amd64) arch="amd64" ;;
  arm64|aarch64) arch="arm64" ;;
  *) echo "Unsupported architecture: $(uname -m)" >&2; exit 1 ;;
esac

asset="project-cognition-${os}-${arch}"
if [[ "$VERSION" == "latest" ]]; then
  url="https://github.com/${REPO}/releases/latest/download/${asset}"
else
  url="https://github.com/${REPO}/releases/download/${VERSION}/${asset}"
fi

mkdir -p "$INSTALL_DIR"
target="${INSTALL_DIR}/project-cognition"

tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT

echo "Downloading ${url}"
curl -fsSL "$url" -o "$tmp"
install -m 0755 "$tmp" "$target"

echo "Installed project-cognition to ${target}"
case ":$PATH:" in
  *":$INSTALL_DIR:"*) ;;
  *)
    echo "Add this to your shell profile if needed:"
    echo "  export PATH=\"${INSTALL_DIR}:\$PATH\""
    ;;
esac
