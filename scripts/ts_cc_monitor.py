#!/usr/bin/env python3
"""MPEG-TS continuity counter (CC) monitor.

Watches a UDP stream or reads from a file/stdin and reports sync errors and
continuity counter discontinuities — useful for verifying end-to-end DVB-T2
transport stream integrity.

Usage
-----
    # Live UDP monitoring (output refreshes in-place):
    python3 scripts/ts_cc_monitor.py --udp 127.0.0.1:5006

    # With PID filter (e.g. PMT on PID 0x0100 = 256):
    python3 scripts/ts_cc_monitor.py --udp 127.0.0.1:5006 --pid 256

    # From a captured file:
    python3 scripts/ts_cc_monitor.py --file capture.ts

    # From stdin:
    cat capture.ts | python3 scripts/ts_cc_monitor.py
"""

from __future__ import annotations

import argparse
import socket
import sys
import time
from pathlib import Path
from typing import Dict, Optional

TS_PACKET_SIZE = 188
SYNC_BYTE = 0x47


# ---------------------------------------------------------------------------
# Packet parsing
# ---------------------------------------------------------------------------

class TsStats:
    """Accumulates packet statistics across multiple parse calls."""

    def __init__(self) -> None:
        self.total_packets: int = 0
        self.sync_errors: int = 0
        self.cc_errors: int = 0
        self._cc_state: Dict[int, int] = {}  # PID → last CC

    def feed(self, data: bytes, pid_filter: Optional[int] = None) -> None:
        """Parse all complete 188-byte packets in *data*."""
        i = 0
        while i + TS_PACKET_SIZE <= len(data):
            pkt = data[i : i + TS_PACKET_SIZE]
            i += TS_PACKET_SIZE
            self.total_packets += 1

            if pkt[0] != SYNC_BYTE:
                self.sync_errors += 1
                continue

            pid = ((pkt[1] & 0x1F) << 8) | pkt[2]
            cc = pkt[3] & 0x0F

            # Skip null packets (PID 0x1FFF) — they carry no payload
            if pid == 0x1FFF:
                continue

            if pid_filter is not None and pid != pid_filter:
                continue

            last = self._cc_state.get(pid)
            if last is not None and ((last + 1) & 0x0F) != cc:
                self.cc_errors += 1
            self._cc_state[pid] = cc

    @property
    def error_rate(self) -> float:
        """CC error rate as a fraction (0–1)."""
        if self.total_packets == 0:
            return 0.0
        return self.cc_errors / self.total_packets

    def summary_line(self) -> str:
        return (
            f"pkts={self.total_packets:>8,}  "
            f"sync_errs={self.sync_errors:>5,}  "
            f"cc_errs={self.cc_errors:>5,}  "
            f"cc_err_rate={self.error_rate:.4%}"
        )


# ---------------------------------------------------------------------------
# Input modes
# ---------------------------------------------------------------------------

def run_udp(host: str, port: int, pid_filter: Optional[int], interval: float) -> None:
    """Monitor a live UDP transport stream, printing stats periodically."""
    stats = TsStats()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind((host, port))
        sock.settimeout(1.0)
    except OSError as exc:
        print(f"[ERROR] Cannot bind to {host}:{port}: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"[INFO] Listening on {host}:{port} (Ctrl-C to stop)…", flush=True)
    last_print = time.monotonic()

    try:
        while True:
            try:
                data, _ = sock.recvfrom(65535)
            except socket.timeout:
                continue
            stats.feed(data, pid_filter)

            now = time.monotonic()
            if now - last_print >= interval:
                print(f"\r{stats.summary_line()}", end="", flush=True)
                last_print = now

    except KeyboardInterrupt:
        print(f"\n{stats.summary_line()}")
        print("[INFO] Stopped by user.")
    finally:
        sock.close()


def run_file(path: Optional[Path], pid_filter: Optional[int]) -> None:
    """Parse a file (or stdin) and print a final summary."""
    if path is not None:
        if not path.exists():
            print(f"[ERROR] File not found: {path}", file=sys.stderr)
            sys.exit(1)
        data = path.read_bytes()
    else:
        data = sys.stdin.buffer.read()

    stats = TsStats()
    stats.feed(data, pid_filter)
    print(stats.summary_line())


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    source = ap.add_mutually_exclusive_group()
    source.add_argument(
        "--udp", metavar="HOST:PORT",
        help="Listen on a UDP socket (e.g. 127.0.0.1:5006)",
    )
    source.add_argument(
        "--file", metavar="PATH",
        help="Read from a captured .ts file (omit to read stdin)",
    )
    ap.add_argument(
        "--pid", type=lambda s: int(s, 0), default=None,
        help="Filter to a single PID (decimal or 0x hex, default: all PIDs)",
    )
    ap.add_argument(
        "--interval", type=float, default=1.0, metavar="SEC",
        help="Stats print interval in seconds for UDP mode (default: 1.0)",
    )
    return ap


def main() -> int:
    args = build_parser().parse_args()

    if args.udp:
        try:
            host, port_str = args.udp.rsplit(":", 1)
            port = int(port_str)
        except ValueError:
            print(
                f"[ERROR] Invalid --udp value '{args.udp}'. "
                "Expected HOST:PORT, e.g. 127.0.0.1:5006.",
                file=sys.stderr,
            )
            return 1
        run_udp(host, port, args.pid, args.interval)
    else:
        file_path = Path(args.file) if args.file else None
        run_file(file_path, args.pid)

    return 0


if __name__ == "__main__":
    sys.exit(main())
