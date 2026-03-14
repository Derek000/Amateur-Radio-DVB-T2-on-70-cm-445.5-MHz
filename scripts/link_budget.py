#!/usr/bin/env python3
"""DVB-T2 70 cm (445.5 MHz) amateur radio link budget calculator.

Computes path loss, received signal level, noise floor, C/N, and reports
the link margin against the DVB-T2 quasi-error-free (QEF) threshold.

Defaults are based on the params.yaml configuration (QPSK, CR 1/2, 7 MHz BW).

Usage
-----
    python3 scripts/link_budget.py --distance 5 --tx-power 5 --tx-gain 10
    python3 scripts/link_budget.py --from-params params.yaml --distance 5
    python3 scripts/link_budget.py --help
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import Optional

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


# ---------------------------------------------------------------------------
# DVB-T2 QEF C/N thresholds  (ETSI EN 302 755 / ETSI TR 101 290)
# These are minimum C/N at the decoder input for QEF (BER < 1e-7).
# ---------------------------------------------------------------------------
QEF_CN_DB: dict[str, dict[str, float]] = {
    "QPSK": {"1/2": 3.1, "2/3": 5.9, "3/4": 7.2, "5/6": 8.5},
    "16QAM": {"1/2": 8.7, "2/3": 11.4, "3/4": 12.9, "5/6": 14.3},
    "64QAM": {"1/2": 14.3, "2/3": 17.3, "3/4": 19.0, "5/6": 20.5},
}
# Practical amateur target: QEF + 10 dB implementation margin
PRACTICAL_MARGIN_DB = 10.0


# ---------------------------------------------------------------------------
# RF maths
# ---------------------------------------------------------------------------

def free_space_path_loss_db(distance_km: float, frequency_mhz: float) -> float:
    """Friis free-space path loss (dB).

    FSPL = 20·log₁₀(d) + 20·log₁₀(f) + 92.45
    where d is in km and f in GHz (here converted from MHz).
    """
    f_ghz = frequency_mhz / 1000.0
    return 20 * math.log10(distance_km) + 20 * math.log10(f_ghz) + 92.45


def noise_floor_dbm(bandwidth_hz: float, noise_figure_db: float) -> float:
    """Receiver noise floor in dBm.

    N = kTB + NF  where T = 290 K, k = 1.380649e-23 J/K.
    """
    k = 1.380649e-23
    t = 290.0
    ktb_dbm = 10 * math.log10(k * t * bandwidth_hz) + 30  # dBm
    return ktb_dbm + noise_figure_db


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def run_budget(
    distance_km: float,
    tx_power_dbm: float,
    tx_gain_dbi: float,
    rx_gain_dbi: float,
    tx_loss_db: float,
    rx_loss_db: float,
    frequency_mhz: float,
    bandwidth_hz: float,
    noise_figure_db: float,
    constellation: str,
    code_rate: str,
) -> int:
    fspl = free_space_path_loss_db(distance_km, frequency_mhz)
    eirp_dbm = tx_power_dbm + tx_gain_dbi - tx_loss_db
    rx_signal_dbm = eirp_dbm - fspl + rx_gain_dbi - rx_loss_db
    noise_dbm = noise_floor_dbm(bandwidth_hz, noise_figure_db)
    cn_db = rx_signal_dbm - noise_dbm

    const_upper = constellation.upper()
    qef = QEF_CN_DB.get(const_upper, {}).get(code_rate)
    if qef is None:
        print(
            f"[WARN] No QEF threshold for {const_upper} / CR {code_rate}. "
            "Using QPSK 1/2 fallback.",
            file=sys.stderr,
        )
        qef = 3.1

    margin = cn_db - qef
    practical_margin = cn_db - (qef + PRACTICAL_MARGIN_DB)

    # -----------------------------------------------------------------------
    # Output
    # -----------------------------------------------------------------------
    W = 54  # column width

    def row(label: str, value: str) -> None:
        print(f"  {label:<30} {value}")

    def sep() -> None:
        print("  " + "─" * (W - 2))

    print()
    print("  " + "═" * (W - 2))
    print(f"  DVB-T2 Link Budget — {frequency_mhz:.1f} MHz / 70 cm")
    print("  " + "═" * (W - 2))
    print()
    print("  ── Transmitter ──────────────────────────────")
    row("TX power",         f"{tx_power_dbm:.1f} dBm")
    row("TX antenna gain",  f"+{tx_gain_dbi:.1f} dBi")
    row("TX cable / filter loss", f"-{tx_loss_db:.1f} dB")
    row("EIRP",             f"{eirp_dbm:.1f} dBm")
    print()
    print("  ── Path ─────────────────────────────────────")
    row("Distance",         f"{distance_km:.1f} km")
    row("Frequency",        f"{frequency_mhz:.1f} MHz")
    row("Free-space path loss", f"-{fspl:.1f} dB")
    print()
    print("  ── Receiver ─────────────────────────────────")
    row("RX antenna gain",  f"+{rx_gain_dbi:.1f} dBi")
    row("RX cable / filter loss", f"-{rx_loss_db:.1f} dB")
    row("Received signal",  f"{rx_signal_dbm:.1f} dBm")
    print()
    print("  ── Noise ────────────────────────────────────")
    row("Channel bandwidth", f"{bandwidth_hz/1e6:.1f} MHz")
    row("Noise figure",     f"{noise_figure_db:.1f} dB")
    row("Noise floor",      f"{noise_dbm:.1f} dBm")
    print()
    print("  ── Link quality ─────────────────────────────")
    row("C/N",              f"{cn_db:.1f} dB")
    row(f"QEF threshold ({const_upper} CR {code_rate})", f"{qef:.1f} dB")
    row("QEF margin",       f"{margin:+.1f} dB  {'✓ PASS' if margin >= 0 else '✗ FAIL'}")
    row("Practical margin (QEF+10 dB)",
        f"{practical_margin:+.1f} dB  {'✓ PASS' if practical_margin >= 0 else '⚠ MARGINAL'}")
    print()

    if margin < 0:
        print(f"  ✗ LINK CLOSED: {abs(margin):.1f} dB short of QEF threshold.")
        print("    → Reduce distance, increase TX power, or improve antenna gain.")
        return 1
    if practical_margin < 0:
        print(f"  ⚠ LINK MARGINAL: achieves QEF but lacks the recommended 10 dB margin.")
        print("    → Consider better antenna or shorter path for reliable operation.")
        return 0
    print(f"  ✓ LINK ROBUST: {practical_margin:.1f} dB above practical target.")
    print()
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--from-params", metavar="YAML",
                    help="Load frequency/BW/constellation/code_rate from params.yaml")

    ap.add_argument("--distance",    type=float, required=True,
                    help="Path distance in km (required)")
    ap.add_argument("--tx-power",    type=float, default=10.0,
                    help="TX power in dBm (default: 10 dBm = 10 mW)")
    ap.add_argument("--tx-gain",     type=float, default=0.0,
                    help="TX antenna gain in dBi (default: 0 = isotropic)")
    ap.add_argument("--rx-gain",     type=float, default=6.0,
                    help="RX antenna gain in dBi (default: 6 dBi)")
    ap.add_argument("--tx-loss",     type=float, default=1.0,
                    help="TX cable/filter loss in dB (default: 1 dB)")
    ap.add_argument("--rx-loss",     type=float, default=1.0,
                    help="RX cable/filter loss in dB (default: 1 dB)")
    ap.add_argument("--noise-figure", type=float, default=6.0,
                    help="RX noise figure in dB (default: 6 dB)")

    # RF params (overridden by --from-params)
    ap.add_argument("--frequency",    type=float, default=445.5,
                    help="Carrier frequency in MHz (default: 445.5)")
    ap.add_argument("--bandwidth",    type=float, default=7.0,
                    help="Channel bandwidth in MHz (default: 7.0)")
    ap.add_argument("--constellation", default="QPSK",
                    choices=["QPSK", "16QAM", "64QAM"],
                    help="Modulation (default: QPSK)")
    ap.add_argument("--code-rate",    default="1/2",
                    choices=["1/2", "2/3", "3/4", "5/6"],
                    help="Code rate (default: 1/2)")
    return ap


def main() -> int:
    args = build_parser().parse_args()

    frequency_mhz = args.frequency
    bandwidth_hz = args.bandwidth * 1e6
    constellation = args.constellation
    code_rate = args.code_rate

    if args.from_params:
        if not HAS_YAML:
            print("[ERROR] PyYAML is required for --from-params. Install: pip install pyyaml",
                  file=sys.stderr)
            return 1
        path = Path(args.from_params)
        if not path.exists():
            print(f"[ERROR] File not found: {path}", file=sys.stderr)
            return 1
        with path.open("r", encoding="utf-8") as fh:
            p = yaml.safe_load(fh)
        frequency_mhz = p.get("rf_frequency_hz", 445_500_000) / 1e6
        bandwidth_hz = float(p.get("channel_bandwidth_hz", 7_000_000))
        constellation = p.get("constellation", "QPSK")
        code_rate = p.get("code_rate", "1/2")

    return run_budget(
        distance_km=args.distance,
        tx_power_dbm=args.tx_power,
        tx_gain_dbi=args.tx_gain,
        rx_gain_dbi=args.rx_gain,
        tx_loss_db=args.tx_loss,
        rx_loss_db=args.rx_loss,
        frequency_mhz=frequency_mhz,
        bandwidth_hz=bandwidth_hz,
        noise_figure_db=args.noise_figure,
        constellation=constellation,
        code_rate=code_rate,
    )


if __name__ == "__main__":
    sys.exit(main())
