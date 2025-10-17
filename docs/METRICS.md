# Metrics: MER & EVM

This repo includes a **MER/EVM logger** that you can insert in the TX chain to validate baseband cleanliness **before** the DAC.

- Block: `grc/blocks/mer_evm_logger.py` (Embedded Python block)
- Flowgraph variant: `grc/tx_dvbt2_445_5MHz_with_metrics.grc`
- Output: `metrics/tx_metrics.csv` with `ts_unix, samples, evm_pct, mer_db` rows

## Where it measures
Placed **after the DVB‑T2 OFDM modulator and before the TX BPF**.
This estimates symbol-domain errors assuming **QPSK** reference.
It is best for **relative** comparisons across your tuning (filter order, back‑off, RF‑BW).

> Note: On RX, true post‑equaliser symbol taps are internal to the demod block, so we provide TX‑side metrics. If you need RX‑side MER, add a File Sink at the appropriate internal point (if exposed) and process offline with a custom flow.

## Targets (bench)
- EVM: the lower the better; track relative improvements
- MER: aim higher (e.g., >30 dB at TX baseband typically indicates good linearity/headroom)

## Usage
- Open `grc/tx_dvbt2_445_5MHz_with_metrics.grc` and run while sending TS via `encode_h264_ts.sh`.
- Metrics CSV accumulates every 4096 symbols in `metrics/tx_metrics.csv`.
- Plot with your favourite tool (e.g., Pandas/Matplotlib).

## Caveats
- The logger does hard‑decision QPSK reference on unit circle; for higher constellations extend the block accordingly.
- OFDM windowing and subcarrier mapping affect the 'ideal' points; treat results as **relative** indicators in your chain.


## Constellations supported
- QPSK, 16QAM, 64QAM. Select by setting the EPY args to `"metrics/tx_metrics.csv", 4096, "16qam"` etc.

## Plotting and report
Generate plots and a simple HTML report:
```bash
python3 scripts/plot_metrics.py --csv metrics/tx_metrics.csv --outdir reports
# See reports/index.html
```

## Auto-inject/remove EPY block
Insert metrics logger between `ofdm` and `tx_bpf`:
```bash
python3 scripts/inject_metrics_block.py grc/tx_dvbt2_445_5MHz.grc --insert   --args '"metrics/tx_metrics.csv", 4096, "qpsk"'
```
Remove it again:
```bash
python3 scripts/inject_metrics_block.py grc/tx_dvbt2_445_5MHz.grc --remove
```
You can customise `--src`/`--dst` if your block IDs differ.
