#!/usr/bin/env python3

import argparse
import sys
import yaml
from xml.etree import ElementTree as ET
from pathlib import Path

# Map YAML keys -> (variable ids) in .grc and device param hints
VAR_MAP = {
    "rf_frequency_hz": "rf_freq",
    "channel_bandwidth_hz": "chan_bw",
}
# Sample rate mapping (tx/rx separate possible later)
SR_KEY = "samp_rate"

DEVICE_HINTS = {
    "lime": {"gain_key": "gain", "bw_key": "bandwidth"},
    "pluto": {"gain_key": "rf_gain", "bw_key": "bw"},
}

def set_param(block, key, new_val):
    for p in block.findall("param"):
        if p.find("key").text == key:
            p.find("value").text = str(new_val)
            return True
    return False

def update_grc(grc_path: Path, params: dict) -> bool:
    tree = ET.parse(grc_path)
    root = tree.getroot()
    changed = False

    # Update variables
    for blk in root.findall("block"):
        key = blk.find("key").text if blk.find("key") is not None else ""
        if key == "variable":
            pid = None
            for p in blk.findall("param"):
                if p.find("key").text == "id":
                    pid = p.find("value").text
            if pid:
                for ykey, vid in VAR_MAP.items():
                    if pid == vid and ykey in params:
                        # set numeric in scientific if needed
                        val = params[ykey]
                        # variables want float exprs like 445.5e6 for Hz; use plain number
                        for p in blk.findall("param"):
                            if p.find("key").text == "value":
                                p.find("value").text = str(val if isinstance(val, (int,float)) else val)
                                changed = True
                if pid == SR_KEY:
                    # prefer tx sample rate param if present else rx
                    sr = params.get("device", {}).get("tx", {}).get("sample_rate") or params.get("device", {}).get("rx", {}).get("sample_rate")
                    if sr:
                        for p in blk.findall("param"):
                            if p.find("key").text == "value":
                                p.find("value").text = str(sr)
                                changed = True

    # Update device blocks' gain and bandwidth if present
    dev = params.get("device", {})
    for blk in root.findall("block"):
        bkey = blk.find("key").text if blk.find("key") is not None else ""
        if bkey in ("soapy_sink", "soapy_source"):
            # assume Lime
            lime = dev.get("tx" if bkey.endswith("sink") else "rx", {})
            if "gain_db" in lime:
                changed |= set_param(blk, "gain", lime["gain_db"])
            if "rf_bw_hz" in lime:
                changed |= set_param(blk, "bandwidth", lime["rf_bw_hz"])
        if bkey in ("iio_pluto_sink", "iio_pluto_source"):
            pl = dev.get("tx" if bkey.endswith("sink") else "rx", {})
            if "gain_db" in pl:
                changed |= set_param(blk, "rf_gain", pl["gain_db"])
            if "rf_bw_hz" in pl:
                changed |= set_param(blk, "bw", pl["rf_bw_hz"])

    if changed:
        tree.write(grc_path, encoding="utf-8", xml_declaration=True)
    return changed

def main():
    ap = argparse.ArgumentParser(description="Patch GNU Radio .grc from params.yaml")
    ap.add_argument("--params", default="params.yaml", help="YAML path (default: params.yaml)")
    ap.add_argument("grc", nargs="+", help=".grc files to patch")
    args = ap.parse_args()

    with open(args.params, "r", encoding="utf-8") as f:
        params = yaml.safe_load(f)

    total = 0
    for grc_path in args.grc:
        path = Path(grc_path)
        if not path.exists():
            print(f"[WARN] Missing: {path}", file=sys.stderr); continue
        if update_grc(path, params):
            print(f"[OK] Patched: {path}")
            total += 1
        else:
            print(f"[INFO] No changes: {path}")
    if total == 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
