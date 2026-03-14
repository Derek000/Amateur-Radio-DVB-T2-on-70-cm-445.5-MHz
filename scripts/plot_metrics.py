#!/usr/bin/env python3
"""Plot MER and EVM metrics and generate a professional HTML report.

Reads the CSV produced by ``grc/blocks/mer_evm_logger.py`` and writes:

* ``reports/mer_over_time.png``   — MER time-series per constellation
* ``reports/evm_over_time.png``   — EVM time-series per constellation
* ``reports/index.html``          — Self-contained HTML report

MER / EVM threshold guidance (QPSK, CR 1/2 for DVB-T2)
--------------------------------------------------------
QPSK   MER threshold ≈  3.1 dB (C/N required at quasi-error-free);
       practical target  ≥ 14 dB for comfortable operation.
16QAM  MER threshold ≈  8.7 dB; practical target ≥ 20 dB.
64QAM  MER threshold ≈ 14.3 dB; practical target ≥ 26 dB.

Usage
-----
    python3 scripts/plot_metrics.py --csv metrics/tx_metrics.csv --outdir reports
"""

from __future__ import annotations

import argparse
import html
import os
import sys
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

import matplotlib
matplotlib.use("Agg")  # non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd


# ---------------------------------------------------------------------------
# Threshold tables
# ---------------------------------------------------------------------------

# (minimum_useful, practical_target) MER thresholds in dB
MER_THRESHOLDS: Dict[str, Tuple[float, float]] = {
    "qpsk":  (3.1,  14.0),
    "16qam": (8.7,  20.0),
    "64qam": (14.3, 26.0),
}
# EVM pass threshold in % (lower is better; practical ≤ 8% for QPSK)
EVM_THRESHOLD_PCT: Dict[str, float] = {
    "qpsk":  8.0,
    "16qam": 4.0,
    "64qam": 2.0,
}

PLOT_STYLE = {
    "figure.facecolor": "white",
    "axes.facecolor": "#f9f9f9",
    "axes.grid": True,
    "grid.color": "#dddddd",
    "grid.linestyle": "-",
    "axes.spines.top": False,
    "axes.spines.right": False,
}


# ---------------------------------------------------------------------------
# Plotting helpers
# ---------------------------------------------------------------------------

def _configure_style() -> None:
    plt.rcParams.update(PLOT_STYLE)


def _date_axis(ax: plt.Axes) -> None:
    """Auto-format the x-axis as a readable timestamp."""
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, ha="right")


def plot_mer(df: pd.DataFrame, outdir: Path) -> Path:
    """Plot MER over time; annotate threshold lines."""
    _configure_style()
    fig, ax = plt.subplots(figsize=(10, 4))

    constellations = df["constellation"].str.lower().unique()
    for c in constellations:
        sub = df[df["constellation"].str.lower() == c]
        ax.plot(sub["ts"], sub["mer_db"], label=f"MER {c.upper()}", linewidth=1.2)
        if c in MER_THRESHOLDS:
            _, target = MER_THRESHOLDS[c]
            ax.axhline(target, linestyle="--", linewidth=0.8, alpha=0.6,
                       label=f"Target {c.upper()} ({target} dB)")

    ax.set_xlabel("Time (UTC)")
    ax.set_ylabel("MER (dB)")
    ax.set_title("Modulation Error Ratio over Time")
    ax.legend(loc="upper left", fontsize=8)
    _date_axis(ax)
    fig.tight_layout()

    out = outdir / "mer_over_time.png"
    fig.savefig(str(out), dpi=130)
    plt.close(fig)
    return out


def plot_evm(df: pd.DataFrame, outdir: Path) -> Path:
    """Plot EVM % over time; annotate threshold lines."""
    _configure_style()
    fig, ax = plt.subplots(figsize=(10, 4))

    constellations = df["constellation"].str.lower().unique()
    for c in constellations:
        sub = df[df["constellation"].str.lower() == c]
        ax.plot(sub["ts"], sub["evm_pct"], label=f"EVM {c.upper()}", linewidth=1.2)
        if c in EVM_THRESHOLD_PCT:
            thr = EVM_THRESHOLD_PCT[c]
            ax.axhline(thr, linestyle="--", linewidth=0.8, alpha=0.6,
                       label=f"Limit {c.upper()} ({thr}%)")

    ax.set_xlabel("Time (UTC)")
    ax.set_ylabel("EVM (%)")
    ax.set_title("Error Vector Magnitude over Time")
    ax.legend(loc="upper left", fontsize=8)
    _date_axis(ax)
    fig.tight_layout()

    out = outdir / "evm_over_time.png"
    fig.savefig(str(out), dpi=130)
    plt.close(fig)
    return out


# ---------------------------------------------------------------------------
# HTML report builder
# ---------------------------------------------------------------------------

_PASS = '<span class="badge pass">PASS</span>'
_FAIL = '<span class="badge fail">FAIL</span>'
_WARN = '<span class="badge warn">MARGINAL</span>'

_CSS = """
body { font-family: 'Segoe UI', Arial, sans-serif; max-width: 960px;
       margin: 40px auto; color: #222; background: #fff; }
h1   { color: #1a3a5c; border-bottom: 2px solid #1a3a5c; padding-bottom: 8px; }
h2   { color: #1a3a5c; margin-top: 2em; }
img  { max-width: 100%; border: 1px solid #ddd; border-radius: 4px;
       margin: 12px 0; }
table { border-collapse: collapse; width: 100%; margin: 1em 0; }
th    { background: #1a3a5c; color: #fff; padding: 8px 12px;
        text-align: left; }
td    { border: 1px solid #ddd; padding: 7px 12px; }
tr:nth-child(even) { background: #f5f7fa; }
.badge { display: inline-block; padding: 2px 10px; border-radius: 12px;
         font-size: 0.82em; font-weight: 700; letter-spacing: .03em; }
.pass  { background: #d4edda; color: #155724; }
.fail  { background: #f8d7da; color: #721c24; }
.warn  { background: #fff3cd; color: #856404; }
.meta  { color: #666; font-size: 0.9em; margin-bottom: 1.5em; }
.thr   { font-size: 0.85em; color: #555; }
"""

def _pass_fail_mer(mean_mer: float, constellation: str) -> str:
    c = constellation.lower()
    if c not in MER_THRESHOLDS:
        return ""
    minimum, target = MER_THRESHOLDS[c]
    if mean_mer >= target:
        return _PASS
    if mean_mer >= minimum:
        return _WARN
    return _FAIL


def _pass_fail_evm(mean_evm: float, constellation: str) -> str:
    c = constellation.lower()
    thr = EVM_THRESHOLD_PCT.get(c)
    if thr is None:
        return ""
    if mean_evm <= thr:
        return _PASS
    if mean_evm <= thr * 1.5:
        return _WARN
    return _FAIL


def build_html_report(
    df: pd.DataFrame,
    outdir: Path,
    csv_path: str,
    generated_at: str,
) -> Path:
    """Write the HTML report to *outdir/index.html*."""
    summary = (
        df.assign(constellation=df["constellation"].str.lower())
        .groupby("constellation")
        .agg(
            count=("mer_db", "count"),
            mer_mean=("mer_db", "mean"),
            mer_min=("mer_db", "min"),
            mer_max=("mer_db", "max"),
            evm_mean=("evm_pct", "mean"),
            evm_max=("evm_pct", "max"),
        )
        .reset_index()
    )

    # Build summary table rows
    rows = []
    for _, row in summary.iterrows():
        c = row["constellation"]
        pf_mer = _pass_fail_mer(row["mer_mean"], c)
        pf_evm = _pass_fail_evm(row["evm_mean"], c)
        thr_note = ""
        if c in MER_THRESHOLDS:
            mn, tgt = MER_THRESHOLDS[c]
            thr_note = f'<br><span class="thr">Min {mn} dB / Target {tgt} dB</span>'
        rows.append(
            f"<tr>"
            f"<td>{html.escape(c.upper())}</td>"
            f"<td>{int(row['count'])}</td>"
            f"<td>{row['mer_mean']:.2f} dB {pf_mer}{thr_note}</td>"
            f"<td>{row['mer_min']:.2f} dB</td>"
            f"<td>{row['mer_max']:.2f} dB</td>"
            f"<td>{row['evm_mean']:.2f}% {pf_evm}</td>"
            f"<td>{row['evm_max']:.2f}%</td>"
            f"</tr>"
        )
    table_rows = "\n".join(rows)

    # Duration
    duration_s = float(df["ts"].max().timestamp() - df["ts"].min().timestamp())
    duration_str = f"{int(duration_s // 60)} min {int(duration_s % 60)} s"

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>DVB-T2 MER / EVM Report — Amateur Radio 445.5 MHz</title>
  <style>{_CSS}</style>
</head>
<body>
  <h1>DVB-T2 MER / EVM Report</h1>
  <p class="meta">
    Source: <code>{html.escape(csv_path)}</code><br>
    Generated: {html.escape(generated_at)}<br>
    Measurement duration: {duration_str} &nbsp;|&nbsp;
    Total windows: {len(df):,}
  </p>

  <h2>MER over Time</h2>
  <img src="mer_over_time.png" alt="MER over time">

  <h2>EVM over Time</h2>
  <img src="evm_over_time.png" alt="EVM over time">

  <h2>Summary by Constellation</h2>
  <table>
    <thead>
      <tr>
        <th>Constellation</th>
        <th>Windows</th>
        <th>Mean MER</th>
        <th>Min MER</th>
        <th>Max MER</th>
        <th>Mean EVM</th>
        <th>Max EVM</th>
      </tr>
    </thead>
    <tbody>
{table_rows}
    </tbody>
  </table>

  <h2>Threshold Reference</h2>
  <table>
    <thead>
      <tr><th>Constellation</th><th>Min MER (dB)</th>
          <th>Target MER (dB)</th><th>EVM Limit (%)</th></tr>
    </thead>
    <tbody>
      <tr><td>QPSK</td>  <td>3.1</td>  <td>14.0</td> <td>8.0</td></tr>
      <tr><td>16-QAM</td><td>8.7</td>  <td>20.0</td> <td>4.0</td></tr>
      <tr><td>64-QAM</td><td>14.3</td> <td>26.0</td> <td>2.0</td></tr>
    </tbody>
  </table>

  <p class="meta">
    Amateur Radio DVB-T2 on 70 cm (445.5 MHz) — MIT Licence<br>
    PASS: mean MER ≥ practical target &nbsp;|&nbsp;
    MARGINAL: min threshold ≤ MER &lt; target &nbsp;|&nbsp;
    FAIL: MER below minimum threshold
  </p>
</body>
</html>
"""

    out = outdir / "index.html"
    with open(str(out), "w", encoding="utf-8") as fh:
        fh.write(html_content)
    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--csv", default="metrics/tx_metrics.csv",
                    help="Input metrics CSV (default: metrics/tx_metrics.csv)")
    ap.add_argument("--outdir", default="reports",
                    help="Output directory for plots and HTML (default: reports)")
    ap.add_argument("--open", action="store_true",
                    help="Open the generated HTML report in the default browser")
    return ap


def main() -> int:
    args = build_parser().parse_args()
    csv_path = Path(args.csv)
    outdir = Path(args.outdir)

    # Validate CSV
    if not csv_path.exists():
        print(f"[ERROR] CSV file not found: {csv_path}", file=sys.stderr)
        print(
            "  Run a TX session with the metrics variant first:\n"
            "  grc/tx_dvbt2_445_5MHz_with_metrics.grc",
            file=sys.stderr,
        )
        return 1

    try:
        df = pd.read_csv(str(csv_path))
    except Exception as exc:
        print(f"[ERROR] Failed to read CSV: {exc}", file=sys.stderr)
        return 1

    required = {"ts_unix", "mer_db", "evm_pct", "constellation"}
    missing = required - set(df.columns)
    if missing:
        print(f"[ERROR] CSV missing columns: {missing}", file=sys.stderr)
        return 1

    if df.empty:
        print("[ERROR] CSV contains no data rows.", file=sys.stderr)
        return 1

    df["ts"] = pd.to_datetime(df["ts_unix"], unit="s", utc=True)
    df["mer_db"] = pd.to_numeric(df["mer_db"], errors="coerce")
    df["evm_pct"] = pd.to_numeric(df["evm_pct"], errors="coerce")
    df = df.dropna(subset=["mer_db", "evm_pct"])

    outdir.mkdir(parents=True, exist_ok=True)
    generated_at = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())

    print(f"[INFO] Plotting {len(df):,} measurement windows…")
    plot_mer(df, outdir)
    plot_evm(df, outdir)
    report = build_html_report(df, outdir, str(csv_path), generated_at)

    print(f"[OK]  Report written to {report}")

    if args.open:
        import webbrowser
        webbrowser.open(report.resolve().as_uri())

    return 0


if __name__ == "__main__":
    sys.exit(main())
