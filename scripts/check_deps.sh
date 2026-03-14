#!/usr/bin/env bash
# check_deps.sh — Verify that all required tools and Python packages are
# available for the Amateur Radio DVB-T2 project.
#
# Usage:  ./scripts/check_deps.sh [--quiet]
#
# Exit codes:
#   0 — all required dependencies found
#   1 — one or more required dependencies missing

set -euo pipefail

QUIET=false
[[ "${1:-}" == "--quiet" ]] && QUIET=true

PASS=0; FAIL=0; WARN=0

_ok()   { ((PASS++)); $QUIET || printf "  [\033[32m OK \033[0m] %s\n" "$1"; }
_fail() { ((FAIL++)); printf "  [\033[31mFAIL\033[0m] %s\n" "$1"; }
_warn() { ((WARN++)); $QUIET || printf "  [\033[33mWARN\033[0m] %s\n" "$1"; }
_hdr()  { $QUIET || printf "\n\033[1m%s\033[0m\n" "$1"; }

# ── System tools ──────────────────────────────────────────────────────────────
_hdr "System tools"
for cmd in python3 ffmpeg grcc; do
  if command -v "$cmd" &>/dev/null; then _ok "$cmd $(command -v "$cmd")"
  else
    if [[ "$cmd" == "grcc" ]]; then _warn "$cmd (optional — required for headless TX/RX)"
    else _fail "$cmd not found"; fi
  fi
done

# GNU Radio version
if command -v python3 &>/dev/null; then
  GR_VER=$(python3 -c "import gnuradio; print(gnuradio.__version__)" 2>/dev/null || echo "")
  if [[ -n "$GR_VER" ]]; then _ok "GNU Radio $GR_VER"
  else _fail "gnuradio Python package not importable"; fi
fi

# ── gr-dvbt2 OOT ─────────────────────────────────────────────────────────────
_hdr "GNU Radio OOT modules"
for mod in dvbt2 dvbs2rx; do
  if python3 -c "import gnuradio.$mod" 2>/dev/null; then
    VER=$(python3 -c "import gnuradio.$mod as m; print(getattr(m,'__version__','?'))" 2>/dev/null)
    _ok "gnuradio.$mod $VER"
  else
    if [[ "$mod" == "dvbs2rx" ]]; then
      _warn "gnuradio.$mod not found (optional — needed for rx_dvbt2_grblocks flowgraph)"
    else
      _fail "gnuradio.$mod not found (required — build from https://github.com/drmpeg/gr-dvbt2)"
    fi
  fi
done

# ── Soapy / device drivers ────────────────────────────────────────────────────
_hdr "SDR device support"
if python3 -c "import SoapySDR" 2>/dev/null; then
  _ok "SoapySDR"
  # List available drivers
  DRIVERS=$(python3 -c "
import SoapySDR
devs = SoapySDR.Device.enumerate()
for d in devs:
    print('    Found device: ' + d.get('label','unknown'))
" 2>/dev/null || echo "    (no devices connected or driver error)")
  $QUIET || echo "$DRIVERS"
else
  _warn "SoapySDR Python bindings not found (needed for LimeSDR/PlutoSDR)"
fi

for pymod in iio; do
  if python3 -c "import $pymod" 2>/dev/null; then _ok "python3 $pymod (PlutoSDR libiio)"
  else _warn "python3 $pymod not found (optional — needed for PlutoSDR iio blocks)"; fi
done

# ── Python packages ───────────────────────────────────────────────────────────
_hdr "Python packages"
for pkg in yaml numpy pandas matplotlib; do
  if python3 -c "import $pkg" 2>/dev/null; then
    VER=$(python3 -c "import $pkg; print(getattr($pkg,'__version__','?'))" 2>/dev/null)
    _ok "$pkg $VER"
  else
    if [[ "$pkg" =~ ^(pandas|matplotlib)$ ]]; then
      _warn "$pkg not found (optional — needed for metrics plotting: pip install $pkg)"
    else
      _fail "$pkg not found (required: pip install pyyaml numpy)"
    fi
  fi
done

# ── Linters ───────────────────────────────────────────────────────────────────
_hdr "Code quality tools"
for cmd in shellcheck yamllint; do
  if command -v "$cmd" &>/dev/null; then _ok "$cmd"
  else _warn "$cmd not found (optional — used by: make lint)"; fi
done

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
printf "Summary: \033[32m%d OK\033[0m  \033[31m%d FAILED\033[0m  \033[33m%d WARNINGS\033[0m\n" \
  "$PASS" "$FAIL" "$WARN"

[[ $FAIL -eq 0 ]] || { echo "Run 'make deps' or see docs/INSTALL.md for setup instructions." >&2; exit 1; }
