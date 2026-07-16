#!/usr/bin/env bash
set -euo pipefail

REPO="${PROJECT_COGNITION_REPO:-chenziyang110/spec-kit-plus}"
VERSION="${PROJECT_COGNITION_VERSION:-latest}"
BINARY="project-cognition"

case "$(uname -s | tr '[:upper:]' '[:lower:]')" in
  linux) os="linux" ;;
  darwin) os="darwin" ;;
  mingw*|msys*|cygwin*)
    echo "On Windows, use the PowerShell installer:"
    echo "  irm https://raw.githubusercontent.com/${REPO}/main/tools/project-cognition/install.ps1 | iex"
    exit 1
    ;;
  *) echo "Unsupported OS: $(uname -s)" >&2; exit 1 ;;
esac

case "$(uname -m)" in
  x86_64|amd64) arch="amd64" ;;
  arm64|aarch64) arch="arm64" ;;
  *) echo "Unsupported architecture: $(uname -m) (expected amd64 or arm64)" >&2; exit 1 ;;
esac

asset="${BINARY}-${os}-${arch}"
if [[ "$VERSION" == "latest" ]]; then
  url="https://github.com/${REPO}/releases/latest/download/${asset}"
else
  url="https://github.com/${REPO}/releases/download/${VERSION}/${asset}"
fi

if [[ -n "${PROJECT_COGNITION_INSTALL_DIR:-}" ]]; then
  install_dir="${PROJECT_COGNITION_INSTALL_DIR}"
elif [[ -w /usr/local/bin ]]; then
  install_dir="/usr/local/bin"
else
  install_dir="${HOME}/.local/bin"
fi

mkdir -p "$install_dir"
target="${install_dir}/${BINARY}"

echo "==> project-cognition installer"
echo "    platform: ${os}/${arch}"
echo "    install:  ${target}"
echo ""

tmp="$(mktemp "${install_dir}/.${BINARY}.XXXXXX")"
trap 'rm -f "$tmp"' EXIT

echo "==> Downloading prebuilt release asset..."
if command -v curl >/dev/null 2>&1; then
  curl -fsSL --retry 3 "$url" -o "$tmp"
elif command -v wget >/dev/null 2>&1; then
  wget -q --tries=3 "$url" -O "$tmp"
else
  echo "Error: curl or wget required for download" >&2
  exit 1
fi

chmod 0755 "$tmp"

echo "==> Verifying..."
"$tmp" --version
root_help="$("$tmp" --help 2>&1 || true)"
for required_command in repair-status scan-set scan-prepare scan-accept; do
  if [[ "$root_help" != *"$required_command"* ]]; then
    echo "Error: downloaded project-cognition binary is missing required ${required_command} command." >&2
    echo "Expected 'project-cognition --help' to include ${required_command}." >&2
    exit 1
  fi
done
scan_prepare_help="$("$tmp" scan-prepare --help 2>&1 || true)"
if [[ "$scan_prepare_help" != *"-force"* || "$scan_prepare_help" != *"-scan-set"* ]]; then
  echo "Error: downloaded project-cognition binary is missing required scan-prepare flags." >&2
  echo "Expected 'project-cognition scan-prepare --help' to include -force and -scan-set." >&2
  exit 1
fi
scan_accept_help="$("$tmp" scan-accept --help 2>&1 || true)"
if [[ "$scan_accept_help" != *"-packet-id"* || "$scan_accept_help" != *"-result"* ]]; then
  echo "Error: downloaded project-cognition binary is missing required scan-accept flags." >&2
  echo "Expected 'project-cognition scan-accept --help' to include -packet-id and -result." >&2
  exit 1
fi
update_help="$("$tmp" update --help 2>&1 || true)"
if [[ "$update_help" != *"-payload-file"* || "$update_help" != *"-verification"* ]]; then
  echo "Error: downloaded project-cognition binary is missing required update flags." >&2
  echo "Expected 'project-cognition update --help' to include -payload-file and -verification." >&2
  exit 1
fi
semantic_intake_help="$("$tmp" semantic-intake --help 2>&1 || true)"
if [[ "$semantic_intake_help" != *"-input"* ]]; then
  echo "Error: downloaded project-cognition semantic-intake binary is missing required input flag." >&2
  echo "Expected 'project-cognition semantic-intake --help' to include -input." >&2
  exit 1
fi
semantic_audit_resume_help="$("$tmp" semantic-audit-resume --help 2>&1 || true)"
if [[ "$semantic_audit_resume_help" != *"-input"* ]]; then
  echo "Error: downloaded project-cognition semantic-audit-resume binary is missing required input flag." >&2
  echo "Expected 'project-cognition semantic-audit-resume --help' to include -input." >&2
  exit 1
fi
lexicon_help="$("$tmp" lexicon --help 2>&1 || true)"
if [[ "$lexicon_help" != *"-mode"* ]]; then
  echo "Error: downloaded project-cognition binary is missing required lexicon catalog mode." >&2
  echo "Expected 'project-cognition lexicon --help' to include -mode." >&2
  exit 1
fi
compass_help="$("$tmp" compass --help 2>&1 || true)"
if [[ "$compass_help" != *"-semantic-intake-file"* || "$compass_help" != *"-query-plan-file"* ]]; then
  echo "Error: downloaded project-cognition binary is missing required compass flags." >&2
  echo "Expected 'project-cognition compass --help' to include -semantic-intake-file and -query-plan-file." >&2
  exit 1
fi
expand_help="$("$tmp" expand --help 2>&1 || true)"
if [[ "$expand_help" != *"-section"* ]]; then
  echo "Error: downloaded project-cognition binary is missing required expand section flag." >&2
  echo "Expected 'project-cognition expand --help' to include -section." >&2
  exit 1
fi
delta_append_help="$("$tmp" delta append --help 2>&1 || true)"
if [[ "$delta_append_help" != *"-verification"* || "$delta_append_help" != *"-generated-surface"* ]]; then
  echo "Error: downloaded project-cognition binary is missing required delta append flags." >&2
  echo "Expected 'project-cognition delta append --help' to include -verification and -generated-surface." >&2
  exit 1
fi
closeout_plan_help="$("$tmp" closeout-plan --help 2>&1 || true)"
if [[ "$closeout_plan_help" != *"-workflow"* || "$closeout_plan_help" != *"-delta-session"* ]]; then
  echo "Error: downloaded project-cognition binary is missing required closeout-plan flags." >&2
  echo "Expected 'project-cognition closeout-plan --help' to include -workflow and -delta-session." >&2
  exit 1
fi

mv -f "$tmp" "$target"

case ":$PATH:" in
  *":$install_dir:"*) ;;
  *)
    echo ""
    echo "==> Add ${install_dir} to your PATH:"
    case "${SHELL:-}" in
      */zsh) echo "    echo 'export PATH=\"${install_dir}:\$PATH\"' >> ~/.zshrc && source ~/.zshrc" ;;
      */bash) echo "    echo 'export PATH=\"${install_dir}:\$PATH\"' >> ~/.bashrc && source ~/.bashrc" ;;
      */fish) echo "    fish_add_path ${install_dir}" ;;
      *) echo "    export PATH=\"${install_dir}:\$PATH\"  # add to your shell profile" ;;
    esac
    ;;
esac

echo ""
echo "==> project-cognition installed successfully."
echo "    Generated workflows will find it as 'project-cognition' on PATH."
