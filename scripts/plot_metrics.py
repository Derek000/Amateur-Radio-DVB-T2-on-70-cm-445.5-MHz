#!/usr/bin/env python3
import argparse, os, time, pandas as pd
import matplotlib.pyplot as plt
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="metrics/tx_metrics.csv")
    ap.add_argument("--outdir", default="reports")
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    df = pd.read_csv(a.csv)
    df["ts"] = pd.to_datetime(df["ts_unix"], unit="s")
    plt.figure()
    for c in df["constellation"].unique():
        sub = df[df["constellation"]==c]; plt.plot(sub["ts"], sub["mer_db"], label=f"MER {c}")
    plt.xlabel("Time"); plt.ylabel("MER (dB)"); plt.legend(); plt.tight_layout()
    plt.savefig(os.path.join(a.outdir, "mer_over_time.png")); plt.close()
    plt.figure()
    for c in df["constellation"].unique():
        sub = df[df["constellation"]==c]; plt.plot(sub["ts"], sub["evm_pct"], label=f"EVM% {c}")
    plt.xlabel("Time"); plt.ylabel("EVM (%)"); plt.legend(); plt.tight_layout()
    plt.savefig(os.path.join(a.outdir, "evm_over_time.png")); plt.close()
    summary = df.groupby("constellation").agg(mer_db_mean=("mer_db","mean"),evm_pct_mean=("evm_pct","mean")).reset_index()
    html = f"""<!DOCTYPE html><html><head><meta charset='utf-8'><title>DVB-T2 Metrics</title>
<style>body{{font-family:sans-serif;max-width:900px;margin:40px auto}}table{{border-collapse:collapse}}td,th{{border:1px solid #ccc;padding:6px}}</style></head><body>
<h1>DVB-T2 MER/EVM Report</h1><p>Generated: {time.ctime()}</p>
<h2>MER over time</h2><img src='mer_over_time.png' style='max-width:100%'/>
<h2>EVM over time</h2><img src='evm_over_time.png' style='max-width:100%'/>
<h2>Summary</h2>{summary.to_html(index=False)}</body></html>"""
    open(os.path.join(a.outdir,"index.html"),"w",encoding="utf-8").write(html)
if __name__ == "__main__":
    main()
