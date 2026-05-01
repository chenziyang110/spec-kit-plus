#!/usr/bin/env bash
set -euo pipefail

REPO="chenziyang110/spec-kit-plus"
BINARY="spec-lint"
BASE_URL="https://github.com/${REPO}/releases/latest/download"

# ---- detect OS and arch ----
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)
case "$ARCH" in
    x86_64|amd64) ARCH="amd64" ;;
    aarch64|arm64) ARCH="arm64" ;;
    *) echo "Unsupported architecture: $ARCH (expected amd64 or arm64)"; exit 1 ;;
esac

case "$OS" in
    linux)  FILENAME="${BINARY}-${OS}-${ARCH}" ;;
    darwin) FILENAME="${BINARY}-${OS}-${ARCH}" ;;
    mingw*|msys*|cygwin*)
        echo "On Windows, use the PowerShell installer:"
        echo "  irm https://raw.githubusercontent.com/${REPO}/main/tools/spec-lint/install.ps1 | iex"
        exit 1 ;;
    *) echo "Unsupported OS: $OS (expected linux or darwin)"; exit 1 ;;
esac

URL="${BASE_URL}/${FILENAME}"

# ---- choose install directory ----
if [ -w /usr/local/bin ]; then
    INSTALL_DIR="/usr/local/bin"
elif [ -d "$HOME/.local/bin" ] && [ -w "$HOME/.local/bin" ]; then
    INSTALL_DIR="$HOME/.local/bin"
else
    INSTALL_DIR="$HOME/.local/bin"
    mkdir -p "$INSTALL_DIR"
fi

echo "==> spec-lint installer"
echo "    platform: ${OS}/${ARCH}"
echo "    install:  ${INSTALL_DIR}/${BINARY}"
echo ""

# ---- download ----
echo "==> Downloading..."
if command -v curl >/dev/null 2>&1; then
    curl -fsSL --retry 3 "$URL" -o "${INSTALL_DIR}/${BINARY}"
elif command -v wget >/dev/null 2>&1; then
    wget -q --tries=3 "$URL" -O "${INSTALL_DIR}/${BINARY}"
else
    echo "Error: curl or wget required for download"
    exit 1
fi

chmod +x "${INSTALL_DIR}/${BINARY}"

# ---- verify ----
echo "==> Verifying..."
"${INSTALL_DIR}/${BINARY}" --version

# ---- PATH check ----
if ! echo "$PATH" | tr ':' '\n' | grep -qF "$INSTALL_DIR"; then
    echo ""
    echo "==> Add ${INSTALL_DIR} to your PATH:"
    case "${SHELL:-}" in
        */zsh)  echo "    echo 'export PATH=\"${INSTALL_DIR}:\$PATH\"' >> ~/.zshrc && source ~/.zshrc" ;;
        */bash) echo "    echo 'export PATH=\"${INSTALL_DIR}:\$PATH\"' >> ~/.bashrc && source ~/.bashrc" ;;
        */fish) echo "    fish_add_path ${INSTALL_DIR}" ;;
        *)      echo "    export PATH=\"${INSTALL_DIR}:\$PATH\"  # add to your shell profile" ;;
    esac
fi

echo ""
echo "==> spec-lint installed successfully."
echo "    Run 'spec-lint -dir <feature-dir>' to validate a spec."
