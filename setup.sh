#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════
# Timing Colour Tool — Setup Script for macOS
# No third-party packages required — uses only the Python standard library.
# Everything stays in this folder.
# ══════════════════════════════════════════════════════════════════════════════

set -e

INSTALL_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$INSTALL_DIR"

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║     🎨  TIMING COLOUR TOOL — macOS Setup  🎨             ║"
echo "║     Colour variations for Timing app projects            ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "   Install directory: $INSTALL_DIR"
echo ""

# ── 1. Check Python ─────────────────────────────────────────────────────────
echo "🔍 Step 1/2: Checking Python..."
PYTHON_CMD=""

# Try system python3 first, then Homebrew locations
for candidate in \
    "/usr/bin/python3" \
    "/usr/local/bin/python3" \
    "/opt/homebrew/bin/python3" \
    "$(which python3 2>/dev/null)"; do
    if [ -x "$candidate" ] 2>/dev/null; then
        PYTHON_VERSION=$("$candidate" --version 2>&1 | awk '{print $2}')
        MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
        MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)
        if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 6 ]; then
            PYTHON_CMD="$candidate"
            echo "   ✅ Python $PYTHON_VERSION found ($candidate)"
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo "   ⚠  Python 3.6+ not found."
    echo ""
    echo "   Install options:"
    echo "     • Run: xcode-select --install"
    echo "     • Or install Homebrew, then: brew install python@3.12"
    echo ""
    exit 1
fi

# ── 2. Create venv ──────────────────────────────────────────────────────────
echo ""
echo "📦 Step 2/2: Setting up Python environment..."

if [ ! -d "$INSTALL_DIR/venv" ]; then
    echo "   🐍 Creating virtual environment..."
    "$PYTHON_CMD" -m venv "$INSTALL_DIR/venv"
    echo "   ✅ Virtual environment created"
else
    echo "   ✅ Virtual environment already exists"
fi

# No pip packages needed — this tool uses only the Python standard library!
echo "   ✅ No third-party packages required (standard library only)"

# ── Create launcher ─────────────────────────────────────────────────────────
echo ""
echo "🔧 Creating launcher script..."

cat > "$INSTALL_DIR/timing-colours" << 'LAUNCHER'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/venv/bin/activate"
exec python "$SCRIPT_DIR/timing_colour_tool.py" "$@"
LAUNCHER

chmod +x "$INSTALL_DIR/timing-colours"
echo "   ✅ Launcher created: ./timing-colours"

# ── Done! ────────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║                 ✅  SETUP COMPLETE!                      ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║                                                          ║"
echo "║  Interactive mode (recommended):                         ║"
echo "║    ./timing-colours                                      ║"
echo "║                                                          ║"
echo "║  Command-line usage:                                     ║"
echo "║    ./timing-colours /path/to/SQLite.db --dry-run         ║"
echo "║    ./timing-colours /path/to/SQLite.db --variation 35    ║"
echo "║    ./timing-colours /path/to/SQLite.db --variation 35 \  ║"
echo "║      --seed 42                                           ║"
echo "║                                                          ║"
echo "║  ⚠  Quit the Timing app before running!                  ║"
echo "║                                                          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
