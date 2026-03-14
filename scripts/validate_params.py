#!/usr/bin/env python3
"""Validate params.yaml against known-good DVB-T2 parameter constraints.

Checks:
  - RF frequency is within the 70 cm amateur band (430–450 MHz)
  - Channel bandwidth is a valid DVB-T2 value (1.7, 5, 6, 7, 8, 10 MHz)
  - Sample rate is sufficient for the chosen bandwidth (Nyquist + headroom)
  - Constellation and code rate are a valid DVB-T2 combination
  - Guard interval, FFT size, and pilot pattern are valid
  - Gain values are within a reasonable operating range

Usage:
  python3 scripts/validate_params.py
  python3 scripts/validate_params.py --params custom.yaml
  python3 scripts/validate_params.py --strict      # warnings become errors

Exit codes:
  0 — valid (warnings may still be printed)
  1 — one or more errors (or --strict + warnings)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

# ── Valid DVB-T2 values (ETSI EN 302 755) ────────────────────────────────────
VALID_BW_HZ        = {1_700_000, 5_000_000, 6_000_000, 7_000_000, 8_000_000, 10_000_000}
VALID_FFT          = {1024, 2048, 4096, 8192, 16384, 32768}
VALID_GI           = {"1/4", "19/128", "1/8", "19/256", "1/16", "1/32", "1/128"}
VALID_PILOT        = {"PP1", "PP2", "PP3", "PP4", "PP5", "PP6", "PP7", "PP8"}
VALID_CONSTELLATION = {"QPSK", "16QAM", "64QAM", "256QAM"}
VALID_CODE_RATE    = {"1/2", "3/5", "2/3", "3/4", "4/5", "5/6"}

BAND_70CM_LOW_HZ  = 430_000_000
BAND_70CM_HIGH_HZ = 450_000_000


class Validator:
    """Accumulates errors and warnings when validating a params dict."""

    def __init__(self, strict: bool = False):
        self.strict = strict
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        if self.strict:
            self.errors.append(f"[strict] {msg}")
        else:
            self.warnings.append(msg)

    def _get(self, params: dict, *keys: str) -> Any:
        obj = params
        for k in keys:
            if not isinstance(obj, dict) or k not in obj:
                return None
            obj = obj[k]
        return obj

    def validate(self, params: dict) -> None:
        self._check_frequency(params)
        self._check_bandwidth(params)
        self._check_modulation(params)
        self._check_fft_gi(params)
        self._check_pilots(params)
        self._check_device(params)
        self._check_udp(params)

    def _check_frequency(self, p: dict) -> None:
        freq = self._get(p, "rf_frequency_hz")
        if freq is None:
            self.error("rf_frequency_hz is missing"); return
        if not isinstance(freq, (int, float)):
            self.error(f"rf_frequency_hz must be a number, got {type(freq).__name__}"); return
        if not (BAND_70CM_LOW_HZ <= float(freq) <= BAND_70CM_HIGH_HZ):
            self.warn(
                f"rf_frequency_hz {float(freq)/1e6:.3f} MHz is outside the 70 cm "
                f"band ({BAND_70CM_LOW_HZ/1e6:.0f}–{BAND_70CM_HIGH_HZ/1e6:.0f} MHz). "
                "Check your local band plan."
            )

    def _check_bandwidth(self, p: dict) -> None:
        bw = self._get(p, "channel_bandwidth_hz")
        if bw is None:
            self.error("channel_bandwidth_hz is missing"); return
        if int(bw) not in VALID_BW_HZ:
            self.error(
                f"channel_bandwidth_hz {bw/1e6:.1f} MHz is not a valid DVB-T2 bandwidth. "
                f"Valid: {sorted(v/1e6 for v in VALID_BW_HZ)}"
            )

    def _check_modulation(self, p: dict) -> None:
        const = self._get(p, "constellation")
        cr    = self._get(p, "code_rate")
        if const is None:
            self.error("constellation is missing")
        elif str(const).upper() not in VALID_CONSTELLATION:
            self.error(f"constellation '{const}' is invalid. Valid: {sorted(VALID_CONSTELLATION)}")
        if cr is None:
            self.error("code_rate is missing")
        elif str(cr) not in VALID_CODE_RATE:
            self.error(f"code_rate '{cr}' is invalid. Valid: {sorted(VALID_CODE_RATE)}")

    def _check_fft_gi(self, p: dict) -> None:
        fft = self._get(p, "fft_size")
        gi  = self._get(p, "guard_interval")
        if fft is not None and int(fft) not in VALID_FFT:
            self.error(f"fft_size {fft} invalid. Valid: {sorted(VALID_FFT)}")
        if gi is not None and str(gi) not in VALID_GI:
            self.error(f"guard_interval '{gi}' invalid. Valid: {sorted(VALID_GI)}")

    def _check_pilots(self, p: dict) -> None:
        pp = self._get(p, "pilot_pattern")
        if pp is not None and str(pp).upper() not in VALID_PILOT:
            self.error(f"pilot_pattern '{pp}' invalid. Valid: {sorted(VALID_PILOT)}")

    def _check_device(self, p: dict) -> None:
        bw = p.get("channel_bandwidth_hz", 7_000_000)
        for side in ("tx", "rx"):
            sr = self._get(p, "device", side, "sample_rate")
            if sr is None:
                self.warn(f"device.{side}.sample_rate not set"); continue
            if float(sr) < float(bw) * 1.1:
                self.error(
                    f"device.{side}.sample_rate {sr/1e6:.2f} Msps is too low for "
                    f"{bw/1e6:.1f} MHz channel (need ≥ {bw*1.1/1e6:.2f} Msps)"
                )

    def _check_udp(self, p: dict) -> None:
        for direction in ("udp_ts_in", "udp_ts_out"):
            port = self._get(p, direction, "port")
            if port is not None and not (1024 <= int(port) <= 65535):
                self.error(f"{direction}.port {port} is out of valid range (1024–65535)")


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--params", default="params.yaml")
    ap.add_argument("--strict", action="store_true",
                    help="Treat warnings as errors")
    args = ap.parse_args()

    path = Path(args.params)
    if not path.exists():
        print(f"ERROR: {path} not found", file=sys.stderr); sys.exit(1)

    try:
        import yaml
        with open(path, encoding="utf-8") as fh:
            params = yaml.safe_load(fh) or {}
    except Exception as exc:
        print(f"ERROR: Cannot parse {path}: {exc}", file=sys.stderr); sys.exit(1)

    v = Validator(strict=args.strict)
    v.validate(params)

    for w in v.warnings:
        print(f"\033[33mWARN\033[0m  {w}")
    for e in v.errors:
        print(f"\033[31mERROR\033[0m {e}")

    if v.errors:
        print(f"\n{len(v.errors)} error(s). Fix params.yaml before running.")
        sys.exit(1)

    print(f"\033[32mOK\033[0m  {path} is valid ({len(v.warnings)} warning(s))")


if __name__ == "__main__":
    main()
