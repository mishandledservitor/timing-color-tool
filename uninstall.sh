#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════
# Timing Colour Tool — Uninstaller
# Removes the virtual environment and generated files. Your database backups
# are kept unless you explicitly choose to remove them.
# ══════════════════════════════════════════════════════════════════════════════

set -e

INSTALL_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$INSTALL_DIR"

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║     🧹  TIMING COLOUR TOOL — Uninstall                   ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "   Location: $INSTALL_DIR"
echo ""

ask_remove() {
    local target="$1"
    local description="$2"
    if [ -e "$target" ]; then
        printf "   Remove %s (%s)? [y/N]: " "$description" "$target"
        read -r answer
        if [[ "$answer" =~ ^[Yy]$ ]]; then
            rm -rf "$target"
            echo "   ✅ Removed $description"
        else
            echo "   ⏭  Kept $description"
        fi
    fi
}

# Virtual environment
ask_remove "$INSTALL_DIR/venv" "Python virtual environment (venv/)"

# Generated launcher
ask_remove "$INSTALL_DIR/timing-colours" "launcher script (timing-colours)"

# Database backups
BACKUPS=$(find "$HOME/Library/Application Support/info.eurocomp.Timing2/" -name "*.backup_*" 2>/dev/null | head -20)
if [ -n "$BACKUPS" ]; then
    echo ""
    echo "   Found database backups:"
    echo "$BACKUPS" | while read -r f; do echo "     $f"; done
    echo ""
    printf "   Remove ALL database backups? [y/N]: "
    read -r answer
    if [[ "$answer" =~ ^[Yy]$ ]]; then
        echo "$BACKUPS" | while read -r f; do rm -f "$f"; done
        echo "   ✅ Removed database backups"
    else
        echo "   ⏭  Kept database backups"
    fi
fi

echo ""
echo "   Done. The Python scripts and README remain in:"
echo "   $INSTALL_DIR"
echo ""
echo "   To fully remove, delete the entire folder:"
echo "   rm -rf \"$INSTALL_DIR\""
echo ""
