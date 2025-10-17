# Amateur Radio DVB‑T2 on 70 cm (445.5 MHz) – GNU Radio, LimeSDR/PlutoSDR

A professional, reproducible **DVB‑T2** transmitter/receiver chain for **445.5 MHz** with a **7 MHz** channel, focused on **spectral purity** and **robust decode** (QPSK, CR 1/2). Runs on GNU Radio 3.10+ with the `gr-dvbt2` OOT module. Supports **LimeSDR** (Soapy/LimeSuite) and **PlutoSDR** (libiio/SoapyPluto).

## Repository layout
```
grc/
  tx_dvbt2_445_5MHz.grc
  tx_dvbt2_445_5MHz_with_metrics.grc
  rx_dvbt2_445_5MHz.grc
  rx_dvbt2_grblocks_445_5MHz.grc
  blocks/mer_evm_logger.py
scripts/
  encode_h264_ts.sh
  run_tx.sh
  run_rx.sh
  patch_grc_from_params.py
  plot_metrics.py
  inject_metrics_block.py
  run_external_rx.sh
  ts_cc_monitor.py
docs/
  SPECTRAL_PURITY_CHECKLIST.md
  ARCHITECTURE.md
  REFERENCES.md
  STB_NOTES.md
  METRICS.md
  EXTERNAL_RX.md
params.yaml
Dockerfile
.devcontainer/devcontainer.json
.github/workflows/ci.yml
Makefile
LICENSE | SECURITY.md | CODE_OF_CONDUCT.md | CONTRIBUTING.md
.gitignore | .gitattributes
```

## Quick start
1. **Dependencies**
   - GNU Radio 3.10+
   - `gr-dvbt2` (build from source; see docs/REFERENCES.md)
   - For LimeSDR: SoapySDR + SoapyLMS7 + LimeSuite
   - For PlutoSDR: libiio + gr-iio *or* SoapyPlutoSDR
2. **Feed H.264→MPEG‑TS** to TX via UDP and run:
   ```bash
   ./scripts/encode_h264_ts.sh sample.mp4
   ./scripts/run_tx.sh
   ./scripts/run_rx.sh
   # VLC: udp://@127.0.0.1:5006
   ```
3. **Parameters auto‑patcher**
   ```bash
   python3 scripts/patch_grc_from_params.py params.yaml      grc/tx_dvbt2_445_5MHz.grc grc/rx_dvbt2_445_5MHz.grc
   ```

## Spectral purity
See `docs/SPECTRAL_PURITY_CHECKLIST.md`: tight TX/RX BPF around 7 MHz, device RF‑BW ≈ 7.5 MHz, IQ/DC calibration, TX back‑off to keep **shoulders ≤ −40 dBc**.

## Metrics and reporting
- TX metrics variant: `grc/tx_dvbt2_445_5MHz_with_metrics.grc` (MER/EVM logger inserted).
- Auto‑inject/remove EPY block:
  ```bash
  python3 scripts/inject_metrics_block.py grc/tx_dvbt2_445_5MHz.grc --insert     --args '"metrics/tx_metrics.csv", 4096, "qpsk"'
  # ... later
  python3 scripts/inject_metrics_block.py grc/tx_dvbt2_445_5MHz.grc --remove
  ```
- Plot + HTML report:
  ```bash
  python3 scripts/plot_metrics.py --csv metrics/tx_metrics.csv --outdir reports
  # Open reports/index.html
  ```

## External DVB‑T2 receiver (optional, GPL‑3.0)
We support an **optional** external receiver for A/B validation:
- Add as submodule: `git submodule add https://github.com/Oleg-Malyutin/sdr_receiver_dvb_t2 extern/sdr_receiver_dvb_t2`
- See `docs/EXTERNAL_RX.md` (Linux/Windows) and licence guidance.
- Use `scripts/ts_cc_monitor.py` to watch MPEG‑TS continuity counters.

## Alternative GNU Radio RX (gr-dvbs2rx)
The devcontainer builds `gr-dvbt2` and **`gr-dvbs2rx`** so you can test the GRC‑only RX variant:
- Flowgraph: `grc/rx_dvbt2_grblocks_445_5MHz.grc`

## Licence
MIT (see `LICENSE`). For Amateur Radio use: comply with local regulations and band plans.
