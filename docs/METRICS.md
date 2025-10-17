# Metrics: MER & EVM
- Block: `grc/blocks/mer_evm_logger.py` (QPSK/16QAM/64QAM)
- TX variant: `grc/tx_dvbt2_445_5MHz_with_metrics.grc`
- Output: `metrics/tx_metrics.csv`

## Constellations
Use EPY args: `"metrics/tx_metrics.csv", 4096, "16qam"` or `"64qam"` to match your mod profile.

## Plotting and report
```bash
python3 scripts/plot_metrics.py --csv metrics/tx_metrics.csv --outdir reports
# Open reports/index.html
```

## Auto-inject/remove EPY block
```bash
python3 scripts/inject_metrics_block.py grc/tx_dvbt2_445_5MHz.grc --insert   --args '"metrics/tx_metrics.csv", 4096, "qpsk"'
python3 scripts/inject_metrics_block.py grc/tx_dvbt2_445_5MHz.grc --remove
```
