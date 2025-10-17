#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# MER/EVM logger with QPSK/16QAM/64QAM support
from gnuradio import gr
import numpy as np
import csv, os, time

CONST_MAP = {
    0: "qpsk",
    1: "16qam",
    2: "64qam",
}

def ref_points(constellation="qpsk"):
    c = constellation.lower()
    if c == "qpsk":
        # Unit circle QPSK
        ang = np.array([np.pi/4, 3*np.pi/4, 5*np.pi/4, 7*np.pi/4])
        return np.exp(1j*ang)
    if c == "16qam":
        # Normalised 16-QAM Gray-ish: points at {-3,-1,1,3} for I/Q normalised to avg power 1
        a = np.array([-3,-1,1,3], dtype=float)
        # Normalise so average power is 1
        # Unnormalised avg power for 16QAM = (2/16)*sum(a^2 over I)*(2/16)*sum(a^2 over Q)? Simpler: compute grid and scale.
        grid = np.array([x + 1j*y for x in a for y in a], dtype=np.complex64)
        avg_pow = np.mean(np.abs(grid)**2)
        grid /= np.sqrt(avg_pow)
        return grid
    if c == "64qam":
        # 64-QAM with levels {-7,-5,-3,-1,1,3,5,7}; normalise to avg power 1
        a = np.array([-7,-5,-3,-1,1,3,5,7], dtype=float)
        grid = np.array([x + 1j*y for x in a for y in a], dtype=np.complex64)
        avg_pow = np.mean(np.abs(grid)**2)
        grid /= np.sqrt(avg_pow)
        return grid
    raise ValueError("Unsupported constellation")

def hard_decide(s, ref):
    # Nearest-neighbour decision
    # For performance, vectorise using broadcasting: choose ref with min distance
    # s shape (N,), ref shape (M,)
    # returns nearest ref points for s
    # Use chunking for memory safety
    N = len(s); M = len(ref)
    out = np.empty_like(s, dtype=np.complex64)
    blk = 4096
    for i in range(0, N, blk):
        chunk = s[i:i+blk]
        # compute |chunk - ref|^2 for each ref
        # distances shape (len(chunk), M)
        distances = np.abs(chunk[:,None] - ref[None,:])**2
        idx = np.argmin(distances, axis=1)
        out[i:i+blk] = ref[idx]
    return out

class mer_evm_logger(gr.sync_block):
    """
    Compute EVM (%) and MER (dB) over windows and log to CSV.
    constellation: 'qpsk' | '16qam' | '64qam'
    """
    def __init__(self, csv_path="metrics/tx_metrics.csv", window=4096, constellation="qpsk"):
        gr.sync_block.__init__(self,
            name="mer_evm_logger",
            in_sig=[np.complex64],
            out_sig=[np.complex64])
        self.csv_path = csv_path
        self.window = max(256, int(window))
        self.constellation = constellation.lower()
        self.ref = ref_points(self.constellation)
        self.buf = np.zeros(self.window, dtype=np.complex64)
        self.idx = 0
        os.makedirs(os.path.dirname(self.csv_path), exist_ok=True)
        if not os.path.exists(self.csv_path):
            with open(self.csv_path, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["ts_unix", "samples", "constellation", "evm_pct", "mer_db"])

    def work(self, input_items, output_items):
        x = input_items[0]
        y = output_items[0]
        y[:] = x  # passthrough
        n = len(x)
        if n == 0:
            return 0

        start = 0
        while start < n:
            take = min(self.window - self.idx, n - start)
            self.buf[self.idx:self.idx+take] = x[start:start+take]
            self.idx += take
            start += take
            if self.idx == self.window:
                s = self.buf
                r = hard_decide(s, self.ref)
                err = s - r
                evm_rms = np.sqrt(np.mean(np.abs(err)**2))
                ref_rms = np.sqrt(np.mean(np.abs(r)**2))
                evm_pct = 100.0 * evm_rms / (ref_rms + 1e-12)
                mer_db = 20.0 * np.log10( (ref_rms + 1e-12) / (evm_rms + 1e-12) )
                with open(self.csv_path, "a", newline="") as f:
                    w = csv.writer(f)
                    w.writerow([time.time(), self.window, self.constellation, f"{evm_pct:.3f}", f"{mer_db:.3f}"])
                self.idx = 0
        return n
