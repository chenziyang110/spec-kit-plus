# Installation Guide

## Prerequisites

- **Linux/macOS** (or Windows; PowerShell scripts now supported without WSL)
- AI coding agent: [Claude Code](https://www.anthropic.com/claude-code), [GitHub Copilot](https://code.visualstudio.com/), [Codebuddy CLI](https://www.codebuddy.ai/cli), [Gemini CLI](https://github.com/google-gemini/gemini-cli), or [Pi Coding Agent](https://pi.dev)
- [uv](https://docs.astral.sh/uv/) for package management
- [Python 3.11+](https://www.python.org/downloads/)
- [Git](https://git-scm.com/downloads)

## Installation

### Install or Upgrade This Fork

For Spec Kit Plus, install from this fork rather than the upstream Spec Kit
repository:

```powershell
python -m pip uninstall -y specify-cli
uv tool install specify-cli --force --from git+https://github.com/chenziyang110/spec-kit-plus.git
Get-Command specify -All
specify --help
```

The uninstall step is intentional. Windows, Conda, and previous pip installs can
leave an older `specify.exe` earlier on PATH, while development builds may still
report the same `0.5.1.dev0` version string. `specify --help` should show the
current command surface, including commands such as `testing`.

### Initialize a New Project

The easiest way to get started is to initialize a new project from this fork. Use
`--refresh` when you want uv to re-check the Git source instead of reusing a
cached build:

```bash
# Install from the latest fork commit
uvx --refresh --from git+https://github.com/chenziyang110/spec-kit-plus.git specify init <PROJECT_NAME>

# Or pin a specific tag or branch when you need reproducibility
uvx --from git+https://github.com/chenziyang110/spec-kit-plus.git@vX.Y.Z specify init <PROJECT_NAME>
```

Or initialize in the current directory:

```bash
uvx --refresh --from git+https://github.com/chenziyang110/spec-kit-plus.git specify init .
# or use the --here flag
uvx --refresh --from git+https://github.com/chenziyang110/spec-kit-plus.git specify init --here
```

### Specify AI Agent

You can proactively specify your AI agent during initialization:

```bash
uvx --refresh --from git+https://github.com/chenziyang110/spec-kit-plus.git specify init <project_name> --ai claude
uvx --refresh --from git+https://github.com/chenziyang110/spec-kit-plus.git specify init <project_name> --ai gemini
uvx --refresh --from git+https://github.com/chenziyang110/spec-kit-plus.git specify init <project_name> --ai copilot
uvx --refresh --from git+https://github.com/chenziyang110/spec-kit-plus.git specify init <project_name> --ai codebuddy
uvx --refresh --from git+https://github.com/chenziyang110/spec-kit-plus.git specify init <project_name> --ai pi
```

### Specify Script Type (Shell vs PowerShell)

All automation scripts now have both Bash (`.sh`) and PowerShell (`.ps1`) variants.

Auto behavior:

- Windows default: `ps`
- Other OS default: `sh`
- Interactive mode: you'll be prompted unless you pass `--script`

Force a specific script type:

```bash
uvx --refresh --from git+https://github.com/chenziyang110/spec-kit-plus.git specify init <project_name> --script sh
uvx --refresh --from git+https://github.com/chenziyang110/spec-kit-plus.git specify init <project_name> --script ps
```

### Ignore Agent Tools Check

If you prefer to get the templates without checking for the right tools:

```bash
uvx --refresh --from git+https://github.com/chenziyang110/spec-kit-plus.git specify init <project_name> --ai claude --ignore-agent-tools
```

## Verification

After initialization, you should see the following commands available in your AI agent:

- `/sp-specify` - Create specifications in Claude skills
- `/sp-plan` - Generate implementation plans in Claude skills
- `/sp-tasks` - Break down into actionable tasks in Claude skills

The `.specify/scripts` directory will contain both `.sh` and `.ps1` scripts.

## Troubleshooting

### Enterprise / Air-Gapped Installation

If your environment blocks access to PyPI (you see 403 errors when running `uv tool install` or `pip install`), you can create a portable wheel bundle on a connected machine and transfer it to the air-gapped target.

**Step 1: Build the wheel on a connected machine (same OS and Python version as the target)**

```bash
# Clone the repository
git clone https://github.com/chenziyang110/spec-kit-plus.git
cd spec-kit-plus

# Build the wheel
pip install build
python -m build --wheel --outdir dist/

# Download the wheel and all its runtime dependencies
pip download -d dist/ dist/specify_cli-*.whl
```

> **Important:** `pip download` resolves platform-specific wheels (e.g., PyYAML includes native extensions). You must run this step on a machine with the **same OS and Python version** as the air-gapped target. If you need to support multiple platforms, repeat this step on each target OS (Linux, macOS, Windows) and Python version.

**Step 2: Transfer the `dist/` directory to the air-gapped machine**

Copy the entire `dist/` directory (which contains the `specify-cli` wheel and all dependency wheels) to the target machine via USB, network share, or other approved transfer method.

**Step 3: Install on the air-gapped machine**

```bash
pip install --no-index --find-links=./dist specify-cli
```

**Step 4: Initialize a project (no network required)**

```bash
# Initialize a project from bundled assets
specify init my-project --ai claude
```

`specify init` uses the templates, commands, and scripts bundled inside the
installed wheel, so the generated project matches the installed CLI version.

> **Note:** Python 3.11+ is required.

> **Windows note:** Offline scaffolding requires PowerShell 7+ (`pwsh`), not Windows PowerShell 5.x (`powershell.exe`). Install from https://aka.ms/powershell.

### Git Credential Manager on Linux

If you're having issues with Git authentication on Linux, you can install Git Credential Manager:

```bash
#!/usr/bin/env bash
set -e
echo "Downloading Git Credential Manager v2.6.1..."
wget https://github.com/git-ecosystem/git-credential-manager/releases/download/v2.6.1/gcm-linux_amd64.2.6.1.deb
echo "Installing Git Credential Manager..."
sudo dpkg -i gcm-linux_amd64.2.6.1.deb
echo "Configuring Git to use GCM..."
git config --global credential.helper manager
echo "Cleaning up..."
rm gcm-linux_amd64.2.6.1.deb
```
