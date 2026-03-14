# Changelog

## [1.1.0] — 2026-03-14

### Fixed — Critical
- **`params.yaml`**: `device.tx/rx.sample_rate` was 4 Msps, which is below the
  Nyquist requirement for a 7 MHz DVB-T2 channel (minimum ~7.7 Msps). Corrected
  to 8 Msps with an explanatory comment.
- **`run_tx.sh` / `run_rx.sh`**: Scripts called `gnuradio-companion` directly,
  making them completely broken in headless/SSH/Docker environments. Rewrote to
  use `grcc` (the GNU Radio command-line compiler) to compile and run the
  flowgraph as a Python script. Falls back to GRC only if a display is available.
- **`encode_h264_ts.sh`**: No check for `ffmpeg` binary, no check that the input
  file exists. Both now produce clear error messages and exit 1.
- **`inject_metrics_block.py`**: Block could be inserted twice silently. Now
  detects an existing block and exits with a clear error.
- **`patch_grc_from_params.py`**: Used bare `open()` without `with`; exited with
  code 1 (error) when no changes were needed, breaking CI pipelines that called
  it on already-patched files. Both fixed. Exit 2 now signals "no changes needed".
- **`plot_metrics.py`**: HTML file handle was never closed (no `with` statement).
  Fixed using a `with open(...)` block.
- **`grc/blocks/mer_evm_logger.py`**: `os.makedirs(os.path.dirname(csv_path))`
  raised `FileNotFoundError` when `csv_path` had no directory component
  (e.g. `"metrics.csv"`), because `os.path.dirname("")` returns `""`. Fixed by
  using `os.path.abspath()` before `dirname`.

### Added
- **`scripts/check_deps.sh`**: Colour-coded dependency checker. Verifies GNU
  Radio, gr-dvbt2, gr-dvbs2rx (optional), SoapySDR, libiio, ffmpeg, grcc, and
  all Python packages. Distinguishes required failures from optional warnings.
  Run via `bash scripts/check_deps.sh` or `make check-deps`.
- **`scripts/validate_params.py`**: Validates `params.yaml` against DVB-T2 spec
  constraints: channel bandwidth, FFT size, guard interval, pilot pattern,
  constellation/code-rate combinations, sample rate vs Nyquist, gain ranges, and
  UDP port ranges. `--strict` flag treats warnings as errors. Integrated into CI.
- **`scripts/link_budget.py`**: DVB-T2 link budget calculator for 70 cm amateur
  radio. Computes FSPL, EIRP, received signal level, noise floor, C/N, and link
  margin against tabulated QEF thresholds (ETSI EN 302 755). Supports all
  standard DVB-T2 constellations and code rates. Run via `make budget DIST=5`.
- **`scripts/status_monitor.py`**: Live terminal MER/EVM dashboard using Rich.
  Reads the metrics CSV and displays a continuously refreshing table with
  colour-coded MER/EVM values, alarm indicators, and rolling statistics.
  `pip install rich` required. Run via `make status`.
- **`--metrics` flag** for `run_tx.sh`: launches the metrics-enabled flowgraph
  variant (`tx_dvbt2_445_5MHz_with_metrics.grc`) directly.
- **`--grblocks` flag** for `run_rx.sh`: launches the `gr-dvbs2rx` all-blocks
  RX variant (`rx_dvbt2_grblocks_445_5MHz.grc`).
- **`--test-card` mode** for `encode_h264_ts.sh`: streams a 60-second synthetic
  SMPTE test card — no video file required.
- **`--params` flag** on `run_tx.sh` and `run_rx.sh`: specify an alternate
  `params.yaml` path.
- **`--watch` mode** for `plot_metrics.py`: continuously regenerates the HTML
  report as the CSV grows during a live TX session.
- **`--dry-run` and `--verbose`** flags for `patch_grc_from_params.py`.
- **`--per-pid` and `--json`** flags for `ts_cc_monitor.py`: per-PID CC
  breakdown and machine-readable JSON output for scripting.
- **`256QAM` support** in `mer_evm_logger.py`.
- **`alarm` column** in metrics CSV: `OK`, `MER_LOW`, or `EVM_HIGH`, with
  configurable thresholds via block constructor args.
- **Alarm event table** in the HTML metrics report.
- **`make help`** target listing all available make targets with descriptions.
- **`make status`, `make budget`, `make clean`** targets.
- **`tests/`**: Pytest-compatible unit tests for `validate_params.py`,
  `link_budget.py`, and `ts_cc_monitor.py`.
- **CI**: Added Python syntax check, `pyflakes` lint, `validate_params.py`, and
  unit test jobs to `.github/workflows/ci.yml`.

### Improved
- **`Dockerfile`**: Converted to a multi-stage build (builder + lean runtime).
  Fixed package name `libvolk2-dev` → `libvolk-dev` (renamed in Ubuntu 22.04+).
  Added `ffmpeg` and Python data packages to the runtime image. Runs as a
  non-root user (`hamradio`, UID 1000). Runs `validate_params.py` on image build.
- **`Makefile`**: Expanded from 2 targets to a full developer workflow with
  `lint`, `test`, `validate`, `check-deps`, `tx`, `rx`, `tx-metrics`,
  `rx-grblocks`, `encode-test`, `report`, `watch-metrics`, `status`, `budget`,
  `pack`, and `clean`.
- **`grc/blocks/mer_evm_logger.py`**: Added thread lock around CSV writes.
  Minimum window size enforced to 256 samples. Improved docstrings.
- **`docs/ARCHITECTURE.md`**: Added ASCII signal-chain diagram, headless
  execution notes, and metrics pipeline diagram.
- **`docs/METRICS.md`**: Documented alarm thresholds, CSV format, and all
  report generation options.
- **`params.yaml`**: Added inline comments explaining each parameter and its
  valid range.

## [1.0.0] — initial

- Initial DVB-T2 TX/RX chain on 445.5 MHz / 7 MHz channel
- GNU Radio 3.10 + gr-dvbt2 + LimeSDR/PlutoSDR (Soapy/IIO)
- MER/EVM logger EPY block (QPSK/16QAM/64QAM)
- `patch_grc_from_params.py`, `inject_metrics_block.py`, `plot_metrics.py`
- `ts_cc_monitor.py`, `encode_h264_ts.sh`
- Docker, devcontainer, GitHub Actions CI
