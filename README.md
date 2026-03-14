# Amateur Radio DVB-T2 on 70 cm (445.5 MHz)

**GNU Radio · LimeSDR / PlutoSDR · QPSK CR 1/2 · 7 MHz channel**

A professional, reproducible DVB-T2 transmitter/receiver chain targeting
445.5 MHz with a 7 MHz channel. Designed for spectral purity, robust decode,
and headless / SSH-safe operation. Runs on GNU Radio 3.10+ with the
[`gr-dvbt2`](https://github.com/drmpeg/gr-dvbt2) OOT module. Supports
**LimeSDR** (Soapy/LimeSuite) and **PlutoSDR** (libiio / SoapyPluto).

---

## Repository layout

```
grc/
  tx_dvbt2_445_5MHz.grc              TX flowgraph (Soapy + IIO device blocks)
  tx_dvbt2_445_5MHz_with_metrics.grc TX with MER/EVM logger inserted
  rx_dvbt2_445_5MHz.grc              RX flowgraph
  rx_dvbt2_grblocks_445_5MHz.grc     RX using gr-dvbs2rx all-GRC blocks
  blocks/
    mer_evm_logger.py                Passthrough EPY block: MER/EVM → CSV
scripts/
  run_tx.sh                          Build & run TX (headless/SSH-safe)
  run_rx.sh                          Build & run RX (headless/SSH-safe)
  encode_h264_ts.sh                  Encode video → MPEG-TS → UDP
  patch_grc_from_params.py           Apply params.yaml to GRC files
  inject_metrics_block.py            Insert/remove MER/EVM EPY block
  plot_metrics.py                    Generate HTML MER/EVM report
  ts_cc_monitor.py                   MPEG-TS continuity counter monitor
  check_deps.sh                      Verify all runtime dependencies
  validate_params.py                 Validate params.yaml against DVB-T2 spec
  link_budget.py                     70 cm link budget calculator
  status_monitor.py                  Live terminal MER/EVM dashboard (requires Rich)
docs/
  ARCHITECTURE.md                    Signal chain overview
  METRICS.md                         MER/EVM logging and reporting
  SPECTRAL_PURITY_CHECKLIST.md       TX spectral quality checklist
  EXTERNAL_RX.md                     Optional external DVB-T2 RX submodule
  STB_NOTES.md                       Set-top box compatibility notes
  REFERENCES.md                      Links and reading material
params.yaml                          Single source of truth for all RF params
Dockerfile                           Multi-stage container (builder + runtime)
Makefile                             Developer workflow targets
```

---

## Quick start

### 1 — Check dependencies

```bash
bash scripts/check_deps.sh
```

This verifies GNU Radio, gr-dvbt2, SoapySDR, ffmpeg, and all Python packages.

### 2 — Validate parameters

```bash
python3 scripts/validate_params.py
# or: make validate
```

Checks `params.yaml` against DVB-T2 spec constraints (bandwidth, modulation,
sample rate, gain range, etc.).

### 3 — Encode and transmit

```bash
# Encode a video file and stream it to the TX flowgraph via UDP
./scripts/encode_h264_ts.sh --input sample.mp4

# Or use a synthetic test card (no video file needed)
./scripts/encode_h264_ts.sh --test-card
# make encode-test

# Start the TX flowgraph (headless/SSH-safe — uses grcc)
./scripts/run_tx.sh
# make tx
```

### 4 — Receive

```bash
./scripts/run_rx.sh
# make rx

# Play the decoded stream
vlc udp://@127.0.0.1:5006
```

### 5 — Apply a custom params.yaml

```bash
python3 scripts/patch_grc_from_params.py params.yaml \
    grc/tx_dvbt2_445_5MHz.grc grc/rx_dvbt2_445_5MHz.grc
```

The TX/RX scripts run this automatically before launching.

---

## Headless / SSH operation

`run_tx.sh` and `run_rx.sh` use `grcc` (the GNU Radio command-line compiler)
to build the flowgraph to a Python file and run it directly — no display
required. They fall back to `gnuradio-companion` only if `grcc` is absent and
a display is available. If neither is possible, a clear error is printed.

---

## MER / EVM metrics

```bash
# Run TX with the metrics EPY block inserted
./scripts/run_tx.sh --metrics
# make tx-metrics

# Generate HTML report from the CSV
python3 scripts/plot_metrics.py --csv metrics/tx_metrics.csv --outdir reports
# make report

# Live refresh as the CSV grows
make watch-metrics
```

The HTML report (`reports/index.html`) contains summary stat cards, MER/EVM
time-series plots with alarm threshold lines, and an alarm event table.

### Insert / remove the logger block manually

```bash
python3 scripts/inject_metrics_block.py grc/tx_dvbt2_445_5MHz.grc \
    --insert --src ofdm --dst tx_bpf \
    --args '"metrics/tx_metrics.csv", 4096, "qpsk"'

python3 scripts/inject_metrics_block.py grc/tx_dvbt2_445_5MHz.grc \
    --remove --src ofdm --dst tx_bpf
```

---

## Link budget

```bash
python3 scripts/link_budget.py --params params.yaml --distance 5
# make budget DIST=5
```

Example output for 5 km, QPSK CR 1/2, 27 dBm TX, 6 dBi antennas:

```
DVB-T2 Link Budget  —  445.500 MHz  /  7 MHz BW
────────────────────────────────────────────────────
  Distance                   5.00 km
  Free-space path loss       99.38 dB
  EIRP                       32.00 dBm
  Received signal           -61.38 dBm
  Noise floor               -101.54 dBm
  C/N (actual)               40.16 dB
  C/N required                3.10 dB
  Link margin               +37.06 dB
  Result  ✓ LINK OK
```

---

## MPEG-TS monitor

```bash
# Live continuity counter check
python3 scripts/ts_cc_monitor.py --udp 127.0.0.1:5006 --per-pid

# JSON output for scripting / logging
python3 scripts/ts_cc_monitor.py --udp 127.0.0.1:5006 --json

# From a recorded file
python3 scripts/ts_cc_monitor.py < recording.ts
```

---

## Spectral purity

See [`docs/SPECTRAL_PURITY_CHECKLIST.md`](docs/SPECTRAL_PURITY_CHECKLIST.md).
Key targets: TX shoulders ≤ −40 dBc, RF-BW ≈ 7.5 MHz, IQ/DC calibration,
gain back-off of −6 dB or more.

---

## Docker

```bash
# Build the multi-stage image (builder + lean runtime)
docker build -t ham-dvbt2 .

# Run with USB device access (LimeSDR/PlutoSDR)
docker run -it --privileged -v "$(pwd)":/workspace ham-dvbt2

# Inside the container
bash scripts/run_tx.sh
```

---

## Developer workflow

```bash
make help           # list all targets
make lint           # shellcheck + yamllint + pyflakes
make test           # pytest
make validate       # validate params.yaml
make check-deps     # dependency check
make pack           # create distributable tar.gz
make clean          # remove generated build artefacts
```

---

## External DVB-T2 receiver (optional, GPL-3.0)

```bash
git submodule add https://github.com/Oleg-Malyutin/sdr_receiver_dvb_t2 \
    extern/sdr_receiver_dvb_t2
```

See [`docs/EXTERNAL_RX.md`](docs/EXTERNAL_RX.md) for build and usage.

---

## Licence

MIT — see [`LICENSE`](LICENSE). For amateur radio use: comply with your local
regulations and band plan. In Australia, refer to the ACMA band plan for
70 cm and the relevant WIA/AREG ATV guidelines.
