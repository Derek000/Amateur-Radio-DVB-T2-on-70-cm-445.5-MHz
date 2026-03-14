#!/usr/bin/env python3
"""GNU Radio embedded Python block: MER / EVM logger.

Inserts into a complex IQ stream (GNU Radio sync_block), accumulates
*window* samples, computes Modulation Error Ratio (MER) and Error Vector
Magnitude (EVM), then appends a row to a CSV file.

Supported constellations: QPSK, 16-QAM, 64-QAM.

CSV columns
-----------
ts_unix       : POSIX timestamp (float)
samples       : number of samples in the measurement window
constellation : constellation label string
evm_pct       : EVM as % of reference RMS amplitude
mer_db        : MER in dB (20·log10(signal/error))
"""

from __future__ import annotations

import csv
import logging
import time
from pathlib import Path
from typing import List

import numpy as np

from gnuradio import gr

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constellation helpers
# ---------------------------------------------------------------------------

def _normalise(grid: np.ndarray) -> np.ndarray:
    """Return *grid* scaled to unit average power."""
    return grid / np.sqrt(np.mean(np.abs(grid) ** 2))


def ref_points(constellation: str = "qpsk") -> np.ndarray:
    """Return normalised reference constellation points.

    Parameters
    ----------
    constellation:
        One of ``"qpsk"``, ``"16qam"``, or ``"64qam"`` (case-insensitive).

    Returns
    -------
    np.ndarray of np.complex64

    Raises
    ------
    ValueError
        If *constellation* is not recognised.
    """
    c = constellation.lower().replace("-", "")

    if c == "qpsk":
        angles = np.array([np.pi / 4, 3 * np.pi / 4, 5 * np.pi / 4, 7 * np.pi / 4])
        return np.exp(1j * angles).astype(np.complex64)

    if c == "16qam":
        a = np.array([-3.0, -1.0, 1.0, 3.0])
        grid = np.array([x + 1j * y for x in a for y in a], dtype=np.complex64)
        return _normalise(grid)

    if c == "64qam":
        a = np.array([-7.0, -5.0, -3.0, -1.0, 1.0, 3.0, 5.0, 7.0])
        grid = np.array([x + 1j * y for x in a for y in a], dtype=np.complex64)
        return _normalise(grid)

    raise ValueError(
        f"Unsupported constellation '{constellation}'. "
        "Choose from: qpsk, 16qam, 64qam."
    )


def hard_decide(symbols: np.ndarray, ref: np.ndarray, chunk: int = 4096) -> np.ndarray:
    """Return nearest reference point for every sample in *symbols*.

    Uses a chunked loop to bound peak memory usage.

    Parameters
    ----------
    symbols : np.ndarray
        Complex IQ samples to classify.
    ref : np.ndarray
        Reference constellation points.
    chunk : int
        Chunk size for the distance computation.

    Returns
    -------
    np.ndarray of np.complex64
    """
    out = np.empty_like(symbols, dtype=np.complex64)
    for i in range(0, len(symbols), chunk):
        seg = symbols[i : i + chunk]
        dist_sq = np.abs(seg[:, None] - ref[None, :]) ** 2
        out[i : i + chunk] = ref[np.argmin(dist_sq, axis=1)]
    return out


# ---------------------------------------------------------------------------
# GNU Radio block
# ---------------------------------------------------------------------------

class mer_evm_logger(gr.sync_block):
    """Measure MER and EVM on a DVB-T2 IQ stream and log to CSV.

    Parameters
    ----------
    csv_path : str
        Output CSV file path.  Parent directories are created automatically.
        A bare filename (no directory component) is resolved relative to the
        current working directory — the parent will be created if needed.
    window : int
        Samples to accumulate per MER/EVM measurement (minimum 256).
    constellation : str
        Modulation scheme: ``"qpsk"``, ``"16qam"``, or ``"64qam"``.
    """

    def __init__(
        self,
        csv_path: str = "metrics/tx_metrics.csv",
        window: int = 4096,
        constellation: str = "qpsk",
    ) -> None:
        gr.sync_block.__init__(
            self,
            name="mer_evm_logger",
            in_sig=[np.complex64],
            out_sig=[np.complex64],
        )

        self.constellation = constellation.lower()
        self.ref = ref_points(self.constellation)
        self.window = max(256, int(window))
        self._buf = np.zeros(self.window, dtype=np.complex64)
        self._idx: int = 0

        # Resolve to an absolute path so that relative/bare filenames work
        # regardless of where GNU Radio changes the working directory.
        resolved = Path(csv_path).resolve()
        resolved.parent.mkdir(parents=True, exist_ok=True)
        self.csv_path = str(resolved)

        # Write CSV header only when starting a fresh file.
        if not resolved.exists():
            with open(self.csv_path, "w", newline="", encoding="utf-8") as fh:
                csv.writer(fh).writerow(
                    ["ts_unix", "samples", "constellation", "evm_pct", "mer_db"]
                )

        log.info(
            "mer_evm_logger ready — window=%d  constellation=%s  csv=%s",
            self.window,
            self.constellation,
            self.csv_path,
        )

    # ------------------------------------------------------------------

    def _compute_and_log(self) -> None:
        """Compute MER/EVM for the accumulated buffer and append one CSV row."""
        r = hard_decide(self._buf, self.ref)
        err = self._buf - r

        evm_rms = float(np.sqrt(np.mean(np.abs(err) ** 2)))
        ref_rms = float(np.sqrt(np.mean(np.abs(r) ** 2))) + 1e-12

        evm_pct = 100.0 * evm_rms / ref_rms
        mer_db = 20.0 * np.log10(ref_rms / max(evm_rms, 1e-12))

        try:
            with open(self.csv_path, "a", newline="", encoding="utf-8") as fh:
                csv.writer(fh).writerow(
                    [
                        f"{time.time():.3f}",
                        self.window,
                        self.constellation,
                        f"{evm_pct:.3f}",
                        f"{mer_db:.3f}",
                    ]
                )
        except OSError as exc:
            log.error("mer_evm_logger: failed writing CSV: %s", exc)

    # ------------------------------------------------------------------

    def work(
        self,
        input_items: List[np.ndarray],
        output_items: List[np.ndarray],
    ) -> int:
        x: np.ndarray = input_items[0]
        output_items[0][:] = x  # transparent pass-through
        n = len(x)
        if n == 0:
            return 0

        start = 0
        while start < n:
            take = min(self.window - self._idx, n - start)
            self._buf[self._idx : self._idx + take] = x[start : start + take]
            self._idx += take
            start += take
            if self._idx == self.window:
                self._compute_and_log()
                self._idx = 0

        return n
