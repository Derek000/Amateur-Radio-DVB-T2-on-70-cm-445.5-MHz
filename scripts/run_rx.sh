#!/usr/bin/env bash
# run_rx.sh — Compile and execute the DVB-T2 RX flowgraph.
#
# Compiles the GRC flowgraph to Python with grcc (if needed), then executes
# it headlessly — ideal for remote operation over SSH.  Falls back to opening
# GNU Radio Companion if grcc is absent.
#
# Usage:
#   ./scripts/run_rx.sh [--grblocks] [--gui]
#
# Options:
#   --grblocks  Use the all-GRC-blocks RX variant (gr-dvbs2rx based).
#   --gui       Force open in GNU Radio Companion instead of running headless.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

GRC_PLAIN="$REPO_ROOT/grc/rx_dvbt2_445_5MHz.grc"
GRC_GRBLOCKS="$REPO_ROOT/grc/rx_dvbt2_grblocks_445_5MHz.grc"
GRC_FILE="$GRC_PLAIN"

USE_GRBLOCKS=false
FORCE_GUI=false

for arg in "$@"; do
    case "$arg" in
        --grblocks) USE_GRBLOCKS=true ;;
        --gui)      FORCE_GUI=true    ;;
        *)          echo "[WARN] Unknown argument: $arg" ;;
    esac
done

if $USE_GRBLOCKS; then
    GRC_FILE="$GRC_GRBLOCKS"
    echo "[INFO] Using gr-blocks RX variant: $GRC_FILE"
else
    echo "[INFO] Using standard RX: $GRC_FILE"
fi

if [[ ! -f "$GRC_FILE" ]]; then
    echo "[ERROR] GRC file not found: $GRC_FILE"
    exit 1
fi

if ! $FORCE_GUI && command -v grcc &>/dev/null; then
    PY_OUT="$REPO_ROOT/grc/rx_dvbt2_445_5MHz.py"
    echo "[INFO] Compiling flowgraph with grcc…"
    grcc -o "$REPO_ROOT/grc" "$GRC_FILE"
    echo "[INFO] Executing…"
    echo "[INFO] RX output → udp://127.0.0.1:5006  (VLC: udp://@127.0.0.1:5006)"
    exec python3 "$PY_OUT"
fi

if command -v gnuradio-companion &>/dev/null; then
    echo "[INFO] grcc not found — opening in GNU Radio Companion."
    exec gnuradio-companion "$GRC_FILE"
fi

echo "[ERROR] Neither grcc nor gnuradio-companion found."
echo "        Install GNU Radio 3.10+: https://www.gnuradio.org/blog/3-10-0-release/"
exit 1
