#!/usr/bin/env python3
import argparse, yaml
from xml.etree import ElementTree as ET
from pathlib import Path

VAR_MAP = { "rf_frequency_hz": "rf_freq", "channel_bandwidth_hz": "chan_bw" }
SR_KEY = "samp_rate"

def set_param(block, key, value):
    for p in block.findall("param"):
        if p.find("key").text == key:
            p.find("value").text = str(value); return True
    return False

def update_grc(path, params):
    tree = ET.parse(path); root = tree.getroot(); changed=False
    for blk in root.findall("block"):
        if blk.find("key").text == "variable":
            pid = None
            for p in blk.findall("param"):
                if p.find("key").text == "id": pid = p.find("value").text
            if pid:
                for yk, vid in VAR_MAP.items():
                    if pid == vid and yk in params:
                        for p in blk.findall("param"):
                            if p.find("key").text == "value":
                                p.find("value").text = str(params[yk]); changed=True
                if pid == SR_KEY:
                    sr = params.get("device", {}).get("tx", {}).get("sample_rate") or params.get("device", {}).get("rx", {}).get("sample_rate")
                    if sr:
                        for p in blk.findall("param"):
                            if p.find("key").text == "value":
                                p.find("value").text = str(sr); changed=True
        key = blk.find("key").text
        if key in ("soapy_sink","soapy_source"):
            prof = params.get("device", {}).get("tx" if key.endswith("sink") else "rx", {})
            if "gain_db" in prof: changed |= set_param(blk, "gain", prof["gain_db"])
            if "rf_bw_hz" in prof: changed |= set_param(blk, "bandwidth", prof["rf_bw_hz"])
        if key in ("iio_pluto_sink","iio_pluto_source"):
            prof = params.get("device", {}).get("tx" if key.endswith("sink") else "rx", {})
            if "gain_db" in prof: changed |= set_param(blk, "rf_gain", prof["gain_db"])
            if "rf_bw_hz" in prof: changed |= set_param(blk, "bw", prof["rf_bw_hz"])
    if changed: tree.write(path, encoding="utf-8", xml_declaration=True)
    return changed

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("params"); ap.add_argument("grc", nargs="+")
    args = ap.parse_args()
    params = yaml.safe_load(open(args.params))
    ok=False
    for g in args.grc:
        if update_grc(Path(g), params): print(f"[OK] Patched {g}"); ok=True
        else: print(f"[INFO] No changes {g}")
    exit(0 if ok else 1)

if __name__ == "__main__":
    main()
