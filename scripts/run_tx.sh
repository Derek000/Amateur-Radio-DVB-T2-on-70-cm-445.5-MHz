#!/usr/bin/env bash
# run_tx.sh — Compile and execute the DVB-T2 TX flowgraph.
#
# Compiles the GRC flowgraph to Python with grcc (if needed), then executes
# it.  Falls back to opening GNU Radio Companion if grcc is absent.
#
# Usage:
#   ./scripts/run_tx.sh [--metrics] [--gui]
#
# Options:
#   --metrics   Use the TX variant with the MER/EVM logger block.
#   --gui       Force open in GNU Radio Companion instead of running headless.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

GRC_PLAIN="$REPO_ROOT/grc/tx_dvbt2_445_5MHz.grc"
GRC_METRICS="$REPO_ROOT/grc/tx_dvbt2_445_5MHz_with_metrics.grc"
GRC_FILE="$GRC_PLAIN"

USE_METRICS=false
FORCE_GUI=false

for arg in "$@"; do
    case "$arg" in
        --metrics) USE_METRICS=true ;;
        --gui)     FORCE_GUI=true   ;;
        *)         echo "[WARN] Unknown argument: $arg" ;;
    esac
done

if $USE_METRICS; then
    GRC_FILE="$GRC_METRICS"
    echo "[INFO] Using TX+metrics variant: $GRC_FILE"
else
    echo "[INFO] Using standard TX: $GRC_FILE"
fi

if [[ ! -f "$GRC_FILE" ]]; then
    echo "[ERROR] GRC file not found: $GRC_FILE"
    exit 1
fi

# Try headless execution via grcc (preferred for remote/SSH use)
if ! $FORCE_GUI && command -v grcc &>/dev/null; then
    PY_OUT="$REPO_ROOT/grc/tx_dvbt2_445_5MHz.py"
    echo "[INFO] Compiling flowgraph with grcc…"
    grcc -o "$REPO_ROOT/grc" "$GRC_FILE"
    echo "[INFO] Executing…"
    exec python3 "$PY_OUT"
fi

# Fall back: open in GUI
if command -v gnuradio-companion &>/dev/null; then
    echo "[INFO] grcc not found — opening in GNU Radio Companion."
    exec gnuradio-companion "$GRC_FILE"
fi

echo "[ERROR] Neither grcc nor gnuradio-companion found."
echo "        Install GNU Radio 3.10+: https://www.gnuradio.org/blog/3-10-0-release/"
exit 1
