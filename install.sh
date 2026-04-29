#!/usr/bin/env bash
# proton-sidecar one-liner installer
# Usage: curl -sSf https://raw.githubusercontent.com/OWNER/proton-sidecar/main/install.sh | bash
set -euo pipefail

REPO_URL="https://github.com/OWNER/proton-sidecar"

echo "==> Installing proton-sidecar..."

# Check Python 3.11+
if ! python3 -c "import sys; assert sys.version_info >= (3, 11)" 2>/dev/null; then
    echo "Error: Python 3.11 or newer is required."
    echo "Install it with your package manager, e.g.:"
    echo "  sudo apt install python3.11"
    echo "  brew install python@3.11"
    exit 1
fi

# Check pipx
if ! command -v pipx &>/dev/null; then
    echo "Error: pipx is required but not found."
    echo "Install it with:"
    echo "  python3 -m pip install --user pipx"
    echo "  python3 -m pipx ensurepath"
    echo "Then re-run this installer."
    exit 1
fi

pipx install "git+${REPO_URL}.git"

echo ""
echo "==> proton-sidecar installed successfully!"
echo ""
echo "Run 'sidecar doctor' to verify your system dependencies."
echo "Run 'sidecar list' to see available companion apps."
