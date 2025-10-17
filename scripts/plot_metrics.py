#!/usr/bin/env python3
import argparse, csv, os, time, statistics
import pandas as pd
import matplotlib.pyplot as plt

def main():
    ap = argparse.ArgumentParser(description="Plot MER/EVM metrics and generate HTML report")
    ap.add_argument("--csv", default="metrics/tx_metrics.csv")
    ap.add_argument("--outdir", default="reports")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    df = pd.read_csv(args.csv)
    if df.empty:
        print("No data in CSV"); return

    # Convert ts to datetime
    df["ts"] = pd.to_datetime(df["ts_unix"], unit="s")
    # Line plots
    plt.figure()
    for const in df["constellation"].unique():
        sub = df[df["constellation"]==const]
        plt.plot(sub["ts"], sub["mer_db"], label=f"MER {const}")
    plt.xlabel("Time"); plt.ylabel("MER (dB)"); plt.legend(); plt.tight_layout()
    mer_png = os.path.join(args.outdir, "mer_over_time.png")
    plt.savefig(mer_png); plt.close()

    plt.figure()
    for const in df["constellation"].unique():
        sub = df[df["constellation"]==const]
        plt.plot(sub["ts"], sub["evm_pct"], label=f"EVM% {const}")
    plt.xlabel("Time"); plt.ylabel("EVM (%)"); plt.legend(); plt.tight_layout()
    evm_png = os.path.join(args.outdir, "evm_over_time.png")
    plt.savefig(evm_png); plt.close()

    # Summary stats
    summary = df.groupby("constellation").agg(
        mer_db_mean=("mer_db", "mean"),
        mer_db_min=("mer_db", "min"),
        mer_db_max=("mer_db", "max"),
        evm_pct_mean=("evm_pct", "mean"),
        evm_pct_min=("evm_pct", "min"),
        evm_pct_max=("evm_pct", "max"),
        samples=("samples","sum")
    ).reset_index()

    summary_csv = os.path.join(args.outdir, "summary.csv")
    summary.to_csv(summary_csv, index=False)

    # HTML report
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>DVB-T2 Metrics Report</title>
<style>body{{font-family:sans-serif; max-width:900px; margin:40px auto}} table{{border-collapse:collapse}} td,th{{border:1px solid #ccc; padding:6px}}</style>
</head><body>
<h1>DVB-T2 MER/EVM Report</h1>
<p>Generated: {time.ctime()}</p>
<h2>MER over time</h2>
<img src="mer_over_time.png" style="max-width:100%"/>
<h2>EVM over time</h2>
<img src="evm_over_time.png" style="max-width:100%"/>
<h2>Summary</h2>
{summary.to_html(index=False)}
<p>Source CSV: {args.csv}</p>
</body></html>
"""
    report_html = os.path.join(args.outdir, "index.html")
    with open(report_html, "w", encoding="utf-8") as f:
        f.write(html)
    print("Wrote:", mer_png, evm_png, summary_csv, report_html)

if __name__ == "__main__":
    main()
