#!/usr/bin/env python3
"""Live terminal dashboard for DVB-T2 TX metrics.

Reads the MER/EVM CSV produced by ``grc/blocks/mer_evm_logger.py`` and
displays a live-updating dashboard in the terminal using Rich.

Requires: pip install rich

Usage
-----
    python3 scripts/status_monitor.py
    python3 scripts/status_monitor.py --csv metrics/tx_metrics.csv --interval 2
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path
from typing import List, NamedTuple, Optional

try:
    from rich import box
    from rich.columns import Columns
    from rich.console import Console
    from rich.layout import Layout
    from rich.live import Live
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    HAS_RICH = True
except ImportError:
    HAS_RICH = False


# ---------------------------------------------------------------------------
# MER/EVM thresholds (same as plot_metrics.py)
# ---------------------------------------------------------------------------
MER_QMIN: dict[str, float]    = {"qpsk": 3.1,  "16qam": 8.7,  "64qam": 14.3}
MER_TARGET: dict[str, float]  = {"qpsk": 14.0, "16qam": 20.0, "64qam": 26.0}
EVM_LIMIT: dict[str, float]   = {"qpsk": 8.0,  "16qam": 4.0,  "64qam": 2.0}


class MetricRow(NamedTuple):
    ts_unix: float
    samples: int
    constellation: str
    evm_pct: float
    mer_db: float


# ---------------------------------------------------------------------------
# CSV reader (tail-safe: reads only last N rows)
# ---------------------------------------------------------------------------

def read_last_rows(csv_path: Path, n: int = 200) -> List[MetricRow]:
    """Return the last *n* data rows from the CSV, oldest first."""
    if not csv_path.exists():
        return []
    rows: List[MetricRow] = []
    try:
        with csv_path.open("r", newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for raw in reader:
                try:
                    rows.append(MetricRow(
                        ts_unix=float(raw["ts_unix"]),
                        samples=int(raw.get("samples", 4096)),
                        constellation=raw["constellation"].lower(),
                        evm_pct=float(raw["evm_pct"]),
                        mer_db=float(raw["mer_db"]),
                    ))
                except (KeyError, ValueError):
                    continue
    except OSError:
        return []
    return rows[-n:]


# ---------------------------------------------------------------------------
# Dashboard rendering
# ---------------------------------------------------------------------------

def _status_colour(mer: float, constellation: str) -> str:
    target = MER_TARGET.get(constellation, 14.0)
    qmin   = MER_QMIN.get(constellation, 3.1)
    if mer >= target:
        return "green"
    if mer >= qmin:
        return "yellow"
    return "red"


def _mer_bar(mer: float, constellation: str, width: int = 20) -> str:
    """Return a Unicode progress bar for MER level."""
    target = MER_TARGET.get(constellation, 14.0)
    fraction = min(1.0, max(0.0, mer / (target * 1.2)))
    filled = int(fraction * width)
    return "█" * filled + "░" * (width - filled)


def build_dashboard(rows: List[MetricRow], csv_path: str, interval: float) -> Panel:
    """Build the Rich panel to display."""
    if not rows:
        return Panel(
            Text("Waiting for data…\nStart the TX flowgraph with the metrics block.",
                 style="yellow"),
            title="DVB-T2 Status Monitor",
            border_style="yellow",
        )

    recent = rows[-1]
    all_rows = rows

    # Compute rolling stats (last 30 windows ≈ ~30 s at 4096 samples/4 Msps)
    tail = rows[-30:]
    avg_mer = sum(r.mer_db  for r in tail) / len(tail)
    avg_evm = sum(r.evm_pct for r in tail) / len(tail)
    min_mer = min(r.mer_db  for r in all_rows)
    max_mer = max(r.mer_db  for r in all_rows)

    c = recent.constellation
    colour = _status_colour(avg_mer, c)
    bar = _mer_bar(avg_mer, c)

    target_mer = MER_TARGET.get(c, 14.0)
    qmin_mer   = MER_QMIN.get(c, 3.1)
    evm_lim    = EVM_LIMIT.get(c, 8.0)

    status_text = "PASS ✓" if avg_mer >= target_mer else ("MARGINAL ⚠" if avg_mer >= qmin_mer else "FAIL ✗")

    # Latest reading panel
    latest_tbl = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    latest_tbl.add_column("Key", style="bold")
    latest_tbl.add_column("Val")
    latest_tbl.add_row("Constellation", c.upper())
    latest_tbl.add_row("Latest MER",  f"[{colour}]{recent.mer_db:.2f} dB[/{colour}]")
    latest_tbl.add_row("Latest EVM",  f"[{colour}]{recent.evm_pct:.2f}%[/{colour}]")
    latest_tbl.add_row("MER bar",     f"[{colour}]{bar}[/{colour}]")
    latest_tbl.add_row("Status",      f"[{colour}]{status_text}[/{colour}]")

    # Rolling stats panel
    stats_tbl = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    stats_tbl.add_column("Key", style="bold")
    stats_tbl.add_column("Val")
    stats_tbl.add_row("Avg MER (30 win)",    f"{avg_mer:.2f} dB")
    stats_tbl.add_row("Avg EVM (30 win)",    f"{avg_evm:.2f}%")
    stats_tbl.add_row("Session MER range",   f"{min_mer:.2f} – {max_mer:.2f} dB")
    stats_tbl.add_row("Total windows",       str(len(all_rows)))
    stats_tbl.add_row("MER target",          f"{target_mer:.1f} dB")
    stats_tbl.add_row("EVM limit",           f"{evm_lim:.1f}%")

    # History (last 8 rows)
    hist_tbl = Table(box=box.SIMPLE, show_header=True, padding=(0, 1))
    hist_tbl.add_column("Time (UTC)", style="dim", width=10)
    hist_tbl.add_column("MER (dB)", justify="right")
    hist_tbl.add_column("EVM (%)", justify="right")
    for r in rows[-8:]:
        t = time.strftime("%H:%M:%S", time.gmtime(r.ts_unix))
        mc = _status_colour(r.mer_db, r.constellation)
        hist_tbl.add_row(
            t,
            f"[{mc}]{r.mer_db:.2f}[/{mc}]",
            f"[{mc}]{r.evm_pct:.2f}[/{mc}]",
        )

    ts_str = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())

    layout = Layout()
    layout.split_column(
        Layout(Columns([Panel(latest_tbl, title="Current"), Panel(stats_tbl, title="Rolling (30 win)")]),
               name="top"),
        Layout(Panel(hist_tbl, title="Recent History"), name="hist"),
        Layout(Text(f"CSV: {csv_path}  |  Refresh: {interval:.0f}s  |  {ts_str}", style="dim"),
               name="footer", size=1),
    )

    return Panel(layout, title="[bold]DVB-T2 TX Status Monitor — 445.5 MHz[/bold]",
                 border_style=colour)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def run(csv_path: Path, interval: float) -> None:
    console = Console()

    with Live(console=console, refresh_per_second=4, screen=True) as live:
        while True:
            rows = read_last_rows(csv_path)
            panel = build_dashboard(rows, str(csv_path), interval)
            live.update(panel)
            time.sleep(interval)


def run_plain(csv_path: Path, interval: float) -> None:
    """Fallback plain-text output when Rich is not installed."""
    while True:
        rows = read_last_rows(csv_path)
        if rows:
            r = rows[-1]
            t = time.strftime("%H:%M:%S", time.gmtime(r.ts_unix))
            print(
                f"[{t}] {r.constellation.upper():6s}  "
                f"MER={r.mer_db:6.2f} dB  EVM={r.evm_pct:5.2f}%  "
                f"(n={len(rows)})",
                flush=True,
            )
        else:
            print(f"[{time.strftime('%H:%M:%S')}] Waiting for {csv_path}…", flush=True)
        time.sleep(interval)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--csv", default="metrics/tx_metrics.csv",
                    help="Metrics CSV path (default: metrics/tx_metrics.csv)")
    ap.add_argument("--interval", type=float, default=2.0,
                    help="Refresh interval in seconds (default: 2)")
    return ap


def main() -> int:
    args = build_parser().parse_args()
    csv_path = Path(args.csv)

    try:
        if HAS_RICH:
            run(csv_path, args.interval)
        else:
            print(
                "[WARN] Rich not installed — using plain-text output.\n"
                "       pip install rich   for the full dashboard.\n",
                file=sys.stderr,
            )
            run_plain(csv_path, args.interval)
    except KeyboardInterrupt:
        print("\nStopped.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
