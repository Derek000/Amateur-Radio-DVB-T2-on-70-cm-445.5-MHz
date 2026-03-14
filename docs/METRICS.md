# Metrics: MER & EVM

## Overview

The `grc/blocks/mer_evm_logger.py` GNU Radio EPY block measures:

- **MER** (Modulation Error Ratio) in dB — higher is better (QPSK QEF ≈ 10+ dB)
- **EVM** (Error Vector Magnitude) as a percentage — lower is better

It is a **passthrough** block: the signal passes through unchanged. Measurements
are appended to a CSV file at configurable intervals.

Supported constellations: QPSK, 16QAM, 64QAM, 256QAM.

## CSV format

```
ts_unix, samples, constellation, evm_pct, mer_db, alarm
1710000000.123, 4096, qpsk, 1.2340, 38.1500, OK
```

The `alarm` column is `OK`, `MER_LOW`, or `EVM_HIGH`, based on configurable
thresholds (default: MER < 15 dB or EVM > 15%).

## Usage

### Option A — Pre-built metrics flowgraph

```bash
./scripts/run_tx.sh --metrics
# make tx-metrics
```

### Option B — Inject into the standard flowgraph

```bash
python3 scripts/inject_metrics_block.py grc/tx_dvbt2_445_5MHz.grc \
    --insert --src ofdm --dst tx_bpf \
    --args '"metrics/tx_metrics.csv", 4096, "qpsk"'
```

### Remove the block

```bash
python3 scripts/inject_metrics_block.py grc/tx_dvbt2_445_5MHz.grc \
    --remove --src ofdm --dst tx_bpf
```

## Report generation

```bash
# One-shot
python3 scripts/plot_metrics.py --csv metrics/tx_metrics.csv --outdir reports
# make report

# Live refresh every 10 seconds
python3 scripts/plot_metrics.py --csv metrics/tx_metrics.csv --watch
# make watch-metrics

# Custom alarm thresholds
python3 scripts/plot_metrics.py --mer-alarm 12 --evm-alarm 20 \
    --csv metrics/tx_metrics.csv --outdir reports
```

The HTML report includes:
- Summary stat cards (total windows, mean/min MER, mean/max EVM, alarm count)
- MER and EVM time-series plots with threshold lines
- Per-constellation summary table
- Alarm event table

## Alarm thresholds

| Parameter     | Default | Meaning                          |
|---------------|---------|----------------------------------|
| `mer_alarm`   | 15 dB   | Log `MER_LOW` when MER < this    |
| `evm_alarm`   | 15 %    | Log `EVM_HIGH` when EVM > this   |

For QPSK CR 1/2, DVB-T2 QEF is achieved at C/N ≈ 3.1 dB; typical
MER for a clean signal is 30–40 dB. Alarms at 15 dB leave headroom
for real operational degradation.
