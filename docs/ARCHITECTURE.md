# Architecture

## Signal chain overview

```
┌─────────────────────────────────────────────────────────────────────┐
│  TX chain                                                           │
│                                                                     │
│  ffmpeg                                                             │
│  encode_h264_ts.sh ──► UDP:5004 ──► DVB-T2 BB encoder              │
│                                         │                           │
│                                         ▼                           │
│                                  OFDM modulator                     │
│                                  (FFT 8k, GI 1/32, QPSK, CR 1/2)  │
│                                         │                           │
│                                (optional: MER/EVM logger)           │
│                                         │                           │
│                                         ▼                           │
│                                    TX BPF (~7 MHz)                  │
│                                         │                           │
│                            ┌────────────┴────────────┐             │
│                            ▼                          ▼             │
│                      Soapy sink                 IIO PlutoSDR sink   │
│                      (LimeSDR)                  (PlutoSDR)          │
│                       RF-BW ≈ 7.5 MHz, gain back-off −6 dB         │
└─────────────────────────────────────────────────────────────────────┘

                         ≈ 445.5 MHz / 7 MHz channel
                         Shoulders ≤ −40 dBc

┌─────────────────────────────────────────────────────────────────────┐
│  RX chain                                                           │
│                                                                     │
│            ┌────────────┬────────────┐                             │
│            ▼            ▼            ▼                             │
│      Soapy source  IIO PlutoSDR  gr-dvbs2rx (gr-blocks variant)   │
│      (LimeSDR)     source                                          │
│            │            │                                           │
│            └─────┬──────┘                                           │
│                  ▼                                                   │
│             RX BPF (~7 MHz)                                         │
│                  │                                                   │
│                  ▼                                                   │
│           DVB-T2 demodulator                                        │
│                  │                                                   │
│                  ▼                                                   │
│             UDP:5006 ──► VLC / STB / ts_cc_monitor.py               │
└─────────────────────────────────────────────────────────────────────┘
```

## Device selection

Both device sink/source blocks are included in each flowgraph. Disable the
unused one in GRC before running. The `patch_grc_from_params.py` script
updates gain and RF-BW for whichever block is active.

## Headless execution

`run_tx.sh` and `run_rx.sh` invoke `grcc` to compile the `.grc` XML to
a standalone Python file, then `exec python3 <file>.py`. No display or
X server is required. This makes the scripts SSH-safe and suitable for
Docker / CI environments.

## Metrics pipeline

```
TX flowgraph
  └─ mer_evm_logger (EPY block, passthrough)
       └─ metrics/tx_metrics.csv
            └─ plot_metrics.py ──► reports/index.html
                                       ├─ mer_over_time.png
                                       └─ evm_over_time.png
```

The logger block is inserted/removed non-destructively by
`inject_metrics_block.py`, which rewires connections rather than editing
signal-path blocks.

## Parameter flow

```
params.yaml
   └─ patch_grc_from_params.py
        ├─ grc/tx_dvbt2_445_5MHz.grc   (variable blocks, Soapy/IIO params)
        └─ grc/rx_dvbt2_445_5MHz.grc
```

`validate_params.py` checks params.yaml before patching to catch invalid
combinations (e.g. sample rate below Nyquist, unsupported constellation).
