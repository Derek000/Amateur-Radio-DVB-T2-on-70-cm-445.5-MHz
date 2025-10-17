# Amateur Radio DVB‑T2 on 70 cm (445.5 MHz) – GNU Radio, LimeSDR/PlutoSDR

A professional, reproducible **DVB‑T2** transmitter/receiver chain for **445.5 MHz** with a **7 MHz** channel, aimed at **spectral purity** and **robust decode** (QPSK, CR 1/2). Runs on GNU Radio 3.10+ with the `gr-dvbt2` OOT module. Works with **LimeSDR** (Soapy/LimeSuite) and **PlutoSDR** (libiio/SoapyPluto).

> DVB‑T2 (H.264/MPEG‑4) aligns with current 70 cm ATV practice. For wide coverage, start with **QPSK + 1/2**.

## Repository layout
```
grc/                      # GNU Radio Companion flowgraphs
  tx_dvbt2_445_5MHz.grc
  rx_dvbt2_445_5MHz.grc
scripts/                  # Helper scripts & runners
  encode_h264_ts.sh
  run_tx.sh
  run_rx.sh
docs/
  SPECTRAL_PURITY_CHECKLIST.md
  ARCHITECTURE.md
  REFERENCES.md
  STB_NOTES.md
params.yaml               # Centralised parameters
Dockerfile                # Optional container build (GNURadio + gr-dvbt2)
.devcontainer/devcontainer.json
Makefile
LICENSE
SECURITY.md
CODE_OF_CONDUCT.md
CONTRIBUTING.md
.github/workflows/ci.yml # Lint & metadata checks
```

## Quick start
1. **Dependencies**
   - GNU Radio 3.10+
   - `gr-dvbt2` (build from source; see docs/REFERENCES.md)
   - For LimeSDR: SoapySDR + SoapyLMS7 + LimeSuite
   - For PlutoSDR: libiio + gr-iio *or* SoapyPlutoSDR
2. **Feed H.264→MPEG‑TS** to the TX via UDP and run the flows:
   ```bash
   ./scripts/encode_h264_ts.sh sample.mp4
   ./scripts/run_tx.sh   # Open GRC; press ▶
   ./scripts/run_rx.sh   # Open GRC; press ▶
   # VLC: udp://@127.0.0.1:5006
   ```
3. **Tuneables**: edit `params.yaml` then set the corresponding variables in GRC (**rf_freq**, **chan_bw**, **samp_rate**, gains).

## Spectral purity – checklist
See `docs/SPECTRAL_PURITY_CHECKLIST.md`. Highlights:
- Tight digital BPF around 7 MHz (TX post‑mod, RX pre‑demod)
- Device RF‑BW ≈ 7.5 MHz; enable IQ/DC calibration
- TX gain back‑off to keep **shoulders ≤ −40 dBc**
- Prefer a shared **10 MHz reference** and an **external 70 cm BPF** for OTA

## STB compatibility (DVB‑T vs DVB‑T2)
- Many legacy STBs decode **DVB‑T/MPEG‑2** only. For **H.264**, you typically need **DVB‑T2** capable STBs.
- Some Strong STBs can manual‑tune **445.5 MHz** on 70 cm and support **DVB‑T2**.

## Licence
MIT (see `LICENSE`). For Amateur Radio use: **observe local regulations** and operate within band/channel allocations.


## Parameters auto‑patcher
Sync `.grc` variables with `params.yaml`:
```bash
python3 scripts/patch_grc_from_params.py params.yaml grc/tx_dvbt2_445_5MHz.grc grc/rx_dvbt2_445_5MHz.grc
```
This updates `rf_freq`, `chan_bw`, `samp_rate`, and device gains/bandwidth (where applicable).

## MER/EVM metrics
Use the TX variant with metrics:
```
grc/tx_dvbt2_445_5MHz_with_metrics.grc
```
It writes rolling CSV to `metrics/tx_metrics.csv`. See `docs/METRICS.md`.


### Metrics and reporting
- Use **metrics variant**: `grc/tx_dvbt2_445_5MHz_with_metrics.grc` (EPY block inserted).
- Or auto‑inject into any TX graph:
  ```bash
  python3 scripts/inject_metrics_block.py grc/tx_dvbt2_445_5MHz.grc --insert     --args '"metrics/tx_metrics.csv", 4096, "qpsk"'
  ```
- Plot + HTML report:
  ```bash
  python3 scripts/plot_metrics.py --csv metrics/tx_metrics.csv --outdir reports
  # Open reports/index.html
  ```
